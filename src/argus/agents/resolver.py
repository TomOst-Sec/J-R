"""Resolver agent — orchestrates platform discovery, scraping, and verification."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from argus.agents.base import BaseAgent
from argus.config.settings import ArgusConfig
from argus.models.agent import AgentInput, ResolverOutput
from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform
from argus.platforms.registry import PlatformRegistry
from argus.storage.database import Database
from argus.storage.repository import AccountRepository, InvestigationRepository
from argus.utils.username_generator import generate_username_candidates
from argus.verification.engine import VerificationEngine
from argus.verification.signals import BioSimilaritySignal, PhotoHashSignal, UsernamePatternSignal

if TYPE_CHECKING:
    import aiohttp

logger = logging.getLogger(__name__)


class ResolverAgent(BaseAgent):
    """Orchestrates platform discovery, scraping, and verification into a single pipeline."""

    name = "resolver"

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        config: ArgusConfig | None = None,
        registry: PlatformRegistry | None = None,
        db: Database | None = None,
    ) -> None:
        self._session = session
        self._config = config or ArgusConfig()
        self._registry = registry or PlatformRegistry()
        self._db = db

    async def _execute(self, input: AgentInput) -> ResolverOutput:
        config = self._config
        target = input.target
        timings: dict[str, float] = {}

        # Step 1: Generate username candidates
        t0 = time.monotonic()
        usernames = generate_username_candidates(target.name)
        if target.username_hint:
            usernames = [target.username_hint] + [u for u in usernames if u != target.username_hint]
        timings["username_gen"] = time.monotonic() - t0

        # Step 2: Scrape seed profiles
        t0 = time.monotonic()
        seed_profiles: list[ProfileData] = []
        if target.seed_urls and self._session:
            seed_profiles = await self._scrape_seeds(target.seed_urls)
        timings["seed_scrape"] = time.monotonic() - t0

        # Step 3: Platform fan-out
        t0 = time.monotonic()
        enabled_platforms = self._registry.get_enabled_platforms(config)
        platform_instances: list[BasePlatform] = []
        if self._session:
            for cls in enabled_platforms:
                try:
                    inst = cls(self._session, config)
                    await inst.initialize(config)
                    platform_instances.append(inst)
                except Exception:
                    logger.warning("Failed to initialize platform %s", cls.name, exc_info=True)

        candidates: list[CandidateProfile] = []
        if platform_instances:
            tasks = [
                self._check_platform(platform, usernames, target.name, target.location)
                for platform in platform_instances
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    candidates.extend(result)
                elif isinstance(result, Exception):
                    logger.warning("Platform fan-out error: %s", result)
        timings["platform_fanout"] = time.monotonic() - t0

        # Step 4: Profile scraping
        t0 = time.monotonic()
        scraped_candidates = await self._scrape_profiles(candidates, platform_instances)
        timings["profile_scrape"] = time.monotonic() - t0

        # Step 5: Verification
        t0 = time.monotonic()
        engine = VerificationEngine(config)
        engine.register_signal(PhotoHashSignal())
        engine.register_signal(BioSimilaritySignal())
        engine.register_signal(UsernamePatternSignal())
        verified = await engine.verify(scraped_candidates, seed_profiles)
        timings["verification"] = time.monotonic() - t0

        # Step 6: Persist
        t0 = time.monotonic()
        if self._db:
            try:
                inv_repo = InvestigationRepository(self._db)
                acct_repo = AccountRepository(self._db)
                inv = await inv_repo.create_investigation(target)
                await acct_repo.save_accounts(inv.id, verified)
                await inv_repo.update_status(inv.id, "completed")
            except Exception:
                logger.warning("Failed to persist results", exc_info=True)
        timings["persist"] = time.monotonic() - t0

        # Step 7: Cleanup
        for inst in platform_instances:
            try:
                await inst.shutdown()
            except Exception:
                pass

        return ResolverOutput(
            target_name=target.name,
            agent_name=self.name,
            accounts=verified,
            metadata={"timings": timings},
        )

    async def _scrape_seeds(self, seed_urls: list[str]) -> list[ProfileData]:
        """Scrape seed URLs to extract ground-truth profiles."""
        profiles: list[ProfileData] = []
        enabled = self._registry.get_enabled_platforms(self._config)
        if not self._session:
            return profiles
        for url in seed_urls:
            for cls in enabled:
                if cls.base_url and cls.base_url in url:
                    try:
                        inst = cls(self._session, self._config)
                        profile = await inst.scrape_profile(url)
                        if profile:
                            profiles.append(profile)
                    except Exception:
                        logger.warning("Seed scrape failed for %s", url, exc_info=True)
                    break
        return profiles

    async def _check_platform(
        self,
        platform: BasePlatform,
        usernames: list[str],
        name: str,
        location: str | None,
    ) -> list[CandidateProfile]:
        """Check username existence and search by name on a platform."""
        candidates: list[CandidateProfile] = []
        try:
            # Check usernames
            for username in usernames:
                try:
                    exists = await platform.check_username(username)
                    if exists:
                        candidates.append(
                            CandidateProfile(
                                platform=platform.name,
                                username=username,
                                url=f"{platform.base_url}/{username}",
                                exists=True,
                            )
                        )
                except Exception:
                    continue

            # Name search
            try:
                search_results = await platform.search_name(name, location)
                for cp in search_results:
                    if not any(c.username == cp.username and c.platform == cp.platform for c in candidates):
                        candidates.append(cp)
            except Exception:
                pass
        except Exception:
            logger.warning("Platform check failed for %s", platform.name, exc_info=True)
        return candidates

    async def _scrape_profiles(
        self,
        candidates: list[CandidateProfile],
        platform_instances: list[BasePlatform],
    ) -> list[CandidateProfile]:
        """Scrape full profiles for all candidates."""
        platform_map = {p.name: p for p in platform_instances}
        scraped: list[CandidateProfile] = []
        for candidate in candidates:
            platform = platform_map.get(candidate.platform)
            if not platform:
                scraped.append(candidate)
                continue
            try:
                profile_data = await platform.scrape_profile(candidate.url)
                scraped.append(
                    CandidateProfile(
                        platform=candidate.platform,
                        username=candidate.username,
                        url=candidate.url,
                        exists=candidate.exists,
                        scraped_data=profile_data,
                    )
                )
            except Exception:
                scraped.append(candidate)
        return scraped

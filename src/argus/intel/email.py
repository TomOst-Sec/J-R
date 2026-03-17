"""Email intelligence -- breach check, MX validation, Gravatar, PGP, linked accounts."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import TYPE_CHECKING

from argus.intel.base import BaseIntelSource, IntelSourceRegistry
from argus.models.intel import (
    BreachRecord,
    EmailReport,
    IntelResult,
    IntelSelector,
    SelectorType,
)

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig

logger = logging.getLogger(__name__)


class EmailIntelModule:
    """Aggregate email intelligence from multiple sources."""

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        self.session = session
        self.config = config
        self._registry = IntelSourceRegistry()
        self._registry.discover_sources()

    async def investigate(self, email: str) -> EmailReport:
        """Run all email intelligence sources in parallel and aggregate results."""
        selector = IntelSelector(selector_type=SelectorType.EMAIL, value=email)

        # Instantiate available sources
        source_names = ["hibp", "email_validate", "pgp"]
        sources: list[BaseIntelSource] = []
        for name in source_names:
            src_cls = self._registry.get_source(name)
            if src_cls is not None:
                src = src_cls(self.session, self.config)
                if await src.is_available():
                    sources.append(src)

        # Run source queries in parallel
        tasks = [src.query(selector) for src in sources]
        # Also run Gravatar check in parallel
        tasks.append(self._check_gravatar(email))

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate
        report = EmailReport(email=email)
        all_intel: list[IntelResult] = []

        for i, result in enumerate(raw_results):
            if isinstance(result, Exception):
                logger.warning("Source query failed: %s", result)
                continue
            if isinstance(result, dict):
                # Gravatar result
                if result.get("found"):
                    report.gravatar_url = result.get("url")
                    report.gravatar_profile = result.get("profile")
                continue
            # list[IntelResult]
            if not isinstance(result, list):
                continue
            for ir in result:
                all_intel.append(ir)
                if ir.source == "hibp" and ir.data.get("found"):
                    for b in ir.data.get("breaches", []):
                        report.breaches.append(
                            BreachRecord(
                                breach_name=b.get("name", "Unknown"),
                                breach_date=None,
                                data_types=b.get("data_classes", []),
                                email=email,
                                description=b.get("description"),
                                is_verified=b.get("is_verified", False),
                                domain=b.get("domain"),
                            )
                        )
                elif ir.source == "email_validate":
                    report.is_deliverable = ir.data.get("is_deliverable")
                    report.mx_records = ir.data.get("mx_records", [])
                elif ir.source == "pgp":
                    report.pgp_keys = ir.data.get("keys", [])

        report.sources = all_intel
        return report

    async def _check_gravatar(self, email: str) -> dict:
        """Check Gravatar for a profile associated with the email."""
        email_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()  # noqa: S324
        url = f"https://en.gravatar.com/{email_hash}.json"
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    entry = data.get("entry", [{}])[0] if data.get("entry") else {}
                    return {
                        "found": True,
                        "url": f"https://gravatar.com/avatar/{email_hash}",
                        "profile": {
                            "display_name": entry.get("displayName"),
                            "about": entry.get("aboutMe"),
                            "urls": entry.get("urls", []),
                            "photos": entry.get("photos", []),
                        },
                    }
        except Exception:
            logger.debug("Gravatar lookup failed for %s", email)
        return {"found": False}

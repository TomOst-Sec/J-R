"""Batch processor — resolve multiple targets from CSV."""

from __future__ import annotations

import asyncio
import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argus.config.settings import ArgusConfig
from argus.models.target import TargetInput

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Results of a batch investigation."""

    targets_processed: int = 0
    targets_skipped: int = 0
    total_accounts: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


def read_targets_csv(csv_path: Path) -> list[TargetInput]:
    """Read targets from CSV. Required column: name. Optional: location, email, username_hint, seed_url."""
    targets: list[TargetInput] = []
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue
            seed_urls = []
            seed_url = row.get("seed_url", "").strip()
            if seed_url:
                seed_urls = [s.strip() for s in seed_url.split(";") if s.strip()]
            targets.append(
                TargetInput(
                    name=name,
                    location=row.get("location", "").strip() or None,
                    email=row.get("email", "").strip() or None,
                    username_hint=row.get("username_hint", "").strip() or None,
                    seed_urls=seed_urls,
                )
            )
    return targets


class BatchProcessor:
    """Process multiple targets concurrently."""

    def __init__(self, config: ArgusConfig | None = None, max_parallel: int = 3) -> None:
        self._config = config or ArgusConfig()
        self._max_parallel = max_parallel

    async def process(
        self,
        csv_path: Path,
        on_progress: Any = None,
    ) -> BatchResult:
        """Process all targets from CSV.

        Args:
            csv_path: Path to CSV file with targets.
            on_progress: Optional callback(target_name, index, total).
        """
        targets = read_targets_csv(csv_path)
        result = BatchResult()
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def _process_one(idx: int, target: TargetInput) -> None:
            async with semaphore:
                if on_progress:
                    on_progress(target.name, idx + 1, len(targets))
                try:
                    count = await self._resolve_target(target)
                    result.targets_processed += 1
                    result.total_accounts += count
                except Exception as e:
                    result.errors.append({"target": target.name, "error": str(e)})
                    logger.warning("Batch error for %s: %s", target.name, e)

        tasks = [_process_one(i, t) for i, t in enumerate(targets)]
        await asyncio.gather(*tasks)
        return result

    async def _resolve_target(self, target: TargetInput) -> int:
        """Resolve a single target. Returns account count."""
        import aiohttp

        from argus.agents.resolver import ResolverAgent
        from argus.models.agent import AgentInput
        from argus.platforms.registry import PlatformRegistry
        from argus.storage.database import Database

        registry = PlatformRegistry()
        registry.discover_platforms()

        db = Database()
        await db.initialize()

        async with aiohttp.ClientSession() as session:
            agent = ResolverAgent(
                session=session, config=self._config, registry=registry, db=db
            )
            output = await agent.execute(AgentInput(target=target))

        await db.close()
        return len(output.accounts) if output else 0

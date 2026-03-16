"""Batch investigation — process multiple targets from CSV."""

from __future__ import annotations

import asyncio
import csv
import io
from dataclasses import dataclass
from pathlib import Path

from argus.config.settings import ArgusConfig
from argus.models.target import TargetInput


@dataclass
class BatchResult:
    """Result of a single batch item."""

    target_name: str
    status: str  # "success" | "error"
    accounts_found: int
    error_message: str | None = None
    output_json: str | None = None


def parse_csv(source: str | Path) -> list[TargetInput]:
    """Parse a CSV file or string into TargetInput objects.

    Expected columns: name (required), location, email, username_hint, phone, seed_urls
    seed_urls should be semicolon-separated if multiple.
    """
    path = Path(source)
    if path.exists():
        text = path.read_text()
    else:
        text = source

    targets: list[TargetInput] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        name = row.get("name", "").strip()
        if not name:
            continue
        seed_urls_str = row.get("seed_urls", "")
        seed_urls = [u.strip() for u in seed_urls_str.split(";") if u.strip()] if seed_urls_str else []
        targets.append(
            TargetInput(
                name=name,
                location=row.get("location", "").strip() or None,
                email=row.get("email", "").strip() or None,
                username_hint=row.get("username_hint", "").strip() or None,
                phone=row.get("phone", "").strip() or None,
                seed_urls=seed_urls,
            )
        )
    return targets


async def run_batch(
    targets: list[TargetInput],
    config: ArgusConfig | None = None,
    max_concurrent: int = 3,
) -> list[BatchResult]:
    """Run investigations for multiple targets with concurrency control."""
    import aiohttp

    from argus.agents.resolver import ResolverAgent
    from argus.models.agent import AgentInput
    from argus.platforms.registry import PlatformRegistry

    config = config or ArgusConfig()
    registry = PlatformRegistry()
    registry.discover_platforms()

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[BatchResult] = []

    async def _process_target(target: TargetInput) -> BatchResult:
        async with semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    agent = ResolverAgent(session=session, config=config, registry=registry)
                    output = await agent.run(AgentInput(target=target))
                    return BatchResult(
                        target_name=target.name,
                        status="success",
                        accounts_found=len(output.accounts),
                        output_json=output.model_dump_json(),
                    )
            except Exception as e:
                return BatchResult(
                    target_name=target.name,
                    status="error",
                    accounts_found=0,
                    error_message=str(e),
                )

    tasks = [_process_target(t) for t in targets]
    results = list(await asyncio.gather(*tasks))
    return results


def results_to_csv(results: list[BatchResult]) -> str:
    """Convert batch results to CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["target_name", "status", "accounts_found", "error_message"])
    writer.writeheader()
    for r in results:
        writer.writerow({
            "target_name": r.target_name,
            "status": r.status,
            "accounts_found": r.accounts_found,
            "error_message": r.error_message or "",
        })
    return output.getvalue()

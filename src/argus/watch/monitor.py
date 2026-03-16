"""Change detection monitor — compares investigation snapshots."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

from argus.models.verification import VerificationResult

logger = logging.getLogger(__name__)


@dataclass
class Change:
    """A detected change between investigation snapshots."""

    type: str  # new_account, removed_account, bio_change, confidence_change, new_content
    platform: str
    username: str = ""
    old_value: str = ""
    new_value: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeReport:
    """Summary of all changes detected in a re-check."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    changes: list[Change] = field(default_factory=list)
    summary: str = ""

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0


def diff_results(
    old_accounts: list[VerificationResult],
    new_accounts: list[VerificationResult],
) -> ChangeReport:
    """Compare two sets of verification results and detect changes."""
    changes: list[Change] = []

    old_map = {(a.candidate.platform, a.candidate.username): a for a in old_accounts}
    new_map = {(a.candidate.platform, a.candidate.username): a for a in new_accounts}

    # New accounts
    for key, vr in new_map.items():
        if key not in old_map:
            changes.append(
                Change(
                    type="new_account",
                    platform=vr.candidate.platform,
                    username=vr.candidate.username,
                    new_value=f"confidence={vr.confidence:.2f}",
                )
            )

    # Removed accounts
    for key, vr in old_map.items():
        if key not in new_map:
            changes.append(
                Change(
                    type="removed_account",
                    platform=vr.candidate.platform,
                    username=vr.candidate.username,
                    old_value=f"confidence={vr.confidence:.2f}",
                )
            )

    # Changed accounts
    for key in old_map.keys() & new_map.keys():
        old_vr = old_map[key]
        new_vr = new_map[key]

        # Confidence change
        if abs(old_vr.confidence - new_vr.confidence) > 0.05:
            changes.append(
                Change(
                    type="confidence_change",
                    platform=old_vr.candidate.platform,
                    username=old_vr.candidate.username,
                    old_value=f"{old_vr.confidence:.2f}",
                    new_value=f"{new_vr.confidence:.2f}",
                )
            )

        # Bio change
        old_bio = (old_vr.candidate.scraped_data.bio or "") if old_vr.candidate.scraped_data else ""
        new_bio = (new_vr.candidate.scraped_data.bio or "") if new_vr.candidate.scraped_data else ""
        if old_bio != new_bio and (old_bio or new_bio):
            changes.append(
                Change(
                    type="bio_change",
                    platform=old_vr.candidate.platform,
                    username=old_vr.candidate.username,
                    old_value=old_bio[:100],
                    new_value=new_bio[:100],
                )
            )

    # Build summary
    summary_parts = []
    new_count = sum(1 for c in changes if c.type == "new_account")
    removed_count = sum(1 for c in changes if c.type == "removed_account")
    changed_count = sum(1 for c in changes if c.type not in ("new_account", "removed_account"))
    if new_count:
        summary_parts.append(f"{new_count} new account(s)")
    if removed_count:
        summary_parts.append(f"{removed_count} removed account(s)")
    if changed_count:
        summary_parts.append(f"{changed_count} change(s)")

    report = ChangeReport(
        changes=changes,
        summary=", ".join(summary_parts) if summary_parts else "No changes detected",
    )
    return report


class WatchMonitor:
    """Periodic re-checking of investigations for changes."""

    def __init__(
        self,
        changes_file: Path | str | None = None,
    ) -> None:
        if changes_file is None:
            changes_file = Path.home() / ".argus" / "changes.jsonl"
        self._changes_file = Path(changes_file)
        self._changes_file.parent.mkdir(parents=True, exist_ok=True)

    def save_change_report(self, investigation_id: str, report: ChangeReport) -> None:
        """Append change report to JSONL file."""
        entry = {
            "investigation_id": investigation_id,
            "timestamp": report.timestamp.isoformat(),
            "summary": report.summary,
            "changes": [
                {
                    "type": c.type,
                    "platform": c.platform,
                    "username": c.username,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                }
                for c in report.changes
            ],
        }
        with self._changes_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    async def notify_webhook(self, url: str, report: ChangeReport) -> None:
        """Send change report to a webhook URL."""
        payload = {
            "summary": report.summary,
            "changes_count": len(report.changes),
            "timestamp": report.timestamp.isoformat(),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status >= 400:
                        logger.warning("Webhook notification failed: %d", resp.status)
        except Exception as e:
            logger.warning("Webhook notification error: %s", e)

    def read_changes(self, limit: int = 100) -> list[dict[str, Any]]:
        """Read recent change reports."""
        if not self._changes_file.exists():
            return []
        entries = []
        with self._changes_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-limit:]

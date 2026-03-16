"""Audit logger — records all actions without PII."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """JSON Lines audit logger. No PII — only action metadata."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        if log_path is None:
            log_path = Path.home() / ".argus" / "audit.log"
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action_type: str,
        platform: str | None = None,
        operator_id: str | None = None,
        reason: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Append an audit entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
        }
        if platform:
            entry["platform"] = platform
        if operator_id:
            entry["operator_id"] = operator_id
        if reason:
            entry["reason"] = reason
        if details:
            entry["details"] = details

        with self._log_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_entries(self, limit: int = 100) -> list[dict]:
        """Read recent audit entries."""
        if not self._log_path.exists():
            return []
        entries = []
        with self._log_path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-limit:]

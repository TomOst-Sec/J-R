"""Repository classes for CRUD operations on investigations, accounts, and content."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from argus.storage.database import Database

from argus.models.profile import ContentItem
from argus.models.target import TargetInput
from argus.models.verification import VerificationResult


class InvestigationRepository:
    """CRUD operations for investigations and their targets."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create_investigation(self, target_input: TargetInput) -> dict:
        """Create a new investigation with its target. Returns {id, target_id}."""
        target_id = str(uuid4())
        investigation_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = self._db.conn
        await conn.execute(
            "INSERT INTO targets (id, name, location, seed_urls, email, username_hint, phone, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                target_id,
                target_input.name,
                target_input.location,
                json.dumps(target_input.seed_urls),
                target_input.email,
                target_input.username_hint,
                target_input.phone,
                now,
            ),
        )
        await conn.execute(
            "INSERT INTO investigations (id, target_id, status, created_at, updated_at) "
            "VALUES (?, ?, 'running', ?, ?)",
            (investigation_id, target_id, now, now),
        )
        await conn.commit()
        return {"id": investigation_id, "target_id": target_id}

    async def get_investigation(self, investigation_id: str) -> dict | None:
        """Get investigation by ID. Returns dict with target info or None."""
        conn = self._db.conn
        row = await conn.execute_fetchall(
            "SELECT i.*, t.name, t.location, t.seed_urls, t.email, t.username_hint, t.phone, t.created_at as target_created_at "
            "FROM investigations i JOIN targets t ON i.target_id = t.id "
            "WHERE i.id = ?",
            (investigation_id,),
        )
        if not row:
            return None
        r = dict(row[0])
        r["seed_urls"] = json.loads(r["seed_urls"]) if r["seed_urls"] else []
        return r

    async def update_status(self, investigation_id: str, status: str) -> None:
        """Update investigation status."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._db.conn
        await conn.execute(
            "UPDATE investigations SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, investigation_id),
        )
        await conn.commit()

    async def list_investigations(self) -> list[dict]:
        """List all investigations."""
        conn = self._db.conn
        rows = await conn.execute_fetchall(
            "SELECT i.*, t.name as target_name FROM investigations i "
            "JOIN targets t ON i.target_id = t.id ORDER BY i.created_at DESC"
        )
        return [dict(r) for r in rows]

    async def delete_investigation(self, investigation_id: str) -> None:
        """Delete an investigation and its related data."""
        conn = self._db.conn
        # Get target_id first
        rows = await conn.execute_fetchall(
            "SELECT target_id FROM investigations WHERE id = ?",
            (investigation_id,),
        )
        if not rows:
            return
        target_id = rows[0]["target_id"]

        # Delete content for accounts under this target
        await conn.execute(
            "DELETE FROM content WHERE account_id IN "
            "(SELECT id FROM accounts WHERE target_id = ?)",
            (target_id,),
        )
        await conn.execute("DELETE FROM accounts WHERE target_id = ?", (target_id,))
        await conn.execute("DELETE FROM investigations WHERE id = ?", (investigation_id,))
        await conn.execute("DELETE FROM targets WHERE id = ?", (target_id,))
        await conn.commit()


class AccountRepository:
    """CRUD operations for verified accounts."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def save_accounts(
        self, investigation_id: str, accounts: list[VerificationResult]
    ) -> None:
        """Save verified accounts for an investigation."""
        conn = self._db.conn
        # Get target_id from investigation
        rows = await conn.execute_fetchall(
            "SELECT target_id FROM investigations WHERE id = ?",
            (investigation_id,),
        )
        if not rows:
            return
        target_id = rows[0]["target_id"]

        for vr in accounts:
            account_id = str(uuid4())
            raw_data = json.dumps(vr.model_dump(), default=str)
            now = datetime.now(timezone.utc).isoformat()
            await conn.execute(
                "INSERT OR REPLACE INTO accounts (id, target_id, platform, username, url, confidence, raw_data, verified_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    account_id,
                    target_id,
                    vr.candidate.platform,
                    vr.candidate.username,
                    vr.candidate.url,
                    vr.confidence,
                    raw_data,
                    now,
                ),
            )
        await conn.commit()

    async def get_accounts(self, investigation_id: str) -> list[VerificationResult]:
        """Get all verified accounts for an investigation."""
        conn = self._db.conn
        rows = await conn.execute_fetchall(
            "SELECT a.* FROM accounts a "
            "JOIN investigations i ON a.target_id = i.target_id "
            "WHERE i.id = ?",
            (investigation_id,),
        )
        results = []
        for r in rows:
            raw = json.loads(r["raw_data"]) if r["raw_data"] else None
            if raw:
                results.append(VerificationResult(**raw))
        return results

    async def account_exists(
        self, investigation_id: str, platform: str, username: str
    ) -> bool:
        """Check if an account has already been verified for this investigation."""
        conn = self._db.conn
        rows = await conn.execute_fetchall(
            "SELECT 1 FROM accounts a "
            "JOIN investigations i ON a.target_id = i.target_id "
            "WHERE i.id = ? AND a.platform = ? AND a.username = ?",
            (investigation_id, platform, username),
        )
        return len(rows) > 0


class ContentRepository:
    """CRUD operations for scraped content."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def save_content(self, account_id: str, items: list[ContentItem]) -> None:
        """Save content items for an account."""
        conn = self._db.conn
        for item in items:
            metadata = json.dumps(item.metadata) if item.metadata else None
            await conn.execute(
                "INSERT OR REPLACE INTO content (id, account_id, text, timestamp, content_type, url, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item.id,
                    account_id,
                    item.text,
                    item.timestamp.isoformat() if item.timestamp else None,
                    item.content_type,
                    item.url,
                    metadata,
                ),
            )
        await conn.commit()

    async def get_content(self, account_id: str) -> list[ContentItem]:
        """Get all content for an account."""
        conn = self._db.conn
        rows = await conn.execute_fetchall(
            "SELECT * FROM content WHERE account_id = ?",
            (account_id,),
        )
        results = []
        for r in rows:
            metadata = json.loads(r["metadata"]) if r["metadata"] else None
            results.append(
                ContentItem(
                    id=r["id"],
                    platform="",  # Not stored in content table, caller knows
                    text=r["text"],
                    timestamp=r["timestamp"],
                    content_type=r["content_type"],
                    url=r["url"],
                    metadata=metadata,
                )
            )
        return results

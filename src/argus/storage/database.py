"""SQLite database layer for investigation persistence."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    seed_urls TEXT,
    email TEXT,
    username_hint TEXT,
    phone TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL REFERENCES targets(id),
    status TEXT NOT NULL DEFAULT 'running',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    config TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL REFERENCES targets(id),
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    url TEXT NOT NULL,
    confidence REAL,
    raw_data TEXT,
    verified_at TEXT
);

CREATE TABLE IF NOT EXISTS content (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    text TEXT NOT NULL,
    timestamp TEXT,
    content_type TEXT DEFAULT 'post',
    url TEXT,
    metadata TEXT
);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = ":memory:"
        self._db_path = str(db_path)
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open connection and create tables if they don't exist."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    @property
    def conn(self) -> aiosqlite.Connection:
        """Return the active connection, raising if not initialized."""
        if self._conn is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._conn

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

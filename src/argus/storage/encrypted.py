"""Optional encrypted database using SQLCipher."""

from __future__ import annotations

import os
from pathlib import Path

from argus.storage.database import Database, _SCHEMA


class EncryptedDatabase(Database):
    """SQLCipher-encrypted database. Falls back to regular Database if sqlcipher3 not available."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        encryption_key: str | None = None,
    ) -> None:
        super().__init__(db_path)
        self._encryption_key = encryption_key or os.environ.get("ARGUS_ENCRYPTION_KEY")

    async def initialize(self) -> None:
        """Open encrypted connection and create tables."""
        if not self._encryption_key:
            raise ValueError(
                "Encryption key required. Set via config, ARGUS_ENCRYPTION_KEY env var, or constructor."
            )

        try:
            import importlib.util

            if importlib.util.find_spec("sqlcipher3") is None:
                raise ImportError("sqlcipher3 not found")
        except ImportError:
            raise ImportError(
                "sqlcipher3 package required for encrypted storage. "
                "Install with: pip install argus-osint[encrypted]"
            ) from None

        # sqlcipher3 is synchronous — wrap it
        import aiosqlite

        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute(f"PRAGMA key = '{self._encryption_key}'")
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()


def create_database(
    db_path: Path | str | None = None,
    encryption_enabled: bool = False,
    encryption_key: str | None = None,
) -> Database:
    """Factory: create regular or encrypted Database based on config."""
    if encryption_enabled:
        return EncryptedDatabase(db_path=db_path, encryption_key=encryption_key)
    return Database(db_path=db_path)

# TASK-009: SQLite persistence layer

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-002
**Estimated Complexity:** medium

## Description

Implement SQLite-based investigation storage with full CRUD operations and resume support.

## Requirements

1. Create `src/argus/storage/database.py`:
   - `Database` class:
     - `__init__(self, db_path: Path | None = None)` — default: `~/.argus/investigations/{investigation_id}/argus.db`
     - `async def initialize(self) -> None` — create tables if not exist
     - `async def close(self) -> None`
     - Uses `aiosqlite` for async SQLite access

   - Schema (create tables):
     ```sql
     targets (id TEXT PK, name TEXT, location TEXT, seed_urls TEXT JSON, email TEXT, username_hint TEXT, phone TEXT, created_at TEXT)
     accounts (id TEXT PK, target_id TEXT FK, platform TEXT, username TEXT, url TEXT, confidence REAL, raw_data TEXT JSON, verified_at TEXT)
     content (id TEXT PK, account_id TEXT FK, text TEXT, timestamp TEXT, content_type TEXT, url TEXT, metadata TEXT JSON)
     investigations (id TEXT PK, target_id TEXT FK, status TEXT, created_at TEXT, updated_at TEXT, config TEXT JSON)
     ```

2. Create `src/argus/storage/repository.py`:
   - `InvestigationRepository`:
     - `create_investigation(target: TargetInput) -> Investigation`
     - `get_investigation(id: str) -> Investigation | None`
     - `update_status(id: str, status: str) -> None`
     - `list_investigations() -> list[Investigation]`
     - `delete_investigation(id: str) -> None`
   - `AccountRepository`:
     - `save_accounts(investigation_id: str, accounts: list[VerificationResult]) -> None`
     - `get_accounts(investigation_id: str) -> list[VerificationResult]`
     - `account_exists(investigation_id: str, platform: str, username: str) -> bool`
   - `ContentRepository`:
     - `save_content(account_id: str, items: list[ContentItem]) -> None`
     - `get_content(account_id: str) -> list[ContentItem]`

3. Create `src/argus/storage/__init__.py`:
   - Export `Database`, `InvestigationRepository`, `AccountRepository`, `ContentRepository`

4. Add `aiosqlite` to pyproject.toml dependencies.

## Acceptance Criteria

- Tables created correctly on first initialization
- Full CRUD operations work for investigations, accounts, content
- Investigation resume: can check which platforms already scraped
- JSON fields properly serialized/deserialized
- Unit tests with in-memory SQLite (`:memory:`)
- `uv run pytest tests/test_storage.py` passes

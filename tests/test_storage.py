"""Tests for the SQLite persistence layer."""

from __future__ import annotations

import pytest

from argus.models.profile import CandidateProfile, ContentItem
from argus.models.target import TargetInput
from argus.models.verification import SignalResult, VerificationResult
from argus.storage.database import Database
from argus.storage.repository import (
    AccountRepository,
    ContentRepository,
    InvestigationRepository,
)


@pytest.fixture
async def db():
    """Create an in-memory database for testing."""
    database = Database(db_path=":memory:")
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
def inv_repo(db: Database) -> InvestigationRepository:
    return InvestigationRepository(db)


@pytest.fixture
def acct_repo(db: Database) -> AccountRepository:
    return AccountRepository(db)


@pytest.fixture
def content_repo(db: Database) -> ContentRepository:
    return ContentRepository(db)


class TestDatabase:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self) -> None:
        db = Database(db_path=":memory:")
        await db.initialize()
        rows = await db.conn.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {r["name"] for r in rows}
        assert "targets" in tables
        assert "investigations" in tables
        assert "accounts" in tables
        assert "content" in tables
        await db.close()

    @pytest.mark.asyncio
    async def test_conn_raises_if_not_initialized(self) -> None:
        db = Database()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = db.conn

    @pytest.mark.asyncio
    async def test_double_initialize(self) -> None:
        db = Database(db_path=":memory:")
        await db.initialize()
        await db.initialize()  # Should not fail
        await db.close()


class TestInvestigationRepository:
    @pytest.mark.asyncio
    async def test_create_investigation(self, db: Database, inv_repo: InvestigationRepository) -> None:
        ti = TargetInput(name="John Doe", email="john@example.com")
        result = await inv_repo.create_investigation(ti)
        assert "id" in result
        assert "target_id" in result

    @pytest.mark.asyncio
    async def test_get_investigation(self, db: Database, inv_repo: InvestigationRepository) -> None:
        ti = TargetInput(name="Jane Smith", location="NYC", seed_urls=["https://example.com"])
        result = await inv_repo.create_investigation(ti)
        inv = await inv_repo.get_investigation(result["id"])
        assert inv is not None
        assert inv["name"] == "Jane Smith"
        assert inv["location"] == "NYC"
        assert inv["seed_urls"] == ["https://example.com"]

    @pytest.mark.asyncio
    async def test_get_investigation_not_found(self, db: Database, inv_repo: InvestigationRepository) -> None:
        inv = await inv_repo.get_investigation("nonexistent")
        assert inv is None

    @pytest.mark.asyncio
    async def test_update_status(self, db: Database, inv_repo: InvestigationRepository) -> None:
        ti = TargetInput(name="Test")
        result = await inv_repo.create_investigation(ti)
        await inv_repo.update_status(result["id"], "completed")
        inv = await inv_repo.get_investigation(result["id"])
        assert inv is not None
        assert inv["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_investigations(self, db: Database, inv_repo: InvestigationRepository) -> None:
        await inv_repo.create_investigation(TargetInput(name="A"))
        await inv_repo.create_investigation(TargetInput(name="B"))
        results = await inv_repo.list_investigations()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delete_investigation(self, db: Database, inv_repo: InvestigationRepository) -> None:
        ti = TargetInput(name="Delete Me")
        result = await inv_repo.create_investigation(ti)
        await inv_repo.delete_investigation(result["id"])
        inv = await inv_repo.get_investigation(result["id"])
        assert inv is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db: Database, inv_repo: InvestigationRepository) -> None:
        await inv_repo.delete_investigation("nonexistent")  # Should not raise


class TestAccountRepository:
    @pytest.mark.asyncio
    async def test_save_and_get_accounts(
        self, db: Database, inv_repo: InvestigationRepository, acct_repo: AccountRepository
    ) -> None:
        result = await inv_repo.create_investigation(TargetInput(name="Test"))
        cp = CandidateProfile(platform="github", username="testuser", url="https://github.com/testuser")
        sr = SignalResult(signal_name="bio", score=0.7, weight=0.2, evidence="match")
        vr = VerificationResult(candidate=cp, signals=[sr], confidence=0.7, threshold_label="likely")
        await acct_repo.save_accounts(result["id"], [vr])

        accounts = await acct_repo.get_accounts(result["id"])
        assert len(accounts) == 1
        assert accounts[0].candidate.platform == "github"
        assert accounts[0].confidence == 0.7

    @pytest.mark.asyncio
    async def test_account_exists(
        self, db: Database, inv_repo: InvestigationRepository, acct_repo: AccountRepository
    ) -> None:
        result = await inv_repo.create_investigation(TargetInput(name="Test"))
        cp = CandidateProfile(platform="twitter", username="user1", url="https://x.com/user1")
        vr = VerificationResult(candidate=cp, signals=[], confidence=0.5, threshold_label="possible")
        await acct_repo.save_accounts(result["id"], [vr])

        assert await acct_repo.account_exists(result["id"], "twitter", "user1")
        assert not await acct_repo.account_exists(result["id"], "twitter", "other")
        assert not await acct_repo.account_exists(result["id"], "github", "user1")


class TestContentRepository:
    @pytest.mark.asyncio
    async def test_save_and_get_content(
        self, db: Database, content_repo: ContentRepository
    ) -> None:
        # Insert a fake account directly
        await db.conn.execute(
            "INSERT INTO targets (id, name, created_at) VALUES ('t1', 'Test', '2024-01-01T00:00:00')"
        )
        await db.conn.execute(
            "INSERT INTO accounts (id, target_id, platform, username, url) VALUES ('a1', 't1', 'twitter', 'u', 'https://x.com/u')"
        )
        await db.conn.commit()

        items = [
            ContentItem(id="c1", platform="twitter", text="Hello world"),
            ContentItem(id="c2", platform="twitter", text="Second post", metadata={"likes": 10}),
        ]
        await content_repo.save_content("a1", items)

        content = await content_repo.get_content("a1")
        assert len(content) == 2
        texts = {c.text for c in content}
        assert "Hello world" in texts
        assert "Second post" in texts

    @pytest.mark.asyncio
    async def test_content_metadata_roundtrip(
        self, db: Database, content_repo: ContentRepository
    ) -> None:
        await db.conn.execute(
            "INSERT INTO targets (id, name, created_at) VALUES ('t2', 'Test', '2024-01-01T00:00:00')"
        )
        await db.conn.execute(
            "INSERT INTO accounts (id, target_id, platform, username, url) VALUES ('a2', 't2', 'reddit', 'u', 'https://reddit.com/u/u')"
        )
        await db.conn.commit()

        items = [ContentItem(id="c3", platform="reddit", text="Post", metadata={"score": 42})]
        await content_repo.save_content("a2", items)

        content = await content_repo.get_content("a2")
        assert len(content) == 1
        assert content[0].metadata == {"score": 42}

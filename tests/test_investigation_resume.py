"""Tests for investigation persistence and resume."""

import hashlib

import pytest

from argus.models.target import TargetInput
from argus.storage.database import Database
from argus.storage.repository import InvestigationRepository


@pytest.fixture
async def db():
    d = Database()
    await d.initialize()
    yield d
    await d.close()


@pytest.fixture
def repo(db):
    return InvestigationRepository(db)


@pytest.fixture
def target_input():
    return TargetInput(
        name="John Doe",
        location="NYC",
        seed_urls=["https://github.com/johndoe"],
    )


class TestGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_new_investigation(self, repo, target_input):
        inv, is_new = await repo.get_or_create_investigation(target_input)
        assert is_new is True
        assert inv["id"] is not None
        assert inv["target_id"] is not None

    @pytest.mark.asyncio
    async def test_returns_existing_on_same_input(self, repo, target_input):
        inv1, is_new1 = await repo.get_or_create_investigation(target_input)
        inv2, is_new2 = await repo.get_or_create_investigation(target_input)
        assert is_new1 is True
        assert is_new2 is False
        assert inv1["id"] == inv2["id"]

    @pytest.mark.asyncio
    async def test_deterministic_id(self, repo, target_input):
        inv1, _ = await repo.get_or_create_investigation(target_input)
        # Same input should produce same investigation ID
        expected_hash = hashlib.sha256(
            f"{target_input.name}|{target_input.location}|{sorted(target_input.seed_urls)}".encode()
        ).hexdigest()[:16]
        assert expected_hash in inv1["id"]

    @pytest.mark.asyncio
    async def test_different_input_different_id(self, repo):
        t1 = TargetInput(name="John Doe", location="NYC")
        t2 = TargetInput(name="Jane Doe", location="LA")
        inv1, _ = await repo.get_or_create_investigation(t1)
        inv2, _ = await repo.get_or_create_investigation(t2)
        assert inv1["id"] != inv2["id"]


class TestPlatformProgress:
    @pytest.mark.asyncio
    async def test_no_platforms_initially(self, repo, target_input):
        inv, _ = await repo.get_or_create_investigation(target_input)
        done = await repo.get_scraped_platforms(inv["id"])
        assert done == set()

    @pytest.mark.asyncio
    async def test_mark_platform_complete(self, repo, target_input):
        inv, _ = await repo.get_or_create_investigation(target_input)
        await repo.mark_platform_complete(inv["id"], "github")
        done = await repo.get_scraped_platforms(inv["id"])
        assert "github" in done

    @pytest.mark.asyncio
    async def test_mark_multiple_platforms(self, repo, target_input):
        inv, _ = await repo.get_or_create_investigation(target_input)
        await repo.mark_platform_complete(inv["id"], "github")
        await repo.mark_platform_complete(inv["id"], "reddit")
        done = await repo.get_scraped_platforms(inv["id"])
        assert done == {"github", "reddit"}

    @pytest.mark.asyncio
    async def test_mark_same_platform_idempotent(self, repo, target_input):
        inv, _ = await repo.get_or_create_investigation(target_input)
        await repo.mark_platform_complete(inv["id"], "github")
        await repo.mark_platform_complete(inv["id"], "github")
        done = await repo.get_scraped_platforms(inv["id"])
        assert done == {"github"}


class TestAutoPurge:
    @pytest.mark.asyncio
    async def test_purge_old_investigations(self, repo, target_input):
        inv, _ = await repo.get_or_create_investigation(target_input)
        # Set created_at to 100 days ago
        conn = repo._db.conn
        await conn.execute(
            "UPDATE investigations SET created_at = datetime('now', '-100 days') WHERE id = ?",
            (inv["id"],),
        )
        await conn.commit()

        purged = await repo.purge_old_investigations(max_age_days=90)
        assert purged >= 1

        result = await repo.get_investigation(inv["id"])
        assert result is None

    @pytest.mark.asyncio
    async def test_purge_keeps_recent(self, repo, target_input):
        inv, _ = await repo.get_or_create_investigation(target_input)
        purged = await repo.purge_old_investigations(max_age_days=90)
        assert purged == 0

        result = await repo.get_investigation(inv["id"])
        assert result is not None

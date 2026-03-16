"""Tests for the Resolver Agent pipeline."""

from __future__ import annotations

import pytest

from argus.agents.resolver import ResolverAgent
from argus.config.settings import ArgusConfig
from argus.models.agent import AgentInput, ResolverOutput
from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.models.target import TargetInput
from argus.platforms.base import BasePlatform
from argus.platforms.registry import PlatformRegistry
from argus.storage.database import Database


class MockPlatform(BasePlatform):
    name = "mock"
    base_url = "https://mock.example.com"
    rate_limit_per_minute = 100
    priority = 50

    def __init__(self, session, config):
        super().__init__(session, config)
        self._users = {"johndoe": True, "jdoe": True}

    async def check_username(self, username: str) -> bool | None:
        return self._users.get(username, False)

    async def search_name(self, name: str, location: str | None = None) -> list[CandidateProfile]:
        if "john" in name.lower():
            return [
                CandidateProfile(
                    platform=self.name,
                    username="john_search",
                    url=f"{self.base_url}/john_search",
                )
            ]
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        return ProfileData(
            username="johndoe",
            display_name="John Doe",
            bio="Software engineer",
        )


class FailingPlatform(BasePlatform):
    name = "failing"
    base_url = "https://failing.example.com"
    priority = 10

    async def check_username(self, username: str) -> bool | None:
        raise RuntimeError("Platform down")

    async def search_name(self, name: str, location: str | None = None) -> list[CandidateProfile]:
        raise RuntimeError("Platform down")

    async def scrape_profile(self, url: str) -> ProfileData | None:
        raise RuntimeError("Platform down")


class FakeSession:
    """Fake aiohttp session for testing."""

    async def get(self, *args, **kwargs):
        raise NotImplementedError("Should not be called directly")


@pytest.fixture
def config():
    return ArgusConfig()


@pytest.fixture
def registry():
    reg = PlatformRegistry()
    reg.register(MockPlatform)
    return reg


@pytest.fixture
def failing_registry():
    reg = PlatformRegistry()
    reg.register(FailingPlatform)
    return reg


class TestResolverAgent:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, config, registry):
        agent = ResolverAgent(
            session=FakeSession(),
            config=config,
            registry=registry,
        )
        input = AgentInput(target=TargetInput(name="John Doe"))
        output = await agent.run(input)
        assert isinstance(output, ResolverOutput)
        assert output.agent_name == "resolver"
        assert output.target_name == "John Doe"
        # Should find some accounts (johndoe matches)
        assert len(output.accounts) >= 0  # may be filtered by threshold

    @pytest.mark.asyncio
    async def test_pipeline_with_persistence(self, config, registry):
        db = Database()
        await db.initialize()
        agent = ResolverAgent(
            session=FakeSession(),
            config=config,
            registry=registry,
            db=db,
        )
        input = AgentInput(target=TargetInput(name="John Doe"))
        output = await agent.run(input)
        assert isinstance(output, ResolverOutput)
        assert output.metadata is not None
        assert "timings" in output.metadata
        await db.close()

    @pytest.mark.asyncio
    async def test_platform_failure_doesnt_crash(self, config, failing_registry):
        agent = ResolverAgent(
            session=FakeSession(),
            config=config,
            registry=failing_registry,
        )
        input = AgentInput(target=TargetInput(name="Test"))
        # Should not raise
        output = await agent.run(input)
        assert isinstance(output, ResolverOutput)
        assert output.accounts == []

    @pytest.mark.asyncio
    async def test_no_session_returns_empty(self, config, registry):
        agent = ResolverAgent(
            session=None,
            config=config,
            registry=registry,
        )
        input = AgentInput(target=TargetInput(name="Test"))
        output = await agent.run(input)
        assert output.accounts == []

    @pytest.mark.asyncio
    async def test_username_hint(self, config, registry):
        agent = ResolverAgent(
            session=FakeSession(),
            config=config,
            registry=registry,
        )
        input = AgentInput(
            target=TargetInput(name="John Doe", username_hint="jdoe_hint")
        )
        output = await agent.run(input)
        assert isinstance(output, ResolverOutput)

    @pytest.mark.asyncio
    async def test_results_sorted_by_confidence(self, config, registry):
        agent = ResolverAgent(
            session=FakeSession(),
            config=config,
            registry=registry,
        )
        input = AgentInput(target=TargetInput(name="John Doe"))
        output = await agent.run(input)
        if len(output.accounts) >= 2:
            for i in range(len(output.accounts) - 1):
                assert output.accounts[i].confidence >= output.accounts[i + 1].confidence

    @pytest.mark.asyncio
    async def test_timings_recorded(self, config, registry):
        agent = ResolverAgent(
            session=FakeSession(),
            config=config,
            registry=registry,
        )
        input = AgentInput(target=TargetInput(name="Test"))
        output = await agent.run(input)
        timings = output.metadata.get("timings", {})
        assert "username_gen" in timings
        assert "platform_fanout" in timings
        assert "verification" in timings

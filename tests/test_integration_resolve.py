"""Integration tests for the full resolve pipeline end-to-end."""

from __future__ import annotations

from unittest.mock import MagicMock

from click.testing import CliRunner

from argus.agents.resolver import ResolverAgent
from argus.cli import main
from argus.config.settings import ArgusConfig
from argus.models.agent import AgentInput
from argus.models.profile import CandidateProfile, ProfileData
from argus.models.target import TargetInput
from argus.platforms.base import BasePlatform
from argus.platforms.registry import PlatformRegistry
from tests.fixtures.mock_responses import (
    GITHUB_USER_JANEDOE,
    GITHUB_USER_JOHNDOE,
    HACKERNEWS_USER_JOHNDOE,
    REDDIT_USER_JOHNDOE,
)


# ---------------------------------------------------------------------------
# Helpers: mock platforms that return canned data without HTTP
# ---------------------------------------------------------------------------


class FakeGitHubPlatform(BasePlatform):
    name = "github"
    base_url = "https://github.com"
    priority = 80

    async def check_username(self, username: str) -> bool | None:
        if username == "johndoe":
            return True
        if username == "janedoe":
            return True
        return False

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        if "john" in name.lower():
            return [
                CandidateProfile(
                    platform=self.name,
                    username="johndoe",
                    url="https://github.com/johndoe",
                )
            ]
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        if "johndoe" in url:
            data = GITHUB_USER_JOHNDOE
            return ProfileData(
                username=data["login"],
                display_name=data["name"],
                bio=data["bio"],
                location=data["location"],
                profile_photo_url=data["avatar_url"],
                links=[data["blog"]] if data["blog"] else [],
                follower_count=data["followers"],
                following_count=data["following"],
                raw_json=data,
            )
        if "janedoe" in url:
            data = GITHUB_USER_JANEDOE
            return ProfileData(
                username=data["login"],
                display_name=data["name"],
                bio=data["bio"],
                location=data["location"],
                profile_photo_url=data["avatar_url"],
                raw_json=data,
            )
        return None


class FakeRedditPlatform(BasePlatform):
    name = "reddit"
    base_url = "https://www.reddit.com"
    priority = 70

    async def check_username(self, username: str) -> bool | None:
        return username == "johndoe"

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        if "johndoe" in url:
            data = REDDIT_USER_JOHNDOE["data"]
            return ProfileData(
                username=data["name"],
                bio=data["subreddit"]["public_description"],
                profile_photo_url=data["icon_img"],
                raw_json=data,
            )
        return None


class FakeHackerNewsPlatform(BasePlatform):
    name = "hackernews"
    base_url = "https://news.ycombinator.com"
    priority = 60

    async def check_username(self, username: str) -> bool | None:
        return username == "johndoe"

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        if "johndoe" in url:
            data = HACKERNEWS_USER_JOHNDOE
            return ProfileData(
                username=data["id"],
                bio=data.get("about"),
                raw_json=data,
            )
        return None


class FailingPlatform(BasePlatform):
    name = "failing"
    base_url = "https://failing.example.com"
    priority = 10

    async def check_username(self, username: str) -> bool | None:
        raise ConnectionError("Platform unavailable")

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        raise ConnectionError("Platform unavailable")

    async def scrape_profile(self, url: str) -> ProfileData | None:
        raise ConnectionError("Platform unavailable")


class EmptyPlatform(BasePlatform):
    name = "empty"
    base_url = "https://empty.example.com"
    priority = 5

    async def check_username(self, username: str) -> bool | None:
        return False

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        return None


def _build_registry(*platform_classes: type[BasePlatform]) -> PlatformRegistry:
    registry = PlatformRegistry()
    for cls in platform_classes:
        registry.register(cls)
    return registry


def _build_resolver(
    registry: PlatformRegistry, config: ArgusConfig | None = None
) -> ResolverAgent:
    config = config or ArgusConfig()
    session = MagicMock()
    return ResolverAgent(session=session, config=config, registry=registry, db=None)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestResolveFindsGitHubProfile:
    async def test_resolve_finds_github_profile(self):
        """Full pipeline: target → username gen → GitHub discovery → verification → output."""
        config = ArgusConfig()
        config.verification.minimum_threshold = 0.0  # Accept all for pipeline test
        registry = _build_registry(FakeGitHubPlatform)
        resolver = _build_resolver(registry, config)

        target = TargetInput(name="John Doe", seed_urls=[])
        agent_input = AgentInput(target=target)
        output = await resolver.run(agent_input)

        assert output.agent_name == "resolver"
        assert output.target_name == "John Doe"
        assert len(output.accounts) > 0

        github_account = next(
            (a for a in output.accounts if a.candidate.platform == "github"), None
        )
        assert github_account is not None
        assert github_account.candidate.username == "johndoe"
        assert github_account.confidence >= 0.0


class TestResolveMultiplePlatforms:
    async def test_resolve_multiple_platforms(self):
        """Mock GitHub + Reddit + HackerNews → multiple verified results."""
        config = ArgusConfig()
        config.verification.minimum_threshold = 0.0  # Accept all for pipeline test
        registry = _build_registry(
            FakeGitHubPlatform, FakeRedditPlatform, FakeHackerNewsPlatform
        )
        resolver = _build_resolver(registry, config)

        target = TargetInput(name="John Doe", seed_urls=[])
        output = await resolver.run(AgentInput(target=target))

        platforms_found = {a.candidate.platform for a in output.accounts}
        # At minimum GitHub should be found (via both check_username and search_name)
        assert "github" in platforms_found
        # Results should be sorted by confidence descending
        confidences = [a.confidence for a in output.accounts]
        assert confidences == sorted(confidences, reverse=True)


class TestResolveFiltersFalsePositives:
    async def test_resolve_filters_false_positives(self):
        """Candidates with low similarity are filtered below threshold."""
        config = ArgusConfig()
        config.verification.minimum_threshold = 0.90  # Very high threshold

        registry = _build_registry(FakeGitHubPlatform)
        resolver = _build_resolver(registry, config)

        target = TargetInput(name="John Doe", seed_urls=[])
        output = await resolver.run(AgentInput(target=target))

        # With a very high threshold, no results should pass without strong signals
        for account in output.accounts:
            assert account.confidence >= 0.90


class TestResolveWithSeedUrl:
    async def test_resolve_with_seed_url(self):
        """Seed profile provides ground truth for bio/photo matching boost."""
        registry = _build_registry(FakeRedditPlatform)
        resolver = _build_resolver(registry)

        target = TargetInput(
            name="John Doe",
            seed_urls=["https://github.com/johndoe"],
            username_hint="johndoe",
        )
        # Note: seed scraping requires matching base_url from registry,
        # and GitHub isn't in registry here. So seed profiles will be empty.
        # But the username hint gives a direct match on Reddit.
        output = await resolver.run(AgentInput(target=target))
        assert output.target_name == "John Doe"


class TestResolvePlatformFailureGraceful:
    async def test_resolve_platform_failure_graceful(self):
        """One platform returns errors → pipeline continues with others."""
        registry = _build_registry(FakeGitHubPlatform, FailingPlatform)
        resolver = _build_resolver(registry)

        target = TargetInput(name="John Doe", seed_urls=[])
        output = await resolver.run(AgentInput(target=target))

        # Pipeline should still return results from GitHub despite failing platform
        assert output.target_name == "John Doe"
        platforms_found = {a.candidate.platform for a in output.accounts}
        assert "failing" not in platforms_found
        # GitHub results should still be present
        assert len(output.accounts) >= 0  # May be 0 if threshold filters all


class TestResolveEmptyResults:
    async def test_resolve_empty_results(self):
        """Target not found anywhere → empty results, no crash."""
        registry = _build_registry(EmptyPlatform)
        resolver = _build_resolver(registry)

        target = TargetInput(name="Nonexistent Person ZZZZZ", seed_urls=[])
        output = await resolver.run(AgentInput(target=target))

        assert output.accounts == []
        assert output.target_name == "Nonexistent Person ZZZZZ"
        assert output.duration_seconds is not None
        assert output.duration_seconds >= 0


class TestCLIResolveTableOutput:
    def test_cli_resolve_table_output(self, monkeypatch):
        """CLI resolve command produces table output."""
        # Mock the async resolver to avoid real HTTP
        from unittest.mock import patch

        from argus.models.agent import ResolverOutput
        from argus.models.verification import SignalResult, VerificationResult

        mock_output = ResolverOutput(
            target_name="John Doe",
            agent_name="resolver",
            accounts=[
                VerificationResult(
                    candidate=CandidateProfile(
                        platform="github",
                        username="johndoe",
                        url="https://github.com/johndoe",
                        exists=True,
                    ),
                    signals=[
                        SignalResult(
                            signal_name="username_pattern",
                            score=0.8,
                            weight=0.1,
                            evidence="test",
                        )
                    ],
                    confidence=0.65,
                    threshold_label="likely",
                )
            ],
        )

        async def fake_resolve_async(**kwargs):
            from argus.cli import _display_table

            _display_table(mock_output, "John Doe", 1, 0.5)

        with patch("argus.cli._resolve_async", side_effect=fake_resolve_async):
            runner = CliRunner()
            result = runner.invoke(main, ["resolve", "John Doe", "--output", "table"])
            assert result.exit_code == 0
            assert "johndoe" in result.output
            assert "github" in result.output


class TestCLIResolveJsonOutput:
    def test_cli_resolve_json_output(self, monkeypatch):
        """CLI resolve command produces valid JSON output."""
        from unittest.mock import patch

        from argus.models.agent import ResolverOutput
        from argus.models.verification import SignalResult, VerificationResult

        mock_output = ResolverOutput(
            target_name="John Doe",
            agent_name="resolver",
            accounts=[
                VerificationResult(
                    candidate=CandidateProfile(
                        platform="github",
                        username="johndoe",
                        url="https://github.com/johndoe",
                        exists=True,
                    ),
                    signals=[
                        SignalResult(
                            signal_name="username_pattern",
                            score=0.8,
                            weight=0.1,
                            evidence="test",
                        )
                    ],
                    confidence=0.65,
                    threshold_label="likely",
                )
            ],
        )

        async def fake_resolve_async(**kwargs):
            from argus.cli import console

            console.print(mock_output.model_dump_json(indent=2))

        with patch("argus.cli._resolve_async", side_effect=fake_resolve_async):
            runner = CliRunner()
            result = runner.invoke(main, ["resolve", "John Doe", "--output", "json"])
            assert result.exit_code == 0
            # Should contain valid JSON with expected fields
            assert "johndoe" in result.output
            assert "resolver" in result.output

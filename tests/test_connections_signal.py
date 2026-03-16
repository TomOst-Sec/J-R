"""Tests for mutual connections verification signal."""

import pytest

from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.connections_signal import MutualConnectionsSignal


def _candidate(platform: str, username: str, bio: str = "", links: list[str] | None = None):
    return CandidateProfile(
        platform=platform,
        username=username,
        url=f"https://{platform}.com/{username}",
        exists=True,
        scraped_data=ProfileData(
            username=username,
            bio=bio,
            links=links or [],
        ),
    )


class TestMutualConnectionsSignal:
    @pytest.mark.asyncio
    async def test_cross_platform_link_high_score(self):
        """GitHub profile linking to twitter/johndoe should get high score."""
        signal = MutualConnectionsSignal()
        gh = _candidate("github", "johndoe", links=["https://twitter.com/johndoe"])
        tw = _candidate("twitter", "johndoe")

        result = await signal.compute(gh, [], [gh, tw])
        assert result.score >= 0.8
        assert "cross-platform" in result.evidence.lower() or "Cross-platform" in result.evidence

    @pytest.mark.asyncio
    async def test_bio_username_mention(self):
        """Bio mentioning another platform's username."""
        signal = MutualConnectionsSignal()
        gh = _candidate("github", "johndoe", bio="Also on Reddit as johndoe")
        reddit = _candidate("reddit", "johndoe")

        result = await signal.compute(gh, [], [gh, reddit])
        assert result.score >= 0.5
        assert "mention" in result.evidence.lower() or "username" in result.evidence.lower()

    @pytest.mark.asyncio
    async def test_shared_external_link(self):
        """Two platforms sharing the same personal website."""
        signal = MutualConnectionsSignal()
        gh = _candidate("github", "johndoe", links=["https://johndoe.dev"])
        tw = _candidate("twitter", "johndoe", links=["https://johndoe.dev"])

        result = await signal.compute(gh, [], [gh, tw])
        assert result.score >= 0.8
        assert "shared" in result.evidence.lower() or "external" in result.evidence.lower()

    @pytest.mark.asyncio
    async def test_no_connections(self):
        """No connections between isolated profiles."""
        signal = MutualConnectionsSignal()
        gh = _candidate("github", "alice")
        tw = _candidate("twitter", "bob")

        result = await signal.compute(gh, [], [gh, tw])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_no_scraped_data(self):
        """Candidate without scraped data returns 0."""
        signal = MutualConnectionsSignal()
        c = CandidateProfile(
            platform="github", username="test", url="https://github.com/test"
        )

        result = await signal.compute(c, [], [c])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_signal_name_and_weight(self):
        signal = MutualConnectionsSignal()
        assert signal.name == "mutual_connections"
        assert signal.default_weight == 0.10

    @pytest.mark.asyncio
    async def test_link_in_bio_text(self):
        """URL embedded in bio text."""
        signal = MutualConnectionsSignal()
        gh = _candidate(
            "github", "johndoe",
            bio="Check my work at https://twitter.com/johndoe"
        )
        tw = _candidate("twitter", "johndoe")

        result = await signal.compute(gh, [], [gh, tw])
        assert result.score > 0

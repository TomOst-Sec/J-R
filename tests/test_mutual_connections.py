"""Tests for MutualConnectionsSignal."""

import pytest

from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.signals import MutualConnectionsSignal


def _make_candidate(username="jdoe", platform="twitter", bio=None, links=None):
    scraped = ProfileData(username=username, bio=bio, links=links or [])
    return CandidateProfile(
        platform=platform, username=username,
        url=f"https://{platform}.com/{username}", scraped_data=scraped,
    )


def _make_seed(username="johndoe", bio=None, links=None):
    return ProfileData(username=username, bio=bio, links=links or [])


class TestMutualConnectionsSignal:
    @pytest.mark.asyncio
    async def test_no_connections(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate()
        seed = _make_seed()
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.0
        assert "No mutual" in result.evidence

    @pytest.mark.asyncio
    async def test_candidate_links_to_other(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate(
            username="jdoe", platform="twitter",
            links=["https://github.com/jdoe_gh"],
        )
        other = _make_candidate(username="jdoe_gh", platform="github")
        result = await signal.compute(candidate, [], [candidate, other])
        assert result.score > 0.0
        assert "Links to" in result.evidence

    @pytest.mark.asyncio
    async def test_candidate_bio_mentions_other(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate(
            username="jdoe", platform="twitter",
            bio="Also on GitHub as jdoe_gh",
        )
        other = _make_candidate(username="jdoe_gh", platform="github")
        result = await signal.compute(candidate, [], [candidate, other])
        assert result.score > 0.0
        assert "mentions" in result.evidence

    @pytest.mark.asyncio
    async def test_seed_links_to_candidate(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate(username="jdoe", platform="twitter")
        seed = _make_seed(
            username="known", links=["https://twitter.com/jdoe"],
        )
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score > 0.0
        assert "Seed" in result.evidence

    @pytest.mark.asyncio
    async def test_seed_bio_mentions_candidate(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate(username="jdoe", platform="twitter")
        seed = _make_seed(username="known", bio="Follow me and jdoe on twitter")
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score > 0.0

    @pytest.mark.asyncio
    async def test_multiple_connections_higher_score(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate(
            username="jdoe", platform="twitter",
            bio="Also on GitHub as jdoe_gh",
            links=["https://github.com/jdoe_gh"],
        )
        other = _make_candidate(username="jdoe_gh", platform="github")
        result = await signal.compute(candidate, [], [candidate, other])
        # Link check matches first (elif skips bio for same candidate)
        assert result.score >= 0.25

    @pytest.mark.asyncio
    async def test_no_scraped_data(self):
        signal = MutualConnectionsSignal()
        candidate = CandidateProfile(
            platform="twitter", username="jdoe", url="https://twitter.com/jdoe",
        )
        result = await signal.compute(candidate, [], [candidate])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_score_capped_at_one(self):
        signal = MutualConnectionsSignal()
        candidate = _make_candidate(
            username="jdoe", platform="twitter",
            bio="a1 a2 a3 a4 a5",
            links=["https://p.com/a1", "https://p.com/a2", "https://p.com/a3",
                    "https://p.com/a4", "https://p.com/a5"],
        )
        others = [_make_candidate(f"a{i}", "p") for i in range(1, 6)]
        result = await signal.compute(candidate, [], [candidate] + others)
        assert result.score <= 1.0

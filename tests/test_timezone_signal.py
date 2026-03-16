"""Tests for the timezone correlation verification signal."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.timezone_signal import TimezoneCorrelationSignal


def _make_candidate(
    username: str,
    timestamps: list[str],
) -> CandidateProfile:
    """Create a candidate with timestamps in raw_json."""
    scraped = ProfileData(
        username=username,
        raw_json={"content_timestamps": timestamps},
    )
    return CandidateProfile(
        platform="github",
        username=username,
        url=f"https://github.com/{username}",
        scraped_data=scraped,
    )


def _make_seed(timestamps: list[str]) -> ProfileData:
    return ProfileData(
        username="seed",
        raw_json={"content_timestamps": timestamps},
    )


def _timestamps_at_hours(hours: list[int], count_per_hour: int = 5) -> list[str]:
    """Generate ISO timestamp strings for given hours."""
    result = []
    for h in hours:
        for d in range(count_per_hour):
            result.append(f"2024-01-{10+d:02d}T{h:02d}:30:00+00:00")
    return result


class TestTimezoneSignal:
    @pytest.mark.asyncio
    async def test_same_timezone(self) -> None:
        """Candidates with same peak hours should score high."""
        signal = TimezoneCorrelationSignal()
        candidate = _make_candidate("user1", _timestamps_at_hours([9, 10, 14, 15], 4))
        seed = _make_seed(_timestamps_at_hours([9, 10, 14, 15], 4))
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score >= 0.8

    @pytest.mark.asyncio
    async def test_different_timezone(self) -> None:
        """Candidates with very different peak hours should score low."""
        signal = TimezoneCorrelationSignal()
        candidate = _make_candidate("user1", _timestamps_at_hours([9, 10, 11], 5))
        seed = _make_seed(_timestamps_at_hours([21, 22, 23], 5))
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score <= 0.3

    @pytest.mark.asyncio
    async def test_close_timezone(self) -> None:
        """Candidates offset by 2 hours should score medium."""
        signal = TimezoneCorrelationSignal()
        candidate = _make_candidate("user1", _timestamps_at_hours([8, 9, 10], 5))
        seed = _make_seed(_timestamps_at_hours([12, 13, 14], 5))
        result = await signal.compute(candidate, [seed], [candidate])
        assert 0.3 <= result.score <= 0.7

    @pytest.mark.asyncio
    async def test_insufficient_timestamps(self) -> None:
        """Should return neutral score (0.5) with too few timestamps."""
        signal = TimezoneCorrelationSignal()
        candidate = _make_candidate("user1", ["2024-01-10T09:00:00+00:00"] * 5)
        seed = _make_seed(_timestamps_at_hours([9, 10], 5))
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.5
        assert "Insufficient" in result.evidence

    @pytest.mark.asyncio
    async def test_no_timestamps(self) -> None:
        """Candidate with no timestamps returns neutral."""
        signal = TimezoneCorrelationSignal()
        scraped = ProfileData(username="empty")
        candidate = CandidateProfile(
            platform="github",
            username="empty",
            url="https://github.com/empty",
            scraped_data=scraped,
        )
        result = await signal.compute(candidate, [], [candidate])
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_cross_candidate_comparison(self) -> None:
        """When no seed timestamps, compare across candidates."""
        signal = TimezoneCorrelationSignal()
        c1 = _make_candidate("user1", _timestamps_at_hours([9, 10, 14], 5))
        c2 = _make_candidate("user2", _timestamps_at_hours([9, 10, 14], 5))
        seed = _make_seed([])  # No seed timestamps
        result = await signal.compute(c1, [seed], [c1, c2])
        assert result.score >= 0.8

    @pytest.mark.asyncio
    async def test_signal_name_and_weight(self) -> None:
        signal = TimezoneCorrelationSignal()
        assert signal.name == "timezone_correlation"
        assert signal.default_weight == 0.15

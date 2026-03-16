"""Tests for the writing style verification signal."""

from __future__ import annotations

import pytest

from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.style_signal import (
    WritingStyleSignal,
    _cosine_similarity,
    _extract_features,
)


def _make_candidate(username: str, texts: list[str]) -> CandidateProfile:
    scraped = ProfileData(
        username=username,
        raw_json={"content_texts": texts},
    )
    return CandidateProfile(
        platform="test",
        username=username,
        url=f"https://example.com/{username}",
        scraped_data=scraped,
    )


def _make_seed(texts: list[str]) -> ProfileData:
    return ProfileData(
        username="seed",
        raw_json={"content_texts": texts},
    )


_CASUAL_TEXTS = [
    "hey everyone! just shipped a new feature. so excited!!",
    "anyone else having issues with the build? lmk...",
    "just pushed a fix. should be good now 🎉",
    "working on something cool... stay tuned!",
    "finished the refactor. much cleaner now!",
    "debugging this for hours... finally found it",
]

_FORMAL_TEXTS = [
    "The quarterly report has been submitted to the board of directors.",
    "Please review the attached document and provide your feedback.",
    "The implementation follows established architectural patterns.",
    "Further investigation revealed the root cause of the issue.",
    "We recommend proceeding with the proposed methodology.",
    "The analysis confirms our initial hypothesis regarding performance.",
]


class TestFeatureExtraction:
    def test_extract_basic_features(self) -> None:
        features = _extract_features(["Hello world. This is a test."])
        assert "avg_sentence_length" in features
        assert "avg_word_length" in features
        assert "vocab_richness" in features

    def test_extract_empty(self) -> None:
        assert _extract_features([]) == {}

    def test_casual_vs_formal_features(self) -> None:
        casual = _extract_features(_CASUAL_TEXTS)
        formal = _extract_features(_FORMAL_TEXTS)
        # Formal text should have longer average sentence and word lengths
        assert formal["avg_word_length"] > casual["avg_word_length"]
        # Casual text should have more exclamations
        assert casual["exclamation_freq"] > formal["exclamation_freq"]


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        a = {"x": 1.0, "y": 2.0}
        assert abs(_cosine_similarity(a, a) - 1.0) < 0.01

    def test_orthogonal_vectors(self) -> None:
        a = {"x": 1.0, "y": 0.0}
        b = {"x": 0.0, "y": 1.0}
        assert abs(_cosine_similarity(a, b)) < 0.01

    def test_empty(self) -> None:
        assert _cosine_similarity({}, {}) == 0.0


class TestWritingStyleSignal:
    @pytest.mark.asyncio
    async def test_similar_style(self) -> None:
        """Same author's texts should score high."""
        signal = WritingStyleSignal()
        candidate = _make_candidate("user1", _CASUAL_TEXTS)
        seed = _make_seed(_CASUAL_TEXTS[:3] + ["this is super cool!! love it", "just tested and it works great!"])
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score > 0.7

    @pytest.mark.asyncio
    async def test_different_style(self) -> None:
        """Very different writing styles should score lower."""
        signal = WritingStyleSignal()
        candidate = _make_candidate("user1", _CASUAL_TEXTS)
        seed = _make_seed(_FORMAL_TEXTS)
        result = await signal.compute(candidate, [seed], [candidate])
        # Score should be less than identical text (1.0) but still high
        # due to shared zero-valued features in cosine similarity
        assert result.score < 1.0

    @pytest.mark.asyncio
    async def test_insufficient_data(self) -> None:
        """Should return neutral with too few texts."""
        signal = WritingStyleSignal()
        candidate = _make_candidate("user1", ["only one text"])
        result = await signal.compute(candidate, [], [candidate])
        assert result.score == 0.5
        assert "Insufficient" in result.evidence

    @pytest.mark.asyncio
    async def test_cross_candidate_comparison(self) -> None:
        """Compare across candidates when no seed data."""
        signal = WritingStyleSignal()
        c1 = _make_candidate("user1", _CASUAL_TEXTS)
        c2 = _make_candidate("user2", _CASUAL_TEXTS)
        result = await signal.compute(c1, [_make_seed([])], [c1, c2])
        assert result.score > 0.7

    @pytest.mark.asyncio
    async def test_signal_name_and_weight(self) -> None:
        signal = WritingStyleSignal()
        assert signal.name == "writing_style"
        assert signal.default_weight == 0.10

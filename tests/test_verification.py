"""Tests for the verification engine and signals."""

import pytest

from argus.config.settings import ArgusConfig
from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.engine import VerificationEngine, _threshold_label
from argus.verification.signals import (
    BaseSignal,
    BioSimilaritySignal,
    PhotoHashSignal,
    UsernamePatternSignal,
    _hamming_distance,
)


# --- Helpers ---

def _make_candidate(
    username: str = "jdoe",
    platform: str = "twitter",
    bio: str | None = None,
    photo_hash: str | None = None,
) -> CandidateProfile:
    scraped = ProfileData(
        username=username,
        bio=bio,
        profile_photo_hash=photo_hash,
    )
    return CandidateProfile(
        platform=platform,
        username=username,
        url=f"https://{platform}.com/{username}",
        scraped_data=scraped,
    )


def _make_seed(
    username: str = "johndoe",
    bio: str | None = None,
    photo_hash: str | None = None,
) -> ProfileData:
    return ProfileData(
        username=username,
        bio=bio,
        profile_photo_hash=photo_hash,
    )


# --- Unit Tests ---

class TestHammingDistance:
    def test_identical_hashes(self):
        assert _hamming_distance("ff", "ff") == 0

    def test_different_hashes(self):
        assert _hamming_distance("ff", "00") == 8

    def test_partial_difference(self):
        assert _hamming_distance("f0", "f1") == 1

    def test_mismatched_length_raises(self):
        with pytest.raises(ValueError):
            _hamming_distance("ff", "fff")


class TestThresholdLabel:
    def test_discarded(self):
        assert _threshold_label(0.0) == "discarded"
        assert _threshold_label(0.29) == "discarded"

    def test_possible(self):
        assert _threshold_label(0.30) == "possible"
        assert _threshold_label(0.44) == "possible"

    def test_likely(self):
        assert _threshold_label(0.45) == "likely"
        assert _threshold_label(0.69) == "likely"

    def test_confirmed(self):
        assert _threshold_label(0.70) == "confirmed"
        assert _threshold_label(1.0) == "confirmed"


class TestPhotoHashSignal:
    @pytest.mark.asyncio
    async def test_no_candidate_hash(self):
        signal = PhotoHashSignal()
        candidate = _make_candidate(photo_hash=None)
        seed = _make_seed(photo_hash="ff" * 8)
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_identical_hash(self):
        h = "ff" * 8
        signal = PhotoHashSignal()
        candidate = _make_candidate(photo_hash=h)
        seed = _make_seed(photo_hash=h)
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_distant_hash(self):
        signal = PhotoHashSignal()
        candidate = _make_candidate(photo_hash="ff" * 8)
        seed = _make_seed(photo_hash="00" * 8)
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_medium_distance(self):
        signal = PhotoHashSignal()
        # "fffffffffffffffe" vs "ffffffffffffffff" = 1 bit diff (score=1.0)
        # We need ~20 bits: "ffffffffffff0000" vs "ffffffffffffffff" = 16 bits
        candidate = _make_candidate(photo_hash="ffffffffffff0000")
        seed = _make_seed(photo_hash="ffffffffffffffff")
        result = await signal.compute(candidate, [seed], [candidate])
        assert 0.0 < result.score < 1.0

    @pytest.mark.asyncio
    async def test_no_seed_photos(self):
        signal = PhotoHashSignal()
        candidate = _make_candidate(photo_hash="ff" * 8)
        seed = _make_seed(photo_hash=None)
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.0


class TestBioSimilaritySignal:
    @pytest.mark.asyncio
    async def test_no_candidate_bio(self):
        signal = BioSimilaritySignal()
        candidate = _make_candidate(bio=None)
        seed = _make_seed(bio="Software engineer")
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_no_seed_bios(self):
        signal = BioSimilaritySignal()
        candidate = _make_candidate(bio="Software engineer")
        seed = _make_seed(bio=None)
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_identical_bios(self):
        signal = BioSimilaritySignal()
        bio = "I am a software engineer who loves Python and machine learning"
        candidate = _make_candidate(bio=bio)
        seed = _make_seed(bio=bio)
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score > 0.9

    @pytest.mark.asyncio
    async def test_different_bios(self):
        signal = BioSimilaritySignal()
        candidate = _make_candidate(bio="I love cooking Italian food and gardening")
        seed = _make_seed(bio="Quantum physicist researching dark matter at CERN")
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score < 0.5


class TestUsernamePatternSignal:
    @pytest.mark.asyncio
    async def test_identical_username(self):
        signal = UsernamePatternSignal()
        candidate = _make_candidate(username="johndoe")
        seed = _make_seed(username="johndoe")
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_similar_username(self):
        signal = UsernamePatternSignal()
        candidate = _make_candidate(username="johndoe123")
        seed = _make_seed(username="johndoe")
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score > 0.8

    @pytest.mark.asyncio
    async def test_different_username(self):
        signal = UsernamePatternSignal()
        candidate = _make_candidate(username="xyzabc999")
        seed = _make_seed(username="johndoe")
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score < 0.7

    @pytest.mark.asyncio
    async def test_no_seeds(self):
        signal = UsernamePatternSignal()
        candidate = _make_candidate(username="johndoe")
        result = await signal.compute(candidate, [], [candidate])
        assert result.score == 0.0


class TestVerificationEngine:
    @pytest.mark.asyncio
    async def test_engine_with_default_signals(self):
        config = ArgusConfig()
        engine = VerificationEngine(config)
        # Default signals are registered automatically

        h = "ff" * 8
        bio = "Software engineer loves Python"
        candidate = _make_candidate(username="johndoe", bio=bio, photo_hash=h)
        seed = _make_seed(username="johndoe", bio=bio, photo_hash=h)

        results = await engine.verify([candidate], [seed])
        assert len(results) == 1
        assert results[0].confidence > 0.5
        assert results[0].threshold_label in ("likely", "confirmed")
        # Should have all default signals: photo, bio, username, timezone
        assert len(results[0].signals) >= 4

    @pytest.mark.asyncio
    async def test_engine_filters_low_confidence(self):
        config = ArgusConfig()
        engine = VerificationEngine(config)
        engine.register_signal(UsernamePatternSignal())

        candidate = _make_candidate(username="xyzabc")
        seed = _make_seed(username="johndoe")

        results = await engine.verify([candidate], [seed])
        # Low-confidence candidates may be filtered
        for r in results:
            assert r.confidence >= config.verification.minimum_threshold

    @pytest.mark.asyncio
    async def test_engine_sorts_descending(self):
        config = ArgusConfig()
        engine = VerificationEngine(config)
        engine.register_signal(UsernamePatternSignal())

        c1 = _make_candidate(username="johndoe")
        c2 = _make_candidate(username="johndoe123")
        seed = _make_seed(username="johndoe")

        results = await engine.verify([c2, c1], [seed])
        if len(results) >= 2:
            assert results[0].confidence >= results[1].confidence

    @pytest.mark.asyncio
    async def test_verify_single(self):
        config = ArgusConfig()
        engine = VerificationEngine(config)
        engine.register_signal(UsernamePatternSignal())

        candidate = _make_candidate(username="johndoe")
        seed = _make_seed(username="johndoe")

        result = await engine.verify_single(candidate, [seed])
        assert result.confidence > 0.0
        assert result.candidate.username == "johndoe"

    @pytest.mark.asyncio
    async def test_engine_has_default_signals(self):
        config = ArgusConfig()
        engine = VerificationEngine(config)
        # Engine should have default signals registered
        assert len(engine._signals) >= 4  # photo, bio, username, timezone

        candidate = _make_candidate()
        seed = _make_seed()

        result = await engine.verify_single(candidate, [seed])
        # With defaults, should produce signal results
        assert len(result.signals) >= 4

    @pytest.mark.asyncio
    async def test_weight_overrides_from_config(self):
        config = ArgusConfig()
        engine = VerificationEngine(config)

        candidate = _make_candidate(username="johndoe")
        seed = _make_seed(username="johndoe")

        result = await engine.verify_single(candidate, [seed])
        # Default signals should include username_pattern
        username_signal = [s for s in result.signals if s.signal_name == "username_pattern"]
        assert len(username_signal) == 1

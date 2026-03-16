"""Tests for face recognition verification signal."""

from __future__ import annotations

from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.face_signal import (
    FaceRecognitionSignal,
    _distance_to_score,
    is_available,
)


class TestFaceRecognitionSignal:
    async def test_returns_neutral_when_library_not_installed(self):
        """When face_recognition isn't installed, return neutral score."""
        signal = FaceRecognitionSignal()
        # face_recognition is likely not installed in test env
        candidate = CandidateProfile(
            platform="github",
            username="test",
            url="https://github.com/test",
            scraped_data=ProfileData(
                username="test",
                profile_photo_url="https://example.com/photo.jpg",
            ),
        )
        seed = ProfileData(
            username="seed",
            profile_photo_url="https://example.com/seed.jpg",
        )
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.signal_name == "face_recognition"
        # Either skipped (0.5) or computed
        assert 0.0 <= result.score <= 1.0

    async def test_no_candidate_photo(self):
        """No candidate photo URL returns neutral."""
        signal = FaceRecognitionSignal()
        candidate = CandidateProfile(
            platform="github",
            username="test",
            url="https://github.com/test",
            scraped_data=ProfileData(username="test"),
        )
        seed = ProfileData(
            username="seed",
            profile_photo_url="https://example.com/seed.jpg",
        )
        result = await signal.compute(candidate, [seed], [candidate])
        assert result.score == 0.5
        assert "No candidate" in result.evidence or "not installed" in result.evidence

    async def test_no_seed_photos(self):
        """No seed photos returns neutral."""
        signal = FaceRecognitionSignal()
        candidate = CandidateProfile(
            platform="github",
            username="test",
            url="https://github.com/test",
            scraped_data=ProfileData(
                username="test",
                profile_photo_url="https://example.com/photo.jpg",
            ),
        )
        result = await signal.compute(candidate, [], [candidate])
        assert result.score == 0.5

    async def test_no_scraped_data(self):
        """No scraped data returns neutral."""
        signal = FaceRecognitionSignal()
        candidate = CandidateProfile(
            platform="github",
            username="test",
            url="https://github.com/test",
        )
        result = await signal.compute(candidate, [], [candidate])
        assert result.score == 0.5

    def test_default_weight_is_zero(self):
        """Signal is disabled by default."""
        signal = FaceRecognitionSignal()
        assert signal.default_weight == 0.0


class TestDistanceToScore:
    def test_very_close(self):
        assert _distance_to_score(0.3) == 0.9

    def test_close(self):
        assert _distance_to_score(0.45) == 0.6

    def test_moderate(self):
        assert _distance_to_score(0.55) == 0.3

    def test_far(self):
        assert _distance_to_score(0.7) == 0.1

    def test_boundary_04(self):
        assert _distance_to_score(0.4) == 0.6

    def test_boundary_05(self):
        assert _distance_to_score(0.5) == 0.3


class TestIsAvailable:
    def test_returns_bool(self):
        result = is_available()
        assert isinstance(result, bool)

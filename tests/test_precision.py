"""Precision validation tests using ground truth dataset."""

import json
from pathlib import Path

import pytest

from argus.config.settings import ArgusConfig
from argus.models.profile import CandidateProfile, ProfileData
from argus.verification.engine import VerificationEngine

FIXTURES = Path(__file__).parent / "fixtures" / "ground_truth"


def _load_fixtures(name: str) -> list[dict]:
    with (FIXTURES / name).open() as f:
        return json.load(f)


def _profile_from_dict(d: dict) -> CandidateProfile:
    return CandidateProfile(
        platform=d["platform"],
        username=d["username"],
        url=f"https://{d['platform']}.com/{d['username']}",
        exists=True,
        scraped_data=ProfileData(
            username=d["username"],
            bio=d.get("bio", ""),
            profile_photo_hash=d.get("photo_hash"),
            links=d.get("links", []),
        ),
    )


def _seed_from_dict(d: dict) -> ProfileData:
    return ProfileData(
        username=d["username"],
        bio=d.get("bio", ""),
        profile_photo_hash=d.get("photo_hash"),
        links=d.get("links", []),
    )


class TestGroundTruthDataset:
    def test_matches_file_has_entries(self):
        matches = _load_fixtures("known_matches.json")
        assert len(matches) >= 20

    def test_non_matches_file_has_entries(self):
        non_matches = _load_fixtures("known_non_matches.json")
        assert len(non_matches) >= 20


class TestPrecisionValidation:
    @pytest.mark.asyncio
    async def test_precision_at_70_threshold(self):
        """Of accounts scored ≥0.70, at least 75% should be true matches."""
        config = ArgusConfig()
        engine = VerificationEngine(config)

        matches = _load_fixtures("known_matches.json")
        non_matches = _load_fixtures("known_non_matches.json")

        true_positive = 0  # True match scored ≥0.70
        false_positive = 0  # Non-match scored ≥0.70

        # Test true matches
        for pair in matches:
            candidate = _profile_from_dict(pair["candidate"])
            seed = _seed_from_dict(pair["seed"])
            result = await engine.verify_single(candidate, [seed], [candidate])
            if result.confidence >= 0.70:
                true_positive += 1

        # Test non-matches
        for pair in non_matches:
            candidate = _profile_from_dict(pair["candidate"])
            seed = _seed_from_dict(pair["seed"])
            result = await engine.verify_single(candidate, [seed], [candidate])
            if result.confidence >= 0.70:
                false_positive += 1

        total_positive = true_positive + false_positive
        if total_positive > 0:
            precision = true_positive / total_positive
            assert precision >= 0.75, (
                f"Precision {precision:.2%} below 75% threshold. "
                f"TP={true_positive}, FP={false_positive}"
            )

    @pytest.mark.asyncio
    async def test_false_positive_rate_at_default_threshold(self):
        """False positive rate should be <30% at default threshold (0.45)."""
        config = ArgusConfig()
        engine = VerificationEngine(config)

        non_matches = _load_fixtures("known_non_matches.json")
        false_positives = 0

        for pair in non_matches:
            candidate = _profile_from_dict(pair["candidate"])
            seed = _seed_from_dict(pair["seed"])
            result = await engine.verify_single(candidate, [seed], [candidate])
            if result.confidence >= 0.45:
                false_positives += 1

        fpr = false_positives / len(non_matches) if non_matches else 0
        assert fpr < 0.30, (
            f"False positive rate {fpr:.2%} exceeds 30% threshold. "
            f"FP={false_positives}/{len(non_matches)}"
        )

    @pytest.mark.asyncio
    async def test_true_matches_get_nonzero_scores(self):
        """True matches should get some confidence score > 0."""
        config = ArgusConfig()
        engine = VerificationEngine(config)

        matches = _load_fixtures("known_matches.json")
        scored = 0

        for pair in matches:
            candidate = _profile_from_dict(pair["candidate"])
            seed = _seed_from_dict(pair["seed"])
            result = await engine.verify_single(candidate, [seed], [candidate])
            if result.confidence > 0.0:
                scored += 1

        # At least 80% of true matches should get nonzero scores
        assert scored / len(matches) >= 0.80

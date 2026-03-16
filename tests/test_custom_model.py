"""Tests for custom scoring model."""

import tempfile
from pathlib import Path

import pytest

from argus.models.verification import SignalResult
from argus.verification.custom_model import CustomScoringModel, LabeledPair


def _make_training_data() -> list[LabeledPair]:
    """Create synthetic labeled data for training."""
    data = []
    # True matches: high signal scores
    for i in range(15):
        data.append(LabeledPair(
            signal_features={"bio": 0.7 + i * 0.02, "photo": 0.8, "username": 0.6 + i * 0.01},
            is_match=True,
        ))
    # Non-matches: low signal scores
    for i in range(15):
        data.append(LabeledPair(
            signal_features={"bio": 0.1 + i * 0.01, "photo": 0.1, "username": 0.2 + i * 0.01},
            is_match=False,
        ))
    return data


class TestCustomScoringModel:
    def test_train(self):
        model = CustomScoringModel()
        data = _make_training_data()
        metrics = model.train(data)
        assert model.is_trained
        assert metrics["accuracy"] > 0.5

    def test_predict(self):
        model = CustomScoringModel()
        model.train(_make_training_data())
        signals = [
            SignalResult(signal_name="bio", score=0.9, weight=0.2, evidence="match"),
            SignalResult(signal_name="photo", score=0.8, weight=0.35, evidence="match"),
            SignalResult(signal_name="username", score=0.7, weight=0.1, evidence="match"),
        ]
        confidence = model.predict(signals)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should predict match for high scores

    def test_predict_non_match(self):
        model = CustomScoringModel()
        model.train(_make_training_data())
        signals = [
            SignalResult(signal_name="bio", score=0.1, weight=0.2, evidence="no match"),
            SignalResult(signal_name="photo", score=0.1, weight=0.35, evidence="no match"),
            SignalResult(signal_name="username", score=0.2, weight=0.1, evidence="no match"),
        ]
        confidence = model.predict(signals)
        assert confidence < 0.5  # Should predict non-match

    def test_save_and_load(self):
        model = CustomScoringModel()
        model.train(_make_training_data())

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.pkl"
            model.save(path)
            loaded = CustomScoringModel.load(path)
            assert loaded.is_trained

            # Should produce same predictions
            signals = [
                SignalResult(signal_name="bio", score=0.8, weight=0.2, evidence="test"),
                SignalResult(signal_name="photo", score=0.7, weight=0.35, evidence="test"),
                SignalResult(signal_name="username", score=0.6, weight=0.1, evidence="test"),
            ]
            assert abs(model.predict(signals) - loaded.predict(signals)) < 0.01

    def test_info_untrained(self):
        model = CustomScoringModel()
        info = model.info()
        assert info["trained"] is False

    def test_info_trained(self):
        model = CustomScoringModel()
        model.train(_make_training_data())
        info = model.info()
        assert info["trained"] is True
        assert info["n_features"] == 3
        assert "bio" in info["features"]

    def test_predict_before_train_raises(self):
        model = CustomScoringModel()
        with pytest.raises(RuntimeError):
            model.predict([])

    def test_too_few_samples_raises(self):
        model = CustomScoringModel()
        with pytest.raises(ValueError):
            model.train([LabeledPair(signal_features={"a": 0.5}, is_match=True)])

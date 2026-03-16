"""Custom scoring model — trainable logistic regression for confidence tuning."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

from argus.models.verification import SignalResult


@dataclass
class LabeledPair:
    """A labeled training example: signal features + ground truth."""

    signal_features: dict[str, float]
    is_match: bool


class CustomScoringModel:
    """Logistic regression model for confidence scoring."""

    def __init__(self) -> None:
        self._model: LogisticRegression | None = None
        self._feature_names: list[str] = []

    @property
    def is_trained(self) -> bool:
        return self._model is not None

    def train(self, labeled_data: list[LabeledPair]) -> dict[str, float]:
        """Train on labeled data. Returns training metrics."""
        if len(labeled_data) < 4:
            raise ValueError("Need at least 4 labeled pairs to train")

        # Extract feature names from first sample
        self._feature_names = sorted(labeled_data[0].signal_features.keys())

        X = np.array([
            [pair.signal_features.get(f, 0.0) for f in self._feature_names]
            for pair in labeled_data
        ])
        y = np.array([int(pair.is_match) for pair in labeled_data])

        self._model = LogisticRegression(max_iter=1000)
        self._model.fit(X, y)

        # Cross-validation
        n_splits = min(5, len(labeled_data))
        if n_splits >= 2:
            scores = cross_val_score(self._model, X, y, cv=n_splits, scoring="accuracy")
            return {"accuracy": float(np.mean(scores)), "std": float(np.std(scores))}
        return {"accuracy": float(self._model.score(X, y)), "std": 0.0}

    def predict(self, signals: list[SignalResult]) -> float:
        """Predict confidence using trained model. Returns probability 0-1."""
        if not self._model:
            raise RuntimeError("Model not trained. Call train() first.")

        features = {s.signal_name: s.score for s in signals}
        X = np.array([[features.get(f, 0.0) for f in self._feature_names]])
        proba = self._model.predict_proba(X)[0]

        # Return probability of class 1 (match)
        return float(proba[1]) if len(proba) > 1 else float(proba[0])

    def save(self, path: Path | str) -> None:
        """Save model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "model": self._model,
            "feature_names": self._feature_names,
        }
        with path.open("wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path | str) -> CustomScoringModel:
        """Load model from disk."""
        path = Path(path)
        with path.open("rb") as f:
            data = pickle.load(f)  # noqa: S301
        instance = cls()
        instance._model = data["model"]
        instance._feature_names = data["feature_names"]
        return instance

    def info(self) -> dict[str, object]:
        """Return model info."""
        if not self._model:
            return {"trained": False}
        return {
            "trained": True,
            "features": self._feature_names,
            "n_features": len(self._feature_names),
            "coefficients": {
                name: float(coef)
                for name, coef in zip(self._feature_names, self._model.coef_[0])
            },
        }

"""Verification engine for multi-signal confidence scoring."""

from argus.config.settings import ArgusConfig
from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import VerificationResult
from argus.verification.signals import (
    BaseSignal,
    BioSimilaritySignal,
    PhotoHashSignal,
    UsernamePatternSignal,
)
from argus.verification.timezone_signal import TimezoneCorrelationSignal


class VerificationEngine:
    """Computes weighted confidence scores across multiple signals."""

    def __init__(self, config: ArgusConfig) -> None:
        self._config = config
        self._signals: list[BaseSignal] = []
        self._weight_overrides = config.verification.signal_weights
        self._minimum_threshold = config.verification.minimum_threshold
        self._register_default_signals()

    def _register_default_signals(self) -> None:
        """Register all built-in verification signals."""
        self._signals.extend([
            PhotoHashSignal(),
            BioSimilaritySignal(),
            UsernamePatternSignal(),
            TimezoneCorrelationSignal(),
        ])

    def register_signal(self, signal: BaseSignal) -> None:
        self._signals.append(signal)

    async def verify(
        self,
        candidates: list[CandidateProfile],
        seed_profiles: list[ProfileData],
    ) -> list[VerificationResult]:
        results: list[VerificationResult] = []
        for candidate in candidates:
            result = await self.verify_single(candidate, seed_profiles, candidates)
            if result.confidence >= self._minimum_threshold:
                results.append(result)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    async def verify_single(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile] | None = None,
    ) -> VerificationResult:
        if all_candidates is None:
            all_candidates = [candidate]

        signals = []
        for signal in self._signals:
            result = await signal.compute(candidate, seed_profiles, all_candidates)
            weight_override = self._weight_overrides.get(signal.name)
            if weight_override is not None:
                result.weight = weight_override
            signals.append(result)

        total_weight = sum(s.weight for s in signals)
        if total_weight > 0:
            confidence = sum(s.score * s.weight for s in signals) / total_weight
        else:
            confidence = 0.0

        confidence = min(max(confidence, 0.0), 1.0)
        label = _threshold_label(confidence)

        return VerificationResult(
            candidate=candidate,
            signals=signals,
            confidence=confidence,
            threshold_label=label,
        )


def _threshold_label(confidence: float) -> str:
    if confidence < 0.30:
        return "discarded"
    elif confidence < 0.45:
        return "possible"
    elif confidence < 0.70:
        return "likely"
    else:
        return "confirmed"

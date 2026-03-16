"""Timezone correlation verification signal."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import SignalResult
from argus.verification.signals import BaseSignal

_MIN_TIMESTAMPS = 10


class TimezoneCorrelationSignal(BaseSignal):
    """Infer timezone from posting patterns and compare across platforms."""

    name = "timezone_correlation"
    default_weight = 0.15

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        # Collect timestamps from candidate's scraped content
        candidate_timestamps = self._get_timestamps(candidate)
        if len(candidate_timestamps) < _MIN_TIMESTAMPS:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence=f"Insufficient timestamps ({len(candidate_timestamps)}/{_MIN_TIMESTAMPS})",
                details={"timestamp_count": len(candidate_timestamps)},
            )

        candidate_peak = self._infer_peak_hours(candidate_timestamps)

        # Collect timestamps from seed profiles' content items
        seed_timestamps: list[datetime] = []
        for seed in seed_profiles:
            if seed.raw_json and "content_timestamps" in seed.raw_json:
                for ts_str in seed.raw_json["content_timestamps"]:
                    try:
                        seed_timestamps.append(datetime.fromisoformat(str(ts_str)))
                    except (ValueError, TypeError):
                        continue

        if len(seed_timestamps) < _MIN_TIMESTAMPS:
            # Compare across other candidates instead
            return self._compare_across_candidates(
                candidate, candidate_peak, all_candidates
            )

        seed_peak = self._infer_peak_hours(seed_timestamps)
        score, evidence = self._compare_peaks(candidate_peak, seed_peak, "seed")

        return SignalResult(
            signal_name=self.name,
            score=score,
            weight=self.default_weight,
            evidence=evidence,
            details={
                "candidate_peak_hours": candidate_peak,
                "seed_peak_hours": seed_peak,
            },
        )

    def _compare_across_candidates(
        self,
        candidate: CandidateProfile,
        candidate_peak: list[int],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        """Compare timezone patterns across all candidates."""
        best_score = 0.5
        best_evidence = "No other candidates with enough timestamps"

        for other in all_candidates:
            if other is candidate:
                continue
            other_timestamps = self._get_timestamps(other)
            if len(other_timestamps) < _MIN_TIMESTAMPS:
                continue
            other_peak = self._infer_peak_hours(other_timestamps)
            score, evidence = self._compare_peaks(
                candidate_peak, other_peak, f"candidate {other.username}"
            )
            if score > best_score:
                best_score = score
                best_evidence = evidence

        return SignalResult(
            signal_name=self.name,
            score=best_score,
            weight=self.default_weight,
            evidence=best_evidence,
        )

    @staticmethod
    def _get_timestamps(candidate: CandidateProfile) -> list[datetime]:
        """Extract timestamps from candidate's scraped data."""
        timestamps: list[datetime] = []
        if candidate.scraped_data and candidate.scraped_data.raw_json:
            raw = candidate.scraped_data.raw_json
            if "content_timestamps" in raw:
                for ts in raw["content_timestamps"]:
                    try:
                        timestamps.append(datetime.fromisoformat(str(ts)))
                    except (ValueError, TypeError):
                        continue
        return timestamps

    @staticmethod
    def _infer_peak_hours(timestamps: list[datetime]) -> list[int]:
        """Find the top 3 most active hours from timestamps."""
        hour_counts: Counter[int] = Counter()
        for ts in timestamps:
            hour_counts[ts.hour] += 1
        return [h for h, _ in hour_counts.most_common(3)]

    @staticmethod
    def _compare_peaks(
        peaks_a: list[int], peaks_b: list[int], label: str
    ) -> tuple[float, str]:
        """Compare two sets of peak hours and return (score, evidence)."""
        if not peaks_a or not peaks_b:
            return 0.5, f"Insufficient peak data for {label}"

        # Find minimum hour difference across all peak pairs
        min_diff = 24
        for ha in peaks_a:
            for hb in peaks_b:
                diff = min(abs(ha - hb), 24 - abs(ha - hb))
                min_diff = min(min_diff, diff)

        if min_diff <= 1:
            score = 0.9
        elif min_diff <= 3:
            score = 0.5
        else:
            score = 0.1

        evidence = f"Peak hour diff={min_diff}h vs {label} (peaks: {peaks_a} vs {peaks_b})"
        return score, evidence

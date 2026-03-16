"""Writing style verification signal — stylometric analysis."""

from __future__ import annotations

import math
import re
import string

from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import SignalResult
from argus.verification.signals import BaseSignal

_MIN_CONTENT_ITEMS = 5


def _extract_features(texts: list[str]) -> dict[str, float]:
    """Extract stylometric features from a collection of texts."""
    if not texts:
        return {}

    all_words: list[str] = []
    sentence_lengths: list[int] = []
    word_lengths: list[int] = []
    total_chars = 0
    exclamation_count = 0
    question_count = 0
    ellipsis_count = 0
    emoji_count = 0
    hashtag_count = 0
    allcaps_count = 0
    total_word_count = 0

    for text in texts:
        total_chars += len(text)
        # Split into sentences (rough)
        sentences = re.split(r'[.!?]+', text)
        for sent in sentences:
            words = sent.split()
            if words:
                sentence_lengths.append(len(words))

        words = text.split()
        total_word_count += len(words)
        for w in words:
            clean = w.strip(string.punctuation)
            if clean:
                all_words.append(clean.lower())
                word_lengths.append(len(clean))
                if clean.isupper() and len(clean) > 1:
                    allcaps_count += 1

        exclamation_count += text.count("!")
        question_count += text.count("?")
        ellipsis_count += text.count("...")
        emoji_count += len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]', text))
        hashtag_count += len(re.findall(r'#\w+', text))

    if not all_words or total_word_count == 0:
        return {}

    unique_words = set(all_words)

    return {
        "avg_sentence_length": sum(sentence_lengths) / max(len(sentence_lengths), 1),
        "avg_word_length": sum(word_lengths) / max(len(word_lengths), 1),
        "vocab_richness": len(unique_words) / total_word_count,
        "exclamation_freq": exclamation_count / total_word_count,
        "question_freq": question_count / total_word_count,
        "ellipsis_freq": ellipsis_count / total_word_count,
        "emoji_freq": emoji_count / total_word_count,
        "hashtag_freq": hashtag_count / total_word_count,
        "allcaps_ratio": allcaps_count / total_word_count,
    }


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Compute cosine similarity between two feature dictionaries."""
    keys = set(a.keys()) | set(b.keys())
    if not keys:
        return 0.0

    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


class WritingStyleSignal(BaseSignal):
    """Compare writing style across platforms using stylometric features."""

    name = "writing_style"
    default_weight = 0.10

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        # Get candidate's content texts
        candidate_texts = self._get_texts(candidate)
        if len(candidate_texts) < _MIN_CONTENT_ITEMS:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence=f"Insufficient content ({len(candidate_texts)}/{_MIN_CONTENT_ITEMS})",
            )

        candidate_features = _extract_features(candidate_texts)
        if not candidate_features:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence="Could not extract features",
            )

        # Compare against seed profiles
        seed_texts: list[str] = []
        for seed in seed_profiles:
            if seed.raw_json and "content_texts" in seed.raw_json:
                seed_texts.extend(seed.raw_json["content_texts"])

        if len(seed_texts) >= _MIN_CONTENT_ITEMS:
            seed_features = _extract_features(seed_texts)
            if seed_features:
                score = _cosine_similarity(candidate_features, seed_features)
                return SignalResult(
                    signal_name=self.name,
                    score=min(score, 1.0),
                    weight=self.default_weight,
                    evidence=f"Style similarity={score:.3f} vs seed",
                    details={
                        "candidate_features": candidate_features,
                        "seed_features": seed_features,
                    },
                )

        # Compare across other candidates
        similarities = []
        for other in all_candidates:
            if other is candidate:
                continue
            other_texts = self._get_texts(other)
            if len(other_texts) < _MIN_CONTENT_ITEMS:
                continue
            other_features = _extract_features(other_texts)
            if other_features:
                sim = _cosine_similarity(candidate_features, other_features)
                similarities.append(sim)

        if similarities:
            avg_sim = sum(similarities) / len(similarities)
            return SignalResult(
                signal_name=self.name,
                score=min(avg_sim, 1.0),
                weight=self.default_weight,
                evidence=f"Avg style similarity={avg_sim:.3f} across {len(similarities)} candidates",
            )

        return SignalResult(
            signal_name=self.name,
            score=0.5,
            weight=self.default_weight,
            evidence="No comparable content for style analysis",
        )

    @staticmethod
    def _get_texts(candidate: CandidateProfile) -> list[str]:
        """Extract content texts from candidate's raw data."""
        if candidate.scraped_data and candidate.scraped_data.raw_json:
            raw = candidate.scraped_data.raw_json
            if "content_texts" in raw:
                return [str(t) for t in raw["content_texts"]]
        return []

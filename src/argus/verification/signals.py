"""Verification signals for candidate profile scoring."""

from abc import ABC, abstractmethod

import jellyfish
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import SignalResult


class BaseSignal(ABC):
    """Abstract base for verification signals."""

    name: str = "unnamed"
    default_weight: float = 1.0

    @abstractmethod
    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        ...


class PhotoHashSignal(BaseSignal):
    """Compare profile photo perceptual hashes."""

    name = "photo_hash"
    default_weight = 0.35

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        candidate_hash = (
            candidate.scraped_data.profile_photo_hash
            if candidate.scraped_data
            else None
        )
        if not candidate_hash:
            return SignalResult(
                signal_name=self.name,
                score=0.0,
                weight=self.default_weight,
                evidence="No profile photo hash available",
            )

        best_score = 0.0
        best_evidence = "No matching seed photos"

        for seed in seed_profiles:
            if not seed.profile_photo_hash:
                continue
            try:
                distance = _hamming_distance(candidate_hash, seed.profile_photo_hash)
            except ValueError:
                continue

            if distance < 10:
                score = 1.0
            elif distance > 30:
                score = 0.0
            else:
                score = 1.0 - (distance - 10) / 20.0

            if score > best_score:
                best_score = score
                best_evidence = f"Photo hash distance={distance} vs seed {seed.username}"

        return SignalResult(
            signal_name=self.name,
            score=best_score,
            weight=self.default_weight,
            evidence=best_evidence,
        )


class BioSimilaritySignal(BaseSignal):
    """Compare bio text using TF-IDF cosine similarity."""

    name = "bio_similarity"
    default_weight = 0.20

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        candidate_bio = candidate.scraped_data.bio if candidate.scraped_data else None
        if not candidate_bio:
            return SignalResult(
                signal_name=self.name,
                score=0.0,
                weight=self.default_weight,
                evidence="No bio text available",
            )

        seed_bios = [s.bio for s in seed_profiles if s.bio]
        if not seed_bios:
            return SignalResult(
                signal_name=self.name,
                score=0.0,
                weight=self.default_weight,
                evidence="No seed bios to compare against",
            )

        all_texts = [candidate_bio] + seed_bios
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        candidate_vec = tfidf_matrix[0:1]
        seed_vecs = tfidf_matrix[1:]
        similarities = cosine_similarity(candidate_vec, seed_vecs).flatten()
        best_idx = similarities.argmax()
        best_score = float(similarities[best_idx])

        return SignalResult(
            signal_name=self.name,
            score=min(max(best_score, 0.0), 1.0),
            weight=self.default_weight,
            evidence=f"Bio cosine similarity={best_score:.3f} vs seed bio",
        )


class UsernamePatternSignal(BaseSignal):
    """Compare usernames using Jaro-Winkler distance."""

    name = "username_pattern"
    default_weight = 0.10

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        candidate_username = candidate.username.lower()
        best_score = 0.0
        best_evidence = "No comparable usernames"

        for seed in seed_profiles:
            seed_username = seed.username.lower()
            sim = jellyfish.jaro_winkler_similarity(candidate_username, seed_username)
            if sim > best_score:
                best_score = sim
                best_evidence = (
                    f"Jaro-Winkler={sim:.3f} between "
                    f"'{candidate_username}' and '{seed_username}'"
                )

        return SignalResult(
            signal_name=self.name,
            score=min(max(best_score, 0.0), 1.0),
            weight=self.default_weight,
            evidence=best_evidence,
        )


def _hamming_distance(hash1: str, hash2: str) -> int:
    """Compute hamming distance between two hex hash strings."""
    if len(hash1) != len(hash2):
        raise ValueError("Hash lengths must match")
    val1 = int(hash1, 16)
    val2 = int(hash2, 16)
    return bin(val1 ^ val2).count("1")

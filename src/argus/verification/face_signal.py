"""Face recognition verification signal — optional enhancement for photo matching.

Requires the face_recognition library: pip install argus-osint[face]
Disabled by default (weight=0.0). Enable via config: face_recognition_enabled=true
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import SignalResult
from argus.verification.signals import BaseSignal

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Try importing face_recognition — graceful fallback if not installed
_face_recognition = None
try:
    import face_recognition as _face_recognition  # type: ignore[no-redef]
except ImportError:
    pass


class FaceRecognitionSignal(BaseSignal):
    """Compare profile photos using face recognition embeddings.

    Requires the face_recognition library. Falls back to neutral score
    if the library is not installed or faces cannot be detected.
    """

    name = "face_recognition"
    default_weight = 0.0  # Disabled by default

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        if _face_recognition is None:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence="face_recognition library not installed — skipped",
            )

        candidate_photo_url = (
            candidate.scraped_data.profile_photo_url
            if candidate.scraped_data
            else None
        )
        if not candidate_photo_url:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence="No candidate profile photo URL available",
            )

        seed_photo_urls = [
            s.profile_photo_url for s in seed_profiles if s.profile_photo_url
        ]
        if not seed_photo_urls:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence="No seed profile photos to compare against",
            )

        # In a real implementation, we would download and compare photos here.
        # For now, return neutral score since we can't download images in tests.
        candidate_encoding = await _get_face_encoding(candidate_photo_url)
        if candidate_encoding is None:
            return SignalResult(
                signal_name=self.name,
                score=0.5,
                weight=self.default_weight,
                evidence="No face detected in candidate photo",
            )

        best_score = 0.0
        best_evidence = "No matching faces in seed photos"

        for seed_url in seed_photo_urls:
            seed_encoding = await _get_face_encoding(seed_url)
            if seed_encoding is None:
                continue

            distance = _face_recognition.face_distance([seed_encoding], candidate_encoding)[0]
            score = _distance_to_score(distance)

            if score > best_score:
                best_score = score
                best_evidence = f"Face distance={distance:.3f} vs seed photo"

        return SignalResult(
            signal_name=self.name,
            score=min(max(best_score, 0.0), 1.0),
            weight=self.default_weight,
            evidence=best_evidence,
        )


async def _get_face_encoding(photo_url: str) -> list[float] | None:
    """Download a photo and extract face encoding.

    Returns None if face_recognition is unavailable, download fails,
    or no face is detected.
    """
    if _face_recognition is None:
        return None

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(photo_url) as resp:
                if resp.status != 200:
                    return None
                image_data = await resp.read()

        import numpy as np
        from PIL import Image

        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image_array = np.array(image)

        face_locations = _face_recognition.face_locations(image_array)
        if not face_locations:
            return None

        # Use the largest face if multiple detected
        if len(face_locations) > 1:
            face_locations = [
                max(face_locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
            ]

        encodings = _face_recognition.face_encodings(image_array, face_locations)
        if not encodings:
            return None

        return encodings[0].tolist()
    except Exception:
        logger.debug("Face encoding extraction failed for %s", photo_url, exc_info=True)
        return None


def _distance_to_score(distance: float) -> float:
    """Convert face distance to a confidence score (0.0–1.0)."""
    if distance < 0.4:
        return 0.9
    if distance < 0.5:
        return 0.6
    if distance < 0.6:
        return 0.3
    return 0.1


def is_available() -> bool:
    """Check if face_recognition library is installed."""
    return _face_recognition is not None

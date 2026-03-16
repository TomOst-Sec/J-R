# TASK-006: Verification engine — confidence scoring framework

**Priority:** critical
**Milestone:** 1
**Team:** any
**Depends:** TASK-002
**Estimated Complexity:** high

## Description

Implement the multi-signal verification engine that scores candidate profiles for confidence, filtering false positives.

## Requirements

1. Create `src/argus/verification/signals.py`:
   - `BaseSignal` abstract class:
     - `name` (str), `default_weight` (float)
     - `async def compute(self, candidate: CandidateProfile, seed_profiles: list[ProfileData], all_candidates: list[CandidateProfile]) -> SignalResult`
   - Implement these signals:
     - `PhotoHashSignal` (weight 0.35): Download profile photos, compute perceptual hashes (pHash via `imagehash`), compare against seed and cross-compare among candidates. Score = 1.0 if hash distance < 10, scaled down to 0 at distance > 30.
     - `BioSimilaritySignal` (weight 0.20): Extract bio text, compute TF-IDF vectors via scikit-learn, cosine similarity against seed bios. Score = cosine similarity value.
     - `UsernamePatternSignal` (weight 0.10): Compare usernames using Jaro-Winkler (jellyfish). Score = max similarity across seed usernames and target name-derived patterns.

2. Create `src/argus/verification/engine.py`:
   - `VerificationEngine` class:
     - `__init__(self, config: ArgusConfig)` — loads signal weights from config
     - `register_signal(self, signal: BaseSignal) -> None`
     - `async def verify(self, candidates: list[CandidateProfile], seed_profiles: list[ProfileData]) -> list[VerificationResult]`:
       - Runs all registered signals for each candidate
       - Computes weighted sum for confidence score
       - Assigns threshold label: <0.30 "discarded", <0.45 "possible", <0.70 "likely", >=0.70 "confirmed"
       - Filters out candidates below minimum threshold
       - Returns sorted by confidence descending
     - `async def verify_single(self, candidate: CandidateProfile, seed_profiles: list[ProfileData]) -> VerificationResult`

3. Create `src/argus/verification/__init__.py`:
   - Export `VerificationEngine`, `BaseSignal`, `PhotoHashSignal`, `BioSimilaritySignal`, `UsernamePatternSignal`

## Acceptance Criteria

- Engine computes weighted confidence scores correctly
- Photo hash comparison works with imagehash library
- Bio similarity uses TF-IDF + cosine similarity
- Username comparison uses Jaro-Winkler distance
- Threshold labels assigned correctly
- Candidates below minimum threshold are filtered out
- Unit tests with synthetic data for each signal and the engine
- `uv run pytest tests/test_verification.py` passes

# TASK-002: Core Pydantic data models

**Priority:** critical
**Milestone:** 1
**Team:** any
**Depends:** TASK-001
**Estimated Complexity:** medium

## Description

Define all shared Pydantic v2 models that agents, platforms, verification, and storage will use.

## Requirements

1. Create `src/argus/models/__init__.py` that re-exports all models.

2. Create `src/argus/models/target.py`:
   - `TargetInput`: name (str), location (str|None), seed_urls (list[str]), email (str|None), username_hint (str|None), phone (str|None)
   - `Target`: id (str, uuid4 default), name, location, seed_urls, email, username_hint, phone, created_at (datetime)

3. Create `src/argus/models/profile.py`:
   - `CandidateProfile`: platform (str), username (str), url (str), exists (bool|None), scraped_data (ProfileData|None)
   - `ProfileData`: username (str), display_name (str|None), bio (str|None), location (str|None), profile_photo_url (str|None), profile_photo_hash (str|None), links (list[str]), join_date (datetime|None), follower_count (int|None), following_count (int|None), raw_json (dict|None)
   - `ContentItem`: id (str), platform (str), text (str), timestamp (datetime|None), content_type (str, default "post"), url (str|None), engagement (dict|None), metadata (dict|None)

4. Create `src/argus/models/verification.py`:
   - `SignalResult`: signal_name (str), score (float, 0.0-1.0), weight (float), evidence (str), details (dict|None)
   - `VerificationResult`: candidate (CandidateProfile), signals (list[SignalResult]), confidence (float, 0.0-1.0), threshold_label (str: "discarded"|"possible"|"likely"|"confirmed")

5. Create `src/argus/models/agent.py`:
   - `AgentInput`: target (TargetInput), config (dict|None), options (dict|None)
   - `AgentOutput`: target_name (str), agent_name (str), results (list[Any]), metadata (dict|None), duration_seconds (float|None)
   - `ResolverOutput(AgentOutput)`: accounts (list[VerificationResult])
   - `LinkerOutput(AgentOutput)`: connections (list[Connection])
   - `ProfilerOutput(AgentOutput)`: dimensions (dict[str, list[TopicScore]])
   - `Connection`: platform (str), content_snippet (str), relationship_type (str), confidence (float), url (str|None), timestamp (datetime|None)
   - `TopicScore`: topic (str), score (float), evidence (list[str]), trend (str|None)

6. Create `src/argus/models/investigation.py`:
   - `Investigation`: id (str), target (Target), status (str: "running"|"completed"|"interrupted"|"failed"), created_at (datetime), updated_at (datetime), resolver_output (ResolverOutput|None), linker_output (LinkerOutput|None), profiler_output (ProfilerOutput|None)

## Acceptance Criteria

- All models importable from `argus.models`
- All models use Pydantic v2 (`model_config = ConfigDict(...)`)
- Models serialize to/from JSON correctly
- Unit tests: create instances, serialize, deserialize for each model
- `uv run ruff check src/argus/models/` passes
- `uv run pytest tests/test_models.py` passes

---
Claimed-By: bravo-2
Claimed-At: 2026-03-16T22:32:21+02:00

Completed-At: 2026-03-16T22:35:06+02:00

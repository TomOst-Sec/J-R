# TASK-012: Resolver Agent — core pipeline

**Priority:** critical
**Milestone:** 1
**Team:** any
**Depends:** TASK-004, TASK-005, TASK-006, TASK-009, TASK-017
**Estimated Complexity:** high

## Description

Implement the Resolver Agent that orchestrates platform discovery, scraping, and verification into a single pipeline.

## Requirements

1. Create `src/argus/agents/resolver.py`:
   - `ResolverAgent(BaseAgent)`:
     - `name = "resolver"`
     - `async def run(self, input: AgentInput) -> ResolverOutput`

   - Pipeline steps:
     1. **Generate username candidates** from target name (via username generator — TASK-017)
     2. **Seed profile scraping** — if seed_urls provided, scrape them first to extract ground-truth signals (photo, bio, location, links)
     3. **Platform fan-out** — for each enabled platform, concurrently:
        a. Check username existence for all candidate usernames
        b. Run name search (if platform supports it)
        c. Collect all hits as CandidateProfile list
     4. **Profile scraping** — for all candidates that exist, scrape full profiles concurrently
     5. **Verification** — pass all scraped candidates + seed profiles to VerificationEngine
     6. **Persist** — save verified results to SQLite via storage layer
     7. **Return** — ResolverOutput with verified accounts sorted by confidence

   - Must use `asyncio.gather` for platform fan-out (Step 3)
   - Must respect per-platform rate limits via stealth module
   - Must handle individual platform failures gracefully (log and continue)
   - Must support investigation resume (skip already-scraped platforms)
   - Must track timing for each phase

2. Create `src/argus/agents/username_generator.py` stub if TASK-017 not yet done (simple: lowercase name, remove spaces, common patterns).

## Acceptance Criteria

- Full resolve pipeline works end-to-end (with at least mock platforms)
- Platform failures don't crash the pipeline
- Results are sorted by confidence
- Investigation resume skips already-completed platforms
- Unit tests with mock platforms and mock verification
- `uv run pytest tests/test_resolver.py` passes

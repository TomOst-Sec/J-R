# TASK-017: Username candidate generator

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-001
**Estimated Complexity:** low

## Description

Implement a username candidate generator that takes a person's name and produces likely username variations to check across platforms.

## Requirements

1. Create `src/argus/utils/username_generator.py`:
   - `generate_username_candidates(name: str, email: str | None = None, username_hint: str | None = None) -> list[str]`:
     - From full name "John Michael Doe":
       - Lowercase full: `johnmichaeldoe`
       - First + last: `johndoe`
       - First initial + last: `jdoe`
       - First + last initial: `johnd`
       - First.last: `john.doe`
       - First_last: `john_doe`
       - First-last: `john-doe`
       - Last + first: `doejohn`
       - Last.first: `doe.john`
       - With common suffixes: `johndoe1`, `johndoe_`, `thejohndoe`, `realjohndoe`
     - If email provided: extract username part before @
     - If username_hint provided: add it + variations (with numbers, underscores)
     - Deduplicate results
     - Return sorted by likelihood (exact hints first, then common patterns)
   - Max 30 candidates per name to avoid excessive API calls

2. Create `src/argus/utils/__init__.py` with exports.

3. Handle edge cases:
   - Single name (mononym): just use that name + variations
   - Names with special characters: normalize (remove accents, transliterate)
   - Very long names: truncate sensibly
   - Common name formats: "van der Berg", "O'Brien", "Al-Rashid"

## Acceptance Criteria

- Generates reasonable username candidates for common names
- Handles edge cases (single names, special chars, compound names)
- Email and hint hints prioritized in output
- Max 30 candidates returned
- Unit tests with diverse name inputs
- `uv run pytest tests/test_username_generator.py` passes

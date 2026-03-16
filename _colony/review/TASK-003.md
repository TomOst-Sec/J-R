# TASK-003: Configuration system

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-001
**Estimated Complexity:** medium

## Description

Implement the argus.toml configuration system with layered loading, env var interpolation, and CLI override support.

## Requirements

1. Create `src/argus/config/settings.py`:
   - `ArgusConfig` Pydantic model with sections:
     - `general`: default_threshold (float=0.45), max_concurrent_requests (int=10), output_format (str="table"), language (str="en")
     - `platforms`: dict[str, PlatformConfig] where PlatformConfig has: enabled (bool=True), rate_limit_per_minute (int=30), credentials (dict|None)
     - `proxy`: url (str|None), rotation_strategy (str="round-robin"), auth (dict|None)
     - `llm`: provider (str="none"), model (str|None), api_key (str|None), base_url (str|None)
     - `verification`: signal_weights (dict with defaults: photo=0.35, bio=0.20, timezone=0.15, username=0.10, connections=0.10, writing_style=0.10), minimum_threshold (float=0.30), photo_matching_enabled (bool=True), face_recognition_enabled (bool=False)
     - `output`: default_format (str="table"), report_template (str|None), include_raw_data (bool=False)
     - `stealth`: user_agent_rotation (bool=True), min_delay (float=2.0), max_delay (float=5.0), respect_robots_txt (bool=False)

2. Create `src/argus/config/loader.py`:
   - Load config from (in priority order): CLI flags > env vars > ./argus.toml > ~/.argus/argus.toml > defaults
   - Env var interpolation: `${ENV_VAR}` syntax in toml values resolves to env var
   - Env var override: `ARGUS_GENERAL_THRESHOLD=0.6` maps to `general.threshold`
   - `load_config(cli_overrides: dict|None = None) -> ArgusConfig`

3. Create `src/argus/config/__init__.py`:
   - Export `ArgusConfig`, `load_config`
   - Module-level `get_config() -> ArgusConfig` singleton accessor

4. Create a default `argus.toml.example` in project root showing all options with comments.

## Acceptance Criteria

- Config loads from toml file correctly
- Env var interpolation works (`${VAR}` in values)
- Env var overrides work (`ARGUS_*` prefix)
- Layered loading: file < env < CLI
- Defaults work when no config file exists
- Unit tests cover: default loading, file loading, env override, env interpolation
- `uv run pytest tests/test_config.py` passes

---
Claimed-By: alpha-1
Claimed-At: 2026-03-16T23:30:00+02:00
Completed-At: 2026-03-16T23:35:00+02:00

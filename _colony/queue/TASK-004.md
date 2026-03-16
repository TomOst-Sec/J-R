# TASK-004: BasePlatform interface and plugin auto-discovery

**Priority:** critical
**Milestone:** 1
**Team:** any
**Depends:** TASK-002
**Estimated Complexity:** medium

## Description

Define the BasePlatform abstract class and implement automatic platform module discovery from the `argus/platforms/` directory.

## Requirements

1. Create `src/argus/platforms/base.py`:
   - `BasePlatform` abstract class with:
     - Class attributes: `name` (str), `base_url` (str), `rate_limit_per_minute` (int=30), `requires_auth` (bool=False), `requires_playwright` (bool=False), `priority` (int=50, higher=checked first)
     - Abstract methods:
       - `async def check_username(self, username: str) -> bool | None` — True if exists, False if not, None if unable to determine
       - `async def search_name(self, name: str, location: str | None = None) -> list[CandidateProfile]`
       - `async def scrape_profile(self, url: str) -> ProfileData | None`
     - Optional methods (default no-op):
       - `async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]`
       - `async def get_connections(self, url: str) -> list[Connection]`
     - Built-in methods:
       - `async def initialize(self, config: ArgusConfig) -> None` — called once before use
       - `async def shutdown(self) -> None` — cleanup
     - Constructor takes `session: aiohttp.ClientSession` and `config: ArgusConfig`

2. Create `src/argus/platforms/registry.py`:
   - `PlatformRegistry` class:
     - `discover_platforms() -> dict[str, type[BasePlatform]]` — scans `argus/platforms/` for all Python files, imports them, finds BasePlatform subclasses
     - `get_platform(name: str) -> type[BasePlatform] | None`
     - `list_platforms() -> list[str]`
     - `get_enabled_platforms(config: ArgusConfig) -> list[type[BasePlatform]]`
   - Auto-discovery uses `importlib` + `inspect` to find subclasses
   - Skip files starting with `_` or named `base.py`, `registry.py`

3. Update `src/argus/platforms/__init__.py`:
   - Export `BasePlatform`, `PlatformRegistry`

4. Create a test platform `tests/fixtures/mock_platform.py` implementing BasePlatform for testing.

## Acceptance Criteria

- BasePlatform is abstract — cannot be instantiated directly
- Auto-discovery finds all platform subclasses in the platforms directory
- Registry correctly filters by enabled config
- Test platform can be instantiated and its methods called
- Unit tests: discovery, registration, enabled filtering
- `uv run pytest tests/test_platforms.py` passes

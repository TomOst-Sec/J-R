# TASK-010: Stealth and rate limiting module

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-003
**Estimated Complexity:** medium

## Description

Implement stealth features: User-Agent rotation, per-platform token bucket rate limiting, random delays, and proxy support.

## Requirements

1. Create `src/argus/stealth/user_agents.py`:
   - Curated list of 50+ realistic browser User-Agent strings (Chrome, Firefox, Safari — desktop and mobile, recent versions)
   - `get_random_user_agent(seed: int | None = None) -> str`
   - `UserAgentRotator` class: round-robin or random selection, seeded PRNG for reproducibility

2. Create `src/argus/stealth/rate_limiter.py`:
   - `TokenBucketRateLimiter`:
     - `__init__(self, rate_per_minute: int, burst: int | None = None)`
     - `async def acquire(self) -> None` — blocks until a token is available
     - `async def wait_if_needed(self) -> float` — returns actual wait time
   - `PlatformRateLimiter`:
     - Manages per-platform rate limiters
     - `get_limiter(platform: str) -> TokenBucketRateLimiter`
     - `async def acquire(self, platform: str) -> None`

3. Create `src/argus/stealth/delays.py`:
   - `async def random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0, seed: int | None = None) -> float` — sleep for random duration, return actual delay
   - `DelayManager`: configurable per-platform delay ranges

4. Create `src/argus/stealth/proxy.py`:
   - `ProxyRotator`:
     - `__init__(self, proxies: list[str], strategy: str = "round-robin")`
     - `get_next() -> str | None` — returns next proxy URL
     - `mark_failed(proxy: str) -> None` — track failures, skip bad proxies
   - Support SOCKS5 and HTTP proxy URLs

5. Create `src/argus/stealth/session.py`:
   - `create_stealth_session(config: ArgusConfig) -> aiohttp.ClientSession` — factory that creates a session with rotated User-Agent, proxy, and appropriate headers

6. Create `src/argus/stealth/__init__.py`:
   - Export all public classes and functions

## Acceptance Criteria

- User-Agent rotation provides realistic browser UAs
- Token bucket correctly rate-limits requests per platform
- Random delays use seeded PRNG for reproducibility
- Proxy rotation works with round-robin and random strategies
- Session factory creates properly configured aiohttp sessions
- Unit tests for each component
- `uv run pytest tests/test_stealth.py` passes

---
Claimed-By: alpha-1
Completed-At: 2026-03-17T00:00:00+02:00

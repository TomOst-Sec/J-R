"""Token bucket rate limiter for per-platform request throttling."""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Async token bucket rate limiter."""

    def __init__(self, rate_per_minute: int, burst: int | None = None) -> None:
        self._rate = rate_per_minute / 60.0  # tokens per second
        self._burst = burst if burst is not None else rate_per_minute
        self._tokens = float(self._burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    async def acquire(self) -> None:
        """Block until a token is available."""
        async with self._lock:
            self._refill()
            while self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= 1.0

    async def wait_if_needed(self) -> float:
        """Acquire a token and return the actual wait time in seconds."""
        start = time.monotonic()
        await self.acquire()
        return time.monotonic() - start


class PlatformRateLimiter:
    """Manages per-platform rate limiters."""

    def __init__(self, default_rate: int = 30) -> None:
        self._default_rate = default_rate
        self._limiters: dict[str, TokenBucketRateLimiter] = {}

    def get_limiter(self, platform: str) -> TokenBucketRateLimiter:
        """Get or create a rate limiter for a platform."""
        if platform not in self._limiters:
            self._limiters[platform] = TokenBucketRateLimiter(self._default_rate)
        return self._limiters[platform]

    def set_rate(self, platform: str, rate_per_minute: int) -> None:
        """Set the rate for a specific platform."""
        self._limiters[platform] = TokenBucketRateLimiter(rate_per_minute)

    async def acquire(self, platform: str) -> None:
        """Acquire a token for the given platform."""
        await self.get_limiter(platform).acquire()

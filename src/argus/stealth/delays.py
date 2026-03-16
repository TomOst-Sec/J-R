"""Random delay utilities for stealth request timing."""

from __future__ import annotations

import asyncio
import random
import time


async def random_delay(
    min_seconds: float = 2.0,
    max_seconds: float = 5.0,
    seed: int | None = None,
) -> float:
    """Sleep for a random duration between min and max seconds.

    Returns the actual delay in seconds.
    """
    rng = random.Random(seed)
    delay = rng.uniform(min_seconds, max_seconds)
    start = time.monotonic()
    await asyncio.sleep(delay)
    return time.monotonic() - start


class DelayManager:
    """Configurable per-platform delay ranges."""

    def __init__(
        self,
        default_min: float = 2.0,
        default_max: float = 5.0,
        seed: int | None = None,
    ) -> None:
        self._default_min = default_min
        self._default_max = default_max
        self._rng = random.Random(seed)
        self._platform_ranges: dict[str, tuple[float, float]] = {}

    def set_range(self, platform: str, min_seconds: float, max_seconds: float) -> None:
        """Set delay range for a specific platform."""
        self._platform_ranges[platform] = (min_seconds, max_seconds)

    async def delay(self, platform: str | None = None) -> float:
        """Sleep for a random duration based on platform config. Returns actual delay."""
        if platform and platform in self._platform_ranges:
            mn, mx = self._platform_ranges[platform]
        else:
            mn, mx = self._default_min, self._default_max
        delay_time = self._rng.uniform(mn, mx)
        start = time.monotonic()
        await asyncio.sleep(delay_time)
        return time.monotonic() - start

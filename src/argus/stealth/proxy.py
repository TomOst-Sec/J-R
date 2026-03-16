"""Proxy rotation for stealth networking."""

from __future__ import annotations

import random


class ProxyRotator:
    """Rotates through proxy URLs with failure tracking."""

    def __init__(
        self,
        proxies: list[str],
        strategy: str = "round-robin",
        seed: int | None = None,
    ) -> None:
        self._proxies = list(proxies)
        self._strategy = strategy
        self._rng = random.Random(seed)
        self._index = 0
        self._failed: set[str] = set()

    def _available(self) -> list[str]:
        return [p for p in self._proxies if p not in self._failed]

    def get_next(self) -> str | None:
        """Return the next proxy URL, or None if all have failed."""
        available = self._available()
        if not available:
            return None
        if self._strategy == "random":
            return self._rng.choice(available)
        # round-robin
        proxy = available[self._index % len(available)]
        self._index += 1
        return proxy

    def mark_failed(self, proxy: str) -> None:
        """Mark a proxy as failed so it will be skipped."""
        self._failed.add(proxy)

    def reset_failures(self) -> None:
        """Clear all failure marks."""
        self._failed.clear()

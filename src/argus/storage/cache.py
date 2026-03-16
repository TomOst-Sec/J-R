"""HTTP response cache for avoiding redundant requests."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class ResponseCache:
    """Simple file-based HTTP response cache with TTL."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        ttl_seconds: int = 3600,
        enabled: bool = True,
    ) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".argus" / "cache"
        self._cache_dir = Path(cache_dir)
        self._ttl = ttl_seconds
        self._enabled = enabled
        if self._enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> str | None:
        """Get cached response for URL, or None if expired/missing."""
        if not self._enabled:
            return None
        path = self._cache_dir / self._key(url)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > self._ttl:
                path.unlink(missing_ok=True)
                return None
            return data["body"]
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def put(self, url: str, body: str) -> None:
        """Cache a response body for a URL."""
        if not self._enabled:
            return
        path = self._cache_dir / self._key(url)
        data = {"url": url, "body": body, "timestamp": time.time()}
        path.write_text(json.dumps(data))

    def clear(self) -> int:
        """Clear all cached responses. Returns count deleted."""
        if not self._cache_dir.exists():
            return 0
        count = 0
        for f in self._cache_dir.iterdir():
            if f.is_file():
                f.unlink()
                count += 1
        return count

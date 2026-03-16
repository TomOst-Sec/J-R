# Platform Development Guide

Add a new platform to Argus in under 30 minutes.

## Overview

Each platform is a single Python file in `src/argus/platforms/` that implements the `BasePlatform` abstract class. The platform registry auto-discovers all subclasses — no registration code needed.

## Step 1: Create the Module

Create `src/argus/platforms/myplatform.py`:

```python
"""MyPlatform module for Argus OSINT."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

_USERNAME_RE = re.compile(r"myplatform\.com/(?:user/)?([^/?#]+)")


class MyPlatform(BasePlatform):
    name = "myplatform"
    base_url = "https://myplatform.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 50  # Higher = checked first

    async def check_username(self, username: str) -> bool | None:
        """Check if username exists. Return True/False/None."""
        try:
            async with self.session.get(
                f"{self.base_url}/api/users/{username}"
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status == 404:
                    return False
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search by name. Return empty list if not supported."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape profile data from a URL."""
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{self.base_url}/api/users/{username}"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return ProfileData(
                    username=data["username"],
                    display_name=data.get("name"),
                    bio=data.get("bio"),
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    match = _USERNAME_RE.search(url)
    return match.group(1) if match else None
```

## Step 2: Required Methods

| Method | Required | Returns |
|--------|----------|---------|
| `check_username(username)` | Yes | `True` (exists), `False` (not found), `None` (error) |
| `search_name(name, location)` | Yes | `list[CandidateProfile]` (empty if unsupported) |
| `scrape_profile(url)` | Yes | `ProfileData | None` |
| `scrape_content(url, max_items)` | No | `list[ContentItem]` (default: empty) |
| `get_connections(url)` | No | `list[Connection]` (default: empty) |

## Step 3: Class Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | required | Platform identifier (lowercase) |
| `base_url` | str | required | Platform base URL |
| `rate_limit_per_minute` | int | 30 | Max requests per minute |
| `requires_auth` | bool | False | Needs API credentials |
| `requires_playwright` | bool | False | Needs browser automation |
| `priority` | int | 50 | Discovery order (higher = first) |

## Step 4: Write Tests

Create `tests/test_platform_myplatform.py`:

```python
from unittest.mock import MagicMock

from argus.config import ArgusConfig
from argus.platforms.myplatform import MyPlatform


def _make_session(responses):
    session = MagicMock()
    # ... mock aiohttp session (see existing tests for pattern)
    return session


class TestMyPlatform:
    async def test_check_username_exists(self):
        session = _make_session({"api/users/testuser": (200, {"username": "testuser"})})
        platform = MyPlatform(session=session, config=ArgusConfig())
        assert await platform.check_username("testuser") is True

    async def test_check_username_not_found(self):
        session = _make_session({})
        platform = MyPlatform(session=session, config=ArgusConfig())
        assert await platform.check_username("nobody") is False
```

## Step 5: Verify

```bash
uv run pytest tests/test_platform_myplatform.py -v
uv run ruff check src/argus/platforms/myplatform.py
```

The platform will be auto-discovered by `PlatformRegistry.discover_platforms()`.

## Tips

- Always handle HTTP errors gracefully (return `None`/`False`/empty list)
- Send realistic User-Agent headers (some platforms block default Python UA)
- Respect `rate_limit_per_minute` — the stealth module enforces this
- Store the full API response in `ProfileData.raw_json` for debugging
- Use `_extract_username(url)` helper for URL parsing

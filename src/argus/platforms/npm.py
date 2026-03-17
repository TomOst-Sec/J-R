"""npm platform module using public registry API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_REGISTRY_BASE = "https://registry.npmjs.org"
_USERNAME_RE = re.compile(r"npmjs\.com/~([^/?#]+)")


class NpmPlatform(BasePlatform):
    """npm platform using the public registry API."""

    name = "npm"
    base_url = "https://www.npmjs.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 50

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_REGISTRY_BASE}/-/v1/search",
                params={"text": f"maintainer:{username}", "size": "1"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("total", 0) > 0
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        # npm has no name-based user search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{self.base_url}/~{username}",
                headers={"Accept": "text/html"},
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                display_name = _extract_meta(html, "og:title")
                bio = _extract_meta(html, "og:description")
                return ProfileData(
                    username=username,
                    display_name=display_name,
                    bio=bio,
                    links=[f"{self.base_url}/~{username}"],
                    raw_json={"source": "html_meta"},
                )
        except Exception:
            return None


def _extract_meta(html: str, property_name: str) -> str | None:
    """Extract an og: meta tag value from HTML."""
    pattern = re.compile(
        rf'<meta[^>]*property=["\']?{re.escape(property_name)}["\']?[^>]*content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    match = pattern.search(html)
    if match:
        value = match.group(1).strip()
        return value if value else None
    return None


def _extract_username(url: str) -> str | None:
    """Extract username from an npm profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

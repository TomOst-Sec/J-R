"""RubyGems platform module using public REST API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://rubygems.org/api/v1"
_USERNAME_RE = re.compile(r"rubygems\.org/profiles/([^/?#]+)")


class RubyGemsPlatform(BasePlatform):
    """RubyGems platform using the public REST API."""

    name = "rubygems"
    base_url = "https://rubygems.org"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 45

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/profiles/{username}.json"
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
        # RubyGems has no name-based user search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/profiles/{username}.json"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return ProfileData(
                    username=data.get("handle", username),
                    bio=data.get("bio") or None,
                    profile_photo_url=data.get("avatar") or None,
                    links=[f"{self.base_url}/profiles/{username}"],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a RubyGems profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

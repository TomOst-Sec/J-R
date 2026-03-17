"""Gravatar platform module using public JSON API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://en.gravatar.com"
_USERNAME_RE = re.compile(r"gravatar\.com/([^/?#]+)")


class GravatarPlatform(BasePlatform):
    """Gravatar platform using the public JSON API."""

    name = "gravatar"
    base_url = "https://gravatar.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 55

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/{username}.json"
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
        # Gravatar has no name-based search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/{username}.json"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                entries = data.get("entry", [])
                if not entries:
                    return None
                entry = entries[0]

                links = []
                for u in entry.get("urls", []):
                    val = u.get("value")
                    if val:
                        links.append(val)

                return ProfileData(
                    username=entry.get("preferredUsername", username),
                    display_name=entry.get("displayName"),
                    bio=entry.get("aboutMe"),
                    profile_photo_url=entry.get("thumbnailUrl"),
                    links=links,
                    raw_json=entry,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username or hash from a Gravatar URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    # Strip .json suffix if present
    if username.endswith(".json"):
        username = username[:-5]
    return username.rstrip("/")

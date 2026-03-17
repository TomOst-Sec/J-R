"""Crates.io platform module using public REST API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://crates.io/api/v1"
_USERNAME_RE = re.compile(r"crates\.io/users/([^/?#]+)")


class CratesIOPlatform(BasePlatform):
    """Crates.io platform using the public REST API."""

    name = "cratesio"
    base_url = "https://crates.io"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 45

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/users/{username}",
                headers={"User-Agent": "argus-osint (https://github.com/argus)"},
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
        # Crates.io has no name-based user search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/users/{username}",
                headers={"User-Agent": "argus-osint (https://github.com/argus)"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                user = data.get("user", data)
                links = []
                if user.get("url"):
                    links.append(user["url"])
                links.append(f"{self.base_url}/users/{user.get('login', username)}")
                return ProfileData(
                    username=user.get("login", username),
                    display_name=user.get("name"),
                    profile_photo_url=user.get("avatar"),
                    links=links,
                    raw_json=user,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Crates.io user URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

"""Bitbucket platform module using public REST API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://api.bitbucket.org/2.0"
_USERNAME_RE = re.compile(r"bitbucket\.org/([^/?#]+)")


class BitbucketPlatform(BasePlatform):
    """Bitbucket platform using the public REST API (no auth required)."""

    name = "bitbucket"
    base_url = "https://bitbucket.org"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 60

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/users/{username}"
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
        # Bitbucket has no public name-based user search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/users/{username}"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                avatar = None
                links = data.get("links", {})
                avatar_link = links.get("avatar", {})
                if isinstance(avatar_link, dict):
                    avatar = avatar_link.get("href")
                profile_links = []
                html_link = links.get("html", {})
                if isinstance(html_link, dict) and html_link.get("href"):
                    profile_links.append(html_link["href"])
                return ProfileData(
                    username=data.get("username", username),
                    display_name=data.get("display_name"),
                    location=data.get("location"),
                    profile_photo_url=avatar,
                    links=profile_links,
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Bitbucket profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

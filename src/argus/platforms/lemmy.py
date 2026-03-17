"""Lemmy platform module using public REST API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://lemmy.world/api/v3"
_USERNAME_RE = re.compile(r"lemmy\.world/u/([^/?#]+)")


class LemmyPlatform(BasePlatform):
    """Lemmy platform using the public REST API (lemmy.world instance)."""

    name = "lemmy"
    base_url = "https://lemmy.world"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 40

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/user",
                params={"username": username},
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
        # Lemmy has no public name-based search for users
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/user",
                params={"username": username},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                person_view = data.get("person_view", {})
                person = person_view.get("person", {})
                counts = person_view.get("counts", {})

                return ProfileData(
                    username=person.get("name", username),
                    display_name=person.get("display_name"),
                    bio=person.get("bio"),
                    profile_photo_url=person.get("avatar"),
                    links=[f"{self.base_url}/u/{person.get('name', username)}"],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Lemmy profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

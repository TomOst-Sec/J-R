"""GitLab platform module using public REST API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://gitlab.com/api/v4"
_USERNAME_RE = re.compile(r"gitlab\.com/([^/?#]+)")


class GitLabPlatform(BasePlatform):
    """GitLab platform using the public REST API (no auth required)."""

    name = "gitlab"
    base_url = "https://gitlab.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 75

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/users", params={"username": username}
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return len(data) > 0
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        try:
            async with self.session.get(
                f"{_API_BASE}/users", params={"search": name}
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for user in data[:10]:
                    results.append(
                        CandidateProfile(
                            platform=self.name,
                            username=user.get("username", ""),
                            url=user.get("web_url", f"{self.base_url}/{user.get('username', '')}"),
                        )
                    )
                return results
        except Exception:
            return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/users", params={"username": username}
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data:
                    return None
                user = data[0]
                links = []
                if user.get("web_url"):
                    links.append(user["web_url"])
                if user.get("website_url"):
                    links.append(user["website_url"])
                return ProfileData(
                    username=user.get("username", username),
                    display_name=user.get("name"),
                    bio=user.get("bio"),
                    location=user.get("location"),
                    profile_photo_url=user.get("avatar_url"),
                    links=links,
                    raw_json=user,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a GitLab profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

"""Codeberg platform module using Gitea REST API."""

from __future__ import annotations

import re
from datetime import datetime

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://codeberg.org/api/v1"
_USERNAME_RE = re.compile(r"codeberg\.org/([^/?#]+)")


class CodebergPlatform(BasePlatform):
    """Codeberg platform using the Gitea REST API."""

    name = "codeberg"
    base_url = "https://codeberg.org"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 55

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
        try:
            async with self.session.get(
                f"{_API_BASE}/users/search",
                params={"q": name, "limit": "10"},
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                users = data.get("data", data) if isinstance(data, dict) else data
                if not isinstance(users, list):
                    return []
                results = []
                for user in users[:10]:
                    login = user.get("login", user.get("username", ""))
                    results.append(
                        CandidateProfile(
                            platform=self.name,
                            username=login,
                            url=f"{self.base_url}/{login}",
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
                f"{_API_BASE}/users/{username}"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                links = [f"{self.base_url}/{data.get('login', username)}"]
                if data.get("website"):
                    links.append(data["website"])

                join_date = None
                if data.get("created"):
                    try:
                        join_date = datetime.fromisoformat(
                            data["created"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                return ProfileData(
                    username=data.get("login", username),
                    display_name=data.get("full_name") or None,
                    bio=data.get("description") or None,
                    location=data.get("location") or None,
                    profile_photo_url=data.get("avatar_url"),
                    join_date=join_date,
                    links=links,
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Codeberg profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

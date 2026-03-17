"""Docker Hub platform module using public REST API."""

from __future__ import annotations

import re
from datetime import datetime

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://hub.docker.com/v2"
_USERNAME_RE = re.compile(r"hub\.docker\.com/u/([^/?#]+)")


class DockerHubPlatform(BasePlatform):
    """Docker Hub platform using the public REST API."""

    name = "dockerhub"
    base_url = "https://hub.docker.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 50

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/users/{username}/"
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
        # Docker Hub has no public name-based user search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/users/{username}/"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                join_date = None
                if data.get("date_joined"):
                    try:
                        join_date = datetime.fromisoformat(
                            data["date_joined"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass
                return ProfileData(
                    username=data.get("username", username),
                    display_name=data.get("full_name") or None,
                    location=data.get("location") or None,
                    profile_photo_url=data.get("gravatar_url") or None,
                    join_date=join_date,
                    links=[f"{self.base_url}/u/{username}"],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Docker Hub profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

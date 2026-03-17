"""Lichess platform module using public REST API."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://lichess.org/api"
_USERNAME_RE = re.compile(r"lichess\.org/@/([^/?#]+)")


class LichessPlatform(BasePlatform):
    """Lichess platform using the public REST API."""

    name = "lichess"
    base_url = "https://lichess.org"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 35

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/user/{username}",
                headers={"Accept": "application/json"},
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
        # Lichess has no public name-based search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/user/{username}",
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                profile = data.get("profile", {})

                # Build display name from first + last
                name_parts = []
                if profile.get("firstName"):
                    name_parts.append(profile["firstName"])
                if profile.get("lastName"):
                    name_parts.append(profile["lastName"])
                display_name = " ".join(name_parts) if name_parts else None

                join_date = None
                created_at = data.get("createdAt")
                if created_at:
                    # Lichess returns milliseconds since epoch
                    join_date = datetime.fromtimestamp(
                        created_at / 1000, tz=timezone.utc
                    )

                return ProfileData(
                    username=data.get("username", username),
                    display_name=display_name,
                    bio=profile.get("bio"),
                    location=profile.get("location"),
                    join_date=join_date,
                    links=[f"{self.base_url}/@/{data.get('username', username)}"],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Lichess profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

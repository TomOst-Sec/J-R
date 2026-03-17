"""Chess.com platform module using public REST API."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://api.chess.com/pub"
_USERNAME_RE = re.compile(r"chess\.com/member/([^/?#]+)")


class ChessComPlatform(BasePlatform):
    """Chess.com platform using the public REST API."""

    name = "chesscom"
    base_url = "https://www.chess.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 35

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/player/{username}"
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
        # Chess.com has no public name-based search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/player/{username}"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

                join_date = None
                joined = data.get("joined")
                if joined:
                    join_date = datetime.fromtimestamp(joined, tz=timezone.utc)

                return ProfileData(
                    username=data.get("username", username),
                    display_name=data.get("name"),
                    location=data.get("location"),
                    profile_photo_url=data.get("avatar"),
                    follower_count=data.get("followers"),
                    join_date=join_date,
                    links=[data.get("url", f"{self.base_url}/member/{username}")],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Chess.com profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

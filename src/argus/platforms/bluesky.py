"""Bluesky platform module using public AT Protocol API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://public.api.bsky.app/xrpc"
_HANDLE_RE = re.compile(r"bsky\.app/profile/([^/?#]+)")


class BlueskyPlatform(BasePlatform):
    """Bluesky platform using the public AT Protocol API."""

    name = "bluesky"
    base_url = "https://bsky.app"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 65

    @staticmethod
    def _resolve_actor(username: str) -> str:
        """Resolve a username to a full actor handle."""
        if "." in username:
            return username
        return f"{username}.bsky.social"

    async def check_username(self, username: str) -> bool | None:
        actor = self._resolve_actor(username)
        try:
            async with self.session.get(
                f"{_API_BASE}/app.bsky.actor.getProfile",
                params={"actor": actor},
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status == 400:
                    return False
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        try:
            async with self.session.get(
                f"{_API_BASE}/app.bsky.actor.searchActors",
                params={"q": name, "limit": "10"},
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                actors = data.get("actors", [])
                results = []
                for actor in actors:
                    handle = actor.get("handle", "")
                    results.append(
                        CandidateProfile(
                            platform=self.name,
                            username=handle,
                            url=f"{self.base_url}/profile/{handle}",
                        )
                    )
                return results
        except Exception:
            return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        handle = _extract_handle(url)
        if not handle:
            return None
        actor = self._resolve_actor(handle)
        try:
            async with self.session.get(
                f"{_API_BASE}/app.bsky.actor.getProfile",
                params={"actor": actor},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return ProfileData(
                    username=data.get("handle", handle),
                    display_name=data.get("displayName"),
                    bio=data.get("description"),
                    profile_photo_url=data.get("avatar"),
                    follower_count=data.get("followersCount"),
                    following_count=data.get("followsCount"),
                    links=[f"{self.base_url}/profile/{data.get('handle', handle)}"],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_handle(url: str) -> str | None:
    """Extract handle from a Bluesky profile URL."""
    match = _HANDLE_RE.search(url)
    if not match:
        return None
    handle = match.group(1)
    return handle.rstrip("/")

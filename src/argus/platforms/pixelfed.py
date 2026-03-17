"""Pixelfed platform module — federated image sharing discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class PixelfedPlatform(BasePlatform):
    """Pixelfed platform for federated image sharing profile discovery."""

    name = "pixelfed"
    base_url = "https://pixelfed.social"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 30

    async def check_username(self, username: str) -> bool | None:
        """Check if a Pixelfed username exists via Mastodon-compatible API."""
        api_url = (
            f"https://pixelfed.social/api/v1/accounts/lookup"
            f"?acct={quote(username)}"
        )
        try:
            async with self.session.get(api_url) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    return True
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Pixelfed users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Pixelfed profile via Mastodon-compatible API."""
        username = self._extract_username(url)
        if not username:
            return None

        api_url = (
            f"https://pixelfed.social/api/v1/accounts/lookup"
            f"?acct={quote(username)}"
        )
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        return self._parse_profile(data, username)

    def _parse_profile(self, data: dict, username: str) -> ProfileData | None:
        """Parse Pixelfed profile from Mastodon-compatible API response."""
        display_name = data.get("display_name")
        bio = data.get("note")
        photo_url = data.get("avatar")

        # Strip HTML tags from bio
        if bio:
            bio = re.sub(r"<[^>]+>", "", bio).strip()

        follower_count = data.get("followers_count")
        following_count = data.get("following_count")

        if not display_name and not bio:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            follower_count=follower_count,
            following_count=following_count,
            raw_json=data,
        )

    @staticmethod
    def _extract_meta(html_text: str, property_name: str) -> str | None:
        """Extract a meta tag value."""
        pattern = rf'<meta\s+(?:property|name)="{re.escape(property_name)}"\s+content="([^"]*)"'
        match = re.search(pattern, html_text)
        if match:
            return match.group(1)
        pattern = rf'content="([^"]*)"\s+(?:property|name)="{re.escape(property_name)}"'
        match = re.search(pattern, html_text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_username(url: str) -> str | None:
        """Extract Pixelfed username from a URL."""
        match = re.search(r"pixelfed\.social/@?([^/?]+)", url)
        return match.group(1) if match else None

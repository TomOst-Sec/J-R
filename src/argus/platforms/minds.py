"""Minds platform module — open-source social network discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class MindsPlatform(BasePlatform):
    """Minds platform for open-source social network profile discovery."""

    name = "minds"
    base_url = "https://www.minds.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 30

    async def check_username(self, username: str) -> bool | None:
        """Check if a Minds username exists via API."""
        api_url = f"https://www.minds.com/api/v1/channel/{quote(username)}"
        try:
            async with self.session.get(api_url) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "error":
                        return False
                    if data.get("channel"):
                        return True
                    return None
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Minds users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Minds profile via API."""
        username = self._extract_username(url)
        if not username:
            return None

        api_url = f"https://www.minds.com/api/v1/channel/{quote(username)}"
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        channel = data.get("channel")
        if not channel:
            return None

        return self._parse_profile(channel, username)

    def _parse_profile(self, channel: dict, username: str) -> ProfileData | None:
        """Parse Minds profile from channel API response."""
        display_name = channel.get("name")
        bio = channel.get("briefdescription")
        photo_url = channel.get("avatar_url")

        # Fallback avatar construction
        if not photo_url:
            icon_url = channel.get("icontime")
            guid = channel.get("guid")
            if icon_url and guid:
                photo_url = f"https://www.minds.com/icon/{guid}/large/{icon_url}"

        follower_count = None
        subs = channel.get("subscribers_count")
        if subs is not None:
            try:
                follower_count = int(subs)
            except (ValueError, TypeError):
                pass

        if not display_name and not bio:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            follower_count=follower_count,
            raw_json=channel,
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
        """Extract Minds username from a URL."""
        match = re.search(r"minds\.com/([^/?]+)", url)
        return match.group(1) if match else None

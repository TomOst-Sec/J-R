"""Trello platform module — project board profile discovery."""

from __future__ import annotations

import logging
import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class TrelloPlatform(BasePlatform):
    """Trello platform for project board profile discovery."""

    name = "trello"
    base_url = "https://trello.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 35

    async def check_username(self, username: str) -> bool | None:
        """Check if a Trello username exists."""
        url = f"https://trello.com/{username}"
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
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
        """Search for Trello users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Trello profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        # Try API first for richer data
        profile_data = await self._try_api(username)
        if profile_data:
            return profile_data

        # Fallback to HTML scraping
        profile_url = f"https://trello.com/{username}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile(text, username)

    async def _try_api(self, username: str) -> ProfileData | None:
        """Try to get profile data from Trello's public API."""
        api_url = f"https://api.trello.com/1/members/{username}"
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        full_name = data.get("fullName")
        bio = data.get("bio")
        avatar_hash = data.get("avatarHash")
        avatar_url = None
        if avatar_hash:
            member_id = data.get("id", "")
            avatar_url = f"https://trello-members.s3.amazonaws.com/{member_id}/{avatar_hash}/170.png"

        if not full_name and not bio:
            return None

        return ProfileData(
            username=username,
            display_name=full_name,
            bio=bio if bio else None,
            profile_photo_url=avatar_url,
            raw_json=data,
        )

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Trello profile from HTML/meta tags."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        if not display_name and not bio:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
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
        """Extract Trello username from a URL."""
        match = re.search(r"trello\.com/([^/?]+)", url)
        return match.group(1) if match else None

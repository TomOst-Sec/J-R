"""Patreon platform module — creator page discovery."""

from __future__ import annotations

import logging
import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class PatreonPlatform(BasePlatform):
    """Patreon platform for creator page discovery."""

    name = "patreon"
    base_url = "https://www.patreon.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 50

    async def check_username(self, username: str) -> bool | None:
        """Check if a Patreon username exists."""
        url = f"https://www.patreon.com/{username}"
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
        """Search for Patreon users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Patreon profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://www.patreon.com/{username}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile(text, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Patreon profile from HTML/meta tags."""
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
        """Extract Patreon username from a URL."""
        match = re.search(r"patreon\.com/([^/?]+)", url)
        return match.group(1) if match else None

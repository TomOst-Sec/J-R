"""Odysee platform module — decentralized video platform discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class OdyseePlatform(BasePlatform):
    """Odysee (LBRY) platform for decentralized video profile discovery."""

    name = "odysee"
    base_url = "https://odysee.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 35

    async def check_username(self, username: str) -> bool | None:
        """Check if an Odysee channel exists."""
        url = f"https://odysee.com/@{quote(username)}"
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    if username.lower() in text.lower():
                        return True
                    return None
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Odysee users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape an Odysee profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://odysee.com/@{quote(username)}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None

        return self._parse_profile(html, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Odysee profile from HTML/meta tags."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        follower_count = None
        fc_match = re.search(r"([\d,.]+)\s*[Ff]ollowers", html_text)
        if fc_match:
            try:
                follower_count = int(fc_match.group(1).replace(",", ""))
            except ValueError:
                pass

        if not display_name and not bio:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            follower_count=follower_count,
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
        """Extract Odysee username from a URL."""
        match = re.search(r"odysee\.com/@([^/?:]+)", url)
        return match.group(1) if match else None

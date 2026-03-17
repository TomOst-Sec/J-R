"""Steam platform module — gaming profile discovery."""

from __future__ import annotations

import logging
import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class SteamPlatform(BasePlatform):
    """Steam platform for gaming profile discovery."""

    name = "steam"
    base_url = "https://steamcommunity.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 45

    async def check_username(self, username: str) -> bool | None:
        """Check if a Steam username exists."""
        url = f"https://steamcommunity.com/id/{username}"
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    if "The specified profile could not be found" in text:
                        return False
                    return True
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Steam users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Steam profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://steamcommunity.com/id/{username}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile(text, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Steam profile from HTML/meta tags."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        # Try to extract real name and location from profile header
        location = None
        real_name = None
        try:
            from bs4 import BeautifulSoup

            try:
                soup = BeautifulSoup(html_text, "lxml")
            except Exception:
                soup = BeautifulSoup(html_text, "html.parser")

            header = soup.select_one(".profile_header_centered_persona, .header_real_name")
            if header:
                name_el = header.select_one(".header_real_name .header_real_name_in")
                if name_el:
                    real_name = name_el.get_text(strip=True)
            loc_el = soup.select_one(".header_real_name .header_real_name_in + br")
            if loc_el and loc_el.next_sibling:
                loc_text = str(loc_el.next_sibling).strip()
                if loc_text:
                    location = loc_text
        except ImportError:
            # Fallback: regex for real name
            rn_match = re.search(r'class="header_real_name"[^>]*>.*?<bdi>([^<]+)</bdi>', html_text, re.DOTALL)
            if rn_match:
                real_name = rn_match.group(1).strip()

        if not display_name and not bio:
            return None

        # Use real name as display_name if og:title is generic
        if real_name and display_name and "Steam Community" in display_name:
            display_name = real_name

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            location=location,
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
        """Extract Steam username from a URL."""
        match = re.search(r"steamcommunity\.com/id/([^/?]+)", url)
        return match.group(1) if match else None

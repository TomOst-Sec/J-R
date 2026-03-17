"""Snapchat platform module — ephemeral social media discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class SnapchatPlatform(BasePlatform):
    """Snapchat platform for profile discovery."""

    name = "snapchat"
    base_url = "https://www.snapchat.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = True
    priority = 40

    async def check_username(self, username: str) -> bool | None:
        """Check if a Snapchat username exists."""
        url = f"https://www.snapchat.com/add/{quote(username)}"
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    if username.lower() in text.lower():
                        return True
                    return None
        except Exception:
            pass

        html = await self._try_browser(url)
        if html is None:
            return None
        if username.lower() in html.lower():
            return True
        return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Snapchat users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Snapchat profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://www.snapchat.com/add/{quote(username)}"
        html = None
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status == 200:
                    html = await resp.text()
        except Exception:
            pass

        if html is None:
            html = await self._try_browser(profile_url)

        if html is None:
            return None

        return self._parse_profile(html, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Snapchat profile from HTML/meta tags."""
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

    async def _try_browser(self, url: str) -> str | None:
        """Attempt to load a page via Playwright browser."""
        if self.browser is None:
            return None
        try:
            page = await self.browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            html = await page.content()
            await page.close()
            return html
        except Exception:
            return None

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
        """Extract Snapchat username from a URL."""
        match = re.search(r"snapchat\.com/add/([^/?]+)", url)
        return match.group(1) if match else None

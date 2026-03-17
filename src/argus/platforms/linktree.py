"""Linktree platform module — social link aggregation."""

from __future__ import annotations

import logging
import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class LinktreePlatform(BasePlatform):
    """Linktree platform for social link discovery."""

    name = "linktree"
    base_url = "https://linktr.ee"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 85

    async def check_username(self, username: str) -> bool | None:
        """Check if a Linktree username exists."""
        url = f"https://linktr.ee/{username}"
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
        """Search for Linktree users — returns empty (no public search)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Linktree profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://linktr.ee/{username}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile(text, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Linktree profile from HTML."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        # Extract all links from the page — this is the high-value data
        links: list[str] = []
        try:
            from bs4 import BeautifulSoup

            try:
                soup = BeautifulSoup(html_text, "lxml")
            except Exception:
                soup = BeautifulSoup(html_text, "html.parser")

            for anchor in soup.find_all("a", href=True):
                href = str(anchor["href"])
                # Skip internal linktree links and javascript
                if (
                    href.startswith("http")
                    and "linktr.ee" not in href
                    and "linktree.com" not in href
                ):
                    links.append(href)
        except ImportError:
            # Fallback: regex extraction
            for m in re.finditer(r'href="(https?://[^"]+)"', html_text):
                href = m.group(1)
                if "linktr.ee" not in href and "linktree.com" not in href:
                    links.append(href)

        if not display_name and not bio and not links:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            links=links,
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
        """Extract Linktree username from a URL."""
        match = re.search(r"linktr\.ee/([^/?]+)", url)
        return match.group(1) if match else None

"""Reusable mixins for fast platform implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

if TYPE_CHECKING:
    pass


class JSONAPIPlatform(BasePlatform):
    """Mixin for platforms with simple JSON REST APIs.

    Subclasses define:
        api_url_template: str  — format string with {username}
        name, base_url, priority, etc.
    """

    api_url_template: str = ""
    username_url_template: str = ""

    async def check_username(self, username: str) -> bool | None:
        url = self.api_url_template.format(username=username)
        try:
            async with self.session.get(url) as resp:
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
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = self._extract_username(url)
        if not username:
            return None
        api_url = self.api_url_template.format(username=username)
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return self._parse_api_profile(username, data)
        except Exception:
            return None

    def _parse_api_profile(self, username: str, data: dict) -> ProfileData | None:
        """Override this to extract profile fields from API JSON."""
        return ProfileData(username=username, raw_json=data)

    def _extract_username(self, url: str) -> str | None:
        """Extract username from URL. Override for custom patterns."""
        domain = self.base_url.replace("https://", "").replace("http://", "")
        pattern = rf"{re.escape(domain)}/([^/?#]+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None


class HTMLScrapePlatform(BasePlatform):
    """Mixin for platforms where we scrape HTML profile pages.

    Subclasses define:
        profile_url_template: str  — format string with {username}
    """

    profile_url_template: str = ""

    async def check_username(self, username: str) -> bool | None:
        url = self.profile_url_template.format(username=username)
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
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
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = self._extract_username(url)
        if not username:
            return None
        profile_url = self.profile_url_template.format(username=username)
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                return self._parse_html_profile(username, html)
        except Exception:
            return None

    def _parse_html_profile(self, username: str, html: str) -> ProfileData | None:
        """Override this to extract profile fields from HTML."""
        display_name = self._extract_meta(html, "og:title")
        bio = self._extract_meta(html, "og:description")
        photo = self._extract_meta(html, "og:image")
        if not display_name and not bio:
            return None
        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo,
        )

    def _extract_username(self, url: str) -> str | None:
        domain = self.base_url.replace("https://", "").replace("http://", "")
        pattern = rf"{re.escape(domain)}/([^/?#]+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_meta(html: str, prop: str) -> str | None:
        pattern = rf'<meta\s+(?:property|name)="{re.escape(prop)}"\s+content="([^"]*)"'
        m = re.search(pattern, html)
        if m:
            return m.group(1)
        pattern = rf'content="([^"]*)"\s+(?:property|name)="{re.escape(prop)}"'
        m = re.search(pattern, html)
        return m.group(1) if m else None

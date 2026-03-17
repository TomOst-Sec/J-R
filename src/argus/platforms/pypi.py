"""PyPI platform module using public pages."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_USERNAME_RE = re.compile(r"pypi\.org/user/([^/?#]+)")


class PyPIPlatform(BasePlatform):
    """PyPI platform using public user pages (HTML only, no JSON API for users)."""

    name = "pypi"
    base_url = "https://pypi.org"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 50

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{self.base_url}/user/{username}/",
                allow_redirects=True,
            ) as resp:
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
        # PyPI has no name-based user search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{self.base_url}/user/{username}/",
                headers={"Accept": "text/html"},
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                display_name = _extract_display_name(html)
                bio = _extract_meta(html, "og:description")
                avatar = _extract_avatar(html)
                return ProfileData(
                    username=username,
                    display_name=display_name,
                    bio=bio,
                    profile_photo_url=avatar,
                    links=[f"{self.base_url}/user/{username}/"],
                    raw_json={"source": "html_scrape"},
                )
        except Exception:
            return None


def _extract_display_name(html: str) -> str | None:
    """Extract display name from PyPI user page."""
    match = re.search(r"<h1[^>]*class=[\"']?page-title[\"']?[^>]*>([^<]+)</h1>", html)
    if match:
        name = match.group(1).strip()
        return name if name else None
    return None


def _extract_avatar(html: str) -> str | None:
    """Extract avatar URL from PyPI user page."""
    match = re.search(r'<img[^>]*class=["\'][^"\']*user-avatar[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', html)
    if match:
        return match.group(1)
    return None


def _extract_meta(html: str, property_name: str) -> str | None:
    """Extract an og: meta tag value from HTML."""
    pattern = re.compile(
        rf'<meta[^>]*property=["\']?{re.escape(property_name)}["\']?[^>]*content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    match = pattern.search(html)
    if match:
        value = match.group(1).strip()
        return value if value else None
    return None


def _extract_username(url: str) -> str | None:
    """Extract username from a PyPI user URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

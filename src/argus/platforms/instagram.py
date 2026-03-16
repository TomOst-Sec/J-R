"""Instagram platform module — best-effort public data extraction."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class InstagramPlatform(BasePlatform):
    """Instagram platform with public HTML/meta tag extraction."""

    name = "instagram"
    base_url = "https://www.instagram.com"
    rate_limit_per_minute = 10
    requires_auth = False
    requires_playwright = True
    priority = 75

    async def check_username(self, username: str) -> bool | None:
        """Check if an Instagram username exists."""
        url = f"https://www.instagram.com/{quote(username)}/"
        try:
            async with self.session.get(url, headers=_BROWSER_HEADERS) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    # Check if it's a login wall
                    if "loginForm" in text or "Login" in text[:500]:
                        return None  # Can't determine — login required
                    return True
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Instagram users via public profile URL patterns."""
        # Instagram doesn't have a public search API, so we return empty
        # In real usage, this would use Google dorking or similar
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape an Instagram profile from its public URL."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://www.instagram.com/{quote(username)}/"
        try:
            async with self.session.get(profile_url, headers=_BROWSER_HEADERS) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile_html(text, username)

    def _parse_profile_html(self, html_text: str, username: str) -> ProfileData | None:
        """Extract profile data from Instagram HTML meta tags and embedded JSON."""
        # Try to extract from shared data JSON
        profile = self._try_shared_data(html_text, username)
        if profile:
            return profile

        # Fallback to meta tags
        return self._parse_meta_tags(html_text, username)

    def _try_shared_data(self, html_text: str, username: str) -> ProfileData | None:
        """Try to parse window._sharedData JSON."""
        match = re.search(
            r'window\._sharedData\s*=\s*(\{.*?\});</script>', html_text
        )
        if not match:
            return None

        try:
            data = json.loads(match.group(1))
            user_data = (
                data.get("entry_data", {})
                .get("ProfilePage", [{}])[0]
                .get("graphql", {})
                .get("user", {})
            )
            if not user_data:
                return None

            return ProfileData(
                username=user_data.get("username", username),
                display_name=user_data.get("full_name"),
                bio=user_data.get("biography"),
                profile_photo_url=user_data.get("profile_pic_url_hd")
                or user_data.get("profile_pic_url"),
                follower_count=user_data.get("edge_followed_by", {}).get("count"),
                following_count=user_data.get("edge_follow", {}).get("count"),
                links=[user_data["external_url"]] if user_data.get("external_url") else [],
                raw_json=user_data,
            )
        except (json.JSONDecodeError, IndexError, KeyError):
            return None

    def _parse_meta_tags(self, html_text: str, username: str) -> ProfileData | None:
        """Extract profile data from OG meta tags."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        # Clean up display_name (often has format "Name (@username)")
        if display_name:
            match = re.match(r"(.+?)\s*\(@\w+\)", display_name)
            if match:
                display_name = match.group(1).strip()

        # Extract follower count from description if present
        follower_count = None
        if bio:
            fc_match = re.search(r"([\d,.]+[KMkm]?)\s*[Ff]ollowers", bio)
            if fc_match:
                follower_count = self._parse_count(fc_match.group(1))

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
        """Extract a meta tag value by property name."""
        pattern = rf'<meta\s+(?:property|name)="{re.escape(property_name)}"\s+content="([^"]*)"'
        match = re.search(pattern, html_text)
        if match:
            return match.group(1)
        # Try reversed attribute order
        pattern = rf'content="([^"]*)"\s+(?:property|name)="{re.escape(property_name)}"'
        match = re.search(pattern, html_text)
        return match.group(1) if match else None

    @staticmethod
    def _parse_count(text: str) -> int | None:
        """Parse follower count strings like '1.2K', '1M', '1,234'."""
        text = text.strip().replace(",", "")
        try:
            if text.upper().endswith("K"):
                return int(float(text[:-1]) * 1000)
            if text.upper().endswith("M"):
                return int(float(text[:-1]) * 1000000)
            return int(text)
        except ValueError:
            return None

    async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]:
        """Scrape content — very limited without login."""
        # Instagram public profiles show very limited content without login
        return []

    @staticmethod
    def _extract_username(url: str) -> str | None:
        """Extract Instagram username from a URL."""
        url = url.rstrip("/")
        if "instagram.com/" in url:
            parts = url.split("instagram.com/")
            if len(parts) > 1:
                username = parts[1].split("/")[0].split("?")[0]
                if username and username not in ("p", "reel", "stories", "explore"):
                    return username
        return None

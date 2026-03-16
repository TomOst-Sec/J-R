"""TikTok platform module — web scraping via embedded JSON."""

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


class TikTokPlatform(BasePlatform):
    """TikTok platform using embedded JSON extraction."""

    name = "tiktok"
    base_url = "https://www.tiktok.com"
    rate_limit_per_minute = 10
    requires_auth = False
    requires_playwright = True
    priority = 60

    async def check_username(self, username: str) -> bool | None:
        """Check if a TikTok username exists."""
        url = f"https://www.tiktok.com/@{quote(username)}"
        try:
            async with self.session.get(url, headers=_BROWSER_HEADERS) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    if f'"uniqueId":"{username}"' in text or f"@{username}" in text:
                        return True
                    # Check meta tags
                    if 'og:title' in text and username.lower() in text.lower():
                        return True
                    return None
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """TikTok has no public search API — return empty."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a TikTok profile from embedded JSON data."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://www.tiktok.com/@{quote(username)}"
        try:
            async with self.session.get(profile_url, headers=_BROWSER_HEADERS) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        # Try to extract from embedded JSON
        profile = self._parse_rehydration_data(text, username)
        if profile:
            return profile

        # Fallback to meta tags
        return self._parse_meta_tags(text, username)

    def _parse_rehydration_data(self, html_text: str, username: str) -> ProfileData | None:
        """Parse __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON."""
        match = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            html_text,
            re.DOTALL,
        )
        if not match:
            # Try SIGI_STATE
            match = re.search(
                r'<script[^>]*id="SIGI_STATE"[^>]*>(.*?)</script>',
                html_text,
                re.DOTALL,
            )
        if not match:
            return None

        try:
            data = json.loads(match.group(1))
            # Navigate to user data (structure varies)
            user_data = self._find_user_data(data, username)
            if not user_data:
                return None

            return ProfileData(
                username=user_data.get("uniqueId", username),
                display_name=user_data.get("nickname"),
                bio=user_data.get("signature"),
                profile_photo_url=user_data.get("avatarLarger") or user_data.get("avatarMedium"),
                follower_count=user_data.get("followerCount"),
                following_count=user_data.get("followingCount"),
                raw_json=user_data,
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _find_user_data(self, data: dict, username: str) -> dict | None:
        """Navigate nested JSON to find user data."""
        # Try common paths
        for path in [
            lambda d: d.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {}),
            lambda d: d.get("UserModule", {}).get("users", {}).get(username, {}),
            lambda d: d.get("webapp.user-detail", {}).get("userInfo", {}).get("user", {}),
        ]:
            try:
                result = path(data)
                if result and isinstance(result, dict) and result.get("uniqueId"):
                    return result
            except (KeyError, TypeError, AttributeError):
                continue
        return None

    def _parse_meta_tags(self, html_text: str, username: str) -> ProfileData | None:
        """Fallback: extract from OG meta tags."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        if not display_name and not bio:
            return None

        # Try to extract follower count from description
        follower_count = None
        if bio:
            fc_match = re.search(r"([\d.]+[KMkm]?)\s*[Ff]ollowers", bio)
            if fc_match:
                follower_count = self._parse_count(fc_match.group(1))

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            follower_count=follower_count,
        )

    async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]:
        """Scrape video descriptions — limited without Playwright."""
        return []

    @staticmethod
    def _extract_meta(html_text: str, prop: str) -> str | None:
        pattern = rf'<meta\s+(?:property|name)="{re.escape(prop)}"\s+content="([^"]*)"'
        match = re.search(pattern, html_text)
        if match:
            return match.group(1)
        pattern = rf'content="([^"]*)"\s+(?:property|name)="{re.escape(prop)}"'
        match = re.search(pattern, html_text)
        return match.group(1) if match else None

    @staticmethod
    def _parse_count(text: str) -> int | None:
        text = text.strip().replace(",", "")
        try:
            if text.upper().endswith("K"):
                return int(float(text[:-1]) * 1000)
            if text.upper().endswith("M"):
                return int(float(text[:-1]) * 1000000)
            return int(float(text))
        except ValueError:
            return None

    @staticmethod
    def _extract_username(url: str) -> str | None:
        match = re.search(r"tiktok\.com/@([^/?]+)", url)
        return match.group(1) if match else None

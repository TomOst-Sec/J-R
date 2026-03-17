"""Matrix platform module — decentralized messaging profile discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class MatrixPlatform(BasePlatform):
    """Matrix platform for decentralized messaging profile discovery."""

    name = "matrix"
    base_url = "https://matrix.to"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 30

    async def check_username(self, username: str) -> bool | None:
        """Check if a Matrix username exists on the matrix.org homeserver."""
        api_url = (
            f"https://matrix.org/_matrix/client/v3/profile/"
            f"@{quote(username)}:matrix.org"
        )
        try:
            async with self.session.get(api_url) as resp:
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
        """Search for Matrix users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Matrix profile via the homeserver API."""
        username = self._extract_username(url)
        if not username:
            return None

        api_url = (
            f"https://matrix.org/_matrix/client/v3/profile/"
            f"@{quote(username)}:matrix.org"
        )
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        return self._parse_profile(data, username)

    def _parse_profile(self, data: dict, username: str) -> ProfileData | None:
        """Parse Matrix profile from API response."""
        display_name = data.get("displayname")
        avatar_mxc = data.get("avatar_url")

        # Convert mxc:// URL to HTTP URL
        photo_url = None
        if avatar_mxc and avatar_mxc.startswith("mxc://"):
            # mxc://matrix.org/AbCdEf -> https://matrix.org/_matrix/media/v3/download/matrix.org/AbCdEf
            parts = avatar_mxc[6:].split("/", 1)
            if len(parts) == 2:
                photo_url = (
                    f"https://matrix.org/_matrix/media/v3/download/"
                    f"{parts[0]}/{parts[1]}"
                )

        if not display_name:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            profile_photo_url=photo_url,
            raw_json=data,
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
        """Extract Matrix username from a URL or @user:server format."""
        # matrix.to/#/@username:matrix.org
        match = re.search(r"matrix\.to/#/@([^:/?]+)", url)
        if match:
            return match.group(1)
        # @username:matrix.org
        match = re.search(r"@([^:/?]+):matrix\.org", url)
        if match:
            return match.group(1)
        # Plain username in URL
        match = re.search(r"matrix\.(?:org|to)/([^/?#]+)", url)
        return match.group(1) if match else None

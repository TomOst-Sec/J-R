"""Discord platform module for Argus OSINT.

Limitations: Discord profiles are not publicly accessible without API/bot access.
This module provides limited capability focused on public server directories
and Google dorking. Most methods return None or empty results by design.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import quote_plus

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_DISCORD_USER_RE = re.compile(r"discord\.com/users/(\d+)")


class _LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href and ("discord" in href or "disboard" in href):
                self.links.append(href)


class DiscordPlatform(BasePlatform):
    """Discord platform — limited to public server directories.

    Discord does not expose user profiles publicly. This module searches
    server directories (disboard.org) and Google for mentions. Most methods
    return None or empty results.
    """

    name = "discord"
    base_url = "https://discord.com"
    rate_limit_per_minute = 10
    requires_auth = False
    requires_playwright = False
    priority = 30

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _USER_AGENT}

    async def check_username(self, username: str) -> bool | None:
        """Cannot determine Discord username existence without API access."""
        return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search Google for Discord mentions of a name."""
        query = f'site:discord.com OR site:disboard.org "{name}"'
        url = f"https://www.google.com/search?q={quote_plus(query)}&num=10"
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception:
            return []

        parser = _LinkExtractor()
        parser.feed(html)

        seen: set[str] = set()
        results: list[CandidateProfile] = []
        for link in parser.links:
            match = _DISCORD_USER_RE.search(link)
            if match:
                user_id = match.group(1)
                if user_id not in seen:
                    seen.add(user_id)
                    results.append(
                        CandidateProfile(
                            platform=self.name,
                            username=user_id,
                            url=f"{self.base_url}/users/{user_id}",
                        )
                    )
                    if len(results) >= 10:
                        break
        return results

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Discord profiles are not publicly accessible without auth."""
        return None

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        """Discord content is not accessible without bot access."""
        return []

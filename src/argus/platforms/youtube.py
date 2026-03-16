"""YouTube platform module for Argus OSINT."""

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

_HANDLE_RE = re.compile(r"/@([^/?#\"']+)")
_CHANNEL_RE = re.compile(r"/(?:c|channel)/([^/?#\"']+)")


class _MetaParser(HTMLParser):
    """Extract meta tags from HTML."""

    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            d = dict(attrs)
            prop = d.get("property", "") or d.get("name", "")
            content = d.get("content", "")
            if prop and content:
                self.meta[prop] = content


class _ChannelLinkParser(HTMLParser):
    """Extract channel links (/@handle) from HTML."""

    def __init__(self):
        super().__init__()
        self.handles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                match = _HANDLE_RE.search(href)
                if match:
                    self.handles.append(match.group(1))


def _extract_handle(url: str) -> str | None:
    """Extract handle from YouTube URL."""
    match = _HANDLE_RE.search(url)
    if match:
        return match.group(1)
    match = _CHANNEL_RE.search(url)
    if match:
        return match.group(1)
    return None


class YouTubePlatform(BasePlatform):
    """YouTube platform — uses scraping with optional API key."""

    name = "youtube"
    base_url = "https://www.youtube.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 55

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    async def check_username(self, username: str) -> bool | None:
        url = f"{self.base_url}/@{username}"
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
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
        # Scrape-based channel search
        encoded = quote_plus(name)
        url = f"{self.base_url}/results?search_query={encoded}&sp=EgIQAg%3D%3D"
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception:
            return []

        parser = _ChannelLinkParser()
        parser.feed(html)

        seen: set[str] = set()
        results: list[CandidateProfile] = []
        for handle in parser.handles:
            if handle not in seen:
                seen.add(handle)
                results.append(
                    CandidateProfile(
                        platform=self.name,
                        username=handle,
                        url=f"{self.base_url}/@{handle}",
                        exists=True,
                    )
                )
                if len(results) >= 10:
                    break
        return results

    async def scrape_profile(self, url: str) -> ProfileData | None:
        handle = _extract_handle(url)
        if not handle:
            return None

        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None

        parser = _MetaParser()
        parser.feed(html)

        og_title = parser.meta.get("og:title", "")
        og_desc = parser.meta.get("og:description", "")
        og_image = parser.meta.get("og:image", "")

        return ProfileData(
            username=handle,
            display_name=og_title or None,
            bio=og_desc or None,
            profile_photo_url=og_image or None,
            raw_json={"og_title": og_title, "og_description": og_desc, "og_image": og_image},
        )

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        # Content scraping requires JavaScript rendering or API key
        # Basic implementation returns empty — full implementation needs Playwright or API
        return []

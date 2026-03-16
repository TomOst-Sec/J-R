"""YouTube platform module using public page scraping."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig

_BASE_URL = "https://www.youtube.com"
_HANDLE_RE = re.compile(r"youtube\.com/@([^/?#]+)")
_CHANNEL_RE = re.compile(r"youtube\.com/channel/([^/?#]+)")


class YouTubePlatform(BasePlatform):
    """YouTube platform using public page data."""

    name = "youtube"
    base_url = _BASE_URL
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 60

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        super().__init__(session, config)

    async def check_username(self, username: str) -> bool | None:
        url = f"{_BASE_URL}/@{username}"
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if '"channelMetadataRenderer"' in text or '"microformatDataRenderer"' in text:
                        return True
                    return False
                if resp.status == 404:
                    return False
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        # YouTube has no public name search API without API key
        # Would need Google dorking: site:youtube.com "@" "name"
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        handle = _extract_handle(url)
        if not handle:
            return None
        channel_url = f"{_BASE_URL}/@{handle}"
        try:
            async with self.session.get(channel_url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
                return _parse_channel_page(handle, text)
        except Exception:
            return None

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        handle = _extract_handle(url)
        if not handle:
            return []
        videos_url = f"{_BASE_URL}/@{handle}/videos"
        try:
            async with self.session.get(videos_url) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
                return _parse_videos(text, max_items)
        except Exception:
            return []


def _extract_handle(url: str) -> str | None:
    match = _HANDLE_RE.search(url)
    if match:
        return match.group(1)
    match = _CHANNEL_RE.search(url)
    if match:
        return match.group(1)
    return None


def _parse_channel_page(handle: str, html: str) -> ProfileData | None:
    """Extract profile data from YouTube channel page HTML."""
    username = handle

    display_name = _extract_meta(html, "og:title") or _extract_meta(html, "title")
    bio = _extract_meta(html, "og:description") or _extract_meta(html, "description")
    photo_url = _extract_meta(html, "og:image")

    links = []
    channel_url = _extract_meta(html, "og:url")
    if channel_url:
        links.append(channel_url)

    # Try to extract subscriber count from page
    subscriber_match = re.search(r'"subscriberCountText":\s*\{"simpleText":\s*"([^"]+)"', html)
    follower_count = None
    if subscriber_match:
        follower_count = _parse_count(subscriber_match.group(1))

    return ProfileData(
        username=username,
        display_name=display_name,
        bio=bio,
        profile_photo_url=photo_url,
        links=links,
        follower_count=follower_count,
    )


def _parse_videos(html: str, max_items: int) -> list[ContentItem]:
    """Extract video items from YouTube videos page HTML."""
    items = []
    # Find video entries in the page data
    video_pattern = re.compile(
        r'"videoId":\s*"([^"]+)".*?"title":\s*\{"runs":\s*\[\{"text":\s*"([^"]*)"',
        re.DOTALL,
    )
    for match in video_pattern.finditer(html):
        if len(items) >= max_items:
            break
        video_id = match.group(1)
        title = match.group(2)
        items.append(
            ContentItem(
                id=video_id,
                platform="youtube",
                text=title,
                content_type="video",
                url=f"https://www.youtube.com/watch?v={video_id}",
            )
        )
    return items


def _extract_meta(html: str, name: str) -> str | None:
    """Extract content from a meta tag."""
    patterns = [
        re.compile(rf'<meta\s+property="{re.escape(name)}"\s+content="([^"]*)"', re.IGNORECASE),
        re.compile(rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"', re.IGNORECASE),
        re.compile(rf'<meta\s+content="([^"]*)"\s+property="{re.escape(name)}"', re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(html)
        if match:
            return match.group(1)
    return None


def _parse_count(text: str) -> int | None:
    """Parse subscriber count like '1.5M subscribers' to int."""
    text = text.lower().replace(",", "").replace(" subscribers", "").strip()
    try:
        if text.endswith("k"):
            return int(float(text[:-1]) * 1000)
        elif text.endswith("m"):
            return int(float(text[:-1]) * 1_000_000)
        elif text.endswith("b"):
            return int(float(text[:-1]) * 1_000_000_000)
        else:
            return int(text)
    except (ValueError, IndexError):
        return None

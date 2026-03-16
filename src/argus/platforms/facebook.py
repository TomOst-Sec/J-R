"""Facebook platform module for Argus OSINT."""

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

_PROFILE_RE = re.compile(r"facebook\.com/(?!groups/|pages/|watch/)([^/?#\"']+)")
_PROFILE_ID_RE = re.compile(r"facebook\.com/profile\.php\?id=(\d+)")


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            d = dict(attrs)
            prop = d.get("property", "") or d.get("name", "")
            content = d.get("content", "")
            if prop and content:
                self.meta[prop] = content
        elif tag == "title":
            self._in_title = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = data.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False


class _LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href and "facebook.com/" in href:
                self.links.append(href)


def _is_login_wall(html: str) -> bool:
    lower = html.lower()
    return "log in" in lower and ("login_form" in lower or "Log in to Facebook" in html)


def _extract_username(url: str) -> str | None:
    m = _PROFILE_ID_RE.search(url)
    if m:
        return m.group(1)
    m = _PROFILE_RE.search(url)
    if m:
        return m.group(1).rstrip("/")
    return None


def _is_profile_url(url: str) -> bool:
    if "facebook.com/groups/" in url or "facebook.com/pages/" in url:
        return False
    if "facebook.com/watch" in url:
        return False
    return bool(_PROFILE_RE.search(url) or _PROFILE_ID_RE.search(url))


class FacebookPlatform(BasePlatform):
    """Facebook platform — Google dork-based with meta tag extraction."""

    name = "facebook"
    base_url = "https://www.facebook.com"
    rate_limit_per_minute = 10
    requires_auth = False
    requires_playwright = True
    priority = 65

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    async def check_username(self, username: str) -> bool | None:
        url = f"{self.base_url}/{username}"
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status == 404:
                    return False
                if resp.status != 200:
                    return None
                html = await resp.text()
                if _is_login_wall(html):
                    return None
                return True
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        query = f'site:facebook.com "{name}"'
        if location:
            query += f' "{location}"'
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
            if not _is_profile_url(link):
                continue
            username = _extract_username(link)
            if username and username not in seen:
                seen.add(username)
                results.append(
                    CandidateProfile(
                        platform=self.name,
                        username=username,
                        url=f"{self.base_url}/{username}",
                        exists=True,
                    )
                )
                if len(results) >= 10:
                    break
        return results

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None

        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None

        if _is_login_wall(html):
            return None

        parser = _MetaParser()
        parser.feed(html)

        og_title = parser.meta.get("og:title", "")
        og_desc = parser.meta.get("og:description", "")
        og_image = parser.meta.get("og:image", "")

        if not og_title or og_title == "Facebook":
            return None

        return ProfileData(
            username=username,
            display_name=og_title or None,
            bio=og_desc or None,
            profile_photo_url=og_image or None,
            raw_json={"og_title": og_title, "og_description": og_desc},
        )

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        return []

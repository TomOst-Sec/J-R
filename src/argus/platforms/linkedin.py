"""LinkedIn platform module for Argus OSINT."""

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

_LINKEDIN_PROFILE_RE = re.compile(r"linkedin\.com/in/([^/?#\"']+)")


class _MetaTagParser(HTMLParser):
    """Extract meta tag content from HTML."""

    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            attr_dict = dict(attrs)
            prop = attr_dict.get("property", "") or attr_dict.get("name", "")
            content = attr_dict.get("content", "")
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
    """Extract LinkedIn profile URLs from HTML."""

    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href and "linkedin.com/in/" in href:
                self.links.append(href)


def _extract_username_from_url(url: str) -> str | None:
    match = _LINKEDIN_PROFILE_RE.search(url)
    return match.group(1).rstrip("/") if match else None


def _is_login_wall(html: str) -> bool:
    """Detect LinkedIn login/auth wall."""
    indicators = ["authwall", "Sign In", "Join LinkedIn", "sign-in"]
    lower = html.lower()
    return any(ind.lower() in lower for ind in indicators)


class LinkedInPlatform(BasePlatform):
    """LinkedIn platform — uses direct HTTP and Google dorking."""

    name = "linkedin"
    base_url = "https://www.linkedin.com"
    rate_limit_per_minute = 10
    requires_auth = False
    requires_playwright = True
    priority = 85

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    async def check_username(self, username: str) -> bool | None:
        url = f"{self.base_url}/in/{username}"
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    if _is_login_wall(text):
                        return None
                    return True
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        query = f'site:linkedin.com/in/ "{name}"'
        if location:
            query += f' "{location}"'
        encoded = quote_plus(query)

        url = f"https://www.google.com/search?q={encoded}&num=10"
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
            username = _extract_username_from_url(link)
            if username and username not in seen:
                seen.add(username)
                results.append(
                    CandidateProfile(
                        platform=self.name,
                        username=username,
                        url=f"{self.base_url}/in/{username}",
                        exists=True,
                    )
                )
                if len(results) >= 10:
                    break

        return results

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username_from_url(url)
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

        parser = _MetaTagParser()
        parser.feed(html)

        og_title = parser.meta.get("og:title", "")
        og_desc = parser.meta.get("og:description", "")
        og_image = parser.meta.get("og:image", "")

        # Extract display name from og:title: "John Doe - Software Engineer - Company"
        display_name = og_title.split(" - ")[0].strip() if og_title else None

        # Use headline as bio (from og:title after the name)
        parts = og_title.split(" - ", 1)
        bio = parts[1].strip() if len(parts) > 1 else og_desc or None

        # Remove " | LinkedIn" suffix from bio
        if bio and bio.endswith(" | LinkedIn"):
            bio = bio[: -len(" | LinkedIn")]

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=og_image or None,
            raw_json={"og_title": og_title, "og_description": og_desc, "og_image": og_image},
        )

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        # LinkedIn public profiles show very limited activity
        # Full content scraping would require Playwright + login
        return []

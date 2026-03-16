"""Medium platform module — blog/article discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


class MediumPlatform(BasePlatform):
    """Medium platform for blog/article discovery."""

    name = "medium"
    base_url = "https://medium.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 45

    async def check_username(self, username: str) -> bool | None:
        """Check if a Medium username exists."""
        url = f"https://medium.com/@{quote(username)}"
        try:
            async with self.session.get(url, allow_redirects=True) as resp:
                if resp.status == 404:
                    return False
                if resp.status == 200:
                    text = await resp.text()
                    # Verify it's a real profile page
                    if f"@{username}" in text or "og:profile" in text:
                        return True
                    return None
                return None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Medium users — returns empty (no public search API)."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Medium profile page."""
        username = self._extract_username(url)
        if not username:
            return None

        profile_url = f"https://medium.com/@{quote(username)}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile(text, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Medium profile from HTML/meta tags."""
        display_name = self._extract_meta(html_text, "og:title")
        bio = self._extract_meta(html_text, "og:description")
        photo_url = self._extract_meta(html_text, "og:image")

        # Try to extract follower count from page text
        follower_count = None
        fc_match = re.search(r"([\d,.]+)\s*[Ff]ollowers", html_text)
        if fc_match:
            try:
                follower_count = int(fc_match.group(1).replace(",", ""))
            except ValueError:
                pass

        if not display_name and not bio:
            return None

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            profile_photo_url=photo_url,
            follower_count=follower_count,
        )

    async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]:
        """Scrape articles from a Medium profile."""
        username = self._extract_username(url)
        if not username:
            return []

        profile_url = f"https://medium.com/@{quote(username)}"
        try:
            async with self.session.get(profile_url) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
        except Exception:
            return []

        return self._parse_articles(text, max_items)

    def _parse_articles(self, html_text: str, max_items: int) -> list[ContentItem]:
        """Parse article links from Medium profile HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "lxml")
        except ImportError:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "html.parser")

        items = []
        for article in soup.select("article, div[data-post-id]")[:max_items]:
            title_el = article.select_one("h2, h3")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            subtitle_el = article.select_one("h3, p.subtitle, div.subtitle")
            subtitle = subtitle_el.get_text(strip=True) if subtitle_el else ""
            text = f"{title} — {subtitle}" if subtitle else title

            link_el = article.select_one("a[href*='medium.com']")
            article_url = None
            article_id = str(len(items))
            if link_el:
                href = link_el.get("href", "")
                article_url = str(href)
                # Extract post ID from URL
                id_match = re.search(r"-([a-f0-9]+)$", href)
                if id_match:
                    article_id = id_match.group(1)

            items.append(
                ContentItem(
                    id=article_id,
                    platform=self.name,
                    text=text,
                    content_type="article",
                    url=article_url,
                )
            )

        return items

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
        """Extract Medium username from a URL."""
        match = re.search(r"medium\.com/@([^/?]+)", url)
        return match.group(1) if match else None

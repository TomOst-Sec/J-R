"""Telegram platform module — username probing via t.me."""

from __future__ import annotations

import re
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform


class TelegramPlatform(BasePlatform):
    """Telegram platform via t.me public pages."""

    name = "telegram"
    base_url = "https://t.me"
    rate_limit_per_minute = 15
    requires_auth = False
    requires_playwright = False
    priority = 35

    async def check_username(self, username: str) -> bool | None:
        """Check if a Telegram username exists via t.me page."""
        url = f"https://t.me/{quote(username)}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
                if "tgme_page_extra" in text or f"@{username}" in text.lower():
                    return True
                if "you can contact" not in text.lower():
                    return False
                return True
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Telegram has no public name search."""
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Telegram profile from t.me page."""
        username = self._extract_username(url)
        if not username:
            return None

        try:
            async with self.session.get(f"https://t.me/{quote(username)}") as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        except Exception:
            return None

        return self._parse_profile(text, username)

    def _parse_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse Telegram profile from t.me HTML."""
        display_name = None
        name_match = re.search(
            r'class="tgme_page_title[^"]*"[^>]*><span[^>]*>([^<]+)', html_text
        )
        if name_match:
            display_name = name_match.group(1).strip()

        bio = None
        bio_match = re.search(
            r'class="tgme_page_description[^"]*"[^>]*>([^<]+)', html_text
        )
        if bio_match:
            bio = bio_match.group(1).strip()

        photo_url = None
        photo_match = re.search(
            r'class="tgme_page_photo[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
            html_text,
            re.DOTALL,
        )
        if photo_match:
            photo_url = photo_match.group(1)

        # Member count for channels/groups
        follower_count = None
        member_match = re.search(
            r'class="tgme_page_extra"[^>]*>([^<]+)', html_text
        )
        if member_match:
            extra = member_match.group(1).strip()
            count_match = re.search(r"([\d\s]+)\s*(?:members|subscribers)", extra)
            if count_match:
                try:
                    follower_count = int(count_match.group(1).replace(" ", ""))
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
        """Scrape public channel posts from t.me/s/ preview."""
        username = self._extract_username(url)
        if not username:
            return []

        # Try public channel preview
        try:
            async with self.session.get(f"https://t.me/s/{quote(username)}") as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
        except Exception:
            return []

        return self._parse_channel_posts(text, max_items)

    def _parse_channel_posts(self, html_text: str, max_items: int) -> list[ContentItem]:
        """Parse channel posts from t.me/s/ preview page."""
        items = []
        # Find message text blocks
        for match in re.finditer(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            html_text,
            re.DOTALL,
        ):
            if len(items) >= max_items:
                break
            text = re.sub(r"<[^>]+>", " ", match.group(1)).strip()
            text = re.sub(r"\s+", " ", text)
            if text:
                items.append(
                    ContentItem(
                        id=str(len(items)),
                        platform=self.name,
                        text=text[:500],
                        content_type="post",
                    )
                )
        return items

    @staticmethod
    def _extract_username(url: str) -> str | None:
        """Extract Telegram username from URL."""
        match = re.search(r"t\.me/(?:s/)?([^/?]+)", url)
        if match:
            username = match.group(1)
            if username not in ("share", "addstickers", "joinchat"):
                return username
        return None

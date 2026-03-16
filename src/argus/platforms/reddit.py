"""Reddit platform module for Argus OSINT."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

if TYPE_CHECKING:
    pass

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_USERNAME_RE = re.compile(r"/user/([^/?#]+)")


class RedditPlatform(BasePlatform):
    """Reddit platform — uses public JSON API."""

    name = "reddit"
    base_url = "https://www.reddit.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 70

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _USER_AGENT}

    def _extract_username(self, url: str) -> str | None:
        match = _USERNAME_RE.search(url)
        return match.group(1) if match else None

    async def check_username(self, username: str) -> bool | None:
        url = f"{self.base_url}/user/{username}/about.json"
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status == 404:
                    return False
                if resp.status != 200:
                    return None
                data = await resp.json()
                # Check for suspended accounts
                user_data = data.get("data", {})
                if user_data.get("is_suspended"):
                    return False
                return True
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        # Reddit has no public name search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = self._extract_username(url)
        if not username:
            return None

        api_url = f"{self.base_url}/user/{username}/about.json"
        try:
            async with self.session.get(api_url, headers=self._headers()) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        user_data = data.get("data", {})
        if user_data.get("is_suspended"):
            return None

        # Extract bio from subreddit description
        subreddit = user_data.get("subreddit", {})
        bio = subreddit.get("public_description") or None

        # Parse join date
        created_utc = user_data.get("created_utc")
        join_date = (
            datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
        )

        return ProfileData(
            username=user_data.get("name", username),
            display_name=user_data.get("name"),
            bio=bio,
            profile_photo_url=user_data.get("icon_img"),
            join_date=join_date,
            follower_count=None,
            following_count=None,
            raw_json=user_data,
        )

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        username = self._extract_username(url)
        if not username:
            return []

        api_url = f"{self.base_url}/user/{username}.json?limit={max_items}&sort=new"
        try:
            async with self.session.get(api_url, headers=self._headers()) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []

        items: list[ContentItem] = []
        children = data.get("data", {}).get("children", [])

        for child in children:
            kind = child.get("kind", "")
            item_data = child.get("data", {})

            # Determine content type and text
            if kind == "t3":  # Post
                title = item_data.get("title", "")
                selftext = item_data.get("selftext", "")
                text = f"{title}\n{selftext}".strip() if selftext else title
                content_type = "post"
            elif kind == "t1":  # Comment
                text = item_data.get("body", "")
                content_type = "comment"
            else:
                continue

            created_utc = item_data.get("created_utc")
            timestamp = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
            )

            permalink = item_data.get("permalink", "")
            item_url = f"{self.base_url}{permalink}" if permalink else None

            items.append(
                ContentItem(
                    id=item_data.get("name", ""),
                    platform=self.name,
                    text=text,
                    timestamp=timestamp,
                    content_type=content_type,
                    url=item_url,
                    engagement={
                        "ups": item_data.get("ups", 0),
                        "num_comments": item_data.get("num_comments", 0),
                    },
                )
            )

        return items

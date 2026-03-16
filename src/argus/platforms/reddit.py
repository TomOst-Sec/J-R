"""Reddit platform module using public JSON API."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

_USER_AGENT = "argus-osint:v0.1.0 (platform research tool)"
_USERNAME_RE = re.compile(r"reddit\.com/u(?:ser)?/([^/?#]+)")


class RedditPlatform(BasePlatform):
    """Reddit platform using the public JSON API (no auth required)."""

    name = "reddit"
    base_url = "https://www.reddit.com"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 70

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _USER_AGENT}

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{self.base_url}/user/{username}/about.json",
                headers=self._headers(),
            ) as resp:
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
        # Reddit has no name-based search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{self.base_url}/user/{username}/about.json",
                headers=self._headers(),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                user = data.get("data", data)
                subreddit = user.get("subreddit", {})

                join_date = None
                created_utc = user.get("created_utc")
                if created_utc:
                    join_date = datetime.fromtimestamp(created_utc, tz=timezone.utc)

                icon_img = user.get("icon_img", "")
                # Strip Reddit's query params from icon URL
                if icon_img and "?" in icon_img:
                    icon_img = icon_img.split("?")[0]

                return ProfileData(
                    username=user.get("name", username),
                    bio=subreddit.get("public_description") or None,
                    profile_photo_url=icon_img or None,
                    join_date=join_date,
                    raw_json=user,
                )
        except Exception:
            return None

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        username = _extract_username(url)
        if not username:
            return []
        try:
            async with self.session.get(
                f"{self.base_url}/user/{username}.json",
                headers=self._headers(),
                params={"limit": str(max_items), "sort": "new"},
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                children = data.get("data", {}).get("children", [])
                items = []
                for child in children:
                    kind = child.get("kind", "")
                    entry = child.get("data", {})

                    if kind == "t3":  # post
                        text_parts = []
                        if entry.get("title"):
                            text_parts.append(entry["title"])
                        if entry.get("selftext"):
                            text_parts.append(entry["selftext"])
                        text = "\n".join(text_parts)
                        content_type = "post"
                    elif kind == "t1":  # comment
                        text = entry.get("body", "")
                        content_type = "comment"
                    else:
                        continue

                    timestamp = None
                    created_utc = entry.get("created_utc")
                    if created_utc:
                        timestamp = datetime.fromtimestamp(
                            created_utc, tz=timezone.utc
                        )

                    items.append(
                        ContentItem(
                            id=entry.get("name", entry.get("id", "")),
                            platform=self.name,
                            text=text,
                            timestamp=timestamp,
                            content_type=content_type,
                            url=entry.get("permalink"),
                            engagement={
                                "ups": entry.get("ups", 0),
                                "num_comments": entry.get("num_comments", 0),
                            },
                        )
                    )
                return items
        except Exception:
            return []


def _extract_username(url: str) -> str | None:
    """Extract username from a Reddit profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

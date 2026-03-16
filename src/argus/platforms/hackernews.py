"""HackerNews platform module for Argus OSINT."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import StringIO
from urllib.parse import parse_qs, urlparse

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

_FIREBASE_API = "https://hacker-news.firebaseio.com/v0"
_ALGOLIA_API = "https://hn.algolia.com/api/v1"


class _HTMLStripper(HTMLParser):
    """Simple HTML tag stripper."""

    def __init__(self):
        super().__init__()
        self._text = StringIO()

    def handle_data(self, data: str) -> None:
        self._text.write(data)

    def get_text(self) -> str:
        return self._text.getvalue().strip()


def _strip_html(html: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


def _extract_username(url: str) -> str | None:
    """Extract username from HN URL like https://news.ycombinator.com/user?id=pg."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "id" in params:
        return params["id"][0]
    # Try path-based: /user/pg
    match = re.search(r"/user/([^/?#]+)", parsed.path)
    return match.group(1) if match else None


class HackerNewsPlatform(BasePlatform):
    """HackerNews platform — uses Firebase and Algolia APIs."""

    name = "hackernews"
    base_url = "https://news.ycombinator.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 60

    async def check_username(self, username: str) -> bool | None:
        url = f"{_FIREBASE_API}/user/{username}.json"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data is not None
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        url = f"{_ALGOLIA_API}/search?query={name}&tags=(story,comment)"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []

        seen: set[str] = set()
        results: list[CandidateProfile] = []
        for hit in data.get("hits", []):
            author = hit.get("author", "")
            if author and author not in seen:
                seen.add(author)
                results.append(
                    CandidateProfile(
                        platform=self.name,
                        username=author,
                        url=f"{self.base_url}/user?id={author}",
                        exists=True,
                    )
                )
        return results

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None

        api_url = f"{_FIREBASE_API}/user/{username}.json"
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        if data is None:
            return None

        # Parse about field (may contain HTML)
        about = data.get("about", "")
        bio = _strip_html(about) if about else None

        # Parse creation timestamp
        created = data.get("created")
        join_date = datetime.fromtimestamp(created, tz=timezone.utc) if created else None

        return ProfileData(
            username=data.get("id", username),
            display_name=data.get("id"),
            bio=bio,
            profile_photo_url=None,  # HN has no profile photos
            join_date=join_date,
            raw_json=data,
        )

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        username = _extract_username(url)
        if not username:
            return []

        api_url = (
            f"{_ALGOLIA_API}/search?tags=author_{username}&hitsPerPage={max_items}"
        )
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []

        items: list[ContentItem] = []
        for hit in data.get("hits", []):
            tags = hit.get("_tags", [])

            # Determine type and text
            if "story" in tags or "show_hn" in tags or "ask_hn" in tags:
                text = hit.get("title", "") or ""
                story_text = hit.get("story_text", "")
                if story_text:
                    text = f"{text}\n{_strip_html(story_text)}".strip()
                content_type = "story"
            elif "comment" in tags:
                comment_text = hit.get("comment_text", "") or ""
                text = _strip_html(comment_text) if comment_text else ""
                content_type = "comment"
            else:
                text = hit.get("title", "") or ""
                content_type = "story"

            # Parse timestamp
            created_str = hit.get("created_at", "")
            timestamp = None
            if created_str:
                try:
                    timestamp = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            item_url = hit.get("url") or None
            if not item_url:
                obj_id = hit.get("objectID", "")
                if obj_id:
                    item_url = f"{self.base_url}/item?id={obj_id}"

            items.append(
                ContentItem(
                    id=hit.get("objectID", ""),
                    platform=self.name,
                    text=text,
                    timestamp=timestamp,
                    content_type=content_type,
                    url=item_url,
                    engagement={
                        "points": hit.get("points", 0),
                        "num_comments": hit.get("num_comments", 0),
                    },
                )
            )

        return items

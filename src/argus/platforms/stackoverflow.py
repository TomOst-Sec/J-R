"""Stack Overflow platform module — Stack Exchange API scraper."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)

_API_BASE = "https://api.stackexchange.com/2.3"


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


class StackOverflowPlatform(BasePlatform):
    """Stack Overflow platform using Stack Exchange API."""

    name = "stackoverflow"
    base_url = "https://stackoverflow.com"
    rate_limit_per_minute = 25
    requires_auth = False
    requires_playwright = False
    priority = 50

    async def _get_json(self, url: str) -> tuple[Any, int]:
        """Make API request with gzip handling."""
        headers = {"Accept": "application/json"}
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                remaining = data.get("quota_remaining")
                if remaining is not None and remaining < 50:
                    logger.warning("Stack Exchange quota low: %s remaining", remaining)
                return data, resp.status
            return None, resp.status

    async def check_username(self, username: str) -> bool | None:
        """Stack Overflow doesn't have unique usernames — always return None."""
        return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Stack Overflow users by name."""
        url = f"{_API_BASE}/users?inname={quote(name)}&site=stackoverflow&sort=reputation&pagesize=10"
        data, status = await self._get_json(url)
        if status != 200 or data is None:
            return []

        candidates = []
        for item in data.get("items", [])[:10]:
            # Filter by location if provided
            if location and item.get("location"):
                if location.lower() not in item["location"].lower():
                    continue

            candidates.append(
                CandidateProfile(
                    platform=self.name,
                    username=item.get("display_name", ""),
                    url=item.get("link", f"https://stackoverflow.com/users/{item.get('user_id', '')}"),
                    exists=True,
                )
            )
        return candidates

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Stack Overflow user profile."""
        user_id = self._extract_user_id(url)
        if not user_id:
            return None

        api_url = f"{_API_BASE}/users/{user_id}?site=stackoverflow&filter=!nNPvSNVZJS"
        data, status = await self._get_json(api_url)
        if status != 200 or data is None:
            return None

        items = data.get("items", [])
        if not items:
            return None

        user = items[0]
        bio = _strip_html(user.get("about_me", "")) if user.get("about_me") else None

        join_date = None
        if user.get("creation_date"):
            try:
                join_date = datetime.fromtimestamp(user["creation_date"], tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                pass

        links = []
        if user.get("website_url"):
            links.append(user["website_url"])

        return ProfileData(
            username=user.get("display_name", ""),
            display_name=user.get("display_name"),
            bio=bio,
            location=user.get("location"),
            profile_photo_url=user.get("profile_image"),
            links=links,
            join_date=join_date,
            raw_json=user,
        )

    async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]:
        """Scrape questions and answers from a user's profile."""
        user_id = self._extract_user_id(url)
        if not user_id:
            return []

        items = []

        # Fetch answers
        ans_url = f"{_API_BASE}/users/{user_id}/answers?site=stackoverflow&sort=votes&pagesize={min(max_items, 30)}&filter=withbody"
        data, status = await self._get_json(ans_url)
        if status == 200 and data:
            for ans in data.get("items", []):
                text = _strip_html(ans.get("body", ""))
                timestamp = None
                if ans.get("creation_date"):
                    try:
                        timestamp = datetime.fromtimestamp(ans["creation_date"], tz=timezone.utc)
                    except (ValueError, TypeError, OSError):
                        pass
                engagement = {"score": ans.get("score", 0)}
                if ans.get("is_accepted"):
                    engagement["accepted"] = True
                items.append(
                    ContentItem(
                        id=str(ans.get("answer_id", len(items))),
                        platform=self.name,
                        text=text[:500],  # Truncate long answers
                        timestamp=timestamp,
                        content_type="answer",
                        url=f"https://stackoverflow.com/a/{ans.get('answer_id', '')}",
                        engagement=engagement,
                    )
                )

        # Fetch questions
        remaining = max_items - len(items)
        if remaining > 0:
            q_url = f"{_API_BASE}/users/{user_id}/questions?site=stackoverflow&sort=votes&pagesize={min(remaining, 20)}&filter=withbody"
            data, status = await self._get_json(q_url)
            if status == 200 and data:
                for q in data.get("items", []):
                    title = q.get("title", "")
                    body = _strip_html(q.get("body", ""))
                    text = f"{title}\n{body}"[:500]
                    timestamp = None
                    if q.get("creation_date"):
                        try:
                            timestamp = datetime.fromtimestamp(q["creation_date"], tz=timezone.utc)
                        except (ValueError, TypeError, OSError):
                            pass
                    items.append(
                        ContentItem(
                            id=str(q.get("question_id", len(items))),
                            platform=self.name,
                            text=text,
                            timestamp=timestamp,
                            content_type="question",
                            url=q.get("link", ""),
                            engagement={"score": q.get("score", 0), "views": q.get("view_count", 0)},
                        )
                    )

        return items[:max_items]

    @staticmethod
    def _extract_user_id(url: str) -> str | None:
        """Extract user ID from a Stack Overflow URL."""
        match = re.search(r"/users/(\d+)", url)
        return match.group(1) if match else None

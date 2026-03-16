"""GitHub platform module using public REST API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig

_API_BASE = "https://api.github.com"
_USERNAME_RE = re.compile(r"github\.com/([^/?#]+)")


class GitHubPlatform(BasePlatform):
    """GitHub platform using the public REST API (no auth required)."""

    name = "github"
    base_url = "https://github.com"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 80

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        super().__init__(session, config)
        self._rate_limit_remaining: int | None = None

    def _update_rate_limit(self, headers: dict) -> None:
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining is not None:
            self._rate_limit_remaining = int(remaining)

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(f"{_API_BASE}/users/{username}") as resp:
                self._update_rate_limit(resp.headers)
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
        query = name
        if location:
            query += f"+location:{location}"
        try:
            async with self.session.get(
                f"{_API_BASE}/search/users", params={"q": query}
            ) as resp:
                self._update_rate_limit(resp.headers)
                if resp.status != 200:
                    return []
                data = await resp.json()
                items = data.get("items", [])[:10]
                return [
                    CandidateProfile(
                        platform=self.name,
                        username=item["login"],
                        url=item["html_url"],
                    )
                    for item in items
                ]
        except Exception:
            return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(f"{_API_BASE}/users/{username}") as resp:
                self._update_rate_limit(resp.headers)
                if resp.status != 200:
                    return None
                data = await resp.json()
                links = []
                if data.get("blog"):
                    links.append(data["blog"])
                if data.get("html_url"):
                    links.append(data["html_url"])
                join_date = None
                if data.get("created_at"):
                    join_date = datetime.fromisoformat(
                        data["created_at"].replace("Z", "+00:00")
                    )
                return ProfileData(
                    username=data.get("login", username),
                    display_name=data.get("name"),
                    bio=data.get("bio"),
                    location=data.get("location"),
                    profile_photo_url=data.get("avatar_url"),
                    links=links,
                    join_date=join_date,
                    follower_count=data.get("followers"),
                    following_count=data.get("following"),
                    raw_json=data,
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
                f"{_API_BASE}/users/{username}/repos",
                params={"sort": "updated", "per_page": str(max_items)},
            ) as resp:
                self._update_rate_limit(resp.headers)
                if resp.status != 200:
                    return []
                repos = await resp.json()
                items = []
                for repo in repos:
                    text_parts = [repo.get("name", "")]
                    if repo.get("description"):
                        text_parts.append(repo["description"])
                    timestamp = None
                    if repo.get("pushed_at"):
                        timestamp = datetime.fromisoformat(
                            repo["pushed_at"].replace("Z", "+00:00")
                        )
                    items.append(
                        ContentItem(
                            id=str(repo.get("id", "")),
                            platform=self.name,
                            text=" — ".join(text_parts),
                            timestamp=timestamp,
                            content_type="repo",
                            url=repo.get("html_url"),
                            engagement={
                                "stars": repo.get("stargazers_count", 0),
                                "forks": repo.get("forks_count", 0),
                            },
                        )
                    )
                return items
        except Exception:
            return []


def _extract_username(url: str) -> str | None:
    match = _USERNAME_RE.search(url)
    return match.group(1) if match else None

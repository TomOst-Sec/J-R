"""Wikipedia platform module using public REST and MediaWiki APIs."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_REST_BASE = "https://en.wikipedia.org/api/rest_v1"
_MW_BASE = "https://en.wikipedia.org/w/api.php"
_TITLE_RE = re.compile(r"wikipedia\.org/wiki/([^?#]+)")


class WikipediaPlatform(BasePlatform):
    """Wikipedia platform using the public REST and MediaWiki APIs."""

    name = "wikipedia"
    base_url = "https://en.wikipedia.org"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 40

    async def check_username(self, username: str) -> bool | None:
        """Check if a Wikipedia article or user page exists."""
        # Try article first
        try:
            async with self.session.get(
                f"{_REST_BASE}/page/summary/{username}"
            ) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        # Try User: namespace via MediaWiki API
        try:
            async with self.session.get(
                _MW_BASE,
                params={
                    "action": "query",
                    "titles": f"User:{username}",
                    "format": "json",
                },
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                pages = data.get("query", {}).get("pages", {})
                # If the only key is "-1", the page doesn't exist
                if "-1" in pages and len(pages) == 1:
                    return False
                return True
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        try:
            async with self.session.get(
                _MW_BASE,
                params={
                    "action": "opensearch",
                    "search": name,
                    "limit": "10",
                    "namespace": "0",
                    "format": "json",
                },
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                # OpenSearch returns [query, [titles], [descriptions], [urls]]
                if len(data) < 4:
                    return []
                titles = data[1]
                urls = data[3]
                results = []
                for title, url in zip(titles, urls):
                    results.append(
                        CandidateProfile(
                            platform=self.name,
                            username=title,
                            url=url,
                        )
                    )
                return results
        except Exception:
            return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        title = _extract_title(url)
        if not title:
            return None
        try:
            async with self.session.get(
                f"{_REST_BASE}/page/summary/{title}"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                thumbnail = data.get("thumbnail", {})
                return ProfileData(
                    username=data.get("title", title),
                    display_name=data.get("title"),
                    bio=data.get("extract"),
                    profile_photo_url=thumbnail.get("source"),
                    links=[data.get("content_urls", {}).get("desktop", {}).get("page", f"{self.base_url}/wiki/{title}")],
                    raw_json=data,
                )
        except Exception:
            return None


def _extract_title(url: str) -> str | None:
    """Extract article title from a Wikipedia URL."""
    match = _TITLE_RE.search(url)
    if not match:
        return None
    title = match.group(1)
    return title.rstrip("/")

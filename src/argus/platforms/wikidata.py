"""Wikidata platform module using public MediaWiki API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://www.wikidata.org/w/api.php"
_QID_RE = re.compile(r"wikidata\.org/(?:wiki|entity)/(Q\d+)", re.IGNORECASE)


class WikidataPlatform(BasePlatform):
    """Wikidata platform using the public MediaWiki API."""

    name = "wikidata"
    base_url = "https://www.wikidata.org"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 35

    async def check_username(self, username: str) -> bool | None:
        """Check if a Q-ID item exists on Wikidata."""
        # If it looks like a Q-ID, try direct lookup
        if re.match(r"^Q\d+$", username, re.IGNORECASE):
            try:
                async with self.session.get(
                    _API_BASE,
                    params={
                        "action": "wbgetentities",
                        "ids": username.upper(),
                        "format": "json",
                        "props": "info",
                    },
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    entities = data.get("entities", {})
                    entity = entities.get(username.upper(), {})
                    if entity.get("missing") is not None:
                        return False
                    return True
            except Exception:
                return None
        # Otherwise search for the term
        try:
            async with self.session.get(
                _API_BASE,
                params={
                    "action": "wbsearchentities",
                    "search": username,
                    "language": "en",
                    "type": "item",
                    "format": "json",
                    "limit": "1",
                },
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                results = data.get("search", [])
                return len(results) > 0
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        try:
            async with self.session.get(
                _API_BASE,
                params={
                    "action": "wbsearchentities",
                    "search": name,
                    "language": "en",
                    "type": "item",
                    "format": "json",
                    "limit": "10",
                },
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for item in data.get("search", []):
                    qid = item.get("id", "")
                    results.append(
                        CandidateProfile(
                            platform=self.name,
                            username=qid,
                            url=item.get("concepturi", f"{self.base_url}/wiki/{qid}"),
                        )
                    )
                return results
        except Exception:
            return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        qid = _extract_qid(url)
        if not qid:
            return None
        try:
            async with self.session.get(
                _API_BASE,
                params={
                    "action": "wbgetentities",
                    "ids": qid,
                    "format": "json",
                    "props": "labels|descriptions|claims|sitelinks",
                    "languages": "en",
                },
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                entities = data.get("entities", {})
                entity = entities.get(qid)
                if not entity or entity.get("missing") is not None:
                    return None

                label = entity.get("labels", {}).get("en", {}).get("value")
                description = entity.get("descriptions", {}).get("en", {}).get("value")

                # Extract Wikipedia link if available
                links = [f"{self.base_url}/wiki/{qid}"]
                sitelinks = entity.get("sitelinks", {})
                enwiki = sitelinks.get("enwiki", {})
                if enwiki.get("title"):
                    wiki_title = enwiki["title"].replace(" ", "_")
                    links.append(f"https://en.wikipedia.org/wiki/{wiki_title}")

                return ProfileData(
                    username=qid,
                    display_name=label,
                    bio=description,
                    links=links,
                    raw_json=entity,
                )
        except Exception:
            return None


def _extract_qid(url: str) -> str | None:
    """Extract Q-ID from a Wikidata URL."""
    match = _QID_RE.search(url)
    if not match:
        return None
    return match.group(1).upper()

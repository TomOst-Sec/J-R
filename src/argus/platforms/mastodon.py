"""Mastodon/Fediverse platform module — WebFinger + Mastodon API."""

from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

_MAJOR_INSTANCES = [
    "mastodon.social",
    "mastodon.online",
    "mstdn.social",
    "hachyderm.io",
]


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


class MastodonPlatform(BasePlatform):
    """Mastodon/Fediverse platform using WebFinger and Mastodon API."""

    name = "mastodon"
    base_url = "https://mastodon.social"
    rate_limit_per_minute = 20
    requires_auth = False
    requires_playwright = False
    priority = 40

    async def check_username(self, username: str) -> bool | None:
        """Check if a Mastodon account exists via WebFinger."""
        if "@" in username:
            parts = username.split("@")
            user = parts[0]
            instance = parts[1] if len(parts) > 1 else "mastodon.social"
            return await self._webfinger(instance, f"{user}@{instance}")

        # Check major instances
        for instance in _MAJOR_INSTANCES:
            result = await self._webfinger(instance, f"{username}@{instance}")
            if result is True:
                return True
        return None

    async def _webfinger(self, instance: str, acct: str) -> bool | None:
        url = f"https://{instance}/.well-known/webfinger?resource=acct:{quote(acct)}"
        try:
            async with self.session.get(url) as resp:
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
        """Search for accounts across major Mastodon instances."""
        candidates = []
        seen_accts: set[str] = set()

        for instance in _MAJOR_INSTANCES:
            url = f"https://{instance}/api/v2/search?q={quote(name)}&type=accounts&limit=5"
            try:
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
            except Exception:
                continue

            for acct in data.get("accounts", []):
                full_acct = acct.get("acct", "")
                if "@" not in full_acct:
                    full_acct = f"{full_acct}@{instance}"
                if full_acct in seen_accts:
                    continue
                seen_accts.add(full_acct)
                candidates.append(
                    CandidateProfile(
                        platform=self.name,
                        username=full_acct,
                        url=acct.get("url", f"https://{instance}/@{acct.get('username', '')}"),
                        exists=True,
                    )
                )
        return candidates[:10]

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Mastodon profile via the instance API."""
        instance, username = self._parse_url(url)
        if not instance or not username:
            return None

        api_url = f"https://{instance}/api/v1/accounts/lookup?acct={quote(username)}"
        try:
            async with self.session.get(api_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        bio = _strip_html(data.get("note", "")) if data.get("note") else None
        join_date = None
        if data.get("created_at"):
            try:
                join_date = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        links = []
        for field in data.get("fields", []):
            value = field.get("value", "")
            href_match = re.search(r'href="([^"]+)"', value)
            if href_match:
                links.append(href_match.group(1))

        return ProfileData(
            username=data.get("acct", username),
            display_name=data.get("display_name"),
            bio=bio,
            profile_photo_url=data.get("avatar"),
            follower_count=data.get("followers_count"),
            following_count=data.get("following_count"),
            join_date=join_date,
            links=links,
            raw_json=data,
        )

    async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]:
        """Scrape toots from a Mastodon account."""
        instance, username = self._parse_url(url)
        if not instance or not username:
            return []

        # First get account ID
        lookup_url = f"https://{instance}/api/v1/accounts/lookup?acct={quote(username)}"
        try:
            async with self.session.get(lookup_url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                account_id = data.get("id")
                if not account_id:
                    return []
        except Exception:
            return []

        # Fetch statuses
        statuses_url = f"https://{instance}/api/v1/accounts/{account_id}/statuses?limit={min(max_items, 40)}&exclude_replies=true"
        try:
            async with self.session.get(statuses_url) as resp:
                if resp.status != 200:
                    return []
                statuses = await resp.json()
        except Exception:
            return []

        items = []
        for status in statuses[:max_items]:
            text = _strip_html(status.get("content", ""))
            if not text:
                continue

            timestamp = None
            if status.get("created_at"):
                try:
                    timestamp = datetime.fromisoformat(status["created_at"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            engagement = {
                "favourites": status.get("favourites_count", 0),
                "reblogs": status.get("reblogs_count", 0),
            }

            items.append(
                ContentItem(
                    id=str(status.get("id", len(items))),
                    platform=self.name,
                    text=text[:500],
                    timestamp=timestamp,
                    content_type="toot",
                    url=status.get("url"),
                    engagement=engagement,
                )
            )
        return items

    @staticmethod
    def _parse_url(url: str) -> tuple[str | None, str | None]:
        """Parse instance and username from a Mastodon URL."""
        match = re.search(r"https?://([^/]+)/@([^/?]+)", url)
        if match:
            return match.group(1), match.group(2)
        return None, None

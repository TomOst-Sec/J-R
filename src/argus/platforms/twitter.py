"""Twitter/X platform module — web scraping with fallback chain."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.platforms.base import BasePlatform

logger = logging.getLogger(__name__)

_NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
]


class TwitterPlatform(BasePlatform):
    """Twitter/X platform with Playwright + Nitter fallback chain."""

    name = "twitter"
    base_url = "https://x.com"
    rate_limit_per_minute = 10
    requires_auth = False
    requires_playwright = True
    priority = 90

    async def check_username(self, username: str) -> bool | None:
        """Check if a Twitter username exists via x.com or nitter fallback."""
        # Try x.com first
        try:
            async with self.session.head(
                f"https://x.com/{quote(username)}",
                allow_redirects=True,
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status == 404:
                    return False
        except Exception:
            pass

        # Fallback to nitter
        for nitter in _NITTER_INSTANCES:
            try:
                async with self.session.get(
                    f"{nitter}/{quote(username)}",
                    allow_redirects=True,
                ) as resp:
                    if resp.status == 200:
                        return True
                    if resp.status == 404:
                        return False
            except Exception:
                continue

        return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for Twitter users by name using nitter search."""
        # Try nitter search
        for nitter in _NITTER_INSTANCES:
            try:
                query = quote(name)
                url = f"{nitter}/search?f=users&q={query}"
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    return self._parse_nitter_search(text)
            except Exception:
                continue
        return []

    def _parse_nitter_search(self, html_text: str) -> list[CandidateProfile]:
        """Parse nitter search results HTML for user profiles."""
        candidates = []
        # Extract usernames from nitter search results
        pattern = r'href="/([^/?"]+)"[^>]*class="[^"]*username'
        matches = re.findall(pattern, html_text)
        if not matches:
            # Alternative: look for @username patterns
            pattern = r'@([A-Za-z0-9_]{1,15})'
            matches = re.findall(pattern, html_text)

        seen = set()
        for username in matches[:10]:
            username = username.strip()
            if username and username not in seen:
                seen.add(username)
                candidates.append(
                    CandidateProfile(
                        platform=self.name,
                        username=username,
                        url=f"https://x.com/{username}",
                        exists=True,
                    )
                )
        return candidates

    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape a Twitter profile via nitter HTML fallback."""
        username = self._extract_username(url)
        if not username:
            return None

        # Try nitter instances
        for nitter in _NITTER_INSTANCES:
            try:
                async with self.session.get(f"{nitter}/{quote(username)}") as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    profile = self._parse_nitter_profile(text, username)
                    if profile:
                        return profile
            except Exception:
                continue

        return None

    def _parse_nitter_profile(self, html_text: str, username: str) -> ProfileData | None:
        """Parse nitter profile HTML into ProfileData."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_text, "lxml")
        except ImportError:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_text, "html.parser")

        # Display name
        display_name = None
        name_el = soup.select_one(".profile-card-fullname")
        if name_el:
            display_name = name_el.get_text(strip=True)

        # Bio
        bio = None
        bio_el = soup.select_one(".profile-bio")
        if bio_el:
            bio = bio_el.get_text(strip=True)

        # Location
        location = None
        loc_el = soup.select_one(".profile-location")
        if loc_el:
            location = loc_el.get_text(strip=True)

        # Profile photo
        photo_url = None
        photo_el = soup.select_one(".profile-card-avatar img, .profile-card img")
        if photo_el and photo_el.get("src"):
            photo_url = str(photo_el["src"])

        # Follower/following counts
        follower_count = self._parse_stat(soup, "followers")
        following_count = self._parse_stat(soup, "following")

        # Join date
        join_date = None
        date_el = soup.select_one(".profile-joindate span")
        if date_el:
            date_text = date_el.get("title", "")
            if date_text:
                try:
                    join_date = datetime.strptime(date_text, "%I:%M %p - %d %b %Y")
                except (ValueError, TypeError):
                    pass

        # Links
        links = []
        link_els = soup.select(".profile-website a")
        for el in link_els:
            href = el.get("href", "")
            if href:
                links.append(str(href))

        return ProfileData(
            username=username,
            display_name=display_name,
            bio=bio,
            location=location,
            profile_photo_url=photo_url,
            links=links,
            join_date=join_date,
            follower_count=follower_count,
            following_count=following_count,
        )

    @staticmethod
    def _parse_stat(soup: Any, stat_name: str) -> int | None:
        """Parse a stat count from nitter profile."""
        el = soup.select_one(f".profile-stat-num[data-stat='{stat_name}']")
        if not el:
            # Try alternative selector
            for stat in soup.select(".profile-stat"):
                label = stat.select_one(".profile-stat-header")
                if label and stat_name.lower() in label.get_text(strip=True).lower():
                    num = stat.select_one(".profile-stat-num")
                    if num:
                        el = num
                        break
        if el:
            text = el.get_text(strip=True).replace(",", "")
            try:
                return int(text)
            except ValueError:
                pass
        return None

    async def scrape_content(self, url: str, max_items: int = 50) -> list[ContentItem]:
        """Scrape tweets via nitter RSS/HTML fallback."""
        username = self._extract_username(url)
        if not username:
            return []

        for nitter in _NITTER_INSTANCES:
            try:
                async with self.session.get(f"{nitter}/{quote(username)}") as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    return self._parse_nitter_timeline(text, username, max_items)
            except Exception:
                continue

        return []

    def _parse_nitter_timeline(
        self, html_text: str, username: str, max_items: int
    ) -> list[ContentItem]:
        """Parse tweets from nitter timeline HTML."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_text, "lxml")
        except ImportError:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_text, "html.parser")

        items = []
        for tweet in soup.select(".timeline-item")[:max_items]:
            text_el = tweet.select_one(".tweet-content")
            if not text_el:
                continue

            text = text_el.get_text(strip=True)
            tweet_id = ""
            link_el = tweet.select_one(".tweet-link")
            tweet_url = None
            if link_el:
                href = link_el.get("href", "")
                tweet_url = f"https://x.com{href}" if href.startswith("/") else href
                # Extract tweet ID from URL
                parts = href.rstrip("/").split("/")
                if parts:
                    tweet_id = parts[-1]

            timestamp = None
            time_el = tweet.select_one(".tweet-date a")
            if time_el:
                title = time_el.get("title", "")
                if title:
                    try:
                        timestamp = datetime.strptime(title, "%b %d, %Y · %I:%M %p %Z")
                    except (ValueError, TypeError):
                        pass

            engagement = {}
            for stat in tweet.select(".tweet-stat"):
                icon = stat.select_one(".icon-container")
                count_el = stat.select_one(".tweet-stat-num")
                if icon and count_el:
                    count_text = count_el.get_text(strip=True).replace(",", "")
                    try:
                        count = int(count_text)
                    except ValueError:
                        count = 0
                    icon_class = " ".join(icon.get("class", []))
                    if "comment" in icon_class or "reply" in icon_class:
                        engagement["replies"] = count
                    elif "retweet" in icon_class:
                        engagement["retweets"] = count
                    elif "heart" in icon_class or "like" in icon_class:
                        engagement["likes"] = count

            items.append(
                ContentItem(
                    id=tweet_id or str(len(items)),
                    platform=self.name,
                    text=text,
                    timestamp=timestamp,
                    content_type="tweet",
                    url=tweet_url,
                    engagement=engagement if engagement else None,
                )
            )
        return items

    @staticmethod
    def _extract_username(url: str) -> str | None:
        """Extract Twitter username from a URL."""
        url = url.rstrip("/")
        for domain in ("x.com/", "twitter.com/", "nitter.net/"):
            if domain in url:
                parts = url.split(domain)
                if len(parts) > 1:
                    username = parts[1].split("/")[0].split("?")[0]
                    if username and not username.startswith("search"):
                        return username
        return None

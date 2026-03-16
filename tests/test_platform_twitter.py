"""Tests for the Twitter/X platform module with mocked HTTP responses."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.twitter import TwitterPlatform


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def twitter(session: aiohttp.ClientSession) -> TwitterPlatform:
    config = MagicMock()
    return TwitterPlatform(session=session, config=config)


_NITTER_PROFILE_HTML = """
<div class="profile-card">
  <img class="profile-card-avatar" src="https://nitter.net/pic/photo.jpg" />
  <div class="profile-card-fullname">John Doe</div>
  <div class="profile-bio">Python developer and hacker</div>
  <div class="profile-location">San Francisco</div>
  <div class="profile-website"><a href="https://johndoe.dev">johndoe.dev</a></div>
  <div class="profile-stat">
    <div class="profile-stat-header">Followers</div>
    <div class="profile-stat-num">1,234</div>
  </div>
  <div class="profile-stat">
    <div class="profile-stat-header">Following</div>
    <div class="profile-stat-num">567</div>
  </div>
</div>
"""

_NITTER_TIMELINE_HTML = """
<div class="timeline-item">
  <div class="tweet-content">Hello world, first tweet!</div>
  <a class="tweet-link" href="/johndoe/status/12345"></a>
</div>
<div class="timeline-item">
  <div class="tweet-content">Second tweet about Python</div>
  <a class="tweet-link" href="/johndoe/status/12346"></a>
</div>
"""

_NITTER_SEARCH_HTML = """
<div class="user-search">
  <a href="/johndoe" class="username">@johndoe</a>
  <a href="/janedoe" class="username">@janedoe</a>
</div>
"""


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_exists_via_xcom(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.head("https://x.com/johndoe", status=200)
            assert await twitter.check_username("johndoe") is True

    @pytest.mark.asyncio
    async def test_not_found_via_xcom(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.head("https://x.com/nonexistent", status=404)
            assert await twitter.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_fallback_to_nitter(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.head("https://x.com/blocked", exception=Exception("blocked"))
            m.get("https://nitter.net/blocked", status=200)
            assert await twitter.check_username("blocked") is True

    @pytest.mark.asyncio
    async def test_all_fail_returns_none(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.head("https://x.com/fail", exception=Exception("err"))
            m.get("https://nitter.net/fail", exception=Exception("err"))
            m.get("https://nitter.privacydev.net/fail", exception=Exception("err"))
            assert await twitter.check_username("fail") is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_via_nitter(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.get(
                "https://nitter.net/search?f=users&q=John%20Doe",
                body=_NITTER_SEARCH_HTML,
            )
            results = await twitter.search_name("John Doe")
        assert len(results) == 2
        assert results[0].username == "johndoe"
        assert results[1].username == "janedoe"

    @pytest.mark.asyncio
    async def test_search_empty(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.get("https://nitter.net/search?f=users&q=nobody999", body="<html></html>")
            results = await twitter.search_name("nobody999")
        assert results == []


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_via_nitter(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.get("https://nitter.net/johndoe", body=_NITTER_PROFILE_HTML)
            profile = await twitter.scrape_profile("https://x.com/johndoe")
        assert profile is not None
        assert profile.username == "johndoe"
        assert profile.display_name == "John Doe"
        assert profile.bio == "Python developer and hacker"
        assert profile.location == "San Francisco"
        assert profile.follower_count == 1234
        assert profile.following_count == 567

    @pytest.mark.asyncio
    async def test_scrape_not_found(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.get("https://nitter.net/nonexistent", status=404)
            m.get("https://nitter.privacydev.net/nonexistent", status=404)
            profile = await twitter.scrape_profile("https://x.com/nonexistent")
        assert profile is None

    @pytest.mark.asyncio
    async def test_scrape_bad_url(self, twitter: TwitterPlatform) -> None:
        assert await twitter.scrape_profile("https://example.com/nottwitter") is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_tweets(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.get("https://nitter.net/johndoe", body=_NITTER_TIMELINE_HTML)
            items = await twitter.scrape_content("https://x.com/johndoe")
        assert len(items) == 2
        assert items[0].content_type == "tweet"
        assert "Hello world" in items[0].text

    @pytest.mark.asyncio
    async def test_scrape_empty(self, twitter: TwitterPlatform) -> None:
        with aioresponses() as m:
            m.get("https://nitter.net/empty", body="<html></html>")
            items = await twitter.scrape_content("https://x.com/empty")
        assert items == []


class TestExtractUsername:
    def test_xcom(self) -> None:
        assert TwitterPlatform._extract_username("https://x.com/johndoe") == "johndoe"

    def test_twitter_com(self) -> None:
        assert TwitterPlatform._extract_username("https://twitter.com/user1") == "user1"

    def test_nitter(self) -> None:
        assert TwitterPlatform._extract_username("https://nitter.net/user2") == "user2"

    def test_with_path(self) -> None:
        assert TwitterPlatform._extract_username("https://x.com/johndoe/status/123") == "johndoe"

    def test_invalid_url(self) -> None:
        assert TwitterPlatform._extract_username("https://example.com/user") is None

    def test_trailing_slash(self) -> None:
        assert TwitterPlatform._extract_username("https://x.com/johndoe/") == "johndoe"

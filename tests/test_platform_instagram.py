"""Tests for the Instagram platform module with mocked HTTP responses."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.instagram import InstagramPlatform


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def instagram(session: aiohttp.ClientSession) -> InstagramPlatform:
    config = MagicMock()
    return InstagramPlatform(session=session, config=config)


_META_PROFILE_HTML = """
<html>
<head>
<meta property="og:title" content="John Doe (@johndoe)" />
<meta property="og:description" content="1,234 Followers, 567 Following - Python dev" />
<meta property="og:image" content="https://scontent.cdninstagram.com/photo.jpg" />
</head>
<body>profile content</body>
</html>
"""

_SHARED_DATA_HTML = """
<html>
<head></head>
<body>
<script>window._sharedData = {"entry_data":{"ProfilePage":[{"graphql":{"user":{"username":"johndoe","full_name":"John Doe","biography":"Developer","profile_pic_url_hd":"https://example.com/pic.jpg","edge_followed_by":{"count":5000},"edge_follow":{"count":200},"external_url":"https://johndoe.dev"}}}]}};</script>
</body>
</html>
"""

_LOGIN_WALL_HTML = """
<html>
<head></head>
<body>
<div id="loginForm">Login required</div>
</body>
</html>
"""


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_exists(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/johndoe/", body="<html>profile</html>")
            assert await instagram.check_username("johndoe") is True

    @pytest.mark.asyncio
    async def test_not_found(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/nonexistent/", status=404)
            assert await instagram.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_login_wall(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/private/", body=_LOGIN_WALL_HTML)
            assert await instagram.check_username("private") is None

    @pytest.mark.asyncio
    async def test_error(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/error/", exception=Exception("timeout"))
            assert await instagram.check_username("error") is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_returns_empty(self, instagram: InstagramPlatform) -> None:
        results = await instagram.search_name("John Doe")
        assert results == []


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_from_meta_tags(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/johndoe/", body=_META_PROFILE_HTML)
            profile = await instagram.scrape_profile("https://www.instagram.com/johndoe")
        assert profile is not None
        assert profile.username == "johndoe"
        assert profile.display_name == "John Doe"
        assert profile.follower_count == 1234
        assert profile.profile_photo_url == "https://scontent.cdninstagram.com/photo.jpg"

    @pytest.mark.asyncio
    async def test_scrape_from_shared_data(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/johndoe/", body=_SHARED_DATA_HTML)
            profile = await instagram.scrape_profile("https://www.instagram.com/johndoe")
        assert profile is not None
        assert profile.username == "johndoe"
        assert profile.display_name == "John Doe"
        assert profile.bio == "Developer"
        assert profile.follower_count == 5000
        assert profile.following_count == 200
        assert "https://johndoe.dev" in profile.links

    @pytest.mark.asyncio
    async def test_scrape_not_found(self, instagram: InstagramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.instagram.com/nonexistent/", status=404)
            assert await instagram.scrape_profile("https://www.instagram.com/nonexistent") is None

    @pytest.mark.asyncio
    async def test_scrape_bad_url(self, instagram: InstagramPlatform) -> None:
        assert await instagram.scrape_profile("https://example.com/notinstagram") is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_returns_empty(self, instagram: InstagramPlatform) -> None:
        items = await instagram.scrape_content("https://www.instagram.com/johndoe")
        assert items == []


class TestExtractUsername:
    def test_standard(self) -> None:
        assert InstagramPlatform._extract_username("https://www.instagram.com/johndoe") == "johndoe"

    def test_trailing_slash(self) -> None:
        assert InstagramPlatform._extract_username("https://www.instagram.com/johndoe/") == "johndoe"

    def test_skips_special_paths(self) -> None:
        assert InstagramPlatform._extract_username("https://www.instagram.com/p/ABC123") is None
        assert InstagramPlatform._extract_username("https://www.instagram.com/explore/") is None

    def test_non_instagram(self) -> None:
        assert InstagramPlatform._extract_username("https://example.com/user") is None


class TestParseCount:
    def test_plain_number(self) -> None:
        assert InstagramPlatform._parse_count("1234") == 1234

    def test_with_commas(self) -> None:
        assert InstagramPlatform._parse_count("1,234") == 1234

    def test_k_suffix(self) -> None:
        assert InstagramPlatform._parse_count("1.2K") == 1200

    def test_m_suffix(self) -> None:
        assert InstagramPlatform._parse_count("2.5M") == 2500000

    def test_invalid(self) -> None:
        assert InstagramPlatform._parse_count("abc") is None

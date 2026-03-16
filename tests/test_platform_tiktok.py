"""Tests for the TikTok platform module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.tiktok import TikTokPlatform

_META_HTML = """
<html>
<head>
<meta property="og:title" content="TestUser (@testuser)" />
<meta property="og:description" content="123K Followers. Developer" />
<meta property="og:image" content="https://p16.tiktokcdn.com/photo.jpg" />
</head>
<body>@testuser</body>
</html>
"""

_REHYDRATION_DATA = json.dumps({
    "__DEFAULT_SCOPE__": {
        "webapp.user-detail": {
            "userInfo": {
                "user": {
                    "uniqueId": "testuser",
                    "nickname": "Test User",
                    "signature": "Developer and creator",
                    "avatarLarger": "https://p16.tiktokcdn.com/avatar.jpg",
                    "followerCount": 50000,
                    "followingCount": 200,
                }
            }
        }
    }
})

_REHYDRATION_HTML = f"""
<html>
<body>
<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">{_REHYDRATION_DATA}</script>
</body>
</html>
"""


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def tiktok(session: aiohttp.ClientSession) -> TikTokPlatform:
    return TikTokPlatform(session=session, config=MagicMock())


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_exists(self, tiktok: TikTokPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.tiktok.com/@testuser", body='<html>@testuser profile</html>')
            assert await tiktok.check_username("testuser") is True

    @pytest.mark.asyncio
    async def test_not_found(self, tiktok: TikTokPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.tiktok.com/@nonexistent", status=404)
            assert await tiktok.check_username("nonexistent") is False


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_from_rehydration(self, tiktok: TikTokPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.tiktok.com/@testuser", body=_REHYDRATION_HTML)
            profile = await tiktok.scrape_profile("https://www.tiktok.com/@testuser")
        assert profile is not None
        assert profile.username == "testuser"
        assert profile.display_name == "Test User"
        assert profile.follower_count == 50000

    @pytest.mark.asyncio
    async def test_from_meta_tags(self, tiktok: TikTokPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.tiktok.com/@testuser", body=_META_HTML)
            profile = await tiktok.scrape_profile("https://www.tiktok.com/@testuser")
        assert profile is not None
        assert profile.follower_count == 123000

    @pytest.mark.asyncio
    async def test_not_found(self, tiktok: TikTokPlatform) -> None:
        with aioresponses() as m:
            m.get("https://www.tiktok.com/@nobody", status=404)
            assert await tiktok.scrape_profile("https://www.tiktok.com/@nobody") is None

    @pytest.mark.asyncio
    async def test_bad_url(self, tiktok: TikTokPlatform) -> None:
        assert await tiktok.scrape_profile("https://example.com/nottt") is None


class TestExtractUsername:
    def test_standard(self) -> None:
        assert TikTokPlatform._extract_username("https://www.tiktok.com/@user123") == "user123"

    def test_with_video(self) -> None:
        assert TikTokPlatform._extract_username("https://www.tiktok.com/@user/video/123") == "user"

    def test_invalid(self) -> None:
        assert TikTokPlatform._extract_username("https://example.com/user") is None


class TestParseCount:
    def test_k(self) -> None:
        assert TikTokPlatform._parse_count("123K") == 123000

    def test_m(self) -> None:
        assert TikTokPlatform._parse_count("1.5M") == 1500000

    def test_plain(self) -> None:
        assert TikTokPlatform._parse_count("5000") == 5000

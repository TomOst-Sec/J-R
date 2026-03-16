"""Tests for YouTube platform module."""

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from argus.config.settings import ArgusConfig
from argus.platforms.youtube import (
    YouTubePlatform,
    _extract_handle,
    _extract_meta,
    _parse_count,
)

_BASE = "https://www.youtube.com"

_CHANNEL_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta property="og:title" content="Test Channel">
<meta property="og:description" content="A channel about testing">
<meta property="og:image" content="https://yt3.ggpht.com/photo.jpg">
<meta property="og:url" content="https://www.youtube.com/@testchannel">
</head>
<body>
<script>
var ytInitialData = {"channelMetadataRenderer":{"title":"Test Channel"},
"subscriberCountText":{"simpleText":"1.5M subscribers"}};
</script>
</body>
</html>
"""

_VIDEOS_HTML = """
<script>
var data = {
"videoId": "abc123", "title": {"runs": [{"text": "My First Video"}]},
"videoId": "def456", "title": {"runs": [{"text": "Second Video"}]}
};
</script>
"""

_NOT_FOUND_HTML = """
<!DOCTYPE html><html><head><title>404</title></head><body>Page not found</body></html>
"""


@pytest.fixture
def config():
    return ArgusConfig()


class TestExtractHandle:
    def test_handle_url(self):
        assert _extract_handle("https://www.youtube.com/@testchannel") == "testchannel"

    def test_channel_url(self):
        assert _extract_handle("https://www.youtube.com/channel/UC123") == "UC123"

    def test_invalid_url(self):
        assert _extract_handle("https://example.com") is None


class TestParseCount:
    def test_plain_number(self):
        assert _parse_count("1000") == 1000

    def test_k_suffix(self):
        assert _parse_count("1.5K subscribers") == 1500

    def test_m_suffix(self):
        assert _parse_count("1.5M subscribers") == 1500000

    def test_invalid(self):
        assert _parse_count("invalid") is None


class TestExtractMeta:
    def test_property(self):
        html = '<meta property="og:title" content="Test">'
        assert _extract_meta(html, "og:title") == "Test"

    def test_name(self):
        html = '<meta name="description" content="A desc">'
        assert _extract_meta(html, "description") == "A desc"

    def test_not_found(self):
        assert _extract_meta("<html></html>", "og:title") is None


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_user_exists(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@testchannel", body=_CHANNEL_HTML)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                result = await platform.check_username("testchannel")
                assert result is True

    @pytest.mark.asyncio
    async def test_user_not_found(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@nonexistent", status=404)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                result = await platform.check_username("nonexistent")
                assert result is False

    @pytest.mark.asyncio
    async def test_no_channel_data(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@nochannel", body=_NOT_FOUND_HTML)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                result = await platform.check_username("nochannel")
                assert result is False


class TestSearchName:
    @pytest.mark.asyncio
    async def test_returns_empty(self, config):
        async with ClientSession() as session:
            platform = YouTubePlatform(session, config)
            results = await platform.search_name("Test User")
            assert results == []


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_profile(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@testchannel", body=_CHANNEL_HTML)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                profile = await platform.scrape_profile("https://www.youtube.com/@testchannel")
                assert profile is not None
                assert profile.username == "testchannel"
                assert profile.display_name == "Test Channel"
                assert profile.bio == "A channel about testing"
                assert profile.profile_photo_url == "https://yt3.ggpht.com/photo.jpg"
                assert profile.follower_count == 1500000

    @pytest.mark.asyncio
    async def test_scrape_profile_not_found(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@ghost", status=404)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                profile = await platform.scrape_profile("https://www.youtube.com/@ghost")
                assert profile is None

    @pytest.mark.asyncio
    async def test_scrape_bad_url(self, config):
        async with ClientSession() as session:
            platform = YouTubePlatform(session, config)
            profile = await platform.scrape_profile("https://example.com")
            assert profile is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_videos(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@testchannel/videos", body=_VIDEOS_HTML)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                items = await platform.scrape_content("https://www.youtube.com/@testchannel")
                assert len(items) >= 1
                assert items[0].content_type == "video"
                assert items[0].platform == "youtube"

    @pytest.mark.asyncio
    async def test_scrape_content_error(self, config):
        with aioresponses() as m:
            m.get(f"{_BASE}/@test/videos", status=500)
            async with ClientSession() as session:
                platform = YouTubePlatform(session, config)
                items = await platform.scrape_content("https://www.youtube.com/@test")
                assert items == []

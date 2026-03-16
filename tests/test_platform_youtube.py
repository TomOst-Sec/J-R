"""Tests for YouTube platform module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.platforms.youtube import YouTubePlatform

CHANNEL_PAGE_HTML = """
<html>
<head>
<meta property="og:title" content="JohnDoeChannel">
<meta property="og:description" content="Tech tutorials and coding">
<meta property="og:image" content="https://yt3.ggpht.com/abc/photo.jpg">
<meta property="og:url" content="https://www.youtube.com/@johndoe">
<link rel="canonical" href="https://www.youtube.com/channel/UCabc123">
</head>
<body></body>
</html>
"""

NOT_FOUND_HTML = "<html><head><title>404 Not Found</title></head><body></body></html>"

SEARCH_RESULTS_HTML = """
<html><body>
<a href="/@johndoe">JohnDoeChannel</a>
<a href="/@janecodes">Jane Codes</a>
<a href="/watch?v=abc">Some video</a>
</body></html>
"""


class _AsyncContextManager:
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


def _async_ctx(resp):
    return _AsyncContextManager(resp)


def _make_mock_response(status, text_data=""):
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text_data)
    return resp


def _make_platform():
    session = MagicMock()
    config = MagicMock()
    config.get_platform_config.return_value = {}
    return YouTubePlatform(session=session, config=config)


class TestYouTubePlatformAttributes:
    def test_name(self):
        assert _make_platform().name == "youtube"

    def test_base_url(self):
        assert _make_platform().base_url == "https://www.youtube.com"

    def test_no_auth(self):
        assert _make_platform().requires_auth is False

    def test_no_playwright(self):
        assert _make_platform().requires_playwright is False


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_channel_exists(self):
        p = _make_platform()
        resp = _make_mock_response(200, CHANNEL_PAGE_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))
        assert await p.check_username("johndoe") is True

    @pytest.mark.asyncio
    async def test_channel_not_found(self):
        p = _make_platform()
        resp = _make_mock_response(404, NOT_FOUND_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))
        assert await p.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_error_returns_none(self):
        p = _make_platform()
        resp = _make_mock_response(500)
        p.session.get = MagicMock(return_value=_async_ctx(resp))
        assert await p.check_username("test") is None


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_channel_page(self):
        p = _make_platform()
        resp = _make_mock_response(200, CHANNEL_PAGE_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://www.youtube.com/@johndoe")
        assert result is not None
        assert result.username == "johndoe"
        assert "JohnDoeChannel" in (result.display_name or "")
        assert result.bio is not None
        assert result.profile_photo_url is not None

    @pytest.mark.asyncio
    async def test_scrape_404_returns_none(self):
        p = _make_platform()
        resp = _make_mock_response(404)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://www.youtube.com/@nobody")
        assert result is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_returns_channels(self):
        p = _make_platform()
        resp = _make_mock_response(200, SEARCH_RESULTS_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        results = await p.search_name("John Doe")
        assert len(results) >= 1
        # Should only return channel links, not video links
        for r in results:
            assert "@" in r.url or "/c/" in r.url

    @pytest.mark.asyncio
    async def test_search_deduplicates(self):
        p = _make_platform()
        resp = _make_mock_response(200, SEARCH_RESULTS_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        results = await p.search_name("John")
        usernames = [r.username for r in results]
        assert len(usernames) == len(set(usernames))

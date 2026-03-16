"""Tests for Facebook platform module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.platforms.facebook import FacebookPlatform

PROFILE_HTML = """
<html>
<head>
<meta property="og:title" content="John Doe">
<meta property="og:description" content="Software engineer. NYC.">
<meta property="og:image" content="https://scontent.facebook.com/photo.jpg">
<meta property="og:url" content="https://www.facebook.com/johndoe">
</head>
<body></body>
</html>
"""

LOGIN_WALL_HTML = """
<html>
<head><title>Log in to Facebook</title>
<meta property="og:title" content="Facebook">
</head>
<body><div id="login_form">Log in</div></body>
</html>
"""

GOOGLE_RESULTS_HTML = """
<html><body>
<a href="https://www.facebook.com/johndoe">John Doe - Facebook</a>
<a href="https://www.facebook.com/profile.php?id=12345">John D.</a>
<a href="https://www.facebook.com/groups/something">Some Group</a>
</body></html>
"""


class _AsyncContextManager:
    def __init__(self, rv):
        self.rv = rv

    async def __aenter__(self):
        return self.rv

    async def __aexit__(self, *a):
        pass


def _ctx(r):
    return _AsyncContextManager(r)


def _resp(status, text=""):
    r = AsyncMock()
    r.status = status
    r.text = AsyncMock(return_value=text)
    return r


def _platform():
    s = MagicMock()
    c = MagicMock()
    c.get_platform_config.return_value = {}
    return FacebookPlatform(session=s, config=c)


class TestAttributes:
    def test_name(self):
        assert _platform().name == "facebook"

    def test_requires_playwright(self):
        assert _platform().requires_playwright is True


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_profile_exists(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, PROFILE_HTML)))
        assert await p.check_username("johndoe") is True

    @pytest.mark.asyncio
    async def test_not_found(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(404)))
        assert await p.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_login_wall(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, LOGIN_WALL_HTML)))
        assert await p.check_username("someone") is None

    @pytest.mark.asyncio
    async def test_error(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(500)))
        assert await p.check_username("test") is None


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_public_profile(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, PROFILE_HTML)))
        result = await p.scrape_profile("https://www.facebook.com/johndoe")
        assert result is not None
        assert result.username == "johndoe"
        assert "John Doe" in (result.display_name or "")
        assert result.profile_photo_url is not None

    @pytest.mark.asyncio
    async def test_login_wall_returns_none(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, LOGIN_WALL_HTML)))
        result = await p.scrape_profile("https://www.facebook.com/someone")
        assert result is None

    @pytest.mark.asyncio
    async def test_404(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(404)))
        assert await p.scrape_profile("https://www.facebook.com/nobody") is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_returns_profiles(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, GOOGLE_RESULTS_HTML)))
        results = await p.search_name("John Doe")
        urls = [r.url for r in results]
        # Should include profile links but not group links
        assert any("johndoe" in u for u in urls)
        assert not any("groups" in u for u in urls)

    @pytest.mark.asyncio
    async def test_deduplicates(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, GOOGLE_RESULTS_HTML)))
        results = await p.search_name("John")
        usernames = [r.username for r in results]
        assert len(usernames) == len(set(usernames))


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_returns_empty(self):
        p = _platform()
        result = await p.scrape_content("https://www.facebook.com/johndoe")
        assert result == []

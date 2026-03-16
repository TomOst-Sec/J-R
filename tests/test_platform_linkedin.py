"""Tests for LinkedIn platform module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.platforms.linkedin import LinkedInPlatform

# Sample responses
PROFILE_HTML_200 = """
<html>
<head>
<meta property="og:title" content="John Doe - Software Engineer - Acme Corp">
<meta property="og:description" content="View John Doe's profile on LinkedIn, the world's largest professional community. John has 5 jobs listed.">
<meta property="og:image" content="https://media.licdn.com/dms/image/abc/profile.jpg">
<meta property="og:url" content="https://www.linkedin.com/in/johndoe">
<title>John Doe - Software Engineer - Acme Corp | LinkedIn</title>
</head>
<body>
<h1>John Doe</h1>
<div class="top-card-layout__headline">Software Engineer at Acme Corp</div>
<div class="top-card-layout__location">San Francisco Bay Area</div>
</body>
</html>
"""

LOGIN_WALL_HTML = """
<html>
<head><title>Sign In | LinkedIn</title></head>
<body>
<div class="authwall">Join LinkedIn to see full profile</div>
</body>
</html>
"""

GOOGLE_SEARCH_HTML = """
<html><body>
<div class="g"><a href="https://www.linkedin.com/in/johndoe">John Doe - Software Engineer</a></div>
<div class="g"><a href="https://www.linkedin.com/in/janedoe">Jane Doe - Designer</a></div>
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


def _make_mock_response(status, text_data="", json_data=None):
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text_data)
    if json_data is not None:
        resp.json = AsyncMock(return_value=json_data)
    return resp


def _make_platform():
    session = MagicMock()
    config = MagicMock()
    config.get_platform_config.return_value = {}
    return LinkedInPlatform(session=session, config=config)


class TestLinkedInPlatformAttributes:
    def test_name(self):
        p = _make_platform()
        assert p.name == "linkedin"

    def test_base_url(self):
        p = _make_platform()
        assert p.base_url == "https://www.linkedin.com"

    def test_requires_playwright(self):
        p = _make_platform()
        assert p.requires_playwright is True

    def test_no_auth_required(self):
        p = _make_platform()
        assert p.requires_auth is False


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_profile_exists(self):
        p = _make_platform()
        resp = _make_mock_response(200, PROFILE_HTML_200)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.check_username("johndoe")
        assert result is True

    @pytest.mark.asyncio
    async def test_profile_not_found(self):
        p = _make_platform()
        resp = _make_mock_response(404)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.check_username("nonexistent_user_xyz")
        assert result is False

    @pytest.mark.asyncio
    async def test_login_wall_returns_none(self):
        p = _make_platform()
        resp = _make_mock_response(999, LOGIN_WALL_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.check_username("someuser")
        assert result is None

    @pytest.mark.asyncio
    async def test_error_returns_none(self):
        p = _make_platform()
        resp = _make_mock_response(500)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.check_username("someuser")
        assert result is None


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_public_profile(self):
        p = _make_platform()
        resp = _make_mock_response(200, PROFILE_HTML_200)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://www.linkedin.com/in/johndoe")
        assert result is not None
        assert result.username == "johndoe"
        assert "John Doe" in (result.display_name or "")
        assert result.bio is not None
        assert "Software Engineer" in result.bio
        assert result.profile_photo_url is not None

    @pytest.mark.asyncio
    async def test_scrape_login_wall(self):
        p = _make_platform()
        resp = _make_mock_response(200, LOGIN_WALL_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://www.linkedin.com/in/someuser")
        # Should return None or partial data when login wall detected
        assert result is None

    @pytest.mark.asyncio
    async def test_scrape_404(self):
        p = _make_platform()
        resp = _make_mock_response(404)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://www.linkedin.com/in/nobody")
        assert result is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_returns_candidates(self):
        p = _make_platform()
        resp = _make_mock_response(200, GOOGLE_SEARCH_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        results = await p.search_name("John Doe", location="San Francisco")
        assert len(results) >= 1
        urls = [r.url for r in results]
        assert any("linkedin.com/in/" in u for u in urls)

    @pytest.mark.asyncio
    async def test_search_deduplicates(self):
        p = _make_platform()
        resp = _make_mock_response(200, GOOGLE_SEARCH_HTML)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        results = await p.search_name("John Doe")
        usernames = [r.username for r in results]
        assert len(usernames) == len(set(usernames))


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_content_returns_empty_by_default(self):
        """LinkedIn public profiles show limited activity — empty is acceptable."""
        p = _make_platform()
        resp = _make_mock_response(200, PROFILE_HTML_200)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        results = await p.scrape_content("https://www.linkedin.com/in/johndoe")
        assert isinstance(results, list)

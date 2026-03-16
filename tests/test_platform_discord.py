"""Tests for Discord platform module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.platforms.discord import DiscordPlatform

GOOGLE_WITH_DISCORD_LINKS = """
<html><body>
<a href="https://discord.com/users/123456789">JohnDoe on Discord</a>
<a href="https://disboard.org/server/987654">Some Server</a>
<a href="https://discord.com/users/999888777">Another User</a>
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
    return DiscordPlatform(session=s, config=c)


class TestAttributes:
    def test_name(self):
        assert _platform().name == "discord"

    def test_low_priority(self):
        assert _platform().priority == 30

    def test_no_playwright(self):
        assert _platform().requires_playwright is False


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_always_returns_none(self):
        p = _platform()
        assert await p.check_username("anyone") is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_finds_user_links(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, GOOGLE_WITH_DISCORD_LINKS)))
        results = await p.search_name("John Doe")
        assert len(results) >= 1
        assert any("123456789" in r.username for r in results)

    @pytest.mark.asyncio
    async def test_deduplicates(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(200, GOOGLE_WITH_DISCORD_LINKS)))
        results = await p.search_name("John")
        ids = [r.username for r in results]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_search_error_returns_empty(self):
        p = _platform()
        p.session.get = MagicMock(return_value=_ctx(_resp(500)))
        assert await p.search_name("test") == []


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_returns_none(self):
        p = _platform()
        assert await p.scrape_profile("https://discord.com/users/123") is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_returns_empty(self):
        p = _platform()
        assert await p.scrape_content("https://discord.com/users/123") == []

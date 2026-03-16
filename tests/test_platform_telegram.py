"""Tests for the Telegram platform module."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.telegram import TelegramPlatform

_PROFILE_HTML = """
<html>
<body>
<div class="tgme_page_photo"><img src="https://cdn.telegram.org/photo.jpg" /></div>
<div class="tgme_page_title"><span>Test Channel</span></div>
<div class="tgme_page_description">A test channel for testing</div>
<div class="tgme_page_extra">12 345 subscribers</div>
</body>
</html>
"""

_CHANNEL_POSTS_HTML = """
<div class="tgme_widget_message_text">First post about testing</div>
<div class="tgme_widget_message_text">Second post <b>with</b> HTML</div>
"""


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def telegram(session: aiohttp.ClientSession) -> TelegramPlatform:
    return TelegramPlatform(session=session, config=MagicMock())


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_exists(self, telegram: TelegramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://t.me/testchannel", body='<div class="tgme_page_extra">info</div>')
            assert await telegram.check_username("testchannel") is True

    @pytest.mark.asyncio
    async def test_not_found(self, telegram: TelegramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://t.me/nonexistent", body="<html>generic page</html>")
            assert await telegram.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_error(self, telegram: TelegramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://t.me/error", exception=Exception("err"))
            assert await telegram.check_username("error") is None


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_channel(self, telegram: TelegramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://t.me/testchannel", body=_PROFILE_HTML)
            profile = await telegram.scrape_profile("https://t.me/testchannel")
        assert profile is not None
        assert profile.display_name == "Test Channel"
        assert profile.bio == "A test channel for testing"
        assert profile.follower_count == 12345

    @pytest.mark.asyncio
    async def test_scrape_not_found(self, telegram: TelegramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://t.me/nonexistent", status=404)
            assert await telegram.scrape_profile("https://t.me/nonexistent") is None

    @pytest.mark.asyncio
    async def test_bad_url(self, telegram: TelegramPlatform) -> None:
        assert await telegram.scrape_profile("https://example.com/not-tg") is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_channel_posts(self, telegram: TelegramPlatform) -> None:
        with aioresponses() as m:
            m.get("https://t.me/s/testchannel", body=_CHANNEL_POSTS_HTML)
            items = await telegram.scrape_content("https://t.me/testchannel")
        assert len(items) == 2
        assert "First post" in items[0].text
        assert "with HTML" in items[1].text  # HTML stripped


class TestExtractUsername:
    def test_standard(self) -> None:
        assert TelegramPlatform._extract_username("https://t.me/testuser") == "testuser"

    def test_channel_preview(self) -> None:
        assert TelegramPlatform._extract_username("https://t.me/s/channel") == "channel"

    def test_invalid(self) -> None:
        assert TelegramPlatform._extract_username("https://example.com/user") is None

    def test_special_paths(self) -> None:
        assert TelegramPlatform._extract_username("https://t.me/share") is None
        assert TelegramPlatform._extract_username("https://t.me/joinchat") is None

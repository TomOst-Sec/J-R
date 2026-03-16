"""Tests for the Medium platform module."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.medium import MediumPlatform

_PROFILE_HTML = """
<html>
<head>
<meta property="og:title" content="John Doe" />
<meta property="og:description" content="Writer and developer" />
<meta property="og:image" content="https://miro.medium.com/photo.jpg" />
</head>
<body>@johndoe — 1,234 Followers</body>
</html>
"""


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def medium(session: aiohttp.ClientSession) -> MediumPlatform:
    return MediumPlatform(session=session, config=MagicMock())


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_exists(self, medium: MediumPlatform) -> None:
        with aioresponses() as m:
            m.get("https://medium.com/@johndoe", body='<html>@johndoe profile</html>')
            assert await medium.check_username("johndoe") is True

    @pytest.mark.asyncio
    async def test_not_found(self, medium: MediumPlatform) -> None:
        with aioresponses() as m:
            m.get("https://medium.com/@nonexistent", status=404)
            assert await medium.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_error(self, medium: MediumPlatform) -> None:
        with aioresponses() as m:
            m.get("https://medium.com/@error", exception=Exception("err"))
            assert await medium.check_username("error") is None


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_success(self, medium: MediumPlatform) -> None:
        with aioresponses() as m:
            m.get("https://medium.com/@johndoe", body=_PROFILE_HTML)
            profile = await medium.scrape_profile("https://medium.com/@johndoe")
        assert profile is not None
        assert profile.display_name == "John Doe"
        assert profile.bio == "Writer and developer"
        assert profile.follower_count == 1234

    @pytest.mark.asyncio
    async def test_scrape_not_found(self, medium: MediumPlatform) -> None:
        with aioresponses() as m:
            m.get("https://medium.com/@none", status=404)
            assert await medium.scrape_profile("https://medium.com/@none") is None

    @pytest.mark.asyncio
    async def test_bad_url(self, medium: MediumPlatform) -> None:
        assert await medium.scrape_profile("https://example.com/not-medium") is None


class TestExtractUsername:
    def test_standard(self) -> None:
        assert MediumPlatform._extract_username("https://medium.com/@johndoe") == "johndoe"

    def test_with_article(self) -> None:
        assert MediumPlatform._extract_username("https://medium.com/@johndoe/my-article-abc123") == "johndoe"

    def test_invalid(self) -> None:
        assert MediumPlatform._extract_username("https://example.com/user") is None

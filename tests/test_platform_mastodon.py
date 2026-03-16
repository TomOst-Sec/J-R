"""Tests for the Mastodon platform module."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.mastodon import MastodonPlatform


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def masto(session: aiohttp.ClientSession) -> MastodonPlatform:
    return MastodonPlatform(session=session, config=MagicMock())


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_full_acct_exists(self, masto: MastodonPlatform) -> None:
        with aioresponses() as m:
            m.get("https://mastodon.social/.well-known/webfinger?resource=acct:user%40mastodon.social", payload={"subject": "acct:user@mastodon.social"})
            assert await masto.check_username("user@mastodon.social") is True

    @pytest.mark.asyncio
    async def test_full_acct_not_found(self, masto: MastodonPlatform) -> None:
        with aioresponses() as m:
            m.get("https://example.org/.well-known/webfinger?resource=acct:nobody%40example.org", status=404)
            assert await masto.check_username("nobody@example.org") is False


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_across_instances(self, masto: MastodonPlatform) -> None:
        payload = {"accounts": [{"acct": "johndoe", "url": "https://mastodon.social/@johndoe", "username": "johndoe"}]}
        with aioresponses() as m:
            m.get("https://mastodon.social/api/v2/search?q=John%20Doe&type=accounts&limit=5", payload=payload)
            m.get("https://mastodon.online/api/v2/search?q=John%20Doe&type=accounts&limit=5", payload={"accounts": []})
            m.get("https://mstdn.social/api/v2/search?q=John%20Doe&type=accounts&limit=5", payload={"accounts": []})
            m.get("https://hachyderm.io/api/v2/search?q=John%20Doe&type=accounts&limit=5", payload={"accounts": []})
            results = await masto.search_name("John Doe")
        assert len(results) == 1
        assert results[0].username == "johndoe@mastodon.social"


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_success(self, masto: MastodonPlatform) -> None:
        payload = {
            "acct": "johndoe",
            "display_name": "John Doe",
            "note": "<p>Hello <b>world</b></p>",
            "avatar": "https://mastodon.social/avatar.jpg",
            "followers_count": 500,
            "following_count": 200,
            "created_at": "2022-01-15T00:00:00.000Z",
            "fields": [{"name": "Website", "value": '<a href="https://johndoe.dev">site</a>'}],
        }
        with aioresponses() as m:
            m.get("https://mastodon.social/api/v1/accounts/lookup?acct=johndoe", payload=payload)
            profile = await masto.scrape_profile("https://mastodon.social/@johndoe")
        assert profile is not None
        assert profile.display_name == "John Doe"
        assert profile.bio == "Hello world"
        assert profile.follower_count == 500
        assert "https://johndoe.dev" in profile.links

    @pytest.mark.asyncio
    async def test_scrape_not_found(self, masto: MastodonPlatform) -> None:
        with aioresponses() as m:
            m.get("https://mastodon.social/api/v1/accounts/lookup?acct=nobody", status=404)
            assert await masto.scrape_profile("https://mastodon.social/@nobody") is None

    @pytest.mark.asyncio
    async def test_bad_url(self, masto: MastodonPlatform) -> None:
        assert await masto.scrape_profile("https://example.com/notmasto") is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_toots(self, masto: MastodonPlatform) -> None:
        lookup = {"id": "123", "acct": "johndoe"}
        statuses = [
            {"id": "1", "content": "<p>First toot!</p>", "created_at": "2024-01-01T12:00:00Z", "favourites_count": 5, "reblogs_count": 2, "url": "https://mastodon.social/@johndoe/1"},
        ]
        with aioresponses() as m:
            m.get("https://mastodon.social/api/v1/accounts/lookup?acct=johndoe", payload=lookup)
            m.get("https://mastodon.social/api/v1/accounts/123/statuses?limit=40&exclude_replies=true", payload=statuses)
            items = await masto.scrape_content("https://mastodon.social/@johndoe")
        assert len(items) == 1
        assert items[0].content_type == "toot"
        assert "First toot" in items[0].text


class TestParseUrl:
    def test_standard(self) -> None:
        inst, user = MastodonPlatform._parse_url("https://mastodon.social/@johndoe")
        assert inst == "mastodon.social"
        assert user == "johndoe"

    def test_custom_instance(self) -> None:
        inst, user = MastodonPlatform._parse_url("https://hachyderm.io/@techuser")
        assert inst == "hachyderm.io"
        assert user == "techuser"

    def test_invalid(self) -> None:
        assert MastodonPlatform._parse_url("https://example.com/user") == (None, None)

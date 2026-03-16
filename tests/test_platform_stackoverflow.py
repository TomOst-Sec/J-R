"""Tests for the Stack Overflow platform module."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from argus.platforms.stackoverflow import StackOverflowPlatform, _strip_html


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def so(session: aiohttp.ClientSession) -> StackOverflowPlatform:
    return StackOverflowPlatform(session=session, config=MagicMock())


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_always_none(self, so: StackOverflowPlatform) -> None:
        assert await so.check_username("anyone") is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_users(self, so: StackOverflowPlatform) -> None:
        payload = {
            "items": [
                {"display_name": "John Doe", "user_id": 12345, "link": "https://stackoverflow.com/users/12345/john-doe", "reputation": 5000},
                {"display_name": "John D", "user_id": 67890, "link": "https://stackoverflow.com/users/67890/john-d", "reputation": 1000},
            ],
            "quota_remaining": 200,
        }
        with aioresponses() as m:
            m.get("https://api.stackexchange.com/2.3/users?inname=John%20Doe&site=stackoverflow&sort=reputation&pagesize=10", payload=payload)
            results = await so.search_name("John Doe")
        assert len(results) == 2
        assert results[0].username == "John Doe"

    @pytest.mark.asyncio
    async def test_search_empty(self, so: StackOverflowPlatform) -> None:
        with aioresponses() as m:
            m.get("https://api.stackexchange.com/2.3/users?inname=nobody999&site=stackoverflow&sort=reputation&pagesize=10", payload={"items": [], "quota_remaining": 200})
            assert await so.search_name("nobody999") == []

    @pytest.mark.asyncio
    async def test_search_with_location(self, so: StackOverflowPlatform) -> None:
        payload = {
            "items": [
                {"display_name": "User1", "user_id": 1, "link": "https://stackoverflow.com/users/1", "location": "New York"},
                {"display_name": "User2", "user_id": 2, "link": "https://stackoverflow.com/users/2", "location": "London"},
            ],
            "quota_remaining": 200,
        }
        with aioresponses() as m:
            m.get("https://api.stackexchange.com/2.3/users?inname=Test&site=stackoverflow&sort=reputation&pagesize=10", payload=payload)
            results = await so.search_name("Test", location="New York")
        assert len(results) == 1
        assert results[0].username == "User1"


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_success(self, so: StackOverflowPlatform) -> None:
        payload = {
            "items": [{
                "display_name": "John Doe",
                "about_me": "<p>I am a <b>Python</b> developer.</p>",
                "location": "San Francisco",
                "profile_image": "https://example.com/photo.jpg",
                "website_url": "https://johndoe.dev",
                "creation_date": 1400000000,
                "reputation": 5000,
            }],
            "quota_remaining": 200,
        }
        with aioresponses() as m:
            m.get("https://api.stackexchange.com/2.3/users/12345?site=stackoverflow&filter=!nNPvSNVZJS", payload=payload)
            profile = await so.scrape_profile("https://stackoverflow.com/users/12345/john-doe")
        assert profile is not None
        assert profile.display_name == "John Doe"
        assert "Python" in (profile.bio or "")
        assert "<" not in (profile.bio or "")  # HTML stripped
        assert "https://johndoe.dev" in profile.links

    @pytest.mark.asyncio
    async def test_scrape_not_found(self, so: StackOverflowPlatform) -> None:
        with aioresponses() as m:
            m.get("https://api.stackexchange.com/2.3/users/99999?site=stackoverflow&filter=!nNPvSNVZJS", payload={"items": [], "quota_remaining": 200})
            assert await so.scrape_profile("https://stackoverflow.com/users/99999") is None

    @pytest.mark.asyncio
    async def test_scrape_bad_url(self, so: StackOverflowPlatform) -> None:
        assert await so.scrape_profile("https://example.com/not-so") is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_answers(self, so: StackOverflowPlatform) -> None:
        ans_payload = {
            "items": [{
                "answer_id": 1,
                "body": "<p>Use <code>async/await</code>.</p>",
                "creation_date": 1700000000,
                "score": 25,
                "is_accepted": True,
            }],
            "quota_remaining": 200,
        }
        q_payload = {"items": [], "quota_remaining": 200}
        with aioresponses() as m:
            m.get("https://api.stackexchange.com/2.3/users/12345/answers?site=stackoverflow&sort=votes&pagesize=30&filter=withbody", payload=ans_payload)
            m.get("https://api.stackexchange.com/2.3/users/12345/questions?site=stackoverflow&sort=votes&pagesize=20&filter=withbody", payload=q_payload)
            items = await so.scrape_content("https://stackoverflow.com/users/12345")
        assert len(items) == 1
        assert items[0].content_type == "answer"
        assert "async/await" in items[0].text
        assert items[0].engagement["accepted"] is True


class TestExtractUserId:
    def test_standard_url(self) -> None:
        assert StackOverflowPlatform._extract_user_id("https://stackoverflow.com/users/12345/john") == "12345"

    def test_url_without_name(self) -> None:
        assert StackOverflowPlatform._extract_user_id("https://stackoverflow.com/users/67890") == "67890"

    def test_invalid_url(self) -> None:
        assert StackOverflowPlatform._extract_user_id("https://example.com/not-so") is None


class TestStripHtml:
    def test_basic(self) -> None:
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_entities(self) -> None:
        assert _strip_html("&amp; &lt;") == "& <"

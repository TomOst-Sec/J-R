"""Tests for HackerNews platform module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.platforms.hackernews import HackerNewsPlatform

# Firebase API responses
USER_RESPONSE = {
    "id": "pg",
    "created": 1160418111,
    "karma": 157236,
    "about": "Bug Fixer. <a href='http://www.ycombinator.com'>YC</a>",
    "submitted": [1000, 1001, 1002],
}

USER_NOT_FOUND = None  # Firebase returns null for missing users

# Algolia API responses
ALGOLIA_SEARCH_RESPONSE = {
    "hits": [
        {
            "author": "pg",
            "objectID": "1000",
            "title": "Ask HN: Best programming language?",
            "story_text": None,
            "created_at": "2023-11-14T12:00:00.000Z",
            "url": None,
            "points": 150,
            "num_comments": 42,
            "story_id": None,
            "_tags": ["story", "author_pg", "ask_hn"],
        },
        {
            "author": "pg",
            "objectID": "1001",
            "title": None,
            "comment_text": "Great insight on this topic.",
            "created_at": "2023-11-15T08:30:00.000Z",
            "url": None,
            "points": 25,
            "num_comments": 0,
            "story_id": 999,
            "_tags": ["comment", "author_pg"],
        },
    ],
    "nbHits": 2,
}

ALGOLIA_NAME_SEARCH_RESPONSE = {
    "hits": [
        {"author": "johndoe", "objectID": "2000"},
        {"author": "john_doe", "objectID": "2001"},
        {"author": "johndoe", "objectID": "2002"},  # duplicate author
    ],
    "nbHits": 3,
}


class _AsyncContextManager:
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


def _async_ctx(resp):
    return _AsyncContextManager(resp)


def _make_mock_response(status: int, json_data):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    return resp


def _make_platform():
    session = MagicMock()
    config = MagicMock()
    config.get_platform_config.return_value = {}
    return HackerNewsPlatform(session=session, config=config)


class TestHackerNewsPlatformAttributes:
    def test_name(self):
        p = _make_platform()
        assert p.name == "hackernews"

    def test_base_url(self):
        p = _make_platform()
        assert p.base_url == "https://news.ycombinator.com"

    def test_no_auth(self):
        p = _make_platform()
        assert p.requires_auth is False

    def test_no_playwright(self):
        p = _make_platform()
        assert p.requires_playwright is False


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_user_exists(self):
        p = _make_platform()
        resp = _make_mock_response(200, USER_RESPONSE)
        p.session.get = MagicMock(return_value=_async_ctx(resp))
        assert await p.check_username("pg") is True

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        p = _make_platform()
        resp = _make_mock_response(200, USER_NOT_FOUND)
        p.session.get = MagicMock(return_value=_async_ctx(resp))
        assert await p.check_username("nonexistent") is False

    @pytest.mark.asyncio
    async def test_error_returns_none(self):
        p = _make_platform()
        resp = _make_mock_response(500, None)
        p.session.get = MagicMock(return_value=_async_ctx(resp))
        assert await p.check_username("test") is None


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_valid_profile(self):
        p = _make_platform()
        resp = _make_mock_response(200, USER_RESPONSE)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://news.ycombinator.com/user?id=pg")
        assert result is not None
        assert result.username == "pg"
        assert "Bug Fixer" in result.bio
        # HTML should be stripped
        assert "<a" not in result.bio
        assert result.join_date is not None
        assert result.raw_json is not None
        assert result.profile_photo_url is None  # HN has no photos

    @pytest.mark.asyncio
    async def test_nonexistent_profile(self):
        p = _make_platform()
        resp = _make_mock_response(200, USER_NOT_FOUND)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        result = await p.scrape_profile("https://news.ycombinator.com/user?id=nobody")
        assert result is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_content(self):
        p = _make_platform()
        resp = _make_mock_response(200, ALGOLIA_SEARCH_RESPONSE)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        items = await p.scrape_content(
            "https://news.ycombinator.com/user?id=pg", max_items=10
        )
        assert len(items) == 2

        story = items[0]
        assert story.content_type == "story"
        assert "Best programming language" in story.text
        assert story.timestamp is not None

        comment = items[1]
        assert comment.content_type == "comment"
        assert "Great insight" in comment.text


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_returns_unique_authors(self):
        p = _make_platform()
        resp = _make_mock_response(200, ALGOLIA_NAME_SEARCH_RESPONSE)
        p.session.get = MagicMock(return_value=_async_ctx(resp))

        results = await p.search_name("John Doe")
        # Should deduplicate: johndoe appears twice
        usernames = [r.username for r in results]
        assert "johndoe" in usernames
        assert "john_doe" in usernames
        assert len(usernames) == len(set(usernames))

"""Tests for Reddit platform module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.platforms.reddit import RedditPlatform

# Sample Reddit API responses
USER_ABOUT_RESPONSE = {
    "kind": "t2",
    "data": {
        "name": "testuser123",
        "subreddit": {
            "public_description": "I'm a software developer from NYC",
            "display_name": "u_testuser123",
        },
        "icon_img": "https://styles.redditmedia.com/t5_abc/avatar.png?width=256",
        "created_utc": 1609459200.0,  # 2021-01-01
        "link_karma": 5000,
        "comment_karma": 12000,
        "is_suspended": False,
        "total_karma": 17000,
    },
}

USER_NOT_FOUND_RESPONSE = {"message": "Not Found", "error": 404}

SUSPENDED_USER_RESPONSE = {
    "kind": "t2",
    "data": {
        "name": "suspendeduser",
        "is_suspended": True,
    },
}

USER_POSTS_RESPONSE = {
    "kind": "Listing",
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "title": "My first post",
                    "selftext": "Hello world!",
                    "created_utc": 1700000000.0,
                    "permalink": "/r/test/comments/abc/my_first_post/",
                    "ups": 42,
                    "num_comments": 5,
                    "name": "t3_abc",
                },
            },
            {
                "kind": "t1",
                "data": {
                    "body": "This is a comment",
                    "created_utc": 1700100000.0,
                    "permalink": "/r/test/comments/def/some_post/xyz/",
                    "ups": 10,
                    "num_comments": 0,
                    "name": "t1_xyz",
                },
            },
        ],
    },
}


def _make_mock_response(status: int, json_data: dict):
    """Create a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    return resp


def _make_platform():
    """Create a RedditPlatform with mocked session and config."""
    session = MagicMock()
    config = MagicMock()
    config.get_platform_config.return_value = {}
    return RedditPlatform(session=session, config=config)


class TestRedditPlatformAttributes:
    def test_name(self):
        platform = _make_platform()
        assert platform.name == "reddit"

    def test_base_url(self):
        platform = _make_platform()
        assert platform.base_url == "https://www.reddit.com"

    def test_no_auth_required(self):
        platform = _make_platform()
        assert platform.requires_auth is False

    def test_no_playwright_required(self):
        platform = _make_platform()
        assert platform.requires_playwright is False


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_user_exists(self):
        platform = _make_platform()
        resp = _make_mock_response(200, USER_ABOUT_RESPONSE)
        platform.session.get = MagicMock(return_value=_async_context(resp))

        result = await platform.check_username("testuser123")
        assert result is True

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        platform = _make_platform()
        resp = _make_mock_response(404, USER_NOT_FOUND_RESPONSE)
        platform.session.get = MagicMock(return_value=_async_context(resp))

        result = await platform.check_username("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_suspended_user(self):
        platform = _make_platform()
        resp = _make_mock_response(200, SUSPENDED_USER_RESPONSE)
        platform.session.get = MagicMock(return_value=_async_context(resp))

        result = await platform.check_username("suspendeduser")
        assert result is False

    @pytest.mark.asyncio
    async def test_error_returns_none(self):
        platform = _make_platform()
        resp = _make_mock_response(500, {})
        platform.session.get = MagicMock(return_value=_async_context(resp))

        result = await platform.check_username("testuser")
        assert result is None

    @pytest.mark.asyncio
    async def test_sends_user_agent(self):
        platform = _make_platform()
        resp = _make_mock_response(200, USER_ABOUT_RESPONSE)
        mock_get = MagicMock(return_value=_async_context(resp))
        platform.session.get = mock_get

        await platform.check_username("testuser123")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
        assert "User-Agent" in headers
        # Should not be a default python user agent
        assert "python" not in headers["User-Agent"].lower()


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_valid_profile(self):
        platform = _make_platform()
        resp = _make_mock_response(200, USER_ABOUT_RESPONSE)
        platform.session.get = MagicMock(return_value=_async_context(resp))

        result = await platform.scrape_profile("https://www.reddit.com/user/testuser123")
        assert result is not None
        assert result.username == "testuser123"
        assert "software developer" in result.bio
        assert result.profile_photo_url is not None
        assert result.join_date is not None
        assert result.raw_json is not None

    @pytest.mark.asyncio
    async def test_scrape_nonexistent_profile(self):
        platform = _make_platform()
        resp = _make_mock_response(404, USER_NOT_FOUND_RESPONSE)
        platform.session.get = MagicMock(return_value=_async_context(resp))

        result = await platform.scrape_profile("https://www.reddit.com/user/nobody")
        assert result is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_posts_and_comments(self):
        platform = _make_platform()
        resp = _make_mock_response(200, USER_POSTS_RESPONSE)
        platform.session.get = MagicMock(return_value=_async_context(resp))

        results = await platform.scrape_content(
            "https://www.reddit.com/user/testuser123", max_items=10
        )
        assert len(results) == 2

        # First item is a post
        post = results[0]
        assert post.content_type == "post"
        assert "My first post" in post.text
        assert post.timestamp is not None
        assert post.url is not None

        # Second item is a comment
        comment = results[1]
        assert comment.content_type == "comment"
        assert "This is a comment" in comment.text


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_returns_empty(self):
        platform = _make_platform()
        result = await platform.search_name("John Doe")
        assert result == []


class _AsyncContextManager:
    """Helper to make mock responses work as async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


def _async_context(resp):
    return _AsyncContextManager(resp)

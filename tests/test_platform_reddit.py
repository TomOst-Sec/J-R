"""Tests for Reddit platform module."""

from unittest.mock import MagicMock

from argus.config import ArgusConfig
from argus.platforms.reddit import RedditPlatform, _extract_username


def _make_session(responses: dict | None = None):
    """Create a mock aiohttp session with configurable responses."""
    session = MagicMock()
    _responses = responses or {}

    class FakeResponse:
        def __init__(self, status, data=None, headers=None):
            self.status = status
            self._data = data
            self.headers = headers or {}

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    def mock_get(url, **kwargs):
        for pattern, (status, data) in _responses.items():
            if pattern in url:
                return FakeResponse(status, data)
        return FakeResponse(404, {})

    session.get = mock_get
    return session


_ABOUT_DATA = {
    "kind": "t2",
    "data": {
        "name": "testuser",
        "subreddit": {
            "public_description": "Just a test user",
            "display_name_prefixed": "u/testuser",
        },
        "icon_img": "https://styles.redditmedia.com/test.png?fidelity=medium",
        "created_utc": 1577836800.0,
        "link_karma": 1234,
        "comment_karma": 5678,
        "is_suspended": False,
    },
}

_SUSPENDED_DATA = {
    "kind": "t2",
    "data": {
        "name": "suspendeduser",
        "is_suspended": True,
    },
}

_POSTS_DATA = {
    "kind": "Listing",
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "id": "abc123",
                    "title": "My first post",
                    "selftext": "Hello world",
                    "created_utc": 1700000000.0,
                    "permalink": "/r/test/comments/abc123/my_first_post/",
                    "ups": 42,
                    "num_comments": 5,
                    "name": "t3_abc123",
                },
            },
            {
                "kind": "t1",
                "data": {
                    "id": "def456",
                    "body": "Great post!",
                    "created_utc": 1700001000.0,
                    "permalink": "/r/test/comments/abc123/my_first_post/def456/",
                    "ups": 10,
                    "num_comments": 0,
                    "name": "t1_def456",
                },
            },
        ],
    },
}


class TestRedditPlatformAttributes:
    def test_class_attributes(self):
        assert RedditPlatform.name == "reddit"
        assert RedditPlatform.base_url == "https://www.reddit.com"
        assert RedditPlatform.rate_limit_per_minute == 20
        assert RedditPlatform.requires_auth is False
        assert RedditPlatform.requires_playwright is False
        assert RedditPlatform.priority == 70


class TestExtractUsername:
    def test_from_profile_url(self):
        assert _extract_username("https://www.reddit.com/user/testuser") == "testuser"

    def test_from_profile_url_trailing_slash(self):
        assert _extract_username("https://www.reddit.com/user/testuser/") == "testuser"

    def test_from_profile_url_with_path(self):
        assert (
            _extract_username("https://www.reddit.com/user/testuser/comments")
            == "testuser"
        )

    def test_no_match(self):
        assert _extract_username("https://example.com/testuser") is None

    def test_old_url_format(self):
        assert _extract_username("https://reddit.com/u/testuser") == "testuser"


class TestCheckUsername:
    async def test_user_exists(self):
        session = _make_session({"user/testuser/about.json": (200, _ABOUT_DATA)})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        assert await platform.check_username("testuser") is True

    async def test_user_not_found(self):
        session = _make_session({})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        assert await platform.check_username("nonexistent") is False

    async def test_suspended_user(self):
        session = _make_session(
            {"user/suspendeduser/about.json": (200, _SUSPENDED_DATA)}
        )
        platform = RedditPlatform(session=session, config=ArgusConfig())
        result = await platform.check_username("suspendeduser")
        assert result is True

    async def test_server_error(self):
        session = _make_session({"user/testuser/about.json": (500, {})})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        assert await platform.check_username("testuser") is None


class TestSearchName:
    async def test_returns_empty(self):
        """Reddit has no name search API."""
        session = _make_session({})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        results = await platform.search_name("John Doe")
        assert results == []


class TestScrapeProfile:
    async def test_scrape_valid_profile(self):
        session = _make_session({"user/testuser/about.json": (200, _ABOUT_DATA)})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        result = await platform.scrape_profile("https://www.reddit.com/user/testuser")
        assert result is not None
        assert result.username == "testuser"
        assert result.bio == "Just a test user"
        assert "styles.redditmedia.com" in result.profile_photo_url
        assert result.join_date is not None
        assert result.raw_json is not None

    async def test_scrape_not_found(self):
        session = _make_session({})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        result = await platform.scrape_profile("https://www.reddit.com/user/nobody")
        assert result is None

    async def test_scrape_invalid_url(self):
        session = _make_session({})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        result = await platform.scrape_profile("https://example.com/foo")
        assert result is None

    async def test_scrape_suspended(self):
        session = _make_session(
            {"user/suspendeduser/about.json": (200, _SUSPENDED_DATA)}
        )
        platform = RedditPlatform(session=session, config=ArgusConfig())
        result = await platform.scrape_profile(
            "https://www.reddit.com/user/suspendeduser"
        )
        assert result is not None
        assert result.username == "suspendeduser"


class TestScrapeContent:
    async def test_scrape_posts(self):
        session = _make_session({"user/testuser.json": (200, _POSTS_DATA)})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        items = await platform.scrape_content(
            "https://www.reddit.com/user/testuser", max_items=10
        )
        assert len(items) == 2
        post = items[0]
        assert post.content_type == "post"
        assert "My first post" in post.text
        assert post.engagement["ups"] == 42

        comment = items[1]
        assert comment.content_type == "comment"
        assert "Great post!" in comment.text

    async def test_scrape_content_invalid_url(self):
        session = _make_session({})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        items = await platform.scrape_content("https://example.com/foo")
        assert items == []

    async def test_scrape_content_not_found(self):
        session = _make_session({})
        platform = RedditPlatform(session=session, config=ArgusConfig())
        items = await platform.scrape_content(
            "https://www.reddit.com/user/nobody"
        )
        assert items == []

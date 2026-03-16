"""Tests for GitHub platform module."""

import re

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from argus.config.settings import ArgusConfig
from argus.platforms.github import GitHubPlatform

_API = "https://api.github.com"

_USER_JSON = {
    "login": "octocat",
    "name": "The Octocat",
    "bio": "GitHub mascot",
    "location": "San Francisco",
    "avatar_url": "https://avatars.githubusercontent.com/u/583231",
    "html_url": "https://github.com/octocat",
    "blog": "https://github.blog",
    "created_at": "2011-01-25T18:44:36Z",
    "followers": 1000,
    "following": 10,
    "public_repos": 8,
}

_SEARCH_JSON = {
    "total_count": 2,
    "items": [
        {"login": "octocat", "html_url": "https://github.com/octocat"},
        {"login": "octocat2", "html_url": "https://github.com/octocat2"},
    ],
}

_REPOS_JSON = [
    {
        "id": 1,
        "name": "hello-world",
        "description": "My first repo",
        "html_url": "https://github.com/octocat/hello-world",
        "pushed_at": "2024-01-15T12:00:00Z",
        "stargazers_count": 100,
        "forks_count": 50,
    },
]


@pytest.fixture
def config():
    return ArgusConfig()


class TestCheckUsername:
    @pytest.mark.asyncio
    async def test_user_exists(self, config):
        with aioresponses() as m:
            m.get(f"{_API}/users/octocat", payload=_USER_JSON, headers={"X-RateLimit-Remaining": "59"})
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                result = await platform.check_username("octocat")
                assert result is True

    @pytest.mark.asyncio
    async def test_user_not_found(self, config):
        with aioresponses() as m:
            m.get(f"{_API}/users/nonexistent", status=404)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                result = await platform.check_username("nonexistent")
                assert result is False

    @pytest.mark.asyncio
    async def test_rate_limited(self, config):
        with aioresponses() as m:
            m.get(f"{_API}/users/test", status=403)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                result = await platform.check_username("test")
                assert result is None


class TestSearchName:
    @pytest.mark.asyncio
    async def test_search_with_results(self, config):
        with aioresponses() as m:
            m.get(re.compile(r"https://api\.github\.com/search/users\?"), payload=_SEARCH_JSON)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                results = await platform.search_name("octocat")
                assert len(results) == 2
                assert results[0].username == "octocat"
                assert results[0].platform == "github"

    @pytest.mark.asyncio
    async def test_search_with_location(self, config):
        with aioresponses() as m:
            m.get(re.compile(r"https://api\.github\.com/search/users\?"), payload=_SEARCH_JSON)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                results = await platform.search_name("octocat", "San Francisco")
                assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_empty(self, config):
        with aioresponses() as m:
            m.get(re.compile(r"https://api\.github\.com/search/users\?"), payload={"total_count": 0, "items": []})
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                results = await platform.search_name("zzzznonexistent")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_error(self, config):
        with aioresponses() as m:
            m.get(re.compile(r"https://api\.github\.com/search/users\?"), status=500)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                results = await platform.search_name("test")
                assert results == []


class TestScrapeProfile:
    @pytest.mark.asyncio
    async def test_scrape_profile(self, config):
        with aioresponses() as m:
            m.get(f"{_API}/users/octocat", payload=_USER_JSON)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                profile = await platform.scrape_profile("https://github.com/octocat")
                assert profile is not None
                assert profile.username == "octocat"
                assert profile.display_name == "The Octocat"
                assert profile.bio == "GitHub mascot"
                assert profile.location == "San Francisco"
                assert profile.follower_count == 1000
                assert profile.following_count == 10
                assert profile.raw_json is not None
                assert "https://github.blog" in profile.links

    @pytest.mark.asyncio
    async def test_scrape_profile_not_found(self, config):
        with aioresponses() as m:
            m.get(f"{_API}/users/ghost", status=404)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                profile = await platform.scrape_profile("https://github.com/ghost")
                assert profile is None

    @pytest.mark.asyncio
    async def test_scrape_profile_bad_url(self, config):
        async with ClientSession() as session:
            platform = GitHubPlatform(session, config)
            profile = await platform.scrape_profile("https://example.com")
            assert profile is None


class TestScrapeContent:
    @pytest.mark.asyncio
    async def test_scrape_repos(self, config):
        with aioresponses() as m:
            m.get(re.compile(r"https://api\.github\.com/users/octocat/repos"), payload=_REPOS_JSON)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                items = await platform.scrape_content("https://github.com/octocat")
                assert len(items) == 1
                assert items[0].content_type == "repo"
                assert "hello-world" in items[0].text
                assert items[0].engagement["stars"] == 100

    @pytest.mark.asyncio
    async def test_scrape_content_error(self, config):
        with aioresponses() as m:
            m.get(re.compile(r"https://api\.github\.com/users/test/repos"), status=500)
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                items = await platform.scrape_content("https://github.com/test")
                assert items == []


class TestRateLimitTracking:
    @pytest.mark.asyncio
    async def test_rate_limit_header_parsed(self, config):
        with aioresponses() as m:
            m.get(
                f"{_API}/users/octocat",
                payload=_USER_JSON,
                headers={"X-RateLimit-Remaining": "42"},
            )
            async with ClientSession() as session:
                platform = GitHubPlatform(session, config)
                await platform.check_username("octocat")
                assert platform._rate_limit_remaining == 42

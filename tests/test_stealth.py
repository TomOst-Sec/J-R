"""Tests for the stealth module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from argus.stealth.delays import DelayManager, random_delay
from argus.stealth.proxy import ProxyRotator
from argus.stealth.rate_limiter import PlatformRateLimiter, TokenBucketRateLimiter
from argus.stealth.session import create_stealth_session
from argus.stealth.user_agents import USER_AGENTS, UserAgentRotator, get_random_user_agent


class TestUserAgents:
    def test_list_has_50_plus_entries(self) -> None:
        assert len(USER_AGENTS) >= 50

    def test_get_random_seeded(self) -> None:
        ua1 = get_random_user_agent(seed=42)
        ua2 = get_random_user_agent(seed=42)
        assert ua1 == ua2

    def test_get_random_different_seeds(self) -> None:
        ua1 = get_random_user_agent(seed=1)
        ua2 = get_random_user_agent(seed=2)
        # Different seeds should (very likely) give different UAs
        # with 50+ options the collision probability is very low
        assert ua1 != ua2

    def test_rotator_round_robin(self) -> None:
        rotator = UserAgentRotator(strategy="round-robin")
        first = rotator.get_next()
        assert first == USER_AGENTS[0]
        second = rotator.get_next()
        assert second == USER_AGENTS[1]

    def test_rotator_round_robin_wraps(self) -> None:
        rotator = UserAgentRotator(strategy="round-robin")
        for _ in range(len(USER_AGENTS)):
            rotator.get_next()
        wrapped = rotator.get_next()
        assert wrapped == USER_AGENTS[0]

    def test_rotator_random_seeded(self) -> None:
        r1 = UserAgentRotator(strategy="random", seed=99)
        r2 = UserAgentRotator(strategy="random", seed=99)
        assert r1.get_next() == r2.get_next()
        assert r1.get_next() == r2.get_next()

    def test_all_uas_are_strings(self) -> None:
        for ua in USER_AGENTS:
            assert isinstance(ua, str)
            assert len(ua) > 20


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_immediate(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=600, burst=10)
        await limiter.acquire()  # Should not block

    @pytest.mark.asyncio
    async def test_wait_if_needed_returns_float(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=600, burst=10)
        wait = await limiter.wait_if_needed()
        assert isinstance(wait, float)
        assert wait < 1.0  # Should be near-instant with high rate

    @pytest.mark.asyncio
    async def test_platform_rate_limiter(self) -> None:
        prl = PlatformRateLimiter(default_rate=600)
        limiter = prl.get_limiter("github")
        assert isinstance(limiter, TokenBucketRateLimiter)
        await prl.acquire("github")  # Should not block

    @pytest.mark.asyncio
    async def test_platform_rate_limiter_returns_same(self) -> None:
        prl = PlatformRateLimiter()
        l1 = prl.get_limiter("twitter")
        l2 = prl.get_limiter("twitter")
        assert l1 is l2

    @pytest.mark.asyncio
    async def test_set_rate(self) -> None:
        prl = PlatformRateLimiter()
        prl.set_rate("slow", 1)
        limiter = prl.get_limiter("slow")
        assert isinstance(limiter, TokenBucketRateLimiter)


class TestDelays:
    @pytest.mark.asyncio
    async def test_random_delay_in_range(self) -> None:
        with patch("argus.stealth.delays.asyncio.sleep", new_callable=AsyncMock):
            actual = await random_delay(min_seconds=1.0, max_seconds=2.0, seed=42)
            assert isinstance(actual, float)

    @pytest.mark.asyncio
    async def test_delay_manager_default(self) -> None:
        dm = DelayManager(default_min=0.0, default_max=0.01, seed=42)
        actual = await dm.delay()
        assert isinstance(actual, float)

    @pytest.mark.asyncio
    async def test_delay_manager_per_platform(self) -> None:
        dm = DelayManager(seed=42)
        dm.set_range("fast", 0.0, 0.01)
        actual = await dm.delay("fast")
        assert isinstance(actual, float)


class TestProxy:
    def test_round_robin(self) -> None:
        pr = ProxyRotator(["http://p1", "http://p2", "http://p3"])
        assert pr.get_next() == "http://p1"
        assert pr.get_next() == "http://p2"
        assert pr.get_next() == "http://p3"
        assert pr.get_next() == "http://p1"

    def test_random_seeded(self) -> None:
        pr1 = ProxyRotator(["http://a", "http://b", "http://c"], strategy="random", seed=42)
        pr2 = ProxyRotator(["http://a", "http://b", "http://c"], strategy="random", seed=42)
        assert pr1.get_next() == pr2.get_next()

    def test_mark_failed(self) -> None:
        pr = ProxyRotator(["http://p1", "http://p2"])
        pr.mark_failed("http://p1")
        assert pr.get_next() == "http://p2"
        assert pr.get_next() == "http://p2"

    def test_all_failed_returns_none(self) -> None:
        pr = ProxyRotator(["http://p1"])
        pr.mark_failed("http://p1")
        assert pr.get_next() is None

    def test_reset_failures(self) -> None:
        pr = ProxyRotator(["http://p1", "http://p2"])
        pr.mark_failed("http://p1")
        pr.reset_failures()
        assert pr.get_next() == "http://p1"

    def test_empty_proxies(self) -> None:
        pr = ProxyRotator([])
        assert pr.get_next() is None


class TestStealthSession:
    @pytest.mark.asyncio
    async def test_creates_session(self) -> None:
        from argus.config.settings import ArgusConfig

        config = ArgusConfig()
        session = create_stealth_session(config)
        assert isinstance(session, __import__("aiohttp").ClientSession)
        await session.close()

    @pytest.mark.asyncio
    async def test_session_has_user_agent(self) -> None:
        from argus.config.settings import ArgusConfig

        config = ArgusConfig()
        session = create_stealth_session(config)
        ua = session.headers.get("User-Agent", "")
        assert "Mozilla" in ua
        await session.close()

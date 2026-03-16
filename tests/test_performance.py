"""Tests for performance optimization: connection pooling and caching."""

import tempfile
import time
import aiohttp
import pytest

from argus.storage.cache import ResponseCache


class TestResponseCache:
    def test_put_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=tmpdir, ttl_seconds=60)
            cache.put("https://example.com", "<html>test</html>")
            result = cache.get("https://example.com")
            assert result == "<html>test</html>"

    def test_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=tmpdir)
            assert cache.get("https://notcached.com") is None

    def test_ttl_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=tmpdir, ttl_seconds=0)
            cache.put("https://example.com", "data")
            time.sleep(0.1)
            assert cache.get("https://example.com") is None

    def test_disabled_cache(self):
        cache = ResponseCache(enabled=False)
        cache.put("https://example.com", "data")
        assert cache.get("https://example.com") is None

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=tmpdir)
            cache.put("https://a.com", "a")
            cache.put("https://b.com", "b")
            count = cache.clear()
            assert count == 2
            assert cache.get("https://a.com") is None

    def test_different_urls_different_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(cache_dir=tmpdir)
            cache.put("https://a.com", "data_a")
            cache.put("https://b.com", "data_b")
            assert cache.get("https://a.com") == "data_a"
            assert cache.get("https://b.com") == "data_b"


class TestConnectionPooling:
    @pytest.mark.asyncio
    async def test_tcp_connector_limits(self):
        """Verify TCPConnector is created with proper limits."""
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        assert connector.limit == 50
        assert connector.limit_per_host == 10
        await connector.close()

    @pytest.mark.asyncio
    async def test_session_with_connector(self):
        """Session with custom connector works."""
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        session = aiohttp.ClientSession(connector=connector)
        assert session.connector is not None
        assert session.connector.limit == 50
        await session.close()

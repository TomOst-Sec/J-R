"""Stealth aiohttp session factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from .user_agents import UserAgentRotator

if TYPE_CHECKING:
    from argus.config.settings import ArgusConfig


def create_stealth_session(config: ArgusConfig) -> aiohttp.ClientSession:
    """Create an aiohttp ClientSession with stealth headers and optional proxy.

    The returned session has a rotated User-Agent and standard browser headers.
    Proxy is configured via the connector if specified in config.
    """
    rotator = UserAgentRotator(strategy="random")
    user_agent = rotator.get_next()

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    connector = None
    if config.proxy.url:
        from aiohttp_socks import ProxyConnector

        connector = ProxyConnector.from_url(config.proxy.url)

    timeout = aiohttp.ClientTimeout(total=30)

    return aiohttp.ClientSession(
        headers=headers,
        connector=connector,
        timeout=timeout,
    )

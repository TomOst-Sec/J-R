"""BasePlatform abstract interface for Argus OSINT platform modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig
    from argus.models.agent import Connection
    from argus.models.profile import CandidateProfile, ContentItem, ProfileData


class BasePlatform(ABC):
    """Abstract base class for all platform modules.

    Subclasses must define `name`, `base_url`, and implement the abstract methods.
    """

    name: str
    base_url: str
    rate_limit_per_minute: int = 30
    requires_auth: bool = False
    requires_playwright: bool = False
    priority: int = 50

    def __init__(self, session: aiohttp.ClientSession, config: ArgusConfig) -> None:
        self.session = session
        self.config = config

    @abstractmethod
    async def check_username(self, username: str) -> bool | None:
        """Check if a username exists on this platform.

        Returns True if exists, False if not, None if unable to determine.
        """

    @abstractmethod
    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        """Search for a person by name, optionally filtered by location."""

    @abstractmethod
    async def scrape_profile(self, url: str) -> ProfileData | None:
        """Scrape profile data from a URL on this platform."""

    async def scrape_content(
        self, url: str, max_items: int = 50
    ) -> list[ContentItem]:
        """Scrape content/posts from a profile URL. Default returns empty list."""
        return []

    async def get_connections(self, url: str) -> list[Connection]:
        """Get connections/relationships from a profile URL. Default returns empty list."""
        return []

    async def initialize(self, config: ArgusConfig) -> None:
        """Called once before the platform is used. Override for setup logic."""

    async def shutdown(self) -> None:
        """Called on cleanup. Override for teardown logic."""

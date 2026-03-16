"""Tests for BasePlatform interface and PlatformRegistry."""

import pytest

from argus.config import ArgusConfig
from argus.config.settings import PlatformConfig
from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform
from argus.platforms.registry import PlatformRegistry


class MockPlatform(BasePlatform):
    """Concrete platform for testing."""

    name = "mock"
    base_url = "https://mock.example.com"

    async def check_username(self, username: str) -> bool | None:
        return username == "exists"

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return [
            CandidateProfile(
                platform=self.name,
                username=name.lower().replace(" ", ""),
                url=f"{self.base_url}/{name.lower().replace(' ', '')}",
            )
        ]

    async def scrape_profile(self, url: str) -> ProfileData | None:
        return ProfileData(username="testuser", display_name="Test User")


class AuthPlatform(BasePlatform):
    """Platform requiring authentication."""

    name = "auth_platform"
    base_url = "https://auth.example.com"
    requires_auth = True
    priority = 10

    async def check_username(self, username: str) -> bool | None:
        return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        return None


class PlaywrightPlatform(BasePlatform):
    """Platform requiring playwright."""

    name = "pw_platform"
    base_url = "https://pw.example.com"
    requires_playwright = True
    priority = 90

    async def check_username(self, username: str) -> bool | None:
        return True

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        return None


class TestBasePlatform:
    """Tests for BasePlatform abstract class."""

    def test_cannot_instantiate_directly(self):
        """BasePlatform is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BasePlatform(session=None, config=ArgusConfig())  # type: ignore[abstract]

    def test_class_attributes_defaults(self):
        """Check default class attributes."""
        assert MockPlatform.rate_limit_per_minute == 30
        assert MockPlatform.requires_auth is False
        assert MockPlatform.requires_playwright is False
        assert MockPlatform.priority == 50

    def test_class_attributes_override(self):
        """Subclass can override class attributes."""
        assert AuthPlatform.requires_auth is True
        assert AuthPlatform.priority == 10
        assert PlaywrightPlatform.requires_playwright is True
        assert PlaywrightPlatform.priority == 90

    @pytest.fixture
    def config(self):
        return ArgusConfig()

    @pytest.fixture
    def mock_platform(self, config):
        return MockPlatform(session=None, config=config)  # type: ignore[arg-type]

    async def test_check_username(self, mock_platform):
        assert await mock_platform.check_username("exists") is True
        assert await mock_platform.check_username("nope") is False

    async def test_search_name(self, mock_platform):
        results = await mock_platform.search_name("John Doe")
        assert len(results) == 1
        assert results[0].platform == "mock"
        assert results[0].username == "johndoe"

    async def test_scrape_profile(self, mock_platform):
        result = await mock_platform.scrape_profile("https://mock.example.com/testuser")
        assert result is not None
        assert result.username == "testuser"

    async def test_scrape_content_default_noop(self, mock_platform):
        """Default scrape_content returns empty list."""
        result = await mock_platform.scrape_content("https://example.com/user")
        assert result == []

    async def test_get_connections_default_noop(self, mock_platform):
        """Default get_connections returns empty list."""
        result = await mock_platform.get_connections("https://example.com/user")
        assert result == []

    async def test_initialize_and_shutdown(self, mock_platform):
        """Initialize and shutdown are callable without error."""
        await mock_platform.initialize(ArgusConfig())
        await mock_platform.shutdown()

    def test_stores_session_and_config(self, config):
        """Constructor stores session and config."""
        platform = MockPlatform(session=None, config=config)  # type: ignore[arg-type]
        assert platform.session is None
        assert platform.config is config


class TestPlatformRegistry:
    """Tests for PlatformRegistry."""

    def test_register_and_get(self):
        """Can register and retrieve a platform."""
        registry = PlatformRegistry()
        registry.register(MockPlatform)
        assert registry.get_platform("mock") is MockPlatform

    def test_get_missing(self):
        """Getting unknown platform returns None."""
        registry = PlatformRegistry()
        assert registry.get_platform("nonexistent") is None

    def test_list_platforms(self):
        """list_platforms returns registered names."""
        registry = PlatformRegistry()
        registry.register(MockPlatform)
        registry.register(AuthPlatform)
        names = registry.list_platforms()
        assert "mock" in names
        assert "auth_platform" in names

    def test_get_enabled_platforms_all_enabled(self):
        """All platforms enabled when no platform config."""
        registry = PlatformRegistry()
        registry.register(MockPlatform)
        registry.register(AuthPlatform)
        config = ArgusConfig()
        enabled = registry.get_enabled_platforms(config)
        assert len(enabled) == 2

    def test_get_enabled_platforms_filters_disabled(self):
        """Disabled platforms are filtered out."""
        registry = PlatformRegistry()
        registry.register(MockPlatform)
        registry.register(AuthPlatform)
        config = ArgusConfig(
            platforms={"auth_platform": PlatformConfig(enabled=False)}
        )
        enabled = registry.get_enabled_platforms(config)
        assert len(enabled) == 1
        assert enabled[0] is MockPlatform

    def test_discover_platforms(self):
        """discover_platforms finds subclasses in the platforms directory."""
        registry = PlatformRegistry()
        discovered = registry.discover_platforms()
        # Should find at least nothing if no modules in platforms/ yet
        assert isinstance(discovered, dict)

    def test_enabled_sorted_by_priority(self):
        """Enabled platforms are sorted by priority descending."""
        registry = PlatformRegistry()
        registry.register(MockPlatform)       # priority 50
        registry.register(AuthPlatform)       # priority 10
        registry.register(PlaywrightPlatform)  # priority 90
        config = ArgusConfig()
        enabled = registry.get_enabled_platforms(config)
        assert enabled[0] is PlaywrightPlatform
        assert enabled[1] is MockPlatform
        assert enabled[2] is AuthPlatform

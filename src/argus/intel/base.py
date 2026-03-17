"""Base class for intelligence data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from argus.models.intel import IntelResult, IntelSelector

if TYPE_CHECKING:
    import aiohttp

    from argus.config.settings import ArgusConfig


class BaseIntelSource(ABC):
    """Abstract base class for all intelligence data sources.

    Subclasses must define `name`, `source_type`, and implement `query()`.
    """

    name: str
    source_type: str  # "breach", "dns", "whois", "cert", "identity", "paste", "records"
    requires_api_key: bool = False
    rate_limit_per_minute: int = 30

    def __init__(
        self,
        session: aiohttp.ClientSession,
        config: ArgusConfig,
    ) -> None:
        self.session = session
        self.config = config

    @abstractmethod
    async def query(self, selector: IntelSelector) -> list[IntelResult]:
        """Query this source with the given selector.

        Returns a list of IntelResult objects.
        """

    async def is_available(self) -> bool:
        """Check if this source is available (API key present, service reachable, etc.)."""
        if self.requires_api_key:
            key = self._get_api_key()
            return key is not None and len(key) > 0
        return True

    def _get_api_key(self) -> str | None:
        """Get the API key for this source from config."""
        intel_cfg = getattr(self.config, "intel", None)
        if intel_cfg is None:
            return None
        key_attr = f"{self.name}_api_key"
        return getattr(intel_cfg, key_attr, None)

    async def initialize(self) -> None:
        """Setup hook."""

    async def shutdown(self) -> None:
        """Cleanup hook."""


class IntelSourceRegistry:
    """Registry for intelligence data sources, similar to PlatformRegistry."""

    def __init__(self) -> None:
        self._sources: dict[str, type[BaseIntelSource]] = {}

    def register(self, source_cls: type[BaseIntelSource]) -> None:
        self._sources[source_cls.name] = source_cls

    def discover_sources(self) -> dict[str, type[BaseIntelSource]]:
        """Auto-discover BaseIntelSource subclasses in intel/sources/."""
        import importlib
        import pkgutil

        from argus.intel import sources as sources_pkg

        for importer, modname, ispkg in pkgutil.iter_modules(
            sources_pkg.__path__, sources_pkg.__name__ + "."
        ):
            try:
                mod = importlib.import_module(modname)
            except ImportError:
                continue
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseIntelSource)
                    and attr is not BaseIntelSource
                    and hasattr(attr, "name")
                ):
                    self._sources[attr.name] = attr

        return self._sources

    def list_sources(self) -> list[str]:
        return sorted(self._sources.keys())

    def get_source(self, name: str) -> type[BaseIntelSource] | None:
        return self._sources.get(name)

    def get_sources_by_type(self, source_type: str) -> list[type[BaseIntelSource]]:
        return [s for s in self._sources.values() if s.source_type == source_type]

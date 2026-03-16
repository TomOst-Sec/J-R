"""Platform registry with auto-discovery for Argus OSINT platform."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from argus.platforms.base import BasePlatform

if TYPE_CHECKING:
    from argus.config.settings import ArgusConfig


class PlatformRegistry:
    """Registry for platform modules with auto-discovery."""

    def __init__(self) -> None:
        self._platforms: dict[str, type[BasePlatform]] = {}

    def register(self, platform_cls: type[BasePlatform]) -> None:
        """Register a platform class by its name attribute."""
        self._platforms[platform_cls.name] = platform_cls

    def get_platform(self, name: str) -> type[BasePlatform] | None:
        """Get a registered platform class by name."""
        return self._platforms.get(name)

    def list_platforms(self) -> list[str]:
        """Return names of all registered platforms."""
        return list(self._platforms.keys())

    def get_enabled_platforms(self, config: ArgusConfig) -> list[type[BasePlatform]]:
        """Return platform classes that are enabled in config, sorted by priority descending."""
        enabled = []
        for name, cls in self._platforms.items():
            platform_config = config.platforms.get(name)
            if platform_config is None or platform_config.enabled:
                enabled.append(cls)
        return sorted(enabled, key=lambda c: c.priority, reverse=True)

    def discover_platforms(self) -> dict[str, type[BasePlatform]]:
        """Scan argus/platforms/ for BasePlatform subclasses and register them.

        Skips files starting with '_' and base.py/registry.py.
        """
        skip_names = {"base", "registry"}
        platforms_dir = Path(__file__).parent

        for module_info in pkgutil.iter_modules([str(platforms_dir)]):
            if module_info.name.startswith("_") or module_info.name in skip_names:
                continue
            try:
                module = importlib.import_module(f"argus.platforms.{module_info.name}")
                for _attr_name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BasePlatform)
                        and obj is not BasePlatform
                        and hasattr(obj, "name")
                    ):
                        self.register(obj)
            except Exception:  # noqa: BLE001
                continue

        return dict(self._platforms)

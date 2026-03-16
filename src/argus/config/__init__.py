"""Argus configuration system."""

from .loader import load_config
from .settings import ArgusConfig

_config: ArgusConfig | None = None


def get_config() -> ArgusConfig:
    """Return the singleton ArgusConfig, loading defaults if needed."""
    global _config  # noqa: PLW0603
    if _config is None:
        _config = load_config()
    return _config


__all__ = ["ArgusConfig", "get_config", "load_config"]

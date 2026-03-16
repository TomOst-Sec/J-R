"""Configuration loader with layered resolution."""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any

from .settings import ArgusConfig

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
_ARGUS_ENV_PREFIX = "ARGUS_"


def _interpolate_env_vars(value: Any) -> Any:
    """Replace ${VAR} placeholders in string values with environment variables."""
    if isinstance(value, str):
        return _ENV_VAR_PATTERN.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)), value
        )
    if isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env_vars(v) for v in value]
    return value


def _collect_env_overrides() -> dict[str, Any]:
    """Collect ARGUS_* env vars and map to nested config keys.

    Example: ARGUS_GENERAL_DEFAULT_THRESHOLD=0.6 -> {"general": {"default_threshold": 0.6}}
    """
    overrides: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(_ARGUS_ENV_PREFIX):
            continue
        parts = key[len(_ARGUS_ENV_PREFIX) :].lower().split("_", 1)
        if len(parts) < 2:
            continue
        section, field = parts[0], parts[1]
        overrides.setdefault(section, {})[field] = _coerce_value(value)
    return overrides


def _coerce_value(value: str) -> Any:
    """Coerce string env var values to appropriate Python types."""
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _find_config_file() -> Path | None:
    """Find argus.toml in standard locations."""
    candidates = [
        Path("argus.toml"),
        Path.home() / ".argus" / "argus.toml",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config(cli_overrides: dict[str, Any] | None = None) -> ArgusConfig:
    """Load configuration with layered resolution.

    Priority (highest to lowest): CLI flags > env vars > ./argus.toml > ~/.argus/argus.toml > defaults
    """
    data: dict[str, Any] = {}

    # Layer 1: Load from file
    config_path = _find_config_file()
    if config_path is not None:
        with config_path.open("rb") as f:
            file_data = tomllib.load(f)
        data = _interpolate_env_vars(file_data)

    # Layer 2: Apply env var overrides
    env_overrides = _collect_env_overrides()
    if env_overrides:
        data = _deep_merge(data, env_overrides)

    # Layer 3: Apply CLI overrides
    if cli_overrides:
        data = _deep_merge(data, cli_overrides)

    return ArgusConfig(**data)

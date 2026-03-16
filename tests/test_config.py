"""Tests for the configuration system."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from argus.config import ArgusConfig, load_config
from argus.config.loader import _coerce_value, _interpolate_env_vars


class TestDefaults:
    """Config loads with sane defaults when no file or env is present."""

    def test_default_config_loads(self) -> None:
        cfg = load_config()
        assert isinstance(cfg, ArgusConfig)

    def test_default_threshold(self) -> None:
        cfg = load_config()
        assert cfg.general.default_threshold == 0.45

    def test_default_stealth(self) -> None:
        cfg = load_config()
        assert cfg.stealth.min_delay == 2.0
        assert cfg.stealth.max_delay == 5.0

    def test_default_verification_weights(self) -> None:
        cfg = load_config()
        assert cfg.verification.signal_weights["photo"] == 0.35

    def test_default_platforms_empty(self) -> None:
        cfg = load_config()
        assert cfg.platforms == {}


class TestFileLoading:
    """Config loads correctly from a TOML file."""

    def test_load_from_toml(self, tmp_path: Path) -> None:
        toml_content = b"""
[general]
default_threshold = 0.7
max_concurrent_requests = 20

[platforms.twitter]
enabled = true
rate_limit_per_minute = 15
"""
        toml_file = tmp_path / "argus.toml"
        toml_file.write_bytes(toml_content)

        with patch("argus.config.loader._find_config_file", return_value=toml_file):
            cfg = load_config()

        assert cfg.general.default_threshold == 0.7
        assert cfg.general.max_concurrent_requests == 20
        assert cfg.platforms["twitter"].rate_limit_per_minute == 15


class TestEnvVarInterpolation:
    """${VAR} placeholders in TOML values resolve to env vars."""

    def test_string_interpolation(self) -> None:
        with patch.dict(os.environ, {"MY_KEY": "secret123"}):
            result = _interpolate_env_vars("${MY_KEY}")
        assert result == "secret123"

    def test_nested_dict_interpolation(self) -> None:
        with patch.dict(os.environ, {"API_KEY": "k123"}):
            result = _interpolate_env_vars({"credentials": {"key": "${API_KEY}"}})
        assert result == {"credentials": {"key": "k123"}}

    def test_missing_env_var_preserved(self) -> None:
        result = _interpolate_env_vars("${NONEXISTENT_VAR_XYZZY}")
        assert result == "${NONEXISTENT_VAR_XYZZY}"

    def test_interpolation_in_toml(self, tmp_path: Path) -> None:
        toml_content = b"""
[llm]
provider = "openai"
api_key = "${TEST_ARGUS_LLM_KEY}"
"""
        toml_file = tmp_path / "argus.toml"
        toml_file.write_bytes(toml_content)

        with (
            patch.dict(os.environ, {"TEST_ARGUS_LLM_KEY": "sk-test"}),
            patch("argus.config.loader._find_config_file", return_value=toml_file),
        ):
            cfg = load_config()

        assert cfg.llm.api_key == "sk-test"


class TestEnvVarOverrides:
    """ARGUS_* env vars override config values."""

    def test_override_threshold(self) -> None:
        with patch.dict(os.environ, {"ARGUS_GENERAL_DEFAULT_THRESHOLD": "0.8"}):
            cfg = load_config()
        assert cfg.general.default_threshold == 0.8

    def test_override_bool(self) -> None:
        with patch.dict(os.environ, {"ARGUS_STEALTH_USER_AGENT_ROTATION": "false"}):
            cfg = load_config()
        assert cfg.stealth.user_agent_rotation is False


class TestCLIOverrides:
    """CLI overrides take highest priority."""

    def test_cli_overrides_defaults(self) -> None:
        cfg = load_config(cli_overrides={"general": {"default_threshold": 0.9}})
        assert cfg.general.default_threshold == 0.9

    def test_cli_overrides_env(self) -> None:
        with patch.dict(os.environ, {"ARGUS_GENERAL_DEFAULT_THRESHOLD": "0.6"}):
            cfg = load_config(cli_overrides={"general": {"default_threshold": 0.99}})
        assert cfg.general.default_threshold == 0.99


class TestCoercion:
    """Value coercion from string env vars to Python types."""

    def test_bool_true(self) -> None:
        assert _coerce_value("true") is True
        assert _coerce_value("yes") is True

    def test_bool_false(self) -> None:
        assert _coerce_value("false") is False
        assert _coerce_value("no") is False

    def test_int(self) -> None:
        assert _coerce_value("42") == 42

    def test_float(self) -> None:
        assert _coerce_value("0.75") == 0.75

    def test_string(self) -> None:
        assert _coerce_value("hello") == "hello"

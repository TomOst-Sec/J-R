"""Argus configuration models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GeneralConfig(BaseModel):
    """General application settings."""

    model_config = ConfigDict(extra="forbid")

    default_threshold: float = 0.45
    max_concurrent_requests: int = 10
    output_format: str = "table"
    language: str = "en"


class PlatformConfig(BaseModel):
    """Per-platform configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    rate_limit_per_minute: int = 30
    credentials: dict[str, str] | None = None


class ProxyConfig(BaseModel):
    """Proxy settings."""

    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    rotation_strategy: str = "round-robin"
    auth: dict[str, str] | None = None


class LLMConfig(BaseModel):
    """LLM provider settings."""

    model_config = ConfigDict(extra="forbid")

    provider: str = "none"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class VerificationConfig(BaseModel):
    """Verification signal settings."""

    model_config = ConfigDict(extra="forbid")

    signal_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "photo": 0.35,
            "bio": 0.20,
            "timezone": 0.15,
            "username": 0.10,
            "connections": 0.10,
            "writing_style": 0.10,
        }
    )
    minimum_threshold: float = 0.30
    photo_matching_enabled: bool = True
    face_recognition_enabled: bool = False


class OutputConfig(BaseModel):
    """Output settings."""

    model_config = ConfigDict(extra="forbid")

    default_format: str = "table"
    report_template: str | None = None
    include_raw_data: bool = False


class StealthConfig(BaseModel):
    """Stealth/anti-detection settings."""

    model_config = ConfigDict(extra="forbid")

    user_agent_rotation: bool = True
    min_delay: float = 2.0
    max_delay: float = 5.0
    respect_robots_txt: bool = False


class ArgusConfig(BaseModel):
    """Root configuration for the Argus platform."""

    model_config = ConfigDict(extra="forbid")

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    platforms: dict[str, PlatformConfig] = Field(default_factory=dict)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    stealth: StealthConfig = Field(default_factory=StealthConfig)

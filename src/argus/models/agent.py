"""Agent models for Argus OSINT platform."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from argus.models.target import TargetInput
from argus.models.verification import VerificationResult


class AgentInput(BaseModel):
    model_config = ConfigDict(strict=False)

    target: TargetInput
    config: dict[str, Any] | None = None
    options: dict[str, Any] | None = None


class AgentOutput(BaseModel):
    model_config = ConfigDict(strict=False)

    target_name: str
    agent_name: str
    results: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None
    duration_seconds: float | None = None


class Connection(BaseModel):
    model_config = ConfigDict(strict=False)

    platform: str
    content_snippet: str
    relationship_type: str
    confidence: float
    url: str | None = None
    timestamp: datetime | None = None


class TopicScore(BaseModel):
    model_config = ConfigDict(strict=False)

    topic: str
    score: float
    evidence: list[str] = Field(default_factory=list)
    trend: str | None = None


class ResolverOutput(AgentOutput):
    accounts: list[VerificationResult] = Field(default_factory=list)


class LinkerOutput(AgentOutput):
    connections: list[Connection] = Field(default_factory=list)


class ProfilerOutput(AgentOutput):
    dimensions: dict[str, list[TopicScore]] = Field(default_factory=dict)

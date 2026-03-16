"""Investigation models for Argus OSINT platform."""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from argus.models.agent import LinkerOutput, ProfilerOutput, ResolverOutput
from argus.models.target import Target


class Investigation(BaseModel):
    model_config = ConfigDict(strict=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    target: Target
    status: Literal["running", "completed", "interrupted", "failed"] = "running"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    resolver_output: ResolverOutput | None = None
    linker_output: LinkerOutput | None = None
    profiler_output: ProfilerOutput | None = None

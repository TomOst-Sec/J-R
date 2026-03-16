"""Target models for Argus OSINT platform."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class TargetInput(BaseModel):
    model_config = ConfigDict(strict=False)

    name: str
    location: str | None = None
    seed_urls: list[str] = Field(default_factory=list)
    email: str | None = None
    username_hint: str | None = None
    phone: str | None = None


class Target(BaseModel):
    model_config = ConfigDict(strict=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    location: str | None = None
    seed_urls: list[str] = Field(default_factory=list)
    email: str | None = None
    username_hint: str | None = None
    phone: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

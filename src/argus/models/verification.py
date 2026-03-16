"""Verification models for Argus OSINT platform."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from argus.models.profile import CandidateProfile


class SignalResult(BaseModel):
    model_config = ConfigDict(strict=False)

    signal_name: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float
    evidence: str
    details: dict | None = None


class VerificationResult(BaseModel):
    model_config = ConfigDict(strict=False)

    candidate: CandidateProfile
    signals: list[SignalResult] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    threshold_label: Literal["discarded", "possible", "likely", "confirmed"]

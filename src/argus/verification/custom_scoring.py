"""Custom scoring models — user-defined signal weights and rules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoringRule(BaseModel):
    """A custom scoring rule that maps signal conditions to score adjustments."""

    model_config = ConfigDict(strict=False)

    name: str
    signal_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    adjustment: float  # positive = boost, negative = penalty


class ScoringProfile(BaseModel):
    """A named collection of signal weights and scoring rules."""

    model_config = ConfigDict(strict=False)

    name: str
    description: str = ""
    weights: dict[str, float] = Field(default_factory=dict)
    rules: list[ScoringRule] = Field(default_factory=list)
    minimum_threshold: float = 0.30


# Built-in profiles
CONSERVATIVE = ScoringProfile(
    name="conservative",
    description="High-confidence only — fewer results, higher precision",
    weights={
        "photo": 0.45,
        "bio": 0.25,
        "username": 0.10,
        "mutual_connections": 0.20,
    },
    minimum_threshold=0.60,
)

AGGRESSIVE = ScoringProfile(
    name="aggressive",
    description="Cast a wide net — more results, lower precision",
    weights={
        "photo": 0.25,
        "bio": 0.15,
        "username": 0.30,
        "mutual_connections": 0.10,
        "timezone": 0.10,
        "writing_style": 0.10,
    },
    minimum_threshold=0.20,
)

BALANCED = ScoringProfile(
    name="balanced",
    description="Default balanced scoring",
    weights={
        "photo": 0.35,
        "bio": 0.20,
        "username": 0.10,
        "mutual_connections": 0.10,
        "timezone": 0.15,
        "writing_style": 0.10,
    },
    minimum_threshold=0.30,
)

BUILTIN_PROFILES: dict[str, ScoringProfile] = {
    "conservative": CONSERVATIVE,
    "aggressive": AGGRESSIVE,
    "balanced": BALANCED,
}


def apply_rules(base_score: float, signals: dict[str, float], rules: list[ScoringRule]) -> float:
    """Apply custom rules to adjust a base confidence score."""
    score = base_score
    for rule in rules:
        signal_value = signals.get(rule.signal_name, 0.0)
        if _evaluate_condition(signal_value, rule.condition, rule.threshold):
            score += rule.adjustment
    return max(0.0, min(1.0, score))


def _evaluate_condition(value: float, condition: str, threshold: float) -> bool:
    """Evaluate a scoring rule condition."""
    if condition == "gt":
        return value > threshold
    elif condition == "lt":
        return value < threshold
    elif condition == "eq":
        return abs(value - threshold) < 0.001
    elif condition == "gte":
        return value >= threshold
    elif condition == "lte":
        return value <= threshold
    return False


def get_profile(name: str) -> ScoringProfile | None:
    """Get a built-in scoring profile by name."""
    return BUILTIN_PROFILES.get(name)


def list_profiles() -> list[str]:
    """List available built-in scoring profile names."""
    return list(BUILTIN_PROFILES.keys())

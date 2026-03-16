"""Profile models for Argus OSINT platform."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileData(BaseModel):
    model_config = ConfigDict(strict=False)

    username: str
    display_name: str | None = None
    bio: str | None = None
    location: str | None = None
    profile_photo_url: str | None = None
    profile_photo_hash: str | None = None
    links: list[str] = Field(default_factory=list)
    join_date: datetime | None = None
    follower_count: int | None = None
    following_count: int | None = None
    raw_json: dict | None = None


class CandidateProfile(BaseModel):
    model_config = ConfigDict(strict=False)

    platform: str
    username: str
    url: str
    exists: bool | None = None
    scraped_data: ProfileData | None = None


class ContentItem(BaseModel):
    model_config = ConfigDict(strict=False)

    id: str
    platform: str
    text: str
    timestamp: datetime | None = None
    content_type: str = "post"
    url: str | None = None
    engagement: dict | None = None
    metadata: dict | None = None

"""Mock platform implementation for testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

if TYPE_CHECKING:
    pass


class MockTestPlatform(BasePlatform):
    """A test platform for fixture use."""

    name = "mock_test"
    base_url = "https://mocktest.example.com"

    async def check_username(self, username: str) -> bool | None:
        return username == "testuser"

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        return [
            CandidateProfile(
                platform=self.name,
                username=name.lower().replace(" ", "_"),
                url=f"{self.base_url}/u/{name.lower().replace(' ', '_')}",
            )
        ]

    async def scrape_profile(self, url: str) -> ProfileData | None:
        return ProfileData(username="testuser", display_name="Mock Test User")

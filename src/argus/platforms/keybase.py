"""Keybase platform module using public API."""

from __future__ import annotations

import re

from argus.models.profile import CandidateProfile, ProfileData
from argus.platforms.base import BasePlatform

_API_BASE = "https://keybase.io/_/api/1.0"
_USERNAME_RE = re.compile(r"keybase\.io/([^/?#]+)")


class KeybasePlatform(BasePlatform):
    """Keybase platform using the public lookup API."""

    name = "keybase"
    base_url = "https://keybase.io"
    rate_limit_per_minute = 30
    requires_auth = False
    requires_playwright = False
    priority = 70

    async def check_username(self, username: str) -> bool | None:
        try:
            async with self.session.get(
                f"{_API_BASE}/user/lookup.json",
                params={"username": username},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                status = data.get("status", {})
                return status.get("code") == 0
        except Exception:
            return None

    async def search_name(
        self, name: str, location: str | None = None
    ) -> list[CandidateProfile]:
        # Keybase has no public name-based search API
        return []

    async def scrape_profile(self, url: str) -> ProfileData | None:
        username = _extract_username(url)
        if not username:
            return None
        try:
            async with self.session.get(
                f"{_API_BASE}/user/lookup.json",
                params={"username": username},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                status = data.get("status", {})
                if status.get("code") != 0:
                    return None
                them = data.get("them", {})
                profile = them.get("profile", {})
                pictures = them.get("pictures", {})
                primary = pictures.get("primary", {})

                # Extract linked accounts from proofs_summary
                links = [f"{self.base_url}/{username}"]
                proofs = them.get("proofs_summary", {}).get("all", [])
                for proof in proofs:
                    service_url = proof.get("service_url")
                    if service_url:
                        links.append(service_url)

                return ProfileData(
                    username=them.get("basics", {}).get("username", username),
                    display_name=profile.get("full_name"),
                    bio=profile.get("bio"),
                    profile_photo_url=primary.get("url"),
                    links=links,
                    raw_json=them,
                )
        except Exception:
            return None


def _extract_username(url: str) -> str | None:
    """Extract username from a Keybase profile URL."""
    match = _USERNAME_RE.search(url)
    if not match:
        return None
    username = match.group(1)
    return username.rstrip("/")

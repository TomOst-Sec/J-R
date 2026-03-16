"""Mutual connections verification signal — cross-platform link detection."""

from __future__ import annotations

from urllib.parse import urlparse

from argus.models.profile import CandidateProfile, ProfileData
from argus.models.verification import SignalResult
from argus.verification.signals import BaseSignal

# Known platform domains for cross-reference detection
_PLATFORM_DOMAINS = {
    "github.com": "github",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "reddit.com": "reddit",
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "youtube.com": "youtube",
    "medium.com": "medium",
    "news.ycombinator.com": "hackernews",
    "mastodon.social": "mastodon",
    "t.me": "telegram",
    "tiktok.com": "tiktok",
    "discord.com": "discord",
}


def _extract_platform_from_url(url: str) -> str | None:
    """Extract platform name from a URL."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        for domain, platform in _PLATFORM_DOMAINS.items():
            if host == domain or host.endswith("." + domain):
                return platform
    except Exception:
        pass
    return None


def _extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from text content."""
    import re

    return re.findall(r"https?://[^\s\)\]\"'<>]+", text)


class MutualConnectionsSignal(BaseSignal):
    """Detect cross-platform connections between discovered accounts."""

    name = "mutual_connections"
    default_weight = 0.10

    async def compute(
        self,
        candidate: CandidateProfile,
        seed_profiles: list[ProfileData],
        all_candidates: list[CandidateProfile],
    ) -> SignalResult:
        evidence_parts: list[str] = []
        max_score = 0.0

        profile = candidate.scraped_data
        if not profile:
            return SignalResult(
                signal_name=self.name,
                score=0.0,
                weight=self.default_weight,
                evidence="No scraped data available",
            )

        # Collect all links from the candidate's profile
        candidate_links = set(profile.links or [])
        if profile.bio:
            candidate_links.update(_extract_urls_from_text(profile.bio))

        # Check for cross-platform links
        other_platforms = {
            c.platform: c
            for c in all_candidates
            if c.platform != candidate.platform and c.scraped_data
        }

        for link in candidate_links:
            linked_platform = _extract_platform_from_url(link)
            if linked_platform and linked_platform in other_platforms:
                other = other_platforms[linked_platform]
                # Check if the link points to the same username
                if other.username.lower() in link.lower():
                    evidence_parts.append(
                        f"Cross-platform link: {candidate.platform} links to {linked_platform}/{other.username}"
                    )
                    max_score = max(max_score, 0.9)
                else:
                    evidence_parts.append(
                        f"Links to {linked_platform} (unverified match)"
                    )
                    max_score = max(max_score, 0.4)

        # Check for shared external links (non-platform URLs)
        if profile.links:
            external_links = {
                url
                for url in profile.links
                if _extract_platform_from_url(url) is None
            }
            for other_candidate in all_candidates:
                if other_candidate.platform == candidate.platform:
                    continue
                other_profile = other_candidate.scraped_data
                if not other_profile or not other_profile.links:
                    continue
                other_external = {
                    url
                    for url in other_profile.links
                    if _extract_platform_from_url(url) is None
                }
                shared = external_links & other_external
                if shared:
                    evidence_parts.append(
                        f"Shared external link with {other_candidate.platform}: {next(iter(shared))}"
                    )
                    max_score = max(max_score, 0.85)

        # Check for username mentions in bio
        if profile.bio:
            bio_lower = profile.bio.lower()
            for other_platform, other_candidate in other_platforms.items():
                if other_candidate.username.lower() in bio_lower:
                    evidence_parts.append(
                        f"Bio mentions {other_platform} username '{other_candidate.username}'"
                    )
                    max_score = max(max_score, 0.6)

        if not evidence_parts:
            evidence = "No cross-platform connections detected"
        else:
            evidence = "; ".join(evidence_parts)

        return SignalResult(
            signal_name=self.name,
            score=max_score,
            weight=self.default_weight,
            evidence=evidence,
        )

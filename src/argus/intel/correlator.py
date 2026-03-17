"""Cross-source correlation engine -- identity clustering and timeline building."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from argus.models.intel import IdentityCluster, IntelResult

logger = logging.getLogger(__name__)


class CorrelationEngine:
    """Match usernames, emails, and display names across sources to build identity clusters."""

    async def correlate(
        self,
        name: str,
        accounts: list[dict[str, Any]],
        intel_results: list[IntelResult],
    ) -> IdentityCluster:
        """Correlate data across sources into an IdentityCluster.

        Parameters
        ----------
        name:
            The target person's name.
        accounts:
            List of account dicts (platform, username, url, display_name, email, etc.).
        intel_results:
            Raw IntelResult objects from various sources.

        Returns
        -------
        IdentityCluster with matched identities, evidence, and timeline.
        """
        cluster_id = hashlib.sha256(name.lower().encode()).hexdigest()[:16]
        cluster = IdentityCluster(cluster_id=cluster_id)

        # Collect all usernames, emails, names
        all_usernames: set[str] = set()
        all_emails: set[str] = set()
        all_names: set[str] = set()
        all_names.add(name)

        for acct in accounts:
            if acct.get("username"):
                all_usernames.add(acct["username"])
            if acct.get("email"):
                all_emails.add(acct["email"])
            if acct.get("display_name"):
                all_names.add(acct["display_name"])
            cluster.accounts.append(acct)

        # Extract data from intel results
        for ir in intel_results:
            if ir.data.get("email"):
                all_emails.add(ir.data["email"])
            if ir.data.get("username"):
                all_usernames.add(ir.data["username"])
            if ir.data.get("display_name"):
                all_names.add(ir.data["display_name"])
            # Build timeline entries from timestamps
            if ir.timestamp:
                cluster.timeline.append(
                    {
                        "source": ir.source,
                        "timestamp": ir.timestamp.isoformat(),
                        "event": f"Data from {ir.source}",
                    }
                )

        cluster.usernames = sorted(all_usernames)
        cluster.emails = sorted(all_emails)
        cluster.names = sorted(all_names)

        # Fuzzy matching for confidence and evidence
        evidence: list[str] = []
        confidence_signals: list[float] = []

        # Username overlap detection
        username_matches = self._find_similar_strings(list(all_usernames))
        for match in username_matches:
            evidence.append(f"Similar usernames: {match[0]} ~ {match[1]} (score: {match[2]:.2f})")
            confidence_signals.append(match[2])

        # Name matching across display names
        name_matches = self._find_similar_strings(list(all_names))
        for match in name_matches:
            evidence.append(f"Similar names: {match[0]} ~ {match[1]} (score: {match[2]:.2f})")
            confidence_signals.append(match[2])

        # Email domain grouping
        domains: dict[str, list[str]] = {}
        for email in all_emails:
            domain = email.split("@")[-1] if "@" in email else ""
            domains.setdefault(domain, []).append(email)
        for domain, emails in domains.items():
            if len(emails) > 1:
                evidence.append(f"Multiple emails on {domain}: {', '.join(emails)}")
                confidence_signals.append(0.6)

        # Cross-platform presence
        platforms = {acct.get("platform") for acct in accounts if acct.get("platform")}
        if len(platforms) > 1:
            evidence.append(f"Present on {len(platforms)} platforms: {', '.join(sorted(platforms))}")
            confidence_signals.append(min(0.3 * len(platforms), 0.9))

        cluster.evidence = evidence
        cluster.confidence = (
            sum(confidence_signals) / len(confidence_signals)
            if confidence_signals
            else 0.0
        )

        # Sort timeline by timestamp
        cluster.timeline.sort(key=lambda t: t.get("timestamp", ""))

        return cluster

    @staticmethod
    def _find_similar_strings(strings: list[str]) -> list[tuple[str, str, float]]:
        """Find pairs of similar strings using jellyfish for fuzzy matching.

        Returns list of (str_a, str_b, similarity_score) tuples.
        """
        matches: list[tuple[str, str, float]] = []
        if len(strings) < 2:
            return matches

        try:
            import jellyfish
        except ImportError:
            logger.debug("jellyfish not installed -- skipping fuzzy matching")
            return matches

        for i in range(len(strings)):
            for j in range(i + 1, len(strings)):
                a = strings[i].lower()
                b = strings[j].lower()
                if a == b:
                    continue
                score = jellyfish.jaro_winkler_similarity(a, b)
                if score >= 0.75:
                    matches.append((strings[i], strings[j], score))

        return matches

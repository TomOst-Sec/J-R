"""CSV report renderer."""

from __future__ import annotations

import csv
import io

from argus.models.investigation import Investigation


def generate_csv(investigation: Investigation) -> str:
    """Generate a flat CSV export of discovered accounts."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["platform", "username", "url", "confidence", "label", "bio", "location"])

    resolver = investigation.resolver_output
    if resolver:
        for vr in resolver.accounts:
            bio = ""
            location = ""
            if vr.candidate.scraped_data:
                bio = (vr.candidate.scraped_data.bio or "")[:200]
                location = vr.candidate.scraped_data.location or ""
            writer.writerow([
                vr.candidate.platform,
                vr.candidate.username,
                vr.candidate.url,
                f"{vr.confidence:.2f}",
                vr.threshold_label,
                bio,
                location,
            ])

    return output.getvalue()

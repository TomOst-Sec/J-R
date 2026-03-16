"""Markdown report renderer."""

from __future__ import annotations

from argus.models.investigation import Investigation


def generate_markdown(investigation: Investigation) -> str:
    """Generate a Markdown investigation report."""
    lines: list[str] = []
    target = investigation.target
    resolver = investigation.resolver_output
    linker = investigation.linker_output
    profiler = investigation.profiler_output

    lines.append(f"# Investigation Report: {target.name}")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    account_count = len(resolver.accounts) if resolver else 0
    if account_count > 0:
        platforms = {a.candidate.platform for a in resolver.accounts}
        lines.append(
            f"Investigation of **{target.name}** discovered {account_count} "
            f"account(s) across {len(platforms)} platform(s). "
        )
        high_conf = [a for a in resolver.accounts if a.confidence >= 0.70]
        if high_conf:
            lines.append(
                f"{len(high_conf)} account(s) matched with high confidence (≥70%)."
            )
    else:
        lines.append(f"Investigation of **{target.name}** found 0 accounts above threshold.")
    lines.append("")

    # Discovered Accounts
    lines.append("## Discovered Accounts")
    lines.append("")
    if resolver and resolver.accounts:
        lines.append("| Platform | Username | URL | Confidence | Label |")
        lines.append("|----------|----------|-----|------------|-------|")
        for vr in resolver.accounts:
            conf_pct = f"{vr.confidence:.0%}"
            lines.append(
                f"| {vr.candidate.platform} | {vr.candidate.username} "
                f"| {vr.candidate.url} | {conf_pct} | {vr.threshold_label} |"
            )
        lines.append("")

        # Verification Details
        lines.append("## Verification Details")
        lines.append("")
        for vr in resolver.accounts:
            lines.append(f"### {vr.candidate.platform}/{vr.candidate.username}")
            lines.append("")
            for sig in vr.signals:
                lines.append(f"- **{sig.signal_name}**: {sig.score:.2f} (weight {sig.weight:.2f}) — {sig.evidence}")
            lines.append("")
    else:
        lines.append("No accounts discovered above threshold.")
        lines.append("")

    # Connections (Linker output)
    if linker and linker.connections:
        lines.append("## Connections")
        lines.append("")
        for conn in linker.connections:
            lines.append(
                f"- [{conn.relationship_type}] {conn.platform}: "
                f"{conn.content_snippet} (confidence: {conn.confidence:.0%})"
            )
        lines.append("")

    # Topic Profile (Profiler output)
    if profiler and profiler.dimensions:
        lines.append("## Behavioral Profile")
        lines.append("")
        for dimension, topics in profiler.dimensions.items():
            lines.append(f"### {dimension.title()}")
            for ts in topics:
                lines.append(f"- {ts.topic}: {ts.score:.2f}")
            lines.append("")

    # Methodology
    lines.append("## Methodology")
    lines.append("")
    agents_run = ["Resolver"]
    if linker:
        agents_run.append("Linker")
    if profiler:
        agents_run.append("Profiler")
    lines.append(f"- **Agents**: {', '.join(agents_run)}")
    if resolver and resolver.accounts:
        signal_names = set()
        for vr in resolver.accounts:
            for sig in vr.signals:
                signal_names.add(sig.signal_name)
        if signal_names:
            lines.append(f"- **Signals**: {', '.join(sorted(signal_names))}")
    lines.append(f"- **Status**: {investigation.status}")
    lines.append("")

    return "\n".join(lines)

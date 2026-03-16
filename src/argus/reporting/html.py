"""HTML report renderer."""

from __future__ import annotations

from argus.models.investigation import Investigation

_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }
h1 { border-bottom: 2px solid #333; padding-bottom: 10px; }
h2 { color: #555; margin-top: 30px; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #f5f5f5; font-weight: 600; }
tr:hover { background: #f9f9f9; }
.conf-high { color: #2d7d2d; font-weight: bold; }
.conf-medium { color: #b5850a; font-weight: bold; }
.conf-low { color: #c0392b; font-weight: bold; }
.evidence { margin: 5px 0; padding: 8px; background: #f8f8f8; border-radius: 4px; font-size: 0.9em; }
a { color: #2563eb; }
.summary { background: #f0f4ff; padding: 15px; border-radius: 8px; margin: 15px 0; }
details { margin: 10px 0; }
summary { cursor: pointer; font-weight: 500; }
.photo { width: 48px; height: 48px; border-radius: 50%; vertical-align: middle; margin-right: 8px; }
"""


def _conf_class(confidence: float) -> str:
    if confidence >= 0.70:
        return "conf-high"
    if confidence >= 0.30:
        return "conf-medium"
    return "conf-low"


def generate_html(investigation: Investigation) -> str:
    """Generate a styled HTML investigation report."""
    target = investigation.target
    resolver = investigation.resolver_output
    linker = investigation.linker_output
    profiler = investigation.profiler_output

    account_count = len(resolver.accounts) if resolver else 0
    platforms = {a.candidate.platform for a in resolver.accounts} if resolver else set()

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang='en'>")
    parts.append("<head>")
    parts.append(f"<meta charset='utf-8'><title>Argus Report: {_esc(target.name)}</title>")
    parts.append(f"<style>{_CSS}</style>")
    parts.append("</head>")
    parts.append("<body>")

    parts.append(f"<h1>Investigation Report: {_esc(target.name)}</h1>")

    # Summary
    parts.append("<div class='summary'>")
    if account_count > 0:
        parts.append(
            f"<p>Found <strong>{account_count}</strong> account(s) across "
            f"<strong>{len(platforms)}</strong> platform(s).</p>"
        )
    else:
        parts.append("<p>No accounts discovered above threshold.</p>")
    parts.append("</div>")

    # Accounts table
    if resolver and resolver.accounts:
        parts.append("<h2>Discovered Accounts</h2>")
        parts.append("<table>")
        parts.append("<tr><th></th><th>Platform</th><th>Username</th><th>URL</th>"
                     "<th>Confidence</th><th>Label</th></tr>")
        for vr in resolver.accounts:
            cc = _conf_class(vr.confidence)
            photo = ""
            if vr.candidate.scraped_data and vr.candidate.scraped_data.profile_photo_url:
                photo = f"<img class='photo' src='{_esc(vr.candidate.scraped_data.profile_photo_url)}' alt=''>"

            parts.append(
                f"<tr>"
                f"<td>{photo}</td>"
                f"<td>{_esc(vr.candidate.platform)}</td>"
                f"<td>{_esc(vr.candidate.username)}</td>"
                f"<td><a href='{_esc(vr.candidate.url)}'>{_esc(vr.candidate.url)}</a></td>"
                f"<td class='{cc}'>{vr.confidence:.0%}</td>"
                f"<td>{_esc(vr.threshold_label)}</td>"
                f"</tr>"
            )
        parts.append("</table>")

        # Evidence (collapsible)
        parts.append("<h2>Verification Details</h2>")
        for vr in resolver.accounts:
            parts.append("<details>")
            parts.append(f"<summary>{_esc(vr.candidate.platform)}/{_esc(vr.candidate.username)} "
                         f"— {vr.confidence:.0%}</summary>")
            for sig in vr.signals:
                parts.append(
                    f"<div class='evidence'><strong>{_esc(sig.signal_name)}</strong>: "
                    f"{sig.score:.2f} (weight {sig.weight:.2f}) — {_esc(sig.evidence)}</div>"
                )
            parts.append("</details>")

    # Connections
    if linker and linker.connections:
        parts.append("<h2>Connections</h2><ul>")
        for conn in linker.connections:
            parts.append(
                f"<li><strong>{_esc(conn.relationship_type)}</strong> "
                f"({_esc(conn.platform)}): {_esc(conn.content_snippet)} "
                f"— {conn.confidence:.0%}</li>"
            )
        parts.append("</ul>")

    # Profile
    if profiler and profiler.dimensions:
        parts.append("<h2>Behavioral Profile</h2>")
        for dim, topics in profiler.dimensions.items():
            parts.append(f"<h3>{_esc(dim.title())}</h3><ul>")
            for ts in topics:
                parts.append(f"<li>{_esc(ts.topic)}: {ts.score:.2f}</li>")
            parts.append("</ul>")

    parts.append("<h2>Methodology</h2><ul>")
    agents = ["Resolver"]
    if linker:
        agents.append("Linker")
    if profiler:
        agents.append("Profiler")
    parts.append(f"<li>Agents: {', '.join(agents)}</li>")
    parts.append(f"<li>Status: {_esc(investigation.status)}</li>")
    parts.append("</ul>")

    parts.append("<footer><p><em>Generated by Argus OSINT Platform</em></p></footer>")
    parts.append("</body></html>")

    return "\n".join(parts)


def _esc(text: str) -> str:
    """HTML-escape text."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

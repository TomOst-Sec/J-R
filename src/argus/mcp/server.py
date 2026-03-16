"""MCP server for Argus OSINT platform — exposes tools, resources, and prompts."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("argus-osint", instructions="Argus OSINT platform — resolve, link, and profile people across social media.")

# ---------------------------------------------------------------------------
# In-memory store for investigations (shared across tools)
# ---------------------------------------------------------------------------

_investigations: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def resolve_person(
    name: str,
    location: str | None = None,
    seed_urls: list[str] | None = None,
    email: str | None = None,
    username_hint: str | None = None,
) -> dict:
    """Resolve a person across social media platforms. Returns verified accounts with confidence scores."""
    from argus.agents.resolver import ResolverAgent
    from argus.config.settings import ArgusConfig
    from argus.models.agent import AgentInput
    from argus.models.target import TargetInput

    target = TargetInput(
        name=name,
        location=location,
        seed_urls=seed_urls or [],
        email=email,
        username_hint=username_hint,
    )
    agent = ResolverAgent(config=ArgusConfig())
    output = await agent.run(AgentInput(target=target))

    # Store for later use
    inv_id = f"inv-{len(_investigations) + 1}"
    _investigations[inv_id] = {
        "id": inv_id,
        "target": name,
        "resolver_output": output.model_dump(),
    }

    result = output.model_dump()
    result["investigation_id"] = inv_id
    return result


@mcp.tool()
async def link_topic(
    name: str,
    topic: str,
    topic_description: str | None = None,
) -> dict:
    """Find connections between a person and a topic across their verified accounts."""
    from argus.agents.linker import LinkerAgent, LinkerInput
    from argus.models.target import TargetInput

    agent = LinkerAgent()
    input_data = LinkerInput(
        target=TargetInput(name=name),
        topic=topic,
        topic_description=topic_description,
    )
    output = await agent.run(input_data)
    return output.model_dump()


@mcp.tool()
async def profile_person(name: str) -> dict:
    """Build a behavioral profile for a person from their online activity."""
    from argus.agents.profiler import ProfilerAgent, ProfilerInput
    from argus.models.target import TargetInput

    agent = ProfilerAgent()
    input_data = ProfilerInput(target=TargetInput(name=name))
    output = await agent.run(input_data)
    return output.model_dump()


@mcp.tool()
async def get_investigation(investigation_id: str) -> dict:
    """Get full results of a stored investigation by ID."""
    inv = _investigations.get(investigation_id)
    if not inv:
        return {"error": f"Investigation {investigation_id} not found"}
    return inv


@mcp.tool()
async def list_investigations() -> list[dict]:
    """List all stored investigations with their IDs and targets."""
    return [
        {"id": inv["id"], "target": inv["target"]}
        for inv in _investigations.values()
    ]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("investigation://{inv_id}/report")
async def investigation_report(inv_id: str) -> str:
    """Rendered markdown report for an investigation."""
    inv = _investigations.get(inv_id)
    if not inv:
        return f"# Error\n\nInvestigation {inv_id} not found."
    target = inv.get("target", "Unknown")
    resolver = inv.get("resolver_output", {})
    accounts = resolver.get("accounts", [])
    lines = [
        f"# Investigation Report: {target}",
        "",
        f"**Investigation ID:** {inv_id}",
        f"**Accounts found:** {len(accounts)}",
        "",
    ]
    for acct in accounts:
        candidate = acct.get("candidate", {})
        lines.append(
            f"- **{candidate.get('platform', '?')}** / "
            f"{candidate.get('username', '?')} — "
            f"confidence: {acct.get('confidence', 0):.0%}"
        )
    return "\n".join(lines)


@mcp.resource("investigation://{inv_id}/accounts")
async def investigation_accounts(inv_id: str) -> str:
    """List of verified accounts for an investigation."""
    inv = _investigations.get(inv_id)
    if not inv:
        return "Investigation not found."
    resolver = inv.get("resolver_output", {})
    accounts = resolver.get("accounts", [])
    lines = []
    for acct in accounts:
        c = acct.get("candidate", {})
        lines.append(f"{c.get('platform', '?')}: {c.get('username', '?')} ({c.get('url', '')})")
    return "\n".join(lines) if lines else "No accounts found."


@mcp.resource("investigation://{inv_id}/connections")
async def investigation_connections(inv_id: str) -> str:
    """Linker results (connections) for an investigation."""
    inv = _investigations.get(inv_id)
    if not inv:
        return "Investigation not found."
    connections = inv.get("linker_output", {}).get("connections", [])
    if not connections:
        return "No connections data available. Run link_topic first."
    lines = []
    for conn in connections:
        lines.append(
            f"- [{conn.get('relationship_type', '?')}] "
            f"{conn.get('platform', '?')}: {conn.get('content_snippet', '')[:80]}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
async def osint_investigate(name: str, context: str = "") -> str:
    """Pre-built prompt for running a full OSINT investigation on a person."""
    return (
        f"Please investigate the person '{name}' using the Argus OSINT tools.\n\n"
        f"Steps:\n"
        f"1. Use resolve_person to find their accounts across social media\n"
        f"2. Review the results and note the investigation_id\n"
        f"3. Use profile_person to build a behavioral profile\n"
        f"4. Summarize findings including platforms found, confidence levels, and key profile traits\n"
        + (f"\nAdditional context: {context}" if context else "")
    )


@mcp.prompt()
async def osint_quick_check(username: str) -> str:
    """Quick username check prompt — look up a specific username across platforms."""
    return (
        f"Please do a quick check for the username '{username}' across social media platforms.\n\n"
        f"Use resolve_person with username_hint='{username}' and name='{username}'.\n"
        f"Report which platforms have this username and the confidence scores."
    )

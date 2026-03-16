"""CrewAI tool wrappers for Argus OSINT agents.

Usage:
    from argus.integrations.crewai import argus_resolve_tool
    # Use with CrewAI agents
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    from crewai.tools import tool
except ImportError as e:
    raise ImportError(
        "CrewAI integration requires crewai. "
        "Install with: pip install argus-osint[crewai]"
    ) from e


@tool("argus_resolve_person")  # type: ignore[misc]
def argus_resolve_tool(
    name: str,
    location: str | None = None,
    email: str | None = None,
    username_hint: str | None = None,
) -> dict[str, Any]:
    """Find and verify a person's social media accounts across platforms.

    Args:
        name: Person's full name to search for
        location: Optional location hint for filtering
        email: Optional email address hint
        username_hint: Optional known username
    """
    return asyncio.run(_resolve_async(name, location, email, username_hint))


@tool("argus_link_topic")  # type: ignore[misc]
def argus_link_tool(
    name: str,
    topic: str,
    topic_description: str | None = None,
) -> dict[str, Any]:
    """Find connections between a person and a topic across their social media.

    Args:
        name: Person's name
        topic: Topic to find connections for
        topic_description: Optional extended description of the topic
    """
    return asyncio.run(_link_async(name, topic, topic_description))


@tool("argus_profile_person")  # type: ignore[misc]
def argus_profile_tool(name: str) -> dict[str, Any]:
    """Build a behavioral profile for a person from their online activity.

    Args:
        name: Person's name to profile
    """
    return asyncio.run(_profile_async(name))


async def _resolve_async(
    name: str,
    location: str | None,
    email: str | None,
    username_hint: str | None,
) -> dict[str, Any]:
    from argus.agents.resolver import ResolverAgent
    from argus.config.settings import ArgusConfig
    from argus.models.agent import AgentInput
    from argus.models.target import TargetInput

    target = TargetInput(
        name=name,
        location=location,
        seed_urls=[],
        email=email,
        username_hint=username_hint,
    )
    agent = ResolverAgent(config=ArgusConfig())
    output = await agent.run(AgentInput(target=target))
    return output.model_dump()


async def _link_async(
    name: str, topic: str, topic_description: str | None
) -> dict[str, Any]:
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


async def _profile_async(name: str) -> dict[str, Any]:
    from argus.agents.profiler import ProfilerAgent, ProfilerInput
    from argus.models.target import TargetInput

    agent = ProfilerAgent()
    input_data = ProfilerInput(target=TargetInput(name=name))
    output = await agent.run(input_data)
    return output.model_dump()

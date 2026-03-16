"""LangChain tool wrappers for Argus OSINT agents.

Usage:
    from argus.integrations.langchain import ArgusResolveTool
    tool = ArgusResolveTool()
    result = tool.invoke({"name": "John Doe"})
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import BaseTool
except ImportError as e:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install with: pip install argus-osint[langchain]"
    ) from e


class ResolveInput(BaseModel):
    """Input schema for the resolve tool."""

    name: str = Field(description="Person's full name to search for")
    location: str | None = Field(default=None, description="Location hint")
    seed_urls: list[str] = Field(default_factory=list, description="Seed profile URLs")
    email: str | None = Field(default=None, description="Email address hint")
    username_hint: str | None = Field(default=None, description="Known username")


class LinkInput(BaseModel):
    """Input schema for the link tool."""

    name: str = Field(description="Person's name")
    topic: str = Field(description="Topic to find connections for")
    topic_description: str | None = Field(default=None, description="Extended topic description")


class ProfileInput(BaseModel):
    """Input schema for the profile tool."""

    name: str = Field(description="Person's name to profile")


class ArgusResolveTool(BaseTool):  # type: ignore[misc]
    """LangChain tool that resolves a person across social media platforms."""

    name: str = "argus_resolve_person"
    description: str = (
        "Find and verify a person's social media accounts across platforms. "
        "Input: person's name and optional hints (location, email, username). "
        "Output: list of verified accounts with confidence scores."
    )
    args_schema: type[BaseModel] = ResolveInput

    def _run(self, **kwargs: Any) -> dict:
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> dict:
        from argus.agents.resolver import ResolverAgent
        from argus.config.settings import ArgusConfig
        from argus.models.agent import AgentInput
        from argus.models.target import TargetInput

        target = TargetInput(
            name=kwargs["name"],
            location=kwargs.get("location"),
            seed_urls=kwargs.get("seed_urls", []),
            email=kwargs.get("email"),
            username_hint=kwargs.get("username_hint"),
        )
        agent = ResolverAgent(config=ArgusConfig())
        output = await agent.run(AgentInput(target=target))
        return output.model_dump()


class ArgusLinkTool(BaseTool):  # type: ignore[misc]
    """LangChain tool that finds connections between a person and a topic."""

    name: str = "argus_link_topic"
    description: str = (
        "Find connections between a person and a specific topic, organization, "
        "or interest across their social media accounts."
    )
    args_schema: type[BaseModel] = LinkInput

    def _run(self, **kwargs: Any) -> dict:
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> dict:
        from argus.agents.linker import LinkerAgent, LinkerInput
        from argus.models.target import TargetInput

        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name=kwargs["name"]),
            topic=kwargs["topic"],
            topic_description=kwargs.get("topic_description"),
        )
        output = await agent.run(input_data)
        return output.model_dump()


class ArgusProfileTool(BaseTool):  # type: ignore[misc]
    """LangChain tool that builds a behavioral profile for a person."""

    name: str = "argus_profile_person"
    description: str = (
        "Build a behavioral profile for a person from their online activity. "
        "Extracts topics, classifies dimensions (professional/personal/public), "
        "and detects temporal trends."
    )
    args_schema: type[BaseModel] = ProfileInput

    def _run(self, **kwargs: Any) -> dict:
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> dict:
        from argus.agents.profiler import ProfilerAgent, ProfilerInput
        from argus.models.target import TargetInput

        agent = ProfilerAgent()
        input_data = ProfilerInput(target=TargetInput(name=kwargs["name"]))
        output = await agent.run(input_data)
        return output.model_dump()

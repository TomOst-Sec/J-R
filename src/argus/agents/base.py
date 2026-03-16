"""Base agent interface with built-in timing."""

from __future__ import annotations

import abc
import time
from typing import Any

from argus.models.agent import AgentInput, AgentOutput


class BaseAgent(abc.ABC):
    """Abstract base class for all Argus agents."""

    name: str = "unnamed"

    async def initialize(self, config: Any = None) -> None:
        """Setup hook called before first run. Override in subclasses."""

    async def shutdown(self) -> None:
        """Cleanup hook called after completion. Override in subclasses."""

    @abc.abstractmethod
    async def _execute(self, agent_input: AgentInput) -> AgentOutput:
        """Core execution logic. Subclasses must implement this."""

    async def run(self, agent_input: AgentInput) -> AgentOutput:
        """Run the agent with built-in timing."""
        start = time.monotonic()
        output = await self._execute(agent_input)
        output.duration_seconds = time.monotonic() - start
        output.agent_name = self.name
        return output

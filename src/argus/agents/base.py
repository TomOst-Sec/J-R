"""Base agent interface for Argus OSINT platform."""

import time
from abc import ABC, abstractmethod

from argus.config.settings import ArgusConfig
from argus.models.agent import AgentInput, AgentOutput


class BaseAgent(ABC):
    """Abstract base class for all Argus agents."""

    name: str = "unnamed"

    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the agent's main logic."""
        ...

    async def initialize(self, config: ArgusConfig) -> None:
        """Setup hook called once before use."""

    async def shutdown(self) -> None:
        """Cleanup hook."""

    async def execute(self, input: AgentInput) -> AgentOutput:
        """Wrap run() with timing."""
        start = time.monotonic()
        output = await self.run(input)
        output.duration_seconds = time.monotonic() - start
        return output

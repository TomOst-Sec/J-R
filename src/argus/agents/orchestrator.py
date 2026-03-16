"""Agent orchestration: sequential pipelines, parallel groups, and investigation management."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from argus.models.agent import AgentInput, AgentOutput

if TYPE_CHECKING:
    from argus.agents.base import BaseAgent
    from argus.models.target import TargetInput


class Pipeline:
    """Executes agents sequentially, passing context forward."""

    def __init__(self) -> None:
        self._agents: list[BaseAgent] = []

    def add(self, agent: BaseAgent) -> Pipeline:
        """Add an agent to the pipeline. Returns self for fluent chaining."""
        self._agents.append(agent)
        return self

    async def execute(self, agent_input: AgentInput) -> list[AgentOutput]:
        """Run agents sequentially, collecting all outputs."""
        outputs: list[AgentOutput] = []
        for agent in self._agents:
            output = await agent.run(agent_input)
            outputs.append(output)
        return outputs


class ParallelGroup:
    """Executes agents concurrently via asyncio.gather."""

    def __init__(self) -> None:
        self._agents: list[BaseAgent] = []

    def add(self, agent: BaseAgent) -> ParallelGroup:
        """Add an agent to the parallel group."""
        self._agents.append(agent)
        return self

    async def execute(self, agent_input: AgentInput) -> list[AgentOutput]:
        """Run all agents concurrently and return their outputs."""
        tasks = [agent.run(agent_input) for agent in self._agents]
        return list(await asyncio.gather(*tasks))


class Orchestrator:
    """Composes Pipeline and ParallelGroup to manage full investigation lifecycle."""

    def __init__(self, config: Any = None) -> None:
        self._config = config
        self._registry: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent by name for later use."""
        self._registry[agent.name] = agent

    def get_agent(self, name: str) -> BaseAgent:
        """Look up a registered agent by name."""
        if name not in self._registry:
            raise KeyError(f"Agent '{name}' not registered")
        return self._registry[name]

    async def run_investigation(
        self,
        target: TargetInput,
        agents: list[str],
    ) -> list[AgentOutput]:
        """Create an investigation and run the requested agents sequentially.

        Returns all agent outputs.
        """
        agent_input = AgentInput(target=target)
        pipeline = Pipeline()
        for agent_name in agents:
            agent = self.get_agent(agent_name)
            await agent.initialize(self._config)
            pipeline.add(agent)

        outputs = await pipeline.execute(agent_input)

        for agent_name in agents:
            await self.get_agent(agent_name).shutdown()

        return outputs

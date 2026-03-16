"""Agent orchestration: pipelines, parallel groups, and investigation runner."""

from __future__ import annotations

import asyncio
from datetime import datetime

from argus.agents.base import BaseAgent
from argus.config.settings import ArgusConfig
from argus.models.agent import AgentInput, AgentOutput, LinkerOutput, ProfilerOutput, ResolverOutput
from argus.models.investigation import Investigation
from argus.models.target import Target, TargetInput


class Pipeline:
    """Run agents sequentially."""

    def __init__(self) -> None:
        self._agents: list[BaseAgent] = []

    def add(self, agent: BaseAgent) -> Pipeline:
        self._agents.append(agent)
        return self

    async def execute(self, input: AgentInput) -> list[AgentOutput]:
        results: list[AgentOutput] = []
        for agent in self._agents:
            output = await agent.execute(input)
            results.append(output)
        return results


class ParallelGroup:
    """Run agents concurrently."""

    def __init__(self) -> None:
        self._agents: list[BaseAgent] = []

    def add(self, agent: BaseAgent) -> ParallelGroup:
        self._agents.append(agent)
        return self

    async def execute(self, input: AgentInput) -> list[AgentOutput]:
        tasks = [agent.execute(input) for agent in self._agents]
        return list(await asyncio.gather(*tasks))


class Orchestrator:
    """Manages investigation lifecycle with agent pipelines."""

    def __init__(self, config: ArgusConfig) -> None:
        self._config = config
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    async def run_investigation(
        self, target: TargetInput, agents: list[str], config: ArgusConfig
    ) -> Investigation:
        target_obj = Target(name=target.name, location=target.location, seed_urls=target.seed_urls,
                            email=target.email, username_hint=target.username_hint, phone=target.phone)
        investigation = Investigation(target=target_obj)

        agent_input = AgentInput(target=target)
        try:
            for agent_name in agents:
                agent = self._agents.get(agent_name)
                if agent is None:
                    continue
                await agent.initialize(config)
                output = await agent.execute(agent_input)
                await agent.shutdown()

                if isinstance(output, ResolverOutput):
                    investigation.resolver_output = output
                elif isinstance(output, LinkerOutput):
                    investigation.linker_output = output
                elif isinstance(output, ProfilerOutput):
                    investigation.profiler_output = output

            investigation.status = "completed"
        except Exception:
            investigation.status = "failed"
            raise
        finally:
            investigation.updated_at = datetime.now()

        return investigation

"""Tests for BaseAgent, Pipeline, ParallelGroup, and Orchestrator."""

import asyncio

import pytest

from argus.agents.base import BaseAgent
from argus.agents.orchestrator import Orchestrator, ParallelGroup, Pipeline
from argus.config.settings import ArgusConfig
from argus.models.agent import (
    AgentInput,
    AgentOutput,
    LinkerOutput,
    ProfilerOutput,
    ResolverOutput,
)
from argus.models.target import TargetInput


class EchoAgent(BaseAgent):
    """Test agent that echoes input."""

    name = "echo"

    async def run(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(target_name=input.target.name, agent_name=self.name, results=["echo"])


class SlowAgent(BaseAgent):
    """Test agent with a small delay."""

    name = "slow"

    async def run(self, input: AgentInput) -> AgentOutput:
        await asyncio.sleep(0.01)
        return AgentOutput(target_name=input.target.name, agent_name=self.name, results=["slow"])


class MockResolverAgent(BaseAgent):
    name = "resolver"

    async def run(self, input: AgentInput) -> ResolverOutput:
        return ResolverOutput(target_name=input.target.name, agent_name=self.name, accounts=[])


class MockLinkerAgent(BaseAgent):
    name = "linker"

    async def run(self, input: AgentInput) -> LinkerOutput:
        return LinkerOutput(target_name=input.target.name, agent_name=self.name, connections=[])


class MockProfilerAgent(BaseAgent):
    name = "profiler"

    async def run(self, input: AgentInput) -> ProfilerOutput:
        return ProfilerOutput(target_name=input.target.name, agent_name=self.name, dimensions={})


class FailingAgent(BaseAgent):
    name = "failing"

    async def run(self, input: AgentInput) -> AgentOutput:
        raise RuntimeError("agent failed")


class TestBaseAgent:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_echo_agent(self):
        agent = EchoAgent()
        input = AgentInput(target=TargetInput(name="Test"))
        output = await agent.execute(input)
        assert output.agent_name == "echo"
        assert output.results == ["echo"]
        assert output.duration_seconds is not None
        assert output.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self):
        agent = EchoAgent()
        config = ArgusConfig()
        await agent.initialize(config)
        await agent.shutdown()


class TestPipeline:
    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        pipe = Pipeline()
        pipe.add(EchoAgent()).add(SlowAgent())
        input = AgentInput(target=TargetInput(name="Test"))
        results = await pipe.execute(input)
        assert len(results) == 2
        assert results[0].agent_name == "echo"
        assert results[1].agent_name == "slow"

    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        pipe = Pipeline()
        input = AgentInput(target=TargetInput(name="Test"))
        results = await pipe.execute(input)
        assert results == []

    @pytest.mark.asyncio
    async def test_fluent_builder(self):
        pipe = Pipeline().add(EchoAgent()).add(EchoAgent())
        assert len(pipe._agents) == 2


class TestParallelGroup:
    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        group = ParallelGroup()
        group.add(SlowAgent()).add(SlowAgent())
        input = AgentInput(target=TargetInput(name="Test"))
        results = await group.execute(input)
        assert len(results) == 2
        assert all(r.agent_name == "slow" for r in results)

    @pytest.mark.asyncio
    async def test_empty_group(self):
        group = ParallelGroup()
        input = AgentInput(target=TargetInput(name="Test"))
        results = await group.execute(input)
        assert results == []


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_run_investigation(self):
        config = ArgusConfig()
        orch = Orchestrator(config)
        orch.register(MockResolverAgent())
        orch.register(MockLinkerAgent())

        target = TargetInput(name="John Doe")
        inv = await orch.run_investigation(target, ["resolver", "linker"], config)
        assert inv.status == "completed"
        assert inv.resolver_output is not None
        assert inv.linker_output is not None
        assert inv.profiler_output is None

    @pytest.mark.asyncio
    async def test_investigation_with_all_agents(self):
        config = ArgusConfig()
        orch = Orchestrator(config)
        orch.register(MockResolverAgent())
        orch.register(MockLinkerAgent())
        orch.register(MockProfilerAgent())

        target = TargetInput(name="Jane")
        inv = await orch.run_investigation(target, ["resolver", "linker", "profiler"], config)
        assert inv.status == "completed"
        assert inv.profiler_output is not None

    @pytest.mark.asyncio
    async def test_investigation_skips_unknown_agents(self):
        config = ArgusConfig()
        orch = Orchestrator(config)
        orch.register(EchoAgent())

        target = TargetInput(name="Test")
        inv = await orch.run_investigation(target, ["unknown", "echo"], config)
        assert inv.status == "completed"

    @pytest.mark.asyncio
    async def test_investigation_failure(self):
        config = ArgusConfig()
        orch = Orchestrator(config)
        orch.register(FailingAgent())

        target = TargetInput(name="Test")
        with pytest.raises(RuntimeError, match="agent failed"):
            await orch.run_investigation(target, ["failing"], config)

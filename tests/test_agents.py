"""Tests for the agent framework: BaseAgent, Pipeline, ParallelGroup, Orchestrator."""

from __future__ import annotations

import asyncio

import pytest

from argus.agents.base import BaseAgent
from argus.agents.orchestrator import Orchestrator, ParallelGroup, Pipeline
from argus.models.agent import AgentInput, AgentOutput
from argus.models.target import TargetInput


class MockAgent(BaseAgent):
    """A simple test agent that records calls."""

    name = "mock"

    def __init__(self, output_name: str = "mock", delay: float = 0.0) -> None:
        self.name = output_name
        self._delay = delay
        self.initialized = False
        self.shut_down = False

    async def initialize(self, config: ArgusConfig) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.shut_down = True

    async def _execute(self, agent_input: AgentInput) -> AgentOutput:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        return AgentOutput(
            target_name=agent_input.target.name,
            agent_name=self.name,
            results=[f"{self.name}_result"],
        )


class FailingAgent(BaseAgent):
    """Agent that raises an error."""

    name = "failing"

    async def _execute(self, agent_input: AgentInput) -> AgentOutput:
        raise RuntimeError("Agent failed")


class TestBaseAgent:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_run_records_timing(self) -> None:
        agent = MockAgent("timed")
        ai = AgentInput(target=TargetInput(name="Test"))
        output = await agent.run(ai)
        assert output.duration_seconds is not None
        assert output.duration_seconds >= 0
        assert output.agent_name == "timed"

    @pytest.mark.asyncio
    async def test_run_returns_results(self) -> None:
        agent = MockAgent("test")
        ai = AgentInput(target=TargetInput(name="John"))
        output = await agent.run(ai)
        assert output.target_name == "John"
        assert output.results == ["test_result"]


class TestPipeline:
    @pytest.mark.asyncio
    async def test_sequential_execution(self) -> None:
        p = Pipeline()
        p.add(MockAgent("first")).add(MockAgent("second"))
        ai = AgentInput(target=TargetInput(name="Test"))
        outputs = await p.execute(ai)
        assert len(outputs) == 2
        assert outputs[0].agent_name == "first"
        assert outputs[1].agent_name == "second"

    @pytest.mark.asyncio
    async def test_empty_pipeline(self) -> None:
        p = Pipeline()
        ai = AgentInput(target=TargetInput(name="Test"))
        outputs = await p.execute(ai)
        assert outputs == []

    @pytest.mark.asyncio
    async def test_pipeline_error_propagates(self) -> None:
        p = Pipeline()
        p.add(MockAgent("ok")).add(FailingAgent())
        ai = AgentInput(target=TargetInput(name="Test"))
        with pytest.raises(RuntimeError, match="Agent failed"):
            await p.execute(ai)


class TestParallelGroup:
    @pytest.mark.asyncio
    async def test_parallel_execution(self) -> None:
        pg = ParallelGroup()
        pg.add(MockAgent("a", delay=0.01)).add(MockAgent("b", delay=0.01))
        ai = AgentInput(target=TargetInput(name="Test"))
        outputs = await pg.execute(ai)
        assert len(outputs) == 2
        names = {o.agent_name for o in outputs}
        assert names == {"a", "b"}

    @pytest.mark.asyncio
    async def test_parallel_faster_than_sequential(self) -> None:
        import time

        pg = ParallelGroup()
        pg.add(MockAgent("a", delay=0.05)).add(MockAgent("b", delay=0.05))
        ai = AgentInput(target=TargetInput(name="Test"))
        start = time.monotonic()
        await pg.execute(ai)
        elapsed = time.monotonic() - start
        # Parallel should take ~0.05s, not ~0.1s
        assert elapsed < 0.09

    @pytest.mark.asyncio
    async def test_empty_parallel(self) -> None:
        pg = ParallelGroup()
        ai = AgentInput(target=TargetInput(name="Test"))
        outputs = await pg.execute(ai)
        assert outputs == []


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_run_investigation(self) -> None:
        config = None
        orch = Orchestrator(config)
        orch.register(MockAgent("resolver"))
        orch.register(MockAgent("linker"))

        target = TargetInput(name="John Doe")
        outputs = await orch.run_investigation(target, ["resolver", "linker"])
        assert len(outputs) == 2
        assert outputs[0].agent_name == "resolver"

    @pytest.mark.asyncio
    async def test_agents_initialized_and_shutdown(self) -> None:
        config = None
        orch = Orchestrator(config)
        agent = MockAgent("test")
        orch.register(agent)

        target = TargetInput(name="Test")
        await orch.run_investigation(target, ["test"])
        assert agent.initialized
        assert agent.shut_down

    @pytest.mark.asyncio
    async def test_unknown_agent_raises(self) -> None:
        config = None
        orch = Orchestrator(config)
        target = TargetInput(name="Test")
        with pytest.raises(KeyError, match="not registered"):
            await orch.run_investigation(target, ["nonexistent"])

    def test_get_agent(self) -> None:
        config = None
        orch = Orchestrator(config)
        agent = MockAgent("test")
        orch.register(agent)
        assert orch.get_agent("test") is agent

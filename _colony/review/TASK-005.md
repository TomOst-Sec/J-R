# TASK-005: BaseAgent interface and agent registry

**Priority:** critical
**Milestone:** 1
**Team:** any
**Depends:** TASK-002
**Estimated Complexity:** medium

## Description

Define the BaseAgent abstract class and orchestrator for chaining agents in sequential/parallel pipelines.

## Requirements

1. Create `src/argus/agents/base.py`:
   - `BaseAgent` abstract class:
     - `name` (str) class attribute
     - `async def run(self, input: AgentInput) -> AgentOutput` — abstract, main entry point
     - `async def initialize(self, config: ArgusConfig) -> None` — setup hook
     - `async def shutdown(self) -> None` — cleanup hook
     - Built-in timing: wraps `run()` to record `duration_seconds` in output

2. Create `src/argus/agents/orchestrator.py`:
   - `Pipeline` class:
     - `add(agent: BaseAgent) -> Pipeline` — fluent builder
     - `async def execute(self, input: AgentInput) -> list[AgentOutput]` — runs agents sequentially, passing output context forward
   - `ParallelGroup` class:
     - `add(agent: BaseAgent) -> ParallelGroup`
     - `async def execute(self, input: AgentInput) -> list[AgentOutput]` — runs agents concurrently via `asyncio.gather`
   - `Orchestrator` class:
     - Composes Pipeline and ParallelGroup
     - `async def run_investigation(self, target: TargetInput, agents: list[str], config: ArgusConfig) -> Investigation`
     - Creates Investigation record, runs requested agents, updates investigation status

3. Update `src/argus/agents/__init__.py`:
   - Export `BaseAgent`, `Pipeline`, `ParallelGroup`, `Orchestrator`

## Acceptance Criteria

- BaseAgent is abstract — cannot be instantiated directly
- Pipeline executes agents sequentially with timing
- ParallelGroup executes agents concurrently
- Orchestrator creates and manages Investigation lifecycle
- Unit tests with mock agents: sequential pipeline, parallel execution, error handling
- `uv run pytest tests/test_agents.py` passes

---
Claimed-By: bravo-2
Claimed-At: 2026-03-16T22:38:05+02:00

Completed-At: 2026-03-16T22:40:07+02:00

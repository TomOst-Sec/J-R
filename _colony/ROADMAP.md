# Development Roadmap

## Phase 1: Foundation (Milestone 1 — MVP) — COMPLETE

**Goal:** `argus resolve "John Doe"` finds accounts across 6 platforms with confidence scoring.

- [x] TASK-001–018: All foundation tasks merged. M1 SHIPPED.

**Status: 18/18 merged.**

## Phase 2: Core Features (Milestone 2) — ~85% COMPLETE

**Goal:** Full pipeline with Linker, Profiler, all agents chained, 14+ platforms, HTML reports.

- [x] TASK-019–032: Core agents, platform modules, verification signals, LLM provider — all merged
- [ ] TASK-033: CLI resolve rework — Rich progress bar + live table
- [ ] TASK-034: Discord platform module
- [ ] TASK-035: Investigation persistence & resume — full implementation
- [ ] TASK-036: Agent chaining via stdin/stdout pipes
- [ ] TASK-037: Mypy strict mode cleanup (40 errors)

**Status: 14/19 done. 5 remaining tasks queued.**

## Phase 3: Polish & Launch (Milestone 3) — TASKS GENERATED

**Goal:** MCP server, REST API, LangChain/CrewAI wrappers, Docker, docs.

- [ ] TASK-038: MCP Server Mode (stdio transport, 5 tools, resources, prompts)
- [ ] TASK-039: REST API Server (FastAPI, WebSocket streaming, auth)
- [ ] TASK-040: Privacy and ethics safeguards (consent, audit, purge, data minimization)
- [ ] TASK-041: Playwright stealth hardening (fingerprint rotation, CAPTCHA detection)
- [ ] TASK-042: LangChain/CrewAI tool wrappers
- [ ] TASK-043: Mutual connections verification signal
- [ ] TASK-044: Docker image (multi-stage, <500MB)
- [ ] TASK-045: Documentation (README, architecture, platform dev guide, API ref)
- [ ] TASK-046: Performance optimization (connection pooling, caching, concurrency)
- [ ] TASK-047: GraphML export for network visualization
- [ ] TASK-048: Interactive REPL shell — argus shell

### M3 Dependency Graph
```
Independent (start immediately):
  TASK-044 (Docker), TASK-045 (docs), TASK-037 (mypy)

Depend on existing code:
  TASK-038 (MCP) ← TASK-012, 019, 020
  TASK-039 (API) ← TASK-012, 019, 020
  TASK-040 (privacy) ← TASK-012
  TASK-041 (stealth) ← TASK-010
  TASK-042 (LangChain) ← TASK-012, 019, 020
  TASK-043 (connections) ← TASK-006
  TASK-046 (perf) ← TASK-012
  TASK-047 (GraphML) ← TASK-022
  TASK-048 (REPL) ← TASK-021
```

## Phase 4: Advanced (Milestone 4)

- [ ] Network Expansion Agent
- [ ] Batch Investigation
- [ ] Change Detection
- [ ] Custom scoring models
- [ ] Web UI
- [ ] Encrypted storage
- [ ] Multi-language content analysis

## Current Phase
Phase 2 wrapping up → Phase 3 ramping

## Notes
- Colony shipped 32 tasks in ~75 minutes (extraordinary throughput)
- 273 tests passing, ruff clean, 40 mypy strict errors (non-blocking)
- Queue restocked: 16 tasks (TASK-033 through TASK-048)
- TASK-033 (CLI rework) and TASK-037 (mypy) are quick wins
- M3 has many independent tasks — all 5 coders can work in parallel
- 55 source files, 31 test files, 15 platform modules

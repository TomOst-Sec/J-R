# Development Roadmap

## Phase 1: Foundation (Milestone 1 — MVP) — COMPLETE

- [x] TASK-001–018: All foundation tasks merged. **M1 SHIPPED.**

## Phase 2: Core Features (Milestone 2) — COMPLETE

- [x] TASK-019–032: All core feature tasks merged
- [x] TASK-033: CLI resolve rework (Rich progress bar)
- [x] TASK-034: Discord platform module
- [x] TASK-035: Investigation persistence & resume
- [x] TASK-036: Agent chaining via stdin/stdout pipes
- [x] TASK-037: Mypy strict mode cleanup

**Status: M2 SHIPPED. 37/37 tasks done.**

## Phase 3: Polish & Launch (Milestone 3) — IN REVIEW

**Goal:** MCP server, REST API, LangChain/CrewAI wrappers, Docker, docs.

- [ ] TASK-038: MCP Server Mode **[IN REVIEW]**
- [ ] TASK-039: REST API Server (FastAPI) **[IN REVIEW]**
- [ ] TASK-040: Privacy and ethics safeguards **[IN REVIEW]**
- [ ] TASK-041: Playwright stealth hardening **[IN REVIEW]**
- [ ] TASK-042: LangChain/CrewAI tool wrappers **[IN REVIEW]**
- [ ] TASK-043: Mutual connections verification signal **[IN REVIEW]**
- [ ] TASK-044: Docker image **[IN REVIEW]**
- [ ] TASK-045: Documentation **[IN REVIEW]**
- [ ] TASK-046: Performance optimization **[IN REVIEW]**
- [ ] TASK-047: GraphML export **[IN REVIEW]**
- [ ] TASK-048: Interactive REPL shell **[IN REVIEW]**
- [ ] TASK-049: Face recognition signal (optional)
- [ ] TASK-053: CI/CD pipeline — GitHub Actions

**Status: 11 in review, 2 in queue. Awaiting audit/judge.**

## Phase 4: Advanced (Milestone 4)

- [ ] TASK-050: Network Expansion Agent — social graph discovery
- [ ] TASK-051: Batch investigation — CSV processing
- [ ] TASK-052: Change detection — periodic re-checking
- [ ] TASK-054: Web UI — investigation dashboard
- [ ] Encrypted storage (not yet tasked)
- [ ] Multi-language content analysis (not yet tasked)
- [ ] Custom scoring models (not yet tasked)

## Current Phase
M3 in review → M4 pre-loaded

## Notes
- Colony shipped 48 tasks total across 4 atlas cycles
- 16 tasks in review — audit/judge throughput is now the bottleneck
- Queue has 6 tasks (TASK-049–054) ready for after review clears
- 15 platform modules, full agent pipeline, MCP + REST API, docs, Docker — all coded
- Tests: 439+ passing

# Development Roadmap

## Phase 1: Foundation (Milestone 1 — MVP) — COMPLETE

**Goal:** `argus resolve "John Doe"` finds accounts across 6 platforms with confidence scoring.

- [x] TASK-001: Project scaffolding (pyproject.toml, directory structure, UV)
- [x] TASK-002: Core Pydantic data models
- [x] TASK-003: Configuration system (argus.toml)
- [x] TASK-004: BasePlatform interface + plugin auto-discovery
- [x] TASK-005: BaseAgent interface + orchestrator
- [x] TASK-006: Verification engine — confidence scoring
- [x] TASK-007: GitHub platform module
- [x] TASK-008: Reddit platform module
- [x] TASK-009: SQLite persistence layer
- [x] TASK-010: Stealth & rate limiting module
- [x] TASK-011: HackerNews platform module
- [x] TASK-012: Resolver Agent (core pipeline)
- [x] TASK-013: CLI — `argus resolve` command *(rejected once, rework needed for Rich progress)*
- [x] TASK-014: Twitter/X platform module
- [x] TASK-015: LinkedIn platform module
- [x] TASK-016: Instagram platform module
- [x] TASK-017: Username candidate generator
- [x] TASK-018: Integration test — end-to-end resolve pipeline

**Status: 18/18 merged to main. M1 SHIPPED.**

## Phase 2: Core Features (Milestone 2) — ~85% COMPLETE

**Goal:** Full pipeline with Linker, Profiler, all agents chained, 14+ platforms, HTML reports.

- [x] TASK-019: Linker Agent — topic connection mapper
- [x] TASK-020: Profiler Agent — behavioral profile builder
- [x] TASK-021: Full CLI — link, profile, investigate, report, platforms commands
- [x] TASK-022: Report generator — JSON, Markdown, HTML, CSV
- [x] TASK-023: Timezone correlation verification signal
- [x] TASK-024: Writing style verification signal
- [x] TASK-025: Facebook platform module
- [x] TASK-026: YouTube platform module
- [x] TASK-027: Medium platform module
- [x] TASK-028: Mastodon/Fediverse platform module
- [x] TASK-029: Stack Overflow platform module
- [x] TASK-030: TikTok platform module
- [x] TASK-031: Telegram platform module
- [x] TASK-032: LLM provider abstraction
- [ ] Discord platform module (not yet tasked)
- [ ] Investigation persistence & resume — full implementation (not yet tasked)
- [ ] Agent chaining via stdin/stdout pipes (not yet tasked)

**Status: 14/17 done. 3 remaining items need tasks generated.**

## Phase 3: Polish & Launch (Milestone 3) — NOT STARTED

**Goal:** MCP server, REST API, LangChain/CrewAI wrappers, Docker, docs.

- [ ] MCP Server Mode
- [ ] REST API Server (FastAPI)
- [ ] LangChain/CrewAI tool wrappers
- [ ] Playwright stealth hardening
- [ ] Privacy safeguards
- [ ] Mutual connections signal
- [ ] Face recognition (optional)
- [ ] Performance optimization
- [ ] Documentation
- [ ] Docker image

## Phase 4: Advanced (Milestone 4)

- [ ] Network Expansion Agent
- [ ] Batch Investigation
- [ ] Change Detection
- [ ] Custom scoring models
- [ ] Web UI
- [ ] Encrypted storage
- [ ] Multi-language content analysis

## Current Phase
Phase 2 wrapping up → Phase 3 next

## Notes
- Colony shipped 32 tasks in ~75 minutes (extraordinary throughput)
- 273 tests passing, ruff clean, 40 mypy strict errors (non-blocking)
- Queue is empty — atlas needs to generate M3 tasks + remaining M2 tasks
- TASK-013 needs rework (missing Rich progress display)
- 55 source files, 31 test files

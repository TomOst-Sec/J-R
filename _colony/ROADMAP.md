# Development Roadmap

## Phase 1: Foundation (Milestone 1 — MVP)

**Goal:** `argus resolve "John Doe"` finds accounts across 6 platforms with confidence scoring.

- [x] TASK-001: Project scaffolding (pyproject.toml, directory structure, UV)
- [x] TASK-002: Core Pydantic data models
- [x] TASK-003: Configuration system (argus.toml)
- [x] TASK-004: BasePlatform interface + plugin auto-discovery
- [x] TASK-005: BaseAgent interface + orchestrator
- [ ] TASK-006: Verification engine — confidence scoring **[IN REVIEW]**
- [x] TASK-007: GitHub platform module
- [x] TASK-008: Reddit platform module
- [x] TASK-009: SQLite persistence layer
- [x] TASK-010: Stealth & rate limiting module
- [ ] TASK-011: HackerNews platform module **[IN REVIEW]**
- [ ] TASK-012: Resolver Agent (core pipeline) **[IN REVIEW]**
- [ ] TASK-013: CLI — `argus resolve` command **[IN REVIEW]**
- [x] TASK-014: Twitter/X platform module
- [ ] TASK-015: LinkedIn platform module **[IN REVIEW]**
- [ ] TASK-016: Instagram platform module **[IN REVIEW]**
- [x] TASK-017: Username candidate generator
- [ ] TASK-018: Integration test — end-to-end resolve pipeline

**Progress: 11/17 merged, 6 in review**

## Phase 2: Core Features (Milestone 2)

**Goal:** Full pipeline with Linker, Profiler, all agents chained, 14+ platforms, HTML reports.

- [ ] TASK-019: Linker Agent — topic connection mapper
- [ ] TASK-020: Profiler Agent — behavioral profile builder
- [ ] TASK-021: Full CLI — link, profile, investigate, report, platforms commands
- [ ] TASK-022: Report generator — JSON, Markdown, HTML
- [ ] TASK-023: Timezone correlation verification signal
- [ ] TASK-024: Writing style verification signal
- [ ] TASK-025: Facebook platform module
- [ ] TASK-026: YouTube platform module
- [ ] TASK-027: Medium platform module
- [ ] TASK-028: Mastodon/Fediverse platform module
- [ ] TASK-029: Stack Overflow platform module
- [ ] TASK-030: TikTok platform module
- [ ] TASK-031: Telegram platform module
- [ ] TASK-032: LLM provider abstraction

### Milestone 2 Dependency Graph
```
TASK-012 (resolver) ─┬── TASK-019 (linker) ─┬── TASK-021 (full CLI)
                     ├── TASK-020 (profiler) ┘
                     └── TASK-022 (report gen)
TASK-006 (verification) ─┬── TASK-023 (timezone signal)
                         └── TASK-024 (style signal)
TASK-004 (platforms) ─┬── TASK-025 (facebook)
                      ├── TASK-026 (youtube)
                      ├── TASK-027 (medium)
                      ├── TASK-028 (mastodon)
                      ├── TASK-029 (stackoverflow)
                      ├── TASK-030 (tiktok)
                      └── TASK-031 (telegram)
TASK-003 (config) ──── TASK-032 (LLM provider)
```

## Phase 3: Polish & Launch (Milestone 3)

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
Phase 1 nearing completion → Phase 2 ramping up

## Notes
- Milestone 1: 11/17 tasks merged to main, 6 in review — expect completion this cycle
- Milestone 2 queue pre-loaded: 15 tasks (TASK-018 through TASK-032)
- Platform modules (TASK-025-031) are highly parallelizable — all 5 coders can work simultaneously
- Linker + Profiler (TASK-019/020) are the critical M2 features, depend on Resolver merge

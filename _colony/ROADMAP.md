# Development Roadmap

## Phase 1: Foundation (Milestone 1 — MVP)

**Goal:** `argus resolve "John Doe"` finds accounts across 6 platforms with confidence scoring.

- [ ] TASK-001: Project scaffolding (pyproject.toml, directory structure, UV) **[ACTIVE — alpha-3, BLOCKED]**
- [ ] TASK-002: Core Pydantic data models
- [ ] TASK-003: Configuration system (argus.toml)
- [ ] TASK-004: BasePlatform interface + plugin auto-discovery
- [ ] TASK-005: BaseAgent interface + orchestrator
- [ ] TASK-006: Verification engine — confidence scoring
- [ ] TASK-007: GitHub platform module
- [ ] TASK-008: Reddit platform module
- [ ] TASK-009: SQLite persistence layer
- [ ] TASK-010: Stealth & rate limiting module
- [ ] TASK-011: HackerNews platform module
- [ ] TASK-012: Resolver Agent (core pipeline)
- [ ] TASK-013: CLI — `argus resolve` command
- [ ] TASK-014: Twitter/X platform module
- [ ] TASK-015: LinkedIn platform module
- [ ] TASK-016: Instagram platform module
- [ ] TASK-017: Username candidate generator
- [ ] TASK-018: Integration test — end-to-end resolve pipeline

### Dependency Graph
```
TASK-001 (scaffolding)
├── TASK-002 (models) ─┬── TASK-004 (platforms) ─┬── TASK-007 (github)
│                      │                         ├── TASK-008 (reddit)
│                      │                         ├── TASK-011 (hackernews)
│                      │                         ├── TASK-014 (twitter)
│                      │                         ├── TASK-015 (linkedin)
│                      │                         └── TASK-016 (instagram)
│                      ├── TASK-005 (agents) ──── TASK-012 (resolver) ── TASK-013 (CLI)
│                      ├── TASK-006 (verification) ── TASK-012
│                      └── TASK-009 (storage) ──── TASK-012
├── TASK-003 (config) ── TASK-010 (stealth)
└── TASK-017 (username gen)
```

## Phase 2: Core Features (Milestone 2)

**Goal:** Full pipeline with Linker, Profiler, all agents chained, 14+ platforms, HTML reports.

- [ ] Linker Agent — topic connection mapping
- [ ] Profiler Agent — behavioral profile builder
- [ ] Agent chaining & orchestration (pipes, Python API)
- [ ] Full CLI (link, profile, investigate, report, shell)
- [ ] 8 additional platforms (Facebook, TikTok, YouTube, Medium, Telegram, Mastodon, StackOverflow, Discord)
- [ ] Report generator (JSON, Markdown, HTML, CSV, GraphML)
- [ ] LLM integration (optional) — LLMProvider abstraction
- [ ] Timezone correlation signal
- [ ] Writing style signal
- [ ] Investigation persistence & resume (full)

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
Phase 1 — Foundation / MVP

## Notes
- TASK-001 is the critical path blocker — all other tasks depend on it
- Platform modules (TASK-007/008/011/014/015/016) are highly parallelizable
- Verification engine (TASK-006) and storage (TASK-009) can be built in parallel with platforms
- CEO Cycle 1 (2026-03-16): Colony bottlenecked on TASK-001 — alpha-3 claimed but 0 commits

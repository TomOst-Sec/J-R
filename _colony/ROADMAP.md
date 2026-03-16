# Development Roadmap

## Phase 1: Foundation (Milestone 1 — MVP) — COMPLETE

- [x] TASK-001–018: All foundation tasks merged. **M1 SHIPPED.**

## Phase 2: Core Features (Milestone 2) — COMPLETE

- [x] TASK-019–032: All merged
- [x] TASK-033–037: M2 completion tasks — all coded, in review/done

**Status: M2 SHIPPED.**

## Phase 3: Polish & Launch (Milestone 3) — IN PROGRESS

**Goal:** MCP server, REST API, LangChain/CrewAI wrappers, Docker, docs.

- [x] TASK-038: MCP Server Mode — coded, **needs fix: mcp dep missing (TASK-056)**
- [x] TASK-039: REST API Server — coded, **needs fix: importorskip (TASK-057)**
- [x] TASK-040: Privacy safeguards — done
- [ ] TASK-041: Playwright stealth hardening **[IN REVIEW]**
- [x] TASK-042: LangChain/CrewAI wrappers — done
- [x] TASK-043: Mutual connections signal — done
- [x] TASK-044: Docker image — done
- [x] TASK-045: Documentation — done
- [x] TASK-046: Performance optimization — done
- [ ] TASK-047: GraphML export **[IN REVIEW — needs fix: TASK-058]**
- [ ] TASK-048: Interactive REPL shell **[IN REVIEW]**
- [ ] TASK-049: Face recognition signal — coded
- [ ] TASK-053: CI/CD pipeline **[IN REVIEW]**

### Rework Tasks (quick fixes)
- [ ] TASK-055: Fix CLI live table
- [ ] TASK-056: Fix mcp dependency
- [ ] TASK-057: Fix importorskip guards
- [ ] TASK-058: Fix GraphML edge ID

### Quality
- [ ] TASK-059: Ground truth precision testing

## Phase 4: Advanced (Milestone 4) — TASKS GENERATED

- [x] TASK-050: Network Expansion Agent — coded
- [ ] TASK-051: Batch investigation **[IN REVIEW]**
- [ ] TASK-052: Change detection **[IN REVIEW]**
- [x] TASK-054: Web UI dashboard — coded
- [ ] TASK-060: Encrypted storage (SQLCipher)
- [ ] TASK-061: Multi-language content analysis
- [ ] TASK-062: Custom scoring models

## Current Phase
M3 polish + rework → M4 in progress

## Notes
- Colony: 62 tasks total, 45 merged, 9 in review, 8 in queue
- 482 tests passing, 62 source files, 15+ platform modules
- 4 rejected tasks need trivial fixes (TASK-055–058)
- Queue depth: 8 tasks for 5 coders

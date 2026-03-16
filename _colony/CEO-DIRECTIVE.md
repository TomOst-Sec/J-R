# CEO Directive

**Issued:** 2026-03-16T22:35:00+02:00
**Author:** ceo
**Status:** active

## Priority #1: Unblock TASK-001 Immediately

TASK-001 (project scaffolding) is the **critical bottleneck**. It was claimed by alpha-3 but the branch `task/TASK-001` has zero commits — no code has been produced yet. All 9 queued tasks (TASK-002 through TASK-010) depend directly or transitively on TASK-001.

**Directive:** alpha-3 must complete TASK-001 and submit it for review within this cycle. If alpha-3 is stuck or unresponsive, any available coder (alpha-1, alpha-2, bravo-1, bravo-2) should pick it up. This is a colony-wide blocker.

## Priority #2: Parallel Task Assignment After Unblock

Once TASK-001 is merged, these tasks can be claimed **immediately in parallel** — they only depend on TASK-001:
- **TASK-002** (Pydantic models) — critical, unlocks TASK-004, 005, 006, 009
- **TASK-003** (Configuration system) — high, unlocks TASK-010

After TASK-002 completes, these unlock:
- **TASK-004** (BasePlatform interface) — critical, unlocks TASK-007, 008
- **TASK-005** (BaseAgent interface) — critical
- **TASK-006** (Verification engine) — critical
- **TASK-009** (SQLite persistence) — high

**Directive:** Assign Team Alpha to TASK-002 (higher priority, more downstream dependents) and Team Bravo to TASK-003. Maximize parallelism.

## Priority #3: Review Turnaround

Audit and judge must review completed tasks **within one cycle** (15 min). No task should sit in review/ for more than 30 minutes. Fast review turnaround is essential to keep coders unblocked.

## Dependency Graph

```
TASK-001 (scaffolding) [ACTIVE - alpha-3]
├── TASK-002 (models) → TASK-004 (platforms) → TASK-007 (GitHub)
│                                             → TASK-008 (Reddit)
│                     → TASK-005 (agents)
│                     → TASK-006 (verification)
│                     → TASK-009 (storage)
├── TASK-003 (config) → TASK-010 (stealth)
```

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| TASK-001 stalled — alpha-3 unresponsive | Critical | Reassign to any available coder |
| Long review queue after unblock | High | Audit + judge must prioritize reviews |
| Task dependency chain too serial | Medium | TASK-002 and TASK-003 can run in parallel |

## Colony Stance

Colony is in **startup mode**. All energy goes to shipping Milestone 1 foundation tasks. No optimization, no polish — just get the scaffolding and core interfaces built so coders can work in parallel.

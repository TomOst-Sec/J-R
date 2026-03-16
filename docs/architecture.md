# Architecture

## Overview

Argus is a multi-agent OSINT platform built in Python 3.12+ with async-first design. The system is organized as a composable agent pipeline with pluggable platform modules and a weighted verification engine.

## Module Layout

```
src/argus/
├── __init__.py          # Package version
├── cli.py               # Click CLI entry point
├── agents/              # BaseAgent protocol + agent implementations
├── platforms/           # BasePlatform interface + per-platform scrapers
├── verification/        # Confidence scoring engine (multi-signal correlation)
├── storage/             # SQLite persistence layer
├── config/              # Configuration loading (argus.toml)
├── stealth/             # Rate limiting, UA rotation, proxy support
└── reporting/           # Output formatters (JSON, Markdown, HTML, CSV)
```

## Agent Pipeline

```
Input (name, location, seed URLs)
  │
  ▼
Resolver Agent ──► discovers accounts across platforms
  │
  ▼
Verification Engine ──► scores each account 0.0–1.0
  │
  ├──► Linker Agent (optional) ──► maps topic connections
  │
  └──► Profiler Agent (optional) ──► builds behavioral profile
  │
  ▼
Output (JSON / Markdown / HTML / CSV)
```

Agents communicate via typed Pydantic models. Each agent implements:

```python
class BaseAgent:
    async def run(self, input: AgentInput) -> AgentOutput: ...
```

## Platform Plugin System

Each platform is a Python module in `argus/platforms/` implementing `BasePlatform`:

- `check_username(username) -> bool | None`
- `search_name(name, location) -> list[CandidateProfile]`
- `scrape_profile(url) -> ProfileData`

New platforms are auto-discovered from the platforms directory.

## Verification Engine

Multi-signal weighted scoring:

- Profile photo perceptual hashing (0.35)
- Bio text TF-IDF cosine similarity (0.20)
- Timezone correlation from posting times (0.15)
- Username pattern Jaro-Winkler distance (0.10)
- Mutual connections cross-platform (0.10)
- Writing style stylometrics (0.10)

Threshold levels: 0.30 (discard), 0.45 (possible), 0.70 (likely), 0.90 (confirmed).

## Key Design Decisions

- **Async-first**: All network I/O uses asyncio + aiohttp. Platform checks run concurrently.
- **Offline-capable**: Works without LLM API keys. Falls back to TF-IDF/regex heuristics.
- **Plugin architecture**: New platforms added by dropping a file, no registration needed.
- **Pydantic models**: All data flows use typed models for validation and serialization.

## Dependencies

| Package | Purpose |
|---------|---------|
| aiohttp | Async HTTP client |
| beautifulsoup4 + lxml | HTML parsing |
| pydantic | Data models and validation |
| click + rich | CLI framework and terminal UI |
| imagehash + Pillow | Profile photo perceptual hashing |
| scikit-learn | TF-IDF vectorization, cosine similarity |
| jellyfish | Fuzzy string matching |
| networkx | Graph-based relationship mapping |
| python-dateutil | Timestamp parsing for timezone analysis |

### Optional

| Package | Extra | Purpose |
|---------|-------|---------|
| playwright | `[playwright]` | JS-rendered page scraping |
| face-recognition | `[face]` | Face embedding photo matching |
| openai | `[llm]` | LLM-enhanced analysis |
| fastapi | `[api]` | REST API server |

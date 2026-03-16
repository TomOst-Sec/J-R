# Argus Architecture Guide

## System Overview

```
┌─────────────────────────────────────────────────────┐
│                      CLI / API / MCP                 │
│  argus resolve │ POST /resolve │ resolve_person tool │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  Agent Pipeline                      │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │ Resolver  │──>│  Linker  │──>│   Profiler   │    │
│  │  Agent    │   │  Agent   │   │    Agent     │    │
│  └────┬─────┘   └──────────┘   └──────────────┘    │
│       │                                              │
│  ┌────▼─────────────────────────────────────────┐   │
│  │           Platform Fan-out (parallel)         │   │
│  │  GitHub │ Reddit │ HN │ Twitter │ LinkedIn │…│   │
│  └────┬─────────────────────────────────────────┘   │
│       │                                              │
│  ┌────▼─────────────────────────────────────────┐   │
│  │        Verification Engine                    │   │
│  │  PhotoHash │ BioSim │ UserPattern │ Timezone  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              Storage (SQLite)                         │
│  investigations │ accounts │ content                  │
└─────────────────────────────────────────────────────┘
```

## Module Layout

```
src/argus/
├── __init__.py          # Package version
├── cli.py               # Click CLI entry point
├── agents/              # BaseAgent protocol + agent implementations
│   ├── base.py          # Abstract BaseAgent with timing
│   ├── resolver.py      # Identity resolution pipeline
│   ├── linker.py        # Topic connection mapper
│   ├── profiler.py      # Behavioral profile builder
│   ├── classifiers.py   # Dimension classification (keyword-based)
│   └── orchestrator.py  # Pipeline and parallel execution
├── platforms/           # BasePlatform interface + per-platform scrapers
│   ├── base.py          # Abstract BasePlatform
│   ├── registry.py      # Auto-discovery registry
│   ├── github.py        # GitHub REST API
│   ├── reddit.py        # Reddit JSON API
│   └── ...              # 11 more platform modules
├── verification/        # Confidence scoring engine
│   ├── engine.py        # VerificationEngine (weighted scoring)
│   └── signals.py       # PhotoHash, BioSim, UsernamePattern signals
├── storage/             # SQLite persistence layer
│   ├── database.py      # Async SQLite wrapper
│   └── repository.py    # Investigation and account repositories
├── config/              # Configuration system
│   ├── settings.py      # Pydantic config models
│   └── loader.py        # Layered config loading
├── stealth/             # Rate limiting, UA rotation, proxy support
├── api/                 # REST API (FastAPI)
│   └── server.py        # Endpoints, WebSocket, auth
├── mcp/                 # MCP server (Model Context Protocol)
│   └── server.py        # Tools, resources, prompts
└── utils/               # Username generation, helpers
```

## Agent Pipeline

### BaseAgent

All agents inherit from `BaseAgent` (ABC) and implement `async def _execute(input) -> output`. The base class wraps execution with automatic timing.

```python
class BaseAgent(abc.ABC):
    name: str
    async def _execute(self, input: AgentInput) -> AgentOutput: ...
    async def run(self, input: AgentInput) -> AgentOutput:  # adds timing
```

### Resolver Agent

The core pipeline agent. Given a `TargetInput`:

1. **Username Generation** — generates 20-30 likely usernames using configurable rules
2. **Seed Scraping** — scrapes provided seed URLs for ground-truth profile data
3. **Platform Fan-out** — checks all enabled platforms in parallel via `asyncio.gather`
4. **Profile Scraping** — scrapes full profiles for discovered candidates
5. **Verification** — scores each candidate using the verification engine
6. **Persistence** — stores results in SQLite
7. **Output** — returns `ResolverOutput` with verified accounts sorted by confidence

### Linker Agent

Takes verified accounts + topic and discovers connections:

1. **Keyword Search** — scans bios and content for topic mentions
2. **Semantic Similarity** — TF-IDF cosine similarity between content and topic
3. **Relationship Classification** — mention, employment, contribution, following
4. **Ranking** — sorted by confidence score, deduplicated

### Profiler Agent

Builds a behavioral profile from aggregated content:

1. **Content Aggregation** — collects text from all verified accounts
2. **Topic Extraction** — TF-IDF with bigrams, top-20 keywords
3. **Activity Scoring** — recency decay × engagement × content length weighting
4. **Dimension Classification** — professional / personal / public (keyword lists)
5. **Temporal Analysis** — rising / declining / stable trend detection
6. **Summary Stats** — estimated timezone, top platforms, posting frequency

## Verification Engine

Multi-signal weighted scoring produces a confidence value (0.0–1.0):

| Signal | Class | Default Weight | Method |
|--------|-------|--------|--------|
| Photo Hash | `PhotoHashSignal` | 0.35 | Perceptual hash hamming distance |
| Bio Similarity | `BioSimilaritySignal` | 0.20 | TF-IDF cosine similarity |
| Timezone | `TimezoneCorrelationSignal` | 0.15 | Posting hour distribution |
| Username Pattern | `UsernamePatternSignal` | 0.10 | Jaro-Winkler string distance |

**Scoring:** `confidence = Σ(score × weight) / Σ(weight)`

**Labels:** <0.30 discarded, 0.30–0.45 possible, 0.45–0.70 likely, ≥0.70 confirmed

## Platform Plugin System

Platforms implement `BasePlatform` (ABC):

```python
class BasePlatform(ABC):
    name: str
    base_url: str
    rate_limit_per_minute: int = 30
    priority: int = 50

    async def check_username(self, username: str) -> bool | None
    async def search_name(self, name: str, location: str | None) -> list[CandidateProfile]
    async def scrape_profile(self, url: str) -> ProfileData | None
    async def scrape_content(self, url: str, max_items: int) -> list[ContentItem]  # optional
```

The `PlatformRegistry` auto-discovers all subclasses in `argus/platforms/` via `importlib` + `inspect`.

## Key Design Decisions

- **Async-first**: All network I/O uses asyncio + aiohttp. Platform checks run concurrently.
- **Offline-capable**: Works without LLM API keys. Falls back to TF-IDF/regex heuristics.
- **Plugin architecture**: New platforms added by dropping a file in platforms/, no registration needed.
- **Pydantic v2 models**: All data flows use typed models for validation and serialization.
- **Three interfaces**: CLI, REST API, and MCP server share the same agent pipeline.

## Dependencies

| Package | Purpose |
|---------|---------|
| aiohttp | Async HTTP client |
| beautifulsoup4 + lxml | HTML parsing |
| pydantic v2 | Data models and validation |
| click + rich | CLI framework and terminal UI |
| imagehash + Pillow | Profile photo perceptual hashing |
| scikit-learn | TF-IDF vectorization, cosine similarity |
| jellyfish | Fuzzy string matching (Jaro-Winkler) |
| networkx | Graph-based relationship mapping |

### Optional

| Package | Extra | Purpose |
|---------|-------|---------|
| fastapi + uvicorn | `[api]` | REST API server |
| mcp | `[mcp]` | MCP server for AI assistants |
| playwright | `[playwright]` | JS-rendered page scraping |
| face-recognition | `[face]` | Face embedding photo matching |
| openai | `[llm]` | LLM-enhanced analysis |

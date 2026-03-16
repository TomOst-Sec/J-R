# Argus

Multi-agent OSINT platform for cross-platform identity resolution and verification.

Argus takes a person's name — plus optional signals like location, known URLs, email, or username — and discovers, verifies, and profiles that person across social media platforms and the open web. Unlike simple username-existence checkers, Argus uses cross-platform signal correlation (bio similarity, profile photo hashing, timezone analysis, writing style) to assign confidence scores and filter false positives.

## Status

**Phase 1 — Foundation / MVP** (in progress)

The project is in early development. The directory structure and build system are scaffolded. No features are implemented yet.

## Installation

Requires Python 3.12+ and [UV](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd argus
uv sync
```

### Optional extras

```bash
uv sync --extra playwright   # Browser automation for JS-rendered platforms
uv sync --extra face          # Face recognition for photo matching
uv sync --extra llm           # LLM integration (OpenAI)
uv sync --extra api           # REST API server (FastAPI)
```

## Development

```bash
uv run pytest                 # Run tests
uv run ruff check src/        # Lint
uv run mypy src/              # Type check
```

## Project Structure

```
src/argus/
├── __init__.py          # Package root (v0.1.0)
├── cli.py               # CLI entry point (click)
├── agents/              # Agent framework (resolver, linker, profiler)
├── platforms/           # Platform scraper modules
├── verification/        # Confidence scoring engine
├── storage/             # SQLite persistence
├── config/              # Configuration system (argus.toml)
├── stealth/             # Rate limiting, proxy rotation, anti-detection
└── reporting/           # Report generation (JSON, Markdown, HTML, CSV)
tests/
├── conftest.py          # Shared test fixtures
├── test_placeholder.py  # Import verification test
└── fixtures/            # Test data
```

## Architecture

Argus is built as a composable agent pipeline:

1. **Resolver Agent** — discovers accounts across platforms, checks username existence, runs name searches
2. **Linker Agent** (optional) — maps connections between a target and a specified topic/organization
3. **Profiler Agent** (optional) — builds a behavioral profile from discovered content

Each agent implements `BaseAgent` with `async def run(input) -> output` and communicates via typed Pydantic models. Agents can run standalone, be chained via CLI pipes, or called through REST API / MCP server.

### Verification Signals

The verification engine scores each discovered account (0.0–1.0) using weighted signals:

| Signal | Weight | Method |
|--------|--------|--------|
| Profile photo match | 0.35 | Perceptual hashing (pHash) |
| Bio similarity | 0.20 | TF-IDF cosine similarity |
| Timezone correlation | 0.15 | Posting timestamp analysis |
| Username pattern | 0.10 | Jaro-Winkler distance |
| Mutual connections | 0.10 | Cross-platform follow graph |
| Writing style | 0.10 | Stylometric features |

### Target Platforms (Milestone 1)

GitHub, Reddit, HackerNews, Twitter/X, LinkedIn, Instagram

## Configuration

Argus uses `argus.toml` for configuration (not yet implemented). Settings cover platform enables, rate limits, proxy config, verification weights, and LLM integration.

All config values are overridable via CLI flags and environment variables.

## License

MIT

# Argus OSINT

Multi-agent OSINT platform for cross-platform identity resolution, verification, and behavioral profiling.

Argus takes a person's name — plus optional signals like location, known URLs, email, or username — and discovers, verifies, and profiles that person across 13+ social media platforms. Unlike simple username checkers, Argus uses cross-platform signal correlation (bio similarity, profile photo hashing, timezone analysis, username patterns) to assign confidence scores and filter false positives.

## Quick Start

```bash
pip install argus-osint
argus resolve "John Doe" --location "San Francisco"
```

Or with UV:

```bash
uvx argus-osint resolve "John Doe"
```

## Features

- **Identity Resolution** — discover accounts across 13+ platforms using username generation, name search, and seed URL matching
- **Confidence Scoring** — multi-signal verification engine with weighted scoring (photo hash, bio similarity, username patterns, timezone)
- **Behavioral Profiling** — TF-IDF topic extraction, dimension classification (professional/personal/public), temporal trends
- **Topic Linking** — find connections between a target and specific topics, organizations, or interests
- **Rich CLI** — table output, JSON output, progress bars, and report generation
- **REST API** — FastAPI server with OpenAPI docs, WebSocket streaming, bearer token auth
- **MCP Server** — Model Context Protocol integration for Claude Code and other AI assistants
- **Plugin Architecture** — add new platforms by implementing a single abstract class

## Platform Support

| Platform | Username Check | Name Search | Profile Scrape | Content Scrape |
|----------|:-:|:-:|:-:|:-:|
| GitHub | Y | Y | Y | Y (repos) |
| Reddit | Y | - | Y | Y (posts/comments) |
| HackerNews | Y | - | Y | Y (stories) |
| Twitter/X | Y | - | Y | - |
| LinkedIn | Y | Y | Y | - |
| Instagram | Y | - | Y | - |
| Facebook | - | Y (dork) | - | - |
| YouTube | Y | Y | Y | - |
| Mastodon | Y | - | Y | - |
| Stack Overflow | Y | Y | Y | - |
| Medium | Y | - | Y | - |
| TikTok | Y | - | Y | - |
| Telegram | Y | - | - | - |

## Installation

Requires Python 3.12+.

```bash
# Core install
pip install argus-osint

# With optional extras
pip install argus-osint[api]         # REST API server (FastAPI + Uvicorn)
pip install argus-osint[playwright]  # Browser automation for JS-rendered platforms
pip install argus-osint[face]        # Face recognition for photo matching
pip install argus-osint[llm]         # LLM integration (OpenAI)
```

### Development

```bash
git clone https://github.com/TomOst-Sec/J-R.git
cd J-R
uv sync --group dev
uv run pytest          # Run tests
uv run ruff check src/ # Lint
```

## Usage

### Resolve a person

```bash
# Table output (default)
argus resolve "John Doe" --location "San Francisco"

# JSON output
argus resolve "John Doe" --output json

# With seed URL and username hint
argus resolve "John Doe" --seed-url https://github.com/johndoe --username-hint johndoe

# Restrict to specific platforms
argus resolve "John Doe" --platforms github,reddit,hackernews
```

### Link topics

```bash
argus link "John Doe" --topic "machine learning"
argus link "John Doe" --topic "Acme Corp" --topic-description "Technology company in SF"
```

### Build profile

```bash
argus profile "John Doe"
argus profile "John Doe" --output json
```

### Generate reports

```bash
argus report "John Doe" --format markdown --output report.md
argus report "John Doe" --format json
```

### List platforms

```bash
argus platforms
```

### Configuration

```bash
argus config init    # Create default argus.toml
argus config show    # Display current config
argus config path    # Show config file locations
```

### REST API Server

```bash
pip install argus-osint[api]
argus serve --api --port 8000
# OpenAPI docs at http://localhost:8000/docs
```

### MCP Server (for Claude Code)

```bash
argus serve --mcp
```

## Configuration

Argus uses `argus.toml` for configuration. Create one with `argus config init`.

```toml
[general]
default_threshold = 0.45
max_concurrent_requests = 10

[stealth]
user_agent_rotation = true
min_delay = 2.0
max_delay = 5.0

[verification]
minimum_threshold = 0.30
photo_matching_enabled = true

[platforms.github]
enabled = true
rate_limit_per_minute = 30
```

Configuration priority: CLI flags > environment variables > ./argus.toml > ~/.argus/argus.toml > defaults.

Environment variable overrides use `ARGUS_` prefix: `ARGUS_GENERAL_THRESHOLD=0.6`.

## Architecture

```
Target Input ──> Resolver Agent ──> Linker Agent ──> Profiler Agent
                      │                  │                 │
              ┌───────┴───────┐          │                 │
              │  Platform     │    Topic Search       TF-IDF Topic
              │  Fan-out      │    + Semantic Sim     Extraction
              │  (parallel)   │                       + Dimension
              │               │                       Classification
              └───────┬───────┘
                      │
              Verification Engine
              (multi-signal scoring)
```

See [docs/architecture.md](docs/architecture.md) for detailed design documentation.

## Documentation

- [Architecture Guide](docs/architecture.md)
- [Platform Development](docs/platform-development.md)
- [API Reference](docs/api-reference.md)
- [Configuration Reference](docs/configuration.md)

## License

MIT

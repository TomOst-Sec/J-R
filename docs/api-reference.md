# API Reference

## CLI Commands

### argus resolve

Resolve a person across social media platforms.

```
argus resolve NAME [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--location` | str | None | Location hint for search filtering |
| `--seed-url` | str (multiple) | [] | Seed profile URLs for verification |
| `--email` | str | None | Email address hint |
| `--username-hint` | str | None | Known username hint |
| `--phone` | str | None | Phone number hint |
| `--threshold` | float | 0.45 | Override minimum confidence threshold |
| `--output` | table\|json | table | Output format |
| `--platforms` | str | all | Comma-separated platform list |
| `--config` | path | None | Path to argus.toml |
| `--verbose` | flag | False | Enable debug output |

### argus link

Find connections between a person and a topic.

```
argus link NAME --topic TOPIC [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--topic` | str | required | Topic to find connections for |
| `--topic-description` | str | None | Extended topic description |
| `--output` | table\|json | table | Output format |

### argus profile

Build a behavioral profile.

```
argus profile NAME [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | table\|json | table | Output format |

### argus report

Generate a report.

```
argus report NAME [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | json\|markdown | json | Report format |
| `--output` | path | stdout | Output file path |

### argus platforms

List registered platform modules.

```
argus platforms
```

### argus config

Configuration management.

```
argus config show     # Display current config (JSON)
argus config path     # Show config file search paths
argus config init     # Create default argus.toml
```

## REST API

Base URL: `http://localhost:8000`

OpenAPI documentation: `http://localhost:8000/docs`

### Authentication

Bearer token authentication. Set token in config or pass via header:

```
Authorization: Bearer <token>
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/resolve` | Run resolver agent |
| POST | `/link` | Run linker agent |
| POST | `/profile` | Run profiler agent |
| POST | `/investigate` | Start background investigation |
| GET | `/investigate/{id}` | Get investigation results |
| GET | `/investigate/{id}/report` | Get rendered report |
| DELETE | `/investigate/{id}` | Delete investigation |
| GET | `/investigations` | List all investigations |
| GET | `/platforms` | List platform modules |
| WS | `/investigate/{id}/stream` | WebSocket event stream |

### Request Examples

```bash
# Resolve
curl -X POST http://localhost:8000/resolve \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "location": "SF"}'

# Link
curl -X POST http://localhost:8000/link \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "topic": "machine learning"}'

# Start investigation
curl -X POST http://localhost:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}'
```

## MCP Tools

Available when running `argus serve --mcp`:

| Tool | Description |
|------|-------------|
| `resolve_person` | Resolve a person across platforms |
| `link_topic` | Find topic connections |
| `profile_person` | Build behavioral profile |
| `get_investigation` | Get stored investigation |
| `list_investigations` | List all investigations |

### MCP Resources

| URI Pattern | Description |
|------------|-------------|
| `investigation://{id}/report` | Markdown report |
| `investigation://{id}/accounts` | Verified accounts list |
| `investigation://{id}/connections` | Linker connections |

### MCP Prompts

| Prompt | Description |
|--------|-------------|
| `osint_investigate` | Full investigation workflow |
| `osint_quick_check` | Quick username check |

## Python Library API

```python
import asyncio
from argus.agents.resolver import ResolverAgent
from argus.models.agent import AgentInput
from argus.models.target import TargetInput

async def main():
    agent = ResolverAgent()
    target = TargetInput(name="John Doe", location="San Francisco")
    output = await agent.run(AgentInput(target=target))
    for account in output.accounts:
        print(f"{account.candidate.platform}: {account.candidate.username} ({account.confidence:.0%})")

asyncio.run(main())
```

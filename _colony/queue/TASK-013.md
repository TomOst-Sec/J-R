# TASK-013: CLI — argus resolve command

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-012
**Estimated Complexity:** medium

## Description

Implement the `argus resolve` CLI command using Click and Rich for terminal output.

## Requirements

1. Update `src/argus/cli.py`:
   - Main Click group: `@click.group()` with version option
   - `argus resolve` subcommand:
     - Arguments: `name` (required, positional)
     - Options: `--location`, `--seed-url` (multiple), `--email`, `--username-hint`, `--phone`
     - Options: `--threshold` (float, override config), `--output` (choice: table|json, default table), `--platforms` (comma-separated list to restrict)
     - Options: `--config` (path to argus.toml)
   - On invocation:
     1. Load config
     2. Create TargetInput from CLI args
     3. Initialize ResolverAgent
     4. Run resolver pipeline with Rich progress bar
     5. Display results

2. Output formats:
   - **table** (default): Rich table with columns: Platform, Username, URL, Confidence, Label
     - Confidence color-coded: red <0.30, yellow 0.30-0.70, green >=0.70
     - Header shows target name, platforms checked, time elapsed
   - **json**: Raw JSON dump of ResolverOutput

3. Progress display:
   - Rich progress bar showing: "Checking platforms... [3/6]"
   - Live table that updates as results come in (accounts appear in real-time)
   - Final summary: "Found N accounts across M platforms in X.Xs"

4. Error handling:
   - Friendly error messages for common issues (no network, config not found)
   - `--verbose` flag for debug output

## Acceptance Criteria

- `argus resolve "John Doe"` works end-to-end
- Table output is formatted and color-coded
- JSON output is valid JSON matching ResolverOutput schema
- Progress display shows real-time updates
- `--help` shows all options with descriptions
- `uv run pytest tests/test_cli.py` passes

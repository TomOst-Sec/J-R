"""Argus CLI entry point."""

from __future__ import annotations

import asyncio
import sys
import time

import click
from rich.console import Console
from rich.table import Table

from argus import __version__

console = Console()


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Argus OSINT platform."""


@main.command()
@click.argument("name")
@click.option("--location", default=None, help="Location hint for search filtering.")
@click.option("--seed-url", multiple=True, help="Seed profile URLs for verification.")
@click.option("--email", default=None, help="Email address hint.")
@click.option("--username-hint", default=None, help="Known username hint.")
@click.option("--phone", default=None, help="Phone number hint.")
@click.option("--threshold", type=float, default=None, help="Override minimum confidence threshold.")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--platforms", default=None, help="Comma-separated list of platforms to check.")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to argus.toml.")
@click.option("--verbose", is_flag=True, help="Enable debug output.")
def resolve(
    name: str,
    location: str | None,
    seed_url: tuple[str, ...],
    email: str | None,
    username_hint: str | None,
    phone: str | None,
    threshold: float | None,
    output_format: str,
    platforms: str | None,
    config_path: str | None,
    verbose: bool,
) -> None:
    """Resolve a person across social media platforms."""
    try:
        asyncio.run(_resolve_async(
            name=name,
            location=location,
            seed_urls=list(seed_url),
            email=email,
            username_hint=username_hint,
            phone=phone,
            threshold=threshold,
            output_format=output_format,
            platforms=platforms,
            config_path=config_path,
            verbose=verbose,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


async def _resolve_async(
    name: str,
    location: str | None,
    seed_urls: list[str],
    email: str | None,
    username_hint: str | None,
    phone: str | None,
    threshold: float | None,
    output_format: str,
    platforms: str | None,
    config_path: str | None,
    verbose: bool,
) -> None:
    import aiohttp

    from argus.agents.resolver import ResolverAgent
    from argus.config import load_config
    from argus.config.settings import ArgusConfig
    from argus.models.agent import AgentInput
    from argus.models.target import TargetInput
    from argus.platforms.registry import PlatformRegistry
    from argus.storage.database import Database

    # Load config
    if config_path:
        config = load_config(config_path)
    else:
        config = ArgusConfig()

    if threshold is not None:
        config.verification.minimum_threshold = threshold

    # Discover platforms
    registry = PlatformRegistry()
    registry.discover_platforms()

    if platforms:
        platform_list = [p.strip() for p in platforms.split(",")]
        for pname in list(registry._platforms.keys()):
            if pname not in platform_list:
                del registry._platforms[pname]

    # Build target
    target = TargetInput(
        name=name,
        location=location,
        seed_urls=seed_urls,
        email=email,
        username_hint=username_hint,
        phone=phone,
    )

    platform_names = registry.list_platforms()
    is_json = output_format == "json"

    if not is_json:
        console.print(f"[bold]Resolving:[/bold] {name}")
        if location:
            console.print(f"[dim]Location:[/dim] {location}")
        console.print(
            f"[dim]Platforms:[/dim] "
            f"{', '.join(platform_names) if platform_names else 'none discovered'}"
        )

    start_time = time.monotonic()

    # Run resolver with progress display
    db = Database()
    await db.initialize()

    async with aiohttp.ClientSession() as session:
        agent = ResolverAgent(
            session=session,
            config=config,
            registry=registry,
            db=db,
        )
        agent_input = AgentInput(target=target)

        if not is_json and platform_names:
            from rich.live import Live
            from rich.panel import Panel
            from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

            results_table = Table(show_header=True, header_style="bold")
            results_table.add_column("Platform")
            results_table.add_column("Username")
            results_table.add_column("URL")
            results_table.add_column("Confidence", justify="right")
            results_table.add_column("Label")

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                console=console,
                transient=False,
            )
            task_id = progress.add_task(
                "Checking platforms...",
                total=len(platform_names),
            )

            from rich.layout import Layout

            layout = Layout()
            layout.split_column(
                Layout(progress, size=1),
                Layout(Panel(results_table, title="Discovered Accounts", border_style="dim")),
            )

            with Live(layout, console=console, refresh_per_second=4, transient=True):
                output = await agent.run(agent_input)
                progress.update(
                    task_id,
                    completed=len(platform_names),
                    description="[green]Pipeline complete[/green]",
                )

                # Populate the live table with results
                from argus.models.agent import ResolverOutput

                if isinstance(output, ResolverOutput):
                    for vr in output.accounts:
                        conf = vr.confidence
                        color = "green" if conf >= 0.70 else "yellow" if conf >= 0.30 else "red"
                        results_table.add_row(
                            vr.candidate.platform,
                            vr.candidate.username,
                            vr.candidate.url,
                            f"[{color}]{conf:.0%}[/{color}]",
                            vr.threshold_label,
                        )
        else:
            output = await agent.run(agent_input)

    await db.close()
    elapsed = time.monotonic() - start_time

    # Display results
    if is_json:
        console.print(output.model_dump_json(indent=2))
    else:
        _display_table(output, name, len(platform_names), elapsed)


def _display_table(output, target_name: str, platform_count: int, elapsed: float) -> None:
    from argus.models.agent import ResolverOutput

    assert isinstance(output, ResolverOutput)
    accounts = output.accounts

    console.print()
    console.print(
        f"[bold]Results for {target_name}[/bold] — "
        f"{platform_count} platforms checked in {elapsed:.1f}s"
    )
    console.print()

    if not accounts:
        console.print("[yellow]No accounts found above threshold.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Platform")
    table.add_column("Username")
    table.add_column("URL")
    table.add_column("Confidence", justify="right")
    table.add_column("Label")

    for vr in accounts:
        conf = vr.confidence
        if conf >= 0.70:
            color = "green"
        elif conf >= 0.30:
            color = "yellow"
        else:
            color = "red"

        table.add_row(
            vr.candidate.platform,
            vr.candidate.username,
            vr.candidate.url,
            f"[{color}]{conf:.0%}[/{color}]",
            vr.threshold_label,
        )

    console.print(table)
    console.print(
        f"\n[bold]Found {len(accounts)} account(s) across "
        f"{len(set(vr.candidate.platform for vr in accounts))} platform(s)[/bold]"
    )


# ---------------------------------------------------------------------------
# argus platforms
# ---------------------------------------------------------------------------


@main.command("platforms")
def platforms_cmd() -> None:
    """List all registered platform modules."""
    from argus.platforms.registry import PlatformRegistry

    registry = PlatformRegistry()
    registry.discover_platforms()
    names = registry.list_platforms()

    if not names:
        console.print("[yellow]No platforms discovered.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Platform")
    table.add_column("Base URL")
    table.add_column("Rate Limit")
    table.add_column("Auth")
    table.add_column("Playwright")
    table.add_column("Priority", justify="right")

    for name in sorted(names):
        cls = registry.get_platform(name)
        if cls is None:
            continue
        table.add_row(
            cls.name,
            cls.base_url,
            f"{cls.rate_limit_per_minute}/min",
            "yes" if cls.requires_auth else "no",
            "yes" if cls.requires_playwright else "no",
            str(cls.priority),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# argus config
# ---------------------------------------------------------------------------


@main.group("config")
def config_cmd() -> None:
    """Manage configuration."""


@config_cmd.command("show")
def config_show() -> None:
    """Display the current configuration."""
    from argus.config import load_config

    config = load_config()
    console.print(config.model_dump_json(indent=2))


@config_cmd.command("path")
def config_path() -> None:
    """Show configuration file search paths."""
    from pathlib import Path

    paths = [
        Path("argus.toml"),
        Path.home() / ".argus" / "argus.toml",
    ]
    for p in paths:
        status = "[green]found[/green]" if p.exists() else "[dim]not found[/dim]"
        console.print(f"  {p} — {status}")


@config_cmd.command("init")
def config_init() -> None:
    """Create a default argus.toml in the current directory."""
    from pathlib import Path

    target = Path("argus.toml")
    if target.exists():
        console.print("[yellow]argus.toml already exists.[/yellow]")
        return

    example = Path("argus.toml.example")
    if example.exists():
        target.write_text(example.read_text())
    else:
        target.write_text("[general]\ndefault_threshold = 0.45\n")
    console.print(f"[green]Created {target}[/green]")


# ---------------------------------------------------------------------------
# argus link
# ---------------------------------------------------------------------------


@main.command("link")
@click.argument("name")
@click.option("--topic", required=True, help="Topic to find connections for.")
@click.option("--topic-description", default=None, help="Extended topic description.")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--input", "input_source", default=None, help="Read JSON from stdin (-) or file.")
@click.option("--quiet", is_flag=True, help="Suppress non-JSON output.")
def link_cmd(
    name: str,
    topic: str,
    topic_description: str | None,
    output_format: str,
    input_source: str | None,
    quiet: bool,
) -> None:
    """Find connections between a person and a topic."""
    try:
        asyncio.run(_link_async(name, topic, topic_description, output_format, input_source, quiet))
    except Exception as e:
        if not quiet:
            console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _link_async(
    name: str,
    topic: str,
    topic_description: str | None,
    output_format: str,
    input_source: str | None = None,
    quiet: bool = False,
) -> None:
    from argus.agents.linker import LinkerAgent, LinkerInput
    from argus.models.target import TargetInput

    stderr_console = Console(stderr=True) if quiet else console

    # Read piped input if specified
    accounts = []
    content = []
    if input_source == "-" or (input_source is None and not sys.stdin.isatty()):
        import json as json_mod

        stdin_data = sys.stdin.read()
        if stdin_data.strip():
            piped = json_mod.loads(stdin_data)
            accounts = piped.get("accounts", [])
            content = piped.get("content", [])

    if not quiet:
        stderr_console.print(f"[bold]Linking:[/bold] {name} <-> {topic}")

    agent = LinkerAgent()
    input_data = LinkerInput(
        target=TargetInput(name=name),
        topic=topic,
        topic_description=topic_description,
        accounts=accounts,
        content=content,
    )
    output = await agent.run(input_data)

    if output_format == "json":
        print(output.model_dump_json(indent=2))
    else:
        if not output.connections:
            stderr_console.print("[yellow]No connections found.[/yellow]")
            return
        table = Table(show_header=True, header_style="bold")
        table.add_column("Platform")
        table.add_column("Type")
        table.add_column("Confidence", justify="right")
        table.add_column("Snippet")
        for conn in output.connections:
            table.add_row(
                conn.platform,
                conn.relationship_type,
                f"{conn.confidence:.0%}",
                conn.content_snippet[:80],
            )
        console.print(table)


# ---------------------------------------------------------------------------
# argus profile
# ---------------------------------------------------------------------------


@main.command("profile")
@click.argument("name")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--input", "input_source", default=None, help="Read JSON from stdin (-) or file.")
@click.option("--quiet", is_flag=True, help="Suppress non-JSON output.")
def profile_cmd(name: str, output_format: str, input_source: str | None, quiet: bool) -> None:
    """Build a behavioral profile for a person."""
    try:
        asyncio.run(_profile_async(name, output_format, input_source, quiet))
    except Exception as e:
        if not quiet:
            console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _profile_async(
    name: str,
    output_format: str,
    input_source: str | None = None,
    quiet: bool = False,
) -> None:
    from rich.tree import Tree

    from argus.agents.profiler import ProfilerAgent, ProfilerInput
    from argus.models.target import TargetInput

    stderr_console = Console(stderr=True) if quiet else console

    # Read piped input
    accounts = []
    content = []
    if input_source == "-" or (input_source is None and not sys.stdin.isatty()):
        import json as json_mod

        stdin_data = sys.stdin.read()
        if stdin_data.strip():
            piped = json_mod.loads(stdin_data)
            accounts = piped.get("accounts", [])
            content = piped.get("content", [])

    if not quiet:
        stderr_console.print(f"[bold]Profiling:[/bold] {name}")

    agent = ProfilerAgent()
    input_data = ProfilerInput(
        target=TargetInput(name=name),
        accounts=accounts,
        content=content,
    )
    output = await agent.run(input_data)

    if output_format == "json":
        print(output.model_dump_json(indent=2))
    else:
        if not output.dimensions:
            stderr_console.print("[yellow]No profile data available.[/yellow]")
            return
        tree = Tree(f"[bold]Profile: {name}[/bold]")
        for dim, topics in output.dimensions.items():
            branch = tree.add(f"[bold]{dim.capitalize()}[/bold]")
            for topic in topics[:10]:
                topic_node = branch.add(f"{topic.topic} (score: {topic.score:.2f}, {topic.trend})")
                for ev in topic.evidence[:3]:
                    topic_node.add(f"[dim]{ev}[/dim]")
        console.print(tree)


# ---------------------------------------------------------------------------
# argus report
# ---------------------------------------------------------------------------


@main.command("report")
@click.argument("name")
@click.option(
    "--format",
    "report_format",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Report format.",
)
@click.option("--output", "output_file", default=None, help="Output file path.")
def report_cmd(name: str, report_format: str, output_file: str | None) -> None:
    """Generate a report from stored investigation results."""
    console.print(f"[bold]Report:[/bold] {name} ({report_format})")

    if report_format == "markdown":
        content = f"# Investigation Report: {name}\n\n_No stored data available._\n"
    else:
        import json as json_mod

        content = json_mod.dumps({"target": name, "status": "no stored data"}, indent=2)

    if output_file:
        from pathlib import Path

        Path(output_file).write_text(content)
        console.print(f"[green]Report saved to {output_file}[/green]")
    else:
        console.print(content)

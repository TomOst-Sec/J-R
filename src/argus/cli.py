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

    console.print(f"[bold]Resolving:[/bold] {name}")
    if location:
        console.print(f"[dim]Location:[/dim] {location}")
    platform_names = registry.list_platforms()
    console.print(f"[dim]Platforms:[/dim] {', '.join(platform_names) if platform_names else 'none discovered'}")

    start_time = time.monotonic()

    # Run resolver
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

        console.print("[dim]Running resolver pipeline...[/dim]")
        output = await agent.run(agent_input)

    await db.close()
    elapsed = time.monotonic() - start_time

    # Display results
    if output_format == "json":
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

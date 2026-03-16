"""Argus CLI entry point — full command suite."""

from __future__ import annotations

import asyncio
import sys
import time

import click
from rich.console import Console
from rich.table import Table

from argus import __version__

console = Console()


def _load_config(config_path: str | None = None):
    from argus.config import load_config
    from argus.config.settings import ArgusConfig

    if config_path:
        return load_config(config_path)
    return ArgusConfig()


def _build_target(name, location, seed_urls, email, username_hint, phone):
    from argus.models.target import TargetInput

    return TargetInput(
        name=name, location=location, seed_urls=seed_urls,
        email=email, username_hint=username_hint, phone=phone,
    )


def _setup_registry(platforms_filter: str | None = None):
    from argus.platforms.registry import PlatformRegistry

    registry = PlatformRegistry()
    registry.discover_platforms()
    if platforms_filter:
        allowed = [p.strip() for p in platforms_filter.split(",")]
        for pname in list(registry._platforms.keys()):
            if pname not in allowed:
                del registry._platforms[pname]
    return registry


def _run_async(coro_func, **kwargs):
    try:
        asyncio.run(coro_func(**kwargs))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if kwargs.get("verbose"):
            console.print_exception()
        sys.exit(1)


# ─── Main group ──────────────────────────────────────────────────────────

@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Argus OSINT platform."""


# ─── resolve ─────────────────────────────────────────────────────────────

@main.command()
@click.argument("name")
@click.option("--location", default=None, help="Location hint.")
@click.option("--seed-url", multiple=True, help="Seed profile URLs.")
@click.option("--email", default=None, help="Email hint.")
@click.option("--username-hint", default=None, help="Known username.")
@click.option("--phone", default=None, help="Phone hint.")
@click.option("--threshold", type=float, default=None, help="Confidence threshold override.")
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--platforms", default=None, help="Comma-separated platform list.")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.option("--verbose", is_flag=True)
def resolve(name, location, seed_url, email, username_hint, phone,
            threshold, output_format, platforms, config_path, verbose):
    """Resolve a person across social media platforms."""
    _run_async(
        _resolve_async, name=name, location=location, seed_url=seed_url,
        email=email, username_hint=username_hint, phone=phone, threshold=threshold,
        output_format=output_format, platforms=platforms, config_path=config_path, verbose=verbose,
    )


async def _resolve_async(*, name, location, seed_url, email, username_hint, phone,
                          threshold, output_format, platforms, config_path, verbose):
    import aiohttp
    from argus.agents.resolver import ResolverAgent
    from argus.models.agent import AgentInput
    from argus.storage.database import Database

    config = _load_config(config_path)
    if threshold is not None:
        config.verification.minimum_threshold = threshold
    registry = _setup_registry(platforms)
    target = _build_target(name, location, list(seed_url), email, username_hint, phone)

    console.print(f"[bold]Resolving:[/bold] {name}")
    platform_names = registry.list_platforms()
    console.print(f"[dim]Platforms:[/dim] {', '.join(platform_names) or 'none'}")

    start = time.monotonic()
    db = Database()
    await db.initialize()
    async with aiohttp.ClientSession() as session:
        agent = ResolverAgent(session=session, config=config, registry=registry, db=db)
        output = await agent.run(AgentInput(target=target))
    await db.close()
    elapsed = time.monotonic() - start

    if output_format == "json":
        console.print(output.model_dump_json(indent=2))
    else:
        _display_resolve_table(output, name, len(platform_names), elapsed)


# ─── link ────────────────────────────────────────────────────────────────

@main.command()
@click.argument("name")
@click.option("--location", default=None, help="Location hint.")
@click.option("--seed-url", multiple=True, help="Seed profile URLs.")
@click.option("--email", default=None)
@click.option("--username-hint", default=None)
@click.option("--phone", default=None)
@click.option("--threshold", type=float, default=None)
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--platforms", default=None)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.option("--verbose", is_flag=True)
def link(name, location, seed_url, email, username_hint, phone,
         threshold, output_format, platforms, config_path, verbose):
    """Find connections and relationships across platforms."""
    _run_async(
        _link_async, name=name, location=location, seed_url=seed_url,
        email=email, username_hint=username_hint, phone=phone, threshold=threshold,
        output_format=output_format, platforms=platforms, config_path=config_path, verbose=verbose,
    )


async def _link_async(*, name, location, seed_url, email, username_hint, phone,
                       threshold, output_format, platforms, config_path, verbose):
    import aiohttp
    from argus.agents.linker import LinkerAgent
    from argus.agents.resolver import ResolverAgent
    from argus.models.agent import AgentInput

    config = _load_config(config_path)
    if threshold is not None:
        config.verification.minimum_threshold = threshold
    registry = _setup_registry(platforms)
    target = _build_target(name, location, list(seed_url), email, username_hint, phone)

    console.print(f"[bold]Linking:[/bold] {name}")
    start = time.monotonic()
    async with aiohttp.ClientSession() as session:
        resolver = ResolverAgent(session=session, config=config, registry=registry)
        resolve_out = await resolver.run(AgentInput(target=target))
        linker = LinkerAgent()
        link_out = await linker.run(AgentInput(
            target=target, options={"verified_accounts": resolve_out.accounts},
        ))
    elapsed = time.monotonic() - start

    if output_format == "json":
        console.print(link_out.model_dump_json(indent=2))
    else:
        console.print(f"\n[bold]Connections for {name}[/bold] ({elapsed:.1f}s)")
        if hasattr(link_out, "connections") and link_out.connections:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Platform")
            table.add_column("Relationship")
            table.add_column("Snippet")
            table.add_column("Confidence", justify="right")
            for c in link_out.connections:
                table.add_row(c.platform, c.relationship_type, c.content_snippet[:60], f"{c.confidence:.0%}")
            console.print(table)
        else:
            console.print("[yellow]No connections found.[/yellow]")


# ─── profile ─────────────────────────────────────────────────────────────

@main.command()
@click.argument("name")
@click.option("--location", default=None)
@click.option("--seed-url", multiple=True)
@click.option("--email", default=None)
@click.option("--username-hint", default=None)
@click.option("--phone", default=None)
@click.option("--threshold", type=float, default=None)
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--platforms", default=None)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.option("--verbose", is_flag=True)
def profile(name, location, seed_url, email, username_hint, phone,
            threshold, output_format, platforms, config_path, verbose):
    """Build a behavioral profile from scraped content."""
    _run_async(
        _profile_async, name=name, location=location, seed_url=seed_url,
        email=email, username_hint=username_hint, phone=phone, threshold=threshold,
        output_format=output_format, platforms=platforms, config_path=config_path, verbose=verbose,
    )


async def _profile_async(*, name, location, seed_url, email, username_hint, phone,
                           threshold, output_format, platforms, config_path, verbose):
    import aiohttp
    from argus.agents.profiler import ProfilerAgent
    from argus.agents.resolver import ResolverAgent
    from argus.models.agent import AgentInput

    config = _load_config(config_path)
    registry = _setup_registry(platforms)
    target = _build_target(name, location, list(seed_url), email, username_hint, phone)

    console.print(f"[bold]Profiling:[/bold] {name}")
    start = time.monotonic()
    async with aiohttp.ClientSession() as session:
        resolver = ResolverAgent(session=session, config=config, registry=registry)
        resolve_out = await resolver.run(AgentInput(target=target))
        profiler = ProfilerAgent()
        prof_out = await profiler.run(AgentInput(
            target=target, options={"verified_accounts": resolve_out.accounts, "content_items": []},
        ))
    elapsed = time.monotonic() - start

    if output_format == "json":
        console.print(prof_out.model_dump_json(indent=2))
    else:
        console.print(f"\n[bold]Profile for {name}[/bold] ({elapsed:.1f}s)")
        if hasattr(prof_out, "dimensions"):
            for dim_name, scores in prof_out.dimensions.items():
                if scores:
                    console.print(f"\n[bold]{dim_name.title()}:[/bold]")
                    for s in scores[:5]:
                        console.print(f"  {s.topic}: {s.score:.0%}")


# ─── investigate ─────────────────────────────────────────────────────────

@main.command()
@click.argument("name")
@click.option("--location", default=None)
@click.option("--seed-url", multiple=True)
@click.option("--email", default=None)
@click.option("--username-hint", default=None)
@click.option("--phone", default=None)
@click.option("--threshold", type=float, default=None)
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--platforms", default=None)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.option("--verbose", is_flag=True)
@click.option("--report-format", type=click.Choice(["json", "markdown", "html", "csv"]), default="json")
@click.option("--report-file", type=click.Path(), default=None, help="Save report to file.")
def investigate(name, report_format, report_file, **kwargs):
    """Run full investigation: resolve + link + profile + report."""
    _run_async(
        _investigate_async, name=name, report_format=report_format, report_file=report_file, **kwargs,
    )


async def _investigate_async(*, name, report_format, report_file, location, seed_url,
                               email, username_hint, phone, threshold, output_format,
                               platforms, config_path, verbose):
    import aiohttp
    from argus.agents.linker import LinkerAgent
    from argus.agents.profiler import ProfilerAgent
    from argus.agents.resolver import ResolverAgent
    from argus.models.agent import AgentInput
    from argus.models.investigation import Investigation
    from argus.models.target import Target
    from argus.reporting import ReportGenerator

    config = _load_config(config_path)
    if threshold is not None:
        config.verification.minimum_threshold = threshold
    registry = _setup_registry(platforms)
    target = _build_target(name, location, list(seed_url), email, username_hint, phone)

    console.print(f"[bold]Investigating:[/bold] {name}")
    start = time.monotonic()

    async with aiohttp.ClientSession() as session:
        console.print("[dim]Step 1/3: Resolving...[/dim]")
        resolver = ResolverAgent(session=session, config=config, registry=registry)
        resolve_out = await resolver.run(AgentInput(target=target))

        console.print("[dim]Step 2/3: Linking...[/dim]")
        linker = LinkerAgent()
        link_out = await linker.run(AgentInput(
            target=target, options={"verified_accounts": resolve_out.accounts},
        ))

        console.print("[dim]Step 3/3: Profiling...[/dim]")
        profiler = ProfilerAgent()
        prof_out = await profiler.run(AgentInput(
            target=target, options={"verified_accounts": resolve_out.accounts, "content_items": []},
        ))

    elapsed = time.monotonic() - start

    target_obj = Target(name=target.name, location=target.location, seed_urls=target.seed_urls,
                        email=target.email, username_hint=target.username_hint, phone=target.phone)
    investigation = Investigation(
        target=target_obj, status="completed",
        resolver_output=resolve_out, linker_output=link_out, profiler_output=prof_out,
    )

    gen = ReportGenerator()
    report = gen.generate(investigation, report_format)
    if report_file:
        with open(report_file, "w") as f:
            f.write(report)
        console.print(f"[green]Report saved to {report_file}[/green]")
    else:
        console.print(report)
    console.print(f"\n[bold]Investigation complete[/bold] ({elapsed:.1f}s)")


# ─── report ──────────────────────────────────────────────────────────────

@main.command()
@click.argument("investigation_id")
@click.option("--format", "fmt", type=click.Choice(["json", "markdown", "html", "csv"]), default="json")
@click.option("--output-file", type=click.Path(), default=None)
def report(investigation_id, fmt, output_file):
    """Generate a report from a stored investigation."""
    _run_async(_report_async, investigation_id=investigation_id, fmt=fmt, output_file=output_file)


async def _report_async(*, investigation_id, fmt, output_file):
    from argus.reporting import ReportGenerator
    from argus.storage.database import Database
    from argus.storage.repository import InvestigationRepository

    db = Database()
    await db.initialize()
    repo = InvestigationRepository(db)
    inv = await repo.get_investigation(investigation_id)
    await db.close()
    if inv is None:
        console.print(f"[red]Investigation {investigation_id} not found.[/red]")
        return
    gen = ReportGenerator()
    output = gen.generate(inv, fmt)
    if output_file:
        with open(output_file, "w") as f:
            f.write(output)
        console.print(f"[green]Report saved to {output_file}[/green]")
    else:
        console.print(output)


# ─── platforms ───────────────────────────────────────────────────────────

@main.command("platforms")
def list_platforms():
    """List all available platforms."""
    from argus.platforms.registry import PlatformRegistry

    registry = PlatformRegistry()
    discovered = registry.discover_platforms()
    if not discovered:
        console.print("[yellow]No platforms discovered.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Priority", justify="right")
    table.add_column("Rate Limit", justify="right")
    table.add_column("Auth")
    table.add_column("Playwright")
    for name, cls in sorted(discovered.items(), key=lambda x: x[1].priority, reverse=True):
        table.add_row(name, str(cls.priority), f"{cls.rate_limit_per_minute}/min",
                      "Yes" if cls.requires_auth else "No",
                      "Yes" if cls.requires_playwright else "No")
    console.print(table)
    console.print(f"\n[dim]{len(discovered)} platform(s) available[/dim]")


# ─── Display helpers ─────────────────────────────────────────────────────

def _display_resolve_table(output, target_name: str, platform_count: int, elapsed: float) -> None:
    from argus.models.agent import ResolverOutput
    assert isinstance(output, ResolverOutput)
    accounts = output.accounts
    console.print()
    console.print(f"[bold]Results for {target_name}[/bold] — {platform_count} platforms in {elapsed:.1f}s")
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
        color = "green" if conf >= 0.70 else ("yellow" if conf >= 0.30 else "red")
        table.add_row(vr.candidate.platform, vr.candidate.username, vr.candidate.url,
                      f"[{color}]{conf:.0%}[/{color}]", vr.threshold_label)
    console.print(table)
    console.print(f"\n[bold]Found {len(accounts)} account(s)[/bold]")

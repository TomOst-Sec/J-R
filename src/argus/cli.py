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
@click.option("--no-browser", is_flag=True, help="Skip browser automation (HTTP-only mode).")
@click.option("--headful", is_flag=True, help="Run browser in visible mode for debugging.")
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
    no_browser: bool,
    headful: bool,
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
            no_browser=no_browser,
            headful=headful,
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
    no_browser: bool = False,
    headful: bool = False,
) -> None:
    from contextlib import asynccontextmanager

    from argus.agents.resolver import ResolverAgent
    from argus.config import load_config
    from argus.config.settings import ArgusConfig
    from argus.models.agent import AgentInput
    from argus.models.target import TargetInput
    from argus.platforms.registry import PlatformRegistry
    from argus.stealth.session import create_stealth_session
    from argus.storage.database import Database

    # Load config
    if config_path:
        config = load_config(config_path)
    else:
        config = ArgusConfig()

    if threshold is not None:
        config.verification.minimum_threshold = threshold
    if headful:
        config.stealth.headless = False
    if no_browser:
        config.stealth.browser_engine = "none"

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

    # Check if any enabled platform needs a browser
    enabled_platforms = registry.get_enabled_platforms(config)
    needs_browser = (
        config.stealth.browser_engine != "none"
        and any(cls.requires_playwright for cls in enabled_platforms)
    )

    # Async context helper for optional browser manager
    @asynccontextmanager
    async def _optional_browser():
        if needs_browser:
            try:
                from argus.stealth.browser_manager import BrowserManager
                async with BrowserManager(config) as mgr:
                    yield mgr
            except ImportError:
                if not is_json:
                    console.print(
                        "[yellow]camoufox not installed — browser platforms will use HTTP fallback[/yellow]"
                    )
                yield None
            except Exception as exc:
                if not is_json:
                    console.print(
                        f"[yellow]Browser launch failed ({exc}) — using HTTP fallback[/yellow]"
                    )
                yield None
        else:
            yield None

    # Run resolver with progress display
    db = Database()
    await db.initialize()

    session = create_stealth_session(config)
    async with session, _optional_browser() as browser_mgr:
        agent = ResolverAgent(
            session=session,
            config=config,
            registry=registry,
            db=db,
            browser=browser_mgr,
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


# ---------------------------------------------------------------------------
# argus intel
# ---------------------------------------------------------------------------


@main.group("intel")
def intel_cmd() -> None:
    """Intelligence gathering commands."""


@intel_cmd.command("email")
@click.argument("email")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to argus.toml.")
def intel_email(email: str, output_format: str, config_path: str | None) -> None:
    """Investigate an email address."""
    try:
        asyncio.run(_intel_email_async(email, output_format, config_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _intel_email_async(email: str, output_format: str, config_path: str | None) -> None:
    from argus.config import load_config
    from argus.config.settings import ArgusConfig
    from argus.intel.email import EmailIntelModule
    from argus.stealth.session import create_stealth_session

    config = load_config(config_path) if config_path else ArgusConfig()
    session = create_stealth_session(config)

    async with session:
        module = EmailIntelModule(session, config)
        report = await module.investigate(email)

    if output_format == "json":
        console.print(report.model_dump_json(indent=2))
    else:
        console.print(f"\n[bold]Email Report:[/bold] {email}\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Deliverable", str(report.is_deliverable))
        table.add_row("Gravatar", report.gravatar_url or "Not found")
        table.add_row("MX Records", ", ".join(report.mx_records) if report.mx_records else "None")
        table.add_row("PGP Keys", str(len(report.pgp_keys)))
        table.add_row("Breaches", str(len(report.breaches)))
        console.print(table)

        if report.breaches:
            console.print("\n[bold]Breaches:[/bold]")
            breach_table = Table(show_header=True, header_style="bold")
            breach_table.add_column("Name")
            breach_table.add_column("Domain")
            breach_table.add_column("Data Types")
            breach_table.add_column("Verified")
            for b in report.breaches:
                breach_table.add_row(
                    b.breach_name,
                    b.domain or "",
                    ", ".join(b.data_types[:5]),
                    "[green]yes[/green]" if b.is_verified else "[red]no[/red]",
                )
            console.print(breach_table)


@intel_cmd.command("phone")
@click.argument("phone_number")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
def intel_phone(phone_number: str, output_format: str) -> None:
    """Investigate a phone number."""
    try:
        asyncio.run(_intel_phone_async(phone_number, output_format))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _intel_phone_async(phone_number: str, output_format: str) -> None:
    import json as json_mod

    from argus.config.settings import ArgusConfig
    from argus.intel.phone import PhoneIntelModule
    from argus.stealth.session import create_stealth_session

    config = ArgusConfig()
    session = create_stealth_session(config)

    async with session:
        module = PhoneIntelModule(session, config)
        metadata, intel_results = await module.investigate(phone_number)

    if output_format == "json":
        console.print(metadata.model_dump_json(indent=2))
    else:
        console.print(f"\n[bold]Phone Report:[/bold] {phone_number}\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Formatted", metadata.number)
        table.add_row("Valid", "[green]yes[/green]" if metadata.is_valid else "[red]no[/red]")
        table.add_row("Country", metadata.country or "Unknown")
        table.add_row("Country Code", metadata.country_code or "Unknown")
        table.add_row("Carrier", metadata.carrier or "Unknown")
        table.add_row("Line Type", metadata.line_type or "Unknown")
        table.add_row("Region", metadata.region or "Unknown")
        console.print(table)


@intel_cmd.command("domain")
@click.argument("domain")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to argus.toml.")
def intel_domain(domain: str, output_format: str, config_path: str | None) -> None:
    """Investigate a domain."""
    try:
        asyncio.run(_intel_domain_async(domain, output_format, config_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _intel_domain_async(domain: str, output_format: str, config_path: str | None) -> None:
    from argus.config import load_config
    from argus.config.settings import ArgusConfig
    from argus.intel.domain import DomainIntelModule
    from argus.stealth.session import create_stealth_session

    config = load_config(config_path) if config_path else ArgusConfig()
    session = create_stealth_session(config)

    async with session:
        module = DomainIntelModule(session, config)
        report = await module.investigate(domain)

    if output_format == "json":
        console.print(report.model_dump_json(indent=2))
    else:
        console.print(f"\n[bold]Domain Report:[/bold] {domain}\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")

        if report.whois:
            table.add_row("Registrar", report.whois.registrar or "Unknown")
            table.add_row("Registrant", report.whois.registrant or "Unknown")
            table.add_row("Created", str(report.whois.creation_date or "Unknown"))
            table.add_row("Expires", str(report.whois.expiry_date or "Unknown"))
            table.add_row("Nameservers", ", ".join(report.whois.nameservers) if report.whois.nameservers else "None")

        if report.dns:
            table.add_row("A Records", ", ".join(report.dns.a) if report.dns.a else "None")
            table.add_row("MX Records", ", ".join(str(mx) for mx in report.dns.mx) if report.dns.mx else "None")
            table.add_row("NS Records", ", ".join(report.dns.ns) if report.dns.ns else "None")

        table.add_row("Subdomains", str(len(report.subdomains)))
        table.add_row("Certificates", str(len(report.certificates)))
        table.add_row("Wayback Snapshots", str(report.wayback_snapshots or 0))
        console.print(table)


@intel_cmd.command("breach")
@click.argument("email")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to argus.toml.")
def intel_breach(email: str, output_format: str, config_path: str | None) -> None:
    """Check an email against breach databases."""
    try:
        asyncio.run(_intel_breach_async(email, output_format, config_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _intel_breach_async(email: str, output_format: str, config_path: str | None) -> None:
    from argus.config import load_config
    from argus.config.settings import ArgusConfig
    from argus.intel.email import EmailIntelModule
    from argus.stealth.session import create_stealth_session

    config = load_config(config_path) if config_path else ArgusConfig()
    session = create_stealth_session(config)

    async with session:
        module = EmailIntelModule(session, config)
        report = await module.investigate(email)

    if output_format == "json":
        import json as json_mod

        breach_data = [b.model_dump(mode="json") for b in report.breaches]
        console.print(json_mod.dumps({"email": email, "breaches": breach_data}, indent=2))
    else:
        console.print(f"\n[bold]Breach Check:[/bold] {email}\n")
        if not report.breaches:
            console.print("[green]No breaches found.[/green]")
            return
        console.print(f"[red]Found in {len(report.breaches)} breach(es):[/red]\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Breach")
        table.add_column("Domain")
        table.add_column("Data Types")
        table.add_column("Verified")
        for b in report.breaches:
            table.add_row(
                b.breach_name,
                b.domain or "",
                ", ".join(b.data_types[:5]),
                "[green]yes[/green]" if b.is_verified else "[red]no[/red]",
            )
        console.print(table)


@intel_cmd.command("image")
@click.argument("url")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
def intel_image(url: str, output_format: str) -> None:
    """Analyze an image URL."""
    try:
        asyncio.run(_intel_image_async(url, output_format))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _intel_image_async(url: str, output_format: str) -> None:
    import json as json_mod

    from argus.config.settings import ArgusConfig
    from argus.intel.image import ImageIntelModule
    from argus.stealth.session import create_stealth_session

    config = ArgusConfig()
    session = create_stealth_session(config)

    async with session:
        module = ImageIntelModule(session, config)
        result = await module.investigate(url)

    if output_format == "json":
        console.print(json_mod.dumps(result, indent=2, default=str))
    else:
        console.print(f"\n[bold]Image Analysis:[/bold] {url}\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Perceptual Hash", result.get("perceptual_hash") or "N/A")
        table.add_row("EXIF Fields", str(len(result.get("exif", {}))))
        if result.get("error"):
            table.add_row("Error", f"[red]{result['error']}[/red]")
        console.print(table)

        exif = result.get("exif", {})
        if exif:
            console.print("\n[bold]EXIF Data:[/bold]")
            exif_table = Table(show_header=True, header_style="bold")
            exif_table.add_column("Tag")
            exif_table.add_column("Value")
            for tag, val in list(exif.items())[:20]:
                exif_table.add_row(str(tag), str(val)[:100])
            console.print(exif_table)


# ---------------------------------------------------------------------------
# argus correlate
# ---------------------------------------------------------------------------


@main.command("correlate")
@click.argument("name")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to argus.toml.")
def correlate_cmd(name: str, output_format: str, config_path: str | None) -> None:
    """Full correlation across all sources for a person."""
    try:
        asyncio.run(_correlate_async(name, output_format, config_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _correlate_async(name: str, output_format: str, config_path: str | None) -> None:
    import json as json_mod

    from argus.config import load_config
    from argus.config.settings import ArgusConfig
    from argus.intel.correlator import CorrelationEngine

    config = load_config(config_path) if config_path else ArgusConfig()

    # Read piped input if available
    accounts: list[dict] = []
    intel_results = []
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()
        if stdin_data.strip():
            piped = json_mod.loads(stdin_data)
            accounts = piped.get("accounts", [])

    console.print(f"[bold]Correlating:[/bold] {name}")

    engine = CorrelationEngine()
    cluster = await engine.correlate(name, accounts, intel_results)

    if output_format == "json":
        console.print(cluster.model_dump_json(indent=2))
    else:
        console.print(f"\n[bold]Identity Cluster:[/bold] {cluster.cluster_id}\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Names", ", ".join(cluster.names))
        table.add_row("Usernames", ", ".join(cluster.usernames) if cluster.usernames else "None")
        table.add_row("Emails", ", ".join(cluster.emails) if cluster.emails else "None")
        table.add_row("Accounts", str(len(cluster.accounts)))
        table.add_row("Confidence", f"{cluster.confidence:.0%}")
        console.print(table)

        if cluster.evidence:
            console.print("\n[bold]Evidence:[/bold]")
            for ev in cluster.evidence:
                console.print(f"  - {ev}")

        if cluster.timeline:
            console.print("\n[bold]Timeline:[/bold]")
            timeline_table = Table(show_header=True, header_style="bold")
            timeline_table.add_column("Timestamp")
            timeline_table.add_column("Source")
            timeline_table.add_column("Event")
            for entry in cluster.timeline[:20]:
                timeline_table.add_row(
                    entry.get("timestamp", ""),
                    entry.get("source", ""),
                    entry.get("event", ""),
                )
            console.print(timeline_table)


# ---------------------------------------------------------------------------
# argus shell
# ---------------------------------------------------------------------------


@main.command("shell")
def shell_cmd() -> None:
    """Start interactive Argus REPL shell."""
    from argus.shell import run_shell

    run_shell()

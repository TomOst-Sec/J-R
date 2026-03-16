"""Interactive REPL shell for Argus OSINT."""

from __future__ import annotations

import asyncio
import cmd
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


class ArgusShell(cmd.Cmd):
    """Interactive Argus OSINT REPL."""

    intro = (
        "[bold]Argus OSINT Shell[/bold]\n"
        "Type 'help' for available commands, 'quit' to exit.\n"
    )
    prompt = "argus> "

    def __init__(self) -> None:
        super().__init__()
        self._current_name: str | None = None
        self._current_results: Any = None
        self._current_investigation_id: str | None = None
        # Print intro with Rich
        console.print(self.intro)
        self.intro = ""  # Don't let cmd.Cmd print it again

    def do_resolve(self, line: str) -> None:
        """Resolve a person: resolve John Doe --location NYC"""
        if not line.strip():
            console.print("[red]Usage: resolve <name> [--location <loc>][/red]")
            return
        parts = line.split("--location")
        name = parts[0].strip()
        location = parts[1].strip() if len(parts) > 1 else None
        self._current_name = name
        console.print(f"[bold]Resolving:[/bold] {name}")
        try:
            result = asyncio.run(self._run_resolve(name, location))
            self._current_results = result
            console.print(f"[green]Found {len(result.accounts)} account(s)[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    async def _run_resolve(self, name: str, location: str | None) -> Any:
        import aiohttp

        from argus.agents.resolver import ResolverAgent
        from argus.config.settings import ArgusConfig
        from argus.models.agent import AgentInput
        from argus.models.target import TargetInput
        from argus.platforms.registry import PlatformRegistry
        from argus.storage.database import Database

        config = ArgusConfig()
        registry = PlatformRegistry()
        registry.discover_platforms()

        target = TargetInput(name=name, location=location)
        db = Database()
        await db.initialize()

        async with aiohttp.ClientSession() as session:
            agent = ResolverAgent(session=session, config=config, registry=registry, db=db)
            output = await agent.execute(AgentInput(target=target))

        await db.close()
        return output

    def do_accounts(self, line: str) -> None:
        """Show discovered accounts from last resolve."""
        if not self._current_results:
            console.print("[yellow]No results. Run 'resolve <name>' first.[/yellow]")
            return
        table = Table(show_header=True, header_style="bold")
        table.add_column("Platform")
        table.add_column("Username")
        table.add_column("Confidence", justify="right")
        table.add_column("Label")
        for vr in self._current_results.accounts:
            conf = vr.confidence
            color = "green" if conf >= 0.7 else ("yellow" if conf >= 0.3 else "red")
            table.add_row(
                vr.candidate.platform,
                vr.candidate.username,
                f"[{color}]{conf:.0%}[/{color}]",
                vr.threshold_label,
            )
        console.print(table)

    def do_results(self, line: str) -> None:
        """Show current investigation results as JSON."""
        if not self._current_results:
            console.print("[yellow]No results. Run 'resolve <name>' first.[/yellow]")
            return
        console.print(self._current_results.model_dump_json(indent=2))

    def do_export(self, line: str) -> None:
        """Export results: export json|markdown|html|csv"""
        if not self._current_results:
            console.print("[yellow]No results to export.[/yellow]")
            return
        fmt = line.strip() or "json"
        console.print(f"[dim]Exporting as {fmt}...[/dim]")
        console.print(self._current_results.model_dump_json(indent=2))

    def do_platforms(self, line: str) -> None:
        """List supported platforms."""
        from argus.platforms.registry import PlatformRegistry

        registry = PlatformRegistry()
        registry.discover_platforms()
        names = registry.list_platforms()
        if names:
            for name in sorted(names):
                console.print(f"  - {name}")
        else:
            console.print("[yellow]No platforms discovered.[/yellow]")

    def do_help(self, line: str) -> None:
        """Show available commands."""
        commands = [
            ("resolve <name>", "Resolve a person across platforms"),
            ("accounts", "Show discovered accounts"),
            ("results", "Show current results as JSON"),
            ("export <format>", "Export results (json, markdown, html, csv)"),
            ("platforms", "List supported platforms"),
            ("help", "Show this help"),
            ("quit / exit", "Exit the shell"),
        ]
        table = Table(show_header=True, header_style="bold")
        table.add_column("Command")
        table.add_column("Description")
        for cmd_name, desc in commands:
            table.add_row(cmd_name, desc)
        console.print(table)

    def do_quit(self, line: str) -> bool:
        """Exit the shell."""
        console.print("[dim]Goodbye.[/dim]")
        return True

    def do_exit(self, line: str) -> bool:
        """Exit the shell."""
        return self.do_quit(line)

    def default(self, line: str) -> None:
        console.print(f"[red]Unknown command: {line}. Type 'help' for available commands.[/red]")

    def completenames(self, text: str, *ignored: Any) -> list[str]:
        commands = [
            "resolve", "accounts", "results", "export",
            "platforms", "help", "quit", "exit",
        ]
        return [c for c in commands if c.startswith(text)]


def run_shell() -> None:
    """Start the interactive Argus shell."""
    shell = ArgusShell()
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")

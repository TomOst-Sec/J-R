"""Tests for the Argus CLI."""

from click.testing import CliRunner

from argus.cli import main


class TestCLI:
    def test_main_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Argus OSINT platform" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_resolve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "--location" in result.output
        assert "--seed-url" in result.output
        assert "--email" in result.output
        assert "--username-hint" in result.output
        assert "--phone" in result.output
        assert "--threshold" in result.output
        assert "--output" in result.output
        assert "--platforms" in result.output
        assert "--config" in result.output
        assert "--verbose" in result.output

    def test_resolve_runs(self):
        runner = CliRunner()
        # Run with no platforms discovered — should complete quickly
        result = runner.invoke(main, ["resolve", "John Doe", "--output", "json"])
        assert result.exit_code == 0
        assert "resolver" in result.output  # JSON output contains agent_name

    def test_resolve_table_output(self):
        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "Test User"])
        assert result.exit_code == 0
        assert "Resolving:" in result.output

    def test_resolve_with_options(self):
        runner = CliRunner()
        result = runner.invoke(main, [
            "resolve", "Jane Doe",
            "--location", "NYC",
            "--email", "jane@example.com",
            "--username-hint", "janedoe",
            "--threshold", "0.5",
            "--output", "json",
        ])
        assert result.exit_code == 0

    def test_resolve_json_valid(self):
        import json as json_module

        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "Test", "--output", "json"])
        assert result.exit_code == 0
        # Find JSON in output (after the status lines)
        lines = result.output.strip().split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)
        if json_lines:
            json_str = "\n".join(json_lines)
            data = json_module.loads(json_str)
            assert data["agent_name"] == "resolver"

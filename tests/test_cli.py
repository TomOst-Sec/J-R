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


class TestPlatformsCLI:
    def test_platforms_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["platforms", "--help"])
        assert result.exit_code == 0

    def test_platforms_runs(self):
        runner = CliRunner()
        result = runner.invoke(main, ["platforms"])
        assert result.exit_code == 0


class TestConfigCLI:
    def test_config_show(self):
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "general" in result.output

    def test_config_path(self):
        runner = CliRunner()
        result = runner.invoke(main, ["config", "path"])
        assert result.exit_code == 0
        assert "argus.toml" in result.output

    def test_config_init(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["config", "init"])
        assert result.exit_code == 0
        assert (tmp_path / "argus.toml").exists()


class TestLinkCLI:
    def test_link_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["link", "--help"])
        assert result.exit_code == 0
        assert "--topic" in result.output

    def test_link_runs(self):
        runner = CliRunner()
        result = runner.invoke(
            main, ["link", "John Doe", "--topic", "machine learning"]
        )
        assert result.exit_code == 0

    def test_link_json_output(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["link", "John Doe", "--topic", "AI", "--output", "json"],
        )
        assert result.exit_code == 0
        assert "linker" in result.output


class TestProfileCLI:
    def test_profile_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["profile", "--help"])
        assert result.exit_code == 0

    def test_profile_runs(self):
        runner = CliRunner()
        result = runner.invoke(main, ["profile", "John Doe"])
        assert result.exit_code == 0

    def test_profile_json_output(self):
        runner = CliRunner()
        result = runner.invoke(
            main, ["profile", "John Doe", "--output", "json"]
        )
        assert result.exit_code == 0
        assert "profiler" in result.output


class TestReportCLI:
    def test_report_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["report", "--help"])
        assert result.exit_code == 0

    def test_report_json(self):
        runner = CliRunner()
        result = runner.invoke(main, ["report", "John Doe", "--format", "json"])
        assert result.exit_code == 0
        assert "John Doe" in result.output

    def test_report_markdown(self):
        runner = CliRunner()
        result = runner.invoke(
            main, ["report", "John Doe", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "# Investigation Report" in result.output

    def test_report_to_file(self, tmp_path):
        runner = CliRunner()
        output_file = str(tmp_path / "report.json")
        result = runner.invoke(
            main, ["report", "John Doe", "--format", "json", "--output", output_file]
        )
        assert result.exit_code == 0
        from pathlib import Path

        assert Path(output_file).exists()


class TestHelpListsAllCommands:
    def test_all_commands_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        for cmd in ["resolve", "link", "profile", "report", "platforms", "config"]:
            assert cmd in result.output

"""Tests for the full Argus CLI."""

from click.testing import CliRunner

from argus.cli import main


class TestMainGroup:
    def test_help(self):
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Argus OSINT platform" in result.output

    def test_version(self):
        result = CliRunner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_commands_listed(self):
        result = CliRunner().invoke(main, ["--help"])
        assert "resolve" in result.output
        assert "link" in result.output
        assert "profile" in result.output
        assert "investigate" in result.output
        assert "report" in result.output
        assert "platforms" in result.output


class TestResolve:
    def test_help(self):
        result = CliRunner().invoke(main, ["resolve", "--help"])
        assert result.exit_code == 0
        assert "--location" in result.output
        assert "--threshold" in result.output

    def test_json_output(self):
        result = CliRunner().invoke(main, ["resolve", "Test User", "--output", "json"])
        assert result.exit_code == 0
        assert "resolver" in result.output

    def test_table_output(self):
        result = CliRunner().invoke(main, ["resolve", "Test"])
        assert result.exit_code == 0
        assert "Resolving:" in result.output


class TestLink:
    def test_help(self):
        result = CliRunner().invoke(main, ["link", "--help"])
        assert result.exit_code == 0

    def test_json_output(self):
        result = CliRunner().invoke(main, ["link", "Test User", "--output", "json"])
        assert result.exit_code == 0

    def test_table_output(self):
        result = CliRunner().invoke(main, ["link", "Test"])
        assert result.exit_code == 0
        assert "Linking:" in result.output


class TestProfile:
    def test_help(self):
        result = CliRunner().invoke(main, ["profile", "--help"])
        assert result.exit_code == 0

    def test_json_output(self):
        result = CliRunner().invoke(main, ["profile", "Test User", "--output", "json"])
        assert result.exit_code == 0
        assert "profiler" in result.output

    def test_table_output(self):
        result = CliRunner().invoke(main, ["profile", "Test"])
        assert result.exit_code == 0
        assert "Profiling:" in result.output


class TestInvestigate:
    def test_help(self):
        result = CliRunner().invoke(main, ["investigate", "--help"])
        assert result.exit_code == 0
        assert "--report-format" in result.output
        assert "--report-file" in result.output

    def test_json_output(self):
        result = CliRunner().invoke(main, ["investigate", "Test", "--output", "json"])
        assert result.exit_code == 0
        assert "Investigating:" in result.output


class TestReport:
    def test_help(self):
        result = CliRunner().invoke(main, ["report", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output

    def test_not_found(self):
        result = CliRunner().invoke(main, ["report", "nonexistent-id"])
        assert result.exit_code == 0
        assert "not found" in result.output


class TestPlatforms:
    def test_list(self):
        result = CliRunner().invoke(main, ["platforms"])
        assert result.exit_code == 0
        assert "platform" in result.output.lower()

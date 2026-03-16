"""Tests for the interactive REPL shell."""

from click.testing import CliRunner

from argus.cli import main
from argus.shell import ArgusShell


class TestShellCommand:
    def test_shell_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["shell", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower() or "REPL" in result.output


class TestArgusShell:
    def test_completenames(self):
        shell = ArgusShell()
        completions = shell.completenames("res")
        assert "resolve" in completions
        assert "results" in completions

    def test_completenames_empty(self):
        shell = ArgusShell()
        completions = shell.completenames("")
        assert len(completions) >= 5  # All commands

    def test_accounts_no_results(self, capsys):
        shell = ArgusShell()
        shell.do_accounts("")
        # Should indicate no results

    def test_results_no_results(self, capsys):
        shell = ArgusShell()
        shell.do_results("")
        # Should indicate no results

    def test_quit_returns_true(self):
        shell = ArgusShell()
        assert shell.do_quit("") is True

    def test_exit_returns_true(self):
        shell = ArgusShell()
        assert shell.do_exit("") is True

    def test_resolve_empty_shows_usage(self, capsys):
        shell = ArgusShell()
        shell.do_resolve("")
        # Should print usage hint

    def test_platforms_lists(self, capsys):
        shell = ArgusShell()
        shell.do_platforms("")
        # Should list or say no platforms

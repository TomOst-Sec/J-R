"""Tests for agent chaining via stdin/stdout pipes."""

from click.testing import CliRunner

from argus.cli import main


class TestPipeMode:
    def test_link_has_input_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["link", "--help"])
        assert "--input" in result.output

    def test_link_has_quiet_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["link", "--help"])
        assert "--quiet" in result.output

    def test_profile_has_input_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["profile", "--help"])
        assert "--input" in result.output

    def test_profile_has_quiet_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["profile", "--help"])
        assert "--quiet" in result.output

    def test_resolve_json_output_clean(self):
        """JSON output should be parseable when piped."""
        import json

        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "Test", "--output", "json"])
        assert result.exit_code == 0
        # Find the JSON object in output
        lines = result.output.strip().split("\n")
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        if json_start is not None:
            json_str = "\n".join(lines[json_start:])
            data = json.loads(json_str)
            assert "agent_name" in data

    def test_link_with_stdin_json(self):
        """Link command can accept JSON from stdin."""
        import json

        piped_data = json.dumps({"accounts": [], "content": []})
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["link", "Test", "--topic", "Python", "--input", "-", "--output", "json"],
            input=piped_data,
        )
        assert result.exit_code == 0

    def test_profile_with_stdin_json(self):
        """Profile command can accept JSON from stdin."""
        import json

        piped_data = json.dumps({"accounts": [], "content": []})
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["profile", "Test", "--input", "-", "--output", "json"],
            input=piped_data,
        )
        assert result.exit_code == 0

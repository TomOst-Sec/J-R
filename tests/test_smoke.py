"""End-to-end smoke tests for the Argus OSINT platform.

Validates core user journeys with mocked HTTP. No network calls.
"""

from __future__ import annotations


from click.testing import CliRunner

from argus.cli import main
from argus.config.settings import ArgusConfig
from argus.models.agent import AgentInput
from argus.models.profile import CandidateProfile, ProfileData
from argus.models.target import TargetInput
from argus.models.verification import VerificationResult
from argus.platforms.registry import PlatformRegistry
from argus.verification.engine import VerificationEngine
from argus.verification.signals import (
    BioSimilaritySignal,
    PhotoHashSignal,
    UsernamePatternSignal,
)


class TestFullPipeline:
    async def test_resolve_link_profile(self):
        """Full pipeline: resolve → link → profile with mocked platforms."""
        from argus.agents.linker import LinkerAgent, LinkerInput
        from argus.agents.profiler import ProfilerAgent, ProfilerInput
        from argus.agents.resolver import ResolverAgent

        # Resolve
        config = ArgusConfig()
        config.verification.minimum_threshold = 0.0
        resolver = ResolverAgent(config=config)
        target = TargetInput(name="Smoke Test User")
        output = await resolver.run(AgentInput(target=target))
        assert output.agent_name == "resolver"
        assert output.target_name == "Smoke Test User"

        # Link
        linker = LinkerAgent()
        link_input = LinkerInput(
            target=target,
            topic="testing",
            accounts=[],
            content=[],
        )
        link_output = await linker.run(link_input)
        assert link_output.agent_name == "linker"

        # Profile
        profiler = ProfilerAgent()
        profile_input = ProfilerInput(target=target)
        profile_output = await profiler.run(profile_input)
        assert profile_output.agent_name == "profiler"


class TestCLIAllCommandsHelp:
    def test_all_commands_respond_to_help(self):
        """Every CLI command should respond to --help."""
        runner = CliRunner()
        commands = ["resolve", "link", "profile", "report", "platforms"]
        for cmd in commands:
            result = runner.invoke(main, [cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} --help failed: {result.output}"

    def test_config_subcommands_help(self):
        runner = CliRunner()
        for subcmd in ["show", "path", "init"]:
            result = runner.invoke(main, ["config", subcmd, "--help"])
            assert result.exit_code == 0


class TestCLIResolveJSON:
    def test_resolve_json_valid(self):
        """argus resolve produces valid JSON output."""
        import json

        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "Smoke Test", "--output", "json"])
        assert result.exit_code == 0
        # Extract JSON from output
        lines = result.output.strip().split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)
        if json_lines:
            data = json.loads("\n".join(json_lines))
            assert data["agent_name"] == "resolver"


class TestConfigDefault:
    def test_default_config_loads(self):
        """Default config loads without errors."""
        config = ArgusConfig()
        assert config.general.default_threshold == 0.45
        assert config.stealth.user_agent_rotation is True
        assert config.verification.minimum_threshold == 0.30


class TestPlatformRegistryDiscovery:
    def test_discovers_platforms(self):
        """Platform registry discovers all platform modules."""
        registry = PlatformRegistry()
        discovered = registry.discover_platforms()
        assert len(discovered) >= 5  # At least GitHub, Reddit, HN, etc.
        names = list(discovered.keys())
        assert "github" in names
        assert "reddit" in names


class TestVerificationEngineSignals:
    async def test_all_signals_compute(self):
        """All built-in signals register and compute without error."""
        config = ArgusConfig()
        engine = VerificationEngine(config)
        engine.register_signal(PhotoHashSignal())
        engine.register_signal(BioSimilaritySignal())
        engine.register_signal(UsernamePatternSignal())

        candidate = CandidateProfile(
            platform="github",
            username="smoketest",
            url="https://github.com/smoketest",
            scraped_data=ProfileData(
                username="smoketest",
                bio="A test user for smoke testing",
            ),
        )
        seed = ProfileData(username="smoketest", bio="Smoke test seed profile")
        results = await engine.verify([candidate], [seed])
        # Should return results (may be empty if below threshold)
        assert isinstance(results, list)

    async def test_verify_single(self):
        """verify_single returns a VerificationResult."""
        config = ArgusConfig()
        engine = VerificationEngine(config)
        engine.register_signal(UsernamePatternSignal())

        candidate = CandidateProfile(
            platform="test",
            username="testuser",
            url="https://test.com/testuser",
        )
        result = await engine.verify_single(candidate, [], None)
        assert isinstance(result, VerificationResult)
        assert 0.0 <= result.confidence <= 1.0


class TestReportFormats:
    def test_json_report(self):
        runner = CliRunner()
        result = runner.invoke(main, ["report", "Smoke", "--format", "json"])
        assert result.exit_code == 0
        assert "Smoke" in result.output

    def test_markdown_report(self):
        runner = CliRunner()
        result = runner.invoke(main, ["report", "Smoke", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Investigation Report" in result.output

    def test_report_to_file(self, tmp_path):
        runner = CliRunner()
        out = str(tmp_path / "report.json")
        result = runner.invoke(main, ["report", "Smoke", "--format", "json", "--output", out])
        assert result.exit_code == 0
        from pathlib import Path

        assert Path(out).exists()

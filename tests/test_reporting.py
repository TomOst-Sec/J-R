"""Tests for report generation."""

import csv
import io
import json

from argus.models.agent import ResolverOutput
from argus.models.investigation import Investigation
from argus.models.profile import CandidateProfile, ProfileData
from argus.models.target import Target
from argus.models.verification import SignalResult, VerificationResult
from argus.reporting.generator import ReportGenerator


def _make_investigation() -> Investigation:
    target = Target(name="John Doe", location="New York")
    candidate = CandidateProfile(
        platform="github",
        username="johndoe",
        url="https://github.com/johndoe",
        exists=True,
        scraped_data=ProfileData(
            username="johndoe",
            display_name="John Doe",
            bio="Software engineer",
            location="NYC",
            profile_photo_url="https://example.com/photo.jpg",
        ),
    )
    signals = [
        SignalResult(signal_name="bio_similarity", score=0.8, weight=0.2, evidence="Bio match"),
        SignalResult(signal_name="username_pattern", score=0.6, weight=0.1, evidence="Username match"),
    ]
    vr = VerificationResult(
        candidate=candidate,
        signals=signals,
        confidence=0.75,
        threshold_label="likely",
    )
    resolver_output = ResolverOutput(
        target_name="John Doe",
        agent_name="resolver",
        accounts=[vr],
    )
    return Investigation(
        target=target,
        status="completed",
        resolver_output=resolver_output,
    )


class TestReportGenerator:
    def test_generate_json(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "json")
        data = json.loads(result)
        assert data["target"]["name"] == "John Doe"
        assert data["status"] == "completed"
        assert data["resolver_output"] is not None

    def test_generate_markdown(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "markdown")
        assert "# Investigation Report" in result
        assert "John Doe" in result
        assert "github" in result.lower()
        assert "johndoe" in result
        assert "Methodology" in result

    def test_generate_markdown_executive_summary(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "markdown")
        assert "Executive Summary" in result or "Summary" in result

    def test_generate_markdown_discovered_accounts(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "markdown")
        assert "Discovered Accounts" in result or "Accounts" in result
        assert "75%" in result or "0.75" in result

    def test_generate_html(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "html")
        assert "<html" in result
        assert "John Doe" in result
        assert "johndoe" in result
        # Should have embedded CSS
        assert "<style" in result

    def test_generate_html_confidence_colors(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "html")
        # 0.75 confidence should be green
        assert "green" in result or "#2" in result

    def test_generate_csv(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "csv")
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        # Header + at least 1 data row
        assert len(rows) >= 2
        header = rows[0]
        assert "platform" in header
        assert "username" in header
        assert "confidence" in header

    def test_generate_json_roundtrip(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        result = gen.generate(inv, "json")
        data = json.loads(result)
        # Should be valid Investigation JSON
        inv2 = Investigation.model_validate(data)
        assert inv2.target.name == "John Doe"

    def test_generate_markdown_no_accounts(self):
        target = Target(name="Nobody")
        resolver_output = ResolverOutput(
            target_name="Nobody", agent_name="resolver", accounts=[]
        )
        inv = Investigation(
            target=target, status="completed", resolver_output=resolver_output
        )
        gen = ReportGenerator()
        result = gen.generate(inv, "markdown")
        assert "No accounts" in result or "0 account" in result

    def test_generate_unsupported_format_raises(self):
        inv = _make_investigation()
        gen = ReportGenerator()
        try:
            gen.generate(inv, "xml")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

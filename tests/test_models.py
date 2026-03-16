"""Tests for core Pydantic data models."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from argus.models import (
    AgentInput,
    AgentOutput,
    CandidateProfile,
    Connection,
    ContentItem,
    Investigation,
    LinkerOutput,
    ProfileData,
    ProfilerOutput,
    ResolverOutput,
    SignalResult,
    Target,
    TargetInput,
    TopicScore,
    VerificationResult,
)


class TestTargetModels:
    def test_target_input_minimal(self) -> None:
        ti = TargetInput(name="John Doe")
        assert ti.name == "John Doe"
        assert ti.seed_urls == []
        assert ti.email is None

    def test_target_input_full(self) -> None:
        ti = TargetInput(
            name="Jane Smith",
            location="NYC",
            seed_urls=["https://example.com"],
            email="jane@example.com",
            username_hint="jsmith",
            phone="+1234567890",
        )
        assert ti.location == "NYC"

    def test_target_has_uuid(self) -> None:
        t = Target(name="Test")
        assert len(t.id) == 36  # UUID format

    def test_target_created_at(self) -> None:
        t = Target(name="Test")
        assert isinstance(t.created_at, datetime)

    def test_target_roundtrip_json(self) -> None:
        t = Target(name="Test", location="Berlin")
        data = json.loads(t.model_dump_json())
        t2 = Target(**data)
        assert t2.name == t.name
        assert t2.location == t.location


class TestProfileModels:
    def test_profile_data(self) -> None:
        pd = ProfileData(username="testuser", display_name="Test User", bio="Hello")
        assert pd.username == "testuser"
        assert pd.links == []

    def test_candidate_profile(self) -> None:
        cp = CandidateProfile(platform="github", username="user1", url="https://github.com/user1")
        assert cp.exists is None
        assert cp.scraped_data is None

    def test_candidate_with_scraped_data(self) -> None:
        pd = ProfileData(username="user1", display_name="User One")
        cp = CandidateProfile(
            platform="github",
            username="user1",
            url="https://github.com/user1",
            exists=True,
            scraped_data=pd,
        )
        assert cp.scraped_data is not None
        assert cp.scraped_data.display_name == "User One"

    def test_content_item(self) -> None:
        ci = ContentItem(id="1", platform="twitter", text="Hello world")
        assert ci.content_type == "post"
        assert ci.timestamp is None

    def test_profile_data_roundtrip(self) -> None:
        pd = ProfileData(
            username="u",
            display_name="U",
            follower_count=100,
            raw_json={"key": "val"},
        )
        data = json.loads(pd.model_dump_json())
        pd2 = ProfileData(**data)
        assert pd2.follower_count == 100
        assert pd2.raw_json == {"key": "val"}


class TestVerificationModels:
    def test_signal_result(self) -> None:
        sr = SignalResult(signal_name="photo", score=0.8, weight=0.35, evidence="match found")
        assert sr.score == 0.8

    def test_verification_result(self) -> None:
        cp = CandidateProfile(platform="github", username="u", url="https://github.com/u")
        sr = SignalResult(signal_name="bio", score=0.5, weight=0.2, evidence="similar")
        vr = VerificationResult(
            candidate=cp, signals=[sr], confidence=0.5, threshold_label="possible"
        )
        assert vr.threshold_label == "possible"
        assert len(vr.signals) == 1

    def test_verification_result_roundtrip(self) -> None:
        cp = CandidateProfile(platform="x", username="u", url="https://x.com/u")
        vr = VerificationResult(
            candidate=cp, signals=[], confidence=0.9, threshold_label="confirmed"
        )
        data = json.loads(vr.model_dump_json())
        vr2 = VerificationResult(**data)
        assert vr2.confidence == 0.9


class TestAgentModels:
    def test_agent_input(self) -> None:
        ti = TargetInput(name="Test")
        ai = AgentInput(target=ti)
        assert ai.config is None

    def test_agent_output(self) -> None:
        ao = AgentOutput(target_name="Test", agent_name="resolver")
        assert ao.results == []
        assert ao.duration_seconds is None

    def test_connection(self) -> None:
        c = Connection(
            platform="twitter",
            content_snippet="mentioned together",
            relationship_type="mention",
            confidence=0.7,
        )
        assert c.confidence == 0.7

    def test_topic_score(self) -> None:
        ts = TopicScore(topic="python", score=0.9, evidence=["repo1", "repo2"])
        assert len(ts.evidence) == 2

    def test_resolver_output(self) -> None:
        ro = ResolverOutput(target_name="Test", agent_name="resolver", accounts=[])
        assert isinstance(ro, AgentOutput)

    def test_linker_output(self) -> None:
        lo = LinkerOutput(target_name="Test", agent_name="linker", connections=[])
        assert isinstance(lo, AgentOutput)

    def test_profiler_output(self) -> None:
        ts = TopicScore(topic="python", score=0.8, evidence=["e1"])
        po = ProfilerOutput(
            target_name="Test", agent_name="profiler", dimensions={"tech": [ts]}
        )
        assert "tech" in po.dimensions

    def test_agent_output_roundtrip(self) -> None:
        ao = AgentOutput(
            target_name="T",
            agent_name="A",
            results=[1, "two", {"three": 3}],
            duration_seconds=1.5,
        )
        data = json.loads(ao.model_dump_json())
        ao2 = AgentOutput(**data)
        assert ao2.duration_seconds == 1.5


class TestInvestigationModel:
    def test_investigation_defaults(self) -> None:
        t = Target(name="Test")
        inv = Investigation(target=t)
        assert inv.status == "running"
        assert inv.resolver_output is None
        assert len(inv.id) == 36

    def test_investigation_roundtrip(self) -> None:
        t = Target(name="Test")
        inv = Investigation(target=t, status="completed")
        data = json.loads(inv.model_dump_json())
        inv2 = Investigation(**data)
        assert inv2.status == "completed"
        assert inv2.target.name == "Test"


class TestImports:
    """Verify all models are importable from argus.models."""

    def test_all_exports(self) -> None:
        from argus import models

        expected = [
            "AgentInput", "AgentOutput", "CandidateProfile", "Connection",
            "ContentItem", "Investigation", "LinkerOutput", "ProfileData",
            "ProfilerOutput", "ResolverOutput", "SignalResult", "Target",
            "TargetInput", "TopicScore", "VerificationResult",
        ]
        for name in expected:
            assert hasattr(models, name), f"Missing export: {name}"

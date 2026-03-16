"""Tests for core Pydantic data models."""

from datetime import datetime

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
    def test_target_input_minimal(self):
        t = TargetInput(name="John Doe")
        assert t.name == "John Doe"
        assert t.location is None
        assert t.seed_urls == []

    def test_target_input_full(self):
        t = TargetInput(
            name="John Doe",
            location="NYC",
            seed_urls=["https://example.com"],
            email="john@example.com",
            username_hint="johndoe",
            phone="+1234567890",
        )
        assert t.email == "john@example.com"

    def test_target_input_roundtrip(self):
        t = TargetInput(name="Jane", location="LA")
        data = t.model_dump_json()
        t2 = TargetInput.model_validate_json(data)
        assert t == t2

    def test_target_has_defaults(self):
        t = Target(name="Test")
        assert t.id  # uuid generated
        assert isinstance(t.created_at, datetime)

    def test_target_roundtrip(self):
        t = Target(name="Test", location="Berlin")
        data = t.model_dump_json()
        t2 = Target.model_validate_json(data)
        assert t2.name == "Test"
        assert t2.location == "Berlin"


class TestProfileModels:
    def test_profile_data_minimal(self):
        pd = ProfileData(username="jdoe")
        assert pd.username == "jdoe"
        assert pd.links == []

    def test_profile_data_full(self):
        pd = ProfileData(
            username="jdoe",
            display_name="John Doe",
            bio="Hello",
            location="NYC",
            profile_photo_url="https://example.com/photo.jpg",
            profile_photo_hash="abc123",
            links=["https://example.com"],
            join_date=datetime(2020, 1, 1),
            follower_count=100,
            following_count=50,
            raw_json={"key": "value"},
        )
        assert pd.follower_count == 100

    def test_profile_data_roundtrip(self):
        pd = ProfileData(username="test", bio="bio")
        data = pd.model_dump_json()
        pd2 = ProfileData.model_validate_json(data)
        assert pd == pd2

    def test_candidate_profile(self):
        cp = CandidateProfile(
            platform="twitter",
            username="jdoe",
            url="https://twitter.com/jdoe",
        )
        assert cp.exists is None
        assert cp.scraped_data is None

    def test_candidate_profile_with_data(self):
        pd = ProfileData(username="jdoe", display_name="John")
        cp = CandidateProfile(
            platform="twitter",
            username="jdoe",
            url="https://twitter.com/jdoe",
            exists=True,
            scraped_data=pd,
        )
        assert cp.scraped_data.display_name == "John"

    def test_candidate_profile_roundtrip(self):
        pd = ProfileData(username="jdoe")
        cp = CandidateProfile(
            platform="github", username="jdoe", url="https://github.com/jdoe", scraped_data=pd
        )
        data = cp.model_dump_json()
        cp2 = CandidateProfile.model_validate_json(data)
        assert cp2.scraped_data.username == "jdoe"

    def test_content_item(self):
        ci = ContentItem(id="1", platform="twitter", text="Hello world")
        assert ci.content_type == "post"
        assert ci.timestamp is None

    def test_content_item_roundtrip(self):
        ci = ContentItem(
            id="1",
            platform="twitter",
            text="Hello",
            timestamp=datetime(2024, 1, 1),
            engagement={"likes": 5},
        )
        data = ci.model_dump_json()
        ci2 = ContentItem.model_validate_json(data)
        assert ci2.engagement == {"likes": 5}


class TestVerificationModels:
    def test_signal_result(self):
        sr = SignalResult(
            signal_name="username_match", score=0.8, weight=1.0, evidence="exact match"
        )
        assert sr.score == 0.8

    def test_signal_result_roundtrip(self):
        sr = SignalResult(
            signal_name="test", score=0.5, weight=0.5, evidence="test", details={"k": "v"}
        )
        data = sr.model_dump_json()
        sr2 = SignalResult.model_validate_json(data)
        assert sr2.details == {"k": "v"}

    def test_verification_result(self):
        cp = CandidateProfile(
            platform="twitter", username="jdoe", url="https://twitter.com/jdoe"
        )
        vr = VerificationResult(
            candidate=cp, confidence=0.9, threshold_label="confirmed"
        )
        assert vr.signals == []
        assert vr.threshold_label == "confirmed"

    def test_verification_result_roundtrip(self):
        cp = CandidateProfile(
            platform="github", username="jdoe", url="https://github.com/jdoe"
        )
        sr = SignalResult(signal_name="bio", score=0.7, weight=1.0, evidence="match")
        vr = VerificationResult(
            candidate=cp, signals=[sr], confidence=0.7, threshold_label="likely"
        )
        data = vr.model_dump_json()
        vr2 = VerificationResult.model_validate_json(data)
        assert len(vr2.signals) == 1
        assert vr2.candidate.platform == "github"


class TestAgentModels:
    def test_agent_input(self):
        ti = TargetInput(name="Test")
        ai = AgentInput(target=ti)
        assert ai.config is None

    def test_agent_input_roundtrip(self):
        ti = TargetInput(name="Test", email="a@b.com")
        ai = AgentInput(target=ti, config={"key": "val"})
        data = ai.model_dump_json()
        ai2 = AgentInput.model_validate_json(data)
        assert ai2.target.email == "a@b.com"

    def test_agent_output(self):
        ao = AgentOutput(target_name="Test", agent_name="resolver")
        assert ao.results == []
        assert ao.duration_seconds is None

    def test_agent_output_roundtrip(self):
        ao = AgentOutput(
            target_name="T", agent_name="A", results=[1, "two"], duration_seconds=3.5
        )
        data = ao.model_dump_json()
        ao2 = AgentOutput.model_validate_json(data)
        assert ao2.duration_seconds == 3.5

    def test_connection(self):
        c = Connection(
            platform="twitter",
            content_snippet="mentioned @jdoe",
            relationship_type="mention",
            confidence=0.6,
        )
        assert c.url is None

    def test_connection_roundtrip(self):
        c = Connection(
            platform="twitter",
            content_snippet="test",
            relationship_type="follow",
            confidence=0.5,
            url="https://example.com",
            timestamp=datetime(2024, 6, 1),
        )
        data = c.model_dump_json()
        c2 = Connection.model_validate_json(data)
        assert c2.timestamp.year == 2024

    def test_topic_score(self):
        ts = TopicScore(topic="tech", score=0.9, evidence=["post about python"])
        assert ts.trend is None

    def test_topic_score_roundtrip(self):
        ts = TopicScore(topic="music", score=0.4, evidence=["a", "b"], trend="increasing")
        data = ts.model_dump_json()
        ts2 = TopicScore.model_validate_json(data)
        assert ts2.trend == "increasing"

    def test_resolver_output(self):
        ro = ResolverOutput(target_name="T", agent_name="resolver")
        assert ro.accounts == []
        assert ro.results == []

    def test_resolver_output_with_accounts(self):
        cp = CandidateProfile(
            platform="twitter", username="jdoe", url="https://twitter.com/jdoe"
        )
        vr = VerificationResult(
            candidate=cp, confidence=0.8, threshold_label="likely"
        )
        ro = ResolverOutput(target_name="T", agent_name="resolver", accounts=[vr])
        data = ro.model_dump_json()
        ro2 = ResolverOutput.model_validate_json(data)
        assert len(ro2.accounts) == 1

    def test_linker_output(self):
        c = Connection(
            platform="twitter", content_snippet="x", relationship_type="y", confidence=0.5
        )
        lo = LinkerOutput(target_name="T", agent_name="linker", connections=[c])
        data = lo.model_dump_json()
        lo2 = LinkerOutput.model_validate_json(data)
        assert len(lo2.connections) == 1

    def test_profiler_output(self):
        ts = TopicScore(topic="tech", score=0.9, evidence=["code"])
        po = ProfilerOutput(
            target_name="T", agent_name="profiler", dimensions={"interests": [ts]}
        )
        data = po.model_dump_json()
        po2 = ProfilerOutput.model_validate_json(data)
        assert len(po2.dimensions["interests"]) == 1


class TestInvestigationModel:
    def test_investigation_defaults(self):
        t = Target(name="Test")
        inv = Investigation(target=t)
        assert inv.id  # uuid
        assert inv.status == "running"
        assert inv.resolver_output is None

    def test_investigation_roundtrip(self):
        t = Target(name="Test", location="NYC")
        inv = Investigation(target=t, status="completed")
        data = inv.model_dump_json()
        inv2 = Investigation.model_validate_json(data)
        assert inv2.status == "completed"
        assert inv2.target.name == "Test"

    def test_investigation_with_outputs(self):
        t = Target(name="Test")
        ro = ResolverOutput(target_name="Test", agent_name="resolver")
        lo = LinkerOutput(target_name="Test", agent_name="linker")
        po = ProfilerOutput(target_name="Test", agent_name="profiler")
        inv = Investigation(
            target=t, resolver_output=ro, linker_output=lo, profiler_output=po
        )
        data = inv.model_dump_json()
        inv2 = Investigation.model_validate_json(data)
        assert inv2.resolver_output is not None
        assert inv2.linker_output is not None
        assert inv2.profiler_output is not None

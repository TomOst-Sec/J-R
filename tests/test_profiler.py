"""Tests for Profiler Agent — behavioral profile builder."""

from __future__ import annotations

from datetime import datetime, timezone

from argus.agents.classifiers import DimensionClassifier
from argus.agents.profiler import ProfilerAgent, ProfilerInput
from argus.models.agent import ProfilerOutput
from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.models.target import TargetInput
from argus.models.verification import VerificationResult


def _make_accounts() -> list[VerificationResult]:
    return [
        VerificationResult(
            candidate=CandidateProfile(
                platform="github",
                username="johndoe",
                url="https://github.com/johndoe",
                exists=True,
                scraped_data=ProfileData(
                    username="johndoe",
                    display_name="John Doe",
                    bio="Machine learning engineer. Building AI tools for developer productivity.",
                ),
            ),
            signals=[],
            confidence=0.85,
            threshold_label="confirmed",
        ),
    ]


def _make_content() -> list[ContentItem]:
    return [
        ContentItem(
            id="1",
            platform="github",
            text="ml-trainer — A machine learning training framework for NLP models",
            content_type="repo",
            timestamp=datetime(2025, 12, 1, 14, 0, tzinfo=timezone.utc),
            engagement={"stars": 50, "forks": 10},
        ),
        ContentItem(
            id="2",
            platform="github",
            text="react-app — Frontend dashboard for monitoring",
            content_type="repo",
            timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
            engagement={"stars": 5, "forks": 1},
        ),
        ContentItem(
            id="3",
            platform="reddit",
            text="Just published a new machine learning paper on transformer architectures. "
            "The engineering challenges in scaling these models are fascinating.",
            content_type="post",
            timestamp=datetime(2025, 12, 15, 15, 0, tzinfo=timezone.utc),
            engagement={"ups": 200, "num_comments": 30},
        ),
        ContentItem(
            id="4",
            platform="reddit",
            text="Hiking in Yosemite this weekend was incredible. Nature is the best medicine.",
            content_type="post",
            timestamp=datetime(2025, 12, 20, 18, 0, tzinfo=timezone.utc),
            engagement={"ups": 50, "num_comments": 5},
        ),
    ]


class TestProfilerAgent:
    async def test_extracts_topics(self):
        """Profiler extracts meaningful topics from content."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            content=_make_content(),
        )
        output = await agent.run(input_data)

        assert isinstance(output, ProfilerOutput)
        assert output.agent_name == "profiler"
        # Should have at least one dimension with topics
        total_topics = sum(len(v) for v in output.dimensions.values())
        assert total_topics > 0

    async def test_dimension_classification(self):
        """Topics are classified into professional/personal/public."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            content=_make_content(),
        )
        output = await agent.run(input_data)

        # Machine learning content should be classified as professional
        if "professional" in output.dimensions:
            prof_topics = [t.topic for t in output.dimensions["professional"]]
            assert len(prof_topics) > 0

    async def test_activity_scoring_produces_rankings(self):
        """Topics within a dimension are ranked by activity score."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            content=_make_content(),
        )
        output = await agent.run(input_data)

        for dim, topics in output.dimensions.items():
            scores = [t.score for t in topics]
            assert scores == sorted(scores, reverse=True)

    async def test_temporal_trend_detection(self):
        """Trend detection works for topics."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            content=_make_content(),
        )
        output = await agent.run(input_data)

        for dim, topics in output.dimensions.items():
            for topic in topics:
                assert topic.trend in ("rising", "declining", "stable")

    async def test_metadata_includes_stats(self):
        """Output metadata includes summary stats."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            content=_make_content(),
        )
        output = await agent.run(input_data)

        assert output.metadata is not None
        assert "top_platforms" in output.metadata
        assert "posting_frequency" in output.metadata
        assert "total_topics_extracted" in output.metadata

    async def test_empty_input(self):
        """Empty accounts and content produces empty dimensions."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="Nobody"),
            accounts=[],
            content=[],
        )
        output = await agent.run(input_data)

        assert output.dimensions == {}
        assert output.duration_seconds is not None

    async def test_evidence_populated(self):
        """Topic scores include evidence snippets."""
        agent = ProfilerAgent()
        input_data = ProfilerInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            content=_make_content(),
        )
        output = await agent.run(input_data)

        for dim, topics in output.dimensions.items():
            for topic in topics:
                assert isinstance(topic.evidence, list)


class TestDimensionClassifier:
    def test_professional(self):
        classifier = DimensionClassifier()
        assert classifier.classify("machine learning engineer") == "professional"
        assert classifier.classify("kubernetes deployment") == "professional"

    def test_personal(self):
        classifier = DimensionClassifier()
        assert classifier.classify("hiking and camping") == "personal"
        assert classifier.classify("cooking recipes") == "personal"

    def test_public(self):
        classifier = DimensionClassifier()
        assert classifier.classify("climate change policy") == "public"
        assert classifier.classify("election results") == "public"

    def test_unknown_defaults_to_personal(self):
        classifier = DimensionClassifier()
        assert classifier.classify("xyzzy12345") == "personal"

    def test_custom_keywords(self):
        classifier = DimensionClassifier(extra_professional={"xyzzy"})
        assert classifier.classify("xyzzy topic") == "professional"

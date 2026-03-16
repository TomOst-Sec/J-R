"""Tests for Linker Agent — topic connection mapper."""

from __future__ import annotations

from argus.agents.linker import LinkerAgent, LinkerInput
from argus.models.agent import Connection, LinkerOutput
from argus.models.profile import CandidateProfile, ContentItem, ProfileData
from argus.models.target import TargetInput
from argus.models.verification import VerificationResult


def _make_verified_accounts() -> list[VerificationResult]:
    """Create synthetic verified accounts with known topic references."""
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
                    bio="Machine learning engineer at Acme Corp",
                    location="San Francisco",
                ),
            ),
            signals=[],
            confidence=0.85,
            threshold_label="confirmed",
        ),
        VerificationResult(
            candidate=CandidateProfile(
                platform="reddit",
                username="johndoe",
                url="https://reddit.com/user/johndoe",
                exists=True,
                scraped_data=ProfileData(
                    username="johndoe",
                    bio="Software developer interested in AI and open source",
                ),
            ),
            signals=[],
            confidence=0.65,
            threshold_label="likely",
        ),
    ]


def _make_content() -> list[ContentItem]:
    """Create synthetic content with known topic references."""
    return [
        ContentItem(
            id="gh1",
            platform="github",
            text="ml-pipeline — A machine learning training pipeline for NLP tasks",
            content_type="repo",
        ),
        ContentItem(
            id="gh2",
            platform="github",
            text="react-dashboard — Frontend dashboard for analytics",
            content_type="repo",
        ),
        ContentItem(
            id="r1",
            platform="reddit",
            text="Just finished training a transformer model for sentiment analysis. "
            "Machine learning is amazing!",
            content_type="post",
        ),
        ContentItem(
            id="r2",
            platform="reddit",
            text="Great recipe for pasta carbonara",
            content_type="comment",
        ),
    ]


class TestLinkerAgent:
    async def test_discovers_topic_connections(self):
        """Linker finds connections between target and a topic."""
        accounts = _make_verified_accounts()
        content = _make_content()

        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="John Doe"),
            topic="machine learning",
            accounts=accounts,
            content=content,
        )
        output = await agent.run(input_data)

        assert isinstance(output, LinkerOutput)
        assert output.agent_name == "linker"
        assert len(output.connections) > 0

    async def test_classifies_relationship_types(self):
        """Connection types are classified correctly."""
        accounts = _make_verified_accounts()
        content = _make_content()

        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="John Doe"),
            topic="machine learning",
            accounts=accounts,
            content=content,
        )
        output = await agent.run(input_data)

        relationship_types = {c.relationship_type for c in output.connections}
        # Should find at least a mention in bio or content
        assert len(relationship_types) > 0

    async def test_ranked_by_confidence(self):
        """Connections are sorted by confidence descending."""
        accounts = _make_verified_accounts()
        content = _make_content()

        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="John Doe"),
            topic="machine learning",
            accounts=accounts,
            content=content,
        )
        output = await agent.run(input_data)

        confidences = [c.confidence for c in output.connections]
        assert confidences == sorted(confidences, reverse=True)

    async def test_no_connections_for_unrelated_topic(self):
        """No connections found for a topic with no relation to content."""
        accounts = _make_verified_accounts()
        content = [
            ContentItem(
                id="x1",
                platform="github",
                text="cooking-recipes — A collection of favorite recipes",
                content_type="repo",
            )
        ]
        # Remove ML references from bios
        for acct in accounts:
            if acct.candidate.scraped_data:
                acct.candidate.scraped_data.bio = "Cooking enthusiast"

        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="John Doe"),
            topic="quantum physics",
            accounts=accounts,
            content=content,
        )
        output = await agent.run(input_data)
        # Should find no/few connections since nothing matches quantum physics
        for conn in output.connections:
            assert conn.confidence < 0.5

    async def test_bio_mention_creates_connection(self):
        """Bio containing topic keyword produces a connection."""
        accounts = [
            VerificationResult(
                candidate=CandidateProfile(
                    platform="github",
                    username="johndoe",
                    url="https://github.com/johndoe",
                    exists=True,
                    scraped_data=ProfileData(
                        username="johndoe",
                        bio="I work at Google on search infrastructure",
                    ),
                ),
                signals=[],
                confidence=0.9,
                threshold_label="confirmed",
            )
        ]
        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="John Doe"),
            topic="Google",
            accounts=accounts,
            content=[],
        )
        output = await agent.run(input_data)

        google_connections = [
            c for c in output.connections if "google" in c.content_snippet.lower()
        ]
        assert len(google_connections) > 0

    async def test_empty_accounts_no_crash(self):
        """Empty accounts list produces empty output."""
        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="Nobody"),
            topic="anything",
            accounts=[],
            content=[],
        )
        output = await agent.run(input_data)
        assert output.connections == []
        assert output.duration_seconds is not None

    async def test_output_has_correct_fields(self):
        """Each Connection has required fields populated."""
        accounts = _make_verified_accounts()
        content = _make_content()

        agent = LinkerAgent()
        input_data = LinkerInput(
            target=TargetInput(name="John Doe"),
            topic="machine learning",
            accounts=accounts,
            content=content,
        )
        output = await agent.run(input_data)

        for conn in output.connections:
            assert isinstance(conn, Connection)
            assert conn.platform != ""
            assert conn.content_snippet != ""
            assert conn.relationship_type != ""
            assert 0.0 <= conn.confidence <= 1.0

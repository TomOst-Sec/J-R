"""Tests for Network Expansion Agent — social graph discovery."""

from __future__ import annotations

from argus.agents.network import NetworkAgent, NetworkInput, NetworkOutput
from argus.models.profile import CandidateProfile, ProfileData
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
                    bio="Engineer at Acme",
                    links=["https://johndoe.dev", "https://twitter.com/johndoe"],
                    raw_json={"company": "@acme-corp", "login": "johndoe"},
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
                    bio="Software dev",
                    raw_json={
                        "name": "johndoe",
                        "subreddit": {"display_name": "u_johndoe"},
                    },
                ),
            ),
            signals=[],
            confidence=0.65,
            threshold_label="likely",
        ),
    ]


class TestNetworkAgent:
    async def test_builds_graph(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)

        assert isinstance(output, NetworkOutput)
        assert output.agent_name == "network"
        assert output.node_count > 0
        assert output.edge_count > 0

    async def test_target_node_exists(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)

        nodes = [n["id"] for n in output.graph_json.get("nodes", [])]
        assert "John Doe" in nodes

    async def test_account_nodes_created(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)

        nodes = [n["id"] for n in output.graph_json.get("nodes", [])]
        assert "github:johndoe" in nodes
        assert "reddit:johndoe" in nodes

    async def test_connections_extracted(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)

        # Should have more nodes than just target + accounts (from links/company)
        assert output.node_count > 3

    async def test_max_nodes_respected(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
            max_nodes=5,
        )
        output = await agent.run(input_data)
        assert output.node_count <= 5

    async def test_graphml_export(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)

        assert output.graph_graphml != ""
        assert "graphml" in output.graph_graphml.lower()

    async def test_key_connections_populated(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)

        for conn in output.key_connections:
            assert "id" in conn
            assert "platform" in conn
            assert "degree" in conn

    async def test_empty_accounts(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="Nobody"),
            accounts=[],
        )
        output = await agent.run(input_data)

        assert output.node_count == 1  # Just the target node
        assert output.edge_count == 0

    async def test_duration_tracked(self):
        agent = NetworkAgent()
        input_data = NetworkInput(
            target=TargetInput(name="John Doe"),
            accounts=_make_accounts(),
        )
        output = await agent.run(input_data)
        assert output.duration_seconds is not None
        assert output.duration_seconds >= 0

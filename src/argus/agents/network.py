"""Network Expansion Agent — discovers social graph connections."""

from __future__ import annotations

from typing import Any

import networkx as nx

from argus.agents.base import BaseAgent
from argus.models.agent import AgentInput, AgentOutput
from argus.models.verification import VerificationResult


class NetworkInput(AgentInput):
    """Input for the Network Agent."""

    accounts: list[VerificationResult] = []
    max_depth: int = 1
    max_nodes: int = 50
    resolve_connections: bool = False


class NetworkOutput(AgentOutput):
    """Output from the Network Agent."""

    graph_json: dict[str, Any] = {}
    graph_graphml: str = ""
    node_count: int = 0
    edge_count: int = 0
    key_connections: list[dict[str, Any]] = []


class NetworkAgent(BaseAgent):
    """Discovers a person's social graph from verified accounts."""

    name = "network"

    async def _execute(self, agent_input: AgentInput) -> AgentOutput:
        if not isinstance(agent_input, NetworkInput):
            return NetworkOutput(
                target_name=agent_input.target.name,
                agent_name=self.name,
            )

        target_name = agent_input.target.name
        accounts = agent_input.accounts
        max_nodes = agent_input.max_nodes

        G = nx.Graph()

        # Add target as central node
        G.add_node(
            target_name,
            type="target",
            platforms=",".join(a.candidate.platform for a in accounts),
        )

        # Extract connections from each verified account
        for account in accounts:
            platform = account.candidate.platform
            username = account.candidate.username
            profile = account.candidate.scraped_data

            # Add the account as a node
            account_id = f"{platform}:{username}"
            G.add_node(account_id, type="account", platform=platform, username=username)
            G.add_edge(target_name, account_id, relationship="owns", platform=platform)

            # Extract connections from profile data
            if profile:
                connections = _extract_connections_from_profile(profile, platform)
                for conn in connections:
                    if G.number_of_nodes() >= max_nodes:
                        break
                    conn_id = f"{platform}:{conn['username']}"
                    if conn_id not in G:
                        G.add_node(
                            conn_id,
                            type="connection",
                            platform=platform,
                            username=conn["username"],
                        )
                    G.add_edge(
                        account_id,
                        conn_id,
                        relationship=conn.get("relationship", "linked"),
                        platform=platform,
                    )

        # Find key connections (highest degree nodes that aren't the target)
        key_connections = []
        for node in sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True):
            if node == target_name:
                continue
            data = G.nodes[node]
            if data.get("type") == "connection":
                key_connections.append({
                    "id": node,
                    "platform": data.get("platform", "unknown"),
                    "username": data.get("username", ""),
                    "degree": G.degree(node),
                })
            if len(key_connections) >= 10:
                break

        # Serialize graph
        graph_json = nx.node_link_data(G)
        graph_graphml = "\n".join(nx.generate_graphml(G))

        return NetworkOutput(
            target_name=target_name,
            agent_name=self.name,
            graph_json=graph_json,
            graph_graphml=graph_graphml,
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            key_connections=key_connections,
        )


def _extract_connections_from_profile(
    profile: Any, platform: str
) -> list[dict[str, str]]:
    """Extract potential connections from profile data."""
    connections: list[dict[str, str]] = []

    # Extract from links
    if hasattr(profile, "links") and profile.links:
        for link in profile.links[:5]:
            connections.append({
                "username": link.split("/")[-1] if "/" in link else link,
                "relationship": "linked",
            })

    # Extract from raw_json if available
    if hasattr(profile, "raw_json") and profile.raw_json:
        raw = profile.raw_json

        # GitHub: extract org/company info
        if platform == "github":
            if raw.get("company"):
                connections.append({
                    "username": raw["company"].lstrip("@"),
                    "relationship": "employed_at",
                })

        # Reddit: extract subreddit activity
        if platform == "reddit":
            subreddit = raw.get("subreddit", {})
            if isinstance(subreddit, dict) and subreddit.get("display_name"):
                connections.append({
                    "username": subreddit["display_name"],
                    "relationship": "active_in",
                })

    return connections

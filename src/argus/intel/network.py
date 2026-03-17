"""Network analysis -- graph construction, centrality, community detection."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NetworkAnalysisModule:
    """Build and analyze a social network graph from discovered accounts."""

    async def analyze(self, accounts: list[dict[str, Any]]) -> dict[str, Any]:
        """Build a networkx graph from accounts and compute analytics.

        Parameters
        ----------
        accounts:
            List of dicts, each with at least 'username', 'platform',
            and optionally 'connections' (list of usernames/ids).

        Returns
        -------
        dict with keys: node_count, edge_count, centrality, communities, components.
        """
        result: dict[str, Any] = {
            "node_count": 0,
            "edge_count": 0,
            "centrality": {},
            "communities": [],
            "components": 0,
            "error": None,
        }

        try:
            import networkx as nx
        except ImportError:
            result["error"] = "networkx not installed"
            return result

        G = nx.Graph()

        # Add nodes and edges
        for acct in accounts:
            node_id = f"{acct.get('platform', 'unknown')}:{acct.get('username', 'unknown')}"
            G.add_node(node_id, **{k: v for k, v in acct.items() if k != "connections"})

            for conn in acct.get("connections", []):
                if isinstance(conn, dict):
                    conn_id = f"{conn.get('platform', 'unknown')}:{conn.get('username', 'unknown')}"
                else:
                    conn_id = str(conn)
                G.add_edge(node_id, conn_id)

        result["node_count"] = G.number_of_nodes()
        result["edge_count"] = G.number_of_edges()

        if G.number_of_nodes() == 0:
            return result

        # Centrality
        try:
            degree_cent = nx.degree_centrality(G)
            # Return top 10 by centrality
            sorted_cent = sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)
            result["centrality"] = {k: round(v, 4) for k, v in sorted_cent[:10]}
        except Exception as exc:
            logger.warning("Centrality computation failed: %s", exc)

        # Connected components
        try:
            result["components"] = nx.number_connected_components(G)
        except Exception:
            pass

        # Community detection
        try:
            from networkx.algorithms.community import greedy_modularity_communities

            communities = greedy_modularity_communities(G)
            result["communities"] = [sorted(list(c)) for c in communities]
        except Exception as exc:
            logger.debug("Community detection failed: %s", exc)

        return result

"""GraphML and JSON graph export for network visualization."""

from __future__ import annotations

import json
from io import BytesIO

import networkx as nx

from argus.models.investigation import Investigation


def generate_graphml(investigation: Investigation) -> str:
    """Generate GraphML XML for Gephi/yEd import."""
    G = _build_graph(investigation)
    buf = BytesIO()
    nx.write_graphml(G, buf)
    return buf.getvalue().decode("utf-8")


def generate_graph_json(investigation: Investigation) -> str:
    """Generate D3.js-compatible JSON: {nodes: [...], links: [...]}."""
    G = _build_graph(investigation)
    data = nx.node_link_data(G)
    return json.dumps(data, indent=2, default=str)


def _build_graph(investigation: Investigation) -> nx.DiGraph:
    """Build a networkx graph from investigation results."""
    G = nx.DiGraph()

    target = investigation.target
    target_id = f"target:{target.name}"
    G.add_node(
        target_id,
        label=target.name,
        node_type="person",
        location=target.location or "",
    )

    resolver = investigation.resolver_output
    if resolver:
        for vr in resolver.accounts:
            account_id = f"account:{vr.candidate.platform}/{vr.candidate.username}"
            G.add_node(
                account_id,
                label=f"{vr.candidate.platform}/{vr.candidate.username}",
                node_type="account",
                platform=vr.candidate.platform,
                username=vr.candidate.username,
                url=vr.candidate.url,
                confidence=str(vr.confidence),
            )
            G.add_edge(
                target_id,
                account_id,
                relationship="has_account",
                weight=vr.confidence,
            )

        # Cross-platform confirmation edges
        accounts = resolver.accounts
        for i, vr1 in enumerate(accounts):
            for vr2 in accounts[i + 1 :]:
                if vr1.candidate.platform != vr2.candidate.platform:
                    # Check for shared signals
                    shared_signals = set()
                    for s in vr1.signals:
                        if s.score > 0.5:
                            shared_signals.add(s.signal_name)
                    for s in vr2.signals:
                        if s.score > 0.5 and s.signal_name in shared_signals:
                            a1 = f"account:{vr1.candidate.platform}/{vr1.candidate.username}"
                            a2 = f"account:{vr2.candidate.platform}/{vr2.candidate.username}"
                            G.add_edge(
                                a1,
                                a2,
                                relationship="cross_confirmed",
                                evidence=s.signal_name,
                            )

    # Linker connections
    linker = investigation.linker_output
    if linker and linker.connections:
        topics_added: set[str] = set()
        for conn in linker.connections:
            topic_id = f"topic:{conn.content_snippet[:30]}"
            if topic_id not in topics_added:
                G.add_node(topic_id, label=conn.content_snippet[:50], node_type="topic")
                topics_added.add(topic_id)
            source = f"account:{conn.platform}/{conn.platform}"
            if G.has_node(source):
                G.add_edge(
                    source,
                    topic_id,
                    relationship=conn.relationship_type,
                    confidence=conn.confidence,
                )

    return G

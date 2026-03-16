"""Tests for GraphML and JSON graph export."""

import json
from xml.etree import ElementTree

from argus.models.agent import ResolverOutput
from argus.models.investigation import Investigation
from argus.models.profile import CandidateProfile, ProfileData
from argus.models.target import Target
from argus.models.verification import SignalResult, VerificationResult
from argus.reporting.graph_export import generate_graph_json, generate_graphml


def _make_investigation():
    target = Target(name="John Doe", location="NYC")
    vr1 = VerificationResult(
        candidate=CandidateProfile(
            platform="github", username="johndoe",
            url="https://github.com/johndoe", exists=True,
            scraped_data=ProfileData(username="johndoe"),
        ),
        signals=[
            SignalResult(signal_name="bio_similarity", score=0.8, weight=0.2, evidence="match"),
        ],
        confidence=0.8, threshold_label="confirmed",
    )
    vr2 = VerificationResult(
        candidate=CandidateProfile(
            platform="reddit", username="johndoe",
            url="https://reddit.com/user/johndoe", exists=True,
            scraped_data=ProfileData(username="johndoe"),
        ),
        signals=[
            SignalResult(signal_name="bio_similarity", score=0.7, weight=0.2, evidence="match"),
        ],
        confidence=0.65, threshold_label="likely",
    )
    resolver = ResolverOutput(
        target_name="John Doe", agent_name="resolver", accounts=[vr1, vr2]
    )
    return Investigation(target=target, status="completed", resolver_output=resolver)


class TestGraphMLExport:
    def test_valid_xml(self):
        inv = _make_investigation()
        xml = generate_graphml(inv)
        # Should parse as valid XML
        ElementTree.fromstring(xml)

    def test_contains_nodes(self):
        inv = _make_investigation()
        xml = generate_graphml(inv)
        assert "John Doe" in xml
        assert "github" in xml
        assert "johndoe" in xml

    def test_contains_edges(self):
        inv = _make_investigation()
        xml = generate_graphml(inv)
        assert "has_account" in xml


class TestGraphJSONExport:
    def test_valid_json(self):
        inv = _make_investigation()
        result = generate_graph_json(inv)
        data = json.loads(result)
        assert "nodes" in data
        assert "edges" in data

    def test_has_nodes(self):
        inv = _make_investigation()
        data = json.loads(generate_graph_json(inv))
        # Should have target + 2 accounts = 3 nodes
        assert len(data["nodes"]) >= 3

    def test_has_links(self):
        inv = _make_investigation()
        data = json.loads(generate_graph_json(inv))
        # Should have at least 2 edges (target → account)
        assert len(data["edges"]) >= 2

    def test_empty_investigation(self):
        target = Target(name="Nobody")
        resolver = ResolverOutput(
            target_name="Nobody", agent_name="resolver", accounts=[]
        )
        inv = Investigation(target=target, status="completed", resolver_output=resolver)
        data = json.loads(generate_graph_json(inv))
        # Just the target node
        assert len(data["nodes"]) >= 1

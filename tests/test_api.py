"""Tests for the Argus REST API server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from argus.api.server import app, configure_auth, _investigations


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset state between tests."""
    _investigations.clear()
    configure_auth(None)  # Disable auth for tests
    yield
    _investigations.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestResolveEndpoint:
    def test_resolve_returns_results(self, client):
        resp = client.post("/resolve", json={"name": "Test User"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "resolver"
        assert data["target_name"] == "Test User"

    def test_resolve_with_options(self, client):
        resp = client.post(
            "/resolve",
            json={
                "name": "Jane Doe",
                "location": "NYC",
                "email": "jane@example.com",
                "threshold": 0.5,
            },
        )
        assert resp.status_code == 200


class TestLinkEndpoint:
    def test_link_returns_results(self, client):
        resp = client.post(
            "/link",
            json={"name": "Test User", "topic": "machine learning"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "linker"

    def test_link_with_description(self, client):
        resp = client.post(
            "/link",
            json={
                "name": "Test",
                "topic": "AI",
                "topic_description": "Artificial intelligence research",
            },
        )
        assert resp.status_code == 200


class TestProfileEndpoint:
    def test_profile_returns_results(self, client):
        resp = client.post("/profile", json={"name": "Test User"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "profiler"


class TestPlatformsEndpoint:
    def test_list_platforms(self, client):
        resp = client.get("/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestInvestigationEndpoints:
    def test_start_investigation(self, client):
        resp = client.post("/investigate", json={"name": "Test User"})
        assert resp.status_code == 200
        data = resp.json()
        assert "investigation_id" in data
        assert data["status"] == "running"

    def test_get_investigation(self, client):
        resp = client.post("/investigate", json={"name": "Test"})
        inv_id = resp.json()["investigation_id"]
        resp = client.get(f"/investigate/{inv_id}")
        assert resp.status_code == 200
        assert resp.json()["target"] == "Test"

    def test_get_investigation_not_found(self, client):
        resp = client.get("/investigate/nonexistent")
        assert resp.status_code == 404

    def test_delete_investigation(self, client):
        resp = client.post("/investigate", json={"name": "Del"})
        inv_id = resp.json()["investigation_id"]
        resp = client.delete(f"/investigate/{inv_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_not_found(self, client):
        resp = client.delete("/investigate/nonexistent")
        assert resp.status_code == 404

    def test_list_investigations(self, client):
        client.post("/investigate", json={"name": "One"})
        client.post("/investigate", json={"name": "Two"})
        resp = client.get("/investigations")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_get_report_json(self, client):
        resp = client.post("/investigate", json={"name": "Report Test"})
        inv_id = resp.json()["investigation_id"]
        resp = client.get(f"/investigate/{inv_id}/report?format=json")
        assert resp.status_code == 200

    def test_get_report_markdown(self, client):
        resp = client.post("/investigate", json={"name": "Report Test"})
        inv_id = resp.json()["investigation_id"]
        resp = client.get(f"/investigate/{inv_id}/report?format=markdown")
        assert resp.status_code == 200
        assert "# Report" in resp.json()["content"]


class TestAuth:
    def test_auth_required_when_configured(self, client):
        configure_auth("secret-token")
        resp = client.get("/platforms")
        assert resp.status_code == 401 or resp.status_code == 403

    def test_auth_succeeds_with_token(self, client):
        configure_auth("secret-token")
        resp = client.get(
            "/platforms", headers={"Authorization": "Bearer secret-token"}
        )
        assert resp.status_code == 200

    def test_auth_fails_with_wrong_token(self, client):
        configure_auth("secret-token")
        resp = client.get(
            "/platforms", headers={"Authorization": "Bearer wrong-token"}
        )
        assert resp.status_code == 401


class TestOpenAPI:
    def test_openapi_spec(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "Argus OSINT API"
        assert "/resolve" in spec["paths"]
        assert "/platforms" in spec["paths"]

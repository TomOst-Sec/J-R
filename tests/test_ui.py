"""Tests for the Argus web UI dashboard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from argus.api.server import app, _investigations, configure_auth


@pytest.fixture(autouse=True)
def _clear_state():
    _investigations.clear()
    configure_auth(None)
    yield
    _investigations.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestWebUI:
    def test_ui_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Argus" in resp.text
        assert "Dashboard" in resp.text

    def test_ui_contains_investigation_form(self, client):
        resp = client.get("/")
        assert "inv-name" in resp.text
        assert "Investigate" in resp.text

    def test_ui_contains_navigation(self, client):
        resp = client.get("/")
        assert "Platforms" in resp.text
        assert "Settings" in resp.text

    def test_ui_has_theme_toggle(self, client):
        resp = client.get("/")
        assert "theme-toggle" in resp.text

    def test_ui_is_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.headers.get("content-type", "")

    def test_ui_has_graph_container(self, client):
        resp = client.get("/")
        assert "graph-container" in resp.text

    def test_ui_has_responsive_meta(self, client):
        resp = client.get("/")
        assert "viewport" in resp.text

"""Tests for the Argus MCP server — tool registration, execution, resources, prompts."""

from __future__ import annotations

import pytest

from argus.mcp.server import (
    _investigations,
    get_investigation,
    investigation_accounts,
    investigation_connections,
    investigation_report,
    link_topic,
    list_investigations,
    mcp,
    osint_investigate,
    osint_quick_check,
    profile_person,
    resolve_person,
)


@pytest.fixture(autouse=True)
def _clear_investigations():
    _investigations.clear()
    yield
    _investigations.clear()


class TestMCPServerSetup:
    def test_server_name(self):
        assert mcp.name == "argus-osint"

    def test_tools_registered(self):
        # FastMCP registers tools via decorators; verify functions exist
        assert callable(resolve_person)
        assert callable(link_topic)
        assert callable(profile_person)
        assert callable(get_investigation)
        assert callable(list_investigations)


class TestResolvePersonTool:
    async def test_resolve_returns_results(self):
        result = await resolve_person(name="Test User")
        assert result["agent_name"] == "resolver"
        assert result["target_name"] == "Test User"
        assert "investigation_id" in result

    async def test_resolve_stores_investigation(self):
        result = await resolve_person(name="Stored Test")
        inv_id = result["investigation_id"]
        assert inv_id in _investigations
        assert _investigations[inv_id]["target"] == "Stored Test"


class TestLinkTopicTool:
    async def test_link_returns_results(self):
        result = await link_topic(name="Test", topic="AI")
        assert result["agent_name"] == "linker"

    async def test_link_with_description(self):
        result = await link_topic(
            name="Test", topic="ML", topic_description="Machine learning research"
        )
        assert result["agent_name"] == "linker"


class TestProfilePersonTool:
    async def test_profile_returns_results(self):
        result = await profile_person(name="Test User")
        assert result["agent_name"] == "profiler"


class TestGetInvestigation:
    async def test_get_existing(self):
        await resolve_person(name="Find Me")
        invs = await list_investigations()
        assert len(invs) > 0
        inv_id = invs[0]["id"]
        result = await get_investigation(inv_id)
        assert result["target"] == "Find Me"

    async def test_get_missing(self):
        result = await get_investigation("nonexistent")
        assert "error" in result


class TestListInvestigations:
    async def test_list_empty(self):
        result = await list_investigations()
        assert result == []

    async def test_list_after_resolve(self):
        await resolve_person(name="One")
        await resolve_person(name="Two")
        result = await list_investigations()
        assert len(result) == 2


class TestResources:
    async def test_report_resource(self):
        result = await resolve_person(name="Report Target")
        inv_id = result["investigation_id"]
        report = await investigation_report(inv_id)
        assert "# Investigation Report" in report
        assert "Report Target" in report

    async def test_report_not_found(self):
        report = await investigation_report("bad-id")
        assert "not found" in report.lower()

    async def test_accounts_resource(self):
        result = await resolve_person(name="Accounts Target")
        inv_id = result["investigation_id"]
        accounts = await investigation_accounts(inv_id)
        assert isinstance(accounts, str)

    async def test_connections_resource_no_data(self):
        result = await resolve_person(name="Conn Target")
        inv_id = result["investigation_id"]
        conns = await investigation_connections(inv_id)
        assert "no connections" in conns.lower() or "run link_topic" in conns.lower()


class TestPrompts:
    async def test_investigate_prompt(self):
        prompt = await osint_investigate(name="John Doe")
        assert "John Doe" in prompt
        assert "resolve_person" in prompt

    async def test_investigate_prompt_with_context(self):
        prompt = await osint_investigate(name="Jane", context="Focus on GitHub")
        assert "Jane" in prompt
        assert "GitHub" in prompt

    async def test_quick_check_prompt(self):
        prompt = await osint_quick_check(username="johndoe")
        assert "johndoe" in prompt
        assert "resolve_person" in prompt

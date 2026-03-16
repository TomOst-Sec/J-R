"""Tests for LangChain and CrewAI integration wrappers.

Tests use mocked imports since langchain-core and crewai are optional deps.
Uses monkeypatch for sys.modules to ensure cleanup on teardown.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest


@pytest.fixture
def mock_langchain(monkeypatch):
    """Mock langchain_core so we can test without installing it."""
    mock_module = ModuleType("langchain_core")
    mock_tools = ModuleType("langchain_core.tools")

    class FakeBaseTool:
        name: str = ""
        description: str = ""
        args_schema = None

        def invoke(self, input_data):
            return self._run(**input_data)

    mock_tools.BaseTool = FakeBaseTool
    mock_module.tools = mock_tools

    monkeypatch.setitem(sys.modules, "langchain_core", mock_module)
    monkeypatch.setitem(sys.modules, "langchain_core.tools", mock_tools)
    yield
    # Force reimport on next use (monkeypatch handles sys.modules cleanup)
    sys.modules.pop("argus.integrations.langchain", None)


@pytest.fixture
def mock_crewai(monkeypatch):
    """Mock crewai so we can test without installing it."""
    mock_module = ModuleType("crewai")
    mock_tools = ModuleType("crewai.tools")

    def tool(name):
        def decorator(func):
            func.tool_name = name
            return func
        return decorator

    mock_tools.tool = tool
    mock_module.tools = mock_tools

    monkeypatch.setitem(sys.modules, "crewai", mock_module)
    monkeypatch.setitem(sys.modules, "crewai.tools", mock_tools)
    yield
    sys.modules.pop("argus.integrations.crewai", None)


class TestLangChainIntegration:
    def test_resolve_tool_has_schema(self, mock_langchain):
        mod = importlib.import_module("argus.integrations.langchain")
        tool = mod.ArgusResolveTool()
        assert tool.name == "argus_resolve_person"
        assert "social media" in tool.description.lower()
        assert tool.args_schema is not None

    def test_link_tool_has_schema(self, mock_langchain):
        mod = importlib.import_module("argus.integrations.langchain")
        tool = mod.ArgusLinkTool()
        assert tool.name == "argus_link_topic"
        assert tool.args_schema is not None

    def test_profile_tool_has_schema(self, mock_langchain):
        mod = importlib.import_module("argus.integrations.langchain")
        tool = mod.ArgusProfileTool()
        assert tool.name == "argus_profile_person"
        assert tool.args_schema is not None

    async def test_resolve_arun(self, mock_langchain):
        mod = importlib.import_module("argus.integrations.langchain")
        tool = mod.ArgusResolveTool()
        result = await tool._arun(name="Test User")
        assert result["agent_name"] == "resolver"
        assert result["target_name"] == "Test User"

    async def test_link_arun(self, mock_langchain):
        mod = importlib.import_module("argus.integrations.langchain")
        tool = mod.ArgusLinkTool()
        result = await tool._arun(name="Test", topic="AI")
        assert result["agent_name"] == "linker"

    async def test_profile_arun(self, mock_langchain):
        mod = importlib.import_module("argus.integrations.langchain")
        tool = mod.ArgusProfileTool()
        result = await tool._arun(name="Test")
        assert result["agent_name"] == "profiler"


class TestCrewAIIntegration:
    def test_resolve_tool_exists(self, mock_crewai):
        mod = importlib.import_module("argus.integrations.crewai")
        assert hasattr(mod, "argus_resolve_tool")
        assert callable(mod.argus_resolve_tool)

    def test_link_tool_exists(self, mock_crewai):
        mod = importlib.import_module("argus.integrations.crewai")
        assert hasattr(mod, "argus_link_tool")

    def test_profile_tool_exists(self, mock_crewai):
        mod = importlib.import_module("argus.integrations.crewai")
        assert hasattr(mod, "argus_profile_tool")

    def test_resolve_tool_name(self, mock_crewai):
        mod = importlib.import_module("argus.integrations.crewai")
        assert mod.argus_resolve_tool.tool_name == "argus_resolve_person"

    def test_link_tool_name(self, mock_crewai):
        mod = importlib.import_module("argus.integrations.crewai")
        assert mod.argus_link_tool.tool_name == "argus_link_topic"


class TestImportErrors:
    def test_langchain_import_error_without_dep(self, monkeypatch):
        """Importing langchain wrapper without langchain installed raises ImportError."""
        # Ensure clean state
        monkeypatch.delitem(sys.modules, "argus.integrations.langchain", raising=False)
        monkeypatch.delitem(sys.modules, "langchain_core", raising=False)
        monkeypatch.delitem(sys.modules, "langchain_core.tools", raising=False)
        with pytest.raises(ImportError, match="langchain-core"):
            importlib.import_module("argus.integrations.langchain")

    def test_crewai_import_error_without_dep(self, monkeypatch):
        """Importing crewai wrapper without crewai installed raises ImportError."""
        monkeypatch.delitem(sys.modules, "argus.integrations.crewai", raising=False)
        monkeypatch.delitem(sys.modules, "crewai", raising=False)
        monkeypatch.delitem(sys.modules, "crewai.tools", raising=False)
        with pytest.raises(ImportError, match="crewai"):
            importlib.import_module("argus.integrations.crewai")

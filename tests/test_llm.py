"""Tests for the LLM provider abstraction and helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from argus.config.settings import ArgusConfig, LLMConfig
from argus.llm.factory import create_provider
from argus.llm.helpers import _extract_keywords, _keyword_classify, _tfidf_similarity, compare_bios, extract_topics, classify_dimension
from argus.llm.provider import NullProvider, OpenAIProvider, AnthropicProvider, OllamaProvider


class TestNullProvider:
    @pytest.mark.asyncio
    async def test_complete_returns_empty(self) -> None:
        p = NullProvider()
        assert await p.complete("test") == ""

    @pytest.mark.asyncio
    async def test_not_available(self) -> None:
        p = NullProvider()
        assert await p.is_available() is False


class TestFactory:
    def test_none_provider(self) -> None:
        config = ArgusConfig()
        p = create_provider(config)
        assert isinstance(p, NullProvider)

    def test_openai_provider(self) -> None:
        config = ArgusConfig(llm=LLMConfig(provider="openai", api_key="DUMMY", model="gpt-4o"))
        p = create_provider(config)
        assert isinstance(p, OpenAIProvider)

    def test_anthropic_provider(self) -> None:
        config = ArgusConfig(llm=LLMConfig(provider="anthropic", api_key="DUMMY"))
        p = create_provider(config)
        assert isinstance(p, AnthropicProvider)

    def test_ollama_provider(self) -> None:
        config = ArgusConfig(llm=LLMConfig(provider="ollama", model="llama3"))
        p = create_provider(config)
        assert isinstance(p, OllamaProvider)

    def test_missing_api_key(self) -> None:
        config = ArgusConfig(llm=LLMConfig(provider="openai"))
        p = create_provider(config)
        assert isinstance(p, NullProvider)


class TestOfflineFallbacks:
    def test_tfidf_similarity_identical(self) -> None:
        assert _tfidf_similarity("hello world", "hello world") == 1.0

    def test_tfidf_similarity_different(self) -> None:
        s = _tfidf_similarity("python developer", "cooking recipes")
        assert s < 0.5

    def test_tfidf_similarity_empty(self) -> None:
        assert _tfidf_similarity("", "hello") == 0.0

    def test_extract_keywords(self) -> None:
        text = "Python developer building machine learning models with scikit-learn"
        keywords = _extract_keywords(text)
        assert "python" in keywords
        assert "developer" in keywords

    def test_keyword_classify_tech(self) -> None:
        assert _keyword_classify("python", "software developer writing code") == "technology"

    def test_keyword_classify_sports(self) -> None:
        assert _keyword_classify("marathon", "running fitness training") == "sports"

    def test_keyword_classify_other(self) -> None:
        assert _keyword_classify("xyzzy", "unknown stuff") == "other"


class TestHelperFunctions:
    @pytest.mark.asyncio
    async def test_compare_bios_offline(self) -> None:
        p = NullProvider()
        score = await compare_bios("Python developer", "Python programmer", p)
        assert score > 0.0

    @pytest.mark.asyncio
    async def test_extract_topics_offline(self) -> None:
        p = NullProvider()
        topics = await extract_topics("Python developer building web applications with Django", p)
        assert len(topics) > 0

    @pytest.mark.asyncio
    async def test_classify_dimension_offline(self) -> None:
        p = NullProvider()
        dim = await classify_dimension("python", "software engineering", p)
        assert dim == "technology"

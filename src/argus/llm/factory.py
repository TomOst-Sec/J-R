"""LLM provider factory — creates the right provider from config."""

from __future__ import annotations

from typing import Any

from argus.llm.provider import (
    AnthropicProvider,
    LLMProvider,
    NullProvider,
    OllamaProvider,
    OpenAIProvider,
)


def create_provider(config: Any) -> LLMProvider:
    """Create an LLM provider based on config.llm settings."""
    if not hasattr(config, "llm"):
        return NullProvider()

    llm_config = config.llm
    provider_name = getattr(llm_config, "provider", "none")
    api_key = getattr(llm_config, "api_key", None)
    model = getattr(llm_config, "model", None)
    base_url = getattr(llm_config, "base_url", None)

    if provider_name == "openai" and api_key:
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4o",
            base_url=base_url,
        )

    if provider_name == "anthropic" and api_key:
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
        )

    if provider_name == "ollama":
        return OllamaProvider(
            model=model or "llama3",
            base_url=base_url or "http://localhost:11434",
        )

    return NullProvider()

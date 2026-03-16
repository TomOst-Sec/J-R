"""LLM provider abstraction — OpenAI, Anthropic, Ollama, and Null backends."""

from __future__ import annotations

import abc
from typing import Any


class LLMProvider(abc.ABC):
    """Abstract LLM provider interface."""

    @abc.abstractmethod
    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 1000
    ) -> str:
        """Generate a completion."""

    @abc.abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available."""


class NullProvider(LLMProvider):
    """No-op provider — always returns empty string."""

    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 1000
    ) -> str:
        return ""

    async def is_available(self) -> bool:
        return False


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                kwargs: dict[str, Any] = {"api_key": self._api_key}
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                self._client = AsyncOpenAI(**kwargs)
            except ImportError:
                return None
        return self._client

    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 1000
    ) -> str:
        client = self._get_client()
        if client is None:
            return ""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def is_available(self) -> bool:
        return self._get_client() is not None


class AnthropicProvider(LLMProvider):
    """Anthropic API provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                return None
        return self._client

    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 1000
    ) -> str:
        client = self._get_client()
        if client is None:
            return ""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        response = await client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    async def is_available(self) -> bool:
        return self._get_client() is not None


class OllamaProvider(LLMProvider):
    """Ollama local API provider."""

    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 1000
    ) -> str:
        import aiohttp
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._base_url}/api/generate", json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "")
        except Exception:
            pass
        return ""

    async def is_available(self) -> bool:
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._base_url}/api/tags") as resp:
                    return resp.status == 200
        except Exception:
            return False

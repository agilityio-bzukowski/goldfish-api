"""AI client abstraction: protocol + provider-specific implementations.

Provider endpoints (as of 2025):
- OpenAI:   POST {base}/v1/chat/completions  (base: https://api.openai.com)
- Anthropic: POST {base}/v1/messages         (base: https://api.anthropic.com), uses x-api-key + anthropic-version
- Ollama:  POST {base}/api/chat             (base: http://localhost:11434), native API
"""

from __future__ import annotations

from typing import Protocol

import httpx

PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
    "ollama": "http://localhost:11434",
}

ANTHROPIC_API_VERSION = "2023-06-01"


class AIClient(Protocol):
    """Minimal contract for an AI chat-completion client."""

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str: ...


class AnthropicClient:
    """Uses Anthropic Messages API: POST /v1/messages (not OpenAI-compatible)."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": ANTHROPIC_API_VERSION,
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        payload = {
            "model": self._model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        url = f"{self._base_url}/v1/messages"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, headers=headers, json=payload, timeout=60.0
            )
            resp.raise_for_status()
        data = resp.json()
        content_blocks = data.get("content") or []
        parts = [
            b["text"]
            for b in content_blocks
            if isinstance(b, dict) and b.get("type") == "text" and "text" in b
        ]
        if not parts:
            raise ValueError("No text content in Anthropic response")
        return "".join(parts)


class OllamaClient:
    """Uses Ollama native /api/chat (works on all Ollama versions; /v1/chat/completions can 404 on older ones)."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 1000},
        }
        url = f"{self._base_url}/api/chat"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, headers={"Content-Type": "application/json"}, json=payload, timeout=60.0
            )
            if resp.status_code >= 400:
                err_detail = _ollama_error_detail(resp, self._model)
                raise ValueError(err_detail)
        data = resp.json()
        content = (data.get("message") or {}).get("content")

        if content is None:
            raise ValueError("No content in Ollama response")

        return content if isinstance(content, str) else str(content)


def _ollama_error_detail(resp: httpx.Response, model: str) -> str:
    """Turn Ollama error response into a clear message (e.g. model not found)."""
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if err and "not found" in str(err).lower():
            return f"Model '{model}' not found. Pull it with: ollama pull {model}"
        if err:
            return str(err)
    except Exception:
        pass
    return f"Ollama returned {resp.status_code}: {resp.text[:200] if resp.text else 'unknown error'}"


class OpenAIClient:
    """Calls any OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        url = f"{self._base_url}/v1/chat/completions"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
        return self._extract_content(resp.json())

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Pull text content from an OpenAI-style chat completion response.

        Raises ValueError when the payload is missing choices or content
        (e.g. content_filter finish_reason).
        """
        content = (
            data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if content is None:
            raise ValueError("No content in AI response")
        return content if isinstance(content, str) else str(content)


def build_ai_client(
    *,
    provider: str,
    api_key: str | None,
    model: str,
    base_url: str | None,
) -> AIClient:
    """Factory: resolve provider settings into a concrete AIClient."""
    p = (provider or "openai").lower()
    resolved_url = (
        base_url.rstrip("/") if base_url else PROVIDER_BASE_URLS.get(p, "https://api.openai.com")
    )
    if p == "ollama":
        return OllamaClient(api_key=api_key, model=model, base_url=resolved_url)
    if p == "anthropic":
        return AnthropicClient(api_key=api_key, model=model, base_url=resolved_url)
    return OpenAIClient(api_key=api_key, model=model, base_url=resolved_url)

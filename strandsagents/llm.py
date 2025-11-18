"""LLM client implementations for Strands Agents."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import List, Sequence

try:
    import certifi
except ImportError:  # pragma: no cover - optional dependency
    certifi = None


Message = dict  # alias for typing readability


class OpenAIChatClient:
    """Minimal OpenAI Chat Completions client for GPT models."""

    def __init__(
        self,
        model: str = "gpt-5-codex",
        api_key: str | None = None,
        api_base: str = "https://api.openai.com/v1",
        timeout: int = 60,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def complete(
        self,
        messages: Sequence[Message],
        temperature: float | None = None,
        max_tokens: int = 800,
    ) -> str:
        if not self.api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Please export the key before running spec agents."
            )

        if self.model.startswith("gpt-5"):
            return self._complete_via_responses(messages, temperature, max_tokens)

        payload = {
            "model": self.model,
            "messages": list(messages),
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "text"},
        }
        if temperature is not None:
            payload["temperature"] = temperature

        data = self._post_json("chat/completions", payload)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI API returned no choices")
        return choices[0].get("message", {}).get("content", "").strip()

    def _complete_via_responses(
        self,
        messages: Sequence[Message],
        temperature: float | None,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": self.model,
            "input": list(messages),
            "max_output_tokens": max_tokens,
            "text": {"format": {"type": "text"}},
        }
        if temperature is not None:
            payload["temperature"] = temperature

        data = self._post_json("responses", payload)
        outputs = data.get("output", [])
        texts: List[str] = []
        for item in outputs:
            if item.get("type") == "message":
                for chunk in item.get("content", []):
                    if chunk.get("type") in ("output_text", "text"):
                        texts.append(chunk.get("text", ""))
        final = "\n".join(t.strip() for t in texts if t.strip())
        return final

    def _post_json(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            url=f"{self.api_base}/{path.lstrip('/')}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        context = ssl.create_default_context(cafile=certifi.where() if certifi else None)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenAI API error: {exc.read().decode('utf-8')}") from exc


class StubLLMClient:
    """Test double that captures prompts and returns a canned response."""

    def __init__(self, response: str = "(stub response)") -> None:
        self.response = response
        self.calls: List[Sequence[Message]] = []

    def complete(self, messages: Sequence[Message], **_: int) -> str:  # type: ignore[override]
        self.calls.append(list(messages))
        return self.response


__all__ = ["OpenAIChatClient", "StubLLMClient", "Message"]

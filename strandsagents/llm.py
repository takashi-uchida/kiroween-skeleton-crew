"""LLM client implementations for Strands Agents."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import List, Sequence


Message = dict  # alias for typing readability


class OpenAIChatClient:
    """Minimal OpenAI Chat Completions client for GPT models."""

    def __init__(
        self,
        model: str = "gpt-5",
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
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        if not self.api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Please export the key before running spec agents."
            )

        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        request = urllib.request.Request(
            url=f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenAI API error: {exc.read().decode('utf-8')}") from exc

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI API returned no choices")

        return choices[0].get("message", {}).get("content", "").strip()


class StubLLMClient:
    """Test double that captures prompts and returns a canned response."""

    def __init__(self, response: str = "(stub response)") -> None:
        self.response = response
        self.calls: List[Sequence[Message]] = []

    def complete(self, messages: Sequence[Message], **_: int) -> str:  # type: ignore[override]
        self.calls.append(list(messages))
        return self.response


__all__ = ["OpenAIChatClient", "StubLLMClient", "Message"]

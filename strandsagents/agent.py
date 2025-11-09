"""Strands Agent implementation that delegates reasoning to an LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from .llm import Message, OpenAIChatClient


@dataclass
class StrandsTask:
    """Unit of work dispatched to a Strands Agent."""

    identifier: str
    title: str
    description: str
    checklist: List[str]


class StrandsAgent:
    """LLM-backed agent that can execute documentation spec tasks."""

    def __init__(
        self,
        name: str,
        system_prompt: str | None = None,
        model: str = "gpt-5",
        llm_client: Optional[Any] = None,
        temperature: float = 0.2,
        max_tokens: int = 900,
    ) -> None:
        self.name = name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or (
            "You are StrandsAgent, a detail-oriented technical writer and engineer. "
            "Execute each task carefully, reason explicitly, and output actionable steps."
        )
        self.llm_client = llm_client or OpenAIChatClient(model=model)

    def run_task(self, task: StrandsTask, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task via the configured language model."""

        messages: Sequence[Message] = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": self._render_prompt(task, context or {}),
            },
        ]

        output = self.llm_client.complete(
            messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return {
            "task_id": task.identifier,
            "title": task.title,
            "output": output,
        }

    def _render_prompt(self, task: StrandsTask, context: Dict[str, Any]) -> str:
        lines = [
            f"Task ID: {task.identifier}",
            f"Task Title: {task.title}",
            "Description:",
            task.description.strip(),
        ]
        if task.checklist:
            lines.append("Checklist:")
            for item in task.checklist:
                lines.append(f"- {item.strip()}")
        if context:
            lines.append("Context:")
            for key, value in context.items():
                lines.append(f"- {key}: {value}")
        lines.append(
            "Produce a clear plan of action, call out any missing information, and include verification steps."
        )
        return "\n".join(lines)


__all__ = ["StrandsAgent", "StrandsTask"]

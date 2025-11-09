"""Utilities to run .kiro spec tasks through Strands Agents."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from .agent import StrandsAgent, StrandsTask
from .llm import OpenAIChatClient

logger = logging.getLogger(__name__)

TASK_HEADER = re.compile(r"^- \[(?: |x)\]\s*(?P<id>[\d\.]+)\.?\s*(?P<title>.+)$")


@dataclass
class SpecTask:
    identifier: str
    title: str
    description: str
    checklist: List[str]


class SpecTaskRunner:
    """Parses spec tasks and executes each via a Strands Agent."""

    def __init__(
        self,
        agent: Optional[StrandsAgent] = None,
        model: str = "gpt-5",
        llm_client: Optional[Any] = None,
    ) -> None:
        self.agent = agent or StrandsAgent(
            name="SpecStrandsAgent",
            model=model,
            llm_client=llm_client,
        )

    def load_tasks(self, tasks_path: Path) -> List[SpecTask]:
        if not tasks_path.exists():
            raise FileNotFoundError(f"Spec tasks file not found: {tasks_path}")

        lines = tasks_path.read_text(encoding="utf-8").splitlines()
        tasks: List[SpecTask] = []
        current_id: Optional[str] = None
        current_title: Optional[str] = None
        description_lines: List[str] = []
        checklist: List[str] = []

        def flush_current() -> None:
            nonlocal current_id, current_title, description_lines, checklist
            if current_id and current_title:
                tasks.append(
                    SpecTask(
                        identifier=current_id,
                        title=current_title.strip(),
                        description="\n".join(description_lines).strip(),
                        checklist=list(checklist),
                    )
                )
            current_id = None
            current_title = None
            description_lines = []
            checklist = []

        for raw_line in lines:
            line = raw_line.rstrip()
            header_match = TASK_HEADER.match(line)
            if header_match:
                flush_current()
                current_id = header_match.group("id")
                current_title = header_match.group("title")
                continue

            if line.strip().startswith("-") and current_id:
                checklist.append(line.strip("- "))
            elif current_id:
                description_lines.append(line.strip())

        flush_current()
        logger.debug("Loaded %s tasks from %s", len(tasks), tasks_path)
        return tasks

    def run(self, tasks_path: Path) -> List[dict]:
        tasks = self.load_tasks(tasks_path)
        results = []
        for task in tasks:
            strands_task = StrandsTask(
                identifier=task.identifier,
                title=task.title,
                description=task.description,
                checklist=task.checklist,
            )
            logger.info("Executing Strands task %s - %s", task.identifier, task.title)
            results.append(self.agent.run_task(strands_task))
        return results


__all__ = ["SpecTask", "SpecTaskRunner"]

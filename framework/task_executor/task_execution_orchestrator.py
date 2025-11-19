"""Coordinator that ties SpecTaskRunner output to real workspaces."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from strandsagents import SpecTask, SpecTaskRunner, StrandsAgent, StrandsTask

from framework.workspace_manager import (
    ConfigManager,
    WorkspaceOrchestrator,
    WorkspaceManagerError,
)

from .code_writer import TaskOutputWriter

logger = logging.getLogger(__name__)


class TaskExecutionError(RuntimeError):
    """Raised when a task cannot be executed."""


@dataclass(slots=True)
class TaskExecutionResult:
    """Metadata about an executed task."""

    task_id: str
    title: str
    branch_name: str
    output_path: Path
    raw_output: str
    workspace_path: Path


class TaskExecutionOrchestrator:
    """High-level coordinator for AI-powered task execution."""

    def __init__(
        self,
        *,
        specs_root: Optional[Path] = None,
        workspace_orchestrator: Optional[WorkspaceOrchestrator] = None,
        task_runner: Optional[SpecTaskRunner] = None,
        output_writer: Optional[TaskOutputWriter] = None,
    ) -> None:
        self.specs_root = Path(specs_root or ".kiro/specs")
        self.workspace_orchestrator = workspace_orchestrator or WorkspaceOrchestrator(
            ConfigManager.load_config()
        )
        self.task_runner = task_runner or SpecTaskRunner()
        self.output_writer = output_writer or TaskOutputWriter()

    def execute_task(
        self,
        *,
        spec_name: str,
        repo_url: str,
        task_id: str,
        tasks_filename: str = "tasks.md",
        requirements_filename: str = "requirements.md",
        design_filename: str = "design.md",
    ) -> TaskExecutionResult:
        """Execute a single spec task end-to-end."""
        spec_dir = self.specs_root / spec_name
        tasks_path = spec_dir / tasks_filename
        spec_task = self._find_task(tasks_path, task_id)
        workspace = self._ensure_workspace(spec_name, repo_url)
        branch_name = workspace.create_task_branch(spec_task.identifier, spec_task.title)
        context = self._build_context(spec_dir, requirements_filename, design_filename)
        raw_result = self._run_task(spec_task, context)
        output_path = self.output_writer.write_output(
            workspace.path, spec_task.identifier, raw_result
        )
        logger.info(
            "Task %s (%s) completed. Output stored at %s",
            spec_task.identifier,
            spec_task.title,
            output_path,
        )
        return TaskExecutionResult(
            task_id=spec_task.identifier,
            title=spec_task.title,
            branch_name=branch_name,
            output_path=output_path,
            raw_output=raw_result,
            workspace_path=workspace.path,
        )

    def execute_all_tasks(
        self,
        *,
        spec_name: str,
        repo_url: str,
        tasks_filename: str = "tasks.md",
        requirements_filename: str = "requirements.md",
        design_filename: str = "design.md",
    ) -> Dict[str, TaskExecutionResult]:
        """Sequentially execute every task defined in the spec."""
        spec_dir = self.specs_root / spec_name
        tasks_path = spec_dir / tasks_filename
        tasks = self.task_runner.load_tasks(tasks_path)
        results: Dict[str, TaskExecutionResult] = {}
        for task in tasks:
            result = self.execute_task(
                spec_name=spec_name,
                repo_url=repo_url,
                task_id=task.identifier,
                tasks_filename=tasks_filename,
                requirements_filename=requirements_filename,
                design_filename=design_filename,
            )
            results[task.identifier] = result
        return results

    def _ensure_workspace(self, spec_name: str, repo_url: str):
        workspace = self.workspace_orchestrator.get_workspace(spec_name)
        if workspace:
            return workspace
        try:
            return self.workspace_orchestrator.create_workspace(spec_name, repo_url)
        except WorkspaceManagerError as exc:
            raise TaskExecutionError(
                f"Failed to prepare workspace for spec '{spec_name}': {exc}"
            ) from exc

    def _find_task(self, tasks_path: Path, task_id: str) -> SpecTask:
        tasks = self.task_runner.load_tasks(tasks_path)
        for task in tasks:
            if task.identifier == task_id:
                return task
        raise TaskExecutionError(
            f"Task '{task_id}' not found in {tasks_path}. "
            "Verify the identifier matches the tasks.md file."
        )

    def _build_context(
        self,
        spec_dir: Path,
        requirements_filename: str,
        design_filename: str,
    ) -> Dict[str, str]:
        context: Dict[str, str] = {}
        req_path = spec_dir / requirements_filename
        design_path = spec_dir / design_filename
        if req_path.exists():
            context["requirements"] = req_path.read_text(encoding="utf-8")
        if design_path.exists():
            context["design"] = design_path.read_text(encoding="utf-8")
        return context

    def _run_task(self, task: SpecTask, context: Dict[str, str]) -> str:
        strands_task = StrandsTask(
            identifier=task.identifier,
            title=task.title,
            description=task.description,
            checklist=task.checklist,
        )
        agent: StrandsAgent = self.task_runner.agent
        result = agent.run_task(strands_task, context=context)
        return result["output"]

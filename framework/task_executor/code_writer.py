"""Utilities for writing AI-generated output into workspaces."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class TaskOutputWriter:
    """Persist raw LLM output so humans can review the generated plan/code.

    The initial implementation stores each task's output as Markdown under
    ``.kiro/generated`` inside the workspace. Future tasks will replace this
    naive dumping with structured code extraction (Task 16 in the spec).
    """

    def __init__(self, relative_output_dir: str = ".kiro/generated") -> None:
        self.relative_output_dir = relative_output_dir

    def write_output(self, workspace_path: Path, task_id: str, content: str) -> Path:
        """Write task output to a deterministic file within the workspace.

        Args:
            workspace_path: Root path of the cloned repository.
            task_id: Identifier such as ``"1.2"`` used for file naming.
            content: Raw LLM output to persist.

        Returns:
            Path to the file that was written.
        """
        target_dir = workspace_path / self.relative_output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"task-{task_id.replace('.', '-')}.md"
        target_file = target_dir / filename
        header = f"# Task {task_id}\n\n"
        target_file.write_text(header + content.strip() + "\n", encoding="utf-8")
        self._ensure_git_exclude(workspace_path, target_dir)
        return target_file

    def _ensure_git_exclude(self, workspace_path: Path, target_dir: Path) -> None:
        """Add the output directory to .git/info/exclude to keep the tree clean."""
        git_dir = workspace_path / ".git" / "info"
        exclude_path = git_dir / "exclude"
        try:
            git_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return  # workspace might not be a git repo (tests), ignore silently

        rel_path = target_dir.relative_to(workspace_path)
        pattern = str(rel_path).rstrip("/") + "/"

        existing: Optional[str] = None
        if exclude_path.exists():
            existing = exclude_path.read_text(encoding="utf-8")
            if pattern in existing:
                return

        with open(exclude_path, "a", encoding="utf-8") as fh:
            if existing and not existing.endswith("\n"):
                fh.write("\n")
            fh.write(pattern + "\n")

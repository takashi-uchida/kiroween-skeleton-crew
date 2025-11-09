"""Base class for every NecroCode spirit."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class BaseSpirit:
    role: str
    skills: List[str]
    workspace: str = "workspace1"
    instance_number: int = 1
    identifier: str = field(init=False)
    current_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.identifier = f"{self.role}_spirit_{self.instance_number}"

    def chant(self, message: str) -> str:
        return f"💀 {self.identifier}: {message}"

    def assign_task(self, task_id: str) -> None:
        """Add task to current workload."""
        if task_id not in self.current_tasks:
            self.current_tasks.append(task_id)

    def complete_task(self, task_id: str) -> None:
        """Mark task as complete and move to completed list."""
        if task_id in self.current_tasks:
            self.current_tasks.remove(task_id)
        # Allow recording completions even if the task is no longer active
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)

    def get_workload(self) -> int:
        """Return the number of active tasks."""
        return len(self.current_tasks)

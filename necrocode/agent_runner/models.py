"""
Data models for Agent Runner.

This module defines all data structures used by the Agent Runner component,
including task context, execution results, and artifacts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class RunnerState(Enum):
    """Runner execution state."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunnerStateSnapshot:
    """
    Snapshot of runner state for persistence.
    
    Contains the current state of the runner along with metadata
    about the current task execution, allowing state recovery.
    """
    runner_id: str
    state: RunnerState
    task_id: Optional[str] = None
    spec_name: Optional[str] = None
    start_time: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Parallel execution tracking
    workspace_path: Optional[str] = None  # Unique workspace for this runner instance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "runner_id": self.runner_id,
            "state": self.state.value,
            "task_id": self.task_id,
            "spec_name": self.spec_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
            "workspace_path": self.workspace_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerStateSnapshot":
        """Create from dictionary."""
        data = data.copy()
        data["state"] = RunnerState(data["state"])
        if data.get("start_time"):
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("last_updated"):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)


class ArtifactType(Enum):
    """Type of artifact produced by task execution."""
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"


@dataclass
class Workspace:
    """
    Workspace information for task execution.
    
    Represents a Git workspace where task implementation occurs,
    including path and branch information.
    """
    path: Path
    branch_name: str
    base_branch: str = "main"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": str(self.path),
            "branch_name": self.branch_name,
            "base_branch": self.base_branch,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        """Create from dictionary."""
        data = data.copy()
        data["path"] = Path(data["path"])
        return cls(**data)


@dataclass
class TaskContext:
    """
    Context information for task execution.
    
    Contains all information needed to execute a task, including task metadata,
    workspace configuration, test settings, and execution parameters.
    """
    task_id: str
    spec_name: str
    title: str
    description: str
    acceptance_criteria: List[str]
    dependencies: List[str]
    required_skill: str
    
    # Workspace information
    slot_path: Path
    slot_id: str
    branch_name: str
    
    # Test settings
    test_commands: Optional[List[str]] = None
    fail_fast: bool = True
    
    # Timeout settings
    timeout_seconds: int = 1800  # 30 minutes
    
    # Playbook
    playbook_path: Optional[Path] = None
    
    # Task complexity and review requirements
    complexity: str = "medium"  # low, medium, high
    require_review: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "spec_name": self.spec_name,
            "title": self.title,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "dependencies": self.dependencies,
            "required_skill": self.required_skill,
            "slot_path": str(self.slot_path),
            "slot_id": self.slot_id,
            "branch_name": self.branch_name,
            "test_commands": self.test_commands,
            "fail_fast": self.fail_fast,
            "timeout_seconds": self.timeout_seconds,
            "playbook_path": str(self.playbook_path) if self.playbook_path else None,
            "complexity": self.complexity,
            "require_review": self.require_review,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskContext":
        """Create from dictionary."""
        data = data.copy()
        if "slot_path" in data:
            data["slot_path"] = Path(data["slot_path"])
        if "playbook_path" in data and data["playbook_path"]:
            data["playbook_path"] = Path(data["playbook_path"])
        return cls(**data)


@dataclass
class ImplementationResult:
    """
    Result of task implementation.
    
    Contains information about the implementation process, including
    changes made, files affected, and any errors encountered.
    """
    success: bool
    diff: str
    files_changed: List[str]
    duration_seconds: float
    error: Optional[str] = None
    review_result: Optional[Any] = None  # ReviewResult from code review collaboration
    pair_session_id: Optional[str] = None  # If implemented with pair programming
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "diff": self.diff,
            "files_changed": self.files_changed,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "review_result": self.review_result,
            "pair_session_id": self.pair_session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImplementationResult":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SingleTestResult:
    """
    Result of a single test execution.
    
    Contains the command executed, output, and execution metrics.
    """
    command: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "command": self.command,
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SingleTestResult":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TestResult:
    """
    Aggregated test execution results.
    
    Contains results from all test commands executed for a task.
    """
    success: bool
    test_results: List[SingleTestResult]
    total_duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "test_results": [r.to_dict() for r in self.test_results],
            "total_duration_seconds": self.total_duration_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestResult":
        """Create from dictionary."""
        data = data.copy()
        data["test_results"] = [
            SingleTestResult.from_dict(r) for r in data["test_results"]
        ]
        return cls(**data)


@dataclass
class PushResult:
    """
    Result of Git push operation.
    
    Contains information about the branch pushed, commit hash,
    and any retry attempts made.
    """
    success: bool
    branch_name: str
    commit_hash: str
    retry_count: int
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "branch_name": self.branch_name,
            "commit_hash": self.commit_hash,
            "retry_count": self.retry_count,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PushResult":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Artifact:
    """
    Artifact produced during task execution.
    
    Represents a file or resource uploaded to the Artifact Store,
    such as diffs, logs, or test results.
    """
    type: ArtifactType
    uri: str
    size_bytes: int
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "uri": self.uri,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Create from dictionary."""
        data = data.copy()
        data["type"] = ArtifactType(data["type"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class RunnerResult:
    """
    Complete result of task execution by Agent Runner.
    
    Contains overall execution status, artifacts produced, and
    detailed results from each execution phase.
    """
    success: bool
    runner_id: str
    task_id: str
    duration_seconds: float
    artifacts: List[Artifact]
    error: Optional[str] = None
    
    # Detailed results
    impl_result: Optional[ImplementationResult] = None
    test_result: Optional[TestResult] = None
    push_result: Optional[PushResult] = None
    
    # Parallel execution metadata
    workspace_path: Optional[str] = None  # Unique workspace used
    concurrent_runners: int = 1  # Number of concurrent runners at execution time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "runner_id": self.runner_id,
            "task_id": self.task_id,
            "duration_seconds": self.duration_seconds,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "error": self.error,
            "impl_result": self.impl_result.to_dict() if self.impl_result else None,
            "test_result": self.test_result.to_dict() if self.test_result else None,
            "push_result": self.push_result.to_dict() if self.push_result else None,
            "workspace_path": self.workspace_path,
            "concurrent_runners": self.concurrent_runners,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerResult":
        """Create from dictionary."""
        data = data.copy()
        data["artifacts"] = [Artifact.from_dict(a) for a in data["artifacts"]]
        if data.get("impl_result"):
            data["impl_result"] = ImplementationResult.from_dict(data["impl_result"])
        if data.get("test_result"):
            data["test_result"] = TestResult.from_dict(data["test_result"])
        if data.get("push_result"):
            data["push_result"] = PushResult.from_dict(data["push_result"])
        return cls(**data)


@dataclass
class PlaybookStep:
    """
    Single step in a Playbook execution sequence.
    
    Defines a command to execute with optional conditions,
    timeout, and retry settings.
    """
    name: str
    command: str
    condition: Optional[str] = None  # e.g., "test_enabled == true"
    fail_fast: bool = True
    timeout_seconds: int = 300
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "command": self.command,
            "condition": self.condition,
            "fail_fast": self.fail_fast,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybookStep":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Playbook:
    """
    Playbook defining task execution workflow.
    
    Contains a sequence of steps to execute for a task,
    with optional metadata for customization.
    """
    name: str
    steps: List[PlaybookStep]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Playbook":
        """Create from dictionary."""
        data = data.copy()
        data["steps"] = [PlaybookStep.from_dict(s) for s in data["steps"]]
        return cls(**data)

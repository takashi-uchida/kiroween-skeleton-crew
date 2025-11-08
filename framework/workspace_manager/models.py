"""Data models for workspace management."""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List
import json


@dataclass
class WorkspaceConfig:
    """Configuration for workspace management."""
    
    base_path: Path
    state_file: Path
    gitignore_path: Path
    auto_push: bool = True
    auto_pr: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with Path objects as strings."""
        return {
            "base_path": str(self.base_path),
            "state_file": str(self.state_file),
            "gitignore_path": str(self.gitignore_path),
            "auto_push": self.auto_push,
            "auto_pr": self.auto_pr,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceConfig":
        """Create from dictionary with string paths."""
        return cls(
            base_path=Path(data["base_path"]),
            state_file=Path(data["state_file"]),
            gitignore_path=Path(data["gitignore_path"]),
            auto_push=data.get("auto_push", True),
            auto_pr=data.get("auto_pr", False),
        )


@dataclass
class WorkspaceInfo:
    """Information about a workspace instance."""
    
    spec_name: str
    workspace_path: Path
    repo_url: str
    current_branch: str
    created_at: str
    tasks_completed: List[str]
    status: str  # 'active', 'completed', 'error'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "spec_name": self.spec_name,
            "workspace_path": str(self.workspace_path),
            "repo_url": self.repo_url,
            "current_branch": self.current_branch,
            "created_at": self.created_at,
            "tasks_completed": self.tasks_completed,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceInfo":
        """Create from dictionary loaded from JSON."""
        return cls(
            spec_name=data["spec_name"],
            workspace_path=Path(data["workspace_path"]),
            repo_url=data["repo_url"],
            current_branch=data["current_branch"],
            created_at=data["created_at"],
            tasks_completed=data.get("tasks_completed", []),
            status=data.get("status", "active"),
        )

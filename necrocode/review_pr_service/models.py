"""
Data models for Review & PR Service.

Defines core data structures for Pull Requests, CI status, and related entities.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import json


class PRState(Enum):
    """Pull Request state enumeration."""
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"
    DRAFT = "draft"


class CIStatus(Enum):
    """Continuous Integration status enumeration."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class PullRequest:
    """
    Pull Request data model.
    
    Represents a pull request with all its metadata and state information.
    Supports serialization to/from JSON for persistence and API communication.
    """
    
    pr_id: str
    pr_number: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    url: str
    state: PRState
    draft: bool
    created_at: datetime
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    author: Optional[str] = None
    reviewers: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    ci_status: Optional[CIStatus] = None
    merge_commit_sha: Optional[str] = None
    task_id: Optional[str] = None
    spec_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert PullRequest to dictionary for serialization.
        
        Returns:
            Dictionary representation with enum values converted to strings
            and datetime objects converted to ISO format strings.
        """
        data = asdict(self)
        data["state"] = self.state.value
        data["ci_status"] = self.ci_status.value if self.ci_status else None
        data["created_at"] = self.created_at.isoformat()
        data["merged_at"] = self.merged_at.isoformat() if self.merged_at else None
        data["closed_at"] = self.closed_at.isoformat() if self.closed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PullRequest":
        """
        Create PullRequest from dictionary.
        
        Args:
            data: Dictionary containing PR data
            
        Returns:
            PullRequest instance
        """
        # Convert string enums back to enum types
        if isinstance(data.get("state"), str):
            data["state"] = PRState(data["state"])
        if data.get("ci_status") and isinstance(data["ci_status"], str):
            data["ci_status"] = CIStatus(data["ci_status"])
        
        # Convert ISO format strings back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("merged_at") and isinstance(data["merged_at"], str):
            data["merged_at"] = datetime.fromisoformat(data["merged_at"])
        if data.get("closed_at") and isinstance(data["closed_at"], str):
            data["closed_at"] = datetime.fromisoformat(data["closed_at"])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """
        Convert PullRequest to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "PullRequest":
        """
        Create PullRequest from JSON string.
        
        Args:
            json_str: JSON string containing PR data
            
        Returns:
            PullRequest instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_mergeable(self) -> bool:
        """
        Check if PR is in a mergeable state.
        
        Returns:
            True if PR is open and CI passed, False otherwise
        """
        return (
            self.state == PRState.OPEN
            and not self.draft
            and self.ci_status == CIStatus.SUCCESS
        )
    
    def update_ci_status(self, status: CIStatus) -> None:
        """
        Update CI status of the PR.
        
        Args:
            status: New CI status
        """
        self.ci_status = status
    
    def mark_as_merged(self, merge_commit_sha: Optional[str] = None) -> None:
        """
        Mark PR as merged.
        
        Args:
            merge_commit_sha: SHA of the merge commit
        """
        self.state = PRState.MERGED
        self.merged_at = datetime.now()
        if merge_commit_sha:
            self.merge_commit_sha = merge_commit_sha
    
    def mark_as_closed(self) -> None:
        """Mark PR as closed without merging."""
        self.state = PRState.CLOSED
        self.closed_at = datetime.now()
    
    def convert_from_draft(self) -> None:
        """Convert PR from draft to ready for review."""
        self.draft = False
        if self.state == PRState.DRAFT:
            self.state = PRState.OPEN


@dataclass
class PRComment:
    """
    Pull Request comment data model.
    
    Represents a comment on a pull request.
    """
    
    comment_id: str
    pr_id: str
    author: str
    body: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_review_comment: bool = False
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert comment to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PRComment":
        """Create comment from dictionary."""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at") and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


@dataclass
class PRMetrics:
    """
    Pull Request metrics data model.
    
    Tracks various metrics for PR analysis and reporting.
    """
    
    pr_id: str
    time_to_merge: Optional[float] = None  # seconds
    review_comment_count: int = 0
    ci_execution_time: Optional[float] = None  # seconds
    commits_count: int = 0
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    review_cycles: int = 0
    time_to_first_review: Optional[float] = None  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PRMetrics":
        """Create metrics from dictionary."""
        return cls(**data)

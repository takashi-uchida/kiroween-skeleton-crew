"""Data models for Repo Pool Manager."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SlotState(Enum):
    """Slot state enumeration."""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    CLEANING = "cleaning"
    ERROR = "error"


@dataclass
class Slot:
    """Workspace slot representation."""
    slot_id: str
    repo_name: str
    repo_url: str
    slot_path: Path
    state: SlotState
    
    # Usage statistics
    allocation_count: int = 0
    total_usage_seconds: int = 0
    last_allocated_at: Optional[datetime] = None
    last_released_at: Optional[datetime] = None
    
    # Git information
    current_branch: Optional[str] = None
    current_commit: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def is_available(self) -> bool:
        """Check if slot is available."""
        return self.state == SlotState.AVAILABLE
    
    def mark_allocated(self, metadata: Optional[Dict] = None) -> None:
        """Mark slot as allocated."""
        self.state = SlotState.ALLOCATED
        self.allocation_count += 1
        self.last_allocated_at = datetime.now()
        self.updated_at = datetime.now()
        if metadata:
            self.metadata.update(metadata)
    
    def mark_released(self) -> None:
        """Mark slot as released."""
        self.state = SlotState.AVAILABLE
        self.last_released_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Calculate usage time if we have allocation time
        if self.last_allocated_at and self.last_released_at:
            usage_seconds = int((self.last_released_at - self.last_allocated_at).total_seconds())
            self.total_usage_seconds += usage_seconds
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "slot_id": self.slot_id,
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "slot_path": str(self.slot_path),
            "state": self.state.value,
            "allocation_count": self.allocation_count,
            "total_usage_seconds": self.total_usage_seconds,
            "last_allocated_at": self.last_allocated_at.isoformat() if self.last_allocated_at else None,
            "last_released_at": self.last_released_at.isoformat() if self.last_released_at else None,
            "current_branch": self.current_branch,
            "current_commit": self.current_commit,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Slot":
        """Create from dictionary."""
        return cls(
            slot_id=data["slot_id"],
            repo_name=data["repo_name"],
            repo_url=data["repo_url"],
            slot_path=Path(data["slot_path"]),
            state=SlotState(data["state"]),
            allocation_count=data.get("allocation_count", 0),
            total_usage_seconds=data.get("total_usage_seconds", 0),
            last_allocated_at=datetime.fromisoformat(data["last_allocated_at"]) if data.get("last_allocated_at") else None,
            last_released_at=datetime.fromisoformat(data["last_released_at"]) if data.get("last_released_at") else None,
            current_branch=data.get("current_branch"),
            current_commit=data.get("current_commit"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class Pool:
    """Repository pool representation."""
    repo_name: str
    repo_url: str
    num_slots: int
    slots: List[Slot]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_available_slots(self) -> List[Slot]:
        """Get available slots."""
        return [slot for slot in self.slots if slot.is_available()]
    
    def get_allocated_slots(self) -> List[Slot]:
        """Get allocated slots."""
        return [slot for slot in self.slots if slot.state == SlotState.ALLOCATED]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "num_slots": self.num_slots,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict, slots: List[Slot]) -> "Pool":
        """Create from dictionary."""
        return cls(
            repo_name=data["repo_name"],
            repo_url=data["repo_url"],
            num_slots=data["num_slots"],
            slots=slots,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SlotStatus:
    """Detailed slot status."""
    slot_id: str
    state: SlotState
    is_locked: bool
    current_branch: Optional[str]
    current_commit: Optional[str]
    allocation_count: int
    last_allocated_at: Optional[datetime]
    disk_usage_mb: float


@dataclass
class PoolSummary:
    """Pool summary statistics."""
    repo_name: str
    total_slots: int
    available_slots: int
    allocated_slots: int
    cleaning_slots: int
    error_slots: int
    total_allocations: int
    average_allocation_time_seconds: float


@dataclass
class CleanupResult:
    """Cleanup operation result."""
    slot_id: str
    success: bool
    duration_seconds: float
    operations: List[str]
    errors: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GitResult:
    """Git operation result."""
    success: bool
    command: str
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float


@dataclass
class AllocationMetrics:
    """Allocation metrics."""
    repo_name: str
    total_allocations: int
    average_allocation_time_seconds: float
    cache_hit_rate: float
    failed_allocations: int

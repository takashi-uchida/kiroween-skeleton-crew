"""
Data models for the Dispatcher component.

Defines core data structures for Agent Pools, Runners, and scheduling policies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class PoolType(Enum):
    """Agent Pool execution type."""
    LOCAL_PROCESS = "local-process"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class RunnerState(Enum):
    """Agent Runner execution state."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SchedulingPolicy(Enum):
    """Task scheduling policy."""
    FIFO = "fifo"  # First In First Out
    PRIORITY = "priority"  # Priority-based
    SKILL_BASED = "skill-based"  # Skill-based routing
    FAIR_SHARE = "fair-share"  # Fair distribution


@dataclass
class AgentPool:
    """
    Agent Pool definition.
    
    Represents a pool of Agent Runners with specific execution type and resource limits.
    """
    name: str
    type: PoolType
    max_concurrency: int
    current_running: int = 0
    
    # Resource quotas
    cpu_quota: Optional[int] = None  # CPU cores
    memory_quota: Optional[int] = None  # MB
    
    # Configuration
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    def can_accept_task(self) -> bool:
        """Check if the pool can accept a new task."""
        return self.enabled and self.current_running < self.max_concurrency
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "max_concurrency": self.max_concurrency,
            "current_running": self.current_running,
            "cpu_quota": self.cpu_quota,
            "memory_quota": self.memory_quota,
            "enabled": self.enabled,
            "config": self.config,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPool":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            type=PoolType(data["type"]),
            max_concurrency=data["max_concurrency"],
            current_running=data.get("current_running", 0),
            cpu_quota=data.get("cpu_quota"),
            memory_quota=data.get("memory_quota"),
            enabled=data.get("enabled", True),
            config=data.get("config", {}),
        )


@dataclass
class Runner:
    """
    Agent Runner information.
    
    Represents a running Agent Runner instance executing a task.
    """
    runner_id: str
    task_id: str
    pool_name: str
    slot_id: str
    state: RunnerState
    started_at: datetime
    pid: Optional[int] = None  # For local process
    container_id: Optional[str] = None  # For Docker
    job_name: Optional[str] = None  # For Kubernetes
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "runner_id": self.runner_id,
            "task_id": self.task_id,
            "pool_name": self.pool_name,
            "slot_id": self.slot_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "pid": self.pid,
            "container_id": self.container_id,
            "job_name": self.job_name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Runner":
        """Deserialize from dictionary."""
        return cls(
            runner_id=data["runner_id"],
            task_id=data["task_id"],
            pool_name=data["pool_name"],
            slot_id=data["slot_id"],
            state=RunnerState(data["state"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            pid=data.get("pid"),
            container_id=data.get("container_id"),
            job_name=data.get("job_name"),
        )


@dataclass
class RunnerInfo:
    """
    Runner monitoring information.
    
    Tracks the runtime state and heartbeat of an Agent Runner.
    """
    runner: Runner
    last_heartbeat: datetime
    state: RunnerState
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "runner": self.runner.to_dict(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "state": self.state.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerInfo":
        """Deserialize from dictionary."""
        return cls(
            runner=Runner.from_dict(data["runner"]),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
            state=RunnerState(data["state"]),
        )


@dataclass
class PoolStatus:
    """
    Agent Pool status information.
    
    Provides current state and resource utilization of an Agent Pool.
    """
    pool_name: str
    type: PoolType
    enabled: bool
    max_concurrency: int
    current_running: int
    utilization: float  # 0.0 - 1.0
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pool_name": self.pool_name,
            "type": self.type.value,
            "enabled": self.enabled,
            "max_concurrency": self.max_concurrency,
            "current_running": self.current_running,
            "utilization": self.utilization,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PoolStatus":
        """Deserialize from dictionary."""
        return cls(
            pool_name=data["pool_name"],
            type=PoolType(data["type"]),
            enabled=data["enabled"],
            max_concurrency=data["max_concurrency"],
            current_running=data["current_running"],
            utilization=data["utilization"],
            cpu_usage=data.get("cpu_usage"),
            memory_usage=data.get("memory_usage"),
        )

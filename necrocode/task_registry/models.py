"""
Data models for Task Registry
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class TaskState(Enum):
    """タスクの状態"""
    READY = "ready"      # 実行可能
    RUNNING = "running"  # 実行中
    BLOCKED = "blocked"  # 依存タスク待ち
    DONE = "done"        # 完了
    FAILED = "failed"    # 失敗


class EventType(Enum):
    """イベントタイプ"""
    TASK_CREATED = "TaskCreated"
    TASK_UPDATED = "TaskUpdated"
    TASK_READY = "TaskReady"
    TASK_ASSIGNED = "TaskAssigned"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"
    RUNNER_STARTED = "RunnerStarted"
    RUNNER_FINISHED = "RunnerFinished"
    PR_OPENED = "PROpened"
    PR_MERGED = "PRMerged"


class ArtifactType(Enum):
    """成果物のタイプ"""
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"


@dataclass
class Artifact:
    """成果物の参照"""
    type: ArtifactType
    uri: str
    size_bytes: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "type": self.type.value,
            "uri": self.uri,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """辞書から復元"""
        return cls(
            type=ArtifactType(data["type"]),
            uri=data["uri"],
            size_bytes=data.get("size_bytes"),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Task:
    """個別タスク"""
    id: str  # 例: "1.1", "2.3"
    title: str
    description: str
    state: TaskState
    dependencies: List[str] = field(default_factory=list)  # 依存タスクのID
    required_skill: Optional[str] = None
    priority: int = 0
    is_optional: bool = False  # tasks.mdの*マーク
    
    # 実行時情報
    assigned_slot: Optional[str] = None
    reserved_branch: Optional[str] = None
    runner_id: Optional[str] = None
    
    # 成果物
    artifacts: List[Artifact] = field(default_factory=list)
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "dependencies": self.dependencies,
            "required_skill": self.required_skill,
            "priority": self.priority,
            "is_optional": self.is_optional,
            "assigned_slot": self.assigned_slot,
            "reserved_branch": self.reserved_branch,
            "runner_id": self.runner_id,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """辞書から復元"""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            state=TaskState(data["state"]),
            dependencies=data.get("dependencies", []),
            required_skill=data.get("required_skill"),
            priority=data.get("priority", 0),
            is_optional=data.get("is_optional", False),
            assigned_slot=data.get("assigned_slot"),
            reserved_branch=data.get("reserved_branch"),
            runner_id=data.get("runner_id"),
            artifacts=[
                Artifact.from_dict(artifact_data)
                for artifact_data in data.get("artifacts", [])
            ],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class Taskset:
    """タスクセット"""
    spec_name: str
    version: int
    tasks: List[Task]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "spec_name": self.spec_name,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tasks": [task.to_dict() for task in self.tasks],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Taskset":
        """辞書から復元"""
        return cls(
            spec_name=data["spec_name"],
            version=data["version"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            tasks=[Task.from_dict(task_data) for task_data in data["tasks"]],
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskEvent:
    """タスクイベント"""
    event_type: EventType
    spec_name: str
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_jsonl(self) -> str:
        """JSON Lines形式に変換"""
        data = {
            "event_type": self.event_type.value,
            "spec_name": self.spec_name,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_jsonl(cls, line: str) -> "TaskEvent":
        """JSON Lines形式から復元"""
        data = json.loads(line)
        return cls(
            event_type=EventType(data["event_type"]),
            spec_name=data["spec_name"],
            task_id=data["task_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data.get("details", {}),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "event_type": self.event_type.value,
            "spec_name": self.spec_name,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskEvent":
        """辞書から復元"""
        return cls(
            event_type=EventType(data["event_type"]),
            spec_name=data["spec_name"],
            task_id=data["task_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data.get("details", {}),
        )

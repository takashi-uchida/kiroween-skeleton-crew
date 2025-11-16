"""Unit tests for Task Registry data models.

Tests serialization/deserialization of Taskset, Task, and TaskEvent models.
Requirements: 1.1
"""

import json
from datetime import datetime
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.models import (
    Task,
    TaskState,
    Taskset,
    TaskEvent,
    EventType,
    Artifact,
    ArtifactType,
)


# ============================================================================
# Task Model Tests
# ============================================================================

def test_task_creation():
    """Test basic Task creation."""
    task = Task(
        id="1.1",
        title="Test Task",
        description="Test description",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    assert task.id == "1.1"
    assert task.title == "Test Task"
    assert task.state == TaskState.READY
    assert task.required_skill == "backend"
    assert task.priority == 1
    assert not task.is_optional


def test_task_to_dict():
    """Test Task serialization to dictionary."""
    task = Task(
        id="1.1",
        title="Test Task",
        description="Test description",
        state=TaskState.READY,
        dependencies=["1.0"],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    task_dict = task.to_dict()
    
    assert task_dict["id"] == "1.1"
    assert task_dict["title"] == "Test Task"
    assert task_dict["state"] == "ready"
    assert task_dict["dependencies"] == ["1.0"]
    assert task_dict["required_skill"] == "backend"
    assert task_dict["priority"] == 1
    assert task_dict["is_optional"] is False


def test_task_from_dict():
    """Test Task deserialization from dictionary."""
    task_dict = {
        "id": "1.1",
        "title": "Test Task",
        "description": "Test description",
        "state": "ready",
        "dependencies": ["1.0"],
        "required_skill": "backend",
        "priority": 1,
        "is_optional": False,
        "assigned_slot": None,
        "reserved_branch": None,
        "runner_id": None,
        "artifacts": [],
        "metadata": {},
        "created_at": "2025-11-15T10:00:00",
        "updated_at": "2025-11-15T10:00:00",
    }
    
    task = Task.from_dict(task_dict)
    
    assert task.id == "1.1"
    assert task.title == "Test Task"
    assert task.state == TaskState.READY
    assert task.dependencies == ["1.0"]
    assert task.required_skill == "backend"


def test_task_with_artifacts():
    """Test Task with artifacts."""
    artifact = Artifact(
        type=ArtifactType.DIFF,
        uri="file://test.diff",
        size_bytes=1024,
    )
    
    task = Task(
        id="1.1",
        title="Test Task",
        description="Test description",
        state=TaskState.DONE,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
        artifacts=[artifact],
    )
    
    assert len(task.artifacts) == 1
    assert task.artifacts[0].type == ArtifactType.DIFF
    assert task.artifacts[0].uri == "file://test.diff"


def test_task_serialization_roundtrip():
    """Test Task serialization and deserialization roundtrip."""
    original_task = Task(
        id="2.3",
        title="Complex Task",
        description="Complex description",
        state=TaskState.RUNNING,
        dependencies=["2.1", "2.2"],
        required_skill="frontend",
        priority=2,
        is_optional=True,
        assigned_slot="slot-1",
        reserved_branch="feature/task-2.3",
        runner_id="runner-1",
        metadata={"key": "value"},
    )
    
    # Serialize
    task_dict = original_task.to_dict()
    
    # Deserialize
    restored_task = Task.from_dict(task_dict)
    
    # Verify
    assert restored_task.id == original_task.id
    assert restored_task.title == original_task.title
    assert restored_task.state == original_task.state
    assert restored_task.dependencies == original_task.dependencies
    assert restored_task.assigned_slot == original_task.assigned_slot
    assert restored_task.reserved_branch == original_task.reserved_branch
    assert restored_task.runner_id == original_task.runner_id
    assert restored_task.metadata == original_task.metadata


# ============================================================================
# Taskset Model Tests
# ============================================================================

def test_taskset_creation():
    """Test basic Taskset creation."""
    task1 = Task(
        id="1.1",
        title="Task 1",
        description="Description 1",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    taskset = Taskset(
        spec_name="test-spec",
        version=1,
        tasks=[task1],
        metadata={"key": "value"},
    )
    
    assert taskset.spec_name == "test-spec"
    assert taskset.version == 1
    assert len(taskset.tasks) == 1
    assert taskset.metadata["key"] == "value"


def test_taskset_to_dict():
    """Test Taskset serialization to dictionary."""
    task1 = Task(
        id="1.1",
        title="Task 1",
        description="Description 1",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    taskset = Taskset(
        spec_name="test-spec",
        version=1,
        tasks=[task1],
        metadata={"key": "value"},
    )
    
    taskset_dict = taskset.to_dict()
    
    assert taskset_dict["spec_name"] == "test-spec"
    assert taskset_dict["version"] == 1
    assert len(taskset_dict["tasks"]) == 1
    assert taskset_dict["tasks"][0]["id"] == "1.1"
    assert taskset_dict["metadata"]["key"] == "value"


def test_taskset_from_dict():
    """Test Taskset deserialization from dictionary."""
    taskset_dict = {
        "spec_name": "test-spec",
        "version": 1,
        "created_at": "2025-11-15T10:00:00",
        "updated_at": "2025-11-15T10:00:00",
        "tasks": [
            {
                "id": "1.1",
                "title": "Task 1",
                "description": "Description 1",
                "state": "ready",
                "dependencies": [],
                "required_skill": "backend",
                "priority": 1,
                "is_optional": False,
                "assigned_slot": None,
                "reserved_branch": None,
                "runner_id": None,
                "artifacts": [],
                "metadata": {},
                "created_at": "2025-11-15T10:00:00",
                "updated_at": "2025-11-15T10:00:00",
            }
        ],
        "metadata": {"key": "value"},
    }
    
    taskset = Taskset.from_dict(taskset_dict)
    
    assert taskset.spec_name == "test-spec"
    assert taskset.version == 1
    assert len(taskset.tasks) == 1
    assert taskset.tasks[0].id == "1.1"
    assert taskset.metadata["key"] == "value"


def test_taskset_serialization_roundtrip():
    """Test Taskset serialization and deserialization roundtrip."""
    task1 = Task(
        id="1.1",
        title="Task 1",
        description="Description 1",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    task2 = Task(
        id="1.2",
        title="Task 2",
        description="Description 2",
        state=TaskState.BLOCKED,
        dependencies=["1.1"],
        required_skill="frontend",
        priority=2,
        is_optional=True,
    )
    
    original_taskset = Taskset(
        spec_name="test-spec",
        version=2,
        tasks=[task1, task2],
        metadata={"kiro_spec_path": ".kiro/specs/test-spec/tasks.md"},
    )
    
    # Serialize
    taskset_dict = original_taskset.to_dict()
    
    # Deserialize
    restored_taskset = Taskset.from_dict(taskset_dict)
    
    # Verify
    assert restored_taskset.spec_name == original_taskset.spec_name
    assert restored_taskset.version == original_taskset.version
    assert len(restored_taskset.tasks) == len(original_taskset.tasks)
    assert restored_taskset.tasks[0].id == original_taskset.tasks[0].id
    assert restored_taskset.tasks[1].dependencies == original_taskset.tasks[1].dependencies
    assert restored_taskset.metadata == original_taskset.metadata


def test_taskset_json_serialization():
    """Test Taskset JSON serialization."""
    task1 = Task(
        id="1.1",
        title="Task 1",
        description="Description 1",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    taskset = Taskset(
        spec_name="test-spec",
        version=1,
        tasks=[task1],
        metadata={},
    )
    
    # Serialize to JSON
    json_str = json.dumps(taskset.to_dict(), indent=2)
    
    # Deserialize from JSON
    taskset_dict = json.loads(json_str)
    restored_taskset = Taskset.from_dict(taskset_dict)
    
    # Verify
    assert restored_taskset.spec_name == taskset.spec_name
    assert restored_taskset.version == taskset.version
    assert len(restored_taskset.tasks) == len(taskset.tasks)


# ============================================================================
# TaskEvent Model Tests
# ============================================================================

def test_task_event_creation():
    """Test basic TaskEvent creation."""
    event = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={"title": "Test Task"},
    )
    
    assert event.event_type == EventType.TASK_CREATED
    assert event.spec_name == "test-spec"
    assert event.task_id == "1.1"
    assert event.details["title"] == "Test Task"


def test_task_event_to_dict():
    """Test TaskEvent serialization to dictionary."""
    event = TaskEvent(
        event_type=EventType.TASK_ASSIGNED,
        spec_name="test-spec",
        task_id="1.1",
        details={"runner_id": "runner-1", "slot": "slot-1"},
    )
    
    event_dict = event.to_dict()
    
    assert event_dict["event_type"] == "TaskAssigned"
    assert event_dict["spec_name"] == "test-spec"
    assert event_dict["task_id"] == "1.1"
    assert event_dict["details"]["runner_id"] == "runner-1"


def test_task_event_from_dict():
    """Test TaskEvent deserialization from dictionary."""
    event_dict = {
        "event_type": "TaskCompleted",
        "spec_name": "test-spec",
        "task_id": "1.1",
        "timestamp": "2025-11-15T10:00:00",
        "details": {"duration_seconds": 120},
    }
    
    event = TaskEvent.from_dict(event_dict)
    
    assert event.event_type == EventType.TASK_COMPLETED
    assert event.spec_name == "test-spec"
    assert event.task_id == "1.1"
    assert event.details["duration_seconds"] == 120


def test_task_event_to_jsonl():
    """Test TaskEvent JSON Lines serialization."""
    event = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={"title": "Test Task"},
    )
    
    jsonl_str = event.to_jsonl()
    
    # Should be valid JSON
    event_dict = json.loads(jsonl_str)
    assert event_dict["event_type"] == "TaskCreated"
    assert event_dict["spec_name"] == "test-spec"
    assert event_dict["task_id"] == "1.1"


def test_task_event_serialization_roundtrip():
    """Test TaskEvent serialization and deserialization roundtrip."""
    original_event = TaskEvent(
        event_type=EventType.RUNNER_STARTED,
        spec_name="test-spec",
        task_id="2.3",
        details={"runner_id": "runner-backend-1", "slot": "workspace-slot-1"},
    )
    
    # Serialize
    event_dict = original_event.to_dict()
    
    # Deserialize
    restored_event = TaskEvent.from_dict(event_dict)
    
    # Verify
    assert restored_event.event_type == original_event.event_type
    assert restored_event.spec_name == original_event.spec_name
    assert restored_event.task_id == original_event.task_id
    assert restored_event.details == original_event.details


# ============================================================================
# Artifact Model Tests
# ============================================================================

def test_artifact_creation():
    """Test basic Artifact creation."""
    artifact = Artifact(
        type=ArtifactType.DIFF,
        uri="file://test.diff",
        size_bytes=1024,
    )
    
    assert artifact.type == ArtifactType.DIFF
    assert artifact.uri == "file://test.diff"
    assert artifact.size_bytes == 1024


def test_artifact_to_dict():
    """Test Artifact serialization to dictionary."""
    artifact = Artifact(
        type=ArtifactType.LOG,
        uri="file://test.log",
        size_bytes=2048,
        metadata={"encoding": "utf-8"},
    )
    
    artifact_dict = artifact.to_dict()
    
    assert artifact_dict["type"] == "log"
    assert artifact_dict["uri"] == "file://test.log"
    assert artifact_dict["size_bytes"] == 2048
    assert artifact_dict["metadata"]["encoding"] == "utf-8"


def test_artifact_from_dict():
    """Test Artifact deserialization from dictionary."""
    artifact_dict = {
        "type": "test",
        "uri": "file://test_results.json",
        "size_bytes": 512,
        "created_at": "2025-11-15T10:00:00",
        "metadata": {"passed": 10, "failed": 0},
    }
    
    artifact = Artifact.from_dict(artifact_dict)
    
    assert artifact.type == ArtifactType.TEST_RESULT
    assert artifact.uri == "file://test_results.json"
    assert artifact.size_bytes == 512
    assert artifact.metadata["passed"] == 10


def test_artifact_serialization_roundtrip():
    """Test Artifact serialization and deserialization roundtrip."""
    original_artifact = Artifact(
        type=ArtifactType.DIFF,
        uri="file://changes.diff",
        size_bytes=4096,
        metadata={"lines_added": 50, "lines_removed": 20},
    )
    
    # Serialize
    artifact_dict = original_artifact.to_dict()
    
    # Deserialize
    restored_artifact = Artifact.from_dict(artifact_dict)
    
    # Verify
    assert restored_artifact.type == original_artifact.type
    assert restored_artifact.uri == original_artifact.uri
    assert restored_artifact.size_bytes == original_artifact.size_bytes
    assert restored_artifact.metadata == original_artifact.metadata


# ============================================================================
# TaskState Enum Tests
# ============================================================================

def test_task_state_values():
    """Test TaskState enum values."""
    assert TaskState.READY.value == "ready"
    assert TaskState.RUNNING.value == "running"
    assert TaskState.BLOCKED.value == "blocked"
    assert TaskState.DONE.value == "done"
    assert TaskState.FAILED.value == "failed"


def test_task_state_from_string():
    """Test TaskState creation from string."""
    assert TaskState("ready") == TaskState.READY
    assert TaskState("running") == TaskState.RUNNING
    assert TaskState("blocked") == TaskState.BLOCKED
    assert TaskState("done") == TaskState.DONE
    assert TaskState("failed") == TaskState.FAILED


# ============================================================================
# EventType Enum Tests
# ============================================================================

def test_event_type_values():
    """Test EventType enum values."""
    assert EventType.TASK_CREATED.value == "TaskCreated"
    assert EventType.TASK_UPDATED.value == "TaskUpdated"
    assert EventType.TASK_READY.value == "TaskReady"
    assert EventType.TASK_ASSIGNED.value == "TaskAssigned"
    assert EventType.TASK_COMPLETED.value == "TaskCompleted"
    assert EventType.TASK_FAILED.value == "TaskFailed"


def test_event_type_from_string():
    """Test EventType creation from string."""
    assert EventType("TaskCreated") == EventType.TASK_CREATED
    assert EventType("TaskAssigned") == EventType.TASK_ASSIGNED
    assert EventType("TaskCompleted") == EventType.TASK_COMPLETED


# ============================================================================
# ArtifactType Enum Tests
# ============================================================================

def test_artifact_type_values():
    """Test ArtifactType enum values."""
    assert ArtifactType.DIFF.value == "diff"
    assert ArtifactType.LOG.value == "log"
    assert ArtifactType.TEST_RESULT.value == "test"


def test_artifact_type_from_string():
    """Test ArtifactType creation from string."""
    assert ArtifactType("diff") == ArtifactType.DIFF
    assert ArtifactType("log") == ArtifactType.LOG
    assert ArtifactType("test") == ArtifactType.TEST_RESULT

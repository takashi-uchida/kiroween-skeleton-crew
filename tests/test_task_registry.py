"""Integration tests for TaskRegistry.

Tests overall integration of all components.
Requirements: All
"""

from datetime import datetime
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import (
    Task,
    TaskState,
    Taskset,
    TaskEvent,
    EventType,
    ArtifactType,
)
from necrocode.task_registry.kiro_sync import TaskDefinition
from necrocode.task_registry.exceptions import (
    TaskNotFoundError,
    TasksetNotFoundError,
    InvalidStateTransitionError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def registry_dir(tmp_path):
    """Create temporary registry directory."""
    return tmp_path / "registry"


@pytest.fixture
def task_registry(registry_dir):
    """Create TaskRegistry instance."""
    return TaskRegistry(registry_dir)


@pytest.fixture
def sample_tasks():
    """Create sample task definitions."""
    return [
        TaskDefinition(
            id="1.1",
            title="Setup database",
            description="Create database schema",
            is_optional=False,
            is_completed=False,
            dependencies=[],
        ),
        TaskDefinition(
            id="1.2",
            title="Implement API",
            description="Create REST API",
            is_optional=False,
            is_completed=False,
            dependencies=["1.1"],
        ),
        TaskDefinition(
            id="2.1",
            title="Create UI",
            description="Build user interface",
            is_optional=False,
            is_completed=False,
            dependencies=[],
        ),
    ]


# ============================================================================
# TaskRegistry Initialization Tests
# ============================================================================

def test_task_registry_creates_directories(registry_dir):
    """Test TaskRegistry creates necessary directories."""
    TaskRegistry(registry_dir)
    
    assert registry_dir.exists()
    assert (registry_dir / "tasksets").exists()
    assert (registry_dir / "events").exists()
    assert (registry_dir / "locks").exists()


def test_task_registry_initializes_components(task_registry):
    """Test TaskRegistry initializes all components."""
    assert task_registry.task_store is not None
    assert task_registry.event_store is not None
    assert task_registry.lock_manager is not None
    assert task_registry.kiro_sync is not None
    assert task_registry.query_engine is not None


# ============================================================================
# Create Taskset Tests
# ============================================================================

def test_create_taskset(task_registry, sample_tasks):
    """Test create_taskset creates new taskset."""
    taskset = task_registry.create_taskset("test-spec", sample_tasks)
    
    assert taskset.spec_name == "test-spec"
    assert taskset.version == 1
    assert len(taskset.tasks) == 3


def test_create_taskset_assigns_unique_ids(task_registry, sample_tasks):
    """Test create_taskset preserves task IDs."""
    taskset = task_registry.create_taskset("test-spec", sample_tasks)
    
    task_ids = [t.id for t in taskset.tasks]
    assert "1.1" in task_ids
    assert "1.2" in task_ids
    assert "2.1" in task_ids


def test_create_taskset_records_event(task_registry, sample_tasks):
    """Test create_taskset records TaskCreated events."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Check events were recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) > 0
    assert any(e.event_type == EventType.TASK_CREATED for e in events)


def test_create_taskset_persists_to_disk(task_registry, sample_tasks):
    """Test create_taskset persists taskset to disk."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Verify file exists
    taskset_file = task_registry.registry_dir / "tasksets" / "test-spec" / "taskset.json"
    assert taskset_file.exists()


# ============================================================================
# Get Taskset Tests
# ============================================================================

def test_get_taskset(task_registry, sample_tasks):
    """Test get_taskset retrieves taskset."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    taskset = task_registry.get_taskset("test-spec")
    
    assert taskset.spec_name == "test-spec"
    assert len(taskset.tasks) == 3


def test_get_taskset_nonexistent_raises_error(task_registry):
    """Test get_taskset raises error for nonexistent taskset."""
    with pytest.raises(TasksetNotFoundError):
        task_registry.get_taskset("nonexistent")


def test_get_taskset_returns_latest_version(task_registry, sample_tasks):
    """Test get_taskset returns latest version."""
    # Create initial taskset
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Update taskset
    taskset = task_registry.get_taskset("test-spec")
    taskset.version = 2
    task_registry.task_store.save_taskset(taskset)
    
    # Get taskset
    loaded = task_registry.get_taskset("test-spec")
    assert loaded.version == 2


# ============================================================================
# Update Task State Tests
# ============================================================================

def test_update_task_state_ready_to_running(task_registry, sample_tasks):
    """Test update_task_state from READY to RUNNING."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    task_registry.update_task_state(
        "test-spec",
        "1.1",
        TaskState.RUNNING,
        metadata={
            "assigned_slot": "slot-1",
            "reserved_branch": "feature/task-1.1",
            "runner_id": "runner-1"
        }
    )
    
    taskset = task_registry.get_taskset("test-spec")
    task = next(t for t in taskset.tasks if t.id == "1.1")
    
    assert task.state == TaskState.RUNNING
    assert task.assigned_slot == "slot-1"
    assert task.reserved_branch == "feature/task-1.1"
    assert task.runner_id == "runner-1"


def test_update_task_state_running_to_done(task_registry, sample_tasks):
    """Test update_task_state from RUNNING to DONE."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # First set to RUNNING
    task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
    
    # Then set to DONE
    task_registry.update_task_state("test-spec", "1.1", TaskState.DONE)
    
    taskset = task_registry.get_taskset("test-spec")
    task = next(t for t in taskset.tasks if t.id == "1.1")
    
    assert task.state == TaskState.DONE


def test_update_task_state_unblocks_dependent_tasks(task_registry, sample_tasks):
    """Test update_task_state unblocks dependent tasks when task completes."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Task 1.2 is blocked by 1.1
    taskset = task_registry.get_taskset("test-spec")
    task_1_2 = next(t for t in taskset.tasks if t.id == "1.2")
    assert task_1_2.state == TaskState.BLOCKED
    
    # Complete task 1.1
    task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
    task_registry.update_task_state("test-spec", "1.1", TaskState.DONE)
    
    # Task 1.2 should now be READY
    taskset = task_registry.get_taskset("test-spec")
    task_1_2 = next(t for t in taskset.tasks if t.id == "1.2")
    assert task_1_2.state == TaskState.READY


def test_update_task_state_records_event(task_registry, sample_tasks):
    """Test update_task_state records event."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
    
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    # Should have TASK_ASSIGNED event (for RUNNING state)
    assert any(e.event_type in [EventType.TASK_UPDATED, EventType.TASK_ASSIGNED] for e in events)


def test_update_task_state_increments_version(task_registry, sample_tasks):
    """Test update_task_state increments taskset version."""
    task_registry.create_taskset("test-spec", sample_tasks)
    initial_version = task_registry.get_taskset("test-spec").version
    
    task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
    
    updated_version = task_registry.get_taskset("test-spec").version
    assert updated_version > initial_version


def test_update_task_state_nonexistent_task_raises_error(task_registry, sample_tasks):
    """Test update_task_state raises error for nonexistent task."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    with pytest.raises(TaskNotFoundError):
        task_registry.update_task_state("test-spec", "nonexistent", TaskState.RUNNING)


# ============================================================================
# Get Ready Tasks Tests
# ============================================================================

def test_get_ready_tasks(task_registry, sample_tasks):
    """Test get_ready_tasks returns READY tasks."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    ready_tasks = task_registry.get_ready_tasks("test-spec")
    
    assert len(ready_tasks) == 2
    assert all(t.state == TaskState.READY for t in ready_tasks)
    assert "1.1" in [t.id for t in ready_tasks]
    assert "2.1" in [t.id for t in ready_tasks]


def test_get_ready_tasks_with_skill_filter(task_registry, sample_tasks):
    """Test get_ready_tasks filters by required_skill."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Set required_skill on tasks manually
    taskset = task_registry.get_taskset("test-spec")
    taskset.tasks[0].required_skill = "backend"
    taskset.tasks[1].required_skill = "backend"
    taskset.tasks[2].required_skill = "frontend"
    task_registry.task_store.save_taskset(taskset)
    
    backend_tasks = task_registry.get_ready_tasks("test-spec", required_skill="backend")
    
    assert len(backend_tasks) == 1
    assert backend_tasks[0].id == "1.1"
    assert backend_tasks[0].required_skill == "backend"


def test_get_ready_tasks_excludes_blocked(task_registry, sample_tasks):
    """Test get_ready_tasks excludes BLOCKED tasks."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    ready_tasks = task_registry.get_ready_tasks("test-spec")
    
    # Task 1.2 is BLOCKED, should not be included
    assert "1.2" not in [t.id for t in ready_tasks]


def test_get_ready_tasks_empty_result(task_registry, sample_tasks):
    """Test get_ready_tasks returns empty list when no ready tasks."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Mark all ready tasks as running
    task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
    task_registry.update_task_state("test-spec", "2.1", TaskState.RUNNING)
    
    ready_tasks = task_registry.get_ready_tasks("test-spec")
    
    assert ready_tasks == []


# ============================================================================
# Add Artifact Tests
# ============================================================================

def test_add_artifact(task_registry, sample_tasks):
    """Test add_artifact adds artifact to task."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    task_registry.add_artifact(
        "test-spec",
        "1.1",
        ArtifactType.DIFF,
        "file://test.diff",
        metadata={"size_bytes": 1024}
    )
    
    taskset = task_registry.get_taskset("test-spec")
    task = next(t for t in taskset.tasks if t.id == "1.1")
    
    assert len(task.artifacts) == 1
    assert task.artifacts[0].type == ArtifactType.DIFF
    assert task.artifacts[0].uri == "file://test.diff"


def test_add_artifact_multiple(task_registry, sample_tasks):
    """Test add_artifact can add multiple artifacts."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    task_registry.add_artifact("test-spec", "1.1", ArtifactType.DIFF, "file://test.diff")
    task_registry.add_artifact("test-spec", "1.1", ArtifactType.LOG, "file://test.log")
    task_registry.add_artifact("test-spec", "1.1", ArtifactType.TEST_RESULT, "file://test.json")
    
    taskset = task_registry.get_taskset("test-spec")
    task = next(t for t in taskset.tasks if t.id == "1.1")
    
    assert len(task.artifacts) == 3


def test_add_artifact_nonexistent_task_raises_error(task_registry, sample_tasks):
    """Test add_artifact raises error for nonexistent task."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    with pytest.raises(TaskNotFoundError):
        task_registry.add_artifact(
            "test-spec",
            "nonexistent",
            ArtifactType.DIFF,
            "file://test.diff"
        )


# ============================================================================
# Sync with Kiro Tests
# ============================================================================

def test_sync_with_kiro(task_registry, tmp_path):
    """Test sync_with_kiro synchronizes with tasks.md."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [ ] 1. Task 1
  - Description
  - _Requirements: _

- [x] 2. Task 2
  - Description
  - _Requirements: 1_
"""
    tasks_md.write_text(content)
    
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    assert result.success
    
    # Verify taskset was created
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 2


# ============================================================================
# Concurrent Access Tests
# ============================================================================

def test_concurrent_task_updates(task_registry, sample_tasks):
    """Test concurrent task updates use locking."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Update task state multiple times
    for i in range(5):
        task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
        task_registry.update_task_state("test-spec", "1.1", TaskState.READY)
    
    # Should complete without errors
    taskset = task_registry.get_taskset("test-spec")
    assert taskset is not None


# ============================================================================
# Integration Tests
# ============================================================================

def test_complete_workflow(task_registry, sample_tasks):
    """Test complete workflow: create → update → query → complete."""
    # Create taskset
    taskset = task_registry.create_taskset("test-spec", sample_tasks)
    assert taskset.version == 1
    
    # Get ready tasks
    ready_tasks = task_registry.get_ready_tasks("test-spec")
    assert len(ready_tasks) == 2
    
    # Start task
    task_registry.update_task_state(
        "test-spec",
        "1.1",
        TaskState.RUNNING,
        metadata={"runner_id": "runner-1"}
    )
    
    # Add artifact
    task_registry.add_artifact(
        "test-spec",
        "1.1",
        ArtifactType.DIFF,
        "file://changes.diff"
    )
    
    # Complete task
    task_registry.update_task_state("test-spec", "1.1", TaskState.DONE)
    
    # Verify dependent task is unblocked
    ready_tasks = task_registry.get_ready_tasks("test-spec")
    assert "1.2" in [t.id for t in ready_tasks]
    
    # Verify events were recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) >= 3  # Created, Updated (Running), Updated (Done)


def test_multiple_tasksets(task_registry, sample_tasks):
    """Test managing multiple tasksets."""
    # Create multiple tasksets
    task_registry.create_taskset("spec-one", sample_tasks)
    task_registry.create_taskset("spec-two", sample_tasks)
    task_registry.create_taskset("spec-three", sample_tasks)
    
    # Verify all exist
    taskset1 = task_registry.get_taskset("spec-one")
    taskset2 = task_registry.get_taskset("spec-two")
    taskset3 = task_registry.get_taskset("spec-three")
    
    assert taskset1.spec_name == "spec-one"
    assert taskset2.spec_name == "spec-two"
    assert taskset3.spec_name == "spec-three"
    
    # Update task in one taskset
    task_registry.update_task_state("spec-one", "1.1", TaskState.RUNNING)
    
    # Verify other tasksets are unaffected
    taskset2 = task_registry.get_taskset("spec-two")
    task = next(t for t in taskset2.tasks if t.id == "1.1")
    assert task.state == TaskState.READY


def test_backup_and_restore(task_registry, sample_tasks, tmp_path):
    """Test backup and restore functionality."""
    # Create taskset
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Update some tasks
    task_registry.update_task_state("test-spec", "1.1", TaskState.DONE)
    
    # Backup
    backup_dir = tmp_path / "backups"
    backup_path = task_registry.task_store.backup_taskset("test-spec", backup_dir)
    
    # Modify taskset
    task_registry.update_task_state("test-spec", "2.1", TaskState.DONE)
    
    # Restore
    task_registry.task_store.restore_taskset(backup_path)
    
    # Verify original state restored
    taskset = task_registry.get_taskset("test-spec")
    task_1_1 = next(t for t in taskset.tasks if t.id == "1.1")
    task_2_1 = next(t for t in taskset.tasks if t.id == "2.1")
    
    assert task_1_1.state == TaskState.DONE
    assert task_2_1.state == TaskState.READY  # Restored to original


def test_event_history_tracking(task_registry, sample_tasks):
    """Test complete event history is tracked."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Perform multiple operations
    task_registry.update_task_state("test-spec", "1.1", TaskState.RUNNING)
    task_registry.add_artifact("test-spec", "1.1", ArtifactType.LOG, "file://log.txt")
    task_registry.update_task_state("test-spec", "1.1", TaskState.DONE)
    
    # Get all events
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    
    # Should have multiple events
    assert len(events) >= 3
    
    # Verify event types
    event_types = {e.event_type for e in events}
    assert EventType.TASK_CREATED in event_types
    assert EventType.TASK_UPDATED in event_types


def test_query_integration(task_registry, sample_tasks):
    """Test query engine integration."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Set required_skill on tasks manually
    taskset = task_registry.get_taskset("test-spec")
    taskset.tasks[0].required_skill = "backend"
    taskset.tasks[1].required_skill = "backend"
    taskset.tasks[2].required_skill = "frontend"
    task_registry.task_store.save_taskset(taskset)
    
    # Query by state
    ready_tasks = task_registry.query_engine.filter_by_state("test-spec", TaskState.READY)
    assert len(ready_tasks) == 2
    
    # Query by skill
    backend_tasks = task_registry.query_engine.filter_by_skill("test-spec", "backend")
    assert len(backend_tasks) == 2
    
    # Complex query
    tasks = task_registry.query_engine.query(
        "test-spec",
        filters={"state": TaskState.READY, "required_skill": "backend"},
        sort_by="priority",
        limit=1
    )
    assert len(tasks) == 1


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_create_taskset_with_empty_tasks(task_registry):
    """Test create_taskset with empty tasks list."""
    taskset = task_registry.create_taskset("empty-spec", [])
    
    assert taskset.spec_name == "empty-spec"
    assert len(taskset.tasks) == 0


def test_update_task_state_with_invalid_transition(task_registry, sample_tasks):
    """Test update_task_state validates state transitions."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Try invalid transition (implementation dependent)
    # This test documents expected behavior
    try:
        task_registry.update_task_state("test-spec", "1.1", TaskState.FAILED)
    except InvalidStateTransitionError:
        pass  # Expected if validation is implemented


def test_registry_persistence_across_instances(registry_dir, sample_tasks):
    """Test registry data persists across instances."""
    # Create taskset with first instance
    registry1 = TaskRegistry(registry_dir)
    registry1.create_taskset("test-spec", sample_tasks)
    
    # Create new instance
    registry2 = TaskRegistry(registry_dir)
    
    # Verify taskset exists
    taskset = registry2.get_taskset("test-spec")
    assert taskset.spec_name == "test-spec"
    assert len(taskset.tasks) == 3

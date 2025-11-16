"""Unit tests for TaskStore.

Tests save, load, backup, and restore functionality.
Requirements: 1.1, 1.3, 9.1, 9.2
"""

import json
from datetime import datetime
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.task_store import TaskStore
from necrocode.task_registry.models import Task, TaskState, Taskset
from necrocode.task_registry.exceptions import TasksetNotFoundError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def storage_dir(tmp_path):
    """Create temporary storage directory."""
    return tmp_path / "tasksets"


@pytest.fixture
def task_store(storage_dir):
    """Create TaskStore instance."""
    return TaskStore(storage_dir)


@pytest.fixture
def sample_task():
    """Create sample Task."""
    return Task(
        id="1.1",
        title="Test Task",
        description="Test description",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )


@pytest.fixture
def sample_taskset(sample_task):
    """Create sample Taskset."""
    return Taskset(
        spec_name="test-spec",
        version=1,
        tasks=[sample_task],
        metadata={"key": "value"},
    )


# ============================================================================
# TaskStore Initialization Tests
# ============================================================================

def test_task_store_creates_storage_dir(storage_dir):
    """Test TaskStore creates storage directory if it doesn't exist."""
    assert not storage_dir.exists()
    
    TaskStore(storage_dir)
    
    assert storage_dir.exists()
    assert storage_dir.is_dir()


def test_task_store_uses_existing_storage_dir(storage_dir):
    """Test TaskStore uses existing storage directory."""
    storage_dir.mkdir(parents=True)
    test_file = storage_dir / "test.txt"
    test_file.write_text("test")
    
    TaskStore(storage_dir)
    
    assert storage_dir.exists()
    assert test_file.exists()


# ============================================================================
# Save Taskset Tests
# ============================================================================

def test_save_taskset_creates_spec_directory(task_store, sample_taskset):
    """Test save_taskset creates spec directory."""
    task_store.save_taskset(sample_taskset)
    
    spec_dir = task_store.storage_dir / "test-spec"
    assert spec_dir.exists()
    assert spec_dir.is_dir()


def test_save_taskset_creates_json_file(task_store, sample_taskset):
    """Test save_taskset creates taskset.json file."""
    task_store.save_taskset(sample_taskset)
    
    taskset_file = task_store.storage_dir / "test-spec" / "taskset.json"
    assert taskset_file.exists()
    assert taskset_file.is_file()


def test_save_taskset_writes_valid_json(task_store, sample_taskset):
    """Test save_taskset writes valid JSON."""
    task_store.save_taskset(sample_taskset)
    
    taskset_file = task_store.storage_dir / "test-spec" / "taskset.json"
    with open(taskset_file, "r") as f:
        data = json.load(f)
    
    assert data["spec_name"] == "test-spec"
    assert data["version"] == 1
    assert len(data["tasks"]) == 1


def test_save_taskset_overwrites_existing(task_store, sample_taskset):
    """Test save_taskset overwrites existing taskset."""
    # Save first version
    task_store.save_taskset(sample_taskset)
    
    # Modify and save again
    sample_taskset.version = 2
    sample_taskset.tasks[0].state = TaskState.DONE
    task_store.save_taskset(sample_taskset)
    
    # Load and verify
    loaded = task_store.load_taskset("test-spec")
    assert loaded.version == 2
    assert loaded.tasks[0].state == TaskState.DONE


# ============================================================================
# Load Taskset Tests
# ============================================================================

def test_load_taskset_returns_taskset(task_store, sample_taskset):
    """Test load_taskset returns Taskset object."""
    task_store.save_taskset(sample_taskset)
    
    loaded = task_store.load_taskset("test-spec")
    
    assert isinstance(loaded, Taskset)
    assert loaded.spec_name == "test-spec"


def test_load_taskset_preserves_data(task_store, sample_taskset):
    """Test load_taskset preserves all data."""
    task_store.save_taskset(sample_taskset)
    
    loaded = task_store.load_taskset("test-spec")
    
    assert loaded.spec_name == sample_taskset.spec_name
    assert loaded.version == sample_taskset.version
    assert len(loaded.tasks) == len(sample_taskset.tasks)
    assert loaded.tasks[0].id == sample_taskset.tasks[0].id
    assert loaded.tasks[0].title == sample_taskset.tasks[0].title
    assert loaded.metadata == sample_taskset.metadata


def test_load_taskset_nonexistent_raises_error(task_store):
    """Test load_taskset raises error for nonexistent taskset."""
    with pytest.raises(TasksetNotFoundError) as exc_info:
        task_store.load_taskset("nonexistent")
    
    assert "nonexistent" in str(exc_info.value)


def test_load_taskset_with_multiple_tasks(task_store):
    """Test load_taskset with multiple tasks."""
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
    
    taskset = Taskset(
        spec_name="multi-task-spec",
        version=1,
        tasks=[task1, task2],
        metadata={},
    )
    
    task_store.save_taskset(taskset)
    loaded = task_store.load_taskset("multi-task-spec")
    
    assert len(loaded.tasks) == 2
    assert loaded.tasks[0].id == "1.1"
    assert loaded.tasks[1].id == "1.2"
    assert loaded.tasks[1].dependencies == ["1.1"]


# ============================================================================
# List Tasksets Tests
# ============================================================================

def test_list_tasksets_empty(task_store):
    """Test list_tasksets returns empty list when no tasksets exist."""
    tasksets = task_store.list_tasksets()
    assert tasksets == []


def test_list_tasksets_single(task_store, sample_taskset):
    """Test list_tasksets returns single taskset."""
    task_store.save_taskset(sample_taskset)
    
    tasksets = task_store.list_tasksets()
    
    assert len(tasksets) == 1
    assert "test-spec" in tasksets


def test_list_tasksets_multiple(task_store):
    """Test list_tasksets returns multiple tasksets."""
    for i in range(3):
        taskset = Taskset(
            spec_name=f"spec-{i}",
            version=1,
            tasks=[],
            metadata={},
        )
        task_store.save_taskset(taskset)
    
    tasksets = task_store.list_tasksets()
    
    assert len(tasksets) == 3
    assert "spec-0" in tasksets
    assert "spec-1" in tasksets
    assert "spec-2" in tasksets


def test_list_tasksets_ignores_non_directories(task_store, sample_taskset):
    """Test list_tasksets ignores non-directory files."""
    task_store.save_taskset(sample_taskset)
    
    # Create a file in storage directory
    (task_store.storage_dir / "not_a_dir.txt").write_text("test")
    
    tasksets = task_store.list_tasksets()
    
    assert len(tasksets) == 1
    assert "test-spec" in tasksets
    assert "not_a_dir.txt" not in tasksets


# ============================================================================
# Backup Taskset Tests
# ============================================================================

def test_backup_taskset_creates_backup_file(task_store, sample_taskset, tmp_path):
    """Test backup_taskset creates backup file."""
    task_store.save_taskset(sample_taskset)
    
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("test-spec", backup_dir)
    
    assert backup_path.exists()
    assert backup_path.is_file()
    assert backup_path.suffix == ".json"


def test_backup_taskset_preserves_data(task_store, sample_taskset, tmp_path):
    """Test backup_taskset preserves all data."""
    task_store.save_taskset(sample_taskset)
    
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("test-spec", backup_dir)
    
    # Load backup and verify
    with open(backup_path, "r") as f:
        backup_data = json.load(f)
    
    assert backup_data["spec_name"] == "test-spec"
    assert backup_data["version"] == 1
    assert len(backup_data["tasks"]) == 1


def test_backup_taskset_nonexistent_raises_error(task_store, tmp_path):
    """Test backup_taskset raises error for nonexistent taskset."""
    backup_dir = tmp_path / "backups"
    
    with pytest.raises(TasksetNotFoundError):
        task_store.backup_taskset("nonexistent", backup_dir)


def test_backup_taskset_creates_backup_directory(task_store, sample_taskset, tmp_path):
    """Test backup_taskset creates backup directory if it doesn't exist."""
    task_store.save_taskset(sample_taskset)
    
    backup_dir = tmp_path / "backups"
    assert not backup_dir.exists()
    
    task_store.backup_taskset("test-spec", backup_dir)
    
    assert backup_dir.exists()
    assert backup_dir.is_dir()


def test_backup_taskset_includes_timestamp(task_store, sample_taskset, tmp_path):
    """Test backup_taskset includes timestamp in filename."""
    task_store.save_taskset(sample_taskset)
    
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("test-spec", backup_dir)
    
    # Filename should contain spec name and timestamp
    assert "test-spec" in backup_path.name
    assert backup_path.name.startswith("test-spec_")


# ============================================================================
# Restore Taskset Tests
# ============================================================================

def test_restore_taskset_restores_data(task_store, sample_taskset, tmp_path):
    """Test restore_taskset restores taskset from backup."""
    # Save and backup
    task_store.save_taskset(sample_taskset)
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("test-spec", backup_dir)
    
    # Modify original
    sample_taskset.version = 2
    task_store.save_taskset(sample_taskset)
    
    # Restore from backup
    spec_name = task_store.restore_taskset(backup_path)
    
    # Verify restored version
    loaded = task_store.load_taskset(spec_name)
    assert loaded.version == 1  # Original version


def test_restore_taskset_returns_spec_name(task_store, sample_taskset, tmp_path):
    """Test restore_taskset returns spec name."""
    task_store.save_taskset(sample_taskset)
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("test-spec", backup_dir)
    
    spec_name = task_store.restore_taskset(backup_path)
    
    assert spec_name == "test-spec"


def test_restore_taskset_nonexistent_backup_raises_error(task_store, tmp_path):
    """Test restore_taskset raises error for nonexistent backup."""
    backup_path = tmp_path / "nonexistent_backup.json"
    
    with pytest.raises(FileNotFoundError):
        task_store.restore_taskset(backup_path)


def test_restore_taskset_invalid_json_raises_error(task_store, tmp_path):
    """Test restore_taskset raises error for invalid JSON."""
    backup_path = tmp_path / "invalid_backup.json"
    backup_path.write_text("{ invalid json }")
    
    with pytest.raises(ValueError):
        task_store.restore_taskset(backup_path)


def test_restore_taskset_overwrites_existing(task_store, sample_taskset, tmp_path):
    """Test restore_taskset overwrites existing taskset."""
    # Save original
    task_store.save_taskset(sample_taskset)
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("test-spec", backup_dir)
    
    # Modify
    sample_taskset.version = 2
    sample_taskset.tasks[0].state = TaskState.DONE
    task_store.save_taskset(sample_taskset)
    
    # Restore
    task_store.restore_taskset(backup_path)
    
    # Verify original state restored
    loaded = task_store.load_taskset("test-spec")
    assert loaded.version == 1
    assert loaded.tasks[0].state == TaskState.READY


# ============================================================================
# Backup Integrity Tests
# ============================================================================

def test_backup_and_restore_roundtrip(task_store, tmp_path):
    """Test complete backup and restore roundtrip."""
    # Create complex taskset
    task1 = Task(
        id="1.1",
        title="Task 1",
        description="Description 1",
        state=TaskState.DONE,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
        assigned_slot="slot-1",
        reserved_branch="feature/task-1.1",
        runner_id="runner-1",
    )
    
    task2 = Task(
        id="1.2",
        title="Task 2",
        description="Description 2",
        state=TaskState.RUNNING,
        dependencies=["1.1"],
        required_skill="frontend",
        priority=2,
        is_optional=True,
    )
    
    original_taskset = Taskset(
        spec_name="complex-spec",
        version=3,
        tasks=[task1, task2],
        metadata={"kiro_spec_path": ".kiro/specs/complex-spec/tasks.md"},
    )
    
    # Save
    task_store.save_taskset(original_taskset)
    
    # Backup
    backup_dir = tmp_path / "backups"
    backup_path = task_store.backup_taskset("complex-spec", backup_dir)
    
    # Delete original
    import shutil
    shutil.rmtree(task_store.storage_dir / "complex-spec")
    
    # Restore
    spec_name = task_store.restore_taskset(backup_path)
    
    # Verify
    restored_taskset = task_store.load_taskset(spec_name)
    assert restored_taskset.spec_name == original_taskset.spec_name
    assert restored_taskset.version == original_taskset.version
    assert len(restored_taskset.tasks) == len(original_taskset.tasks)
    assert restored_taskset.tasks[0].assigned_slot == original_taskset.tasks[0].assigned_slot
    assert restored_taskset.tasks[1].dependencies == original_taskset.tasks[1].dependencies
    assert restored_taskset.metadata == original_taskset.metadata


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_save_taskset_with_empty_tasks(task_store):
    """Test save_taskset with empty tasks list."""
    taskset = Taskset(
        spec_name="empty-spec",
        version=1,
        tasks=[],
        metadata={},
    )
    
    task_store.save_taskset(taskset)
    loaded = task_store.load_taskset("empty-spec")
    
    assert len(loaded.tasks) == 0


def test_load_taskset_with_corrupted_json(task_store, storage_dir):
    """Test load_taskset handles corrupted JSON gracefully."""
    # Create corrupted taskset file
    spec_dir = storage_dir / "corrupted-spec"
    spec_dir.mkdir(parents=True)
    taskset_file = spec_dir / "taskset.json"
    taskset_file.write_text("{ invalid json }")
    
    with pytest.raises(ValueError):
        task_store.load_taskset("corrupted-spec")


def test_save_and_load_taskset_with_special_characters(task_store):
    """Test save and load taskset with special characters in data."""
    task = Task(
        id="1.1",
        title="Task with 日本語 and émojis 🎉",
        description="Description with\nnewlines\tand\ttabs",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    taskset = Taskset(
        spec_name="special-chars-spec",
        version=1,
        tasks=[task],
        metadata={"note": "Contains 特殊文字"},
    )
    
    task_store.save_taskset(taskset)
    loaded = task_store.load_taskset("special-chars-spec")
    
    assert loaded.tasks[0].title == task.title
    assert loaded.tasks[0].description == task.description
    assert loaded.metadata["note"] == taskset.metadata["note"]

"""Unit tests for Repo Pool Manager data models.

Tests serialization/deserialization of Pool, Slot, and SlotStatus models.
Requirements: 1.1
"""

import json
from datetime import datetime
from pathlib import Path
import pytest

from necrocode.repo_pool.models import (
    Pool,
    Slot,
    SlotState,
    SlotStatus,
    PoolSummary,
    CleanupResult,
    GitResult,
    AllocationMetrics,
)


# ============================================================================
# Slot Model Tests
# ============================================================================

def test_slot_creation():
    """Test basic Slot creation."""
    slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    assert slot.slot_id == "workspace-test-repo-slot1"
    assert slot.repo_name == "test-repo"
    assert slot.repo_url == "https://github.com/test/repo.git"
    assert slot.state == SlotState.AVAILABLE
    assert slot.allocation_count == 0
    assert slot.total_usage_seconds == 0


def test_slot_is_available():
    """Test Slot.is_available() method."""
    slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    assert slot.is_available() is True
    
    slot.state = SlotState.ALLOCATED
    assert slot.is_available() is False


def test_slot_mark_allocated():
    """Test Slot.mark_allocated() method."""
    slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    initial_count = slot.allocation_count
    slot.mark_allocated(metadata={"agent_id": "agent-1"})
    
    assert slot.state == SlotState.ALLOCATED
    assert slot.allocation_count == initial_count + 1
    assert slot.last_allocated_at is not None
    assert slot.metadata["agent_id"] == "agent-1"


def test_slot_mark_released():
    """Test Slot.mark_released() method."""
    slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.ALLOCATED,
    )
    
    slot.mark_allocated()
    slot.mark_released()
    
    assert slot.state == SlotState.AVAILABLE
    assert slot.last_released_at is not None
    assert slot.total_usage_seconds >= 0


def test_slot_to_dict():
    """Test Slot serialization to dictionary."""
    slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
        current_branch="main",
        current_commit="abc123",
    )
    
    slot_dict = slot.to_dict()
    
    assert slot_dict["slot_id"] == "workspace-test-repo-slot1"
    assert slot_dict["repo_name"] == "test-repo"
    assert slot_dict["state"] == "available"
    assert slot_dict["current_branch"] == "main"
    assert slot_dict["current_commit"] == "abc123"
    assert "slot_path" in slot_dict


def test_slot_from_dict():
    """Test Slot deserialization from dictionary."""
    slot_dict = {
        "slot_id": "workspace-test-repo-slot1",
        "repo_name": "test-repo",
        "repo_url": "https://github.com/test/repo.git",
        "slot_path": "/tmp/test/slot1",
        "state": "available",
        "allocation_count": 5,
        "total_usage_seconds": 3600,
        "last_allocated_at": "2025-11-15T10:00:00",
        "last_released_at": "2025-11-15T11:00:00",
        "current_branch": "main",
        "current_commit": "abc123",
        "metadata": {"key": "value"},
        "created_at": "2025-11-15T09:00:00",
        "updated_at": "2025-11-15T11:00:00",
    }
    
    slot = Slot.from_dict(slot_dict)
    
    assert slot.slot_id == "workspace-test-repo-slot1"
    assert slot.repo_name == "test-repo"
    assert slot.state == SlotState.AVAILABLE
    assert slot.allocation_count == 5
    assert slot.total_usage_seconds == 3600
    assert slot.current_branch == "main"
    assert slot.metadata["key"] == "value"


def test_slot_serialization_roundtrip():
    """Test Slot serialization and deserialization roundtrip."""
    original_slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.ALLOCATED,
        allocation_count=10,
        total_usage_seconds=7200,
        current_branch="feature/test",
        current_commit="def456",
        metadata={"agent_id": "agent-1", "task_id": "task-1"},
    )
    
    # Serialize
    slot_dict = original_slot.to_dict()
    
    # Deserialize
    restored_slot = Slot.from_dict(slot_dict)
    
    # Verify
    assert restored_slot.slot_id == original_slot.slot_id
    assert restored_slot.repo_name == original_slot.repo_name
    assert restored_slot.state == original_slot.state
    assert restored_slot.allocation_count == original_slot.allocation_count
    assert restored_slot.total_usage_seconds == original_slot.total_usage_seconds
    assert restored_slot.current_branch == original_slot.current_branch
    assert restored_slot.current_commit == original_slot.current_commit
    assert restored_slot.metadata == original_slot.metadata


# ============================================================================
# Pool Model Tests
# ============================================================================

def test_pool_creation():
    """Test basic Pool creation."""
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    now = datetime.now()
    pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=1,
        slots=[slot1],
        created_at=now,
        updated_at=now,
    )
    
    assert pool.repo_name == "test-repo"
    assert pool.repo_url == "https://github.com/test/repo.git"
    assert pool.num_slots == 1
    assert len(pool.slots) == 1


def test_pool_get_available_slots():
    """Test Pool.get_available_slots() method."""
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    slot2 = Slot(
        slot_id="workspace-test-repo-slot2",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot2"),
        state=SlotState.ALLOCATED,
    )
    
    now = datetime.now()
    pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=2,
        slots=[slot1, slot2],
        created_at=now,
        updated_at=now,
    )
    
    available = pool.get_available_slots()
    assert len(available) == 1
    assert available[0].slot_id == "workspace-test-repo-slot1"


def test_pool_get_allocated_slots():
    """Test Pool.get_allocated_slots() method."""
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    slot2 = Slot(
        slot_id="workspace-test-repo-slot2",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot2"),
        state=SlotState.ALLOCATED,
    )
    
    now = datetime.now()
    pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=2,
        slots=[slot1, slot2],
        created_at=now,
        updated_at=now,
    )
    
    allocated = pool.get_allocated_slots()
    assert len(allocated) == 1
    assert allocated[0].slot_id == "workspace-test-repo-slot2"


def test_pool_to_dict():
    """Test Pool serialization to dictionary."""
    now = datetime.now()
    pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=2,
        slots=[],
        created_at=now,
        updated_at=now,
        metadata={"key": "value"},
    )
    
    pool_dict = pool.to_dict()
    
    assert pool_dict["repo_name"] == "test-repo"
    assert pool_dict["repo_url"] == "https://github.com/test/repo.git"
    assert pool_dict["num_slots"] == 2
    assert pool_dict["metadata"]["key"] == "value"


def test_pool_from_dict():
    """Test Pool deserialization from dictionary."""
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    pool_dict = {
        "repo_name": "test-repo",
        "repo_url": "https://github.com/test/repo.git",
        "num_slots": 1,
        "created_at": "2025-11-15T09:00:00",
        "updated_at": "2025-11-15T10:00:00",
        "metadata": {"key": "value"},
    }
    
    pool = Pool.from_dict(pool_dict, slots=[slot1])
    
    assert pool.repo_name == "test-repo"
    assert pool.num_slots == 1
    assert len(pool.slots) == 1
    assert pool.metadata["key"] == "value"


def test_pool_serialization_roundtrip():
    """Test Pool serialization and deserialization roundtrip."""
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    now = datetime.now()
    original_pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=1,
        slots=[slot1],
        created_at=now,
        updated_at=now,
        metadata={"default_branch": "main"},
    )
    
    # Serialize
    pool_dict = original_pool.to_dict()
    
    # Deserialize
    restored_pool = Pool.from_dict(pool_dict, slots=[slot1])
    
    # Verify
    assert restored_pool.repo_name == original_pool.repo_name
    assert restored_pool.repo_url == original_pool.repo_url
    assert restored_pool.num_slots == original_pool.num_slots
    assert restored_pool.metadata == original_pool.metadata


# ============================================================================
# SlotStatus Model Tests
# ============================================================================

def test_slot_status_creation():
    """Test SlotStatus creation."""
    status = SlotStatus(
        slot_id="workspace-test-repo-slot1",
        state=SlotState.AVAILABLE,
        is_locked=False,
        current_branch="main",
        current_commit="abc123",
        allocation_count=5,
        last_allocated_at=datetime.now(),
        disk_usage_mb=150.5,
    )
    
    assert status.slot_id == "workspace-test-repo-slot1"
    assert status.state == SlotState.AVAILABLE
    assert status.is_locked is False
    assert status.current_branch == "main"
    assert status.allocation_count == 5
    assert status.disk_usage_mb == 150.5


# ============================================================================
# PoolSummary Model Tests
# ============================================================================

def test_pool_summary_creation():
    """Test PoolSummary creation."""
    summary = PoolSummary(
        repo_name="test-repo",
        total_slots=5,
        available_slots=3,
        allocated_slots=2,
        cleaning_slots=0,
        error_slots=0,
        total_allocations=100,
        average_allocation_time_seconds=45.5,
    )
    
    assert summary.repo_name == "test-repo"
    assert summary.total_slots == 5
    assert summary.available_slots == 3
    assert summary.allocated_slots == 2
    assert summary.total_allocations == 100
    assert summary.average_allocation_time_seconds == 45.5


# ============================================================================
# CleanupResult Model Tests
# ============================================================================

def test_cleanup_result_creation():
    """Test CleanupResult creation."""
    result = CleanupResult(
        slot_id="workspace-test-repo-slot1",
        success=True,
        duration_seconds=12.5,
        operations=["fetch", "clean", "reset"],
        errors=[],
    )
    
    assert result.slot_id == "workspace-test-repo-slot1"
    assert result.success is True
    assert result.duration_seconds == 12.5
    assert len(result.operations) == 3
    assert len(result.errors) == 0


def test_cleanup_result_with_errors():
    """Test CleanupResult with errors."""
    result = CleanupResult(
        slot_id="workspace-test-repo-slot1",
        success=False,
        duration_seconds=5.0,
        operations=["fetch"],
        errors=["Fetch failed: connection timeout"],
    )
    
    assert result.success is False
    assert len(result.errors) == 1
    assert "timeout" in result.errors[0]


# ============================================================================
# GitResult Model Tests
# ============================================================================

def test_git_result_creation():
    """Test GitResult creation."""
    result = GitResult(
        success=True,
        command="git fetch --all",
        stdout="Fetching origin\n",
        stderr="",
        exit_code=0,
        duration_seconds=2.5,
    )
    
    assert result.success is True
    assert result.command == "git fetch --all"
    assert result.exit_code == 0
    assert result.duration_seconds == 2.5


def test_git_result_failure():
    """Test GitResult for failed operation."""
    result = GitResult(
        success=False,
        command="git clone invalid-url",
        stdout="",
        stderr="fatal: repository not found",
        exit_code=128,
        duration_seconds=1.0,
    )
    
    assert result.success is False
    assert result.exit_code == 128
    assert "not found" in result.stderr


# ============================================================================
# AllocationMetrics Model Tests
# ============================================================================

def test_allocation_metrics_creation():
    """Test AllocationMetrics creation."""
    metrics = AllocationMetrics(
        repo_name="test-repo",
        total_allocations=100,
        average_allocation_time_seconds=15.5,
        cache_hit_rate=0.75,
        failed_allocations=5,
    )
    
    assert metrics.repo_name == "test-repo"
    assert metrics.total_allocations == 100
    assert metrics.average_allocation_time_seconds == 15.5
    assert metrics.cache_hit_rate == 0.75
    assert metrics.failed_allocations == 5


# ============================================================================
# SlotState Enum Tests
# ============================================================================

def test_slot_state_values():
    """Test SlotState enum values."""
    assert SlotState.AVAILABLE.value == "available"
    assert SlotState.ALLOCATED.value == "allocated"
    assert SlotState.CLEANING.value == "cleaning"
    assert SlotState.ERROR.value == "error"


def test_slot_state_from_string():
    """Test SlotState creation from string."""
    assert SlotState("available") == SlotState.AVAILABLE
    assert SlotState("allocated") == SlotState.ALLOCATED
    assert SlotState("cleaning") == SlotState.CLEANING
    assert SlotState("error") == SlotState.ERROR


# ============================================================================
# JSON Serialization Tests
# ============================================================================

def test_slot_json_serialization():
    """Test Slot JSON serialization."""
    slot = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test/slot1"),
        state=SlotState.AVAILABLE,
    )
    
    # Serialize to JSON
    json_str = json.dumps(slot.to_dict(), indent=2)
    
    # Deserialize from JSON
    slot_dict = json.loads(json_str)
    restored_slot = Slot.from_dict(slot_dict)
    
    # Verify
    assert restored_slot.slot_id == slot.slot_id
    assert restored_slot.repo_name == slot.repo_name
    assert restored_slot.state == slot.state


def test_pool_json_serialization():
    """Test Pool JSON serialization."""
    now = datetime.now()
    pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=2,
        slots=[],
        created_at=now,
        updated_at=now,
    )
    
    # Serialize to JSON
    json_str = json.dumps(pool.to_dict(), indent=2)
    
    # Deserialize from JSON
    pool_dict = json.loads(json_str)
    restored_pool = Pool.from_dict(pool_dict, slots=[])
    
    # Verify
    assert restored_pool.repo_name == pool.repo_name
    assert restored_pool.num_slots == pool.num_slots

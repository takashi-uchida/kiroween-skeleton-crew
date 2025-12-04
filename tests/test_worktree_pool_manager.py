"""Tests for WorktreePoolManager."""

import pytest
import tempfile
from pathlib import Path
from necrocode.repo_pool import PoolManager, PoolConfig
from necrocode.repo_pool.models import SlotState
from necrocode.repo_pool.exceptions import (
    PoolNotFoundError,
    NoAvailableSlotError,
    SlotAllocationError,
)


@pytest.fixture
def temp_workspaces():
    """Create temporary workspaces directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def pool_config(temp_workspaces):
    """Create pool configuration."""
    return PoolConfig(
        workspaces_dir=temp_workspaces,
        lock_timeout=5.0,
        cleanup_timeout=10.0,
    )


@pytest.fixture
def pool_manager(pool_config):
    """Create PoolManager instance."""
    return PoolManager(config=pool_config)


def test_create_worktree_pool(pool_manager):
    """Test creating a pool with git worktree."""
    # Note: This test requires a real git repository
    # For unit testing, you might want to mock git operations
    
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=3
    )
    
    assert pool.repo_name == "test-repo"
    assert pool.num_slots == 3
    assert len(pool.slots) == 3
    
    # Verify all slots are available
    for slot in pool.slots:
        assert slot.state == SlotState.AVAILABLE
        assert slot.slot_path.exists()
        assert slot.current_branch is not None


def test_allocate_and_release_slot(pool_manager):
    """Test slot allocation and release."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=2
    )
    
    # Allocate slot
    slot = pool_manager.allocate_slot("test-repo", metadata={"task": "test-task"})
    
    assert slot is not None
    assert slot.state == SlotState.ALLOCATED
    assert slot.allocation_count == 1
    assert slot.metadata["task"] == "test-task"
    
    # Release slot
    pool_manager.release_slot(slot.slot_id, cleanup=True)
    
    # Verify slot is available again
    released_slot = pool_manager.slot_store.load_slot(slot.slot_id)
    assert released_slot.state == SlotState.AVAILABLE


def test_parallel_allocation(pool_manager):
    """Test allocating multiple slots in parallel."""
    # Create pool with multiple slots
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=5
    )
    
    # Allocate multiple slots
    allocated_slots = []
    for i in range(3):
        slot = pool_manager.allocate_slot("test-repo", metadata={"task": f"task-{i}"})
        allocated_slots.append(slot)
    
    # Verify all slots are different
    slot_ids = [s.slot_id for s in allocated_slots]
    assert len(slot_ids) == len(set(slot_ids))
    
    # Verify all are allocated
    for slot in allocated_slots:
        assert slot.state == SlotState.ALLOCATED


def test_no_available_slots(pool_manager):
    """Test behavior when no slots are available."""
    # Create pool with 1 slot
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=1
    )
    
    # Allocate the only slot
    slot1 = pool_manager.allocate_slot("test-repo")
    assert slot1 is not None
    
    # Try to allocate another slot (should fail)
    with pytest.raises(NoAvailableSlotError):
        pool_manager.allocate_slot("test-repo")


def test_add_slot_dynamically(pool_manager):
    """Test adding a slot to an existing pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=2
    )
    
    initial_count = pool.num_slots
    
    # Add new slot
    new_slot = pool_manager.add_slot("test-repo")
    
    assert new_slot.state == SlotState.AVAILABLE
    
    # Verify pool has one more slot
    updated_pool = pool_manager.get_pool("test-repo")
    assert updated_pool.num_slots == initial_count + 1


def test_remove_slot(pool_manager):
    """Test removing a slot from a pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=3
    )
    
    initial_count = pool.num_slots
    slot_to_remove = pool.slots[0]
    
    # Remove slot
    pool_manager.remove_slot(slot_to_remove.slot_id, force=False)
    
    # Verify pool has one less slot
    updated_pool = pool_manager.get_pool("test-repo")
    assert updated_pool.num_slots == initial_count - 1


def test_pool_summary(pool_manager):
    """Test getting pool summary."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=3
    )
    
    # Allocate one slot
    pool_manager.allocate_slot("test-repo")
    
    # Get summary
    summaries = pool_manager.get_pool_summary()
    
    assert "test-repo" in summaries
    summary = summaries["test-repo"]
    
    assert summary.total_slots == 3
    assert summary.allocated_slots == 1
    assert summary.available_slots == 2


def test_slot_status(pool_manager):
    """Test getting slot status."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=2
    )
    
    slot = pool.slots[0]
    
    # Get status
    status = pool_manager.get_slot_status(slot.slot_id)
    
    assert status.slot_id == slot.slot_id
    assert status.state == SlotState.AVAILABLE
    assert status.is_locked == False
    assert status.allocation_count == 0


def test_allocation_metrics(pool_manager):
    """Test allocation metrics tracking."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=2
    )
    
    # Perform some allocations
    slot1 = pool_manager.allocate_slot("test-repo")
    pool_manager.release_slot(slot1.slot_id)
    
    slot2 = pool_manager.allocate_slot("test-repo")
    pool_manager.release_slot(slot2.slot_id)
    
    # Get metrics
    metrics = pool_manager.get_allocation_metrics("test-repo")
    
    assert metrics.repo_name == "test-repo"
    assert metrics.total_allocations == 2
    assert metrics.average_allocation_time_seconds > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

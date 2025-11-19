"""Integration tests for pool lifecycle.

Tests pool creation, slot management, and deletion lifecycle.
Requirements: 1.1, 1.2, 7.1, 7.2, 7.5
"""

import time
from pathlib import Path
import sys
import pytest
import shutil
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.models import SlotState
from necrocode.repo_pool.exceptions import (
    PoolNotFoundError,
    SlotNotFoundError,
    SlotAllocationError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def workspaces_dir(tmp_path):
    """Create temporary workspaces directory."""
    return tmp_path / "workspaces"


@pytest.fixture
def config(workspaces_dir):
    """Create PoolConfig instance."""
    return PoolConfig(
        workspaces_dir=workspaces_dir,
        default_num_slots=2,
        lock_timeout=5.0,
    )


@pytest.fixture
def pool_manager(config):
    """Create PoolManager instance."""
    return PoolManager(config)


@pytest.fixture
def test_repo_url():
    """Return a test repository URL."""
    # Use a small public repository for testing
    return "https://github.com/octocat/Hello-World.git"


# ============================================================================
# Pool Creation Tests
# ============================================================================

def test_create_pool_basic(pool_manager, test_repo_url):
    """Test basic pool creation."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Verify pool properties
    assert pool.repo_name == "test-repo"
    assert pool.repo_url == test_repo_url
    assert pool.num_slots == 2
    assert len(pool.slots) == 2
    assert pool.created_at is not None
    assert pool.updated_at is not None
    
    # Verify all slots are available
    for slot in pool.slots:
        assert slot.state == SlotState.AVAILABLE
        assert slot.repo_name == "test-repo"
        assert slot.repo_url == test_repo_url
        assert slot.slot_path.exists()
        assert (slot.slot_path / ".git").exists()


def test_create_pool_with_custom_slots(pool_manager, test_repo_url):
    """Test pool creation with custom number of slots."""
    pool = pool_manager.create_pool(
        repo_name="custom-repo",
        repo_url=test_repo_url,
        num_slots=5
    )
    
    assert pool.num_slots == 5
    assert len(pool.slots) == 5
    
    # Verify slot IDs are unique
    slot_ids = [slot.slot_id for slot in pool.slots]
    assert len(slot_ids) == len(set(slot_ids))


def test_create_multiple_pools(pool_manager, test_repo_url):
    """Test creating multiple pools."""
    # Create first pool
    pool1 = pool_manager.create_pool(
        repo_name="repo1",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Create second pool
    pool2 = pool_manager.create_pool(
        repo_name="repo2",
        repo_url=test_repo_url,
        num_slots=3
    )
    
    # Verify both pools exist
    assert pool1.repo_name == "repo1"
    assert pool2.repo_name == "repo2"
    assert len(pool1.slots) == 2
    assert len(pool2.slots) == 3
    
    # Verify pools are independent
    pools = pool_manager.list_pools()
    assert "repo1" in pools
    assert "repo2" in pools


def test_pool_persistence(pool_manager, test_repo_url, config):
    """Test that pool data persists across manager instances."""
    # Create pool
    pool_manager.create_pool(
        repo_name="persist-repo",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Create new manager instance
    new_manager = PoolManager(config)
    
    # Verify pool can be retrieved
    pool = new_manager.get_pool("persist-repo")
    assert pool.repo_name == "persist-repo"
    assert pool.num_slots == 2
    assert len(pool.slots) == 2


# ============================================================================
# Pool Retrieval Tests
# ============================================================================

def test_get_pool(pool_manager, test_repo_url):
    """Test retrieving an existing pool."""
    # Create pool
    created_pool = pool_manager.create_pool(
        repo_name="get-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Retrieve pool
    retrieved_pool = pool_manager.get_pool("get-test")
    
    assert retrieved_pool.repo_name == created_pool.repo_name
    assert retrieved_pool.num_slots == created_pool.num_slots
    assert len(retrieved_pool.slots) == len(created_pool.slots)


def test_get_nonexistent_pool(pool_manager):
    """Test retrieving a non-existent pool raises error."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.get_pool("nonexistent")


def test_list_pools(pool_manager, test_repo_url):
    """Test listing all pools."""
    # Initially empty
    assert len(pool_manager.list_pools()) == 0
    
    # Create pools
    pool_manager.create_pool("repo1", test_repo_url, 2)
    pool_manager.create_pool("repo2", test_repo_url, 3)
    pool_manager.create_pool("repo3", test_repo_url, 1)
    
    # List pools
    pools = pool_manager.list_pools()
    assert len(pools) == 3
    assert "repo1" in pools
    assert "repo2" in pools
    assert "repo3" in pools


# ============================================================================
# Slot Addition Tests
# ============================================================================

def test_add_slot_to_existing_pool(pool_manager, test_repo_url):
    """Test adding a slot to an existing pool."""
    # Create pool with 2 slots
    pool = pool_manager.create_pool(
        repo_name="add-slot-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    initial_slot_count = len(pool.slots)
    
    # Add a new slot
    new_slot = pool_manager.add_slot("add-slot-test")
    
    # Verify slot was added
    assert new_slot is not None
    assert new_slot.state == SlotState.AVAILABLE
    assert new_slot.slot_path.exists()
    assert (new_slot.slot_path / ".git").exists()
    
    # Verify pool has one more slot
    updated_pool = pool_manager.get_pool("add-slot-test")
    assert len(updated_pool.slots) == initial_slot_count + 1


def test_add_multiple_slots(pool_manager, test_repo_url):
    """Test adding multiple slots to a pool."""
    # Create pool with 1 slot
    pool_manager.create_pool(
        repo_name="multi-add-test",
        repo_url=test_repo_url,
        num_slots=1
    )
    
    # Add 3 more slots
    for i in range(3):
        slot = pool_manager.add_slot("multi-add-test")
        assert slot is not None
    
    # Verify pool has 4 slots total
    pool = pool_manager.get_pool("multi-add-test")
    assert len(pool.slots) == 4


def test_add_slot_to_nonexistent_pool(pool_manager):
    """Test adding slot to non-existent pool raises error."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.add_slot("nonexistent")


# ============================================================================
# Slot Removal Tests
# ============================================================================

def test_remove_available_slot(pool_manager, test_repo_url):
    """Test removing an available slot."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="remove-test",
        repo_url=test_repo_url,
        num_slots=3
    )
    
    slot_to_remove = pool.slots[0]
    slot_id = slot_to_remove.slot_id
    slot_path = slot_to_remove.slot_path
    
    # Remove slot
    pool_manager.remove_slot(slot_id)
    
    # Verify slot was removed
    updated_pool = pool_manager.get_pool("remove-test")
    assert len(updated_pool.slots) == 2
    assert not any(s.slot_id == slot_id for s in updated_pool.slots)
    
    # Verify slot directory was deleted
    assert not slot_path.exists()


def test_remove_allocated_slot_fails(pool_manager, test_repo_url):
    """Test that removing an allocated slot fails."""
    # Create pool
    pool_manager.create_pool(
        repo_name="remove-allocated-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Allocate a slot
    slot = pool_manager.allocate_slot("remove-allocated-test")
    
    # Try to remove allocated slot
    with pytest.raises(SlotAllocationError):
        pool_manager.remove_slot(slot.slot_id)


def test_remove_nonexistent_slot(pool_manager):
    """Test removing non-existent slot raises error."""
    with pytest.raises(SlotNotFoundError):
        pool_manager.remove_slot("nonexistent-slot")


def test_remove_multiple_slots(pool_manager, test_repo_url):
    """Test removing multiple slots."""
    # Create pool with 5 slots
    pool = pool_manager.create_pool(
        repo_name="multi-remove-test",
        repo_url=test_repo_url,
        num_slots=5
    )
    
    # Remove 3 slots
    slots_to_remove = pool.slots[:3]
    for slot in slots_to_remove:
        pool_manager.remove_slot(slot.slot_id)
    
    # Verify only 2 slots remain
    updated_pool = pool_manager.get_pool("multi-remove-test")
    assert len(updated_pool.slots) == 2


# ============================================================================
# Complete Lifecycle Tests
# ============================================================================

def test_complete_pool_lifecycle(pool_manager, test_repo_url):
    """Test complete pool lifecycle: create, use, modify, cleanup."""
    # 1. Create pool
    pool = pool_manager.create_pool(
        repo_name="lifecycle-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    assert len(pool.slots) == 2
    
    # 2. Allocate slot
    slot1 = pool_manager.allocate_slot("lifecycle-test")
    assert slot1 is not None
    assert slot1.state == SlotState.ALLOCATED
    
    # 3. Add more slots
    new_slot = pool_manager.add_slot("lifecycle-test")
    assert new_slot is not None
    
    pool = pool_manager.get_pool("lifecycle-test")
    assert len(pool.slots) == 3
    
    # 4. Release slot
    pool_manager.release_slot(slot1.slot_id)
    
    # 5. Remove a slot
    pool_manager.remove_slot(new_slot.slot_id)
    
    pool = pool_manager.get_pool("lifecycle-test")
    assert len(pool.slots) == 2
    
    # 6. Verify all remaining slots are available
    for slot in pool.slots:
        assert slot.state == SlotState.AVAILABLE


def test_pool_lifecycle_with_multiple_allocations(pool_manager, test_repo_url):
    """Test pool lifecycle with multiple allocation/release cycles."""
    # Create pool
    pool_manager.create_pool(
        repo_name="multi-alloc-test",
        repo_url=test_repo_url,
        num_slots=3
    )
    
    # Perform multiple allocation/release cycles
    for cycle in range(3):
        # Allocate all slots
        allocated_slots = []
        for i in range(3):
            slot = pool_manager.allocate_slot("multi-alloc-test")
            assert slot is not None
            allocated_slots.append(slot)
        
        # Verify all slots are allocated
        pool = pool_manager.get_pool("multi-alloc-test")
        assert all(s.state == SlotState.ALLOCATED for s in pool.slots)
        
        # Release all slots
        for slot in allocated_slots:
            pool_manager.release_slot(slot.slot_id)
        
        # Verify all slots are available
        pool = pool_manager.get_pool("multi-alloc-test")
        assert all(s.state == SlotState.AVAILABLE for s in pool.slots)


def test_pool_state_consistency_after_operations(pool_manager, test_repo_url):
    """Test that pool state remains consistent after various operations."""
    # Create pool
    pool_manager.create_pool(
        repo_name="consistency-test",
        repo_url=test_repo_url,
        num_slots=4
    )
    
    # Perform mixed operations
    slot1 = pool_manager.allocate_slot("consistency-test")
    slot2 = pool_manager.allocate_slot("consistency-test")
    
    new_slot = pool_manager.add_slot("consistency-test")
    
    pool_manager.release_slot(slot1.slot_id)
    
    slot3 = pool_manager.allocate_slot("consistency-test")
    
    # Verify state consistency
    pool = pool_manager.get_pool("consistency-test")
    assert len(pool.slots) == 5
    
    allocated_count = sum(1 for s in pool.slots if s.state == SlotState.ALLOCATED)
    available_count = sum(1 for s in pool.slots if s.state == SlotState.AVAILABLE)
    
    assert allocated_count == 2  # slot2 and slot3
    assert available_count == 3  # slot1 (released), new_slot, and 2 original


# ============================================================================
# Pool Summary Tests
# ============================================================================

def test_pool_summary_after_lifecycle(pool_manager, test_repo_url):
    """Test pool summary reflects lifecycle changes."""
    # Create pool
    pool_manager.create_pool(
        repo_name="summary-test",
        repo_url=test_repo_url,
        num_slots=3
    )
    
    # Allocate some slots
    slot1 = pool_manager.allocate_slot("summary-test")
    slot2 = pool_manager.allocate_slot("summary-test")
    
    # Get summary
    summary = pool_manager.get_pool_summary()
    
    assert "summary-test" in summary
    pool_summary = summary["summary-test"]
    
    assert pool_summary.total_slots == 3
    assert pool_summary.allocated_slots == 2
    assert pool_summary.available_slots == 1
    assert pool_summary.total_allocations >= 2


def test_multiple_pools_summary(pool_manager, test_repo_url):
    """Test summary with multiple pools."""
    # Create multiple pools
    pool_manager.create_pool("pool1", test_repo_url, 2)
    pool_manager.create_pool("pool2", test_repo_url, 3)
    pool_manager.create_pool("pool3", test_repo_url, 1)
    
    # Allocate slots from different pools
    pool_manager.allocate_slot("pool1")
    pool_manager.allocate_slot("pool2")
    pool_manager.allocate_slot("pool2")
    
    # Get summary
    summary = pool_manager.get_pool_summary()
    
    assert len(summary) == 3
    assert summary["pool1"].allocated_slots == 1
    assert summary["pool2"].allocated_slots == 2
    assert summary["pool3"].allocated_slots == 0


# ============================================================================
# Error Recovery Tests
# ============================================================================

def test_pool_recovery_after_partial_creation(pool_manager, workspaces_dir):
    """Test recovery when pool creation is partially completed."""
    # Simulate partial pool creation by creating directory structure
    # but not completing the pool creation
    repo_dir = workspaces_dir / "partial-repo"
    repo_dir.mkdir(parents=True)
    
    # Now try to create pool normally
    # This should handle the existing directory gracefully
    pool = pool_manager.create_pool(
        repo_name="partial-repo",
        repo_url="https://github.com/octocat/Hello-World.git",
        num_slots=2
    )
    
    assert pool is not None
    assert len(pool.slots) == 2


def test_slot_metadata_persistence(pool_manager, test_repo_url):
    """Test that slot metadata persists through lifecycle."""
    # Create pool
    pool_manager.create_pool(
        repo_name="metadata-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Allocate and release multiple times
    for i in range(3):
        slot = pool_manager.allocate_slot("metadata-test")
        time.sleep(0.1)  # Small delay to ensure different timestamps
        pool_manager.release_slot(slot.slot_id)
    
    # Verify allocation count increased
    pool = pool_manager.get_pool("metadata-test")
    # At least one slot should have allocation_count >= 3
    assert any(s.allocation_count >= 3 for s in pool.slots)


# ============================================================================
# Cleanup Tests
# ============================================================================

def test_cleanup_pool_directory(pool_manager, test_repo_url, workspaces_dir):
    """Test that pool directory can be cleaned up."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="cleanup-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    
    # Verify directory exists
    pool_dir = workspaces_dir / "cleanup-test"
    assert pool_dir.exists()
    
    # Remove all slots
    for slot in pool.slots:
        pool_manager.remove_slot(slot.slot_id)
    
    # Verify slots are removed
    pool = pool_manager.get_pool("cleanup-test")
    assert len(pool.slots) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

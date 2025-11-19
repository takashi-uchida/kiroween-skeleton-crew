"""Unit tests for PoolManager.

Integration tests for the main PoolManager API.
Requirements: All
"""

import subprocess
from datetime import datetime
from pathlib import Path
import pytest

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.models import SlotState
from necrocode.repo_pool.exceptions import (
    PoolNotFoundError,
    NoAvailableSlotError,
    SlotNotFoundError,
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
    return PoolConfig(workspaces_dir=workspaces_dir)


@pytest.fixture
def pool_manager(config):
    """Create PoolManager instance."""
    return PoolManager(config)


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Create initial commit
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
    
    return repo_dir


# ============================================================================
# PoolManager Initialization Tests
# ============================================================================

def test_pool_manager_initialization(pool_manager, workspaces_dir):
    """Test PoolManager initialization."""
    assert pool_manager.workspaces_dir == workspaces_dir
    assert workspaces_dir.exists()
    assert pool_manager.slot_store is not None
    assert pool_manager.slot_allocator is not None
    assert pool_manager.git_ops is not None
    assert pool_manager.slot_cleaner is not None
    assert pool_manager.lock_manager is not None


# ============================================================================
# Pool Creation Tests
# ============================================================================

def test_create_pool(pool_manager, temp_repo):
    """Test creating a pool."""
    pool = pool_manager.create_pool(
        repo_name="test-repo",
        repo_url=str(temp_repo),
        num_slots=2
    )
    
    assert pool.repo_name == "test-repo"
    assert pool.num_slots == 2
    assert len(pool.slots) == 2
    
    # Verify slots are created
    for slot in pool.slots:
        assert slot.state == SlotState.AVAILABLE
        assert slot.slot_path.exists()


def test_create_pool_duplicate_raises_error(pool_manager, temp_repo):
    """Test creating duplicate pool raises error."""
    pool_manager.create_pool(
        repo_name="test-repo",
        repo_url=str(temp_repo),
        num_slots=1
    )
    
    # Try to create again
    with pytest.raises(ValueError):
        pool_manager.create_pool(
            repo_name="test-repo",
            repo_url=str(temp_repo),
            num_slots=1
        )


# ============================================================================
# Get Pool Tests
# ============================================================================

def test_get_pool(pool_manager, temp_repo):
    """Test getting a pool."""
    # Create pool first
    pool_manager.create_pool(
        repo_name="test-repo",
        repo_url=str(temp_repo),
        num_slots=1
    )
    
    # Get pool
    pool = pool_manager.get_pool("test-repo")
    
    assert pool.repo_name == "test-repo"
    assert pool.num_slots == 1


def test_get_pool_not_found(pool_manager):
    """Test getting non-existent pool raises error."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.get_pool("nonexistent-repo")


# ============================================================================
# List Pools Tests
# ============================================================================

def test_list_pools_empty(pool_manager):
    """Test listing pools when none exist."""
    pools = pool_manager.list_pools()
    
    assert len(pools) == 0


def test_list_pools(pool_manager, temp_repo):
    """Test listing pools."""
    # Create multiple pools
    pool_manager.create_pool("repo1", str(temp_repo), 1)
    pool_manager.create_pool("repo2", str(temp_repo), 1)
    
    pools = pool_manager.list_pools()
    
    assert len(pools) == 2
    assert "repo1" in pools
    assert "repo2" in pools


# ============================================================================
# Allocate Slot Tests
# ============================================================================

def test_allocate_slot(pool_manager, temp_repo):
    """Test allocating a slot."""
    # Create pool
    pool_manager.create_pool("test-repo", str(temp_repo), 2)
    
    # Allocate slot
    slot = pool_manager.allocate_slot("test-repo", metadata={"task_id": "task-1"})
    
    assert slot is not None
    assert slot.state == SlotState.ALLOCATED
    assert slot.metadata["task_id"] == "task-1"


def test_allocate_slot_pool_not_found(pool_manager):
    """Test allocating slot from non-existent pool."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.allocate_slot("nonexistent-repo")


def test_allocate_slot_no_available_slots(pool_manager, temp_repo):
    """Test allocating slot when none available."""
    # Create pool with 1 slot
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    
    # Allocate the only slot
    pool_manager.allocate_slot("test-repo")
    
    # Try to allocate again
    with pytest.raises(NoAvailableSlotError):
        pool_manager.allocate_slot("test-repo")


# ============================================================================
# Release Slot Tests
# ============================================================================

def test_release_slot(pool_manager, temp_repo):
    """Test releasing a slot."""
    # Create pool and allocate slot
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    slot = pool_manager.allocate_slot("test-repo")
    
    # Release slot
    pool_manager.release_slot(slot.slot_id, cleanup=False)
    
    # Verify slot is available
    status = pool_manager.get_slot_status(slot.slot_id)
    assert status.state == SlotState.AVAILABLE


def test_release_slot_not_found(pool_manager):
    """Test releasing non-existent slot."""
    with pytest.raises(SlotNotFoundError):
        pool_manager.release_slot("workspace-nonexistent-slot1")


# ============================================================================
# Get Slot Status Tests
# ============================================================================

def test_get_slot_status(pool_manager, temp_repo):
    """Test getting slot status."""
    # Create pool
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    slot = pool_manager.allocate_slot("test-repo")
    
    # Get status
    status = pool_manager.get_slot_status(slot.slot_id)
    
    assert status.slot_id == slot.slot_id
    assert status.state == SlotState.ALLOCATED
    assert status.is_locked is False
    assert status.disk_usage_mb >= 0


# ============================================================================
# Get Pool Summary Tests
# ============================================================================

def test_get_pool_summary(pool_manager, temp_repo):
    """Test getting pool summary."""
    # Create pool with multiple slots
    pool_manager.create_pool("test-repo", str(temp_repo), 3)
    
    # Allocate one slot
    pool_manager.allocate_slot("test-repo")
    
    # Get summary
    summaries = pool_manager.get_pool_summary()
    
    assert "test-repo" in summaries
    summary = summaries["test-repo"]
    assert summary.total_slots == 3
    assert summary.available_slots == 2
    assert summary.allocated_slots == 1


# ============================================================================
# Add Slot Tests
# ============================================================================

def test_add_slot(pool_manager, temp_repo):
    """Test adding a slot to existing pool."""
    # Create pool
    pool_manager.create_pool("test-repo", str(temp_repo), 2)
    
    # Add slot
    new_slot = pool_manager.add_slot("test-repo")
    
    assert new_slot is not None
    assert new_slot.state == SlotState.AVAILABLE
    
    # Verify pool has 3 slots now
    pool = pool_manager.get_pool("test-repo")
    assert pool.num_slots == 3


# ============================================================================
# Remove Slot Tests
# ============================================================================

def test_remove_slot(pool_manager, temp_repo):
    """Test removing a slot from pool."""
    # Create pool
    pool_manager.create_pool("test-repo", str(temp_repo), 2)
    pool = pool_manager.get_pool("test-repo")
    slot_id = pool.slots[0].slot_id
    
    # Remove slot
    pool_manager.remove_slot(slot_id)
    
    # Verify pool has 1 slot now
    pool = pool_manager.get_pool("test-repo")
    assert pool.num_slots == 1


def test_remove_slot_allocated_without_force(pool_manager, temp_repo):
    """Test removing allocated slot without force fails."""
    # Create pool and allocate slot
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    slot = pool_manager.allocate_slot("test-repo")
    
    # Try to remove without force
    from necrocode.repo_pool.exceptions import SlotAllocationError
    with pytest.raises(SlotAllocationError):
        pool_manager.remove_slot(slot.slot_id, force=False)


# ============================================================================
# Anomaly Detection Tests
# ============================================================================

def test_detect_anomalies(pool_manager, temp_repo):
    """Test detecting anomalies in the pool system."""
    # Create pool
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    
    # Detect anomalies
    anomalies = pool_manager.detect_anomalies()
    
    assert "long_allocated_slots" in anomalies
    assert "corrupted_slots" in anomalies
    assert "orphaned_locks" in anomalies


# ============================================================================
# Performance Metrics Tests
# ============================================================================

def test_get_allocation_metrics(pool_manager, temp_repo):
    """Test getting allocation metrics."""
    # Create pool and perform allocation
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    pool_manager.allocate_slot("test-repo")
    
    # Get metrics
    metrics = pool_manager.get_allocation_metrics("test-repo")
    
    assert metrics.repo_name == "test-repo"
    assert metrics.total_allocations >= 1


def test_get_performance_metrics(pool_manager, temp_repo):
    """Test getting comprehensive performance metrics."""
    # Create pool and perform operations
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    slot = pool_manager.allocate_slot("test-repo")
    pool_manager.release_slot(slot.slot_id, cleanup=False)
    
    # Get metrics
    metrics = pool_manager.get_performance_metrics("test-repo")
    
    assert "test-repo" in metrics
    assert "allocation" in metrics["test-repo"]
    assert "cleanup" in metrics["test-repo"]
    assert "pool" in metrics["test-repo"]


# ============================================================================
# Integration Tests
# ============================================================================

def test_complete_workflow(pool_manager, temp_repo):
    """Test complete pool management workflow."""
    # Create pool
    pool = pool_manager.create_pool("test-repo", str(temp_repo), 2)
    assert pool.num_slots == 2
    
    # Allocate slot
    slot1 = pool_manager.allocate_slot("test-repo")
    assert slot1.state == SlotState.ALLOCATED
    
    # Allocate another slot
    slot2 = pool_manager.allocate_slot("test-repo")
    assert slot2.state == SlotState.ALLOCATED
    
    # Release first slot
    pool_manager.release_slot(slot1.slot_id, cleanup=False)
    
    # Verify we can allocate again
    slot3 = pool_manager.allocate_slot("test-repo")
    assert slot3 is not None


def test_multiple_pools(pool_manager, temp_repo):
    """Test managing multiple pools."""
    # Create multiple pools
    pool1 = pool_manager.create_pool("repo1", str(temp_repo), 1)
    pool2 = pool_manager.create_pool("repo2", str(temp_repo), 1)
    
    # Allocate from each pool
    slot1 = pool_manager.allocate_slot("repo1")
    slot2 = pool_manager.allocate_slot("repo2")
    
    assert slot1.repo_name == "repo1"
    assert slot2.repo_name == "repo2"
    
    # Get summary
    summaries = pool_manager.get_pool_summary()
    assert len(summaries) == 2


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_allocate_slot_with_cleanup(pool_manager, temp_repo):
    """Test slot allocation performs cleanup."""
    # Create pool
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    
    # Allocate slot (should perform cleanup)
    slot = pool_manager.allocate_slot("test-repo")
    
    assert slot is not None
    assert slot.current_branch is not None
    assert slot.current_commit is not None


def test_clear_metrics(pool_manager, temp_repo):
    """Test clearing performance metrics."""
    # Create pool and perform operations
    pool_manager.create_pool("test-repo", str(temp_repo), 1)
    pool_manager.allocate_slot("test-repo")
    
    # Clear metrics
    pool_manager.clear_metrics("test-repo")
    
    # Verify metrics are cleared
    metrics = pool_manager.get_allocation_metrics("test-repo")
    assert metrics.total_allocations == 0

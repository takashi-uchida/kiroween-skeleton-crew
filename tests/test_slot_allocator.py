"""Unit tests for SlotAllocator.

Tests allocation strategy, LRU cache, and metrics.
Requirements: 2.1, 2.2, 2.4, 10.2, 10.5
"""

from datetime import datetime
from pathlib import Path
import pytest

from necrocode.repo_pool.slot_allocator import SlotAllocator
from necrocode.repo_pool.slot_store import SlotStore
from necrocode.repo_pool.models import Slot, SlotState


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def workspaces_dir(tmp_path):
    """Create temporary workspaces directory."""
    return tmp_path / "workspaces"


@pytest.fixture
def slot_store(workspaces_dir):
    """Create SlotStore instance."""
    return SlotStore(workspaces_dir)


@pytest.fixture
def slot_allocator(slot_store):
    """Create SlotAllocator instance."""
    return SlotAllocator(slot_store)


@pytest.fixture
def sample_slots(workspaces_dir):
    """Create sample slots for testing."""
    slots = []
    for i in range(1, 4):
        slot = Slot(
            slot_id=f"workspace-test-repo-slot{i}",
            repo_name="test-repo",
            repo_url="https://github.com/test/repo.git",
            slot_path=workspaces_dir / "test-repo" / f"slot{i}",
            state=SlotState.AVAILABLE,
        )
        slots.append(slot)
    return slots


# ============================================================================
# Find Available Slot Tests
# ============================================================================

def test_find_available_slot_success(slot_allocator, slot_store, sample_slots):
    """Test finding an available slot."""
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Find available slot
    found_slot = slot_allocator.find_available_slot("test-repo")
    
    assert found_slot is not None
    assert found_slot.state == SlotState.AVAILABLE
    assert found_slot.repo_name == "test-repo"


def test_find_available_slot_no_pool(slot_allocator):
    """Test finding slot when pool doesn't exist."""
    found_slot = slot_allocator.find_available_slot("nonexistent-repo")
    
    assert found_slot is None


def test_find_available_slot_all_allocated(slot_allocator, slot_store, sample_slots):
    """Test finding slot when all slots are allocated."""
    # Mark all slots as allocated
    for slot in sample_slots:
        slot.state = SlotState.ALLOCATED
        slot_store.save_slot(slot)
    
    # Try to find available slot
    found_slot = slot_allocator.find_available_slot("test-repo")
    
    assert found_slot is None


def test_find_available_slot_prefers_recently_used(slot_allocator, slot_store, sample_slots):
    """Test that find_available_slot prefers recently used slots."""
    # Set different last_allocated_at times
    now = datetime.now()
    sample_slots[0].last_allocated_at = None  # Never used
    sample_slots[1].last_allocated_at = now  # Most recent
    sample_slots[2].last_allocated_at = datetime(2020, 1, 1)  # Old
    
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Find available slot
    found_slot = slot_allocator.find_available_slot("test-repo")
    
    # Should prefer the most recently used slot
    assert found_slot is not None
    assert found_slot.slot_id == "workspace-test-repo-slot2"


# ============================================================================
# Mark Allocated Tests
# ============================================================================

def test_mark_allocated(slot_allocator, slot_store, sample_slots):
    """Test marking a slot as allocated."""
    # Save slot
    slot_store.save_slot(sample_slots[0])
    
    # Mark as allocated
    slot_allocator.mark_allocated("workspace-test-repo-slot1", metadata={"agent_id": "agent-1"})
    
    # Load and verify
    loaded_slot = slot_store.load_slot("workspace-test-repo-slot1")
    assert loaded_slot.state == SlotState.ALLOCATED
    assert loaded_slot.allocation_count == 1
    assert loaded_slot.metadata["agent_id"] == "agent-1"


def test_mark_allocated_updates_lru_cache(slot_allocator, slot_store, sample_slots):
    """Test mark_allocated updates LRU cache."""
    # Save slot
    slot_store.save_slot(sample_slots[0])
    
    # Mark as allocated
    slot_allocator.mark_allocated("workspace-test-repo-slot1")
    
    # Verify LRU cache was updated
    assert "test-repo" in slot_allocator.lru_cache
    assert "workspace-test-repo-slot1" in slot_allocator.lru_cache["test-repo"]


# ============================================================================
# Mark Available Tests
# ============================================================================

def test_mark_available(slot_allocator, slot_store, sample_slots):
    """Test marking a slot as available."""
    # Save slot as allocated
    sample_slots[0].state = SlotState.ALLOCATED
    sample_slots[0].last_allocated_at = datetime.now()
    slot_store.save_slot(sample_slots[0])
    
    # Mark as available
    slot_allocator.mark_available("workspace-test-repo-slot1")
    
    # Load and verify
    loaded_slot = slot_store.load_slot("workspace-test-repo-slot1")
    assert loaded_slot.state == SlotState.AVAILABLE
    assert loaded_slot.last_released_at is not None


# ============================================================================
# LRU Cache Tests
# ============================================================================

def test_update_lru_cache(slot_allocator):
    """Test updating LRU cache."""
    # Update cache
    slot_allocator.update_lru_cache("test-repo", "workspace-test-repo-slot1")
    
    # Verify cache
    assert "test-repo" in slot_allocator.lru_cache
    assert "workspace-test-repo-slot1" in slot_allocator.lru_cache["test-repo"]


def test_update_lru_cache_moves_to_end(slot_allocator):
    """Test LRU cache moves recently used slot to end."""
    # Add multiple slots
    slot_allocator.update_lru_cache("test-repo", "workspace-test-repo-slot1")
    slot_allocator.update_lru_cache("test-repo", "workspace-test-repo-slot2")
    slot_allocator.update_lru_cache("test-repo", "workspace-test-repo-slot3")
    
    # Update slot1 again (should move to end)
    slot_allocator.update_lru_cache("test-repo", "workspace-test-repo-slot1")
    
    # Verify order (most recent should be last)
    cache_keys = list(slot_allocator.lru_cache["test-repo"].keys())
    assert cache_keys[-1] == "workspace-test-repo-slot1"


def test_lru_cache_limits_size(slot_allocator):
    """Test LRU cache limits size to prevent unbounded growth."""
    # Add more than max cache size (100)
    for i in range(150):
        slot_allocator.update_lru_cache("test-repo", f"workspace-test-repo-slot{i}")
    
    # Verify cache size is limited
    assert len(slot_allocator.lru_cache["test-repo"]) <= 100


# ============================================================================
# Allocation Metrics Tests
# ============================================================================

def test_get_allocation_metrics_initial(slot_allocator):
    """Test getting allocation metrics initially."""
    metrics = slot_allocator.get_allocation_metrics("test-repo")
    
    assert metrics.repo_name == "test-repo"
    assert metrics.total_allocations == 0
    assert metrics.average_allocation_time_seconds == 0.0
    assert metrics.cache_hit_rate == 0.0
    assert metrics.failed_allocations == 0


def test_get_allocation_metrics_after_allocations(slot_allocator, slot_store, sample_slots):
    """Test getting allocation metrics after allocations."""
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Perform allocations
    slot_allocator.find_available_slot("test-repo")
    slot_allocator.find_available_slot("test-repo")
    
    # Get metrics
    metrics = slot_allocator.get_allocation_metrics("test-repo")
    
    assert metrics.total_allocations == 2
    assert metrics.average_allocation_time_seconds >= 0.0


def test_allocation_metrics_tracks_cache_hits(slot_allocator, slot_store, sample_slots):
    """Test allocation metrics tracks cache hits."""
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Add slot to cache
    slot_allocator.update_lru_cache("test-repo", "workspace-test-repo-slot1")
    
    # Find slot (should be cache hit)
    slot_allocator.find_available_slot("test-repo")
    
    # Get metrics
    metrics = slot_allocator.get_allocation_metrics("test-repo")
    
    assert metrics.cache_hit_rate > 0.0


def test_allocation_metrics_tracks_failed_allocations(slot_allocator):
    """Test allocation metrics tracks failed allocations."""
    # Try to find slot in non-existent pool
    slot_allocator.find_available_slot("nonexistent-repo")
    
    # Get metrics
    metrics = slot_allocator.get_allocation_metrics("nonexistent-repo")
    
    assert metrics.failed_allocations == 1


# ============================================================================
# Clear Metrics Tests
# ============================================================================

def test_clear_metrics_single_repo(slot_allocator, slot_store, sample_slots):
    """Test clearing metrics for a single repository."""
    # Save slots and perform allocation
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    slot_allocator.find_available_slot("test-repo")
    
    # Clear metrics
    slot_allocator.clear_metrics("test-repo")
    
    # Verify metrics are cleared
    metrics = slot_allocator.get_allocation_metrics("test-repo")
    assert metrics.total_allocations == 0


def test_clear_metrics_all_repos(slot_allocator, slot_store, sample_slots):
    """Test clearing metrics for all repositories."""
    # Save slots and perform allocations
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    slot_allocator.find_available_slot("test-repo")
    
    # Clear all metrics
    slot_allocator.clear_metrics()
    
    # Verify metrics are cleared
    metrics = slot_allocator.get_allocation_metrics("test-repo")
    assert metrics.total_allocations == 0


# ============================================================================
# Integration Tests
# ============================================================================

def test_allocation_workflow(slot_allocator, slot_store, sample_slots):
    """Test complete allocation workflow."""
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Find and allocate slot
    found_slot = slot_allocator.find_available_slot("test-repo")
    assert found_slot is not None
    
    slot_allocator.mark_allocated(found_slot.slot_id, metadata={"task_id": "task-1"})
    
    # Verify slot is allocated
    loaded_slot = slot_store.load_slot(found_slot.slot_id)
    assert loaded_slot.state == SlotState.ALLOCATED
    assert loaded_slot.metadata["task_id"] == "task-1"
    
    # Release slot
    slot_allocator.mark_available(found_slot.slot_id)
    
    # Verify slot is available
    loaded_slot = slot_store.load_slot(found_slot.slot_id)
    assert loaded_slot.state == SlotState.AVAILABLE


def test_multiple_allocations_and_releases(slot_allocator, slot_store, sample_slots):
    """Test multiple allocation and release cycles."""
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Perform multiple allocation cycles
    for i in range(5):
        # Find and allocate
        found_slot = slot_allocator.find_available_slot("test-repo")
        assert found_slot is not None
        
        slot_allocator.mark_allocated(found_slot.slot_id)
        
        # Release
        slot_allocator.mark_available(found_slot.slot_id)
    
    # Verify metrics
    metrics = slot_allocator.get_allocation_metrics("test-repo")
    assert metrics.total_allocations >= 5


def test_allocation_with_mixed_states(slot_allocator, slot_store, sample_slots):
    """Test allocation with slots in mixed states."""
    # Set different states
    sample_slots[0].state = SlotState.ALLOCATED
    sample_slots[1].state = SlotState.AVAILABLE
    sample_slots[2].state = SlotState.ERROR
    
    # Save slots
    for slot in sample_slots:
        slot_store.save_slot(slot)
    
    # Find available slot
    found_slot = slot_allocator.find_available_slot("test-repo")
    
    # Should find the only available slot
    assert found_slot is not None
    assert found_slot.slot_id == "workspace-test-repo-slot2"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_find_available_slot_empty_pool(slot_allocator, slot_store):
    """Test finding slot in empty pool."""
    # Create pool directory but no slots
    pool_dir = slot_store.workspaces_dir / "test-repo"
    pool_dir.mkdir(parents=True)
    
    found_slot = slot_allocator.find_available_slot("test-repo")
    
    assert found_slot is None


def test_allocation_metrics_with_no_data(slot_allocator):
    """Test getting metrics with no allocation data."""
    metrics = slot_allocator.get_allocation_metrics("new-repo")
    
    assert metrics.repo_name == "new-repo"
    assert metrics.total_allocations == 0
    assert metrics.average_allocation_time_seconds == 0.0
    assert metrics.cache_hit_rate == 0.0


def test_lru_cache_multiple_repos(slot_allocator):
    """Test LRU cache handles multiple repositories."""
    # Update cache for different repos
    slot_allocator.update_lru_cache("repo1", "workspace-repo1-slot1")
    slot_allocator.update_lru_cache("repo2", "workspace-repo2-slot1")
    slot_allocator.update_lru_cache("repo1", "workspace-repo1-slot2")
    
    # Verify separate caches
    assert "repo1" in slot_allocator.lru_cache
    assert "repo2" in slot_allocator.lru_cache
    assert len(slot_allocator.lru_cache["repo1"]) == 2
    assert len(slot_allocator.lru_cache["repo2"]) == 1

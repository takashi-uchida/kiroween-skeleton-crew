"""Unit tests for SlotStore.

Tests save, load, and delete operations for pools and slots.
Requirements: 1.3, 1.5, 7.5
"""

import json
from datetime import datetime
from pathlib import Path
import pytest

from necrocode.repo_pool.slot_store import SlotStore
from necrocode.repo_pool.models import Pool, Slot, SlotState
from necrocode.repo_pool.exceptions import PoolNotFoundError, SlotNotFoundError


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
def sample_slot(workspaces_dir):
    """Create a sample slot for testing."""
    return Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=workspaces_dir / "test-repo" / "slot1",
        state=SlotState.AVAILABLE,
        current_branch="main",
        current_commit="abc123",
    )


@pytest.fixture
def sample_pool(sample_slot):
    """Create a sample pool for testing."""
    now = datetime.now()
    return Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=1,
        slots=[sample_slot],
        created_at=now,
        updated_at=now,
    )


# ============================================================================
# SlotStore Initialization Tests
# ============================================================================

def test_slot_store_creates_workspaces_dir(workspaces_dir):
    """Test SlotStore creates workspaces directory if it doesn't exist."""
    assert not workspaces_dir.exists()
    
    SlotStore(workspaces_dir)
    
    assert workspaces_dir.exists()
    assert workspaces_dir.is_dir()


def test_slot_store_uses_existing_workspaces_dir(workspaces_dir):
    """Test SlotStore uses existing workspaces directory."""
    workspaces_dir.mkdir(parents=True)
    test_file = workspaces_dir / "test.txt"
    test_file.write_text("test")
    
    SlotStore(workspaces_dir)
    
    assert workspaces_dir.exists()
    assert test_file.exists()


# ============================================================================
# Pool Save and Load Tests
# ============================================================================

def test_save_pool(slot_store, sample_pool):
    """Test saving pool metadata."""
    slot_store.save_pool(sample_pool)
    
    pool_file = slot_store.workspaces_dir / "test-repo" / "pool.json"
    assert pool_file.exists()
    
    # Verify file content
    with open(pool_file, 'r') as f:
        pool_data = json.load(f)
    
    assert pool_data["repo_name"] == "test-repo"
    assert pool_data["repo_url"] == "https://github.com/test/repo.git"
    assert pool_data["num_slots"] == 1


def test_load_pool(slot_store, sample_pool):
    """Test loading pool metadata."""
    # Save first
    slot_store.save_pool(sample_pool)
    
    # Load
    loaded_pool = slot_store.load_pool("test-repo")
    
    assert loaded_pool.repo_name == sample_pool.repo_name
    assert loaded_pool.repo_url == sample_pool.repo_url
    assert loaded_pool.num_slots == sample_pool.num_slots


def test_load_pool_not_found(slot_store):
    """Test loading non-existent pool raises PoolNotFoundError."""
    with pytest.raises(PoolNotFoundError):
        slot_store.load_pool("nonexistent-repo")


def test_pool_exists(slot_store, sample_pool):
    """Test pool_exists method."""
    assert not slot_store.pool_exists("test-repo")
    
    slot_store.save_pool(sample_pool)
    
    assert slot_store.pool_exists("test-repo")


# ============================================================================
# Slot Save and Load Tests
# ============================================================================

def test_save_slot(slot_store, sample_slot):
    """Test saving slot metadata."""
    slot_store.save_slot(sample_slot)
    
    slot_file = slot_store.workspaces_dir / "test-repo" / "slot1" / "slot.json"
    assert slot_file.exists()
    
    # Verify file content
    with open(slot_file, 'r') as f:
        slot_data = json.load(f)
    
    assert slot_data["slot_id"] == "workspace-test-repo-slot1"
    assert slot_data["repo_name"] == "test-repo"
    assert slot_data["state"] == "available"


def test_load_slot(slot_store, sample_slot):
    """Test loading slot metadata."""
    # Save first
    slot_store.save_slot(sample_slot)
    
    # Load
    loaded_slot = slot_store.load_slot("workspace-test-repo-slot1")
    
    assert loaded_slot.slot_id == sample_slot.slot_id
    assert loaded_slot.repo_name == sample_slot.repo_name
    assert loaded_slot.state == sample_slot.state
    assert loaded_slot.current_branch == sample_slot.current_branch


def test_load_slot_not_found(slot_store):
    """Test loading non-existent slot raises SlotNotFoundError."""
    with pytest.raises(SlotNotFoundError):
        slot_store.load_slot("workspace-nonexistent-repo-slot1")


def test_load_slot_invalid_id_format(slot_store):
    """Test loading slot with invalid ID format."""
    with pytest.raises(SlotNotFoundError):
        slot_store.load_slot("invalid-id")


def test_slot_exists(slot_store, sample_slot):
    """Test slot_exists method."""
    assert not slot_store.slot_exists("workspace-test-repo-slot1")
    
    slot_store.save_slot(sample_slot)
    
    assert slot_store.slot_exists("workspace-test-repo-slot1")


# ============================================================================
# List Slots Tests
# ============================================================================

def test_list_slots_empty(slot_store):
    """Test listing slots for non-existent pool."""
    slots = slot_store.list_slots("nonexistent-repo")
    assert len(slots) == 0


def test_list_slots_single(slot_store, sample_slot):
    """Test listing slots with single slot."""
    slot_store.save_slot(sample_slot)
    
    slots = slot_store.list_slots("test-repo")
    
    assert len(slots) == 1
    assert slots[0].slot_id == "workspace-test-repo-slot1"


def test_list_slots_multiple(slot_store, workspaces_dir):
    """Test listing slots with multiple slots."""
    # Create multiple slots
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=workspaces_dir / "test-repo" / "slot1",
        state=SlotState.AVAILABLE,
    )
    
    slot2 = Slot(
        slot_id="workspace-test-repo-slot2",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=workspaces_dir / "test-repo" / "slot2",
        state=SlotState.ALLOCATED,
    )
    
    slot_store.save_slot(slot1)
    slot_store.save_slot(slot2)
    
    slots = slot_store.list_slots("test-repo")
    
    assert len(slots) == 2
    slot_ids = {s.slot_id for s in slots}
    assert "workspace-test-repo-slot1" in slot_ids
    assert "workspace-test-repo-slot2" in slot_ids


def test_list_slots_ignores_corrupted_files(slot_store, workspaces_dir):
    """Test list_slots ignores corrupted slot files."""
    # Create valid slot
    slot1 = Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=workspaces_dir / "test-repo" / "slot1",
        state=SlotState.AVAILABLE,
    )
    slot_store.save_slot(slot1)
    
    # Create corrupted slot file
    slot2_dir = workspaces_dir / "test-repo" / "slot2"
    slot2_dir.mkdir(parents=True)
    (slot2_dir / "slot.json").write_text("invalid json {")
    
    # Should only return valid slot
    slots = slot_store.list_slots("test-repo")
    assert len(slots) == 1
    assert slots[0].slot_id == "workspace-test-repo-slot1"


# ============================================================================
# Delete Slot Tests
# ============================================================================

def test_delete_slot(slot_store, sample_slot):
    """Test deleting a slot."""
    # Save first
    slot_store.save_slot(sample_slot)
    assert slot_store.slot_exists("workspace-test-repo-slot1")
    
    # Delete
    slot_store.delete_slot("workspace-test-repo-slot1")
    
    # Verify deletion
    assert not slot_store.slot_exists("workspace-test-repo-slot1")
    slot_dir = slot_store.workspaces_dir / "test-repo" / "slot1"
    assert not slot_dir.exists()


def test_delete_slot_not_found(slot_store):
    """Test deleting non-existent slot raises SlotNotFoundError."""
    with pytest.raises(SlotNotFoundError):
        slot_store.delete_slot("workspace-nonexistent-repo-slot1")


def test_delete_slot_invalid_id_format(slot_store):
    """Test deleting slot with invalid ID format."""
    with pytest.raises(SlotNotFoundError):
        slot_store.delete_slot("invalid-id")


def test_delete_slot_removes_directory(slot_store, sample_slot, workspaces_dir):
    """Test delete_slot removes entire slot directory."""
    # Save slot and create some files
    slot_store.save_slot(sample_slot)
    slot_dir = workspaces_dir / "test-repo" / "slot1"
    (slot_dir / "test_file.txt").write_text("test content")
    (slot_dir / "subdir").mkdir()
    (slot_dir / "subdir" / "nested.txt").write_text("nested content")
    
    # Delete
    slot_store.delete_slot("workspace-test-repo-slot1")
    
    # Verify entire directory is removed
    assert not slot_dir.exists()


# ============================================================================
# Slot Persistence Tests
# ============================================================================

def test_slot_state_persistence(slot_store, sample_slot):
    """Test slot state is persisted correctly."""
    # Save with AVAILABLE state
    sample_slot.state = SlotState.AVAILABLE
    slot_store.save_slot(sample_slot)
    
    loaded = slot_store.load_slot("workspace-test-repo-slot1")
    assert loaded.state == SlotState.AVAILABLE
    
    # Update to ALLOCATED state
    sample_slot.state = SlotState.ALLOCATED
    slot_store.save_slot(sample_slot)
    
    loaded = slot_store.load_slot("workspace-test-repo-slot1")
    assert loaded.state == SlotState.ALLOCATED


def test_slot_metadata_persistence(slot_store, sample_slot):
    """Test slot metadata is persisted correctly."""
    sample_slot.metadata = {"agent_id": "agent-1", "task_id": "task-1"}
    slot_store.save_slot(sample_slot)
    
    loaded = slot_store.load_slot("workspace-test-repo-slot1")
    assert loaded.metadata["agent_id"] == "agent-1"
    assert loaded.metadata["task_id"] == "task-1"


def test_slot_usage_statistics_persistence(slot_store, sample_slot):
    """Test slot usage statistics are persisted correctly."""
    sample_slot.allocation_count = 10
    sample_slot.total_usage_seconds = 3600
    sample_slot.last_allocated_at = datetime.now()
    slot_store.save_slot(sample_slot)
    
    loaded = slot_store.load_slot("workspace-test-repo-slot1")
    assert loaded.allocation_count == 10
    assert loaded.total_usage_seconds == 3600
    assert loaded.last_allocated_at is not None


# ============================================================================
# Pool and Slot Integration Tests
# ============================================================================

def test_save_pool_and_slots(slot_store, sample_pool, sample_slot):
    """Test saving pool and its slots."""
    # Save pool
    slot_store.save_pool(sample_pool)
    
    # Save slot
    slot_store.save_slot(sample_slot)
    
    # Load pool
    loaded_pool = slot_store.load_pool("test-repo")
    
    # Verify pool has slots
    assert len(loaded_pool.slots) == 1
    assert loaded_pool.slots[0].slot_id == "workspace-test-repo-slot1"


def test_pool_with_multiple_slots(slot_store, workspaces_dir):
    """Test pool with multiple slots."""
    # Create pool
    now = datetime.now()
    pool = Pool(
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        num_slots=3,
        slots=[],
        created_at=now,
        updated_at=now,
    )
    slot_store.save_pool(pool)
    
    # Create multiple slots
    for i in range(1, 4):
        slot = Slot(
            slot_id=f"workspace-test-repo-slot{i}",
            repo_name="test-repo",
            repo_url="https://github.com/test/repo.git",
            slot_path=workspaces_dir / "test-repo" / f"slot{i}",
            state=SlotState.AVAILABLE,
        )
        slot_store.save_slot(slot)
    
    # Load pool
    loaded_pool = slot_store.load_pool("test-repo")
    
    # Verify all slots are loaded
    assert len(loaded_pool.slots) == 3
    assert loaded_pool.num_slots == 3


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_save_slot_creates_parent_directories(slot_store, sample_slot):
    """Test save_slot creates parent directories if they don't exist."""
    # Ensure parent doesn't exist
    slot_dir = slot_store.workspaces_dir / "test-repo" / "slot1"
    assert not slot_dir.exists()
    
    # Save slot
    slot_store.save_slot(sample_slot)
    
    # Verify directories were created
    assert slot_dir.exists()
    assert (slot_dir / "slot.json").exists()


def test_save_pool_creates_parent_directories(slot_store, sample_pool):
    """Test save_pool creates parent directories if they don't exist."""
    # Ensure parent doesn't exist
    pool_dir = slot_store.workspaces_dir / "test-repo"
    assert not pool_dir.exists()
    
    # Save pool
    slot_store.save_pool(sample_pool)
    
    # Verify directories were created
    assert pool_dir.exists()
    assert (pool_dir / "pool.json").exists()


def test_slot_with_special_characters_in_repo_name(slot_store, workspaces_dir):
    """Test slot with special characters in repository name."""
    slot = Slot(
        slot_id="workspace-test-repo-123-slot1",
        repo_name="test-repo-123",
        repo_url="https://github.com/test/repo-123.git",
        slot_path=workspaces_dir / "test-repo-123" / "slot1",
        state=SlotState.AVAILABLE,
    )
    
    slot_store.save_slot(slot)
    loaded = slot_store.load_slot("workspace-test-repo-123-slot1")
    
    assert loaded.repo_name == "test-repo-123"


def test_multiple_pools(slot_store, workspaces_dir):
    """Test managing multiple pools."""
    now = datetime.now()
    
    # Create two pools
    pool1 = Pool(
        repo_name="repo-one",
        repo_url="https://github.com/test/repo-one.git",
        num_slots=1,
        slots=[],
        created_at=now,
        updated_at=now,
    )
    
    pool2 = Pool(
        repo_name="repo-two",
        repo_url="https://github.com/test/repo-two.git",
        num_slots=1,
        slots=[],
        created_at=now,
        updated_at=now,
    )
    
    slot_store.save_pool(pool1)
    slot_store.save_pool(pool2)
    
    # Verify both pools exist
    assert slot_store.pool_exists("repo-one")
    assert slot_store.pool_exists("repo-two")
    
    # Load both pools
    loaded1 = slot_store.load_pool("repo-one")
    loaded2 = slot_store.load_pool("repo-two")
    
    assert loaded1.repo_name == "repo-one"
    assert loaded2.repo_name == "repo-two"


def test_slot_update_preserves_other_fields(slot_store, sample_slot):
    """Test updating slot preserves other fields."""
    # Save initial slot
    sample_slot.allocation_count = 5
    sample_slot.metadata = {"key": "value"}
    slot_store.save_slot(sample_slot)
    
    # Load and update
    loaded = slot_store.load_slot("workspace-test-repo-slot1")
    loaded.state = SlotState.ALLOCATED
    slot_store.save_slot(loaded)
    
    # Load again and verify
    final = slot_store.load_slot("workspace-test-repo-slot1")
    assert final.state == SlotState.ALLOCATED
    assert final.allocation_count == 5
    assert final.metadata["key"] == "value"

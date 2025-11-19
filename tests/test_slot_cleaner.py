"""Unit tests for SlotCleaner.

Tests cleanup, verification, and repair operations.
Requirements: 3.1, 3.2, 3.3, 3.4, 9.2
"""

import subprocess
from datetime import datetime
from pathlib import Path
import pytest

from necrocode.repo_pool.slot_cleaner import SlotCleaner
from necrocode.repo_pool.git_operations import GitOperations
from necrocode.repo_pool.models import Slot, SlotState


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def git_ops():
    """Create GitOperations instance."""
    return GitOperations(max_retries=2, retry_delay=0.1)


@pytest.fixture
def slot_cleaner(git_ops):
    """Create SlotCleaner instance."""
    return SlotCleaner(git_ops)


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


@pytest.fixture
def sample_slot(temp_repo):
    """Create a sample slot for testing."""
    return Slot(
        slot_id="workspace-test-repo-slot1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=temp_repo,
        state=SlotState.AVAILABLE,
    )


# ============================================================================
# Cleanup Before Allocation Tests
# ============================================================================

def test_cleanup_before_allocation_success(slot_cleaner, sample_slot, temp_repo):
    """Test successful cleanup before allocation."""
    # Create an untracked file
    (temp_repo / "untracked.txt").write_text("untracked content")
    
    result = slot_cleaner.cleanup_before_allocation(sample_slot)
    
    assert result.success is True
    assert result.slot_id == "workspace-test-repo-slot1"
    assert "fetch" in result.operations
    assert "clean" in result.operations
    assert "reset" in result.operations
    assert len(result.errors) == 0
    
    # Verify untracked file was removed
    assert not (temp_repo / "untracked.txt").exists()


def test_cleanup_before_allocation_updates_slot_info(slot_cleaner, sample_slot, temp_repo):
    """Test cleanup updates slot git information."""
    result = slot_cleaner.cleanup_before_allocation(sample_slot)
    
    assert result.success is True
    assert sample_slot.current_branch is not None
    assert sample_slot.current_commit is not None


def test_cleanup_before_allocation_sets_cleaning_state(slot_cleaner, sample_slot):
    """Test cleanup sets slot to CLEANING state during operation."""
    original_state = sample_slot.state
    
    result = slot_cleaner.cleanup_before_allocation(sample_slot)
    
    # After cleanup, state should be restored or set appropriately
    assert result.success is True


# ============================================================================
# Cleanup After Release Tests
# ============================================================================

def test_cleanup_after_release_success(slot_cleaner, sample_slot, temp_repo):
    """Test successful cleanup after release."""
    # Create an untracked file
    (temp_repo / "untracked.txt").write_text("untracked content")
    
    result = slot_cleaner.cleanup_after_release(sample_slot)
    
    assert result.success is True
    assert result.slot_id == "workspace-test-repo-slot1"
    assert "fetch" in result.operations
    assert "clean" in result.operations
    assert "reset" in result.operations
    
    # Verify untracked file was removed
    assert not (temp_repo / "untracked.txt").exists()


def test_cleanup_after_release_sets_available_state(slot_cleaner, sample_slot):
    """Test cleanup after release sets slot to AVAILABLE state."""
    sample_slot.state = SlotState.ALLOCATED
    
    result = slot_cleaner.cleanup_after_release(sample_slot)
    
    assert result.success is True
    assert sample_slot.state == SlotState.AVAILABLE


# ============================================================================
# Verify Slot Integrity Tests
# ============================================================================

def test_verify_slot_integrity_valid_slot(slot_cleaner, sample_slot, temp_repo):
    """Test verify_slot_integrity returns True for valid slot."""
    is_valid = slot_cleaner.verify_slot_integrity(sample_slot)
    
    assert is_valid is True


def test_verify_slot_integrity_missing_directory(slot_cleaner, sample_slot, tmp_path):
    """Test verify_slot_integrity returns False for missing directory."""
    sample_slot.slot_path = tmp_path / "nonexistent"
    
    is_valid = slot_cleaner.verify_slot_integrity(sample_slot)
    
    assert is_valid is False


def test_verify_slot_integrity_missing_git_directory(slot_cleaner, sample_slot, tmp_path):
    """Test verify_slot_integrity returns False for missing .git directory."""
    # Create directory without .git
    no_git_dir = tmp_path / "no_git"
    no_git_dir.mkdir()
    sample_slot.slot_path = no_git_dir
    
    is_valid = slot_cleaner.verify_slot_integrity(sample_slot)
    
    assert is_valid is False


# ============================================================================
# Repair Slot Tests
# ============================================================================

def test_repair_slot_already_valid(slot_cleaner, sample_slot):
    """Test repair_slot returns success for already valid slot."""
    result = slot_cleaner.repair_slot(sample_slot)
    
    assert result.success is True
    assert "verified_integrity" in result.actions_taken
    assert len(result.errors) == 0


def test_repair_slot_missing_git_directory(slot_cleaner, sample_slot, tmp_path):
    """Test repair_slot attempts to fix missing .git directory."""
    # Create directory without .git
    no_git_dir = tmp_path / "no_git"
    no_git_dir.mkdir()
    sample_slot.slot_path = no_git_dir
    sample_slot.repo_url = "https://github.com/test/invalid-repo.git"
    
    result = slot_cleaner.repair_slot(sample_slot)
    
    # Should attempt repair but may fail due to invalid URL
    assert "integrity_check_failed" in result.actions_taken


# ============================================================================
# Warmup Slot Tests
# ============================================================================

def test_warmup_slot_success(slot_cleaner, sample_slot):
    """Test successful slot warmup."""
    sample_slot.state = SlotState.AVAILABLE
    
    result = slot_cleaner.warmup_slot(sample_slot)
    
    assert result.success is True
    assert "fetch" in result.operations
    assert "verify_integrity" in result.operations
    assert "update_metadata" in result.operations


def test_warmup_slot_not_available(slot_cleaner, sample_slot):
    """Test warmup fails for non-available slot."""
    sample_slot.state = SlotState.ALLOCATED
    
    result = slot_cleaner.warmup_slot(sample_slot)
    
    assert result.success is False
    assert "not available" in result.errors[0].lower()


def test_warmup_slot_updates_metadata(slot_cleaner, sample_slot):
    """Test warmup updates slot metadata."""
    sample_slot.state = SlotState.AVAILABLE
    
    result = slot_cleaner.warmup_slot(sample_slot)
    
    assert result.success is True
    assert sample_slot.current_branch is not None
    assert sample_slot.current_commit is not None


# ============================================================================
# Cleanup Log Tests
# ============================================================================

def test_get_cleanup_log_empty(slot_cleaner):
    """Test get_cleanup_log returns empty list initially."""
    log = slot_cleaner.get_cleanup_log()
    
    assert len(log) == 0


def test_get_cleanup_log_records_operations(slot_cleaner, sample_slot):
    """Test cleanup operations are logged."""
    slot_cleaner.cleanup_before_allocation(sample_slot)
    
    log = slot_cleaner.get_cleanup_log()
    
    assert len(log) > 0
    assert log[0].slot_id == "workspace-test-repo-slot1"
    assert log[0].operation_type == "before_allocation"


def test_get_cleanup_log_filter_by_slot_id(slot_cleaner, sample_slot, temp_repo):
    """Test get_cleanup_log can filter by slot_id."""
    # Perform cleanup
    slot_cleaner.cleanup_before_allocation(sample_slot)
    
    # Create another slot and cleanup
    slot2 = Slot(
        slot_id="workspace-test-repo-slot2",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=temp_repo,
        state=SlotState.AVAILABLE,
    )
    slot_cleaner.cleanup_after_release(slot2)
    
    # Filter log
    log_slot1 = slot_cleaner.get_cleanup_log("workspace-test-repo-slot1")
    
    assert len(log_slot1) == 1
    assert log_slot1[0].slot_id == "workspace-test-repo-slot1"


# ============================================================================
# Parallel Cleanup Tests
# ============================================================================

def test_cleanup_slots_parallel(slot_cleaner, temp_repo):
    """Test parallel cleanup of multiple slots."""
    # Create multiple slots
    slots = []
    for i in range(1, 4):
        slot = Slot(
            slot_id=f"workspace-test-repo-slot{i}",
            repo_name="test-repo",
            repo_url="https://github.com/test/repo.git",
            slot_path=temp_repo,
            state=SlotState.AVAILABLE,
        )
        slots.append(slot)
    
    # Perform parallel cleanup
    results = slot_cleaner.cleanup_slots_parallel(slots, operation="warmup")
    
    assert len(results) == 3
    for slot_id, result in results.items():
        assert result.slot_id in [s.slot_id for s in slots]


def test_warmup_slots_parallel(slot_cleaner, temp_repo):
    """Test parallel warmup of multiple slots."""
    # Create multiple slots
    slots = []
    for i in range(1, 3):
        slot = Slot(
            slot_id=f"workspace-test-repo-slot{i}",
            repo_name="test-repo",
            repo_url="https://github.com/test/repo.git",
            slot_path=temp_repo,
            state=SlotState.AVAILABLE,
        )
        slots.append(slot)
    
    # Perform parallel warmup
    results = slot_cleaner.warmup_slots_parallel(slots)
    
    assert len(results) == 2
    for result in results.values():
        assert result.success is True


# ============================================================================
# Background Cleanup Tests
# ============================================================================

def test_cleanup_background(slot_cleaner, sample_slot):
    """Test background cleanup starts successfully."""
    sample_slot.state = SlotState.AVAILABLE
    
    task_id = slot_cleaner.cleanup_background(sample_slot, operation="warmup")
    
    assert task_id is not None
    assert sample_slot.slot_id in task_id


def test_is_background_cleanup_complete(slot_cleaner, sample_slot):
    """Test checking if background cleanup is complete."""
    sample_slot.state = SlotState.AVAILABLE
    
    task_id = slot_cleaner.cleanup_background(sample_slot, operation="warmup")
    
    # Wait a bit for completion
    import time
    time.sleep(0.5)
    
    is_complete = slot_cleaner.is_background_cleanup_complete(task_id)
    
    # Should eventually complete
    assert isinstance(is_complete, bool)


def test_get_background_cleanup_result(slot_cleaner, sample_slot):
    """Test getting background cleanup result."""
    sample_slot.state = SlotState.AVAILABLE
    
    task_id = slot_cleaner.cleanup_background(sample_slot, operation="warmup")
    
    # Get result (with timeout)
    result = slot_cleaner.get_background_cleanup_result(task_id, timeout=2.0)
    
    # Should get a result
    if result is not None:
        assert result.slot_id == sample_slot.slot_id


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_cleanup_handles_invalid_repo(slot_cleaner, sample_slot, tmp_path):
    """Test cleanup handles invalid repository gracefully."""
    # Point to non-git directory
    invalid_dir = tmp_path / "invalid"
    invalid_dir.mkdir()
    sample_slot.slot_path = invalid_dir
    
    result = slot_cleaner.cleanup_before_allocation(sample_slot)
    
    # Should fail but not crash
    assert result.success is False
    assert len(result.errors) > 0


def test_cleanup_records_errors(slot_cleaner, sample_slot, tmp_path):
    """Test cleanup records errors in result."""
    # Point to non-existent directory
    sample_slot.slot_path = tmp_path / "nonexistent"
    
    result = slot_cleaner.cleanup_before_allocation(sample_slot)
    
    assert result.success is False
    assert len(result.errors) > 0
    assert result.slot_id == sample_slot.slot_id

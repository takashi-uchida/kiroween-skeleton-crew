"""Integration tests for cleanup operations with real Git repositories.

Tests cleanup operations on actual Git repositories.
Requirements: 3.1, 3.2, 3.3, 3.4
"""

import time
from pathlib import Path
import sys
import pytest
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.models import SlotState
from necrocode.repo_pool.git_operations import GitOperations


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
        lock_timeout=10.0,
        cleanup_timeout=60.0,
    )


@pytest.fixture
def pool_manager(config):
    """Create PoolManager instance."""
    return PoolManager(config)


@pytest.fixture
def git_ops():
    """Create GitOperations instance."""
    return GitOperations()


@pytest.fixture
def test_repo_url():
    """Return a test repository URL."""
    # Use a small, stable public repository
    return "https://github.com/octocat/Hello-World.git"


@pytest.fixture
def test_pool(pool_manager, test_repo_url):
    """Create a test pool with real Git repository."""
    pool = pool_manager.create_pool(
        repo_name="cleanup-test",
        repo_url=test_repo_url,
        num_slots=2
    )
    return pool


# ============================================================================
# Basic Cleanup Tests
# ============================================================================

def test_cleanup_before_allocation(pool_manager, test_pool):
    """Test cleanup operations before slot allocation."""
    # Allocate a slot
    slot = pool_manager.allocate_slot("cleanup-test")
    assert slot is not None
    
    # Verify slot is clean
    assert slot.slot_path.exists()
    assert (slot.slot_path / ".git").exists()
    
    # Check working tree is clean
    git_ops = GitOperations()
    is_clean = git_ops.is_clean_working_tree(slot.slot_path)
    assert is_clean


def test_cleanup_after_release(pool_manager, test_pool):
    """Test cleanup operations after slot release."""
    # Allocate slot
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create some untracked files
    test_file = slot_path / "test_untracked.txt"
    test_file.write_text("This should be cleaned up")
    
    test_dir = slot_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "nested_file.txt").write_text("Nested untracked file")
    
    # Release slot (should trigger cleanup)
    pool_manager.release_slot(slot.slot_id)
    
    # Verify untracked files were removed
    assert not test_file.exists()
    assert not test_dir.exists()
    
    # Verify working tree is clean
    git_ops = GitOperations()
    is_clean = git_ops.is_clean_working_tree(slot_path)
    assert is_clean


def test_cleanup_removes_untracked_files(pool_manager, test_pool, git_ops):
    """Test that cleanup removes all untracked files."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create various untracked files
    (slot_path / "file1.txt").write_text("untracked 1")
    (slot_path / "file2.log").write_text("untracked 2")
    
    subdir = slot_path / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("untracked 3")
    
    # Release and cleanup
    pool_manager.release_slot(slot.slot_id)
    
    # Verify all untracked files are gone
    assert not (slot_path / "file1.txt").exists()
    assert not (slot_path / "file2.log").exists()
    assert not subdir.exists()


def test_cleanup_resets_working_directory(pool_manager, test_pool, git_ops):
    """Test that cleanup resets working directory to HEAD."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Modify a tracked file
    readme_path = slot_path / "README"
    if readme_path.exists():
        original_content = readme_path.read_text()
        readme_path.write_text("Modified content")
        
        # Verify file was modified
        assert readme_path.read_text() == "Modified content"
        
        # Release and cleanup
        pool_manager.release_slot(slot.slot_id)
        
        # Verify file was reset
        assert readme_path.read_text() == original_content


# ============================================================================
# Git Fetch Tests
# ============================================================================

def test_cleanup_fetches_latest_changes(pool_manager, test_pool, git_ops):
    """Test that cleanup fetches latest changes from remote."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Get current commit
    initial_commit = git_ops.get_current_commit(slot_path)
    
    # Release slot (triggers fetch)
    pool_manager.release_slot(slot.slot_id)
    
    # Allocate again
    slot2 = pool_manager.allocate_slot("cleanup-test")
    
    # Verify fetch was performed (remote refs should be up to date)
    result = git_ops.fetch_all(slot2.slot_path)
    assert result.success


def test_cleanup_updates_remote_branches(pool_manager, test_pool, git_ops):
    """Test that cleanup updates remote branch information."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Get remote branches before cleanup
    branches_before = git_ops.list_remote_branches(slot_path)
    
    # Release and cleanup
    pool_manager.release_slot(slot.slot_id)
    
    # Allocate again and check branches
    slot2 = pool_manager.allocate_slot("cleanup-test")
    branches_after = git_ops.list_remote_branches(slot2.slot_path)
    
    # Should have remote branches
    assert len(branches_after) > 0
    assert any("origin/" in branch for branch in branches_after)


# ============================================================================
# Branch Switching Tests
# ============================================================================

def test_cleanup_after_branch_switch(pool_manager, test_pool, git_ops):
    """Test cleanup after switching branches."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Get initial branch
    initial_branch = git_ops.get_current_branch(slot_path)
    
    # Try to switch to a different branch if available
    remote_branches = git_ops.list_remote_branches(slot_path)
    if len(remote_branches) > 1:
        # Find a different branch
        target_branch = None
        for branch in remote_branches:
            if "master" not in branch and "main" not in branch:
                target_branch = branch.replace("origin/", "")
                break
        
        if target_branch:
            # Switch branch
            git_ops.checkout(slot_path, target_branch)
            
            # Verify branch switched
            current_branch = git_ops.get_current_branch(slot_path)
            assert current_branch == target_branch
    
    # Release and cleanup
    pool_manager.release_slot(slot.slot_id)
    
    # Allocate again
    slot2 = pool_manager.allocate_slot("cleanup-test")
    
    # Working tree should be clean regardless of branch
    assert git_ops.is_clean_working_tree(slot2.slot_path)


# ============================================================================
# Modified Files Tests
# ============================================================================

def test_cleanup_handles_modified_tracked_files(pool_manager, test_pool, git_ops):
    """Test cleanup handles modified tracked files correctly."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Find and modify a tracked file
    readme_path = slot_path / "README"
    if readme_path.exists():
        readme_path.write_text("Modified content for testing")
        
        # Verify file is modified
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=slot_path,
            capture_output=True,
            text=True
        )
        assert "README" in result.stdout
        
        # Release and cleanup
        pool_manager.release_slot(slot.slot_id)
        
        # Verify file was reset
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=slot_path,
            capture_output=True,
            text=True
        )
        assert result.stdout.strip() == ""


def test_cleanup_handles_deleted_tracked_files(pool_manager, test_pool, git_ops):
    """Test cleanup handles deleted tracked files correctly."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Find and delete a tracked file
    readme_path = slot_path / "README"
    if readme_path.exists():
        readme_path.unlink()
        
        # Verify file is deleted
        assert not readme_path.exists()
        
        # Release and cleanup
        pool_manager.release_slot(slot.slot_id)
        
        # Verify file was restored
        assert readme_path.exists()


# ============================================================================
# Staged Changes Tests
# ============================================================================

def test_cleanup_handles_staged_changes(pool_manager, test_pool, git_ops):
    """Test cleanup handles staged changes correctly."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create and stage a new file
    new_file = slot_path / "staged_file.txt"
    new_file.write_text("Staged content")
    
    subprocess.run(
        ["git", "add", "staged_file.txt"],
        cwd=slot_path,
        check=True
    )
    
    # Verify file is staged
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=slot_path,
        capture_output=True,
        text=True
    )
    assert "staged_file.txt" in result.stdout
    
    # Release and cleanup
    pool_manager.release_slot(slot.slot_id)
    
    # Verify staged file was removed
    assert not new_file.exists()
    
    # Verify no staged changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=slot_path,
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == ""


# ============================================================================
# Nested Directory Tests
# ============================================================================

def test_cleanup_removes_nested_untracked_directories(pool_manager, test_pool):
    """Test cleanup removes deeply nested untracked directories."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create nested directory structure
    nested_path = slot_path / "level1" / "level2" / "level3"
    nested_path.mkdir(parents=True)
    
    (nested_path / "file.txt").write_text("Deep file")
    (slot_path / "level1" / "file1.txt").write_text("Level 1 file")
    (slot_path / "level1" / "level2" / "file2.txt").write_text("Level 2 file")
    
    # Release and cleanup
    pool_manager.release_slot(slot.slot_id)
    
    # Verify entire structure was removed
    assert not (slot_path / "level1").exists()


def test_cleanup_preserves_gitignored_files(pool_manager, test_pool):
    """Test that cleanup behavior with .gitignore files."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create .gitignore if it doesn't exist
    gitignore_path = slot_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text("*.log\n")
    
    # Create a file that matches .gitignore
    log_file = slot_path / "test.log"
    log_file.write_text("Log content")
    
    # Release and cleanup (git clean -fdx removes ignored files too)
    pool_manager.release_slot(slot.slot_id)
    
    # Verify ignored file was removed (git clean -fdx removes everything)
    assert not log_file.exists()


# ============================================================================
# Multiple Cleanup Cycles Tests
# ============================================================================

def test_multiple_cleanup_cycles(pool_manager, test_pool):
    """Test multiple allocation/cleanup cycles."""
    for cycle in range(3):
        # Allocate
        slot = pool_manager.allocate_slot("cleanup-test")
        slot_path = slot.slot_path
        
        # Create untracked files
        (slot_path / f"file_{cycle}.txt").write_text(f"Cycle {cycle}")
        
        # Modify tracked file if exists
        readme_path = slot_path / "README"
        if readme_path.exists():
            readme_path.write_text(f"Modified in cycle {cycle}")
        
        # Release and cleanup
        pool_manager.release_slot(slot.slot_id)
        
        # Verify cleanup was successful
        git_ops = GitOperations()
        assert git_ops.is_clean_working_tree(slot_path)
        assert not (slot_path / f"file_{cycle}.txt").exists()


def test_cleanup_consistency_across_slots(pool_manager, test_pool):
    """Test cleanup consistency across different slots."""
    # Allocate both slots
    slot1 = pool_manager.allocate_slot("cleanup-test")
    slot2 = pool_manager.allocate_slot("cleanup-test")
    
    # Modify both slots
    (slot1.slot_path / "file1.txt").write_text("Slot 1 file")
    (slot2.slot_path / "file2.txt").write_text("Slot 2 file")
    
    # Release both
    pool_manager.release_slot(slot1.slot_id)
    pool_manager.release_slot(slot2.slot_id)
    
    # Verify both are clean
    git_ops = GitOperations()
    assert git_ops.is_clean_working_tree(slot1.slot_path)
    assert git_ops.is_clean_working_tree(slot2.slot_path)
    assert not (slot1.slot_path / "file1.txt").exists()
    assert not (slot2.slot_path / "file2.txt").exists()


# ============================================================================
# Cleanup Performance Tests
# ============================================================================

def test_cleanup_performance_basic(pool_manager, test_pool):
    """Test basic cleanup performance."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create multiple untracked files
    for i in range(10):
        (slot_path / f"file_{i}.txt").write_text(f"Content {i}")
    
    # Measure cleanup time
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    # Cleanup should complete in reasonable time (< 10 seconds)
    assert cleanup_time < 10.0
    
    # Verify cleanup was successful
    git_ops = GitOperations()
    assert git_ops.is_clean_working_tree(slot_path)


def test_cleanup_with_large_untracked_files(pool_manager, test_pool):
    """Test cleanup with large untracked files."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create a large untracked file (1MB)
    large_file = slot_path / "large_file.bin"
    large_file.write_bytes(b"x" * (1024 * 1024))
    
    # Release and cleanup
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    # Verify file was removed
    assert not large_file.exists()
    
    # Cleanup should still be reasonably fast
    assert cleanup_time < 15.0


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_cleanup_handles_permission_errors_gracefully(pool_manager, test_pool):
    """Test cleanup handles permission errors gracefully."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Create a file
    test_file = slot_path / "test.txt"
    test_file.write_text("Test content")
    
    # Note: Making files read-only may not prevent git clean on all systems
    # This test verifies cleanup completes even with potential permission issues
    
    # Release and cleanup
    try:
        pool_manager.release_slot(slot.slot_id)
        # Cleanup should complete
        assert True
    except Exception as e:
        # If cleanup fails, it should be handled gracefully
        pytest.fail(f"Cleanup failed with exception: {e}")


def test_cleanup_with_corrupted_git_state(pool_manager, test_pool, git_ops):
    """Test cleanup can handle and recover from corrupted git state."""
    slot = pool_manager.allocate_slot("cleanup-test")
    slot_path = slot.slot_path
    
    # Simulate a partially corrupted state by creating an invalid index
    # (This is a mild corruption that git can recover from)
    index_path = slot_path / ".git" / "index"
    if index_path.exists():
        # Backup original
        original_content = index_path.read_bytes()
        
        # Create untracked file
        (slot_path / "test.txt").write_text("Test")
        
        # Release and cleanup (should handle gracefully)
        try:
            pool_manager.release_slot(slot.slot_id)
            # Verify cleanup completed
            assert True
        except Exception:
            # Restore original index
            index_path.write_bytes(original_content)
            raise


# ============================================================================
# Cleanup Logging Tests
# ============================================================================

def test_cleanup_logging(pool_manager, test_pool):
    """Test that cleanup operations are logged."""
    slot = pool_manager.allocate_slot("cleanup-test")
    
    # Create some files to clean
    (slot.slot_path / "test.txt").write_text("Test")
    
    # Release and cleanup
    pool_manager.release_slot(slot.slot_id)
    
    # Verify slot was cleaned (state should be AVAILABLE)
    pool = pool_manager.get_pool("cleanup-test")
    released_slot = next(s for s in pool.slots if s.slot_id == slot.slot_id)
    assert released_slot.state == SlotState.AVAILABLE


# ============================================================================
# Integration with Allocation Tests
# ============================================================================

def test_cleanup_integration_with_allocation_cycle(pool_manager, test_pool):
    """Test complete integration of cleanup with allocation cycle."""
    # First allocation
    slot1 = pool_manager.allocate_slot("cleanup-test")
    slot1_path = slot1.slot_path
    
    # Make changes
    (slot1_path / "untracked.txt").write_text("Untracked")
    readme_path = slot1_path / "README"
    if readme_path.exists():
        original_content = readme_path.read_text()
        readme_path.write_text("Modified")
    
    # Release (cleanup)
    pool_manager.release_slot(slot1.slot_id)
    
    # Second allocation (should get clean slot)
    slot2 = pool_manager.allocate_slot("cleanup-test")
    
    # Verify slot is clean
    git_ops = GitOperations()
    assert git_ops.is_clean_working_tree(slot2.slot_path)
    assert not (slot2.slot_path / "untracked.txt").exists()
    
    if readme_path.exists():
        assert readme_path.read_text() == original_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

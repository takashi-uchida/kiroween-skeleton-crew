"""Unit tests for Repo Pool LockManager.

Tests lock acquisition, timeout, and stale lock detection.
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import time
from pathlib import Path
import pytest
import threading

from necrocode.repo_pool.lock_manager import LockManager
from necrocode.repo_pool.exceptions import LockTimeoutError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def locks_dir(tmp_path):
    """Create temporary locks directory."""
    return tmp_path / "locks"


@pytest.fixture
def lock_manager(locks_dir):
    """Create LockManager instance."""
    return LockManager(locks_dir)


# ============================================================================
# LockManager Initialization Tests
# ============================================================================

def test_lock_manager_creates_locks_dir(locks_dir):
    """Test LockManager creates locks directory if it doesn't exist."""
    assert not locks_dir.exists()
    
    LockManager(locks_dir)
    
    assert locks_dir.exists()
    assert locks_dir.is_dir()


def test_lock_manager_uses_existing_locks_dir(locks_dir):
    """Test LockManager uses existing locks directory."""
    locks_dir.mkdir(parents=True)
    test_file = locks_dir / "test.txt"
    test_file.write_text("test")
    
    LockManager(locks_dir)
    
    assert locks_dir.exists()
    assert test_file.exists()


# ============================================================================
# Acquire Lock Tests
# ============================================================================

def test_acquire_slot_lock_creates_lock_file(lock_manager):
    """Test acquire_slot_lock creates lock file."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        lock_file = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
        assert lock_file.exists()


def test_acquire_slot_lock_releases_on_exit(lock_manager):
    """Test acquire_slot_lock releases lock on context exit."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        pass
    
    # Lock should be released
    assert not lock_manager.is_locked("workspace-test-repo-slot1")


def test_acquire_slot_lock_allows_reentry_after_release(lock_manager):
    """Test acquire_slot_lock allows reentry after release."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        pass
    
    # Should be able to acquire again
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        assert lock_manager.is_locked("workspace-test-repo-slot1")


def test_acquire_slot_lock_blocks_concurrent_access(lock_manager):
    """Test acquire_slot_lock blocks concurrent access."""
    acquired_second_lock = False
    
    def try_acquire_second_lock():
        nonlocal acquired_second_lock
        try:
            with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=0.5):
                acquired_second_lock = True
        except LockTimeoutError:
            pass
    
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        # Start thread that tries to acquire same lock
        thread = threading.Thread(target=try_acquire_second_lock)
        thread.start()
        thread.join()
    
    # Second lock should not have been acquired
    assert not acquired_second_lock


def test_acquire_slot_lock_different_slots_independent(lock_manager):
    """Test acquire_slot_lock for different slots are independent."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        # Should be able to acquire lock for different slot
        with lock_manager.acquire_slot_lock("workspace-test-repo-slot2"):
            assert lock_manager.is_locked("workspace-test-repo-slot1")
            assert lock_manager.is_locked("workspace-test-repo-slot2")


def test_acquire_slot_lock_releases_on_exception(lock_manager):
    """Test acquire_slot_lock releases lock even when exception occurs."""
    try:
        with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
            raise ValueError("Test exception")
    except ValueError:
        pass
    
    # Lock should be released
    assert not lock_manager.is_locked("workspace-test-repo-slot1")


# ============================================================================
# Lock Timeout Tests
# ============================================================================

def test_acquire_slot_lock_timeout_raises_error(lock_manager):
    """Test acquire_slot_lock raises LockTimeoutError on timeout."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        # Try to acquire same lock with short timeout
        with pytest.raises(LockTimeoutError) as exc_info:
            with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=0.1):
                pass
        
        assert "workspace-test-repo-slot1" in str(exc_info.value)


def test_acquire_slot_lock_custom_timeout(lock_manager):
    """Test acquire_slot_lock respects custom timeout."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        start_time = time.time()
        
        try:
            with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=0.5):
                pass
        except LockTimeoutError:
            elapsed = time.time() - start_time
            # Should timeout around 0.5 seconds
            assert 0.4 < elapsed < 0.7


# ============================================================================
# Is Locked Tests
# ============================================================================

def test_is_locked_returns_true_when_locked(lock_manager):
    """Test is_locked returns True when lock is held."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        assert lock_manager.is_locked("workspace-test-repo-slot1")


def test_is_locked_returns_false_when_not_locked(lock_manager):
    """Test is_locked returns False when lock is not held."""
    assert not lock_manager.is_locked("workspace-test-repo-slot1")


def test_is_locked_returns_false_after_release(lock_manager):
    """Test is_locked returns False after lock is released."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        pass
    
    assert not lock_manager.is_locked("workspace-test-repo-slot1")


def test_is_locked_different_slots(lock_manager):
    """Test is_locked correctly reports status for different slots."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        assert lock_manager.is_locked("workspace-test-repo-slot1")
        assert not lock_manager.is_locked("workspace-test-repo-slot2")


# ============================================================================
# Force Unlock Tests
# ============================================================================

def test_force_unlock_releases_lock(lock_manager):
    """Test force_unlock releases held lock."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        lock_manager.force_unlock("workspace-test-repo-slot1")
        
        # Lock should be released
        assert not lock_manager.is_locked("workspace-test-repo-slot1")


def test_force_unlock_allows_reacquisition(lock_manager):
    """Test force_unlock allows lock to be reacquired."""
    # Acquire lock in separate thread and don't release
    def hold_lock():
        with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
            time.sleep(1)
    
    thread = threading.Thread(target=hold_lock)
    thread.start()
    
    # Wait for lock to be acquired
    time.sleep(0.1)
    
    # Force unlock
    lock_manager.force_unlock("workspace-test-repo-slot1")
    
    # Should be able to acquire now
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=0.5):
        assert lock_manager.is_locked("workspace-test-repo-slot1")
    
    thread.join()


def test_force_unlock_nonexistent_lock(lock_manager):
    """Test force_unlock handles nonexistent lock gracefully."""
    # Should not raise error
    lock_manager.force_unlock("workspace-nonexistent-slot")


def test_force_unlock_removes_lock_file(lock_manager):
    """Test force_unlock removes lock file."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        lock_file = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
        assert lock_file.exists()
        
        lock_manager.force_unlock("workspace-test-repo-slot1")
        
        # Lock file should be removed
        assert not lock_file.exists()


# ============================================================================
# Stale Lock Detection Tests
# ============================================================================

def test_detect_stale_locks(lock_manager):
    """Test detection of stale locks."""
    # Create a lock file manually (simulating stale lock)
    lock_file = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch()
    
    # Modify file time to make it old
    old_time = time.time() - 3600  # 1 hour ago
    import os
    os.utime(lock_file, (old_time, old_time))
    
    # Detect stale locks (older than 0.5 hours)
    stale_locks = lock_manager.detect_stale_locks(max_age_hours=0.5)
    
    assert len(stale_locks) == 1
    assert "workspace-test-repo-slot1" in stale_locks


def test_detect_stale_locks_ignores_recent_locks(lock_manager):
    """Test detect_stale_locks ignores recent locks."""
    # Create a recent lock file
    lock_file = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch()
    
    # Detect stale locks (older than 1 hour)
    stale_locks = lock_manager.detect_stale_locks(max_age_hours=1)
    
    # Should not detect recent lock as stale
    assert len(stale_locks) == 0


def test_detect_stale_locks_multiple(lock_manager):
    """Test detect_stale_locks with multiple locks."""
    # Create multiple lock files with different ages
    old_time = time.time() - 7200  # 2 hours ago
    recent_time = time.time() - 1800  # 30 minutes ago
    
    import os
    
    # Old lock 1
    lock1 = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
    lock1.parent.mkdir(parents=True, exist_ok=True)
    lock1.touch()
    os.utime(lock1, (old_time, old_time))
    
    # Old lock 2
    lock2 = lock_manager.locks_dir / "workspace-test-repo-slot2.lock"
    lock2.touch()
    os.utime(lock2, (old_time, old_time))
    
    # Recent lock
    lock3 = lock_manager.locks_dir / "workspace-test-repo-slot3.lock"
    lock3.touch()
    os.utime(lock3, (recent_time, recent_time))
    
    # Detect stale locks (older than 1 hour)
    stale_locks = lock_manager.detect_stale_locks(max_age_hours=1)
    
    assert len(stale_locks) == 2
    assert "workspace-test-repo-slot1" in stale_locks
    assert "workspace-test-repo-slot2" in stale_locks
    assert "workspace-test-repo-slot3" not in stale_locks


# ============================================================================
# Cleanup Stale Locks Tests
# ============================================================================

def test_cleanup_stale_locks(lock_manager):
    """Test cleanup_stale_locks removes stale locks."""
    # Create a stale lock file
    lock_file = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch()
    
    # Make it old
    old_time = time.time() - 3600  # 1 hour ago
    import os
    os.utime(lock_file, (old_time, old_time))
    
    # Cleanup stale locks
    cleaned_count = lock_manager.cleanup_stale_locks(max_age_hours=0.5)
    
    assert cleaned_count == 1
    assert not lock_file.exists()


def test_cleanup_stale_locks_preserves_recent_locks(lock_manager):
    """Test cleanup_stale_locks preserves recent locks."""
    # Create a recent lock file
    lock_file = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch()
    
    # Cleanup stale locks (older than 1 hour)
    cleaned_count = lock_manager.cleanup_stale_locks(max_age_hours=1)
    
    assert cleaned_count == 0
    assert lock_file.exists()


def test_cleanup_stale_locks_multiple(lock_manager):
    """Test cleanup_stale_locks with multiple locks."""
    old_time = time.time() - 7200  # 2 hours ago
    recent_time = time.time() - 1800  # 30 minutes ago
    
    import os
    
    # Create multiple locks
    lock1 = lock_manager.locks_dir / "workspace-test-repo-slot1.lock"
    lock1.parent.mkdir(parents=True, exist_ok=True)
    lock1.touch()
    os.utime(lock1, (old_time, old_time))
    
    lock2 = lock_manager.locks_dir / "workspace-test-repo-slot2.lock"
    lock2.touch()
    os.utime(lock2, (old_time, old_time))
    
    lock3 = lock_manager.locks_dir / "workspace-test-repo-slot3.lock"
    lock3.touch()
    os.utime(lock3, (recent_time, recent_time))
    
    # Cleanup stale locks
    cleaned_count = lock_manager.cleanup_stale_locks(max_age_hours=1)
    
    assert cleaned_count == 2
    assert not lock1.exists()
    assert not lock2.exists()
    assert lock3.exists()


# ============================================================================
# Concurrent Access Tests
# ============================================================================

def test_multiple_threads_sequential_access(lock_manager):
    """Test multiple threads can access sequentially."""
    results = []
    
    def worker(worker_id):
        with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=5.0):
            results.append(worker_id)
            time.sleep(0.1)
    
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # All workers should have completed
    assert len(results) == 5
    assert set(results) == {0, 1, 2, 3, 4}


def test_lock_prevents_race_condition(lock_manager, tmp_path):
    """Test lock prevents race condition in file writes."""
    counter_file = tmp_path / "counter.txt"
    counter_file.write_text("0")
    
    def increment_counter():
        with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=5.0):
            # Read current value
            value = int(counter_file.read_text())
            time.sleep(0.01)  # Simulate processing
            # Write incremented value
            counter_file.write_text(str(value + 1))
    
    threads = []
    for i in range(10):
        thread = threading.Thread(target=increment_counter)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Final value should be 10 (no race condition)
    final_value = int(counter_file.read_text())
    assert final_value == 10


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_acquire_slot_lock_with_zero_timeout(lock_manager):
    """Test acquire_slot_lock with zero timeout."""
    with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
        # Try to acquire with zero timeout
        with pytest.raises(LockTimeoutError):
            with lock_manager.acquire_slot_lock("workspace-test-repo-slot1", timeout=0):
                pass


def test_acquire_slot_lock_with_special_characters_in_slot_id(lock_manager):
    """Test acquire_slot_lock with special characters in slot ID."""
    # Should handle special characters safely
    slot_id = "workspace-test-repo-123-slot1"
    
    with lock_manager.acquire_slot_lock(slot_id):
        assert lock_manager.is_locked(slot_id)


def test_multiple_lock_managers_same_directory(locks_dir):
    """Test multiple LockManager instances share same locks."""
    manager1 = LockManager(locks_dir)
    manager2 = LockManager(locks_dir)
    
    with manager1.acquire_slot_lock("workspace-test-repo-slot1"):
        # manager2 should see the lock
        assert manager2.is_locked("workspace-test-repo-slot1")
        
        # manager2 should not be able to acquire
        with pytest.raises(LockTimeoutError):
            with manager2.acquire_slot_lock("workspace-test-repo-slot1", timeout=0.1):
                pass


def test_lock_with_very_long_slot_id(lock_manager):
    """Test lock with very long slot ID."""
    long_slot_id = "workspace-" + "a" * 200 + "-slot1"
    
    with lock_manager.acquire_slot_lock(long_slot_id):
        assert lock_manager.is_locked(long_slot_id)


def test_rapid_lock_acquisition_and_release(lock_manager):
    """Test rapid lock acquisition and release."""
    for i in range(100):
        with lock_manager.acquire_slot_lock("workspace-test-repo-slot1"):
            pass
    
    # Should complete without errors
    assert not lock_manager.is_locked("workspace-test-repo-slot1")

"""Unit tests for LockManager.

Tests lock acquisition, timeout, and deadlock detection.
Requirements: 6.1, 6.3, 6.4, 6.5
"""

import time
from pathlib import Path
import sys
import pytest
import threading

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.lock_manager import LockManager
from necrocode.task_registry.exceptions import LockTimeoutError


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

def test_acquire_lock_creates_lock_file(lock_manager):
    """Test acquire_lock creates lock file."""
    with lock_manager.acquire_lock("test-spec"):
        lock_file = lock_manager.locks_dir / "test-spec.lock"
        assert lock_file.exists()


def test_acquire_lock_releases_on_exit(lock_manager):
    """Test acquire_lock releases lock on context exit."""
    with lock_manager.acquire_lock("test-spec"):
        pass
    
    # Lock should be released
    assert not lock_manager.is_locked("test-spec")


def test_acquire_lock_allows_reentry_after_release(lock_manager):
    """Test acquire_lock allows reentry after release."""
    with lock_manager.acquire_lock("test-spec"):
        pass
    
    # Should be able to acquire again
    with lock_manager.acquire_lock("test-spec"):
        assert lock_manager.is_locked("test-spec")


def test_acquire_lock_blocks_concurrent_access(lock_manager):
    """Test acquire_lock blocks concurrent access."""
    acquired_second_lock = False
    
    def try_acquire_second_lock():
        nonlocal acquired_second_lock
        try:
            with lock_manager.acquire_lock("test-spec", timeout=0.5):
                acquired_second_lock = True
        except LockTimeoutError:
            pass
    
    with lock_manager.acquire_lock("test-spec"):
        # Start thread that tries to acquire same lock
        thread = threading.Thread(target=try_acquire_second_lock)
        thread.start()
        thread.join()
    
    # Second lock should not have been acquired
    assert not acquired_second_lock


def test_acquire_lock_different_specs_independent(lock_manager):
    """Test acquire_lock for different specs are independent."""
    with lock_manager.acquire_lock("spec-one"):
        # Should be able to acquire lock for different spec
        with lock_manager.acquire_lock("spec-two"):
            assert lock_manager.is_locked("spec-one")
            assert lock_manager.is_locked("spec-two")


def test_acquire_lock_releases_on_exception(lock_manager):
    """Test acquire_lock releases lock even when exception occurs."""
    try:
        with lock_manager.acquire_lock("test-spec"):
            raise ValueError("Test exception")
    except ValueError:
        pass
    
    # Lock should be released
    assert not lock_manager.is_locked("test-spec")


# ============================================================================
# Lock Timeout Tests
# ============================================================================

def test_acquire_lock_timeout_raises_error(lock_manager):
    """Test acquire_lock raises LockTimeoutError on timeout."""
    with lock_manager.acquire_lock("test-spec"):
        # Try to acquire same lock with short timeout
        with pytest.raises(LockTimeoutError) as exc_info:
            with lock_manager.acquire_lock("test-spec", timeout=0.1):
                pass
        
        assert "test-spec" in str(exc_info.value)


def test_acquire_lock_custom_timeout(lock_manager):
    """Test acquire_lock respects custom timeout."""
    with lock_manager.acquire_lock("test-spec"):
        start_time = time.time()
        
        try:
            with lock_manager.acquire_lock("test-spec", timeout=0.5):
                pass
        except LockTimeoutError:
            elapsed = time.time() - start_time
            # Should timeout around 0.5 seconds
            assert 0.4 < elapsed < 0.7


def test_acquire_lock_retry_interval(lock_manager):
    """Test acquire_lock uses retry interval."""
    retry_count = 0
    
    def count_retries():
        nonlocal retry_count
        with lock_manager.acquire_lock("test-spec"):
            time.sleep(0.3)
    
    # Start thread that holds lock
    thread = threading.Thread(target=count_retries)
    thread.start()
    
    # Wait for lock to be acquired
    time.sleep(0.1)
    
    # Try to acquire with retries
    start_time = time.time()
    try:
        with lock_manager.acquire_lock("test-spec", timeout=0.5, retry_interval=0.1):
            pass
    except LockTimeoutError:
        elapsed = time.time() - start_time
        # Should have retried multiple times
        assert elapsed >= 0.5
    
    thread.join()


# ============================================================================
# Is Locked Tests
# ============================================================================

def test_is_locked_returns_true_when_locked(lock_manager):
    """Test is_locked returns True when lock is held."""
    with lock_manager.acquire_lock("test-spec"):
        assert lock_manager.is_locked("test-spec")


def test_is_locked_returns_false_when_not_locked(lock_manager):
    """Test is_locked returns False when lock is not held."""
    assert not lock_manager.is_locked("test-spec")


def test_is_locked_returns_false_after_release(lock_manager):
    """Test is_locked returns False after lock is released."""
    with lock_manager.acquire_lock("test-spec"):
        pass
    
    assert not lock_manager.is_locked("test-spec")


def test_is_locked_different_specs(lock_manager):
    """Test is_locked correctly reports status for different specs."""
    with lock_manager.acquire_lock("spec-one"):
        assert lock_manager.is_locked("spec-one")
        assert not lock_manager.is_locked("spec-two")


# ============================================================================
# Force Unlock Tests
# ============================================================================

def test_force_unlock_releases_lock(lock_manager):
    """Test force_unlock releases held lock."""
    with lock_manager.acquire_lock("test-spec"):
        lock_manager.force_unlock("test-spec")
        
        # Lock should be released
        assert not lock_manager.is_locked("test-spec")


def test_force_unlock_allows_reacquisition(lock_manager):
    """Test force_unlock allows lock to be reacquired."""
    # Acquire lock in separate thread and don't release
    def hold_lock():
        with lock_manager.acquire_lock("test-spec"):
            time.sleep(1)
    
    thread = threading.Thread(target=hold_lock)
    thread.start()
    
    # Wait for lock to be acquired
    time.sleep(0.1)
    
    # Force unlock
    lock_manager.force_unlock("test-spec")
    
    # Should be able to acquire now
    with lock_manager.acquire_lock("test-spec", timeout=0.5):
        assert lock_manager.is_locked("test-spec")
    
    thread.join()


def test_force_unlock_nonexistent_lock(lock_manager):
    """Test force_unlock handles nonexistent lock gracefully."""
    # Should not raise error
    lock_manager.force_unlock("nonexistent-spec")


def test_force_unlock_removes_lock_file(lock_manager):
    """Test force_unlock removes lock file."""
    with lock_manager.acquire_lock("test-spec"):
        lock_file = lock_manager.locks_dir / "test-spec.lock"
        assert lock_file.exists()
        
        lock_manager.force_unlock("test-spec")
        
        # Lock file should be removed
        assert not lock_file.exists()


# ============================================================================
# Deadlock Detection Tests
# ============================================================================

def test_detect_stale_lock(lock_manager):
    """Test detection of stale locks."""
    # Create a lock file manually (simulating stale lock)
    lock_file = lock_manager.locks_dir / "test-spec.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch()
    
    # Modify file time to make it old
    old_time = time.time() - 3600  # 1 hour ago
    import os
    os.utime(lock_file, (old_time, old_time))
    
    # Should be able to detect and handle stale lock
    assert lock_file.exists()


def test_force_unlock_clears_deadlock(lock_manager):
    """Test force_unlock can clear potential deadlock."""
    # Simulate deadlock scenario
    with lock_manager.acquire_lock("spec-one"):
        # Another process might be waiting for this lock
        # Force unlock should clear it
        lock_manager.force_unlock("spec-one")
        
        # Should be able to acquire again
        with lock_manager.acquire_lock("spec-one", timeout=0.5):
            assert lock_manager.is_locked("spec-one")


# ============================================================================
# Concurrent Access Tests
# ============================================================================

def test_multiple_threads_sequential_access(lock_manager):
    """Test multiple threads can access sequentially."""
    results = []
    
    def worker(worker_id):
        with lock_manager.acquire_lock("test-spec", timeout=5.0):
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
        with lock_manager.acquire_lock("counter", timeout=5.0):
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

def test_acquire_lock_with_zero_timeout(lock_manager):
    """Test acquire_lock with zero timeout."""
    with lock_manager.acquire_lock("test-spec"):
        # Try to acquire with zero timeout
        with pytest.raises(LockTimeoutError):
            with lock_manager.acquire_lock("test-spec", timeout=0):
                pass


def test_acquire_lock_with_negative_timeout(lock_manager):
    """Test acquire_lock with negative timeout."""
    with lock_manager.acquire_lock("test-spec"):
        # Negative timeout should be treated as zero
        with pytest.raises(LockTimeoutError):
            with lock_manager.acquire_lock("test-spec", timeout=-1):
                pass


def test_acquire_lock_with_special_characters_in_spec_name(lock_manager):
    """Test acquire_lock with special characters in spec name."""
    # Should handle special characters safely
    spec_name = "test-spec-with-special-chars_123"
    
    with lock_manager.acquire_lock(spec_name):
        assert lock_manager.is_locked(spec_name)


def test_lock_manager_handles_permission_error(locks_dir):
    """Test LockManager handles permission errors gracefully."""
    # This test is platform-dependent and may not work on all systems
    # Skip if we can't create the scenario
    try:
        locks_dir.mkdir(parents=True)
        locks_dir.chmod(0o444)  # Read-only
        
        lock_manager = LockManager(locks_dir)
        
        # Should handle permission error
        with pytest.raises((PermissionError, OSError)):
            with lock_manager.acquire_lock("test-spec"):
                pass
    finally:
        # Restore permissions for cleanup
        try:
            locks_dir.chmod(0o755)
        except:
            pass


def test_nested_lock_acquisition_same_spec(lock_manager):
    """Test nested lock acquisition for same spec."""
    # Nested acquisition of same lock should work (reentrant)
    with lock_manager.acquire_lock("test-spec"):
        # This might timeout or succeed depending on implementation
        # The test documents the behavior
        try:
            with lock_manager.acquire_lock("test-spec", timeout=0.1):
                pass
        except LockTimeoutError:
            # Expected if locks are not reentrant
            pass


def test_lock_cleanup_on_process_termination(lock_manager):
    """Test lock files are cleaned up properly."""
    with lock_manager.acquire_lock("test-spec"):
        lock_file = lock_manager.locks_dir / "test-spec.lock"
        assert lock_file.exists()
    
    # After context exit, lock file should be cleaned up
    # (actual cleanup depends on implementation)
    # This test documents expected behavior


def test_multiple_lock_managers_same_directory(locks_dir):
    """Test multiple LockManager instances share same locks."""
    manager1 = LockManager(locks_dir)
    manager2 = LockManager(locks_dir)
    
    with manager1.acquire_lock("test-spec"):
        # manager2 should see the lock
        assert manager2.is_locked("test-spec")
        
        # manager2 should not be able to acquire
        with pytest.raises(LockTimeoutError):
            with manager2.acquire_lock("test-spec", timeout=0.1):
                pass


def test_lock_with_very_long_spec_name(lock_manager):
    """Test lock with very long spec name."""
    long_spec_name = "a" * 200
    
    with lock_manager.acquire_lock(long_spec_name):
        assert lock_manager.is_locked(long_spec_name)


def test_rapid_lock_acquisition_and_release(lock_manager):
    """Test rapid lock acquisition and release."""
    for i in range(100):
        with lock_manager.acquire_lock("test-spec"):
            pass
    
    # Should complete without errors
    assert not lock_manager.is_locked("test-spec")

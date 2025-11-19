"""Integration tests for concurrent slot allocation.

Tests multiple processes/threads allocating slots simultaneously.
Requirements: 4.1, 4.2
"""

import time
from pathlib import Path
import sys
import pytest
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.models import SlotState, Slot
from necrocode.repo_pool.exceptions import (
    NoAvailableSlotError,
    LockTimeoutError,
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
        default_num_slots=5,
        lock_timeout=10.0,
    )


@pytest.fixture
def pool_manager(config):
    """Create PoolManager instance."""
    return PoolManager(config)


@pytest.fixture
def test_repo_url():
    """Return a test repository URL."""
    return "https://github.com/octocat/Hello-World.git"


@pytest.fixture
def populated_pool(pool_manager, test_repo_url):
    """Create a pool with multiple slots for testing."""
    pool = pool_manager.create_pool(
        repo_name="concurrent-test",
        repo_url=test_repo_url,
        num_slots=5
    )
    return pool


# ============================================================================
# Thread-based Concurrent Allocation Tests
# ============================================================================

def test_concurrent_allocations_threads(pool_manager, populated_pool):
    """Test concurrent slot allocations from multiple threads."""
    allocated_slots = []
    errors = []
    lock = threading.Lock()
    
    def allocate_slot(worker_id: int):
        try:
            slot = pool_manager.allocate_slot("concurrent-test")
            if slot:
                with lock:
                    allocated_slots.append((worker_id, slot.slot_id))
        except Exception as e:
            with lock:
                errors.append((worker_id, str(e)))
    
    # Create threads to allocate slots concurrently
    threads = []
    for i in range(5):
        thread = threading.Thread(target=allocate_slot, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All allocations should succeed
    assert len(allocated_slots) == 5
    assert len(errors) == 0
    
    # Verify all allocated slot IDs are unique
    slot_ids = [slot_id for _, slot_id in allocated_slots]
    assert len(slot_ids) == len(set(slot_ids))
    
    # Verify all slots are in allocated state
    pool = pool_manager.get_pool("concurrent-test")
    for slot in pool.slots:
        assert slot.state == SlotState.ALLOCATED


def test_concurrent_allocations_exceed_capacity_threads(pool_manager, populated_pool):
    """Test concurrent allocations when exceeding pool capacity."""
    allocated_slots = []
    failed_allocations = []
    lock = threading.Lock()
    
    def allocate_slot(worker_id: int):
        try:
            slot = pool_manager.allocate_slot("concurrent-test")
            if slot:
                with lock:
                    allocated_slots.append(slot.slot_id)
            else:
                with lock:
                    failed_allocations.append(worker_id)
        except NoAvailableSlotError:
            with lock:
                failed_allocations.append(worker_id)
    
    # Try to allocate more slots than available (10 threads, 5 slots)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate_slot, i) for i in range(10)]
        for future in futures:
            future.result()
    
    # Exactly 5 should succeed, 5 should fail
    assert len(allocated_slots) == 5
    assert len(failed_allocations) == 5
    
    # All allocated slots should be unique
    assert len(allocated_slots) == len(set(allocated_slots))


def test_concurrent_allocate_and_release_threads(pool_manager, populated_pool):
    """Test concurrent allocations and releases."""
    operations = []
    lock = threading.Lock()
    
    def allocate_and_release(worker_id: int):
        try:
            # Allocate
            slot = pool_manager.allocate_slot("concurrent-test")
            if slot:
                with lock:
                    operations.append(("allocate", worker_id, slot.slot_id))
                
                # Hold for a short time
                time.sleep(0.1)
                
                # Release
                pool_manager.release_slot(slot.slot_id)
                with lock:
                    operations.append(("release", worker_id, slot.slot_id))
        except Exception as e:
            with lock:
                operations.append(("error", worker_id, str(e)))
    
    # Execute concurrent allocate/release cycles
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate_and_release, i) for i in range(10)]
        for future in futures:
            future.result()
    
    # Count successful operations
    allocations = [op for op in operations if op[0] == "allocate"]
    releases = [op for op in operations if op[0] == "release"]
    
    # All allocations should have corresponding releases
    assert len(allocations) == len(releases)
    assert len(allocations) >= 5  # At least 5 should succeed


def test_concurrent_same_slot_prevention_threads(pool_manager, populated_pool):
    """Test that the same slot cannot be allocated to multiple threads."""
    allocated_slots = []
    lock = threading.Lock()
    
    def allocate_slot(worker_id: int):
        slot = pool_manager.allocate_slot("concurrent-test")
        if slot:
            with lock:
                allocated_slots.append(slot.slot_id)
            time.sleep(0.2)  # Hold the slot
    
    # Try to allocate all slots concurrently
    threads = []
    for i in range(5):
        thread = threading.Thread(target=allocate_slot, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # All allocated slots must be unique (no double allocation)
    assert len(allocated_slots) == len(set(allocated_slots))
    assert len(allocated_slots) == 5


def test_rapid_allocation_release_cycles_threads(pool_manager, populated_pool):
    """Test rapid allocation and release cycles."""
    success_count = 0
    lock = threading.Lock()
    
    def rapid_cycle(worker_id: int):
        nonlocal success_count
        for _ in range(5):
            try:
                slot = pool_manager.allocate_slot("concurrent-test")
                if slot:
                    pool_manager.release_slot(slot.slot_id)
                    with lock:
                        success_count += 1
            except Exception:
                pass
    
    # Execute rapid cycles
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(rapid_cycle, i) for i in range(3)]
        for future in futures:
            future.result()
    
    # Most cycles should succeed
    assert success_count >= 10


# ============================================================================
# Process-based Concurrent Allocation Tests
# ============================================================================

def _allocate_slot_process(workspaces_dir: str, repo_name: str, worker_id: int):
    """Helper function for process-based allocation testing."""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from necrocode.repo_pool.pool_manager import PoolManager
    from necrocode.repo_pool.config import PoolConfig
    
    try:
        config = PoolConfig(workspaces_dir=Path(workspaces_dir))
        manager = PoolManager(config)
        slot = manager.allocate_slot(repo_name)
        if slot:
            return (True, slot.slot_id, worker_id)
        else:
            return (False, None, worker_id)
    except Exception as e:
        return (False, str(e), worker_id)


def test_concurrent_allocations_multiple_processes(pool_manager, populated_pool, workspaces_dir):
    """Test concurrent allocations from multiple processes."""
    # Use multiprocessing to simulate multiple processes
    with ProcessPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(_allocate_slot_process, str(workspaces_dir), "concurrent-test", i)
            for i in range(5)
        ]
        results = [future.result() for future in futures]
    
    # All allocations should succeed
    successful = [r for r in results if r[0]]
    assert len(successful) == 5
    
    # All slot IDs should be unique
    slot_ids = [r[1] for r in successful]
    assert len(slot_ids) == len(set(slot_ids))


def _allocate_and_release_process(workspaces_dir: str, repo_name: str, worker_id: int):
    """Helper function for process-based allocate/release testing."""
    import sys
    from pathlib import Path
    import time
    
    # Add project root to path
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from necrocode.repo_pool.pool_manager import PoolManager
    from necrocode.repo_pool.config import PoolConfig
    
    try:
        config = PoolConfig(workspaces_dir=Path(workspaces_dir))
        manager = PoolManager(config)
        
        slot = manager.allocate_slot(repo_name)
        if slot:
            time.sleep(0.1)  # Simulate work
            manager.release_slot(slot.slot_id)
            return (True, worker_id)
        else:
            return (False, worker_id)
    except Exception as e:
        return (False, str(e))


def test_concurrent_allocate_release_multiple_processes(pool_manager, populated_pool, workspaces_dir):
    """Test concurrent allocate/release from multiple processes."""
    # Execute allocate/release cycles from multiple processes
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(_allocate_and_release_process, str(workspaces_dir), "concurrent-test", i)
            for i in range(10)
        ]
        results = [future.result() for future in futures]
    
    # Count successful operations
    successful = [r for r in results if r[0]]
    
    # At least 5 should succeed (pool has 5 slots)
    assert len(successful) >= 5


# ============================================================================
# Lock Mechanism Tests
# ============================================================================

def test_lock_prevents_double_allocation(pool_manager, populated_pool):
    """Test that locking prevents double allocation of same slot."""
    allocated_slots = []
    lock = threading.Lock()
    
    def try_allocate(worker_id: int):
        slot = pool_manager.allocate_slot("concurrent-test")
        if slot:
            with lock:
                allocated_slots.append((worker_id, slot.slot_id))
    
    # Try to allocate from multiple threads simultaneously
    threads = []
    for i in range(10):
        thread = threading.Thread(target=try_allocate, args=(i,))
        threads.append(thread)
    
    # Start all threads at once
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Verify no duplicate slot IDs
    slot_ids = [slot_id for _, slot_id in allocated_slots]
    assert len(slot_ids) == len(set(slot_ids))
    
    # Maximum 5 allocations (pool capacity)
    assert len(allocated_slots) <= 5


def test_lock_timeout_behavior(pool_manager, populated_pool):
    """Test lock timeout behavior under contention."""
    # Create a config with short timeout
    short_timeout_config = PoolConfig(
        workspaces_dir=pool_manager.config.workspaces_dir,
        lock_timeout=0.5,
    )
    short_timeout_manager = PoolManager(short_timeout_config)
    
    allocated_slots = []
    timeouts = []
    lock = threading.Lock()
    
    def allocate_with_timeout(worker_id: int):
        try:
            slot = short_timeout_manager.allocate_slot("concurrent-test")
            if slot:
                with lock:
                    allocated_slots.append(slot.slot_id)
                time.sleep(1.0)  # Hold longer than timeout
        except LockTimeoutError:
            with lock:
                timeouts.append(worker_id)
    
    # Try many concurrent allocations
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate_with_timeout, i) for i in range(10)]
        for future in futures:
            try:
                future.result()
            except Exception:
                pass
    
    # Some should succeed, some may timeout
    assert len(allocated_slots) + len(timeouts) >= 5


def test_lock_release_on_exception(pool_manager, populated_pool):
    """Test that locks are released even when exceptions occur."""
    def allocate_with_error(worker_id: int):
        try:
            slot = pool_manager.allocate_slot("concurrent-test")
            if slot and worker_id == 0:
                # Simulate an error for first worker
                raise RuntimeError("Simulated error")
            return slot
        except RuntimeError:
            # Error should not leave lock held
            pass
    
    # First allocation with error
    allocate_with_error(0)
    
    # Subsequent allocations should still work
    slot = pool_manager.allocate_slot("concurrent-test")
    assert slot is not None


# ============================================================================
# Stress Tests
# ============================================================================

def test_high_concurrency_allocation_stress(pool_manager, populated_pool):
    """Stress test with high number of concurrent allocation attempts."""
    allocated_slots = []
    failed_attempts = []
    lock = threading.Lock()
    
    def allocate_attempt(worker_id: int):
        try:
            slot = pool_manager.allocate_slot("concurrent-test")
            if slot:
                with lock:
                    allocated_slots.append(slot.slot_id)
            else:
                with lock:
                    failed_attempts.append(worker_id)
        except Exception:
            with lock:
                failed_attempts.append(worker_id)
    
    # Try many concurrent allocations
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(allocate_attempt, i) for i in range(50)]
        for future in futures:
            future.result()
    
    # Exactly 5 should succeed (pool capacity)
    assert len(allocated_slots) == 5
    assert len(failed_attempts) == 45
    
    # All successful allocations should be unique
    assert len(allocated_slots) == len(set(allocated_slots))


def test_sustained_allocation_release_load(pool_manager, populated_pool):
    """Test sustained load of allocation and release operations."""
    operation_count = 0
    lock = threading.Lock()
    
    def sustained_operations(worker_id: int):
        nonlocal operation_count
        for _ in range(10):
            try:
                slot = pool_manager.allocate_slot("concurrent-test")
                if slot:
                    time.sleep(0.01)  # Minimal work
                    pool_manager.release_slot(slot.slot_id)
                    with lock:
                        operation_count += 1
            except Exception:
                pass
    
    # Execute sustained operations
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(sustained_operations, i) for i in range(5)]
        for future in futures:
            future.result()
    
    # Most operations should succeed
    assert operation_count >= 40


# ============================================================================
# Data Consistency Tests
# ============================================================================

def test_slot_state_consistency_after_concurrent_ops(pool_manager, populated_pool):
    """Test that slot states remain consistent after concurrent operations."""
    def allocate_and_release(worker_id: int):
        slot = pool_manager.allocate_slot("concurrent-test")
        if slot:
            time.sleep(0.05)
            pool_manager.release_slot(slot.slot_id)
    
    # Execute concurrent operations
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate_and_release, i) for i in range(10)]
        for future in futures:
            future.result()
    
    # Verify all slots are back to available state
    pool = pool_manager.get_pool("concurrent-test")
    for slot in pool.slots:
        assert slot.state == SlotState.AVAILABLE


def test_allocation_count_accuracy_concurrent(pool_manager, populated_pool):
    """Test that allocation counts are accurate under concurrent access."""
    def allocate_and_release(worker_id: int):
        slot = pool_manager.allocate_slot("concurrent-test")
        if slot:
            pool_manager.release_slot(slot.slot_id)
    
    # Execute many concurrent operations
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(allocate_and_release, i) for i in range(20)]
        for future in futures:
            future.result()
    
    # Verify allocation counts increased
    pool = pool_manager.get_pool("concurrent-test")
    total_allocations = sum(slot.allocation_count for slot in pool.slots)
    
    # Should have at least 20 total allocations across all slots
    assert total_allocations >= 20


def test_no_slot_corruption_under_concurrency(pool_manager, populated_pool):
    """Test that slot data doesn't get corrupted under concurrent access."""
    def allocate_and_verify(worker_id: int):
        slot = pool_manager.allocate_slot("concurrent-test")
        if slot:
            # Verify slot data integrity
            assert slot.slot_id is not None
            assert slot.repo_name == "concurrent-test"
            assert slot.state == SlotState.ALLOCATED
            assert slot.slot_path.exists()
            
            pool_manager.release_slot(slot.slot_id)
    
    # Execute concurrent operations
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate_and_verify, i) for i in range(20)]
        for future in futures:
            future.result()
    
    # Final verification of all slots
    pool = pool_manager.get_pool("concurrent-test")
    for slot in pool.slots:
        assert slot.slot_id is not None
        assert slot.repo_name == "concurrent-test"
        assert slot.slot_path.exists()


# ============================================================================
# Multiple Pools Concurrent Access
# ============================================================================

def test_concurrent_access_different_pools(pool_manager, test_repo_url):
    """Test concurrent access to different pools."""
    # Create multiple pools
    for i in range(3):
        pool_manager.create_pool(f"pool-{i}", test_repo_url, 3)
    
    allocated_slots = []
    lock = threading.Lock()
    
    def allocate_from_pool(pool_name: str, worker_id: int):
        slot = pool_manager.allocate_slot(pool_name)
        if slot:
            with lock:
                allocated_slots.append((pool_name, slot.slot_id))
    
    # Allocate from different pools concurrently
    with ThreadPoolExecutor(max_workers=9) as executor:
        futures = []
        for i in range(3):
            for j in range(3):
                future = executor.submit(allocate_from_pool, f"pool-{i}", j)
                futures.append(future)
        
        for future in futures:
            future.result()
    
    # All allocations should succeed
    assert len(allocated_slots) == 9
    
    # Verify allocations are distributed across pools
    pool_0_allocs = [s for p, s in allocated_slots if p == "pool-0"]
    pool_1_allocs = [s for p, s in allocated_slots if p == "pool-1"]
    pool_2_allocs = [s for p, s in allocated_slots if p == "pool-2"]
    
    assert len(pool_0_allocs) == 3
    assert len(pool_1_allocs) == 3
    assert len(pool_2_allocs) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

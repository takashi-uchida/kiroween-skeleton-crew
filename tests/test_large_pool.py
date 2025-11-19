"""Performance tests for large pool management.

Tests managing pools with many slots (100+).
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import time
from pathlib import Path
import sys
import pytest
import statistics
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.models import SlotState


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def workspaces_dir(tmp_path):
    """Create temporary workspaces directory."""
    return tmp_path / "workspaces"


@pytest.fixture
def config(workspaces_dir):
    """Create PoolConfig instance for large pool."""
    return PoolConfig(
        workspaces_dir=workspaces_dir,
        default_num_slots=100,
        lock_timeout=60.0,
        cleanup_timeout=180.0,
        enable_metrics=True,
    )


@pytest.fixture
def pool_manager(config):
    """Create PoolManager instance."""
    return PoolManager(config)


@pytest.fixture
def test_repo_url():
    """Return a test repository URL."""
    return "https://github.com/octocat/Hello-World.git"


# ============================================================================
# Large Pool Creation Tests
# ============================================================================

@pytest.mark.slow
def test_create_large_pool_performance(pool_manager, test_repo_url):
    """Test performance of creating a large pool (100 slots)."""
    print("\n" + "="*60)
    print("Creating large pool with 100 slots...")
    print("This may take several minutes...")
    print("="*60)
    
    start_time = time.time()
    
    pool = pool_manager.create_pool(
        repo_name="large-pool",
        repo_url=test_repo_url,
        num_slots=100
    )
    
    creation_time = time.time() - start_time
    
    print(f"\nLarge Pool Creation (100 slots):")
    print(f"  Total time: {creation_time:.2f}s ({creation_time/60:.2f} minutes)")
    print(f"  Time per slot: {creation_time/100:.2f}s")
    print(f"  Slots per minute: {100/(creation_time/60):.2f}")
    
    # Verify pool was created correctly
    assert pool.num_slots == 100
    assert len(pool.slots) == 100
    
    # Verify all slots are available
    available_count = sum(1 for s in pool.slots if s.state == SlotState.AVAILABLE)
    assert available_count == 100
    
    # Should complete in reasonable time (allow 30 minutes)
    assert creation_time < 1800


@pytest.mark.slow
def test_large_pool_with_smaller_size(pool_manager, test_repo_url):
    """Test creating a moderately large pool (20 slots) for faster testing."""
    start_time = time.time()
    
    pool = pool_manager.create_pool(
        repo_name="medium-pool",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    creation_time = time.time() - start_time
    
    print(f"\nMedium Pool Creation (20 slots):")
    print(f"  Total time: {creation_time:.2f}s")
    print(f"  Time per slot: {creation_time/20:.2f}s")
    
    assert pool.num_slots == 20
    assert len(pool.slots) == 20
    
    # Should complete faster
    assert creation_time < 600  # 10 minutes


# ============================================================================
# Large Pool Allocation Tests
# ============================================================================

def test_allocation_from_large_pool(pool_manager, test_repo_url):
    """Test allocation performance from a large pool."""
    # Create a medium-sized pool for testing
    pool = pool_manager.create_pool(
        repo_name="alloc-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    allocation_times = []
    
    # Allocate 10 slots
    for i in range(10):
        start = time.time()
        slot = pool_manager.allocate_slot("alloc-large")
        alloc_time = time.time() - start
        allocation_times.append(alloc_time)
        
        assert slot is not None
    
    avg_time = statistics.mean(allocation_times)
    
    print(f"\nAllocation from Large Pool (20 slots):")
    print(f"  Average allocation time: {avg_time:.3f}s")
    print(f"  Min: {min(allocation_times):.3f}s")
    print(f"  Max: {max(allocation_times):.3f}s")
    
    # Allocation should remain fast even with large pool
    assert avg_time < 2.0


def test_concurrent_allocation_large_pool(pool_manager, test_repo_url):
    """Test concurrent allocations from a large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="concurrent-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    allocated_slots = []
    
    def allocate_slot(worker_id: int):
        slot = pool_manager.allocate_slot("concurrent-large")
        if slot:
            return slot.slot_id
        return None
    
    start_time = time.time()
    
    # Allocate 15 slots concurrently
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(allocate_slot, i) for i in range(15)]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start_time
    successful = [r for r in results if r is not None]
    
    print(f"\nConcurrent Allocation from Large Pool:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Successful allocations: {len(successful)}/15")
    print(f"  Throughput: {len(successful)/total_time:.2f} allocs/sec")
    
    assert len(successful) == 15
    assert total_time < 30.0


# ============================================================================
# Large Pool Summary Tests
# ============================================================================

def test_large_pool_summary_performance(pool_manager, test_repo_url):
    """Test performance of getting summary for large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="summary-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    # Allocate some slots
    for i in range(10):
        pool_manager.allocate_slot("summary-large")
    
    # Measure summary generation
    start_time = time.time()
    summary = pool_manager.get_pool_summary()
    summary_time = time.time() - start_time
    
    print(f"\nLarge Pool Summary Performance:")
    print(f"  Summary generation time: {summary_time:.3f}s")
    print(f"  Total slots: {summary['summary-large'].total_slots}")
    print(f"  Allocated: {summary['summary-large'].allocated_slots}")
    print(f"  Available: {summary['summary-large'].available_slots}")
    
    # Summary should be fast even for large pool
    assert summary_time < 2.0
    assert summary["summary-large"].total_slots == 20


def test_multiple_large_pools_summary(pool_manager, test_repo_url):
    """Test summary performance with multiple large pools."""
    # Create multiple pools
    for i in range(5):
        pool_manager.create_pool(f"pool-{i}", test_repo_url, 10)
    
    # Allocate from each
    for i in range(5):
        for j in range(5):
            pool_manager.allocate_slot(f"pool-{i}")
    
    # Measure summary
    start_time = time.time()
    summary = pool_manager.get_pool_summary()
    summary_time = time.time() - start_time
    
    print(f"\nMultiple Large Pools Summary:")
    print(f"  Number of pools: 5")
    print(f"  Total slots: {sum(s.total_slots for s in summary.values())}")
    print(f"  Summary time: {summary_time:.3f}s")
    
    assert len(summary) == 5
    assert summary_time < 3.0


# ============================================================================
# Large Pool Slot Status Tests
# ============================================================================

def test_slot_status_query_large_pool(pool_manager, test_repo_url):
    """Test querying slot status in large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="status-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    # Query status for all slots
    query_times = []
    
    for slot in pool.slots[:10]:  # Test first 10 slots
        start = time.time()
        status = pool_manager.get_slot_status(slot.slot_id)
        query_time = time.time() - start
        query_times.append(query_time)
        
        assert status is not None
    
    avg_time = statistics.mean(query_times)
    
    print(f"\nSlot Status Query (Large Pool):")
    print(f"  Average query time: {avg_time:.3f}s")
    print(f"  Total for 10 queries: {sum(query_times):.3f}s")
    
    # Queries should remain fast
    assert avg_time < 1.0


# ============================================================================
# Large Pool Allocation Pattern Tests
# ============================================================================

def test_allocation_pattern_large_pool(pool_manager, test_repo_url):
    """Test allocation patterns in large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="pattern-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    # Allocate and release in pattern
    pattern_times = []
    
    for cycle in range(5):
        cycle_start = time.time()
        
        # Allocate 10 slots
        allocated = []
        for i in range(10):
            slot = pool_manager.allocate_slot("pattern-large")
            if slot:
                allocated.append(slot)
        
        # Release all
        for slot in allocated:
            pool_manager.release_slot(slot.slot_id)
        
        cycle_time = time.time() - cycle_start
        pattern_times.append(cycle_time)
        
        print(f"  Cycle {cycle + 1}: {cycle_time:.3f}s")
    
    avg_cycle = statistics.mean(pattern_times)
    
    print(f"\nAllocation Pattern (Large Pool):")
    print(f"  Average cycle time: {avg_cycle:.3f}s")
    
    # Cycles should be consistent
    assert avg_cycle < 30.0


# ============================================================================
# Large Pool Metrics Tests
# ============================================================================

def test_metrics_accuracy_large_pool(pool_manager, test_repo_url):
    """Test metrics accuracy with large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="metrics-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    # Perform many allocations
    for i in range(30):
        slot = pool_manager.allocate_slot("metrics-large")
        if slot:
            pool_manager.release_slot(slot.slot_id)
    
    # Get metrics
    metrics = pool_manager.slot_allocator.get_allocation_metrics("metrics-large")
    
    print(f"\nMetrics (Large Pool):")
    print(f"  Total allocations: {metrics.total_allocations}")
    print(f"  Average time: {metrics.average_allocation_time_seconds:.3f}s")
    print(f"  Cache hit rate: {metrics.cache_hit_rate:.2%}")
    
    # Verify metrics
    assert metrics.total_allocations >= 30


# ============================================================================
# Large Pool Stress Tests
# ============================================================================

def test_sustained_load_large_pool(pool_manager, test_repo_url):
    """Test sustained load on large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="stress-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    duration = 30  # seconds
    operations = []
    
    def sustained_ops(worker_id: int):
        start = time.time()
        count = 0
        while time.time() - start < duration:
            slot = pool_manager.allocate_slot("stress-large")
            if slot:
                pool_manager.release_slot(slot.slot_id)
                count += 1
        return count
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(sustained_ops, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start_time
    total_ops = sum(results)
    throughput = total_ops / total_time
    
    print(f"\nSustained Load (Large Pool, {duration}s):")
    print(f"  Total operations: {total_ops}")
    print(f"  Throughput: {throughput:.2f} ops/sec")
    print(f"  Operations per worker: {results}")
    
    # Should maintain reasonable throughput
    assert throughput > 0.5


def test_high_concurrency_large_pool(pool_manager, test_repo_url):
    """Test high concurrency with large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="concurrency-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    num_workers = 50
    
    def allocate_attempt(worker_id: int):
        slot = pool_manager.allocate_slot("concurrency-large")
        if slot:
            time.sleep(0.1)  # Hold briefly
            pool_manager.release_slot(slot.slot_id)
            return True
        return False
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(allocate_attempt, i) for i in range(num_workers)]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r)
    
    print(f"\nHigh Concurrency (Large Pool):")
    print(f"  Workers: {num_workers}")
    print(f"  Successful: {successful}")
    print(f"  Total time: {total_time:.3f}s")
    
    # Most should succeed
    assert successful >= 20


# ============================================================================
# Large Pool Memory Tests
# ============================================================================

def test_memory_usage_large_pool(pool_manager, test_repo_url):
    """Test memory usage with large pool."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="memory-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    after_creation = process.memory_info().rss / 1024 / 1024
    
    # Perform operations
    for i in range(50):
        slot = pool_manager.allocate_slot("memory-large")
        if slot:
            pool_manager.release_slot(slot.slot_id)
    
    final_memory = process.memory_info().rss / 1024 / 1024
    
    print(f"\nMemory Usage (Large Pool):")
    print(f"  Initial: {initial_memory:.2f} MB")
    print(f"  After creation: {after_creation:.2f} MB")
    print(f"  After operations: {final_memory:.2f} MB")
    print(f"  Total increase: {final_memory - initial_memory:.2f} MB")
    
    # Memory increase should be reasonable
    assert final_memory - initial_memory < 200


# ============================================================================
# Large Pool Scalability Tests
# ============================================================================

def test_pool_size_scalability(pool_manager, test_repo_url):
    """Test how performance scales with pool size."""
    pool_sizes = [5, 10, 20]
    results = {}
    
    for size in pool_sizes:
        pool_name = f"scale-{size}"
        
        # Create pool
        start = time.time()
        pool = pool_manager.create_pool(pool_name, test_repo_url, size)
        creation_time = time.time() - start
        
        # Test allocation
        alloc_times = []
        for i in range(min(5, size)):
            start = time.time()
            slot = pool_manager.allocate_slot(pool_name)
            alloc_times.append(time.time() - start)
            if slot:
                pool_manager.release_slot(slot.slot_id)
        
        avg_alloc = statistics.mean(alloc_times)
        
        results[size] = {
            'creation_time': creation_time,
            'avg_allocation': avg_alloc,
            'time_per_slot': creation_time / size
        }
    
    print(f"\nPool Size Scalability:")
    for size, data in results.items():
        print(f"  {size} slots:")
        print(f"    Creation: {data['creation_time']:.2f}s")
        print(f"    Per slot: {data['time_per_slot']:.2f}s")
        print(f"    Avg allocation: {data['avg_allocation']:.3f}s")


# ============================================================================
# Large Pool Cleanup Tests
# ============================================================================

def test_cleanup_performance_large_pool(pool_manager, test_repo_url):
    """Test cleanup performance in large pool."""
    # Create pool
    pool = pool_manager.create_pool(
        repo_name="cleanup-large",
        repo_url=test_repo_url,
        num_slots=20
    )
    
    cleanup_times = []
    
    # Test cleanup on multiple slots
    for i in range(10):
        slot = pool_manager.allocate_slot("cleanup-large")
        
        # Create files
        for j in range(10):
            (slot.slot_path / f"file_{j}.txt").write_text(f"Content {j}")
        
        # Measure cleanup
        start = time.time()
        pool_manager.release_slot(slot.slot_id)
        cleanup_times.append(time.time() - start)
    
    avg_cleanup = statistics.mean(cleanup_times)
    
    print(f"\nCleanup Performance (Large Pool):")
    print(f"  Average cleanup time: {avg_cleanup:.3f}s")
    print(f"  Min: {min(cleanup_times):.3f}s")
    print(f"  Max: {max(cleanup_times):.3f}s")
    
    # Cleanup should remain efficient
    assert avg_cleanup < 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "not slow"])

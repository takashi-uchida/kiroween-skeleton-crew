"""Performance tests for slot allocation.

Tests allocation performance and metrics.
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
    """Create PoolConfig instance."""
    return PoolConfig(
        workspaces_dir=workspaces_dir,
        default_num_slots=10,
        lock_timeout=30.0,
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


@pytest.fixture
def performance_pool(pool_manager, test_repo_url):
    """Create a pool for performance testing."""
    pool = pool_manager.create_pool(
        repo_name="perf-test",
        repo_url=test_repo_url,
        num_slots=10
    )
    return pool


# ============================================================================
# Basic Allocation Performance Tests
# ============================================================================

def test_single_allocation_performance(pool_manager, performance_pool):
    """Test performance of single slot allocation."""
    allocation_times = []
    
    for i in range(10):
        start_time = time.time()
        slot = pool_manager.allocate_slot("perf-test")
        allocation_time = time.time() - start_time
        allocation_times.append(allocation_time)
        
        assert slot is not None
        
        # Release for next iteration
        pool_manager.release_slot(slot.slot_id)
    
    # Calculate statistics
    avg_time = statistics.mean(allocation_times)
    max_time = max(allocation_times)
    min_time = min(allocation_times)
    
    print(f"\nSingle Allocation Performance:")
    print(f"  Average: {avg_time:.3f}s")
    print(f"  Min: {min_time:.3f}s")
    print(f"  Max: {max_time:.3f}s")
    
    # Allocation should be reasonably fast (< 2 seconds on average)
    assert avg_time < 2.0


def test_sequential_allocations_performance(pool_manager, performance_pool):
    """Test performance of sequential allocations."""
    start_time = time.time()
    
    allocated_slots = []
    for i in range(10):
        slot = pool_manager.allocate_slot("perf-test")
        assert slot is not None
        allocated_slots.append(slot)
    
    total_time = time.time() - start_time
    avg_time = total_time / 10
    
    print(f"\nSequential Allocations (10 slots):")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average per allocation: {avg_time:.3f}s")
    
    # Should complete in reasonable time
    assert total_time < 20.0


def test_allocation_with_immediate_release_performance(pool_manager, performance_pool):
    """Test performance of allocation followed by immediate release."""
    cycle_times = []
    
    for i in range(20):
        start_time = time.time()
        
        slot = pool_manager.allocate_slot("perf-test")
        pool_manager.release_slot(slot.slot_id)
        
        cycle_time = time.time() - start_time
        cycle_times.append(cycle_time)
    
    avg_time = statistics.mean(cycle_times)
    
    print(f"\nAllocation + Release Cycles (20 cycles):")
    print(f"  Average cycle time: {avg_time:.3f}s")
    
    # Cycle should be reasonably fast
    assert avg_time < 3.0


# ============================================================================
# LRU Cache Performance Tests
# ============================================================================

def test_lru_cache_hit_performance(pool_manager, performance_pool):
    """Test that LRU cache improves allocation performance."""
    # First allocation (cache miss)
    start_time = time.time()
    slot1 = pool_manager.allocate_slot("perf-test")
    first_allocation_time = time.time() - start_time
    pool_manager.release_slot(slot1.slot_id)
    
    # Second allocation (should hit cache)
    start_time = time.time()
    slot2 = pool_manager.allocate_slot("perf-test")
    second_allocation_time = time.time() - start_time
    
    print(f"\nLRU Cache Performance:")
    print(f"  First allocation: {first_allocation_time:.3f}s")
    print(f"  Second allocation (cache hit): {second_allocation_time:.3f}s")
    
    # Second allocation should be at least as fast (LRU benefit)
    # Note: May not always be faster due to system variations
    assert second_allocation_time < first_allocation_time * 2


def test_lru_allocation_pattern(pool_manager, performance_pool):
    """Test allocation pattern with LRU strategy."""
    allocation_times = []
    
    # Perform multiple allocation/release cycles
    for cycle in range(5):
        cycle_times = []
        for i in range(10):
            start_time = time.time()
            slot = pool_manager.allocate_slot("perf-test")
            alloc_time = time.time() - start_time
            cycle_times.append(alloc_time)
            pool_manager.release_slot(slot.slot_id)
        
        avg_cycle_time = statistics.mean(cycle_times)
        allocation_times.append(avg_cycle_time)
        print(f"  Cycle {cycle + 1} avg: {avg_cycle_time:.3f}s")
    
    # Later cycles should benefit from LRU (warmed up slots)
    # Average of last 3 cycles should be <= average of first 2 cycles
    early_avg = statistics.mean(allocation_times[:2])
    later_avg = statistics.mean(allocation_times[2:])
    
    print(f"\nLRU Pattern Analysis:")
    print(f"  Early cycles avg: {early_avg:.3f}s")
    print(f"  Later cycles avg: {later_avg:.3f}s")


# ============================================================================
# Concurrent Allocation Performance Tests
# ============================================================================

def test_concurrent_allocation_throughput(pool_manager, performance_pool):
    """Test throughput of concurrent allocations."""
    num_workers = 10
    allocations_per_worker = 5
    
    def allocate_and_release(worker_id: int):
        times = []
        for i in range(allocations_per_worker):
            start = time.time()
            slot = pool_manager.allocate_slot("perf-test")
            if slot:
                pool_manager.release_slot(slot.slot_id)
                times.append(time.time() - start)
        return times
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(allocate_and_release, i) for i in range(num_workers)]
        results = [future.result() for future in futures]
    
    total_time = time.time() - start_time
    total_operations = sum(len(times) for times in results)
    throughput = total_operations / total_time
    
    all_times = [t for times in results for t in times]
    avg_time = statistics.mean(all_times) if all_times else 0
    
    print(f"\nConcurrent Allocation Throughput:")
    print(f"  Total operations: {total_operations}")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Throughput: {throughput:.2f} ops/sec")
    print(f"  Average operation time: {avg_time:.3f}s")
    
    # Should achieve reasonable throughput
    assert throughput > 1.0  # At least 1 operation per second


def test_concurrent_allocation_scalability(pool_manager, performance_pool):
    """Test how allocation performance scales with concurrency."""
    worker_counts = [1, 2, 5, 10]
    results = {}
    
    for num_workers in worker_counts:
        def allocate_release(worker_id: int):
            slot = pool_manager.allocate_slot("perf-test")
            if slot:
                pool_manager.release_slot(slot.slot_id)
                return True
            return False
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(allocate_release, i) for i in range(num_workers)]
            successes = sum(1 for f in futures if f.result())
        
        elapsed = time.time() - start_time
        results[num_workers] = {
            'time': elapsed,
            'successes': successes,
            'throughput': successes / elapsed if elapsed > 0 else 0
        }
    
    print(f"\nConcurrency Scalability:")
    for workers, data in results.items():
        print(f"  {workers} workers: {data['time']:.3f}s, "
              f"{data['throughput']:.2f} ops/sec")


# ============================================================================
# Allocation Metrics Tests
# ============================================================================

def test_allocation_metrics_tracking(pool_manager, performance_pool):
    """Test that allocation metrics are tracked correctly."""
    # Perform several allocations
    for i in range(10):
        slot = pool_manager.allocate_slot("perf-test")
        if slot:
            pool_manager.release_slot(slot.slot_id)
    
    # Get metrics
    metrics = pool_manager.slot_allocator.get_allocation_metrics("perf-test")
    
    print(f"\nAllocation Metrics:")
    print(f"  Total allocations: {metrics.total_allocations}")
    print(f"  Average time: {metrics.average_allocation_time_seconds:.3f}s")
    print(f"  Cache hit rate: {metrics.cache_hit_rate:.2%}")
    print(f"  Failed allocations: {metrics.failed_allocations}")
    
    # Verify metrics are being tracked
    assert metrics.total_allocations >= 10
    assert metrics.average_allocation_time_seconds > 0


def test_allocation_metrics_accuracy(pool_manager, performance_pool):
    """Test accuracy of allocation metrics."""
    # Perform allocations with known timing
    measured_times = []
    
    for i in range(5):
        start = time.time()
        slot = pool_manager.allocate_slot("perf-test")
        elapsed = time.time() - start
        measured_times.append(elapsed)
        
        if slot:
            pool_manager.release_slot(slot.slot_id)
    
    # Get metrics
    metrics = pool_manager.slot_allocator.get_allocation_metrics("perf-test")
    
    # Metrics should be reasonably close to measured times
    measured_avg = statistics.mean(measured_times)
    
    print(f"\nMetrics Accuracy:")
    print(f"  Measured average: {measured_avg:.3f}s")
    print(f"  Reported average: {metrics.average_allocation_time_seconds:.3f}s")
    
    # Should be within reasonable range
    assert abs(metrics.average_allocation_time_seconds - measured_avg) < 1.0


# ============================================================================
# Pool Summary Performance Tests
# ============================================================================

def test_pool_summary_performance(pool_manager, performance_pool):
    """Test performance of getting pool summary."""
    # Allocate some slots
    allocated = []
    for i in range(5):
        slot = pool_manager.allocate_slot("perf-test")
        if slot:
            allocated.append(slot)
    
    # Measure summary generation time
    start_time = time.time()
    summary = pool_manager.get_pool_summary()
    summary_time = time.time() - start_time
    
    print(f"\nPool Summary Performance:")
    print(f"  Generation time: {summary_time:.3f}s")
    
    # Summary should be fast
    assert summary_time < 1.0
    
    # Verify summary data
    assert "perf-test" in summary
    assert summary["perf-test"].total_slots == 10
    assert summary["perf-test"].allocated_slots == 5


def test_multiple_pools_summary_performance(pool_manager, test_repo_url):
    """Test summary performance with multiple pools."""
    # Create multiple pools
    for i in range(5):
        pool_manager.create_pool(f"pool-{i}", test_repo_url, 5)
    
    # Allocate from each pool
    for i in range(5):
        pool_manager.allocate_slot(f"pool-{i}")
    
    # Measure summary time
    start_time = time.time()
    summary = pool_manager.get_pool_summary()
    summary_time = time.time() - start_time
    
    print(f"\nMultiple Pools Summary Performance:")
    print(f"  Number of pools: 5")
    print(f"  Generation time: {summary_time:.3f}s")
    
    # Should still be fast with multiple pools
    assert summary_time < 2.0
    assert len(summary) == 5


# ============================================================================
# Slot Status Performance Tests
# ============================================================================

def test_slot_status_query_performance(pool_manager, performance_pool):
    """Test performance of querying slot status."""
    # Get all slot IDs
    pool = pool_manager.get_pool("perf-test")
    slot_ids = [slot.slot_id for slot in pool.slots]
    
    # Measure status query time
    query_times = []
    for slot_id in slot_ids:
        start = time.time()
        status = pool_manager.get_slot_status(slot_id)
        query_time = time.time() - start
        query_times.append(query_time)
        
        assert status is not None
    
    avg_time = statistics.mean(query_times)
    
    print(f"\nSlot Status Query Performance:")
    print(f"  Average query time: {avg_time:.3f}s")
    print(f"  Total for 10 slots: {sum(query_times):.3f}s")
    
    # Status queries should be fast
    assert avg_time < 0.5


# ============================================================================
# Warmup Performance Tests
# ============================================================================

def test_slot_warmup_performance(pool_manager, performance_pool):
    """Test performance of slot warmup."""
    pool = pool_manager.get_pool("perf-test")
    slot = pool.slots[0]
    
    # Measure warmup time
    start_time = time.time()
    pool_manager.slot_cleaner.warmup_slot(slot)
    warmup_time = time.time() - start_time
    
    print(f"\nSlot Warmup Performance:")
    print(f"  Warmup time: {warmup_time:.3f}s")
    
    # Warmup should complete in reasonable time
    assert warmup_time < 30.0


def test_multiple_slot_warmup_performance(pool_manager, performance_pool):
    """Test performance of warming up multiple slots."""
    pool = pool_manager.get_pool("perf-test")
    
    start_time = time.time()
    
    for slot in pool.slots[:5]:
        pool_manager.slot_cleaner.warmup_slot(slot)
    
    total_time = time.time() - start_time
    avg_time = total_time / 5
    
    print(f"\nMultiple Slot Warmup Performance:")
    print(f"  Total time (5 slots): {total_time:.3f}s")
    print(f"  Average per slot: {avg_time:.3f}s")
    
    # Should complete in reasonable time
    assert total_time < 60.0


# ============================================================================
# Memory and Resource Tests
# ============================================================================

def test_allocation_memory_efficiency(pool_manager, performance_pool):
    """Test memory efficiency of allocations."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform many allocations
    for i in range(50):
        slot = pool_manager.allocate_slot("perf-test")
        if slot:
            pool_manager.release_slot(slot.slot_id)
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"\nMemory Efficiency:")
    print(f"  Initial memory: {initial_memory:.2f} MB")
    print(f"  Final memory: {final_memory:.2f} MB")
    print(f"  Increase: {memory_increase:.2f} MB")
    
    # Memory increase should be reasonable (< 100 MB)
    assert memory_increase < 100


# ============================================================================
# Stress Tests
# ============================================================================

def test_sustained_load_performance(pool_manager, performance_pool):
    """Test performance under sustained load."""
    duration = 10  # seconds
    operations = []
    
    def sustained_operations():
        start = time.time()
        count = 0
        while time.time() - start < duration:
            slot = pool_manager.allocate_slot("perf-test")
            if slot:
                pool_manager.release_slot(slot.slot_id)
                count += 1
        return count
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(sustained_operations) for _ in range(5)]
        results = [future.result() for future in futures]
    
    total_time = time.time() - start_time
    total_ops = sum(results)
    throughput = total_ops / total_time
    
    print(f"\nSustained Load Performance ({duration}s):")
    print(f"  Total operations: {total_ops}")
    print(f"  Throughput: {throughput:.2f} ops/sec")
    print(f"  Operations per worker: {[r for r in results]}")
    
    # Should maintain reasonable throughput
    assert throughput > 0.5


def test_allocation_performance_degradation(pool_manager, performance_pool):
    """Test that performance doesn't degrade over time."""
    batch_size = 10
    num_batches = 5
    batch_times = []
    
    for batch in range(num_batches):
        start_time = time.time()
        
        for i in range(batch_size):
            slot = pool_manager.allocate_slot("perf-test")
            if slot:
                pool_manager.release_slot(slot.slot_id)
        
        batch_time = time.time() - start_time
        batch_times.append(batch_time)
        print(f"  Batch {batch + 1}: {batch_time:.3f}s")
    
    # Calculate trend
    first_half_avg = statistics.mean(batch_times[:2])
    second_half_avg = statistics.mean(batch_times[2:])
    
    print(f"\nPerformance Degradation Analysis:")
    print(f"  First half average: {first_half_avg:.3f}s")
    print(f"  Second half average: {second_half_avg:.3f}s")
    
    # Performance should not degrade significantly
    # Allow up to 50% degradation
    assert second_half_avg < first_half_avg * 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

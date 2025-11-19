#!/usr/bin/env python3
"""
Performance Optimization Example for Repo Pool Manager

This example demonstrates the performance optimization features:
1. Parallel git fetch operations
2. Parallel slot cleanup
3. Background cleanup
4. Metrics collection and export

Requirements: Task 10 (Performance Optimization)
"""

import time
from pathlib import Path

from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.pool_manager import PoolManager


def example_parallel_operations():
    """Demonstrate parallel git fetch and cleanup operations."""
    print("=" * 60)
    print("Example 1: Parallel Operations")
    print("=" * 60)
    
    # Initialize pool manager
    config = PoolConfig(
        workspaces_dir=Path.home() / ".necrocode" / "workspaces_perf_test"
    )
    manager = PoolManager(config=config)
    
    # Create a test pool with multiple slots
    repo_name = "test-parallel"
    repo_url = "https://github.com/octocat/Hello-World.git"
    num_slots = 5
    
    print(f"\nCreating pool '{repo_name}' with {num_slots} slots...")
    try:
        pool = manager.create_pool(repo_name, repo_url, num_slots)
        print(f"✓ Pool created with {len(pool.slots)} slots")
    except ValueError:
        print(f"Pool '{repo_name}' already exists, using existing pool")
        pool = manager.get_pool(repo_name)
    
    # Demonstrate parallel warmup
    print(f"\n--- Parallel Warmup ---")
    print(f"Warming up {len(pool.slots)} slots in parallel...")
    
    start_time = time.time()
    result = manager.warmup_pool_parallel(repo_name, max_workers=3)
    duration = time.time() - start_time
    
    print(f"✓ Warmup complete:")
    print(f"  - Slots warmed: {result['slots_warmed']}")
    print(f"  - Successful: {result['successful']}")
    print(f"  - Failed: {result['failed']}")
    print(f"  - Total duration: {duration:.2f}s")
    print(f"  - Average per slot: {duration / result['slots_warmed']:.2f}s")
    
    # Demonstrate parallel cleanup
    print(f"\n--- Parallel Cleanup ---")
    print(f"Cleaning up {len(pool.slots)} slots in parallel...")
    
    start_time = time.time()
    result = manager.cleanup_pool_parallel(repo_name, operation="warmup", max_workers=3)
    duration = time.time() - start_time
    
    print(f"✓ Cleanup complete:")
    print(f"  - Slots cleaned: {result['slots_cleaned']}")
    print(f"  - Successful: {result['successful']}")
    print(f"  - Failed: {result['failed']}")
    print(f"  - Total duration: {duration:.2f}s")


def example_background_cleanup():
    """Demonstrate background cleanup operations."""
    print("\n" + "=" * 60)
    print("Example 2: Background Cleanup")
    print("=" * 60)
    
    # Initialize pool manager
    config = PoolConfig(
        workspaces_dir=Path.home() / ".necrocode" / "workspaces_perf_test"
    )
    manager = PoolManager(config=config)
    
    repo_name = "test-parallel"
    
    # Allocate a slot
    print(f"\nAllocating slot from pool '{repo_name}'...")
    slot = manager.allocate_slot(repo_name)
    print(f"✓ Allocated slot: {slot.slot_id}")
    
    # Release with background cleanup
    print(f"\n--- Background Cleanup ---")
    print(f"Releasing slot with background cleanup...")
    
    task_id = manager.release_slot_background(slot.slot_id, cleanup=True)
    print(f"✓ Slot released immediately")
    print(f"  - Background task ID: {task_id}")
    
    # Check if cleanup is complete
    print(f"\nChecking background cleanup status...")
    is_complete = manager.slot_cleaner.is_background_cleanup_complete(task_id)
    print(f"  - Complete: {is_complete}")
    
    # Wait for cleanup to complete
    print(f"\nWaiting for background cleanup to complete...")
    result = manager.slot_cleaner.get_background_cleanup_result(task_id, timeout=30.0)
    
    if result:
        print(f"✓ Background cleanup completed:")
        print(f"  - Success: {result.success}")
        print(f"  - Duration: {result.duration_seconds:.2f}s")
        print(f"  - Operations: {', '.join(result.operations)}")
        if result.errors:
            print(f"  - Errors: {', '.join(result.errors)}")
    else:
        print("✗ Background cleanup timed out or failed")
    
    # Show active background tasks
    active_tasks = manager.slot_cleaner.get_active_background_tasks()
    print(f"\nActive background tasks: {len(active_tasks)}")


def example_metrics_collection():
    """Demonstrate metrics collection and export."""
    print("\n" + "=" * 60)
    print("Example 3: Metrics Collection")
    print("=" * 60)
    
    # Initialize pool manager
    config = PoolConfig(
        workspaces_dir=Path.home() / ".necrocode" / "workspaces_perf_test"
    )
    manager = PoolManager(config=config)
    
    repo_name = "test-parallel"
    
    # Perform some allocations to generate metrics
    print(f"\nPerforming test allocations to generate metrics...")
    
    for i in range(3):
        print(f"  Allocation {i+1}/3...")
        slot = manager.allocate_slot(repo_name)
        time.sleep(0.5)  # Simulate some work
        manager.release_slot(slot.slot_id)
    
    print("✓ Test allocations complete")
    
    # Get allocation metrics
    print(f"\n--- Allocation Metrics ---")
    metrics = manager.get_allocation_metrics(repo_name)
    print(f"Repository: {metrics.repo_name}")
    print(f"  - Total allocations: {metrics.total_allocations}")
    print(f"  - Average time: {metrics.average_allocation_time_seconds:.3f}s")
    print(f"  - Cache hit rate: {metrics.cache_hit_rate:.1%}")
    print(f"  - Failed allocations: {metrics.failed_allocations}")
    
    # Get comprehensive performance metrics
    print(f"\n--- Performance Metrics ---")
    perf_metrics = manager.get_performance_metrics(repo_name)
    
    if repo_name in perf_metrics:
        repo_metrics = perf_metrics[repo_name]
        
        print(f"Allocation:")
        print(f"  - Total: {repo_metrics['allocation']['total_allocations']}")
        print(f"  - Avg time: {repo_metrics['allocation']['average_time_seconds']:.3f}s")
        print(f"  - Cache hit rate: {repo_metrics['allocation']['cache_hit_rate']:.1%}")
        
        print(f"Cleanup:")
        print(f"  - Total: {repo_metrics['cleanup']['total_cleanups']}")
        print(f"  - Successful: {repo_metrics['cleanup']['successful_cleanups']}")
        print(f"  - Failed: {repo_metrics['cleanup']['failed_cleanups']}")
        print(f"  - Avg time: {repo_metrics['cleanup']['average_time_seconds']:.3f}s")
        
        print(f"Pool:")
        print(f"  - Total slots: {repo_metrics['pool']['total_slots']}")
        print(f"  - Available: {repo_metrics['pool']['available_slots']}")
        print(f"  - Allocated: {repo_metrics['pool']['allocated_slots']}")
        print(f"  - Error: {repo_metrics['pool']['error_slots']}")
    
    # Export metrics to file
    print(f"\n--- Export Metrics ---")
    output_file = Path("examples/output/performance_metrics.json")
    exported = manager.export_metrics(output_file)
    print(f"✓ Metrics exported to: {output_file}")
    print(f"  - Timestamp: {exported['timestamp']}")
    print(f"  - Total pools: {exported['system']['total_pools']}")


def example_performance_comparison():
    """Compare sequential vs parallel operations."""
    print("\n" + "=" * 60)
    print("Example 4: Performance Comparison")
    print("=" * 60)
    
    # Initialize pool manager
    config = PoolConfig(
        workspaces_dir=Path.home() / ".necrocode" / "workspaces_perf_test"
    )
    manager = PoolManager(config=config)
    
    repo_name = "test-parallel"
    pool = manager.get_pool(repo_name)
    available_slots = [s for s in pool.slots if s.state.value == "available"]
    
    if len(available_slots) < 3:
        print("Not enough available slots for comparison")
        return
    
    # Sequential warmup (simulate)
    print(f"\n--- Sequential Warmup (simulated) ---")
    print(f"Warming up {len(available_slots)} slots sequentially...")
    
    sequential_times = []
    for slot in available_slots:
        start = time.time()
        result = manager.slot_cleaner.warmup_slot(slot)
        sequential_times.append(time.time() - start)
    
    sequential_total = sum(sequential_times)
    print(f"✓ Sequential warmup complete:")
    print(f"  - Total time: {sequential_total:.2f}s")
    print(f"  - Average per slot: {sequential_total / len(available_slots):.2f}s")
    
    # Parallel warmup
    print(f"\n--- Parallel Warmup ---")
    print(f"Warming up {len(available_slots)} slots in parallel...")
    
    start_time = time.time()
    result = manager.warmup_pool_parallel(repo_name, max_workers=3)
    parallel_total = time.time() - start_time
    
    print(f"✓ Parallel warmup complete:")
    print(f"  - Total time: {parallel_total:.2f}s")
    print(f"  - Average per slot: {parallel_total / result['slots_warmed']:.2f}s")
    
    # Calculate speedup
    if parallel_total > 0:
        speedup = sequential_total / parallel_total
        print(f"\n--- Performance Improvement ---")
        print(f"  - Speedup: {speedup:.2f}x")
        print(f"  - Time saved: {sequential_total - parallel_total:.2f}s")
        print(f"  - Efficiency: {(speedup / 3) * 100:.1f}% (with 3 workers)")


def main():
    """Run all performance optimization examples."""
    print("\n" + "=" * 60)
    print("Repo Pool Manager - Performance Optimization Examples")
    print("=" * 60)
    
    try:
        # Example 1: Parallel operations
        example_parallel_operations()
        
        # Example 2: Background cleanup
        example_background_cleanup()
        
        # Example 3: Metrics collection
        example_metrics_collection()
        
        # Example 4: Performance comparison
        example_performance_comparison()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

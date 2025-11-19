#!/usr/bin/env python3
"""
Concurrent Allocation Example for Repo Pool Manager

This example demonstrates:
1. Multiple processes allocating slots concurrently
2. Lock-based concurrency control preventing double allocation
3. Handling NoAvailableSlotError when pool is exhausted
4. Monitoring allocation patterns across concurrent workers

Requirements: Task 4 (Concurrency Control), Task 2 (Slot Allocation)
"""

import time
import multiprocessing as mp
from pathlib import Path
from datetime import datetime

from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.exceptions import NoAvailableSlotError, LockTimeoutError


def worker_allocate_and_work(worker_id: int, repo_name: str, workspaces_dir: Path, work_duration: float):
    """
    Worker function that allocates a slot, performs work, and releases it.
    
    Args:
        worker_id: Unique identifier for this worker
        repo_name: Name of the repository pool
        workspaces_dir: Directory containing workspaces
        work_duration: How long to simulate work (seconds)
    """
    # Each worker creates its own PoolManager instance
    config = PoolConfig(workspaces_dir=workspaces_dir, lock_timeout=10.0)
    manager = PoolManager(config=config)
    
    try:
        print(f"[Worker {worker_id}] Attempting to allocate slot...")
        start_time = time.time()
        
        # Allocate a slot (with automatic locking)
        slot = manager.allocate_slot(repo_name, metadata={"worker_id": worker_id})
        
        allocation_time = time.time() - start_time
        print(f"[Worker {worker_id}] ✓ Allocated {slot.slot_id} in {allocation_time:.2f}s")
        
        # Simulate work
        print(f"[Worker {worker_id}] Working for {work_duration}s...")
        time.sleep(work_duration)
        
        # Release the slot
        print(f"[Worker {worker_id}] Releasing {slot.slot_id}...")
        manager.release_slot(slot.slot_id)
        
        print(f"[Worker {worker_id}] ✓ Released {slot.slot_id}")
        
        return {
            "worker_id": worker_id,
            "slot_id": slot.slot_id,
            "allocation_time": allocation_time,
            "success": True
        }
        
    except NoAvailableSlotError:
        print(f"[Worker {worker_id}] ✗ No available slots")
        return {
            "worker_id": worker_id,
            "slot_id": None,
            "allocation_time": None,
            "success": False,
            "error": "NoAvailableSlotError"
        }
        
    except LockTimeoutError:
        print(f"[Worker {worker_id}] ✗ Lock timeout")
        return {
            "worker_id": worker_id,
            "slot_id": None,
            "allocation_time": None,
            "success": False,
            "error": "LockTimeoutError"
        }
        
    except Exception as e:
        print(f"[Worker {worker_id}] ✗ Error: {e}")
        return {
            "worker_id": worker_id,
            "slot_id": None,
            "allocation_time": None,
            "success": False,
            "error": str(e)
        }


def example_basic_concurrent_allocation():
    """Example 1: Basic concurrent allocation with multiple workers."""
    print("=" * 70)
    print("Example 1: Basic Concurrent Allocation")
    print("=" * 70)
    
    # Setup
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_concurrent_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "concurrent-test"
    repo_url = "https://github.com/octocat/Hello-World.git"
    num_slots = 3
    num_workers = 5  # More workers than slots
    
    # Create pool
    print(f"\nCreating pool '{repo_name}' with {num_slots} slots...")
    try:
        pool = manager.create_pool(repo_name, repo_url, num_slots)
        print(f"✓ Pool created with {len(pool.slots)} slots")
    except ValueError:
        print(f"Pool '{repo_name}' already exists, using existing pool")
    
    # Launch concurrent workers
    print(f"\nLaunching {num_workers} concurrent workers...")
    print(f"(Note: Only {num_slots} can work simultaneously)\n")
    
    with mp.Pool(processes=num_workers) as pool:
        results = pool.starmap(
            worker_allocate_and_work,
            [(i, repo_name, workspaces_dir, 2.0) for i in range(num_workers)]
        )
    
    # Analyze results
    print("\n" + "=" * 70)
    print("Results Summary")
    print("=" * 70)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\nSuccessful allocations: {len(successful)}/{num_workers}")
    print(f"Failed allocations: {len(failed)}/{num_workers}")
    
    if successful:
        avg_allocation_time = sum(r["allocation_time"] for r in successful) / len(successful)
        print(f"Average allocation time: {avg_allocation_time:.2f}s")
        
        print("\nSlot usage:")
        slot_usage = {}
        for r in successful:
            slot_id = r["slot_id"]
            slot_usage[slot_id] = slot_usage.get(slot_id, 0) + 1
        
        for slot_id, count in sorted(slot_usage.items()):
            print(f"  {slot_id}: {count} allocation(s)")
    
    if failed:
        print("\nFailure reasons:")
        error_counts = {}
        for r in failed:
            error = r.get("error", "Unknown")
            error_counts[error] = error_counts.get(error, 0) + 1
        
        for error, count in error_counts.items():
            print(f"  {error}: {count}")


def example_wave_allocation():
    """Example 2: Wave-based allocation pattern."""
    print("\n" + "=" * 70)
    print("Example 2: Wave-Based Allocation")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_concurrent_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "concurrent-test"
    num_waves = 3
    workers_per_wave = 4
    
    print(f"\nRunning {num_waves} waves of {workers_per_wave} workers each...")
    
    all_results = []
    
    for wave in range(num_waves):
        print(f"\n--- Wave {wave + 1}/{num_waves} ---")
        
        with mp.Pool(processes=workers_per_wave) as pool:
            results = pool.starmap(
                worker_allocate_and_work,
                [(i + wave * workers_per_wave, repo_name, workspaces_dir, 1.0) 
                 for i in range(workers_per_wave)]
            )
        
        all_results.extend(results)
        
        successful = len([r for r in results if r["success"]])
        print(f"Wave {wave + 1} complete: {successful}/{workers_per_wave} successful")
        
        # Brief pause between waves
        time.sleep(0.5)
    
    # Overall summary
    print("\n" + "=" * 70)
    print("Overall Summary")
    print("=" * 70)
    
    total_successful = len([r for r in all_results if r["success"]])
    total_workers = num_waves * workers_per_wave
    
    print(f"\nTotal allocations: {total_successful}/{total_workers}")
    print(f"Success rate: {(total_successful / total_workers) * 100:.1f}%")


def example_stress_test():
    """Example 3: Stress test with rapid allocation/release cycles."""
    print("\n" + "=" * 70)
    print("Example 3: Stress Test")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_concurrent_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "concurrent-test"
    num_workers = 10
    work_duration = 0.5  # Short work duration for rapid cycling
    
    print(f"\nStress testing with {num_workers} workers...")
    print(f"Work duration: {work_duration}s per allocation\n")
    
    start_time = time.time()
    
    with mp.Pool(processes=num_workers) as pool:
        results = pool.starmap(
            worker_allocate_and_work,
            [(i, repo_name, workspaces_dir, work_duration) for i in range(num_workers)]
        )
    
    total_time = time.time() - start_time
    
    # Analyze results
    print("\n" + "=" * 70)
    print("Stress Test Results")
    print("=" * 70)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\nTotal time: {total_time:.2f}s")
    print(f"Successful: {len(successful)}/{num_workers}")
    print(f"Failed: {len(failed)}/{num_workers}")
    print(f"Throughput: {len(successful) / total_time:.2f} allocations/second")
    
    if successful:
        allocation_times = [r["allocation_time"] for r in successful]
        print(f"\nAllocation times:")
        print(f"  Min: {min(allocation_times):.3f}s")
        print(f"  Max: {max(allocation_times):.3f}s")
        print(f"  Avg: {sum(allocation_times) / len(allocation_times):.3f}s")


def example_monitor_pool_during_load():
    """Example 4: Monitor pool status during concurrent load."""
    print("\n" + "=" * 70)
    print("Example 4: Pool Monitoring During Load")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_concurrent_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "concurrent-test"
    num_workers = 6
    work_duration = 3.0  # Longer duration to observe state changes
    
    print(f"\nStarting {num_workers} workers with {work_duration}s work duration...")
    print("Monitoring pool status every 0.5s...\n")
    
    # Start workers in background
    pool = mp.Pool(processes=num_workers)
    async_result = pool.starmap_async(
        worker_allocate_and_work,
        [(i, repo_name, workspaces_dir, work_duration) for i in range(num_workers)]
    )
    
    # Monitor pool status while workers are running
    print(f"{'Time':<8} {'Available':<12} {'Allocated':<12} {'Cleaning':<12} {'Error':<8}")
    print("-" * 60)
    
    start_time = time.time()
    while not async_result.ready():
        elapsed = time.time() - start_time
        summary = manager.get_pool_summary()
        
        if repo_name in summary:
            pool_summary = summary[repo_name]
            print(f"{elapsed:>6.1f}s  "
                  f"{pool_summary.available_slots:<12} "
                  f"{pool_summary.allocated_slots:<12} "
                  f"{pool_summary.cleaning_slots:<12} "
                  f"{pool_summary.error_slots:<8}")
        
        time.sleep(0.5)
    
    # Get results
    results = async_result.get()
    pool.close()
    pool.join()
    
    # Final summary
    print("\n" + "=" * 70)
    print("Final Status")
    print("=" * 70)
    
    summary = manager.get_pool_summary()
    if repo_name in summary:
        pool_summary = summary[repo_name]
        print(f"\nPool: {repo_name}")
        print(f"  Total slots: {pool_summary.total_slots}")
        print(f"  Available: {pool_summary.available_slots}")
        print(f"  Allocated: {pool_summary.allocated_slots}")
        print(f"  Total allocations: {pool_summary.total_allocations}")
    
    successful = len([r for r in results if r["success"]])
    print(f"\nWorker results: {successful}/{num_workers} successful")


def main():
    """Run all concurrent allocation examples."""
    print("\n" + "=" * 70)
    print("Repo Pool Manager - Concurrent Allocation Examples")
    print("=" * 70)
    
    try:
        # Example 1: Basic concurrent allocation
        example_basic_concurrent_allocation()
        
        # Example 2: Wave-based allocation
        example_wave_allocation()
        
        # Example 3: Stress test
        example_stress_test()
        
        # Example 4: Monitor during load
        example_monitor_pool_during_load()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Required for multiprocessing on some platforms
    mp.set_start_method('spawn', force=True)
    main()

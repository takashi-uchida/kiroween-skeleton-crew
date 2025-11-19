#!/usr/bin/env python3
"""
Basic Pool Usage Example for Repo Pool Manager

This is a simple, beginner-friendly example demonstrating the core workflow:
1. Initialize PoolManager
2. Create a pool
3. Allocate a slot
4. Use the slot for work
5. Release the slot
6. Check pool status

For more advanced examples, see:
- concurrent_allocation.py - Concurrent access patterns
- custom_cleanup.py - Custom cleanup operations
- error_recovery_example.py - Error handling and recovery
- performance_optimization_example.py - Performance tuning
"""

from pathlib import Path
from necrocode.repo_pool import PoolManager, PoolConfig


def main():
    """Simple example of basic pool operations."""
    
    print("=" * 70)
    print("Repo Pool Manager - Basic Usage Example")
    print("=" * 70)
    
    # Step 1: Initialize PoolManager
    print("\n1. Initialize PoolManager")
    print("-" * 70)
    
    config = PoolConfig(
        workspaces_dir=Path.home() / ".necrocode" / "workspaces_basic_example",
        lock_timeout=30.0,
        cleanup_timeout=60.0
    )
    manager = PoolManager(config=config)
    
    print(f"✓ PoolManager initialized")
    print(f"  Workspaces directory: {config.workspaces_dir}")
    
    # Step 2: Create a pool
    print("\n2. Create a Pool")
    print("-" * 70)
    
    repo_name = "hello-world"
    repo_url = "https://github.com/octocat/Hello-World.git"
    num_slots = 3
    
    print(f"Creating pool '{repo_name}' with {num_slots} slots...")
    print(f"Repository: {repo_url}")
    
    try:
        pool = manager.create_pool(
            repo_name=repo_name,
            repo_url=repo_url,
            num_slots=num_slots
        )
        print(f"✓ Pool created successfully")
        print(f"  Pool name: {pool.repo_name}")
        print(f"  Total slots: {pool.num_slots}")
        print(f"  Created at: {pool.created_at}")
    except ValueError as e:
        print(f"Pool already exists: {e}")
        pool = manager.get_pool(repo_name)
        print(f"✓ Using existing pool with {pool.num_slots} slots")
    
    # Step 3: Check pool status
    print("\n3. Check Pool Status")
    print("-" * 70)
    
    summary = manager.get_pool_summary()
    if repo_name in summary:
        pool_summary = summary[repo_name]
        print(f"Pool: {repo_name}")
        print(f"  Total slots: {pool_summary.total_slots}")
        print(f"  Available: {pool_summary.available_slots}")
        print(f"  Allocated: {pool_summary.allocated_slots}")
        print(f"  Cleaning: {pool_summary.cleaning_slots}")
        print(f"  Error: {pool_summary.error_slots}")
    
    # Step 4: Allocate a slot
    print("\n4. Allocate a Slot")
    print("-" * 70)
    
    print(f"Requesting slot from pool '{repo_name}'...")
    slot = manager.allocate_slot(
        repo_name=repo_name,
        metadata={"task": "example-task", "user": "demo"}
    )
    
    if slot:
        print(f"✓ Slot allocated successfully")
        print(f"  Slot ID: {slot.slot_id}")
        print(f"  Path: {slot.slot_path}")
        print(f"  State: {slot.state.value}")
        print(f"  Current branch: {slot.current_branch}")
        print(f"  Current commit: {slot.current_commit[:8] if slot.current_commit else 'N/A'}")
    else:
        print("✗ No available slots")
        return
    
    # Step 5: Use the slot (simulate work)
    print("\n5. Use the Slot")
    print("-" * 70)
    
    print(f"Working in slot: {slot.slot_path}")
    print("  (In a real scenario, you would:")
    print("   - Checkout a branch")
    print("   - Make code changes")
    print("   - Run tests")
    print("   - Commit changes")
    print("   - etc.)")
    
    # Example: Check current branch
    from necrocode.repo_pool.git_operations import GitOperations
    git_ops = GitOperations()
    
    current_branch = git_ops.get_current_branch(slot.slot_path)
    print(f"\n  Current branch: {current_branch}")
    
    # Example: List remote branches
    remote_branches = git_ops.list_remote_branches(slot.slot_path)
    print(f"  Remote branches: {len(remote_branches)} found")
    if remote_branches:
        print(f"    First 3: {', '.join(remote_branches[:3])}")
    
    # Step 6: Check slot status
    print("\n6. Check Slot Status")
    print("-" * 70)
    
    status = manager.get_slot_status(slot.slot_id)
    print(f"Slot: {slot.slot_id}")
    print(f"  State: {status.state.value}")
    print(f"  Locked: {status.is_locked}")
    print(f"  Allocation count: {status.allocation_count}")
    print(f"  Last allocated: {status.last_allocated_at}")
    print(f"  Disk usage: {status.disk_usage_mb:.2f} MB")
    
    # Step 7: Release the slot
    print("\n7. Release the Slot")
    print("-" * 70)
    
    print(f"Releasing slot: {slot.slot_id}")
    manager.release_slot(slot.slot_id)
    print(f"✓ Slot released successfully")
    print("  (Automatic cleanup performed: fetch, clean, reset)")
    
    # Step 8: Final pool status
    print("\n8. Final Pool Status")
    print("-" * 70)
    
    summary = manager.get_pool_summary()
    if repo_name in summary:
        pool_summary = summary[repo_name]
        print(f"Pool: {repo_name}")
        print(f"  Total slots: {pool_summary.total_slots}")
        print(f"  Available: {pool_summary.available_slots}")
        print(f"  Allocated: {pool_summary.allocated_slots}")
        print(f"  Total allocations: {pool_summary.total_allocations}")
        print(f"  Average allocation time: {pool_summary.average_allocation_time_seconds:.2f}s")
    
    # Summary
    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  1. PoolManager handles all pool and slot operations")
    print("  2. Slots are automatically cleaned before allocation and after release")
    print("  3. File-based locking prevents concurrent access to the same slot")
    print("  4. Pool status can be monitored at any time")
    print("\nNext steps:")
    print("  - See concurrent_allocation.py for parallel usage")
    print("  - See custom_cleanup.py for cleanup customization")
    print("  - See error_recovery_example.py for error handling")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

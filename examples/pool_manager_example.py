"""
Example usage of PoolManager.

This example demonstrates:
1. Creating a pool with multiple slots
2. Allocating and releasing slots
3. Getting slot status and pool summaries
4. Adding and removing slots dynamically
"""

import tempfile
from pathlib import Path

from necrocode.repo_pool import (
    PoolManager,
    PoolConfig,
    SlotState,
    NoAvailableSlotError,
)


def main():
    """Demonstrate PoolManager usage."""
    
    # Create a temporary directory for this example
    with tempfile.TemporaryDirectory() as tmpdir:
        print("=" * 60)
        print("PoolManager Example")
        print("=" * 60)
        
        # Initialize PoolManager with custom config
        config = PoolConfig(
            workspaces_dir=Path(tmpdir) / "workspaces",
            lock_timeout=10.0,
        )
        manager = PoolManager(config)
        print(f"\n✓ Initialized PoolManager")
        print(f"  Workspaces directory: {config.workspaces_dir}")
        
        # Note: For this example to work with real git operations,
        # you would need a valid git repository URL.
        # Here we'll demonstrate the API without actual git operations.
        
        print("\n" + "=" * 60)
        print("1. List Pools (should be empty)")
        print("=" * 60)
        pools = manager.list_pools()
        print(f"Pools: {pools}")
        
        print("\n" + "=" * 60)
        print("2. Get Pool Summary (should be empty)")
        print("=" * 60)
        summary = manager.get_pool_summary()
        print(f"Summary: {summary}")
        
        # To demonstrate pool creation, you would need a real git repo:
        # 
        # print("\n" + "=" * 60)
        # print("3. Create Pool")
        # print("=" * 60)
        # pool = manager.create_pool(
        #     repo_name="example-repo",
        #     repo_url="https://github.com/user/example-repo.git",
        #     num_slots=3
        # )
        # print(f"Created pool: {pool.repo_name}")
        # print(f"  Number of slots: {pool.num_slots}")
        # print(f"  Available slots: {len(pool.get_available_slots())}")
        #
        # print("\n" + "=" * 60)
        # print("4. Allocate Slot")
        # print("=" * 60)
        # slot = manager.allocate_slot("example-repo")
        # print(f"Allocated slot: {slot.slot_id}")
        # print(f"  State: {slot.state.value}")
        # print(f"  Path: {slot.slot_path}")
        # print(f"  Branch: {slot.current_branch}")
        #
        # print("\n" + "=" * 60)
        # print("5. Get Slot Status")
        # print("=" * 60)
        # status = manager.get_slot_status(slot.slot_id)
        # print(f"Slot status: {slot.slot_id}")
        # print(f"  State: {status.state.value}")
        # print(f"  Locked: {status.is_locked}")
        # print(f"  Allocations: {status.allocation_count}")
        # print(f"  Disk usage: {status.disk_usage_mb:.2f} MB")
        #
        # print("\n" + "=" * 60)
        # print("6. Release Slot")
        # print("=" * 60)
        # manager.release_slot(slot.slot_id)
        # print(f"Released slot: {slot.slot_id}")
        #
        # print("\n" + "=" * 60)
        # print("7. Add Slot Dynamically")
        # print("=" * 60)
        # new_slot = manager.add_slot("example-repo")
        # print(f"Added new slot: {new_slot.slot_id}")
        #
        # print("\n" + "=" * 60)
        # print("8. Get Pool Summary")
        # print("=" * 60)
        # summary = manager.get_pool_summary()
        # for repo_name, pool_summary in summary.items():
        #     print(f"\nPool: {repo_name}")
        #     print(f"  Total slots: {pool_summary.total_slots}")
        #     print(f"  Available: {pool_summary.available_slots}")
        #     print(f"  Allocated: {pool_summary.allocated_slots}")
        #     print(f"  Total allocations: {pool_summary.total_allocations}")
        #
        # print("\n" + "=" * 60)
        # print("9. Remove Slot")
        # print("=" * 60)
        # manager.remove_slot(new_slot.slot_id)
        # print(f"Removed slot: {new_slot.slot_id}")
        
        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)
        print("\nNote: To run with actual git operations, provide a valid")
        print("repository URL and uncomment the code sections above.")


if __name__ == "__main__":
    main()

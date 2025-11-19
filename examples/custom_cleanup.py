#!/usr/bin/env python3
"""
Custom Cleanup Example for Repo Pool Manager

This example demonstrates:
1. Customizing cleanup operations before allocation
2. Customizing cleanup operations after release
3. Selective cleanup (skip certain operations)
4. Custom cleanup hooks and callbacks
5. Cleanup verification and integrity checks

Requirements: Task 5 (Slot Cleaner), Task 3 (Cleanup Operations)
"""

import time
from pathlib import Path
from typing import List, Optional

from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.slot_cleaner import SlotCleaner
from necrocode.repo_pool.models import Slot, CleanupResult
from necrocode.repo_pool.git_operations import GitOperations


def example_selective_cleanup():
    """Example 1: Selective cleanup operations."""
    print("=" * 70)
    print("Example 1: Selective Cleanup")
    print("=" * 70)
    
    # Initialize pool manager
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_cleanup_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "cleanup-test"
    repo_url = "https://github.com/octocat/Hello-World.git"
    
    # Create pool
    print(f"\nCreating pool '{repo_name}'...")
    try:
        pool = manager.create_pool(repo_name, repo_url, num_slots=2)
        print(f"✓ Pool created with {len(pool.slots)} slots")
    except ValueError:
        print(f"Pool '{repo_name}' already exists")
        pool = manager.get_pool(repo_name)
    
    # Allocate with custom cleanup options
    print("\n--- Allocation with selective cleanup ---")
    
    # Option 1: Skip fetch (faster, but may not have latest changes)
    print("\n1. Allocate without fetch:")
    slot = manager.allocate_slot(repo_name, skip_fetch=True)
    print(f"✓ Allocated {slot.slot_id} (fetch skipped)")
    manager.release_slot(slot.slot_id)
    
    # Option 2: Skip cleanup entirely (fastest, but risky)
    print("\n2. Allocate without any cleanup:")
    slot = manager.allocate_slot(repo_name, skip_cleanup=True)
    print(f"✓ Allocated {slot.slot_id} (cleanup skipped)")
    manager.release_slot(slot.slot_id, cleanup=False)
    print(f"✓ Released {slot.slot_id} (cleanup skipped)")
    
    # Option 3: Full cleanup (safest, but slower)
    print("\n3. Allocate with full cleanup:")
    slot = manager.allocate_slot(repo_name)
    print(f"✓ Allocated {slot.slot_id} (full cleanup)")
    manager.release_slot(slot.slot_id)
    print(f"✓ Released {slot.slot_id} (full cleanup)")


def example_custom_cleanup_operations():
    """Example 2: Define custom cleanup operations."""
    print("\n" + "=" * 70)
    print("Example 2: Custom Cleanup Operations")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_cleanup_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "cleanup-test"
    
    # Get a slot
    slot = manager.allocate_slot(repo_name)
    print(f"\n✓ Allocated {slot.slot_id}")
    
    # Define custom cleanup function
    def custom_cleanup(slot: Slot) -> CleanupResult:
        """Custom cleanup that also removes build artifacts."""
        print(f"\n--- Running custom cleanup for {slot.slot_id} ---")
        
        cleaner = SlotCleaner()
        git_ops = GitOperations()
        operations = []
        errors = []
        start_time = time.time()
        
        # 1. Standard git operations
        print("  1. Fetching latest changes...")
        result = git_ops.fetch_all(slot.slot_path)
        operations.append("fetch")
        if not result.success:
            errors.append(f"Fetch failed: {result.stderr}")
        
        print("  2. Cleaning untracked files...")
        result = git_ops.clean(slot.slot_path, force=True)
        operations.append("clean")
        if not result.success:
            errors.append(f"Clean failed: {result.stderr}")
        
        print("  3. Resetting working directory...")
        result = git_ops.reset_hard(slot.slot_path)
        operations.append("reset")
        if not result.success:
            errors.append(f"Reset failed: {result.stderr}")
        
        # 4. Custom: Remove build artifacts
        print("  4. Removing build artifacts...")
        build_dirs = ["node_modules", "dist", "build", "__pycache__", ".pytest_cache"]
        for build_dir in build_dirs:
            dir_path = slot.slot_path / build_dir
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                print(f"     Removed: {build_dir}")
        operations.append("remove_build_artifacts")
        
        # 5. Custom: Clear log files
        print("  5. Clearing log files...")
        log_patterns = ["*.log", "*.tmp"]
        for pattern in log_patterns:
            for log_file in slot.slot_path.glob(f"**/{pattern}"):
                log_file.unlink()
                print(f"     Removed: {log_file.name}")
        operations.append("clear_logs")
        
        duration = time.time() - start_time
        
        return CleanupResult(
            slot_id=slot.slot_id,
            success=len(errors) == 0,
            duration_seconds=duration,
            operations=operations,
            errors=errors
        )
    
    # Run custom cleanup
    result = custom_cleanup(slot)
    
    print(f"\n--- Cleanup Results ---")
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Operations: {', '.join(result.operations)}")
    if result.errors:
        print(f"Errors: {', '.join(result.errors)}")
    
    # Release slot
    manager.release_slot(slot.slot_id)


def example_cleanup_with_verification():
    """Example 3: Cleanup with integrity verification."""
    print("\n" + "=" * 70)
    print("Example 3: Cleanup with Verification")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_cleanup_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "cleanup-test"
    
    # Allocate slot
    slot = manager.allocate_slot(repo_name)
    print(f"\n✓ Allocated {slot.slot_id}")
    
    # Perform cleanup with verification
    print("\n--- Cleanup with verification ---")
    
    cleaner = SlotCleaner()
    
    # 1. Run cleanup
    print("1. Running cleanup...")
    result = cleaner.cleanup_before_allocation(slot)
    print(f"   ✓ Cleanup complete in {result.duration_seconds:.2f}s")
    
    # 2. Verify integrity
    print("2. Verifying slot integrity...")
    is_valid = cleaner.verify_slot_integrity(slot)
    
    if is_valid:
        print("   ✓ Slot integrity verified")
    else:
        print("   ✗ Slot integrity check failed")
        
        # 3. Attempt repair if needed
        print("3. Attempting to repair slot...")
        repair_result = cleaner.repair_slot(slot)
        
        if repair_result.success:
            print(f"   ✓ Slot repaired successfully")
            print(f"   Operations: {', '.join(repair_result.operations)}")
        else:
            print(f"   ✗ Repair failed")
            print(f"   Errors: {', '.join(repair_result.errors)}")
    
    # Release slot
    manager.release_slot(slot.slot_id)


def example_cleanup_callbacks():
    """Example 4: Cleanup with progress callbacks."""
    print("\n" + "=" * 70)
    print("Example 4: Cleanup with Callbacks")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_cleanup_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "cleanup-test"
    
    # Define callback functions
    def on_operation_start(operation: str, slot_id: str):
        """Called when a cleanup operation starts."""
        print(f"  → Starting: {operation} on {slot_id}")
    
    def on_operation_complete(operation: str, slot_id: str, success: bool, duration: float):
        """Called when a cleanup operation completes."""
        status = "✓" if success else "✗"
        print(f"  {status} Completed: {operation} in {duration:.2f}s")
    
    def on_cleanup_complete(slot_id: str, result: CleanupResult):
        """Called when entire cleanup is complete."""
        print(f"\n  Cleanup summary for {slot_id}:")
        print(f"    Success: {result.success}")
        print(f"    Total duration: {result.duration_seconds:.2f}s")
        print(f"    Operations: {len(result.operations)}")
    
    # Custom cleanup with callbacks
    print("\n--- Cleanup with progress callbacks ---")
    
    slot = manager.allocate_slot(repo_name)
    print(f"\nAllocated {slot.slot_id}\n")
    
    cleaner = SlotCleaner()
    git_ops = GitOperations()
    
    operations = [
        ("fetch", lambda: git_ops.fetch_all(slot.slot_path)),
        ("clean", lambda: git_ops.clean(slot.slot_path, force=True)),
        ("reset", lambda: git_ops.reset_hard(slot.slot_path)),
    ]
    
    all_operations = []
    errors = []
    total_start = time.time()
    
    for op_name, op_func in operations:
        on_operation_start(op_name, slot.slot_id)
        
        op_start = time.time()
        result = op_func()
        op_duration = time.time() - op_start
        
        all_operations.append(op_name)
        if not result.success:
            errors.append(f"{op_name} failed: {result.stderr}")
        
        on_operation_complete(op_name, slot.slot_id, result.success, op_duration)
    
    total_duration = time.time() - total_start
    
    cleanup_result = CleanupResult(
        slot_id=slot.slot_id,
        success=len(errors) == 0,
        duration_seconds=total_duration,
        operations=all_operations,
        errors=errors
    )
    
    on_cleanup_complete(slot.slot_id, cleanup_result)
    
    # Release slot
    manager.release_slot(slot.slot_id)


def example_conditional_cleanup():
    """Example 5: Conditional cleanup based on slot state."""
    print("\n" + "=" * 70)
    print("Example 5: Conditional Cleanup")
    print("=" * 70)
    
    workspaces_dir = Path.home() / ".necrocode" / "workspaces_cleanup_test"
    config = PoolConfig(workspaces_dir=workspaces_dir)
    manager = PoolManager(config=config)
    
    repo_name = "cleanup-test"
    
    def smart_cleanup(slot: Slot) -> CleanupResult:
        """
        Intelligent cleanup that adapts based on slot state.
        
        - If recently used: Skip fetch (use cached state)
        - If long idle: Full cleanup including fetch
        - If error state: Force cleanup and repair
        """
        from datetime import datetime, timedelta
        
        print(f"\n--- Smart cleanup for {slot.slot_id} ---")
        
        cleaner = SlotCleaner()
        git_ops = GitOperations()
        operations = []
        errors = []
        start_time = time.time()
        
        # Determine cleanup strategy
        now = datetime.now()
        recently_used_threshold = timedelta(minutes=30)
        
        if slot.last_released_at and (now - slot.last_released_at) < recently_used_threshold:
            print("  Strategy: Light cleanup (recently used)")
            
            # Skip fetch, just clean and reset
            print("  - Cleaning untracked files...")
            result = git_ops.clean(slot.slot_path, force=True)
            operations.append("clean")
            if not result.success:
                errors.append(f"Clean failed: {result.stderr}")
            
            print("  - Resetting working directory...")
            result = git_ops.reset_hard(slot.slot_path)
            operations.append("reset")
            if not result.success:
                errors.append(f"Reset failed: {result.stderr}")
        
        else:
            print("  Strategy: Full cleanup (idle or first use)")
            
            # Full cleanup including fetch
            print("  - Fetching latest changes...")
            result = git_ops.fetch_all(slot.slot_path)
            operations.append("fetch")
            if not result.success:
                errors.append(f"Fetch failed: {result.stderr}")
            
            print("  - Cleaning untracked files...")
            result = git_ops.clean(slot.slot_path, force=True)
            operations.append("clean")
            if not result.success:
                errors.append(f"Clean failed: {result.stderr}")
            
            print("  - Resetting working directory...")
            result = git_ops.reset_hard(slot.slot_path)
            operations.append("reset")
            if not result.success:
                errors.append(f"Reset failed: {result.stderr}")
            
            # Verify integrity
            print("  - Verifying integrity...")
            if not cleaner.verify_slot_integrity(slot):
                print("  - Integrity check failed, repairing...")
                repair_result = cleaner.repair_slot(slot)
                operations.append("repair")
                if not repair_result.success:
                    errors.extend(repair_result.errors)
        
        duration = time.time() - start_time
        
        return CleanupResult(
            slot_id=slot.slot_id,
            success=len(errors) == 0,
            duration_seconds=duration,
            operations=operations,
            errors=errors
        )
    
    # Test with multiple allocations
    print("\n--- First allocation (full cleanup expected) ---")
    slot1 = manager.allocate_slot(repo_name)
    result1 = smart_cleanup(slot1)
    print(f"Operations: {', '.join(result1.operations)}")
    print(f"Duration: {result1.duration_seconds:.2f}s")
    manager.release_slot(slot1.slot_id)
    
    # Immediate re-allocation (light cleanup expected)
    print("\n--- Immediate re-allocation (light cleanup expected) ---")
    slot2 = manager.allocate_slot(repo_name)
    result2 = smart_cleanup(slot2)
    print(f"Operations: {', '.join(result2.operations)}")
    print(f"Duration: {result2.duration_seconds:.2f}s")
    manager.release_slot(slot2.slot_id)
    
    print(f"\n--- Comparison ---")
    print(f"First cleanup: {len(result1.operations)} operations, {result1.duration_seconds:.2f}s")
    print(f"Second cleanup: {len(result2.operations)} operations, {result2.duration_seconds:.2f}s")
    print(f"Time saved: {result1.duration_seconds - result2.duration_seconds:.2f}s")


def main():
    """Run all custom cleanup examples."""
    print("\n" + "=" * 70)
    print("Repo Pool Manager - Custom Cleanup Examples")
    print("=" * 70)
    
    try:
        # Example 1: Selective cleanup
        example_selective_cleanup()
        
        # Example 2: Custom cleanup operations
        example_custom_cleanup_operations()
        
        # Example 3: Cleanup with verification
        example_cleanup_with_verification()
        
        # Example 4: Cleanup callbacks
        example_cleanup_callbacks()
        
        # Example 5: Conditional cleanup
        example_conditional_cleanup()
        
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
    main()

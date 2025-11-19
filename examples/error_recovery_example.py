"""
Example: Error Handling and Recovery in Repo Pool Manager

This example demonstrates:
1. Detecting anomalies (long-allocated slots, corrupted slots, orphaned locks)
2. Manual slot recovery
3. Automatic recovery with different options
4. Slot isolation for manual intervention
"""

import logging
import time
from pathlib import Path
from datetime import datetime, timedelta

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.models import SlotState


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_detect_anomalies():
    """Example: Detect various anomalies in the pool system."""
    print("\n" + "="*70)
    print("Example 1: Detecting Anomalies")
    print("="*70)
    
    # Create pool manager
    config = PoolConfig(
        workspaces_dir=Path("./test_workspaces_recovery"),
        stale_lock_hours=1  # Consider locks older than 1 hour as stale
    )
    manager = PoolManager(config=config)
    
    # Create a test pool
    try:
        pool = manager.create_pool(
            repo_name="test-repo",
            repo_url="https://github.com/octocat/Hello-World.git",
            num_slots=3
        )
        print(f"✓ Created pool with {pool.num_slots} slots")
    except Exception as e:
        print(f"Pool may already exist: {e}")
    
    # Simulate a long-allocated slot
    print("\n--- Simulating long-allocated slot ---")
    slot1 = manager.allocate_slot("test-repo")
    if slot1:
        # Manually set allocation time to 25 hours ago
        slot1.last_allocated_at = datetime.now() - timedelta(hours=25)
        manager.slot_store.save_slot(slot1)
        print(f"✓ Simulated long allocation for {slot1.slot_id}")
    
    # Detect anomalies
    print("\n--- Running anomaly detection ---")
    anomalies = manager.detect_anomalies(max_allocation_hours=24)
    
    print(f"\nAnomaly Detection Results:")
    print(f"  Long-allocated slots: {len(anomalies['long_allocated_slots'])}")
    for slot in anomalies['long_allocated_slots']:
        duration = datetime.now() - slot.last_allocated_at
        print(f"    - {slot.slot_id}: allocated for {duration}")
    
    print(f"  Corrupted slots: {len(anomalies['corrupted_slots'])}")
    for slot in anomalies['corrupted_slots']:
        print(f"    - {slot.slot_id}: state={slot.state.value}")
    
    print(f"  Orphaned locks: {len(anomalies['orphaned_locks'])}")
    for slot_id in anomalies['orphaned_locks']:
        print(f"    - {slot_id}")
    
    # Clean up
    if slot1:
        manager.release_slot(slot1.slot_id)


def example_manual_recovery():
    """Example: Manually recover a corrupted slot."""
    print("\n" + "="*70)
    print("Example 2: Manual Slot Recovery")
    print("="*70)
    
    config = PoolConfig(workspaces_dir=Path("./test_workspaces_recovery"))
    manager = PoolManager(config=config)
    
    # Get a slot
    try:
        slot = manager.allocate_slot("test-repo")
        if not slot:
            print("No available slots")
            return
        
        print(f"✓ Allocated slot: {slot.slot_id}")
        
        # Simulate corruption by marking as ERROR
        print("\n--- Simulating slot corruption ---")
        slot.state = SlotState.ERROR
        manager.slot_store.save_slot(slot)
        print(f"✓ Marked {slot.slot_id} as ERROR")
        
        # Attempt recovery
        print("\n--- Attempting recovery ---")
        success = manager.recover_slot(slot.slot_id, force=False)
        
        if success:
            print(f"✓ Successfully recovered {slot.slot_id}")
            
            # Verify recovery
            recovered_slot = manager.slot_store.load_slot(slot.slot_id)
            print(f"  State after recovery: {recovered_slot.state.value}")
        else:
            print(f"✗ Failed to recover {slot.slot_id}")
            
            # Try force recovery
            print("\n--- Attempting force recovery ---")
            success = manager.recover_slot(slot.slot_id, force=True)
            if success:
                print(f"✓ Force recovery succeeded for {slot.slot_id}")
        
        # Release slot
        manager.release_slot(slot.slot_id)
        
    except Exception as e:
        print(f"Error: {e}")


def example_slot_isolation():
    """Example: Isolate a problematic slot."""
    print("\n" + "="*70)
    print("Example 3: Slot Isolation")
    print("="*70)
    
    config = PoolConfig(workspaces_dir=Path("./test_workspaces_recovery"))
    manager = PoolManager(config=config)
    
    try:
        # Get a slot
        slot = manager.allocate_slot("test-repo")
        if not slot:
            print("No available slots")
            return
        
        print(f"✓ Allocated slot: {slot.slot_id}")
        
        # Isolate the slot
        print("\n--- Isolating slot ---")
        manager.isolate_slot(slot.slot_id)
        print(f"✓ Isolated {slot.slot_id}")
        
        # Verify isolation
        isolated_slot = manager.slot_store.load_slot(slot.slot_id)
        print(f"  State: {isolated_slot.state.value}")
        print(f"  Isolated at: {isolated_slot.metadata.get('isolated_at')}")
        print(f"  Reason: {isolated_slot.metadata.get('isolation_reason')}")
        
        # Try to allocate - should skip isolated slot
        print("\n--- Attempting to allocate (should skip isolated slot) ---")
        try:
            next_slot = manager.allocate_slot("test-repo")
            if next_slot:
                print(f"✓ Allocated different slot: {next_slot.slot_id}")
                manager.release_slot(next_slot.slot_id)
        except Exception as e:
            print(f"No other slots available: {e}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_auto_recovery():
    """Example: Automatic recovery from anomalies."""
    print("\n" + "="*70)
    print("Example 4: Automatic Recovery")
    print("="*70)
    
    config = PoolConfig(workspaces_dir=Path("./test_workspaces_recovery"))
    manager = PoolManager(config=config)
    
    # Simulate various anomalies
    print("\n--- Setting up anomalies ---")
    
    # 1. Long-allocated slot
    try:
        slot1 = manager.allocate_slot("test-repo")
        if slot1:
            slot1.last_allocated_at = datetime.now() - timedelta(hours=25)
            manager.slot_store.save_slot(slot1)
            print(f"✓ Simulated long allocation: {slot1.slot_id}")
    except:
        pass
    
    # 2. Corrupted slot
    try:
        slot2 = manager.allocate_slot("test-repo")
        if slot2:
            slot2.state = SlotState.ERROR
            manager.slot_store.save_slot(slot2)
            manager.release_slot(slot2.slot_id, cleanup=False)
            print(f"✓ Simulated corruption: {slot2.slot_id}")
    except:
        pass
    
    # Run auto-recovery
    print("\n--- Running automatic recovery ---")
    results = manager.auto_recover(
        max_allocation_hours=24,
        recover_corrupted=True,
        cleanup_orphaned_locks=True,
        force_release_long_allocated=True
    )
    
    print("\nRecovery Results:")
    print(f"  Long-allocated slots released: {results['long_allocated_released']}")
    print(f"  Corrupted slots recovered: {results['corrupted_recovered']}")
    print(f"  Corrupted slots isolated: {results['corrupted_isolated']}")
    print(f"  Orphaned locks cleaned: {results['orphaned_locks_cleaned']}")
    
    if results['errors']:
        print(f"\nErrors encountered:")
        for error in results['errors']:
            print(f"  - {error}")
    else:
        print("\n✓ No errors during recovery")
    
    # Verify pool status after recovery
    print("\n--- Pool status after recovery ---")
    summary = manager.get_pool_summary()
    for repo_name, pool_summary in summary.items():
        print(f"\nPool: {repo_name}")
        print(f"  Total slots: {pool_summary.total_slots}")
        print(f"  Available: {pool_summary.available_slots}")
        print(f"  Allocated: {pool_summary.allocated_slots}")
        print(f"  Error: {pool_summary.error_slots}")


def example_comprehensive_health_check():
    """Example: Comprehensive health check and recovery."""
    print("\n" + "="*70)
    print("Example 5: Comprehensive Health Check")
    print("="*70)
    
    config = PoolConfig(workspaces_dir=Path("./test_workspaces_recovery"))
    manager = PoolManager(config=config)
    
    print("\n--- Step 1: Detect all anomalies ---")
    anomalies = manager.detect_anomalies(max_allocation_hours=24)
    
    total_issues = (
        len(anomalies['long_allocated_slots']) +
        len(anomalies['corrupted_slots']) +
        len(anomalies['orphaned_locks'])
    )
    
    print(f"Total issues found: {total_issues}")
    
    if total_issues == 0:
        print("✓ System is healthy!")
        return
    
    print("\n--- Step 2: Review issues ---")
    
    if anomalies['long_allocated_slots']:
        print(f"\nLong-allocated slots ({len(anomalies['long_allocated_slots'])}):")
        for slot in anomalies['long_allocated_slots']:
            duration = datetime.now() - slot.last_allocated_at
            print(f"  - {slot.slot_id}: {duration}")
    
    if anomalies['corrupted_slots']:
        print(f"\nCorrupted slots ({len(anomalies['corrupted_slots'])}):")
        for slot in anomalies['corrupted_slots']:
            print(f"  - {slot.slot_id}: state={slot.state.value}")
    
    if anomalies['orphaned_locks']:
        print(f"\nOrphaned locks ({len(anomalies['orphaned_locks'])}):")
        for slot_id in anomalies['orphaned_locks']:
            print(f"  - {slot_id}")
    
    print("\n--- Step 3: Automatic recovery ---")
    results = manager.auto_recover(
        max_allocation_hours=24,
        recover_corrupted=True,
        cleanup_orphaned_locks=True,
        force_release_long_allocated=True
    )
    
    print("\nRecovery completed:")
    print(f"  ✓ {results['long_allocated_released']} slots released")
    print(f"  ✓ {results['corrupted_recovered']} slots recovered")
    print(f"  ⚠ {results['corrupted_isolated']} slots isolated")
    print(f"  ✓ {results['orphaned_locks_cleaned']} locks cleaned")
    
    if results['errors']:
        print(f"  ✗ {len(results['errors'])} error(s) occurred")
    
    print("\n--- Step 4: Final health check ---")
    final_anomalies = manager.detect_anomalies(max_allocation_hours=24)
    final_issues = (
        len(final_anomalies['long_allocated_slots']) +
        len(final_anomalies['corrupted_slots']) +
        len(final_anomalies['orphaned_locks'])
    )
    
    print(f"Remaining issues: {final_issues}")
    
    if final_issues == 0:
        print("✓ All issues resolved!")
    else:
        print("⚠ Some issues remain - manual intervention may be required")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("Repo Pool Manager - Error Handling and Recovery Examples")
    print("="*70)
    
    try:
        # Run examples
        example_detect_anomalies()
        time.sleep(1)
        
        example_manual_recovery()
        time.sleep(1)
        
        example_slot_isolation()
        time.sleep(1)
        
        example_auto_recovery()
        time.sleep(1)
        
        example_comprehensive_health_check()
        
        print("\n" + "="*70)
        print("All examples completed!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

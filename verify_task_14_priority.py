#!/usr/bin/env python3
"""
Verification script for Task 14: Priority Management Implementation

This script verifies that all priority management features are working correctly.
"""

import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import SchedulingPolicy
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState
from necrocode.task_registry.kiro_sync import TaskDefinition


def verify_priority_reading():
    """Verify Requirement 7.1: Reading task priority."""
    print("\n=== Verifying Priority Reading (Requirement 7.1) ===")
    
    # Create tasks with different priorities
    tasks = [
        Task(id="1", title="Low", description="", state=TaskState.READY, priority=1),
        Task(id="2", title="High", description="", state=TaskState.READY, priority=10),
        Task(id="3", title="Medium", description="", state=TaskState.READY, priority=5),
    ]
    
    # Verify priority field exists and is readable
    for task in tasks:
        assert hasattr(task, 'priority'), "Task should have priority field"
        assert isinstance(task.priority, int), "Priority should be an integer"
        print(f"✓ Task {task.id}: priority={task.priority}")
    
    print("✅ Priority reading verified")
    return True


def verify_priority_sorting():
    """Verify Requirements 7.2, 7.3: Priority-based sorting with FIFO."""
    print("\n=== Verifying Priority Sorting (Requirements 7.2, 7.3) ===")
    
    temp_dir = tempfile.mkdtemp(prefix="verify_priority_")
    try:
        config = DispatcherConfig(
            task_registry_dir=temp_dir,
            scheduling_policy=SchedulingPolicy.PRIORITY
        )
        dispatcher = DispatcherCore(config)
        
        # Create tasks with different priorities
        tasks = [
            Task(id="1", title="Low", description="", state=TaskState.READY, 
                 priority=1, created_at=datetime(2024, 1, 1, 10, 0, 0)),
            Task(id="2", title="High1", description="", state=TaskState.READY, 
                 priority=10, created_at=datetime(2024, 1, 1, 10, 0, 1)),
            Task(id="3", title="Medium", description="", state=TaskState.READY, 
                 priority=5, created_at=datetime(2024, 1, 1, 10, 0, 2)),
            Task(id="4", title="High2", description="", state=TaskState.READY, 
                 priority=10, created_at=datetime(2024, 1, 1, 10, 0, 3)),
        ]
        
        # Add to queue
        for task in tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Dequeue and verify order
        dequeued = []
        while not dispatcher.task_queue.is_empty():
            task = dispatcher.task_queue.dequeue()
            if task:
                dequeued.append((task.id, task.priority))
        
        # Expected order: High1 (10), High2 (10), Medium (5), Low (1)
        # High1 before High2 due to FIFO (created earlier)
        expected = [("2", 10), ("4", 10), ("3", 5), ("1", 1)]
        
        print(f"Dequeued order: {dequeued}")
        print(f"Expected order: {expected}")
        
        assert dequeued == expected, f"Order mismatch: {dequeued} != {expected}"
        
        print("✓ Higher priority tasks come first")
        print("✓ Same priority tasks maintain FIFO order")
        print("✅ Priority sorting verified")
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def verify_dynamic_priority_change():
    """Verify Requirement 7.4: Dynamic priority changes."""
    print("\n=== Verifying Dynamic Priority Changes (Requirement 7.4) ===")
    
    temp_dir = tempfile.mkdtemp(prefix="verify_priority_")
    try:
        # Create registry and dispatcher
        registry = TaskRegistry(registry_dir=temp_dir)
        config = DispatcherConfig(
            task_registry_dir=temp_dir,
            scheduling_policy=SchedulingPolicy.PRIORITY
        )
        dispatcher = DispatcherCore(config)
        
        # Create taskset
        spec_name = "test-spec"
        task_defs = [
            TaskDefinition(id="1", title="Task 1", description="", 
                          is_optional=False, is_completed=False, dependencies=[]),
            TaskDefinition(id="2", title="Task 2", description="", 
                          is_optional=False, is_completed=False, dependencies=[]),
        ]
        registry.create_taskset(spec_name, task_defs)
        
        # Get tasks and add to queue
        taskset = registry.get_taskset(spec_name)
        taskset.tasks[0].priority = 1  # Task 1: low priority
        taskset.tasks[1].priority = 10  # Task 2: high priority
        
        for task in taskset.tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Verify initial order (Task 2 should be first)
        initial_order = [t.id for t in dispatcher.task_queue.get_all_tasks()]
        print(f"Initial order: {initial_order}")
        assert initial_order[0] == "2", "Task 2 should be first (higher priority)"
        
        # Update Task 1 priority to 15 (higher than Task 2)
        success = dispatcher.update_task_priority(spec_name, "1", 15)
        assert success, "Priority update should succeed"
        print("✓ Priority update succeeded")
        
        # Verify new order (Task 1 should now be first)
        new_order = [t.id for t in dispatcher.task_queue.get_all_tasks()]
        print(f"New order: {new_order}")
        assert new_order[0] == "1", "Task 1 should now be first (updated priority)"
        
        print("✓ Queue reordered after priority change")
        print("✅ Dynamic priority changes verified")
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def verify_scheduling_policy_changes():
    """Verify Requirement 7.5: Enable/disable priority scheduling."""
    print("\n=== Verifying Scheduling Policy Changes (Requirement 7.5) ===")
    
    temp_dir = tempfile.mkdtemp(prefix="verify_priority_")
    try:
        config = DispatcherConfig(
            task_registry_dir=temp_dir,
            scheduling_policy=SchedulingPolicy.PRIORITY
        )
        dispatcher = DispatcherCore(config)
        
        # Verify initial policy
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.PRIORITY
        print(f"✓ Initial policy: {dispatcher.config.scheduling_policy.value}")
        
        # Disable priority scheduling
        dispatcher.disable_priority_scheduling()
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.FIFO
        assert dispatcher.scheduler.policy == SchedulingPolicy.FIFO
        print(f"✓ Disabled priority scheduling: {dispatcher.config.scheduling_policy.value}")
        
        # Re-enable priority scheduling
        dispatcher.enable_priority_scheduling()
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.PRIORITY
        assert dispatcher.scheduler.policy == SchedulingPolicy.PRIORITY
        print(f"✓ Re-enabled priority scheduling: {dispatcher.config.scheduling_policy.value}")
        
        # Try other policies
        for policy in [SchedulingPolicy.SKILL_BASED, SchedulingPolicy.FAIR_SHARE]:
            dispatcher.set_scheduling_policy(policy)
            assert dispatcher.config.scheduling_policy == policy
            assert dispatcher.scheduler.policy == policy
            print(f"✓ Switched to {policy.value}")
        
        # Verify status includes policy
        status = dispatcher.get_status()
        assert "scheduling_policy" in status
        print(f"✓ Status includes scheduling_policy: {status['scheduling_policy']}")
        
        print("✅ Scheduling policy changes verified")
        return True
        
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("Task 14: Priority Management Implementation Verification")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("Priority Reading (7.1)", verify_priority_reading()))
    except Exception as e:
        print(f"❌ Priority reading failed: {e}")
        results.append(("Priority Reading (7.1)", False))
    
    try:
        results.append(("Priority Sorting (7.2, 7.3)", verify_priority_sorting()))
    except Exception as e:
        print(f"❌ Priority sorting failed: {e}")
        results.append(("Priority Sorting (7.2, 7.3)", False))
    
    try:
        results.append(("Dynamic Priority Changes (7.4)", verify_dynamic_priority_change()))
    except Exception as e:
        print(f"❌ Dynamic priority changes failed: {e}")
        results.append(("Dynamic Priority Changes (7.4)", False))
    
    try:
        results.append(("Scheduling Policy Changes (7.5)", verify_scheduling_policy_changes()))
    except Exception as e:
        print(f"❌ Scheduling policy changes failed: {e}")
        results.append(("Scheduling Policy Changes (7.5)", False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

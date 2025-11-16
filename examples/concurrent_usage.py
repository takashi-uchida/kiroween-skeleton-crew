#!/usr/bin/env python3
"""
Task Registry - Concurrent Usage Example

This example demonstrates concurrent access patterns:
- Multiple processes accessing the same taskset
- Lock acquisition and timeout handling
- Optimistic locking with version numbers
- Safe concurrent task updates
"""

import time
import multiprocessing as mp
from pathlib import Path
from datetime import datetime
from necrocode.task_registry import (
    TaskRegistry,
    TaskState,
    LockTimeoutError
)
from necrocode.task_registry.kiro_sync import TaskDefinition


def worker_process(worker_id: int, spec_name: str, task_ids: list):
    """
    Simulates a worker process that picks up and executes tasks.
    
    Args:
        worker_id: Unique identifier for this worker
        spec_name: Name of the taskset to work on
        task_ids: List of task IDs this worker should attempt to execute
    """
    registry_dir = Path.home() / ".necrocode" / "registry"
    registry = TaskRegistry(registry_dir=registry_dir)
    
    print(f"[Worker {worker_id}] Started")
    
    for task_id in task_ids:
        try:
            # Acquire lock before updating task state
            with registry.lock_manager.acquire_lock(spec_name, timeout=5.0):
                print(f"[Worker {worker_id}] Acquired lock for task {task_id}")
                
                # Get current taskset
                taskset = registry.get_taskset(spec_name)
                
                # Find the task
                task = next((t for t in taskset.tasks if t.id == task_id), None)
                if not task:
                    print(f"[Worker {worker_id}] Task {task_id} not found")
                    continue
                
                # Check if task is ready
                if task.state != TaskState.READY:
                    print(f"[Worker {worker_id}] Task {task_id} is not ready (state: {task.state.value})")
                    continue
                
                # Update task to RUNNING
                registry.update_task_state(
                    spec_name=spec_name,
                    task_id=task_id,
                    new_state=TaskState.RUNNING,
                    metadata={
                        "runner_id": f"worker-{worker_id}",
                        "assigned_slot": f"slot-{worker_id}",
                        "started_at": datetime.now().isoformat()
                    }
                )
                print(f"[Worker {worker_id}] Started task {task_id}")
            
            # Simulate task execution (outside the lock)
            execution_time = 0.5 + (worker_id * 0.1)  # Vary execution time
            print(f"[Worker {worker_id}] Executing task {task_id}...")
            time.sleep(execution_time)
            
            # Acquire lock again to mark task as done
            with registry.lock_manager.acquire_lock(spec_name, timeout=5.0):
                print(f"[Worker {worker_id}] Completing task {task_id}")
                
                # Add artifact
                registry.add_artifact(
                    spec_name=spec_name,
                    task_id=task_id,
                    artifact_type="diff",
                    uri=f"file://artifacts/{spec_name}/{task_id}/changes.diff",
                    metadata={
                        "worker_id": worker_id,
                        "execution_time": execution_time
                    }
                )
                
                # Update task to DONE
                registry.update_task_state(
                    spec_name=spec_name,
                    task_id=task_id,
                    new_state=TaskState.DONE
                )
                print(f"[Worker {worker_id}] Completed task {task_id}")
                
        except LockTimeoutError:
            print(f"[Worker {worker_id}] Failed to acquire lock for task {task_id} (timeout)")
        except Exception as e:
            print(f"[Worker {worker_id}] Error processing task {task_id}: {e}")
    
    print(f"[Worker {worker_id}] Finished")


def main():
    print("=" * 60)
    print("Task Registry - Concurrent Usage Example")
    print("=" * 60)
    print()
    
    # Initialize Task Registry
    registry_dir = Path.home() / ".necrocode" / "registry"
    registry = TaskRegistry(registry_dir=registry_dir)
    print(f"✓ Initialized Task Registry at: {registry_dir}")
    print()
    
    # Create a taskset with multiple independent tasks
    spec_name = "concurrent-example"
    print(f"Creating taskset: {spec_name}")
    print("-" * 60)
    
    tasks = [
        TaskDefinition(
            id="1.1",
            title="Task 1.1 - Independent",
            description="This task has no dependencies",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="1.2",
            title="Task 1.2 - Independent",
            description="This task has no dependencies",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="2.1",
            title="Task 2.1 - Independent",
            description="This task has no dependencies",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="2.2",
            title="Task 2.2 - Independent",
            description="This task has no dependencies",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="3.1",
            title="Task 3.1 - Depends on 1.1 and 1.2",
            description="This task depends on backend tasks",
            dependencies=["1.1", "1.2"],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="3.2",
            title="Task 3.2 - Depends on 2.1 and 2.2",
            description="This task depends on frontend tasks",
            dependencies=["2.1", "2.2"],
            is_optional=False,
            is_completed=False
        )
    ]
    
    taskset = registry.create_taskset(spec_name=spec_name, tasks=tasks)
    print(f"✓ Created taskset with {len(taskset.tasks)} tasks")
    print()
    
    # Show initial state
    print("Initial task states:")
    print("-" * 60)
    for task in taskset.tasks:
        deps = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""
        print(f"  [{task.id}] {task.title} - {task.state.value}{deps}")
    print()
    
    # Launch multiple worker processes
    print("Launching 3 worker processes...")
    print("-" * 60)
    
    # Assign tasks to workers
    worker_tasks = [
        ["1.1", "2.1"],  # Worker 1
        ["1.2", "2.2"],  # Worker 2
        ["1.1", "1.2"]   # Worker 3 (will compete for tasks)
    ]
    
    processes = []
    for worker_id, task_ids in enumerate(worker_tasks, start=1):
        p = mp.Process(
            target=worker_process,
            args=(worker_id, spec_name, task_ids)
        )
        p.start()
        processes.append(p)
    
    # Wait for all workers to complete
    for p in processes:
        p.join()
    
    print()
    print("All workers completed")
    print()
    
    # Show final state
    print("Final task states:")
    print("-" * 60)
    taskset = registry.get_taskset(spec_name)
    for task in taskset.tasks:
        metadata_info = ""
        if task.runner_id:
            metadata_info = f" (executed by {task.runner_id})"
        print(f"  [{task.id}] {task.title} - {task.state.value}{metadata_info}")
    print()
    
    # Check if dependent tasks are now ready
    print("Checking dependent tasks...")
    print("-" * 60)
    ready_tasks = registry.get_ready_tasks(spec_name)
    if ready_tasks:
        print(f"  {len(ready_tasks)} tasks are now ready:")
        for task in ready_tasks:
            print(f"    [{task.id}] {task.title}")
    else:
        print("  No tasks are ready (all dependencies not yet satisfied)")
    print()
    
    # Show event history
    print("Event history for task 1.1:")
    print("-" * 60)
    events = registry.event_store.get_events_by_task(
        spec_name=spec_name,
        task_id="1.1"
    )
    for event in events:
        timestamp = event.timestamp.strftime('%H:%M:%S.%f')[:-3]
        print(f"  {timestamp} - {event.event_type.value}")
        if event.details:
            for key, value in list(event.details.items())[:3]:  # Show first 3 details
                print(f"    {key}: {value}")
    print()
    
    # Demonstrate lock checking
    print("Lock status:")
    print("-" * 60)
    is_locked = registry.lock_manager.is_locked(spec_name)
    print(f"  Taskset locked: {is_locked}")
    print()
    
    # Show statistics
    print("Execution statistics:")
    print("-" * 60)
    states_count = {}
    for task in taskset.tasks:
        state = task.state.value
        states_count[state] = states_count.get(state, 0) + 1
    
    for state, count in sorted(states_count.items()):
        print(f"  {state.upper()}: {count}")
    print()
    
    print("=" * 60)
    print("Concurrent usage example completed successfully!")
    print("=" * 60)
    print()
    print("Key takeaways:")
    print("  • Multiple workers can safely access the same taskset")
    print("  • Locks prevent race conditions during state updates")
    print("  • Workers can execute tasks in parallel")
    print("  • Task dependencies are automatically resolved")
    print("  • Event history tracks all state transitions")


if __name__ == "__main__":
    # Set multiprocessing start method for compatibility
    mp.set_start_method('spawn', force=True)
    main()

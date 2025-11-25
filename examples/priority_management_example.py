"""
Example: Priority Management in Dispatcher

Demonstrates:
1. Reading task priority
2. Priority-based sorting (higher priority first, FIFO for same priority)
3. Dynamic priority changes
4. Enabling/disabling priority-based scheduling

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import logging
import time
from pathlib import Path
from datetime import datetime

from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import SchedulingPolicy
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_tasks(registry: TaskRegistry, spec_name: str):
    """Create test tasks with different priorities."""
    logger.info("Setting up test tasks with different priorities...")
    
    tasks = [
        Task(
            id="1",
            title="Low priority task",
            description="This task has low priority",
            state=TaskState.READY,
            priority=1,
            created_at=datetime.now()
        ),
        Task(
            id="2",
            title="High priority task",
            description="This task has high priority",
            state=TaskState.READY,
            priority=10,
            created_at=datetime.now()
        ),
        Task(
            id="3",
            title="Medium priority task",
            description="This task has medium priority",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now()
        ),
        Task(
            id="4",
            title="Another high priority task",
            description="This task also has high priority (FIFO test)",
            state=TaskState.READY,
            priority=10,
            created_at=datetime.now()
        ),
    ]
    
    # Create taskset
    from necrocode.task_registry.models import Taskset
    taskset = Taskset(
        spec_name=spec_name,
        version=1,
        tasks=tasks
    )
    
    # Save to registry
    registry.create_taskset(taskset)
    logger.info(f"Created {len(tasks)} test tasks")
    
    return tasks


def demonstrate_priority_reading(dispatcher: DispatcherCore):
    """Demonstrate reading task priority (Requirement 7.1)."""
    logger.info("\n=== Demonstrating Priority Reading ===")
    
    # Get tasks from queue
    queued_tasks = dispatcher.task_queue.get_all_tasks()
    
    logger.info(f"Tasks in queue: {len(queued_tasks)}")
    for task in queued_tasks:
        logger.info(f"  Task {task.id}: priority={task.priority}, title='{task.title}'")


def demonstrate_priority_sorting(dispatcher: DispatcherCore):
    """Demonstrate priority-based sorting (Requirements 7.2, 7.3)."""
    logger.info("\n=== Demonstrating Priority-Based Sorting ===")
    
    # Get tasks in priority order
    queued_tasks = dispatcher.task_queue.get_all_tasks()
    
    logger.info("Tasks are sorted by:")
    logger.info("  1. Priority (higher first)")
    logger.info("  2. Creation time (FIFO for same priority)")
    logger.info("\nQueue order:")
    
    for i, task in enumerate(queued_tasks, 1):
        logger.info(
            f"  {i}. Task {task.id} (priority={task.priority}): {task.title}"
        )
    
    # Verify sorting
    logger.info("\nVerifying sort order...")
    for i in range(len(queued_tasks) - 1):
        current = queued_tasks[i]
        next_task = queued_tasks[i + 1]
        
        if current.priority < next_task.priority:
            logger.error(
                f"ERROR: Task {current.id} (priority={current.priority}) "
                f"should come after Task {next_task.id} (priority={next_task.priority})"
            )
        elif current.priority == next_task.priority:
            if current.created_at > next_task.created_at:
                logger.error(
                    f"ERROR: Task {current.id} should come after Task {next_task.id} "
                    f"(same priority, but created later)"
                )
            else:
                logger.info(
                    f"✓ Tasks {current.id} and {next_task.id} have same priority, "
                    f"correctly ordered by creation time (FIFO)"
                )
        else:
            logger.info(
                f"✓ Task {current.id} (priority={current.priority}) "
                f"correctly comes before Task {next_task.id} (priority={next_task.priority})"
            )


def demonstrate_dynamic_priority_change(dispatcher: DispatcherCore, spec_name: str):
    """Demonstrate dynamic priority changes (Requirement 7.4)."""
    logger.info("\n=== Demonstrating Dynamic Priority Changes ===")
    
    # Show current queue
    logger.info("Current queue order:")
    queued_tasks = dispatcher.task_queue.get_all_tasks()
    for i, task in enumerate(queued_tasks, 1):
        logger.info(f"  {i}. Task {task.id} (priority={task.priority})")
    
    # Change priority of task 1 from 1 to 15
    logger.info("\nChanging Task 1 priority from 1 to 15...")
    success = dispatcher.update_task_priority(spec_name, "1", 15)
    
    if success:
        logger.info("✓ Priority updated successfully")
        
        # Show new queue order
        logger.info("\nNew queue order:")
        queued_tasks = dispatcher.task_queue.get_all_tasks()
        for i, task in enumerate(queued_tasks, 1):
            logger.info(f"  {i}. Task {task.id} (priority={task.priority})")
        
        # Verify task 1 is now at the front
        if queued_tasks[0].id == "1":
            logger.info("✓ Task 1 is now at the front of the queue")
        else:
            logger.error("ERROR: Task 1 should be at the front of the queue")
    else:
        logger.error("✗ Failed to update priority")


def demonstrate_scheduling_policy_changes(dispatcher: DispatcherCore):
    """Demonstrate enabling/disabling priority scheduling (Requirement 7.5)."""
    logger.info("\n=== Demonstrating Scheduling Policy Changes ===")
    
    # Show current policy
    status = dispatcher.get_status()
    logger.info(f"Current scheduling policy: {status['scheduling_policy']}")
    
    # Disable priority scheduling (switch to FIFO)
    logger.info("\nDisabling priority-based scheduling...")
    dispatcher.disable_priority_scheduling()
    
    status = dispatcher.get_status()
    logger.info(f"New scheduling policy: {status['scheduling_policy']}")
    
    if status['scheduling_policy'] == SchedulingPolicy.FIFO.value:
        logger.info("✓ Priority scheduling disabled (using FIFO)")
    else:
        logger.error("ERROR: Policy should be FIFO")
    
    # Re-enable priority scheduling
    logger.info("\nRe-enabling priority-based scheduling...")
    dispatcher.enable_priority_scheduling()
    
    status = dispatcher.get_status()
    logger.info(f"New scheduling policy: {status['scheduling_policy']}")
    
    if status['scheduling_policy'] == SchedulingPolicy.PRIORITY.value:
        logger.info("✓ Priority scheduling enabled")
    else:
        logger.error("ERROR: Policy should be PRIORITY")
    
    # Try other policies
    logger.info("\nTrying other scheduling policies...")
    
    for policy in [SchedulingPolicy.SKILL_BASED, SchedulingPolicy.FAIR_SHARE]:
        logger.info(f"\nSwitching to {policy.value}...")
        dispatcher.set_scheduling_policy(policy)
        
        status = dispatcher.get_status()
        if status['scheduling_policy'] == policy.value:
            logger.info(f"✓ Successfully switched to {policy.value}")
        else:
            logger.error(f"ERROR: Policy should be {policy.value}")


def main():
    """Main example function."""
    logger.info("=== Priority Management Example ===\n")
    
    # Set up test environment
    spec_name = "priority-test"
    registry_dir = Path("tmp_priority_test")
    
    # Clean up any existing test data
    import shutil
    if registry_dir.exists():
        shutil.rmtree(registry_dir)
    
    try:
        # Create Task Registry
        registry = TaskRegistry(registry_dir=str(registry_dir))
        
        # Set up test tasks
        tasks = setup_test_tasks(registry, spec_name)
        
        # Create Dispatcher with priority-based scheduling
        config = DispatcherConfig(
            task_registry_dir=str(registry_dir),
            scheduling_policy=SchedulingPolicy.PRIORITY,
            poll_interval=1,
            max_global_concurrency=5
        )
        
        dispatcher = DispatcherCore(config)
        
        # Manually add tasks to queue for demonstration
        logger.info("\nAdding tasks to queue...")
        for task in tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Run demonstrations
        demonstrate_priority_reading(dispatcher)
        demonstrate_priority_sorting(dispatcher)
        demonstrate_dynamic_priority_change(dispatcher, spec_name)
        demonstrate_scheduling_policy_changes(dispatcher)
        
        logger.info("\n=== Example Complete ===")
        
    finally:
        # Clean up
        if registry_dir.exists():
            shutil.rmtree(registry_dir)
            logger.info("\nCleaned up test data")


if __name__ == "__main__":
    main()

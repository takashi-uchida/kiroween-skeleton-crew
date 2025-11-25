"""
Example: Deadlock Detection Integration with DispatcherCore.

Demonstrates how deadlock detection works within the full Dispatcher system.
"""

import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from necrocode.dispatcher import DispatcherCore, DispatcherConfig
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, Taskset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_test_tasks_with_deadlock():
    """Create test tasks with circular dependencies."""
    tasks = [
        Task(
            id="1",
            title="Setup Database",
            description="Initialize database schema",
            state=TaskState.READY,
            dependencies=["3"],  # Depends on task 3
            metadata={"spec_name": "test-project"}
        ),
        Task(
            id="2",
            title="Create API",
            description="Implement REST API",
            state=TaskState.READY,
            dependencies=["1"],  # Depends on task 1
            metadata={"spec_name": "test-project"}
        ),
        Task(
            id="3",
            title="Add Authentication",
            description="Implement JWT auth",
            state=TaskState.READY,
            dependencies=["2"],  # Depends on task 2 (creates cycle!)
            metadata={"spec_name": "test-project"}
        ),
        Task(
            id="4",
            title="Write Tests",
            description="Add unit tests",
            state=TaskState.READY,
            dependencies=[],  # No dependencies - can proceed
            metadata={"spec_name": "test-project"}
        ),
    ]
    return tasks


def example_automatic_detection():
    """Example: Automatic deadlock detection in DispatcherCore."""
    print("\n" + "="*70)
    print("Example 1: Automatic Deadlock Detection")
    print("="*70)
    
    # Create tasks with circular dependencies
    print("\n1. Creating tasks with circular dependencies...")
    tasks = create_test_tasks_with_deadlock()
    print(f"   Created {len(tasks)} tasks")
    
    # Show dependencies
    print("\n2. Task dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"   {task.id}: {task.title} (depends on: {deps})")
    
    # Initialize DispatcherCore
    print("\n3. Initializing DispatcherCore...")
    config = DispatcherConfig()
    dispatcher = DispatcherCore(config)
    
    # Use deadlock detector directly
    print("\n4. Running deadlock detection...")
    cycles = dispatcher.deadlock_detector.detect_deadlock(tasks)
    
    if cycles:
        print("   ❌ Deadlock detected!")
        
        print(f"\n5. Deadlock details:")
        print(f"   Detected cycles: {len(cycles)}")
        
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " -> ".join(cycle)
            print(f"   Cycle {i}: {cycle_str}")
        
        # Get blocked tasks
        blocked_tasks = dispatcher.deadlock_detector.get_blocked_tasks(tasks)
        print(f"\n6. Blocked tasks ({len(blocked_tasks)}):")
        for task in blocked_tasks:
            print(f"   - {task.id}: {task.title}")
        
        # Get tasks that can proceed
        unblocked_tasks = [t for t in tasks if t not in blocked_tasks]
        print(f"\n7. Tasks that can proceed ({len(unblocked_tasks)}):")
        for task in unblocked_tasks:
            print(f"   - {task.id}: {task.title}")
        
        # Get resolution suggestions
        suggestions = dispatcher.deadlock_detector.suggest_resolution(cycles)
        print(f"\n8. Resolution suggestions:")
        for suggestion in suggestions:
            print(f"   - {suggestion}")
    else:
        print("   ✅ No deadlock detected")


def example_exception_handling():
    """Example: Exception-based deadlock handling."""
    print("\n" + "="*70)
    print("Example 2: Exception-Based Deadlock Handling")
    print("="*70)
    
    # Create tasks with circular dependencies
    print("\n1. Creating tasks with circular dependencies...")
    tasks = create_test_tasks_with_deadlock()
    
    # Initialize DispatcherCore
    print("\n2. Initializing DispatcherCore...")
    config = DispatcherConfig()
    dispatcher = DispatcherCore(config)
    
    # Try to detect deadlock with exception
    print("\n3. Running deadlock detection with raise_on_deadlock=True...")
    
    try:
        dispatcher.deadlock_detector.check_for_deadlock(tasks, raise_on_deadlock=True)
        print("   ✅ No deadlock detected")
    except Exception as e:
        print(f"   ❌ DeadlockDetectedError raised!")
        print(f"\n4. Exception details:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)[:200]}...")
        
        print(f"\n5. Handling deadlock:")
        print("   - Logging error to monitoring system")
        print("   - Notifying system administrators")
        print("   - Pausing task assignment")
        print("   - Waiting for manual intervention")


def example_no_deadlock():
    """Example: Valid dependencies with no deadlock."""
    print("\n" + "="*70)
    print("Example 3: Valid Dependencies (No Deadlock)")
    print("="*70)
    
    # Create tasks with valid dependencies
    print("\n1. Creating tasks with valid dependencies...")
    tasks = [
        Task(
            id="1",
            title="Setup Database",
            description="Initialize database schema",
            state=TaskState.READY,
            dependencies=[],
            metadata={"spec_name": "valid-project"}
        ),
        Task(
            id="2",
            title="Create API",
            description="Implement REST API",
            state=TaskState.READY,
            dependencies=["1"],
            metadata={"spec_name": "valid-project"}
        ),
        Task(
            id="3",
            title="Add Authentication",
            description="Implement JWT auth",
            state=TaskState.READY,
            dependencies=["2"],
            metadata={"spec_name": "valid-project"}
        ),
        Task(
            id="4",
            title="Write Tests",
            description="Add unit tests",
            state=TaskState.READY,
            dependencies=["3"],
            metadata={"spec_name": "valid-project"}
        ),
    ]
    
    # Show dependencies
    print("\n2. Task dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"   {task.id}: {task.title} (depends on: {deps})")
    
    # Initialize DispatcherCore
    print("\n3. Initializing DispatcherCore...")
    config = DispatcherConfig()
    dispatcher = DispatcherCore(config)
    
    # Check for deadlock
    print("\n4. Running deadlock detection...")
    cycles = dispatcher.deadlock_detector.detect_deadlock(tasks)
    
    if cycles:
        print("   ❌ Unexpected deadlock detected!")
    else:
        print("   ✅ No deadlock detected - dependencies are valid")
        
        print(f"\n5. Deadlock status:")
        print(f"   Detected cycles: {len(cycles)}")
        print("   All tasks can proceed in dependency order")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("Dispatcher Deadlock Detection Integration Examples")
    print("="*70)
    
    example_automatic_detection()
    example_exception_handling()
    example_no_deadlock()
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

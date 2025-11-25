"""
Example usage of DeadlockDetector.

Demonstrates how to detect circular dependencies in task graphs.
"""

import logging
from datetime import datetime

from necrocode.dispatcher.deadlock_detector import DeadlockDetector
from necrocode.dispatcher.exceptions import DeadlockDetectedError
from necrocode.task_registry.models import Task, TaskState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_no_deadlock():
    """Example: Linear dependencies with no deadlock."""
    print("\n" + "="*60)
    print("Example 1: Linear Dependencies (No Deadlock)")
    print("="*60)
    
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Setup database",
            description="Initialize database schema",
            state=TaskState.READY,
            dependencies=[]
        ),
        Task(
            id="2",
            title="Create API endpoints",
            description="Implement REST API",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        Task(
            id="3",
            title="Add authentication",
            description="Implement JWT auth",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="4",
            title="Write tests",
            description="Add unit tests",
            state=TaskState.READY,
            dependencies=["3"]
        ),
    ]
    
    print("\nTask dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}: {task.title} (depends on: {deps})")
    
    cycles = detector.detect_deadlock(tasks)
    
    if cycles:
        print(f"\n❌ Deadlock detected! {len(cycles)} cycle(s) found:")
        for i, cycle in enumerate(cycles, 1):
            print(f"  Cycle {i}: {' -> '.join(cycle)}")
    else:
        print("\n✅ No deadlock detected - dependencies are valid")


def example_simple_deadlock():
    """Example: Simple circular dependency (A -> B -> A)."""
    print("\n" + "="*60)
    print("Example 2: Simple Circular Dependency")
    print("="*60)
    
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Frontend",
            description="Build frontend",
            state=TaskState.READY,
            dependencies=["2"]  # Frontend depends on Backend
        ),
        Task(
            id="2",
            title="Backend",
            description="Build backend",
            state=TaskState.READY,
            dependencies=["1"]  # Backend depends on Frontend (circular!)
        ),
    ]
    
    print("\nTask dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}: {task.title} (depends on: {deps})")
    
    cycles = detector.detect_deadlock(tasks)
    
    if cycles:
        print(f"\n❌ Deadlock detected! {len(cycles)} cycle(s) found:")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " -> ".join(cycle)
            print(f"  Cycle {i}: {cycle_str}")
        
        # Get resolution suggestions
        suggestions = detector.suggest_resolution(cycles)
        print("\n💡 Suggested resolutions:")
        for suggestion in suggestions:
            print(f"  {suggestion}")
        
        # Get blocked tasks
        blocked_tasks = detector.get_blocked_tasks(tasks)
        print(f"\n🚫 {len(blocked_tasks)} task(s) blocked by circular dependencies:")
        for task in blocked_tasks:
            print(f"  - {task.id}: {task.title}")
    else:
        print("\n✅ No deadlock detected")


def example_complex_deadlock():
    """Example: Complex circular dependency (A -> B -> C -> A)."""
    print("\n" + "="*60)
    print("Example 3: Complex Circular Dependency")
    print("="*60)
    
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Database schema",
            description="Design database",
            state=TaskState.READY,
            dependencies=["3"]  # Depends on API design
        ),
        Task(
            id="2",
            title="API implementation",
            description="Implement API",
            state=TaskState.READY,
            dependencies=["1"]  # Depends on Database
        ),
        Task(
            id="3",
            title="API design",
            description="Design API",
            state=TaskState.READY,
            dependencies=["2"]  # Depends on API implementation (circular!)
        ),
    ]
    
    print("\nTask dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}: {task.title} (depends on: {deps})")
    
    cycles = detector.detect_deadlock(tasks)
    
    if cycles:
        print(f"\n❌ Deadlock detected! {len(cycles)} cycle(s) found:")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " -> ".join(cycle)
            print(f"  Cycle {i}: {cycle_str}")
        
        suggestions = detector.suggest_resolution(cycles)
        print("\n💡 Suggested resolutions:")
        for suggestion in suggestions:
            print(f"  {suggestion}")


def example_raise_on_deadlock():
    """Example: Raise exception on deadlock detection."""
    print("\n" + "="*60)
    print("Example 4: Raise Exception on Deadlock")
    print("="*60)
    
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task A",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task B",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
    ]
    
    print("\nTask dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}: {task.title} (depends on: {deps})")
    
    print("\nChecking for deadlock with raise_on_deadlock=True...")
    
    try:
        detector.check_for_deadlock(tasks, raise_on_deadlock=True)
        print("✅ No deadlock detected")
    except DeadlockDetectedError as e:
        print(f"\n❌ DeadlockDetectedError raised:")
        print(f"  {e}")


def example_mixed_graph():
    """Example: Mixed graph with valid and circular dependencies."""
    print("\n" + "="*60)
    print("Example 5: Mixed Graph (Valid + Circular)")
    print("="*60)
    
    detector = DeadlockDetector()
    
    tasks = [
        # Valid linear chain
        Task(
            id="1",
            title="Setup",
            description="Initial setup",
            state=TaskState.READY,
            dependencies=[]
        ),
        Task(
            id="2",
            title="Config",
            description="Configuration",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        # Circular dependency
        Task(
            id="3",
            title="Service A",
            description="Service A",
            state=TaskState.READY,
            dependencies=["4"]
        ),
        Task(
            id="4",
            title="Service B",
            description="Service B",
            state=TaskState.READY,
            dependencies=["3"]
        ),
        # Another valid task
        Task(
            id="5",
            title="Tests",
            description="Write tests",
            state=TaskState.READY,
            dependencies=["2"]
        ),
    ]
    
    print("\nTask dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}: {task.title} (depends on: {deps})")
    
    cycles = detector.detect_deadlock(tasks)
    
    if cycles:
        print(f"\n❌ Deadlock detected! {len(cycles)} cycle(s) found:")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " -> ".join(cycle)
            print(f"  Cycle {i}: {cycle_str}")
        
        blocked_tasks = detector.get_blocked_tasks(tasks)
        print(f"\n🚫 {len(blocked_tasks)} task(s) blocked:")
        for task in blocked_tasks:
            print(f"  - {task.id}: {task.title}")
        
        print(f"\n✅ {len(tasks) - len(blocked_tasks)} task(s) can proceed:")
        for task in tasks:
            if task not in blocked_tasks:
                print(f"  - {task.id}: {task.title}")


def example_completed_tasks_ignored():
    """Example: Completed tasks are ignored in deadlock detection."""
    print("\n" + "="*60)
    print("Example 6: Completed Tasks Ignored")
    print("="*60)
    
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task A",
            description="First task",
            state=TaskState.DONE,  # Completed
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task B",
            description="Second task",
            state=TaskState.DONE,  # Completed
            dependencies=["1"]
        ),
        Task(
            id="3",
            title="Task C",
            description="Third task",
            state=TaskState.READY,
            dependencies=[]
        ),
    ]
    
    print("\nTask dependencies:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        state = task.state.value
        print(f"  {task.id}: {task.title} (depends on: {deps}, state: {state})")
    
    cycles = detector.detect_deadlock(tasks)
    
    if cycles:
        print(f"\n❌ Deadlock detected! {len(cycles)} cycle(s) found")
    else:
        print("\n✅ No deadlock detected - completed tasks are ignored")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("DeadlockDetector Examples")
    print("="*60)
    
    example_no_deadlock()
    example_simple_deadlock()
    example_complex_deadlock()
    example_raise_on_deadlock()
    example_mixed_graph()
    example_completed_tasks_ignored()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

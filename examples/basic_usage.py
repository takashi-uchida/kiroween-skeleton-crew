#!/usr/bin/env python3
"""
Task Registry - Basic Usage Example

This example demonstrates the basic usage of Task Registry:
- Creating a taskset
- Updating task states
- Getting ready tasks
- Adding artifacts
"""

from pathlib import Path
from datetime import datetime
from necrocode.task_registry import (
    TaskRegistry,
    TaskState,
    ArtifactType,
    EventType
)
from necrocode.task_registry.kiro_sync import TaskDefinition


def main():
    print("=" * 60)
    print("Task Registry - Basic Usage Example")
    print("=" * 60)
    print()
    
    # Initialize Task Registry
    registry_dir = Path.home() / ".necrocode" / "registry"
    registry = TaskRegistry(registry_dir=registry_dir)
    print(f"✓ Initialized Task Registry at: {registry_dir}")
    print()
    
    # Create a taskset for a chat application
    spec_name = "chat-app-example"
    print(f"Creating taskset: {spec_name}")
    print("-" * 60)
    
    tasks = [
        TaskDefinition(
            id="1.1",
            title="Setup database schema",
            description="Create User and Message models with MongoDB",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="1.2",
            title="Implement JWT authentication",
            description="Add login/register endpoints with JWT token generation",
            dependencies=["1.1"],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="2.1",
            title="Create login UI",
            description="Build React login form component",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="2.2",
            title="Create chat interface",
            description="Build real-time chat UI with WebSocket",
            dependencies=["1.2", "2.1"],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="3.1",
            title="Write unit tests",
            description="Add unit tests for authentication",
            dependencies=["1.2"],
            is_optional=True,
            is_completed=False
        )
    ]
    
    taskset = registry.create_taskset(spec_name=spec_name, tasks=tasks)
    print(f"✓ Created taskset: {taskset.spec_name} v{taskset.version}")
    print(f"  Total tasks: {len(taskset.tasks)}")
    print()
    
    # Get ready tasks
    print("Getting ready tasks...")
    print("-" * 60)
    ready_tasks = registry.get_ready_tasks(spec_name=spec_name)
    for task in ready_tasks:
        print(f"  [{task.id}] {task.title}")
        print(f"      Skill: {task.required_skill}, Priority: {task.priority}")
    print()
    
    # Update task state to RUNNING
    print("Starting task 1.1...")
    print("-" * 60)
    registry.update_task_state(
        spec_name=spec_name,
        task_id="1.1",
        new_state=TaskState.RUNNING,
        metadata={
            "assigned_slot": "workspace-chat-app-slot1",
            "reserved_branch": "feature/task-chat-app-1.1",
            "runner_id": "runner-backend-1"
        }
    )
    print("✓ Task 1.1 is now RUNNING")
    print()
    
    # Simulate task completion
    print("Completing task 1.1...")
    print("-" * 60)
    
    # Add artifact
    registry.add_artifact(
        spec_name=spec_name,
        task_id="1.1",
        artifact_type=ArtifactType.DIFF,
        uri="file://~/.necrocode/artifacts/chat-app/1.1/changes.diff",
        metadata={
            "size_bytes": 2048,
            "files_changed": ["models/User.js", "models/Message.js"]
        }
    )
    print("✓ Added artifact: changes.diff")
    
    # Update state to DONE
    registry.update_task_state(
        spec_name=spec_name,
        task_id="1.1",
        new_state=TaskState.DONE
    )
    print("✓ Task 1.1 is now DONE")
    print()
    
    # Check if dependent tasks are now ready
    print("Checking dependent tasks...")
    print("-" * 60)
    ready_tasks = registry.get_ready_tasks(spec_name=spec_name)
    for task in ready_tasks:
        print(f"  [{task.id}] {task.title}")
        if "1.1" in task.dependencies:
            print(f"      → Unblocked by task 1.1")
    print()
    
    # Get task events
    print("Task 1.1 event history:")
    print("-" * 60)
    events = registry.event_store.get_events_by_task(
        spec_name=spec_name,
        task_id="1.1"
    )
    for event in events:
        print(f"  {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {event.event_type.value}")
        if event.details:
            for key, value in event.details.items():
                print(f"    {key}: {value}")
    print()
    
    # Query tasks by state
    print("Completed tasks:")
    print("-" * 60)
    done_tasks = registry.query_engine.filter_by_state(
        spec_name=spec_name,
        state=TaskState.DONE
    )
    for task in done_tasks:
        print(f"  [{task.id}] {task.title}")
    print()
    
    # Get taskset summary
    print("Taskset summary:")
    print("-" * 60)
    taskset = registry.get_taskset(spec_name)
    states_count = {}
    for task in taskset.tasks:
        state = task.state.value
        states_count[state] = states_count.get(state, 0) + 1
    
    for state, count in states_count.items():
        print(f"  {state.upper()}: {count}")
    print()
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

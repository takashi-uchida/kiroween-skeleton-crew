#!/usr/bin/env python3
"""
Task Registry - Kiro Sync Example

This example demonstrates the Kiro synchronization features:
- Syncing from tasks.md to Task Registry
- Syncing from Task Registry to tasks.md
- Bidirectional synchronization
- Handling task updates
"""

from pathlib import Path
from necrocode.task_registry import (
    TaskRegistry,
    TaskState
)
from necrocode.task_registry.kiro_sync import TaskDefinition


def create_sample_tasks_md(tasks_md_path: Path):
    """Create a sample tasks.md file for demonstration"""
    content = """# Implementation Plan

- [ ] 1. Setup project structure
  - Initialize Node.js project with Express
  - Setup MongoDB connection
  - _Requirements: 1.1_

- [ ] 1.1 Create database models
  - [ ] 1.1.1 User model with authentication fields
    - email, password, username
    - _Requirements: 1.1, 1.2_
  
  - [ ] 1.1.2 Message model with relationships
    - sender, receiver, content, timestamp
    - _Requirements: 1.1, 2.1_

- [ ] 2. Implement authentication
  - [ ] 2.1 JWT token generation
    - Create login endpoint
    - Create register endpoint
    - _Requirements: 1.2, 2.1_
  
  - [ ] 2.2 Authentication middleware
    - Validate JWT tokens
    - Protect routes
    - _Requirements: 1.2, 2.2_

- [ ] 3. Build frontend
  - [ ] 3.1 Login form component
    - React form with validation
    - _Requirements: 3.1_
  
  - [ ] 3.2 Chat interface
    - Real-time message display
    - WebSocket integration
    - _Requirements: 3.2, 3.3_

- [ ]* 4. Testing
  - [ ]* 4.1 Unit tests for authentication
    - Test login/register endpoints
    - _Requirements: すべて_
  
  - [ ]* 4.2 Integration tests
    - Test end-to-end flows
    - _Requirements: すべて_
"""
    tasks_md_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_md_path.write_text(content)


def main():
    print("=" * 60)
    print("Task Registry - Kiro Sync Example")
    print("=" * 60)
    print()
    
    # Initialize Task Registry
    registry_dir = Path.home() / ".necrocode" / "registry"
    registry = TaskRegistry(registry_dir=registry_dir)
    print(f"✓ Initialized Task Registry at: {registry_dir}")
    print()
    
    # Create a taskset first
    spec_name = "kiro-sync-example"
    print(f"Creating initial taskset: {spec_name}")
    print("-" * 60)
    
    # Create initial tasks
    tasks = [
        TaskDefinition(
            id="1",
            title="Setup project structure",
            description="Initialize Node.js project with Express",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="1.1",
            title="Create database models",
            description="User and Message models",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="2",
            title="Implement authentication",
            description="JWT token generation and validation",
            dependencies=["1"],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="3",
            title="Build frontend",
            description="React components",
            dependencies=[],
            is_optional=False,
            is_completed=False
        ),
        TaskDefinition(
            id="4",
            title="Testing",
            description="Unit and integration tests",
            dependencies=["2", "3"],
            is_optional=True,
            is_completed=False
        )
    ]
    
    taskset = registry.create_taskset(spec_name=spec_name, tasks=tasks)
    print(f"✓ Created taskset with {len(taskset.tasks)} tasks")
    print()
    
    # Create sample tasks.md
    kiro_spec_dir = Path(".kiro/specs") / spec_name
    tasks_md_path = kiro_spec_dir / "tasks.md"
    
    print(f"Creating sample tasks.md at: {tasks_md_path}")
    print("-" * 60)
    create_sample_tasks_md(tasks_md_path)
    print("✓ Sample tasks.md created")
    print()
    
    # Display initial tasks
    print("Initial tasks in Task Registry:")
    print("-" * 60)
    taskset = registry.get_taskset(spec_name)
    for task in taskset.tasks:
        optional_mark = "*" if task.is_optional else " "
        deps = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""
        print(f"  [{optional_mark}] {task.id} - {task.title}{deps}")
    print()
    
    # Update some task states in Task Registry
    print("Updating task states in Task Registry...")
    print("-" * 60)
    
    # Start and complete task 1
    registry.update_task_state(
        spec_name=spec_name,
        task_id="1",
        new_state=TaskState.RUNNING
    )
    registry.update_task_state(
        spec_name=spec_name,
        task_id="1",
        new_state=TaskState.DONE
    )
    print("✓ Task 1 marked as DONE")
    
    # Now task 2 should be unblocked, start it
    registry.update_task_state(
        spec_name=spec_name,
        task_id="2",
        new_state=TaskState.RUNNING,
        metadata={
            "runner_id": "runner-backend-1",
            "assigned_slot": "workspace-1"
        }
    )
    print("✓ Task 2 marked as RUNNING")
    print()
    
    # Sync back to Kiro
    print("Syncing from Task Registry to tasks.md...")
    print("-" * 60)
    result = registry.sync_with_kiro(spec_name=spec_name)
    print(f"✓ Sync completed:")
    print(f"  Tasks updated: {len(result.tasks_updated)}")
    print()
    
    # Show updated tasks.md content
    print("Updated tasks.md (first 30 lines):")
    print("-" * 60)
    updated_content = tasks_md_path.read_text()
    lines = updated_content.split('\n')[:30]
    for line in lines:
        if '[x]' in line:
            print(f"  {line}  ← COMPLETED")
        elif '[-]' in line:
            print(f"  {line}  ← IN PROGRESS")
        else:
            print(f"  {line}")
    print()
    
    # Demonstrate bidirectional sync
    print("Testing bidirectional sync...")
    print("-" * 60)
    
    # Manually update tasks.md (simulate user editing)
    print("Simulating manual edit in tasks.md...")
    updated_content = updated_content.replace(
        "- [ ] 3. Build frontend",
        "- [x] 3. Build frontend"
    )
    tasks_md_path.write_text(updated_content)
    print("✓ Manually marked task 3 as complete in tasks.md")
    print()
    
    # Sync bidirectionally
    print("Running bidirectional sync...")
    result = registry.sync_with_kiro(spec_name=spec_name)
    print(f"✓ Bidirectional sync completed:")
    print(f"  Tasks added: {len(result.tasks_added)}")
    print(f"  Tasks updated: {len(result.tasks_updated)}")
    print()
    
    # Verify the sync
    print("Verifying sync results:")
    print("-" * 60)
    taskset = registry.get_taskset(spec_name)
    
    # Check task 3
    task_3 = next((t for t in taskset.tasks if t.id == "3"), None)
    if task_3:
        print(f"  Task 3 state: {task_3.state.value}")
        if task_3.state == TaskState.DONE:
            print("  ✓ Task 3 correctly synced from tasks.md")
    
    # Check task 1
    task_1 = next((t for t in taskset.tasks if t.id == "1"), None)
    if task_1:
        print(f"  Task 1 state: {task_1.state.value}")
        if task_1.state == TaskState.DONE:
            print("  ✓ Task 1 state preserved")
    print()
    
    # Show dependency resolution
    print("Dependency resolution:")
    print("-" * 60)
    ready_tasks = registry.get_ready_tasks(spec_name)
    print(f"  Ready tasks: {len(ready_tasks)}")
    for task in ready_tasks[:5]:  # Show first 5
        print(f"    [{task.id}] {task.title}")
    print()
    
    # Show optional tasks
    print("Optional tasks (marked with *):")
    print("-" * 60)
    optional_tasks = [t for t in taskset.tasks if t.is_optional]
    for task in optional_tasks:
        print(f"  [{task.id}] {task.title}")
    print()
    
    print("=" * 60)
    print("Kiro sync example completed successfully!")
    print("=" * 60)
    print()
    print("Key takeaways:")
    print("  • tasks.md checkboxes sync with Task Registry states")
    print("  • [ ] = READY, [-] = RUNNING, [x] = DONE")
    print("  • Dependencies are automatically parsed from _Requirements:_")
    print("  • Optional tasks (marked with *) are identified")
    print("  • Bidirectional sync keeps both sources in sync")


if __name__ == "__main__":
    main()

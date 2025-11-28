"""
Example demonstrating PR event handling functionality.

This example shows how to use the handle_pr_merged method to process
PR merge events, including:
- Recording PR merged events in Task Registry
- Deleting source branches
- Returning workspace slots to Repo Pool Manager
- Unblocking dependent tasks
"""

from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState


def example_pr_merged_event():
    """
    Example: Handle PR merged event with all post-merge operations.
    """
    print("=" * 80)
    print("PR Event Handling Example")
    print("=" * 80)
    
    # Create a temporary task registry
    temp_dir = tempfile.mkdtemp()
    registry = TaskRegistry(registry_dir=Path(temp_dir))
    
    try:
        # Create a test spec with tasks
        spec_name = "chat-app"
        tasks = [
            Task(
                id="1",
                title="Implement authentication",
                description="Add JWT authentication",
                state=TaskState.IN_PROGRESS,
                dependencies=[]
            ),
            Task(
                id="2",
                title="Create chat interface",
                description="Build real-time chat UI",
                state=TaskState.BLOCKED,
                dependencies=["1"]  # Depends on task 1
            ),
            Task(
                id="3",
                title="Add message persistence",
                description="Store messages in database",
                state=TaskState.BLOCKED,
                dependencies=["1"]  # Also depends on task 1
            )
        ]
        
        registry.create_taskset(spec_name, "Chat Application", tasks)
        print(f"\n✓ Created taskset '{spec_name}' with {len(tasks)} tasks")
        
        # Display initial task states
        print("\nInitial Task States:")
        for task in tasks:
            print(f"  - Task {task.id}: {task.state.value}")
        
        # Simulate a merged PR for task 1
        pr = PullRequest(
            pr_id="101",
            pr_number=101,
            title="Task 1: Implement authentication",
            description="Added JWT authentication with login/register endpoints",
            source_branch="feature/task-1-authentication",
            target_branch="main",
            url="https://github.com/myorg/chat-app/pull/101",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now(),
            merged_at=datetime.now(),
            merge_commit_sha="abc123def456",
            task_id="1",
            spec_id=spec_name,
            metadata={
                "workspace_id": "workspace-chat-app",
                "slot_id": "slot-1"
            }
        )
        
        print(f"\n✓ Created PR #{pr.pr_number}: {pr.title}")
        print(f"  - Source: {pr.source_branch}")
        print(f"  - Target: {pr.target_branch}")
        print(f"  - State: {pr.state.value}")
        print(f"  - Merge SHA: {pr.merge_commit_sha}")
        
        # Note: In a real scenario, you would use PRService.handle_pr_merged()
        # For this example, we'll manually demonstrate the operations
        
        print("\n" + "=" * 80)
        print("Processing PR Merged Event")
        print("=" * 80)
        
        # 1. Record PR merged event
        print("\n1. Recording PR merged event in Task Registry...")
        from necrocode.task_registry.models import TaskEvent, EventType
        
        event = TaskEvent(
            event_type=EventType.TASK_COMPLETED,
            spec_name=spec_name,
            task_id=pr.task_id,
            timestamp=datetime.now(),
            details={
                "event": "pr_merged",
                "pr_url": pr.url,
                "pr_number": pr.pr_number,
                "pr_id": pr.pr_id,
                "source_branch": pr.source_branch,
                "target_branch": pr.target_branch,
                "merged_at": pr.merged_at.isoformat(),
                "merge_commit_sha": pr.merge_commit_sha,
            }
        )
        
        registry.event_store.record_event(event)
        print(f"   ✓ Recorded PR merged event for task {pr.task_id}")
        
        # 2. Branch deletion (simulated)
        print("\n2. Deleting source branch...")
        print(f"   ✓ Would delete branch: {pr.source_branch}")
        print("   (In production: git_host_client.delete_branch(branch_name))")
        
        # 3. Slot return (simulated)
        print("\n3. Returning workspace slot to Repo Pool Manager...")
        workspace_id = pr.metadata.get("workspace_id")
        slot_id = pr.metadata.get("slot_id")
        print(f"   ✓ Would return slot: {slot_id} from workspace: {workspace_id}")
        print("   (In production: repo_pool_client.release_slot(workspace_id, slot_id))")
        
        # Record slot return event
        slot_event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name=spec_name,
            task_id=pr.task_id,
            timestamp=datetime.now(),
            details={
                "event": "slot_returned",
                "workspace_id": workspace_id,
                "slot_id": slot_id,
                "pr_number": pr.pr_number,
            }
        )
        registry.event_store.record_event(slot_event)
        print(f"   ✓ Recorded slot return event")
        
        # 4. Unblock dependent tasks
        print("\n4. Unblocking dependent tasks...")
        
        # Update task 1 to COMPLETED
        registry.update_task_state(spec_name, "1", TaskState.COMPLETED)
        print(f"   ✓ Updated task 1 state to COMPLETED")
        
        # Get updated taskset
        taskset = registry.get_taskset(spec_name)
        
        # Find and unblock dependent tasks
        unblocked_count = 0
        for task in taskset.tasks:
            if "1" in task.dependencies and task.state == TaskState.BLOCKED:
                # Check if all dependencies are satisfied
                all_deps_satisfied = True
                for dep_id in task.dependencies:
                    dep_task = next((t for t in taskset.tasks if t.id == dep_id), None)
                    if dep_task and dep_task.state != TaskState.COMPLETED:
                        all_deps_satisfied = False
                        break
                
                if all_deps_satisfied:
                    registry.update_task_state(spec_name, task.id, TaskState.PENDING)
                    unblocked_count += 1
                    print(f"   ✓ Unblocked task {task.id}: {task.title}")
        
        print(f"\n   Total tasks unblocked: {unblocked_count}")
        
        # Display final task states
        print("\n" + "=" * 80)
        print("Final Task States")
        print("=" * 80)
        
        taskset = registry.get_taskset(spec_name)
        for task in taskset.tasks:
            status_icon = "✓" if task.state == TaskState.COMPLETED else "→" if task.state == TaskState.PENDING else "⏸"
            print(f"  {status_icon} Task {task.id}: {task.state.value} - {task.title}")
        
        # Display recorded events
        print("\n" + "=" * 80)
        print("Recorded Events")
        print("=" * 80)
        
        all_events = registry.event_store.get_events(spec_name, "1")
        print(f"\nEvents for task 1 ({len(all_events)} total):")
        for event in all_events:
            event_name = event.details.get("event", event.event_type.value)
            print(f"  - {event.timestamp.strftime('%H:%M:%S')}: {event_name}")
            if event_name == "pr_merged":
                print(f"    PR #{event.details['pr_number']}: {event.details['pr_url']}")
            elif event_name == "slot_returned":
                print(f"    Workspace: {event.details['workspace_id']}, Slot: {event.details['slot_id']}")
        
        print("\n" + "=" * 80)
        print("Summary")
        print("=" * 80)
        print("""
The handle_pr_merged() method performs the following operations:

1. ✓ Records PR merged event in Task Registry
   - Captures PR details, merge commit SHA, timestamps
   - Marks task as COMPLETED

2. ✓ Deletes source branch (if configured)
   - Cleans up merged branches automatically
   - Configurable via delete_branch_after_merge setting

3. ✓ Returns workspace slot to Repo Pool Manager
   - Releases resources for other tasks
   - Records slot return event for tracking

4. ✓ Unblocks dependent tasks
   - Finds tasks that depend on completed task
   - Updates BLOCKED tasks to PENDING when all dependencies satisfied
   - Enables automatic workflow progression

This enables fully automated post-merge workflows in the NecroCode system!
        """)
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print("\n✓ Cleaned up temporary registry")


def example_pr_merged_with_config():
    """
    Example: Configure PR merge behavior.
    """
    print("\n" + "=" * 80)
    print("PR Merge Configuration Example")
    print("=" * 80)
    
    from necrocode.review_pr_service.config import PRServiceConfig, MergeConfig, GitHostType
    
    # Create configuration with custom merge settings
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your_github_token",
        repository="myorg/myrepo",
        merge=MergeConfig(
            delete_branch_after_merge=True,  # Auto-delete branches
            auto_merge_enabled=False,         # Manual merge approval
            require_ci_success=True,          # Require CI to pass
            required_approvals=2,             # Need 2 approvals
            check_conflicts=True              # Check for conflicts
        )
    )
    
    print("\nMerge Configuration:")
    print(f"  - Delete branch after merge: {config.merge.delete_branch_after_merge}")
    print(f"  - Auto-merge enabled: {config.merge.auto_merge_enabled}")
    print(f"  - Require CI success: {config.merge.require_ci_success}")
    print(f"  - Required approvals: {config.merge.required_approvals}")
    print(f"  - Check conflicts: {config.merge.check_conflicts}")
    
    print("\nUsage with PRService:")
    print("""
    from necrocode.review_pr_service.pr_service import PRService
    
    service = PRService(config)
    
    # Handle PR merged event with custom settings
    service.handle_pr_merged(
        pr=merged_pr,
        delete_branch=True,      # Override config if needed
        return_slot=True,        # Return workspace slot
        unblock_dependencies=True # Unblock dependent tasks
    )
    """)


if __name__ == "__main__":
    example_pr_merged_event()
    example_pr_merged_with_config()

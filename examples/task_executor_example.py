"""
Example: Using TaskExecutor to implement tasks.

This example demonstrates how to use the TaskExecutor to execute
task implementation with Kiro integration.
"""

from pathlib import Path
from necrocode.agent_runner import (
    TaskExecutor,
    KiroClient,
    TaskContext,
    Workspace,
)


def main():
    """Demonstrate TaskExecutor usage."""
    
    # Create a task context
    task_context = TaskContext(
        task_id="1.1",
        spec_name="user-authentication",
        title="Implement JWT authentication",
        description="Add JWT-based authentication to the API with login and register endpoints",
        acceptance_criteria=[
            "User can register with email and password",
            "User can login and receive JWT token",
            "Protected endpoints validate JWT token",
            "Passwords are hashed with bcrypt",
        ],
        dependencies=["1.0"],  # Depends on database setup
        required_skill="backend",
        slot_path=Path("/tmp/workspace"),
        slot_id="slot-1",
        branch_name="feature/task-1.1-jwt-auth",
        complexity="medium",
        require_review=True,
        timeout_seconds=1800,  # 30 minutes
    )
    
    # Create a workspace
    workspace = Workspace(
        path=Path("/tmp/workspace/slot-1"),
        branch_name="feature/task-1.1-jwt-auth",
        base_branch="main",
    )
    
    # Create TaskExecutor with default Kiro client
    executor = TaskExecutor()
    
    print(f"Executing task: {task_context.title}")
    print(f"Task ID: {task_context.task_id}")
    print(f"Workspace: {workspace.path}")
    print(f"Branch: {workspace.branch_name}")
    print()
    
    # Execute the task
    result = executor.execute(task_context, workspace)
    
    # Display results
    print("=" * 60)
    print("EXECUTION RESULTS")
    print("=" * 60)
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.2f} seconds")
    print(f"Files Changed: {len(result.files_changed)}")
    
    if result.files_changed:
        print("\nModified Files:")
        for file in result.files_changed:
            print(f"  - {file}")
    
    if result.error:
        print(f"\nError: {result.error}")
    
    if result.diff:
        print(f"\nDiff Preview (first 500 chars):")
        print(result.diff[:500])
        if len(result.diff) > 500:
            print("...")
    
    print()
    
    # Example: Using custom Kiro client
    print("=" * 60)
    print("CUSTOM KIRO CLIENT EXAMPLE")
    print("=" * 60)
    
    # Create custom Kiro client with specific configuration
    custom_client = KiroClient(workspace_path=workspace.path)
    executor_custom = TaskExecutor(kiro_client=custom_client)
    
    print("TaskExecutor created with custom Kiro client")
    print(f"Kiro workspace: {custom_client.workspace_path}")
    
    # Example: Building implementation prompt
    print()
    print("=" * 60)
    print("IMPLEMENTATION PROMPT EXAMPLE")
    print("=" * 60)
    
    prompt = executor._build_implementation_prompt(task_context)
    print("Generated prompt for Kiro:")
    print()
    print(prompt)


if __name__ == "__main__":
    main()

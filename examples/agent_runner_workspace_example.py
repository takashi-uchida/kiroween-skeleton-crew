"""
Example: Using Agent Runner WorkspaceManager

This example demonstrates how to use the WorkspaceManager to prepare
a workspace, commit changes, push with retry, and rollback if needed.
"""

from pathlib import Path
from necrocode.agent_runner import (
    WorkspaceManager,
    RetryConfig,
    WorkspacePreparationError,
    PushError,
)


def main():
    """Demonstrate WorkspaceManager usage."""
    
    # Create WorkspaceManager with custom retry configuration
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=60.0,
        exponential_base=2.0
    )
    workspace_manager = WorkspaceManager(retry_config=retry_config)
    
    # Example workspace path (in real usage, this would be from Repo Pool Manager)
    slot_path = Path("/path/to/workspace/slot")
    branch_name = "feature/task-agent-runner-1-workspace-manager"
    
    try:
        # Step 1: Prepare workspace
        print("Preparing workspace...")
        workspace = workspace_manager.prepare_workspace(
            slot_path=slot_path,
            branch_name=branch_name,
            base_branch="main"
        )
        print(f"✓ Workspace prepared: {workspace.path}")
        print(f"✓ Branch created: {workspace.branch_name}")
        
        # Step 2: Make changes (simulated - in real usage, TaskExecutor would do this)
        print("\nImplementing task...")
        # ... code changes happen here ...
        
        # Step 3: Commit changes
        print("\nCommitting changes...")
        commit_hash = workspace_manager.commit_changes(
            workspace=workspace,
            commit_message="feat(workspace): implement workspace manager [Task 2.1]"
        )
        print(f"✓ Changes committed: {commit_hash}")
        
        # Step 4: Get diff
        print("\nGetting diff...")
        diff = workspace_manager.get_diff(workspace)
        print(f"✓ Diff retrieved ({len(diff)} bytes)")
        
        # Step 5: Push branch with retry
        print("\nPushing branch...")
        push_result = workspace_manager.push_branch(
            workspace=workspace,
            branch_name=branch_name
        )
        print(f"✓ Branch pushed: {push_result.branch_name}")
        print(f"  Commit: {push_result.commit_hash}")
        print(f"  Retries: {push_result.retry_count}")
        
        print("\n✓ Task execution completed successfully!")
        
    except WorkspacePreparationError as e:
        print(f"\n✗ Workspace preparation failed: {e}")
        print("Attempting rollback...")
        try:
            workspace_manager.rollback(workspace)
            print("✓ Rollback successful")
        except Exception as rollback_error:
            print(f"✗ Rollback failed: {rollback_error}")
    
    except PushError as e:
        print(f"\n✗ Push failed after retries: {e}")
        print("Changes are committed locally but not pushed to remote")
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


def demonstrate_rollback():
    """Demonstrate rollback functionality."""
    print("\n" + "="*60)
    print("Demonstrating Rollback")
    print("="*60)
    
    workspace_manager = WorkspaceManager()
    slot_path = Path("/path/to/workspace/slot")
    
    try:
        # Prepare workspace
        workspace = workspace_manager.prepare_workspace(
            slot_path=slot_path,
            branch_name="feature/task-test-rollback",
            base_branch="main"
        )
        
        # Simulate some changes that we want to rollback
        print("\nMaking changes...")
        # ... changes happen ...
        
        # Rollback changes
        print("\nRolling back changes...")
        workspace_manager.rollback(workspace)
        print("✓ Rollback successful - workspace reset to origin/main")
        
    except WorkspacePreparationError as e:
        print(f"✗ Rollback failed: {e}")


if __name__ == "__main__":
    print("="*60)
    print("Agent Runner WorkspaceManager Example")
    print("="*60)
    
    # Note: This example requires a real Git repository
    # In production, the slot_path would be provided by Repo Pool Manager
    print("\nNote: This is a demonstration of the API.")
    print("To run with a real repository, update the slot_path variable.")
    print("\nAPI Overview:")
    print("  1. prepare_workspace() - checkout, fetch, rebase, create branch")
    print("  2. commit_changes() - stage and commit changes")
    print("  3. get_diff() - get diff between current state and base branch")
    print("  4. push_branch() - push with exponential backoff retry")
    print("  5. rollback() - reset to base branch and clean untracked files")
    
    # Uncomment to run with a real repository:
    # main()
    # demonstrate_rollback()

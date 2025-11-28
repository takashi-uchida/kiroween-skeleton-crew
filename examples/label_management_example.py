"""
Example demonstrating label management functionality in Review & PR Service.

This example shows how to:
1. Apply labels based on task type and priority
2. Update labels based on CI status changes
3. Configure custom label rules
4. Disable automatic label management
"""

from datetime import datetime
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import PRServiceConfig, GitHostType, LabelConfig
from necrocode.review_pr_service.models import PullRequest, CIStatus, PRState
from necrocode.task_registry.models import Task, TaskState


def example_basic_label_application():
    """Example: Apply labels based on task metadata."""
    print("=" * 60)
    print("Example 1: Basic Label Application")
    print("=" * 60)
    
    # Configure PR Service with label management enabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
    )
    
    # Create PR Service
    pr_service = PRService(config)
    
    # Create a sample task with metadata
    task = Task(
        id="1.1",
        title="Implement user authentication",
        description="Add JWT-based authentication",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "backend",  # Will trigger backend labels
            "priority": "high",  # Will add priority:high label
        }
    )
    
    # Create a sample PR
    pr = PullRequest(
        pr_id="12345",
        pr_number=42,
        title="Task 1.1: Implement user authentication",
        description="JWT-based authentication implementation",
        source_branch="feature/auth",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
    )
    
    # Apply labels (this would normally be called internally by create_pr)
    print(f"\nApplying labels to PR #{pr.pr_number}...")
    print(f"Task type: {task.metadata.get('type')}")
    print(f"Task priority: {task.metadata.get('priority')}")
    
    # Expected labels:
    # - backend, api (from task type)
    # - priority:high (from priority)
    print("\nExpected labels:")
    print("  - backend")
    print("  - api")
    print("  - priority:high")
    
    # Note: Actual API call would be made here
    # pr_service._apply_labels(pr, task)


def example_ci_status_label_updates():
    """Example: Update labels based on CI status changes."""
    print("\n" + "=" * 60)
    print("Example 2: CI Status Label Updates")
    print("=" * 60)
    
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
    )
    
    pr_service = PRService(config)
    
    pr_id = "12345"
    
    # Scenario 1: CI starts (pending)
    print(f"\nScenario 1: CI starts")
    print(f"  Updating PR {pr_id} with CI status: PENDING")
    print(f"  Expected action: Add 'ci:pending' label")
    
    # pr_service.update_labels_for_ci_status(pr_id, CIStatus.PENDING)
    
    # Scenario 2: CI succeeds
    print(f"\nScenario 2: CI succeeds")
    print(f"  Updating PR {pr_id} with CI status: SUCCESS")
    print(f"  Expected actions:")
    print(f"    1. Remove 'ci:pending' label")
    print(f"    2. Add 'ci:success' label")
    
    # pr_service.update_labels_for_ci_status(pr_id, CIStatus.SUCCESS)
    
    # Scenario 3: CI fails
    print(f"\nScenario 3: CI fails on retry")
    print(f"  Updating PR {pr_id} with CI status: FAILURE")
    print(f"  Expected actions:")
    print(f"    1. Remove 'ci:success' label")
    print(f"    2. Add 'ci:failure' label")
    
    # pr_service.update_labels_for_ci_status(pr_id, CIStatus.FAILURE)


def example_custom_label_rules():
    """Example: Configure custom label rules."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Label Rules")
    print("=" * 60)
    
    # Configure custom label rules
    custom_labels = LabelConfig(
        enabled=True,
        rules={
            "backend": ["backend-service", "api", "server"],
            "frontend": ["frontend-app", "ui", "client"],
            "database": ["database", "schema", "migration"],
            "devops": ["infrastructure", "deployment", "ci-cd"],
            "documentation": ["docs", "readme"],
            "testing": ["tests", "qa", "quality"],
        },
        ci_status_labels=True,
        priority_labels=True,
    )
    
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
        labels=custom_labels,
    )
    
    pr_service = PRService(config)
    
    print("\nCustom label rules configured:")
    for task_type, labels in custom_labels.rules.items():
        print(f"  {task_type}: {', '.join(labels)}")
    
    # Example task with custom labels
    task = Task(
        id="2.1",
        title="Update database schema",
        description="Add new tables for user profiles",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "database",  # Will trigger custom database labels
            "priority": "medium",
        }
    )
    
    print(f"\nTask type: {task.metadata.get('type')}")
    print(f"Expected labels: database, schema, migration, priority:medium")


def example_disable_label_management():
    """Example: Disable automatic label management."""
    print("\n" + "=" * 60)
    print("Example 4: Disable Label Management")
    print("=" * 60)
    
    # Configure with labels disabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
    )
    
    # Disable label management
    config.labels.enabled = False
    
    pr_service = PRService(config)
    
    print("\nLabel management disabled")
    print("No labels will be automatically applied to PRs")
    
    task = Task(
        id="3.1",
        title="Some task",
        description="Task description",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "backend",
            "priority": "high",
        }
    )
    
    pr = PullRequest(
        pr_id="12345",
        pr_number=42,
        title="Test PR",
        description="Test",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
    )
    
    # This will not apply any labels because labels.enabled = False
    # pr_service._apply_labels(pr, task)
    print("Labels would NOT be applied even though task has type and priority")


def example_selective_label_features():
    """Example: Enable/disable specific label features."""
    print("\n" + "=" * 60)
    print("Example 5: Selective Label Features")
    print("=" * 60)
    
    # Configure with selective features
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
    )
    
    # Enable task type labels but disable priority and CI labels
    config.labels.enabled = True
    config.labels.priority_labels = False
    config.labels.ci_status_labels = False
    
    pr_service = PRService(config)
    
    print("\nLabel configuration:")
    print(f"  Overall enabled: {config.labels.enabled}")
    print(f"  Priority labels: {config.labels.priority_labels}")
    print(f"  CI status labels: {config.labels.ci_status_labels}")
    
    task = Task(
        id="4.1",
        title="Frontend component",
        description="Build login form",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "frontend",
            "priority": "high",
        }
    )
    
    print(f"\nTask metadata:")
    print(f"  Type: {task.metadata.get('type')}")
    print(f"  Priority: {task.metadata.get('priority')}")
    
    print(f"\nExpected labels:")
    print(f"  - frontend, ui (from task type)")
    print(f"  - priority:high will NOT be added (disabled)")
    print(f"  - ci:* labels will NOT be added (disabled)")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Label Management Examples")
    print("=" * 60)
    
    example_basic_label_application()
    example_ci_status_label_updates()
    example_custom_label_rules()
    example_disable_label_management()
    example_selective_label_features()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNote: These examples demonstrate the API usage.")
    print("Actual API calls are commented out to avoid making real requests.")
    print("Uncomment the API calls and provide valid credentials to test with real Git hosts.")


if __name__ == "__main__":
    main()

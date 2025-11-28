"""
Example: Basic PR Service Usage

Demonstrates how to use the PRService to create and manage pull requests.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.review_pr_service import (
    PRService,
    PRServiceConfig,
    GitHostType,
)
from necrocode.task_registry.models import Task, TaskState, Artifact, ArtifactType
from datetime import datetime


def example_create_pr():
    """Example: Create a PR for a task."""
    print("=" * 60)
    print("Example: Create PR for Task")
    print("=" * 60)
    
    # Configure PR Service for GitHub
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",  # Replace with your repository
        api_token="your-github-token",  # Replace with your token
        task_registry_path="~/.necrocode/task_registry",
    )
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create a sample task
    task = Task(
        id="1.1",
        title="Implement user authentication",
        description="Add JWT-based authentication to the API",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "backend",
            "priority": "high",
            "reviewers": ["reviewer1", "reviewer2"],
        }
    )
    
    # Add some sample artifacts
    task.artifacts = [
        Artifact(
            type=ArtifactType.DIFF,
            uri="https://example.com/artifacts/task-1.1/diff.txt",
            size_bytes=1024,
            created_at=datetime.now(),
            metadata={"name": "Code Changes"}
        ),
        Artifact(
            type=ArtifactType.TEST_RESULT,
            uri="https://example.com/artifacts/task-1.1/test-results.json",
            size_bytes=2048,
            created_at=datetime.now(),
            metadata={
                "name": "Test Results",
                "total_tests": 25,
                "passed": 24,
                "failed": 1,
                "skipped": 0,
                "duration": 12.5,
            }
        ),
        Artifact(
            type=ArtifactType.LOG,
            uri="https://example.com/artifacts/task-1.1/execution.log",
            size_bytes=4096,
            created_at=datetime.now(),
            metadata={
                "name": "Execution Log",
                "execution_time": 45.2,
                "has_errors": False,
            }
        ),
    ]
    
    # Acceptance criteria
    acceptance_criteria = [
        "User can register with email and password",
        "User can login and receive JWT token",
        "Protected endpoints validate JWT token",
        "Passwords are hashed with bcrypt",
        "All tests pass",
    ]
    
    try:
        # Create PR
        print("\nCreating PR...")
        pr = pr_service.create_pr(
            task=task,
            branch_name="feature/task-1.1-user-auth",
            base_branch="main",
            acceptance_criteria=acceptance_criteria,
        )
        
        print(f"\n✅ PR Created Successfully!")
        print(f"   PR Number: #{pr.pr_number}")
        print(f"   PR URL: {pr.url}")
        print(f"   Title: {pr.title}")
        print(f"   State: {pr.state.value}")
        print(f"   Draft: {pr.draft}")
        print(f"   Source: {pr.source_branch}")
        print(f"   Target: {pr.target_branch}")
        
    except Exception as e:
        print(f"\n❌ Failed to create PR: {e}")


def example_update_pr_description():
    """Example: Update PR description with execution results."""
    print("\n" + "=" * 60)
    print("Example: Update PR Description")
    print("=" * 60)
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
    )
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # PR ID to update (replace with actual PR ID)
    pr_id = "12345"
    
    # Updates to add
    updates = {
        "execution_time": 45.2,
        "test_results": {
            "total": 25,
            "passed": 24,
            "failed": 1,
            "skipped": 0,
            "duration": 12.5,
        },
        "execution_logs": [
            {
                "name": "Build Log",
                "url": "https://example.com/logs/build.log"
            },
            {
                "name": "Test Log",
                "url": "https://example.com/logs/test.log"
            },
        ],
    }
    
    try:
        print(f"\nUpdating PR {pr_id}...")
        pr_service.update_pr_description(pr_id, updates)
        print(f"✅ PR description updated successfully!")
        
    except Exception as e:
        print(f"❌ Failed to update PR: {e}")


def example_with_gitlab():
    """Example: Create PR with GitLab."""
    print("\n" + "=" * 60)
    print("Example: Create PR with GitLab")
    print("=" * 60)
    
    # Configure PR Service for GitLab
    config = PRServiceConfig(
        git_host_type=GitHostType.GITLAB,
        git_host_url="https://gitlab.com",
        repository="12345",  # GitLab project ID
        api_token="your-gitlab-token",
    )
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    print(f"✅ PR Service initialized for GitLab")
    print(f"   Project ID: {config.repository}")
    print(f"   URL: {config.git_host_url}")


def example_with_custom_template():
    """Example: Use custom PR template."""
    print("\n" + "=" * 60)
    print("Example: Custom PR Template")
    print("=" * 60)
    
    # Configure PR Service with custom template
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
    )
    
    # Set custom template path
    config.template.template_path = "templates/custom-pr-template.md"
    
    # Add custom sections
    config.template.custom_sections = {
        "Breaking Changes": "None",
        "Migration Guide": "No migration required",
        "Performance Impact": "Minimal impact expected",
    }
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    print(f"✅ PR Service initialized with custom template")
    print(f"   Template: {config.template.template_path}")
    print(f"   Custom sections: {list(config.template.custom_sections.keys())}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("PR Service Examples")
    print("=" * 60)
    
    # Note: These examples require valid credentials and repository access
    # Uncomment the examples you want to run
    
    # example_create_pr()
    # example_update_pr_description()
    # example_with_gitlab()
    example_with_custom_template()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNote: To run the PR creation examples, you need to:")
    print("  1. Replace 'owner/repo' with your actual repository")
    print("  2. Set a valid API token (GitHub/GitLab/Bitbucket)")
    print("  3. Ensure you have write access to the repository")
    print("  4. Uncomment the example functions you want to run")


if __name__ == "__main__":
    main()

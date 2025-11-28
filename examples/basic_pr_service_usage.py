#!/usr/bin/env python3
"""
Basic PR Service Usage Example

This example demonstrates the basic usage of the Review & PR Service,
including PR creation, updating, and comment posting.
"""

import os
from datetime import datetime
from necrocode.review_pr_service import (
    PRService,
    PRServiceConfig,
    GitHostType,
)
from necrocode.review_pr_service.config import (
    LabelConfig,
    ReviewerConfig,
    MergeConfig,
    DraftConfig,
)
from necrocode.task_registry.models import Task, TaskState


def main():
    """Basic PR service usage example"""
    
    # ========================================
    # 1. Configuration
    # ========================================
    
    print("=" * 60)
    print("Basic PR Service Usage Example")
    print("=" * 60)
    
    # Get API token from environment
    api_token = os.getenv("GITHUB_TOKEN")
    if not api_token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("   Set it with: export GITHUB_TOKEN='your-token'")
        return
    
    # Create configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",  # Replace with your repository
        api_token=api_token,
    )
    
    # Configure labels
    config.labels = LabelConfig(
        enabled=True,
        rules={
            "backend": ["backend", "api"],
            "frontend": ["frontend", "ui"],
            "database": ["database", "schema"],
        }
    )
    
    # Configure reviewers
    config.reviewers = ReviewerConfig(
        enabled=True,
        strategy="round-robin",
        default_reviewers=["reviewer1", "reviewer2"],
    )
    
    # Configure merge settings
    config.merge = MergeConfig(
        strategy="squash",
        auto_merge_enabled=False,
        delete_branch_after_merge=True,
        required_approvals=1,
    )
    
    # Configure draft PR settings
    config.draft = DraftConfig(
        enabled=True,
        create_as_draft=True,
        convert_on_ci_success=True,
    )
    
    print("\n✅ Configuration created")
    print(f"   Git Host: {config.git_host_type.value}")
    print(f"   Repository: {config.repository}")
    print(f"   Labels enabled: {config.labels.enabled}")
    print(f"   Reviewers enabled: {config.reviewers.enabled}")
    
    # ========================================
    # 2. Initialize PR Service
    # ========================================
    
    print("\n" + "=" * 60)
    print("Initializing PR Service")
    print("=" * 60)
    
    try:
        pr_service = PRService(config)
        print("✅ PR Service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize PR Service: {e}")
        return
    
    # ========================================
    # 3. Create a Task
    # ========================================
    
    print("\n" + "=" * 60)
    print("Creating Task")
    print("=" * 60)
    
    task = Task(
        id="1.1",
        title="Implement user authentication",
        description="Add JWT-based authentication to the API with login and register endpoints",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "backend",
            "priority": "high",
            "estimated_hours": 8,
        }
    )
    
    print(f"✅ Task created: {task.id} - {task.title}")
    print(f"   Type: {task.metadata.get('type')}")
    print(f"   Priority: {task.metadata.get('priority')}")
    
    # ========================================
    # 4. Create Pull Request
    # ========================================
    
    print("\n" + "=" * 60)
    print("Creating Pull Request")
    print("=" * 60)
    
    # Define acceptance criteria
    acceptance_criteria = [
        "User can register with email and password",
        "User can login and receive JWT token",
        "Protected endpoints validate JWT token",
        "Passwords are hashed with bcrypt",
        "All tests pass",
    ]
    
    try:
        pr = pr_service.create_pr(
            task=task,
            branch_name="feature/task-1.1-user-auth",
            base_branch="main",
            acceptance_criteria=acceptance_criteria,
        )
        
        print(f"✅ Pull Request created successfully!")
        print(f"   PR Number: #{pr.pr_number}")
        print(f"   PR URL: {pr.url}")
        print(f"   Title: {pr.title}")
        print(f"   Source Branch: {pr.source_branch}")
        print(f"   Target Branch: {pr.target_branch}")
        print(f"   Draft: {pr.draft}")
        print(f"   State: {pr.state.value}")
        
        if pr.labels:
            print(f"   Labels: {', '.join(pr.labels)}")
        if pr.reviewers:
            print(f"   Reviewers: {', '.join(pr.reviewers)}")
        
    except Exception as e:
        print(f"❌ Failed to create PR: {e}")
        return
    
    # ========================================
    # 5. Update PR Description
    # ========================================
    
    print("\n" + "=" * 60)
    print("Updating PR Description")
    print("=" * 60)
    
    # Simulate execution results
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
        pr_service.update_pr_description(
            pr_id=pr.pr_id,
            updates=updates
        )
        print("✅ PR description updated successfully")
        print(f"   Execution time: {updates['execution_time']}s")
        print(f"   Tests: {updates['test_results']['passed']}/{updates['test_results']['total']} passed")
    except Exception as e:
        print(f"❌ Failed to update PR: {e}")
    
    # ========================================
    # 6. Post Comment
    # ========================================
    
    print("\n" + "=" * 60)
    print("Posting Comment")
    print("=" * 60)
    
    try:
        pr_service.post_comment(
            pr_id=pr.pr_id,
            message="Please review the authentication implementation",
            details={
                "Security Review": "Required",
                "Priority": "High",
                "Estimated Review Time": "30 minutes",
            }
        )
        print("✅ Comment posted successfully")
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")
    
    # ========================================
    # 7. Post Test Failure Comment (Example)
    # ========================================
    
    print("\n" + "=" * 60)
    print("Posting Test Failure Comment (Example)")
    print("=" * 60)
    
    # Simulate test failure
    test_results = {
        "total": 25,
        "passed": 24,
        "failed": 1,
        "skipped": 0,
        "duration": 12.5,
        "failed_tests": [
            {
                "name": "test_password_hashing",
                "error": "AssertionError: Password hash does not match expected format"
            }
        ]
    }
    
    try:
        pr_service.post_test_failure_comment(
            pr_id=pr.pr_id,
            test_results=test_results,
            error_log_url="https://ci.example.com/logs/456",
            artifact_links={
                "Test Report": "https://artifacts.example.com/report.html",
                "Coverage Report": "https://artifacts.example.com/coverage.html",
            }
        )
        print("✅ Test failure comment posted successfully")
    except Exception as e:
        print(f"❌ Failed to post test failure comment: {e}")
    
    # ========================================
    # 8. Check for Conflicts
    # ========================================
    
    print("\n" + "=" * 60)
    print("Checking for Merge Conflicts")
    print("=" * 60)
    
    try:
        conflict_result = pr_service.check_merge_conflicts(pr.pr_id)
        
        if conflict_result['has_conflicts']:
            print("⚠️  Merge conflicts detected!")
            print(f"   Details: {conflict_result['details']}")
            if conflict_result.get('conflicting_files'):
                print(f"   Conflicting files: {', '.join(conflict_result['conflicting_files'])}")
        else:
            print("✅ No merge conflicts detected")
    except Exception as e:
        print(f"❌ Failed to check conflicts: {e}")
    
    # ========================================
    # Summary
    # ========================================
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Successfully demonstrated PR Service basic usage")
    print(f"   - Created PR #{pr.pr_number}")
    print(f"   - Updated PR description with execution results")
    print(f"   - Posted comments")
    print(f"   - Checked for conflicts")
    print(f"\n📝 View your PR at: {pr.url}")


if __name__ == "__main__":
    main()

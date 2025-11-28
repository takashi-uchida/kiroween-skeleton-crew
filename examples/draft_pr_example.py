"""
Example: Draft PR Functionality

This example demonstrates how to use the draft PR features of the Review & PR Service.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
from pathlib import Path
from datetime import datetime

from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    DraftConfig,
    ReviewerConfig
)
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.models import CIStatus
from necrocode.task_registry.models import Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_create_draft_pr():
    """
    Example 1: Create a draft PR.
    
    Demonstrates creating a PR in draft state, which:
    - Does not assign reviewers (if configured)
    - Adds a draft label
    - Can be converted to ready later
    
    Requirements: 12.1
    """
    logger.info("=== Example 1: Create Draft PR ===")
    
    # Configure PR Service with draft enabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
        draft=DraftConfig(
            enabled=True,
            create_as_draft=True,  # Create PRs as draft by default
            skip_reviewers=True,   # Don't assign reviewers to drafts
            draft_label="draft"
        )
    )
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create a task
    task = Task(
        id="1.1",
        title="Implement user authentication",
        description="Add JWT-based authentication",
        dependencies=[],
        metadata={
            "type": "backend",
            "priority": "high"
        }
    )
    
    # Create draft PR
    pr = pr_service.create_pr(
        task=task,
        branch_name="feature/task-1.1-auth",
        base_branch="main"
    )
    
    logger.info(f"Created draft PR: {pr.url}")
    logger.info(f"Draft status: {pr.draft}")
    logger.info(f"Reviewers assigned: {len(pr.reviewers)}")  # Should be 0 if skip_reviewers=True
    
    return pr


def example_convert_draft_to_ready():
    """
    Example 2: Convert draft PR to ready for review.
    
    Demonstrates manually converting a draft PR to ready state, which:
    - Marks PR as ready for review
    - Assigns reviewers
    - Removes draft label
    
    Requirements: 12.2
    """
    logger.info("=== Example 2: Convert Draft to Ready ===")
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
        draft=DraftConfig(
            enabled=True,
            convert_on_ci_success=False  # Manual conversion
        )
    )
    
    pr_service = PRService(config)
    
    # Assume we have a draft PR ID
    draft_pr_id = "123"
    
    # Convert to ready
    pr_service.convert_draft_to_ready(
        pr_id=draft_pr_id,
        assign_reviewers=True,  # Assign reviewers after conversion
        update_labels=True      # Remove draft label
    )
    
    logger.info(f"Converted PR {draft_pr_id} to ready for review")


def example_auto_convert_on_ci_success():
    """
    Example 3: Auto-convert draft PR when CI succeeds.
    
    Demonstrates automatic conversion of draft PR to ready when CI passes.
    This is useful for work-in-progress PRs that should only be reviewed
    after tests pass.
    
    Requirements: 12.2
    """
    logger.info("=== Example 3: Auto-Convert on CI Success ===")
    
    # Configure PR Service with auto-conversion enabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
        draft=DraftConfig(
            enabled=True,
            create_as_draft=True,
            convert_on_ci_success=True  # Auto-convert when CI passes
        )
    )
    
    pr_service = PRService(config)
    
    # Simulate CI status change to SUCCESS
    draft_pr_id = "123"
    
    # This would typically be called by CI monitoring or webhook handler
    converted = pr_service.convert_draft_on_ci_success(draft_pr_id)
    
    if converted:
        logger.info(f"PR {draft_pr_id} auto-converted to ready (CI success)")
    else:
        logger.info(f"PR {draft_pr_id} not converted (conditions not met)")


def example_draft_pr_workflow():
    """
    Example 4: Complete draft PR workflow.
    
    Demonstrates a complete workflow:
    1. Create draft PR
    2. Wait for CI to pass
    3. Auto-convert to ready
    4. Assign reviewers
    
    Requirements: 12.1, 12.2, 12.3
    """
    logger.info("=== Example 4: Complete Draft PR Workflow ===")
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
        draft=DraftConfig(
            enabled=True,
            create_as_draft=True,
            convert_on_ci_success=True,
            skip_reviewers=True,
            draft_label="wip"
        ),
        reviewers=ReviewerConfig(
            enabled=True,
            skip_draft_prs=True,  # Don't assign reviewers to drafts
            default_reviewers=["reviewer1", "reviewer2"]
        )
    )
    
    pr_service = PRService(config)
    
    # Step 1: Create draft PR
    task = Task(
        id="2.1",
        title="Add user profile page",
        description="Create user profile UI",
        dependencies=["1.1"],
        metadata={"type": "frontend"}
    )
    
    pr = pr_service.create_pr(
        task=task,
        branch_name="feature/task-2.1-profile",
        base_branch="main"
    )
    
    logger.info(f"Step 1: Created draft PR #{pr.pr_number}")
    logger.info(f"  - Draft: {pr.draft}")
    logger.info(f"  - Reviewers: {pr.reviewers}")  # Should be empty
    logger.info(f"  - Labels: {pr.labels}")  # Should include 'wip'
    
    # Step 2: Simulate CI running and passing
    logger.info("Step 2: Waiting for CI to pass...")
    # In real scenario, CI would run and webhook would trigger conversion
    
    # Step 3: Auto-convert when CI succeeds
    logger.info("Step 3: CI passed, auto-converting to ready...")
    converted = pr_service.convert_draft_on_ci_success(pr.pr_id)
    
    if converted:
        logger.info("  - PR converted to ready for review")
        logger.info("  - Reviewers assigned")
        logger.info("  - Draft label removed")
    
    logger.info("Workflow complete!")


def example_disable_draft_feature():
    """
    Example 5: Disable draft feature.
    
    Demonstrates how to disable the draft feature entirely.
    When disabled, all PRs are created as ready for review.
    
    Requirements: 12.5
    """
    logger.info("=== Example 5: Disable Draft Feature ===")
    
    # Configure PR Service with draft disabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="your-github-token",
        draft=DraftConfig(
            enabled=False  # Disable draft feature
        )
    )
    
    pr_service = PRService(config)
    
    # Create PR (will be created as ready, not draft)
    task = Task(
        id="3.1",
        title="Add API endpoint",
        description="Create REST API endpoint",
        dependencies=[],
        metadata={"type": "backend"}
    )
    
    pr = pr_service.create_pr(
        task=task,
        branch_name="feature/task-3.1-api",
        base_branch="main"
    )
    
    logger.info(f"Created PR: {pr.url}")
    logger.info(f"Draft status: {pr.draft}")  # Should be False
    logger.info(f"Reviewers assigned: {len(pr.reviewers)}")  # Should have reviewers


def example_draft_with_gitlab():
    """
    Example 6: Draft PRs with GitLab.
    
    Demonstrates draft PR functionality with GitLab merge requests.
    GitLab uses "Draft:" prefix or work_in_progress flag.
    
    Requirements: 12.1, 12.2
    """
    logger.info("=== Example 6: Draft PRs with GitLab ===")
    
    # Configure PR Service for GitLab
    config = PRServiceConfig(
        git_host_type=GitHostType.GITLAB,
        repository="project-id",  # GitLab project ID
        api_token="your-gitlab-token",
        git_host_url="https://gitlab.com",
        draft=DraftConfig(
            enabled=True,
            create_as_draft=True
        )
    )
    
    pr_service = PRService(config)
    
    # Create draft MR (GitLab's equivalent of PR)
    task = Task(
        id="4.1",
        title="Update documentation",
        description="Update README",
        dependencies=[],
        metadata={"type": "documentation"}
    )
    
    pr = pr_service.create_pr(
        task=task,
        branch_name="feature/task-4.1-docs",
        base_branch="main"
    )
    
    logger.info(f"Created draft MR: {pr.url}")
    logger.info(f"Title: {pr.title}")  # GitLab adds "Draft:" prefix
    
    # Convert to ready
    pr_service.convert_draft_to_ready(pr.pr_id)
    logger.info("Converted to ready (Draft: prefix removed)")


if __name__ == "__main__":
    print("Draft PR Functionality Examples")
    print("=" * 50)
    print()
    
    # Note: These examples require valid API tokens and repositories
    # Uncomment the examples you want to run
    
    # example_create_draft_pr()
    # example_convert_draft_to_ready()
    # example_auto_convert_on_ci_success()
    # example_draft_pr_workflow()
    # example_disable_draft_feature()
    # example_draft_with_gitlab()
    
    print("\nExamples completed!")
    print("\nNote: To run these examples, you need to:")
    print("1. Set valid API tokens in the configuration")
    print("2. Use actual repository names")
    print("3. Have appropriate permissions")

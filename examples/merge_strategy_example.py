"""
Example demonstrating merge strategy functionality in Review & PR Service.

This example shows how to:
1. Configure merge strategies
2. Merge PRs with different strategies
3. Enable auto-merge on CI success
4. Check for merge conflicts
5. Handle merge failures

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
from pathlib import Path
from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    MergeStrategy,
    MergeConfig
)
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.models import PullRequest, CIStatus, PRState
from necrocode.task_registry.models import Task
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_merge_strategy_configuration():
    """
    Example 1: Configure merge strategies.
    
    Requirements: 9.1
    """
    logger.info("=" * 60)
    logger.info("Example 1: Merge Strategy Configuration")
    logger.info("=" * 60)
    
    # Create configuration with merge settings
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="fake_token_for_example",
        merge=MergeConfig(
            strategy=MergeStrategy.SQUASH,  # Use squash merge
            auto_merge_enabled=False,
            delete_branch_after_merge=True,
            require_ci_success=True,
            required_approvals=2,  # Require 2 approvals
            check_conflicts=True
        )
    )
    
    logger.info(f"Merge strategy: {config.merge.strategy.value}")
    logger.info(f"Auto-merge enabled: {config.merge.auto_merge_enabled}")
    logger.info(f"Delete branch after merge: {config.merge.delete_branch_after_merge}")
    logger.info(f"Require CI success: {config.merge.require_ci_success}")
    logger.info(f"Required approvals: {config.merge.required_approvals}")
    logger.info(f"Check conflicts: {config.merge.check_conflicts}")
    
    # Different merge strategies
    strategies = [
        MergeStrategy.MERGE,   # Standard merge commit
        MergeStrategy.SQUASH,  # Squash all commits into one
        MergeStrategy.REBASE,  # Rebase and merge
    ]
    
    logger.info("\nAvailable merge strategies:")
    for strategy in strategies:
        logger.info(f"  - {strategy.value}: {strategy.name}")
    
    logger.info("\n✓ Merge strategy configuration complete\n")


def example_manual_merge():
    """
    Example 2: Manually merge a PR with specific strategy.
    
    Requirements: 9.1, 9.3, 9.4
    """
    logger.info("=" * 60)
    logger.info("Example 2: Manual PR Merge")
    logger.info("=" * 60)
    
    # Create service with configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="fake_token_for_example",
        merge=MergeConfig(
            strategy=MergeStrategy.SQUASH,
            required_approvals=1,
            check_conflicts=True
        )
    )
    
    # Note: This would fail with fake credentials, but shows the API
    try:
        service = PRService(config)
        
        # Merge PR with default strategy from config
        logger.info("Merging PR #123 with default strategy (squash)...")
        # service.merge_pr(
        #     pr_id="123",
        #     check_ci=True,
        #     check_approvals=True,
        #     check_conflicts=True
        # )
        
        # Merge PR with specific strategy (override config)
        logger.info("Merging PR #124 with rebase strategy...")
        # service.merge_pr(
        #     pr_id="124",
        #     merge_strategy=MergeStrategy.REBASE,
        #     delete_branch=True
        # )
        
        # Merge PR without deleting branch
        logger.info("Merging PR #125 without deleting branch...")
        # service.merge_pr(
        #     pr_id="125",
        #     delete_branch=False
        # )
        
        logger.info("\n✓ Manual merge examples complete\n")
    
    except Exception as e:
        logger.error(f"Expected error with fake credentials: {e}")
        logger.info("\n✓ Manual merge API demonstrated\n")


def example_auto_merge():
    """
    Example 3: Enable auto-merge on CI success.
    
    Requirements: 9.2
    """
    logger.info("=" * 60)
    logger.info("Example 3: Auto-Merge on CI Success")
    logger.info("=" * 60)
    
    # Create service with auto-merge enabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="fake_token_for_example",
        merge=MergeConfig(
            strategy=MergeStrategy.SQUASH,
            auto_merge_enabled=True,  # Enable auto-merge
            require_ci_success=True,
            required_approvals=1,
            check_conflicts=True
        )
    )
    
    logger.info(f"Auto-merge enabled: {config.merge.auto_merge_enabled}")
    logger.info(f"Required approvals: {config.merge.required_approvals}")
    
    try:
        service = PRService(config)
        
        # Simulate CI success event
        pr_id = "123"
        logger.info(f"\nSimulating CI success for PR {pr_id}...")
        
        # This would be called when CI status changes to SUCCESS
        # merged = service.auto_merge_on_ci_success(pr_id)
        # 
        # if merged:
        #     logger.info(f"✓ PR {pr_id} was automatically merged")
        # else:
        #     logger.info(f"✗ PR {pr_id} was not merged (conditions not met)")
        
        logger.info("\nAuto-merge workflow:")
        logger.info("1. CI status changes to SUCCESS")
        logger.info("2. Service checks if auto-merge is enabled")
        logger.info("3. Service verifies all conditions:")
        logger.info("   - PR is open and not draft")
        logger.info("   - CI status is SUCCESS")
        logger.info("   - Required approvals are met")
        logger.info("   - No merge conflicts")
        logger.info("4. If all conditions met, PR is automatically merged")
        
        logger.info("\n✓ Auto-merge example complete\n")
    
    except Exception as e:
        logger.error(f"Expected error with fake credentials: {e}")
        logger.info("\n✓ Auto-merge API demonstrated\n")


def example_conflict_detection():
    """
    Example 4: Check for merge conflicts.
    
    Requirements: 9.4, 13.1, 13.2
    """
    logger.info("=" * 60)
    logger.info("Example 4: Merge Conflict Detection")
    logger.info("=" * 60)
    
    # Create service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="fake_token_for_example",
        merge=MergeConfig(
            check_conflicts=True
        )
    )
    
    try:
        service = PRService(config)
        
        pr_id = "123"
        logger.info(f"Checking for conflicts in PR {pr_id}...")
        
        # Check for conflicts
        # result = service.check_merge_conflicts(pr_id)
        # 
        # logger.info(f"\nConflict check result:")
        # logger.info(f"  PR: #{result['pr_number']}")
        # logger.info(f"  Has conflicts: {result['has_conflicts']}")
        # logger.info(f"  Checked at: {result['checked_at']}")
        # 
        # if result['has_conflicts']:
        #     logger.info(f"  Details: {result['details']['message']}")
        #     
        #     # Post comment about conflicts
        #     logger.info(f"\nPosting conflict comment to PR {pr_id}...")
        #     service.post_conflict_comment(
        #         pr_id=pr_id,
        #         conflict_details=result['details']
        #     )
        #     logger.info("✓ Conflict comment posted")
        
        logger.info("\nConflict detection workflow:")
        logger.info("1. Check PR for merge conflicts")
        logger.info("2. If conflicts found:")
        logger.info("   - Post comment to PR with details")
        logger.info("   - Record conflict event in Task Registry")
        logger.info("   - Provide resolution instructions")
        logger.info("3. If no conflicts, proceed with merge")
        
        logger.info("\n✓ Conflict detection example complete\n")
    
    except Exception as e:
        logger.error(f"Expected error with fake credentials: {e}")
        logger.info("\n✓ Conflict detection API demonstrated\n")


def example_merge_failure_handling():
    """
    Example 5: Handle merge failures.
    
    Requirements: 9.5
    """
    logger.info("=" * 60)
    logger.info("Example 5: Merge Failure Handling")
    logger.info("=" * 60)
    
    # Create service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="fake_token_for_example",
        task_registry_path=str(Path.home() / ".necrocode" / "task_registry")
    )
    
    try:
        service = PRService(config)
        
        pr_id = "123"
        logger.info(f"Attempting to merge PR {pr_id}...")
        
        # Simulate merge failure scenarios
        logger.info("\nPossible merge failure scenarios:")
        logger.info("1. CI status is not SUCCESS")
        logger.info("2. Required approvals not met")
        logger.info("3. Merge conflicts detected")
        logger.info("4. PR is in draft state")
        logger.info("5. Network or API errors")
        
        # When merge fails, the service:
        # 1. Logs the error
        # 2. Records failure event in Task Registry
        # 3. Raises PRServiceError with details
        
        logger.info("\nMerge failure handling:")
        logger.info("1. Error is logged with details")
        logger.info("2. Failure event recorded in Task Registry:")
        logger.info("   - Event type: TASK_FAILED")
        logger.info("   - Error message")
        logger.info("   - Timestamp")
        logger.info("   - PR details")
        logger.info("3. Exception raised to caller")
        logger.info("4. Caller can retry or take corrective action")
        
        # Example of handling merge failure
        logger.info("\nExample error handling:")
        logger.info("""
try:
    service.merge_pr(pr_id="123")
except PRServiceError as e:
    logger.error(f"Merge failed: {e}")
    # Take corrective action:
    # - Check CI status
    # - Request more approvals
    # - Resolve conflicts
    # - Retry merge
        """)
        
        logger.info("\n✓ Merge failure handling example complete\n")
    
    except Exception as e:
        logger.error(f"Expected error with fake credentials: {e}")
        logger.info("\n✓ Merge failure handling demonstrated\n")


def example_complete_merge_workflow():
    """
    Example 6: Complete merge workflow with all features.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    logger.info("=" * 60)
    logger.info("Example 6: Complete Merge Workflow")
    logger.info("=" * 60)
    
    # Create service with full configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="fake_token_for_example",
        merge=MergeConfig(
            strategy=MergeStrategy.SQUASH,
            auto_merge_enabled=True,
            delete_branch_after_merge=True,
            require_ci_success=True,
            required_approvals=2,
            check_conflicts=True
        ),
        task_registry_path=str(Path.home() / ".necrocode" / "task_registry")
    )
    
    logger.info("Complete merge workflow:")
    logger.info("\n1. PR Creation")
    logger.info("   - PR created with task details")
    logger.info("   - Labels and reviewers assigned")
    logger.info("   - CI triggered automatically")
    
    logger.info("\n2. CI Execution")
    logger.info("   - Tests run on PR branch")
    logger.info("   - CI status monitored")
    logger.info("   - Status updates posted to PR")
    
    logger.info("\n3. Review Process")
    logger.info("   - Reviewers notified")
    logger.info("   - Comments and feedback provided")
    logger.info("   - Approvals collected")
    
    logger.info("\n4. Pre-Merge Checks")
    logger.info("   - CI status: SUCCESS ✓")
    logger.info("   - Approvals: 2/2 ✓")
    logger.info("   - Conflicts: None ✓")
    logger.info("   - Draft status: False ✓")
    
    logger.info("\n5. Merge Execution")
    logger.info("   - Strategy: SQUASH")
    logger.info("   - All commits squashed into one")
    logger.info("   - Merged to target branch")
    logger.info("   - Source branch deleted")
    
    logger.info("\n6. Post-Merge Actions")
    logger.info("   - PR marked as merged")
    logger.info("   - Merge event recorded in Task Registry")
    logger.info("   - Workspace slot returned to pool")
    logger.info("   - Dependent tasks unblocked")
    logger.info("   - Reviewer loads updated")
    
    logger.info("\n7. Failure Handling (if needed)")
    logger.info("   - Error logged and recorded")
    logger.info("   - Failure event in Task Registry")
    logger.info("   - Notification sent")
    logger.info("   - Manual intervention requested")
    
    logger.info("\n✓ Complete merge workflow demonstrated\n")


def main():
    """Run all merge strategy examples."""
    logger.info("\n" + "=" * 60)
    logger.info("MERGE STRATEGY EXAMPLES")
    logger.info("=" * 60 + "\n")
    
    try:
        # Run examples
        example_merge_strategy_configuration()
        example_manual_merge()
        example_auto_merge()
        example_conflict_detection()
        example_merge_failure_handling()
        example_complete_merge_workflow()
        
        logger.info("=" * 60)
        logger.info("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

"""
Example demonstrating conflict detection functionality in Review & PR Service.

This example shows how to:
1. Check for conflicts when creating a PR
2. Post conflict comments automatically
3. Re-check conflicts after resolution
4. Perform periodic conflict checks on multiple PRs

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

import logging
from pathlib import Path
from necrocode.review_pr_service.config import PRServiceConfig, GitHostType
from necrocode.review_pr_service.pr_service import PRService
from necrocode.task_registry.models import Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_conflict_detection_on_creation():
    """
    Example 1: Conflict detection when creating a PR.
    
    Demonstrates automatic conflict checking when a PR is created.
    """
    logger.info("=" * 60)
    logger.info("Example 1: Conflict Detection on PR Creation")
    logger.info("=" * 60)
    
    # Configure PR Service with conflict detection enabled
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
        task_registry_path=str(Path.home() / ".necrocode" / "task_registry"),
    )
    
    # Enable conflict detection on PR creation
    config.conflict_detection.enabled = True
    config.conflict_detection.check_on_creation = True
    config.conflict_detection.auto_comment = True
    
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
            "priority": "high",
        }
    )
    
    try:
        # Create PR - conflicts will be automatically checked
        pr = pr_service.create_pr(
            task=task,
            branch_name="feature/auth-implementation",
            base_branch="main"
        )
        
        logger.info(f"✅ PR created: #{pr.pr_number}")
        logger.info(f"   URL: {pr.url}")
        logger.info(f"   Conflicts checked automatically on creation")
        
    except Exception as e:
        logger.error(f"❌ Failed to create PR: {e}")


def example_manual_conflict_check():
    """
    Example 2: Manual conflict checking for an existing PR.
    
    Demonstrates how to manually check for conflicts in a PR.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Manual Conflict Check")
    logger.info("=" * 60)
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    
    config.conflict_detection.enabled = True
    config.conflict_detection.auto_comment = True
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Check for conflicts in an existing PR
    pr_id = "123"  # Replace with actual PR ID
    
    try:
        # Check for conflicts
        conflict_result = pr_service.check_merge_conflicts(pr_id)
        
        logger.info(f"Conflict check for PR {pr_id}:")
        logger.info(f"  Has conflicts: {conflict_result['has_conflicts']}")
        logger.info(f"  Checked at: {conflict_result['checked_at']}")
        
        if conflict_result['has_conflicts']:
            logger.warning("⚠️  Conflicts detected!")
            logger.info(f"  Details: {conflict_result['details']}")
            
            # Post conflict comment
            pr_service.post_conflict_comment(
                pr_id=pr_id,
                conflict_details=conflict_result['details']
            )
            logger.info("  Conflict comment posted to PR")
        else:
            logger.info("✅ No conflicts detected")
        
    except Exception as e:
        logger.error(f"❌ Failed to check conflicts: {e}")


def example_recheck_after_resolution():
    """
    Example 3: Re-check conflicts after resolution attempt.
    
    Demonstrates how to verify that conflicts have been resolved.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Re-check Conflicts After Resolution")
    logger.info("=" * 60)
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
        task_registry_path=str(Path.home() / ".necrocode" / "task_registry"),
    )
    
    config.conflict_detection.enabled = True
    config.conflict_detection.auto_comment = True
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Re-check conflicts after developer pushes resolution
    pr_id = "123"  # Replace with actual PR ID
    
    try:
        logger.info(f"Re-checking conflicts for PR {pr_id}...")
        
        # Re-check conflicts
        conflicts_resolved = pr_service.recheck_conflicts_after_resolution(
            pr_id=pr_id,
            post_success_comment=True  # Post success comment if resolved
        )
        
        if conflicts_resolved:
            logger.info("✅ Conflicts have been resolved!")
            logger.info("   Success comment posted to PR")
        else:
            logger.warning("⚠️  Conflicts still exist")
            logger.info("   Developer needs to continue resolving conflicts")
        
    except Exception as e:
        logger.error(f"❌ Failed to re-check conflicts: {e}")


def example_periodic_conflict_check():
    """
    Example 4: Periodic conflict checking for multiple PRs.
    
    Demonstrates how to check multiple PRs for conflicts periodically.
    This would typically be run by a scheduler (e.g., cron job).
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Periodic Conflict Check")
    logger.info("=" * 60)
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
        task_registry_path=str(Path.home() / ".necrocode" / "task_registry"),
    )
    
    config.conflict_detection.enabled = True
    config.conflict_detection.periodic_check = True
    config.conflict_detection.check_interval = 3600  # Check every hour
    config.conflict_detection.auto_comment = True
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # List of PR IDs to check (in production, this would be fetched from Git host)
    pr_ids = ["123", "124", "125"]  # Replace with actual PR IDs
    
    try:
        logger.info(f"Running periodic conflict check for {len(pr_ids)} PRs...")
        
        # Perform periodic check
        results = pr_service.periodic_conflict_check(
            pr_ids=pr_ids,
            only_open_prs=True
        )
        
        # Summarize results
        logger.info("\nPeriodic Check Results:")
        logger.info("-" * 40)
        
        for pr_id, has_conflicts in results.items():
            if has_conflicts is None:
                logger.warning(f"  PR {pr_id}: Check failed")
            elif has_conflicts:
                logger.warning(f"  PR {pr_id}: ⚠️  Conflicts detected")
            else:
                logger.info(f"  PR {pr_id}: ✅ No conflicts")
        
        # Count statistics
        total = len(results)
        with_conflicts = sum(1 for v in results.values() if v is True)
        without_conflicts = sum(1 for v in results.values() if v is False)
        failed = sum(1 for v in results.values() if v is None)
        
        logger.info("-" * 40)
        logger.info(f"Total PRs checked: {total}")
        logger.info(f"  With conflicts: {with_conflicts}")
        logger.info(f"  Without conflicts: {without_conflicts}")
        logger.info(f"  Check failed: {failed}")
        
    except Exception as e:
        logger.error(f"❌ Periodic conflict check failed: {e}")


def example_conflict_detection_workflow():
    """
    Example 5: Complete conflict detection workflow.
    
    Demonstrates a complete workflow from PR creation through conflict
    detection, notification, and resolution verification.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Complete Conflict Detection Workflow")
    logger.info("=" * 60)
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
        task_registry_path=str(Path.home() / ".necrocode" / "task_registry"),
    )
    
    # Enable all conflict detection features
    config.conflict_detection.enabled = True
    config.conflict_detection.check_on_creation = True
    config.conflict_detection.auto_comment = True
    config.conflict_detection.periodic_check = True
    config.conflict_detection.recheck_on_push = True
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create a task
    task = Task(
        id="2.1",
        title="Update database schema",
        description="Add new columns to users table",
        dependencies=["1.1"],
        metadata={
            "type": "database",
            "priority": "high",
        }
    )
    
    try:
        # Step 1: Create PR with automatic conflict detection
        logger.info("\nStep 1: Creating PR...")
        pr = pr_service.create_pr(
            task=task,
            branch_name="feature/db-schema-update",
            base_branch="main"
        )
        logger.info(f"✅ PR created: #{pr.pr_number}")
        logger.info(f"   Conflicts automatically checked on creation")
        
        # Step 2: Manual conflict check (if needed)
        logger.info("\nStep 2: Manual conflict check...")
        conflict_result = pr_service.check_merge_conflicts(pr.pr_id)
        
        if conflict_result['has_conflicts']:
            logger.warning("⚠️  Conflicts detected!")
            
            # Step 3: Post conflict comment
            logger.info("\nStep 3: Posting conflict notification...")
            pr_service.post_conflict_comment(
                pr_id=pr.pr_id,
                conflict_details=conflict_result['details']
            )
            logger.info("✅ Conflict comment posted")
            
            # Simulate developer resolving conflicts...
            logger.info("\n[Developer resolves conflicts and pushes changes...]")
            
            # Step 4: Re-check after resolution
            logger.info("\nStep 4: Re-checking conflicts after resolution...")
            conflicts_resolved = pr_service.recheck_conflicts_after_resolution(
                pr_id=pr.pr_id,
                post_success_comment=True
            )
            
            if conflicts_resolved:
                logger.info("✅ Conflicts resolved successfully!")
            else:
                logger.warning("⚠️  Conflicts still exist, needs more work")
        else:
            logger.info("✅ No conflicts detected")
        
        logger.info("\n" + "=" * 60)
        logger.info("Workflow completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")


def example_configuration_options():
    """
    Example 6: Conflict detection configuration options.
    
    Demonstrates various configuration options for conflict detection.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Configuration Options")
    logger.info("=" * 60)
    
    # Create config with custom conflict detection settings
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    
    # Customize conflict detection behavior
    config.conflict_detection.enabled = True
    config.conflict_detection.check_on_creation = True  # Check when PR is created
    config.conflict_detection.auto_comment = True  # Auto-post conflict comments
    config.conflict_detection.periodic_check = True  # Enable periodic checking
    config.conflict_detection.check_interval = 1800  # Check every 30 minutes
    config.conflict_detection.recheck_on_push = True  # Re-check when code is pushed
    
    logger.info("Conflict Detection Configuration:")
    logger.info(f"  Enabled: {config.conflict_detection.enabled}")
    logger.info(f"  Check on creation: {config.conflict_detection.check_on_creation}")
    logger.info(f"  Auto-comment: {config.conflict_detection.auto_comment}")
    logger.info(f"  Periodic check: {config.conflict_detection.periodic_check}")
    logger.info(f"  Check interval: {config.conflict_detection.check_interval}s")
    logger.info(f"  Recheck on push: {config.conflict_detection.recheck_on_push}")
    
    # You can also disable conflict detection entirely
    config_disabled = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    config_disabled.conflict_detection.enabled = False
    
    logger.info("\nConflict detection can be disabled:")
    logger.info(f"  Enabled: {config_disabled.conflict_detection.enabled}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Review & PR Service - Conflict Detection Examples")
    print("=" * 60)
    print("\nThese examples demonstrate conflict detection functionality.")
    print("Replace placeholder values (tokens, PR IDs) with actual values.")
    print("\n" + "=" * 60 + "\n")
    
    # Run examples
    # Note: Comment out examples that require actual Git host access
    
    # example_conflict_detection_on_creation()
    # example_manual_conflict_check()
    # example_recheck_after_resolution()
    # example_periodic_conflict_check()
    # example_conflict_detection_workflow()
    example_configuration_options()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

"""
CI Status Monitor Example

Demonstrates how to use CIStatusMonitor to monitor CI/CD status for pull requests.
"""

import time
from pathlib import Path

from necrocode.review_pr_service import (
    PRServiceConfig,
    PRService,
    CIStatusMonitor,
    GitHostType,
    PullRequest,
    CIStatus,
)
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState


def on_ci_success(pr: PullRequest, ci_status: CIStatus):
    """Callback for CI success."""
    print(f"✅ CI succeeded for PR #{pr.pr_number}: {pr.url}")
    print(f"   Status: {ci_status.value}")


def on_ci_failure(pr: PullRequest, ci_status: CIStatus):
    """Callback for CI failure."""
    print(f"❌ CI failed for PR #{pr.pr_number}: {pr.url}")
    print(f"   Status: {ci_status.value}")


def on_status_change(pr: PullRequest, old_status: CIStatus, new_status: CIStatus):
    """Callback for any CI status change."""
    print(f"🔄 CI status changed for PR #{pr.pr_number}")
    print(f"   {old_status.value} → {new_status.value}")


def example_synchronous_monitoring():
    """Example: Synchronous CI status check."""
    print("\n" + "="*60)
    print("Example 1: Synchronous CI Status Check")
    print("="*60 + "\n")
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create CI Status Monitor
    ci_monitor = CIStatusMonitor(
        git_host_client=pr_service.git_host_client,
        config=config,
        task_registry=pr_service.task_registry
    )
    
    # Create a mock PR for demonstration
    pr = PullRequest(
        pr_id="123",
        pr_number=42,
        title="Add new feature",
        description="This PR adds a new feature",
        source_branch="feature/new-feature",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state="open",
        draft=False,
        created_at="2024-01-01T00:00:00Z",
    )
    
    # Get current CI status (synchronous)
    try:
        ci_status = ci_monitor.monitor_ci_status(
            pr=pr,
            on_success=on_ci_success,
            on_failure=on_ci_failure,
            on_status_change=on_status_change
        )
        
        print(f"Current CI status: {ci_status.value}")
    
    except Exception as e:
        print(f"Error: {e}")


def example_background_monitoring():
    """Example: Background CI status monitoring with polling."""
    print("\n" + "="*60)
    print("Example 2: Background CI Status Monitoring")
    print("="*60 + "\n")
    
    # Configure PR Service with custom CI settings
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    
    # Customize CI monitoring settings
    config.ci.enabled = True
    config.ci.polling_interval = 30  # Poll every 30 seconds
    config.ci.timeout = 1800  # 30 minute timeout
    config.ci.auto_comment_on_failure = True
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create CI Status Monitor
    ci_monitor = CIStatusMonitor(
        git_host_client=pr_service.git_host_client,
        config=config,
        task_registry=pr_service.task_registry
    )
    
    # Create a mock PR
    pr = PullRequest(
        pr_id="123",
        pr_number=42,
        title="Add new feature",
        description="This PR adds a new feature",
        source_branch="feature/new-feature",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state="open",
        draft=False,
        created_at="2024-01-01T00:00:00Z",
        spec_id="my-feature",
        task_id="1.1",
    )
    
    # Start background monitoring
    print(f"Starting CI monitoring for PR #{pr.pr_number}...")
    print(f"Polling interval: {config.ci.polling_interval}s")
    print(f"Timeout: {config.ci.timeout}s\n")
    
    ci_monitor.start_monitoring(
        pr=pr,
        on_success=on_ci_success,
        on_failure=on_ci_failure,
        on_status_change=on_status_change
    )
    
    # Check monitoring status
    status = ci_monitor.get_monitoring_status(pr.pr_id)
    print(f"Monitoring status: {status}\n")
    
    # Simulate waiting for CI to complete
    print("Waiting for CI to complete (simulated)...")
    print("In production, this would poll the actual CI status.\n")
    
    # Wait a bit to see some polling activity
    time.sleep(5)
    
    # Stop monitoring
    print("Stopping CI monitoring...")
    ci_monitor.stop_monitoring(pr.pr_id)
    
    print("✓ Monitoring stopped")


def example_multiple_prs():
    """Example: Monitor multiple PRs simultaneously."""
    print("\n" + "="*60)
    print("Example 3: Monitor Multiple PRs")
    print("="*60 + "\n")
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    
    config.ci.polling_interval = 60
    config.ci.timeout = 3600
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create CI Status Monitor
    ci_monitor = CIStatusMonitor(
        git_host_client=pr_service.git_host_client,
        config=config,
        task_registry=pr_service.task_registry
    )
    
    # Create multiple PRs
    prs = [
        PullRequest(
            pr_id=f"{i}",
            pr_number=100 + i,
            title=f"Feature {i}",
            description=f"This PR implements feature {i}",
            source_branch=f"feature/feature-{i}",
            target_branch="main",
            url=f"https://github.com/owner/repo/pull/{100+i}",
            state="open",
            draft=False,
            created_at="2024-01-01T00:00:00Z",
            spec_id=f"feature-{i}",
            task_id=f"{i}.1",
        )
        for i in range(1, 4)
    ]
    
    # Start monitoring all PRs
    print(f"Starting CI monitoring for {len(prs)} PRs...\n")
    
    for pr in prs:
        ci_monitor.start_monitoring(
            pr=pr,
            on_success=on_ci_success,
            on_failure=on_ci_failure,
            on_status_change=on_status_change
        )
        print(f"✓ Monitoring PR #{pr.pr_number}")
    
    print()
    
    # Get status of all monitored PRs
    all_status = ci_monitor.get_all_monitoring_status()
    print(f"Currently monitoring {len(all_status)} PRs:")
    for pr_id, status in all_status.items():
        print(f"  PR {pr_id}: {status}")
    
    print()
    
    # Wait a bit
    time.sleep(3)
    
    # Stop all monitoring
    print("Stopping all CI monitoring...")
    ci_monitor.stop_all_monitoring()
    
    print("✓ All monitoring stopped")


def example_with_task_registry():
    """Example: CI monitoring with Task Registry integration."""
    print("\n" + "="*60)
    print("Example 4: CI Monitoring with Task Registry")
    print("="*60 + "\n")
    
    # Setup Task Registry
    registry_dir = Path.home() / ".necrocode" / "task_registry"
    task_registry = TaskRegistry(registry_dir=registry_dir)
    
    print(f"Task Registry: {registry_dir}\n")
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
        task_registry_path=str(registry_dir),
    )
    
    config.ci.polling_interval = 30
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create CI Status Monitor with Task Registry
    ci_monitor = CIStatusMonitor(
        git_host_client=pr_service.git_host_client,
        config=config,
        task_registry=task_registry
    )
    
    # Create a PR linked to a task
    pr = PullRequest(
        pr_id="123",
        pr_number=42,
        title="Implement authentication",
        description="This PR implements JWT authentication",
        source_branch="feature/auth",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state="open",
        draft=False,
        created_at="2024-01-01T00:00:00Z",
        spec_id="authentication-feature",
        task_id="2.1",
    )
    
    print(f"PR #{pr.pr_number}: {pr.title}")
    print(f"Linked to: spec={pr.spec_id}, task={pr.task_id}\n")
    
    # Start monitoring
    print("Starting CI monitoring with Task Registry integration...")
    
    ci_monitor.start_monitoring(
        pr=pr,
        on_success=lambda p, s: print(f"✅ CI success recorded to Task Registry"),
        on_failure=lambda p, s: print(f"❌ CI failure recorded to Task Registry"),
        on_status_change=lambda p, o, n: print(f"🔄 Status change recorded: {o.value} → {n.value}")
    )
    
    print("✓ Monitoring started")
    print("\nCI status changes will be recorded to Task Registry:")
    print("  - TaskUpdated events for status changes")
    print("  - TaskCompleted event on CI success")
    print("  - TaskFailed event on CI failure\n")
    
    # Wait a bit
    time.sleep(3)
    
    # Stop monitoring
    ci_monitor.stop_monitoring(pr.pr_id)
    print("✓ Monitoring stopped")


def example_custom_callbacks():
    """Example: Custom callbacks for CI events."""
    print("\n" + "="*60)
    print("Example 5: Custom CI Event Callbacks")
    print("="*60 + "\n")
    
    # Configure PR Service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="your-github-token",
        repository="owner/repo",
    )
    
    # Initialize PR Service
    pr_service = PRService(config)
    
    # Create CI Status Monitor
    ci_monitor = CIStatusMonitor(
        git_host_client=pr_service.git_host_client,
        config=config,
        task_registry=pr_service.task_registry
    )
    
    # Custom callback: Auto-merge on CI success
    def auto_merge_on_success(pr: PullRequest, ci_status: CIStatus):
        print(f"✅ CI succeeded for PR #{pr.pr_number}")
        print(f"   Attempting auto-merge...")
        
        try:
            # In production, this would call:
            # pr_service.git_host_client.merge_pr(pr.pr_id)
            print(f"   ✓ PR #{pr.pr_number} merged successfully")
        except Exception as e:
            print(f"   ✗ Auto-merge failed: {e}")
    
    # Custom callback: Post comment on CI failure
    def comment_on_failure(pr: PullRequest, ci_status: CIStatus):
        print(f"❌ CI failed for PR #{pr.pr_number}")
        print(f"   Posting failure comment...")
        
        comment = f"""
## ❌ CI Failed

The CI pipeline has failed for this PR. Please review the logs and fix the issues.

**Status:** {ci_status.value}
**PR:** {pr.url}

---
*This comment was automatically posted by NecroCode*
"""
        
        try:
            # In production, this would call:
            # pr_service.git_host_client.add_comment(pr.pr_id, comment)
            print(f"   ✓ Comment posted to PR #{pr.pr_number}")
        except Exception as e:
            print(f"   ✗ Failed to post comment: {e}")
    
    # Custom callback: Update labels on status change
    def update_labels_on_change(pr: PullRequest, old_status: CIStatus, new_status: CIStatus):
        print(f"🔄 CI status changed for PR #{pr.pr_number}")
        print(f"   {old_status.value} → {new_status.value}")
        print(f"   Updating labels...")
        
        try:
            # In production, this would call:
            # pr_service.update_labels_for_ci_status(pr.pr_id, new_status)
            print(f"   ✓ Labels updated")
        except Exception as e:
            print(f"   ✗ Failed to update labels: {e}")
    
    # Create a PR
    pr = PullRequest(
        pr_id="123",
        pr_number=42,
        title="Add new feature",
        description="This PR adds a new feature",
        source_branch="feature/new-feature",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state="open",
        draft=False,
        created_at="2024-01-01T00:00:00Z",
    )
    
    # Start monitoring with custom callbacks
    print(f"Starting CI monitoring with custom callbacks...\n")
    
    ci_monitor.start_monitoring(
        pr=pr,
        on_success=auto_merge_on_success,
        on_failure=comment_on_failure,
        on_status_change=update_labels_on_change
    )
    
    print("✓ Monitoring started with custom callbacks:")
    print("  - Auto-merge on CI success")
    print("  - Post comment on CI failure")
    print("  - Update labels on status change\n")
    
    # Wait a bit
    time.sleep(3)
    
    # Stop monitoring
    ci_monitor.stop_monitoring(pr.pr_id)
    print("✓ Monitoring stopped")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CI Status Monitor Examples")
    print("="*60)
    
    # Note: These examples use mock data and won't make actual API calls
    # In production, you would need valid API tokens and repository access
    
    try:
        example_synchronous_monitoring()
        example_background_monitoring()
        example_multiple_prs()
        example_with_task_registry()
        example_custom_callbacks()
        
        print("\n" + "="*60)
        print("All examples completed!")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

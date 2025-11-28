"""
Example: Webhook Handler Usage

Demonstrates how to set up and use the WebhookHandler to receive
events from Git hosts (GitHub, GitLab, Bitbucket).
"""

import time
import logging
from pathlib import Path

from necrocode.review_pr_service.config import PRServiceConfig, GitHostType, WebhookConfig
from necrocode.review_pr_service.webhook_handler import WebhookHandler, WebhookEvent
from necrocode.review_pr_service.pr_service import PRService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def handle_pr_merged(event: WebhookEvent):
    """
    Handle PR merge events
    
    This callback is invoked when a PR is merged.
    """
    logger.info(f"PR #{event.pr_number} was merged!")
    logger.info(f"  Repository: {event.repository}")
    logger.info(f"  Merged by: {event.merged_by}")
    logger.info(f"  Timestamp: {event.timestamp}")
    
    # Example: Clean up resources after merge
    # - Return repo pool slot
    # - Update task registry
    # - Delete branch if configured
    logger.info("Cleaning up resources...")


def handle_ci_status_changed(event: WebhookEvent):
    """
    Handle CI status change events
    
    This callback is invoked when CI status changes.
    """
    logger.info(f"CI status changed for PR #{event.pr_number}")
    logger.info(f"  Repository: {event.repository}")
    logger.info(f"  New status: {event.ci_status}")
    logger.info(f"  Timestamp: {event.timestamp}")
    
    # Example: Take action based on CI status
    if event.ci_status.value == "success":
        logger.info("CI passed! Ready for review.")
    elif event.ci_status.value == "failure":
        logger.info("CI failed! Adding comment to PR...")


def example_github_webhook():
    """Example: GitHub webhook setup"""
    logger.info("=== GitHub Webhook Example ===")
    
    # Configure for GitHub
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="ghp_your_token_here",
        repository="owner/repo",
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret="your_webhook_secret_here",
            verify_signature=True,
            async_processing=True
        )
    )
    
    # Create webhook handler
    webhook_handler = WebhookHandler(
        config=config,
        on_pr_merged=handle_pr_merged,
        on_ci_status_changed=handle_ci_status_changed
    )
    
    # Start webhook server
    logger.info("Starting webhook server on port 8080...")
    webhook_handler.start()
    
    logger.info("Webhook server is running. Configure GitHub webhook:")
    logger.info("  URL: http://your-server:8080/webhook")
    logger.info("  Content type: application/json")
    logger.info("  Secret: your_webhook_secret_here")
    logger.info("  Events: Pull requests, Check suites")
    
    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down webhook server...")
        webhook_handler.stop()


def example_gitlab_webhook():
    """Example: GitLab webhook setup"""
    logger.info("=== GitLab Webhook Example ===")
    
    # Configure for GitLab
    config = PRServiceConfig(
        git_host_type=GitHostType.GITLAB,
        api_token="glpat-your_token_here",
        repository="group/project",
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret="your_webhook_token_here",
            verify_signature=True
        )
    )
    
    # Create webhook handler
    webhook_handler = WebhookHandler(
        config=config,
        on_pr_merged=handle_pr_merged,
        on_ci_status_changed=handle_ci_status_changed
    )
    
    # Start webhook server
    webhook_handler.start()
    
    logger.info("Webhook server is running. Configure GitLab webhook:")
    logger.info("  URL: http://your-server:8080/webhook")
    logger.info("  Secret Token: your_webhook_token_here")
    logger.info("  Trigger: Merge request events, Pipeline events")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        webhook_handler.stop()


def example_with_pr_service():
    """Example: Integrate webhook with PR service"""
    logger.info("=== Webhook + PR Service Integration ===")
    
    # Configure service
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="ghp_your_token_here",
        repository="owner/repo",
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret="your_webhook_secret"
        )
    )
    
    # Create PR service
    pr_service = PRService(config)
    
    # Define handlers that use PR service
    def on_pr_merged(event: WebhookEvent):
        """Handle PR merge with PR service"""
        logger.info(f"Processing merge for PR #{event.pr_number}")
        
        # Use PR service to handle post-merge tasks
        pr_service.handle_pr_merged(str(event.pr_number))
    
    def on_ci_status(event: WebhookEvent):
        """Handle CI status with PR service"""
        logger.info(f"Processing CI status for PR #{event.pr_number}")
        
        # Update PR based on CI status
        if event.ci_status.value == "failure":
            # Add comment about failure
            logger.info("Adding failure comment to PR")
    
    # Create and start webhook handler
    webhook_handler = WebhookHandler(
        config=config,
        on_pr_merged=on_pr_merged,
        on_ci_status_changed=on_ci_status
    )
    
    webhook_handler.start()
    
    logger.info("Integrated webhook + PR service running")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        webhook_handler.stop()


def example_register_handlers():
    """Example: Register handlers after initialization"""
    logger.info("=== Dynamic Handler Registration ===")
    
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret="secret"
        )
    )
    
    # Create handler without callbacks
    webhook_handler = WebhookHandler(config)
    
    # Register handlers dynamically
    webhook_handler.register_pr_merged_handler(handle_pr_merged)
    webhook_handler.register_ci_status_handler(handle_ci_status_changed)
    
    webhook_handler.start()
    
    logger.info("Webhook server with dynamic handlers running")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        webhook_handler.stop()


def example_no_signature_verification():
    """Example: Webhook without signature verification (development only)"""
    logger.info("=== Webhook Without Signature Verification ===")
    logger.warning("WARNING: This is for development only!")
    
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret=None,  # No secret = no verification
            verify_signature=False
        )
    )
    
    webhook_handler = WebhookHandler(
        config=config,
        on_pr_merged=handle_pr_merged,
        on_ci_status_changed=handle_ci_status_changed
    )
    
    webhook_handler.start()
    
    logger.info("Webhook server running WITHOUT signature verification")
    logger.warning("Do not use this in production!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        webhook_handler.stop()


if __name__ == "__main__":
    import sys
    
    examples = {
        "github": example_github_webhook,
        "gitlab": example_gitlab_webhook,
        "integrated": example_with_pr_service,
        "dynamic": example_register_handlers,
        "no-verify": example_no_signature_verification,
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("Usage: python webhook_handler_example.py [example]")
        print("\nAvailable examples:")
        print("  github      - GitHub webhook setup")
        print("  gitlab      - GitLab webhook setup")
        print("  integrated  - Webhook + PR Service integration")
        print("  dynamic     - Dynamic handler registration")
        print("  no-verify   - Without signature verification (dev only)")
        print("\nExample:")
        print("  python webhook_handler_example.py github")

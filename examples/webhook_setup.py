#!/usr/bin/env python3
"""
Webhook Setup Example

This example demonstrates how to set up and configure webhooks for the
Review & PR Service, including GitHub, GitLab, and Bitbucket webhooks.
"""

import os
import time
from necrocode.review_pr_service import (
    PRService,
    PRServiceConfig,
    GitHostType,
)
from necrocode.review_pr_service.webhook_handler import (
    WebhookHandler,
    WebhookEvent,
)
from necrocode.review_pr_service.config import WebhookConfig
from necrocode.review_pr_service.models import CIStatus


def setup_github_webhook():
    """Set up webhook for GitHub"""
    
    print("=" * 60)
    print("GitHub Webhook Setup")
    print("=" * 60)
    
    # Get credentials
    github_token = os.getenv("GITHUB_TOKEN")
    webhook_secret = os.getenv("WEBHOOK_SECRET", "default-secret-change-me")
    
    if not github_token:
        print("❌ GITHUB_TOKEN not set")
        return None
    
    # Configure webhook
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token=github_token,
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret=webhook_secret,
            verify_signature=True,  # Always verify in production
            async_processing=True,
        )
    )
    
    print("✅ GitHub webhook configuration created")
    print(f"   Port: {config.webhook.port}")
    print(f"   Signature verification: {config.webhook.verify_signature}")
    print(f"   Async processing: {config.webhook.async_processing}")
    
    print("\n📝 GitHub Webhook Configuration:")
    print("   1. Go to: https://github.com/owner/repo/settings/hooks")
    print("   2. Click 'Add webhook'")
    print("   3. Set Payload URL: http://your-server:8080/webhook")
    print("   4. Set Content type: application/json")
    print(f"   5. Set Secret: {webhook_secret}")
    print("   6. Select events:")
    print("      - Pull requests")
    print("      - Check suites")
    print("      - Statuses")
    print("   7. Click 'Add webhook'")
    
    return config


def setup_gitlab_webhook():
    """Set up webhook for GitLab"""
    
    print("\n" + "=" * 60)
    print("GitLab Webhook Setup")
    print("=" * 60)
    
    # Get credentials
    gitlab_token = os.getenv("GITLAB_TOKEN")
    webhook_secret = os.getenv("WEBHOOK_SECRET", "default-secret-change-me")
    
    if not gitlab_token:
        print("❌ GITLAB_TOKEN not set")
        return None
    
    # Configure webhook
    config = PRServiceConfig(
        git_host_type=GitHostType.GITLAB,
        repository="group/project",
        api_token=gitlab_token,
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret=webhook_secret,
            verify_signature=True,
            async_processing=True,
        )
    )
    
    print("✅ GitLab webhook configuration created")
    print(f"   Port: {config.webhook.port}")
    
    print("\n📝 GitLab Webhook Configuration:")
    print("   1. Go to: https://gitlab.com/group/project/-/hooks")
    print("   2. Set URL: http://your-server:8080/webhook")
    print(f"   3. Set Secret Token: {webhook_secret}")
    print("   4. Select triggers:")
    print("      - Merge request events")
    print("      - Pipeline events")
    print("   5. Click 'Add webhook'")
    
    return config


def setup_bitbucket_webhook():
    """Set up webhook for Bitbucket"""
    
    print("\n" + "=" * 60)
    print("Bitbucket Webhook Setup")
    print("=" * 60)
    
    # Get credentials
    bitbucket_token = os.getenv("BITBUCKET_TOKEN")
    webhook_secret = os.getenv("WEBHOOK_SECRET", "default-secret-change-me")
    
    if not bitbucket_token:
        print("❌ BITBUCKET_TOKEN not set")
        return None
    
    # Configure webhook
    config = PRServiceConfig(
        git_host_type=GitHostType.BITBUCKET,
        repository="workspace/repo",
        api_token=bitbucket_token,
        webhook=WebhookConfig(
            enabled=True,
            port=8080,
            secret=webhook_secret,
            verify_signature=True,
            async_processing=True,
        )
    )
    
    print("✅ Bitbucket webhook configuration created")
    print(f"   Port: {config.webhook.port}")
    
    print("\n📝 Bitbucket Webhook Configuration:")
    print("   1. Go to: https://bitbucket.org/workspace/repo/admin/addon/admin/bitbucket-webhooks/bb-webhooks-repo-admin")
    print("   2. Click 'Add webhook'")
    print("   3. Set Title: NecroCode Webhook")
    print("   4. Set URL: http://your-server:8080/webhook")
    print(f"   5. Set Secret: {webhook_secret}")
    print("   6. Select triggers:")
    print("      - Pull Request Merged")
    print("      - Build Status Updated")
    print("   7. Click 'Save'")
    
    return config


def create_webhook_handlers(pr_service):
    """Create webhook event handlers"""
    
    print("\n" + "=" * 60)
    print("Creating Webhook Handlers")
    print("=" * 60)
    
    def on_pr_merged(event: WebhookEvent):
        """Handle PR merge event"""
        print(f"\n🎉 PR Merged Event Received")
        print(f"   PR #{event.pr_number}")
        print(f"   Repository: {event.repository}")
        print(f"   Merged by: {event.merged_by}")
        print(f"   Timestamp: {event.timestamp}")
        
        # Handle post-merge tasks
        try:
            pr_service.handle_pr_merged(str(event.pr_number))
            print(f"   ✅ Post-merge tasks completed")
        except Exception as e:
            print(f"   ❌ Error handling merge: {e}")
    
    def on_ci_status_changed(event: WebhookEvent):
        """Handle CI status change event"""
        print(f"\n🔄 CI Status Changed")
        print(f"   PR #{event.pr_number}")
        print(f"   Status: {event.ci_status.value}")
        print(f"   Repository: {event.repository}")
        print(f"   Timestamp: {event.timestamp}")
        
        # Handle CI status
        if event.ci_status == CIStatus.SUCCESS:
            print(f"   ✅ CI passed!")
            # Could auto-merge here if configured
            
        elif event.ci_status == CIStatus.FAILURE:
            print(f"   ❌ CI failed!")
            # Post failure comment
            try:
                pr_service.post_comment(
                    pr_id=str(event.pr_number),
                    message="⚠️ CI checks failed. Please review the errors.",
                    details={
                        "Status": event.ci_status.value,
                        "Timestamp": event.timestamp.isoformat(),
                    }
                )
                print(f"   ✅ Failure comment posted")
            except Exception as e:
                print(f"   ❌ Error posting comment: {e}")
    
    print("✅ Webhook handlers created")
    print("   - on_pr_merged: Handle PR merge events")
    print("   - on_ci_status_changed: Handle CI status changes")
    
    return on_pr_merged, on_ci_status_changed


def start_webhook_server(config, on_pr_merged, on_ci_status_changed):
    """Start webhook server"""
    
    print("\n" + "=" * 60)
    print("Starting Webhook Server")
    print("=" * 60)
    
    # Create webhook handler
    webhook_handler = WebhookHandler(
        config=config,
        on_pr_merged=on_pr_merged,
        on_ci_status_changed=on_ci_status_changed,
    )
    
    # Start server
    webhook_handler.start()
    
    print(f"✅ Webhook server started")
    print(f"   Listening on: http://0.0.0.0:{config.webhook.port}/webhook")
    print(f"   Health check: http://0.0.0.0:{config.webhook.port}/health")
    
    return webhook_handler


def test_webhook_health(port=8080):
    """Test webhook server health"""
    
    print("\n" + "=" * 60)
    print("Testing Webhook Health")
    print("=" * 60)
    
    import urllib.request
    import json
    
    try:
        # Test health endpoint
        response = urllib.request.urlopen(f"http://localhost:{port}/health")
        data = json.loads(response.read().decode())
        
        print("✅ Health check passed")
        print(f"   Status: {data.get('status')}")
        print(f"   Service: {data.get('service')}")
        
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def simulate_github_webhook(port=8080, secret="default-secret-change-me"):
    """Simulate a GitHub webhook event for testing"""
    
    print("\n" + "=" * 60)
    print("Simulating GitHub Webhook")
    print("=" * 60)
    
    import urllib.request
    import json
    import hmac
    import hashlib
    
    # Create test payload
    payload = {
        "action": "closed",
        "pull_request": {
            "id": 12345,
            "number": 42,
            "merged": True,
            "merged_by": {
                "login": "test-user"
            },
            "title": "Test PR",
        },
        "repository": {
            "full_name": "owner/repo"
        }
    }
    
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Generate signature
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Send webhook
    try:
        req = urllib.request.Request(
            f"http://localhost:{port}/webhook",
            data=payload_bytes,
            headers={
                'Content-Type': 'application/json',
                'X-GitHub-Event': 'pull_request',
                'X-Hub-Signature-256': f'sha256={signature}',
            }
        )
        
        response = urllib.request.urlopen(req)
        print(f"✅ Webhook sent successfully")
        print(f"   Response code: {response.getcode()}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to send webhook: {e}")
        return False


def main():
    """Main function demonstrating webhook setup"""
    
    print("=" * 60)
    print("Webhook Setup Examples")
    print("=" * 60)
    
    # Show setup instructions for all platforms
    github_config = setup_github_webhook()
    gitlab_config = setup_gitlab_webhook()
    bitbucket_config = setup_bitbucket_webhook()
    
    # Use GitHub for demonstration
    if not github_config:
        print("\n❌ Cannot proceed without GITHUB_TOKEN")
        print("   Set it with: export GITHUB_TOKEN='your-token'")
        return
    
    # Create PR service
    print("\n" + "=" * 60)
    print("Initializing PR Service")
    print("=" * 60)
    
    try:
        pr_service = PRService(github_config)
        print("✅ PR Service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize PR Service: {e}")
        return
    
    # Create webhook handlers
    on_pr_merged, on_ci_status_changed = create_webhook_handlers(pr_service)
    
    # Start webhook server
    webhook_handler = start_webhook_server(
        github_config,
        on_pr_merged,
        on_ci_status_changed
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Test health endpoint
    test_webhook_health(github_config.webhook.port)
    
    # Simulate webhook (optional)
    print("\n" + "=" * 60)
    print("Testing Webhook (Optional)")
    print("=" * 60)
    print("Simulating a GitHub PR merge webhook...")
    
    simulate_github_webhook(
        port=github_config.webhook.port,
        secret=github_config.webhook.secret
    )
    
    # Keep server running
    print("\n" + "=" * 60)
    print("Webhook Server Running")
    print("=" * 60)
    print(f"Server is listening on port {github_config.webhook.port}")
    print("Configure your Git host webhook to point to:")
    print(f"  http://your-server:{github_config.webhook.port}/webhook")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down webhook server...")
        webhook_handler.stop()
        print("✅ Server stopped")
    
    print("\n" + "=" * 60)
    print("Webhook Setup Complete")
    print("=" * 60)
    print("Next steps:")
    print("1. Deploy this script to your server")
    print("2. Configure your Git host webhook")
    print("3. Test with a real PR merge or CI event")
    print("4. Monitor logs for webhook events")


if __name__ == "__main__":
    main()

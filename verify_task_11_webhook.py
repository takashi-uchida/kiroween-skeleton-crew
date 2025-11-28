#!/usr/bin/env python3
"""
Verification script for Task 11: Webhook Handler

This script verifies that the webhook handler implementation is working correctly.
"""

import sys
import time
import hmac
import hashlib
import json
import requests
from threading import Thread

from necrocode.review_pr_service.config import PRServiceConfig, GitHostType, WebhookConfig
from necrocode.review_pr_service.webhook_handler import WebhookHandler, WebhookEvent


def verify_webhook_handler():
    """Verify webhook handler functionality"""
    print("=" * 70)
    print("Task 11: Webhook Handler Verification")
    print("=" * 70)
    
    # Track callback invocations
    events_received = []
    
    def on_pr_merged(event: WebhookEvent):
        """Handle PR merge events"""
        print(f"\n✅ PR Merged callback invoked!")
        print(f"   PR #{event.pr_number}")
        print(f"   Repository: {event.repository}")
        print(f"   Merged by: {event.merged_by}")
        events_received.append(("pr_merged", event))
    
    def on_ci_status(event: WebhookEvent):
        """Handle CI status events"""
        print(f"\n✅ CI Status callback invoked!")
        print(f"   Status: {event.ci_status.value}")
        print(f"   PR #{event.pr_number}")
        events_received.append(("ci_status", event))
    
    # Configure webhook handler
    print("\n1. Configuring webhook handler...")
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="test-token",
        webhook=WebhookConfig(
            enabled=True,
            port=8765,  # Use non-standard port for testing
            secret="test-secret-key",
            verify_signature=True,
            async_processing=True
        )
    )
    print("   ✅ Configuration created")
    
    # Create webhook handler
    print("\n2. Creating webhook handler...")
    webhook_handler = WebhookHandler(
        config=config,
        on_pr_merged=on_pr_merged,
        on_ci_status_changed=on_ci_status
    )
    print("   ✅ Webhook handler created")
    
    # Start webhook server
    print("\n3. Starting webhook server...")
    webhook_handler.start()
    time.sleep(1)  # Give server time to start
    print("   ✅ Server started on port 8765")
    
    try:
        # Test health endpoint
        print("\n4. Testing health endpoint...")
        response = requests.get("http://localhost:8765/health", timeout=5)
        if response.status_code == 200 and response.json().get("status") == "healthy":
            print("   ✅ Health check passed")
        else:
            print("   ❌ Health check failed")
            return False
        
        # Test GitHub PR merged webhook
        print("\n5. Testing GitHub PR merged webhook...")
        payload = {
            "action": "closed",
            "pull_request": {
                "id": 12345,
                "number": 42,
                "merged": True,
                "merged_by": {
                    "login": "testuser"
                }
            },
            "repository": {
                "full_name": "owner/repo"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = hmac.new(
            b"test-secret-key",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        response = requests.post(
            "http://localhost:8765/webhook",
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": f"sha256={signature}"
            },
            timeout=5
        )
        
        if response.status_code == 202:
            print("   ✅ Webhook accepted (202)")
            time.sleep(0.5)  # Wait for async processing
            
            if len(events_received) > 0 and events_received[-1][0] == "pr_merged":
                print("   ✅ PR merged event processed")
            else:
                print("   ❌ PR merged event not processed")
                return False
        else:
            print(f"   ❌ Webhook rejected ({response.status_code})")
            return False
        
        # Test GitHub CI status webhook
        print("\n6. Testing GitHub CI status webhook...")
        payload = {
            "state": "success",
            "sha": "abc123def456",
            "repository": {
                "full_name": "owner/repo"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = hmac.new(
            b"test-secret-key",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        response = requests.post(
            "http://localhost:8765/webhook",
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "status",
                "X-Hub-Signature-256": f"sha256={signature}"
            },
            timeout=5
        )
        
        if response.status_code == 202:
            print("   ✅ Webhook accepted (202)")
            time.sleep(0.5)  # Wait for async processing
            
            if len(events_received) > 1 and events_received[-1][0] == "ci_status":
                print("   ✅ CI status event processed")
            else:
                print("   ❌ CI status event not processed")
                return False
        else:
            print(f"   ❌ Webhook rejected ({response.status_code})")
            return False
        
        # Test invalid signature
        print("\n7. Testing invalid signature rejection...")
        payload = {"test": "data"}
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        response = requests.post(
            "http://localhost:8765/webhook",
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": "sha256=invalid_signature"
            },
            timeout=5
        )
        
        if response.status_code == 401:
            print("   ✅ Invalid signature rejected (401)")
        else:
            print(f"   ❌ Invalid signature not rejected ({response.status_code})")
            return False
        
        # Test dynamic handler registration
        print("\n8. Testing dynamic handler registration...")
        new_events = []
        
        def new_handler(event):
            new_events.append(event)
        
        webhook_handler.register_pr_merged_handler(new_handler)
        
        # Send another PR merged event
        payload = {
            "action": "closed",
            "pull_request": {
                "id": 67890,
                "number": 99,
                "merged": True,
                "merged_by": {"login": "newuser"}
            },
            "repository": {"full_name": "owner/repo"}
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = hmac.new(
            b"test-secret-key",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        response = requests.post(
            "http://localhost:8765/webhook",
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": f"sha256={signature}"
            },
            timeout=5
        )
        
        time.sleep(0.5)
        
        if len(new_events) > 0:
            print("   ✅ Dynamic handler invoked")
        else:
            print("   ❌ Dynamic handler not invoked")
            return False
        
        print("\n" + "=" * 70)
        print("✅ All webhook handler tests passed!")
        print("=" * 70)
        
        print("\n📊 Summary:")
        print(f"   - Total events received: {len(events_received)}")
        print(f"   - PR merged events: {sum(1 for e in events_received if e[0] == 'pr_merged')}")
        print(f"   - CI status events: {sum(1 for e in events_received if e[0] == 'ci_status')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Stop webhook server
        print("\n9. Stopping webhook server...")
        webhook_handler.stop()
        time.sleep(0.5)
        print("   ✅ Server stopped")


if __name__ == "__main__":
    try:
        success = verify_webhook_handler()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

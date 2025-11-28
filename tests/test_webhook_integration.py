"""
Integration tests for WebhookHandler with actual webhook delivery.

These tests verify webhook reception and processing with real webhook payloads.
They can be run in two modes:

1. Mock mode (default): Uses simulated webhook requests
2. Live mode: Requires actual webhook setup with Git host

For live mode, set environment variables:
- WEBHOOK_TEST_MODE=live
- WEBHOOK_SECRET: Webhook secret configured in Git host
- WEBHOOK_PORT: Port to listen on (default: 8080)

The tests will start a webhook server and wait for events from the Git host.
You'll need to manually trigger events (create PR, merge PR, etc.) during the test.
"""

import os
import pytest
import asyncio
import json
import hmac
import hashlib
import time
from datetime import datetime
from typing import List
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from necrocode.review_pr_service.webhook_handler import (
    WebhookHandler,
    WebhookEvent,
    WebhookEventType
)
from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    WebhookConfig
)
from necrocode.review_pr_service.models import CIStatus


# Test mode: 'mock' or 'live'
TEST_MODE = os.getenv("WEBHOOK_TEST_MODE", "mock")


@pytest.fixture
def webhook_secret():
    """Get webhook secret from environment or use default"""
    return os.getenv("WEBHOOK_SECRET", "test_secret_key_12345")


@pytest.fixture
def webhook_port():
    """Get webhook port from environment or use default"""
    return int(os.getenv("WEBHOOK_PORT", "8080"))


@pytest.fixture
def github_webhook_config(webhook_secret, webhook_port):
    """Create GitHub webhook configuration"""
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="dummy",
        webhook=WebhookConfig(
            enabled=True,
            port=webhook_port,
            secret=webhook_secret,
        )
    )


@pytest.fixture
def gitlab_webhook_config(webhook_secret, webhook_port):
    """Create GitLab webhook configuration"""
    return PRServiceConfig(
        git_host_type=GitHostType.GITLAB,
        repository="12345",
        api_token="dummy",
        webhook=WebhookConfig(
            enabled=True,
            port=webhook_port,
            secret=webhook_secret,
        )
    )


@pytest.fixture
def bitbucket_webhook_config(webhook_secret, webhook_port):
    """Create Bitbucket webhook configuration"""
    return PRServiceConfig(
        git_host_type=GitHostType.BITBUCKET,
        repository="workspace/repo",
        api_token="dummy",
        webhook=WebhookConfig(
            enabled=True,
            port=webhook_port,
            secret=webhook_secret,
        )
    )


class EventCollector:
    """Helper class to collect webhook events during tests"""
    
    def __init__(self):
        self.events: List[WebhookEvent] = []
        self.pr_merged_events: List[WebhookEvent] = []
        self.ci_status_events: List[WebhookEvent] = []
    
    def on_pr_merged(self, event: WebhookEvent):
        """Callback for PR merged events"""
        self.events.append(event)
        self.pr_merged_events.append(event)
    
    def on_ci_status_changed(self, event: WebhookEvent):
        """Callback for CI status change events"""
        self.events.append(event)
        self.ci_status_events.append(event)
    
    def clear(self):
        """Clear all collected events"""
        self.events.clear()
        self.pr_merged_events.clear()
        self.ci_status_events.clear()


class TestGitHubWebhookIntegration:
    """Integration tests for GitHub webhooks"""
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_github_pr_merged_webhook(self, github_webhook_config):
        """Test receiving GitHub PR merged webhook"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=github_webhook_config,
            on_pr_merged=collector.on_pr_merged,
            on_ci_status_changed=collector.on_ci_status_changed
        )
        
        # Start webhook server
        handler.start()
        
        try:
            # Wait for server to start
            await asyncio.sleep(0.5)
            
            # Simulate webhook delivery
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
            
            # Send webhook request
            await self._send_github_webhook(
                handler,
                event_type="pull_request",
                payload=payload,
                secret=github_webhook_config.webhook.secret
            )
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Verify event was received and processed
            assert len(collector.pr_merged_events) == 1
            event = collector.pr_merged_events[0]
            assert event.event_type == WebhookEventType.PR_MERGED
            assert event.pr_number == 42
            assert event.merged_by == "testuser"
            assert event.repository == "owner/repo"
            
            print(f"✓ Received and processed GitHub PR merged webhook")
            
        finally:
            handler.stop()
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_github_ci_status_webhook(self, github_webhook_config):
        """Test receiving GitHub CI status webhook"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=github_webhook_config,
            on_pr_merged=collector.on_pr_merged,
            on_ci_status_changed=collector.on_ci_status_changed
        )
        
        handler.start()
        
        try:
            await asyncio.sleep(0.5)
            
            # Simulate CI status webhook
            payload = {
                "state": "success",
                "sha": "abc123def456",
                "repository": {
                    "full_name": "owner/repo"
                }
            }
            
            await self._send_github_webhook(
                handler,
                event_type="status",
                payload=payload,
                secret=github_webhook_config.webhook.secret
            )
            
            await asyncio.sleep(0.5)
            
            # Verify event was received
            assert len(collector.ci_status_events) == 1
            event = collector.ci_status_events[0]
            assert event.event_type == WebhookEventType.CI_STATUS_CHANGED
            assert event.ci_status == CIStatus.SUCCESS
            
            print(f"✓ Received and processed GitHub CI status webhook")
            
        finally:
            handler.stop()
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_github_webhook_signature_verification(self, github_webhook_config):
        """Test GitHub webhook signature verification"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=github_webhook_config,
            on_pr_merged=collector.on_pr_merged,
        )
        
        handler.start()
        
        try:
            await asyncio.sleep(0.5)
            
            payload = {
                "action": "closed",
                "pull_request": {"id": 123, "number": 1, "merged": True},
                "repository": {"full_name": "owner/repo"}
            }
            
            # Test with invalid signature
            response = await self._send_github_webhook(
                handler,
                event_type="pull_request",
                payload=payload,
                secret="wrong_secret"
            )
            
            # Should be rejected
            assert response.status == 401
            assert len(collector.events) == 0
            
            print(f"✓ Invalid signature correctly rejected")
            
            # Test with valid signature
            response = await self._send_github_webhook(
                handler,
                event_type="pull_request",
                payload=payload,
                secret=github_webhook_config.webhook.secret
            )
            
            await asyncio.sleep(0.5)
            
            # Should be accepted
            assert response.status == 202
            assert len(collector.events) == 1
            
            print(f"✓ Valid signature correctly accepted")
            
        finally:
            handler.stop()
    
    async def _send_github_webhook(
        self,
        handler: WebhookHandler,
        event_type: str,
        payload: dict,
        secret: str
    ):
        """Helper to send GitHub webhook request"""
        import aiohttp
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Generate signature
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-GitHub-Event': event_type,
            'X-Hub-Signature-256': f'sha256={signature}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://localhost:{handler.webhook_port}/webhook',
                data=payload_bytes,
                headers=headers
            ) as response:
                return response


class TestGitLabWebhookIntegration:
    """Integration tests for GitLab webhooks"""
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_gitlab_merge_request_webhook(self, gitlab_webhook_config):
        """Test receiving GitLab merge request webhook"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=gitlab_webhook_config,
            on_pr_merged=collector.on_pr_merged,
        )
        
        handler.start()
        
        try:
            await asyncio.sleep(0.5)
            
            payload = {
                "object_attributes": {
                    "action": "merge",
                    "iid": 42
                },
                "project": {
                    "path_with_namespace": "group/project"
                },
                "user": {
                    "username": "testuser"
                }
            }
            
            await self._send_gitlab_webhook(
                handler,
                event_type="Merge Request Hook",
                payload=payload,
                token=gitlab_webhook_config.webhook.secret
            )
            
            await asyncio.sleep(0.5)
            
            # Verify event was received
            assert len(collector.pr_merged_events) == 1
            event = collector.pr_merged_events[0]
            assert event.event_type == WebhookEventType.PR_MERGED
            assert event.pr_number == 42
            assert event.merged_by == "testuser"
            
            print(f"✓ Received and processed GitLab MR webhook")
            
        finally:
            handler.stop()
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_gitlab_pipeline_webhook(self, gitlab_webhook_config):
        """Test receiving GitLab pipeline webhook"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=gitlab_webhook_config,
            on_ci_status_changed=collector.on_ci_status_changed,
        )
        
        handler.start()
        
        try:
            await asyncio.sleep(0.5)
            
            payload = {
                "object_attributes": {
                    "status": "success"
                },
                "merge_request": {
                    "iid": 42
                },
                "project": {
                    "path_with_namespace": "group/project"
                }
            }
            
            await self._send_gitlab_webhook(
                handler,
                event_type="Pipeline Hook",
                payload=payload,
                token=gitlab_webhook_config.webhook.secret
            )
            
            await asyncio.sleep(0.5)
            
            # Verify event was received
            assert len(collector.ci_status_events) == 1
            event = collector.ci_status_events[0]
            assert event.event_type == WebhookEventType.CI_STATUS_CHANGED
            assert event.ci_status == CIStatus.SUCCESS
            
            print(f"✓ Received and processed GitLab pipeline webhook")
            
        finally:
            handler.stop()
    
    async def _send_gitlab_webhook(
        self,
        handler: WebhookHandler,
        event_type: str,
        payload: dict,
        token: str
    ):
        """Helper to send GitLab webhook request"""
        import aiohttp
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        headers = {
            'X-Gitlab-Event': event_type,
            'X-Gitlab-Token': token,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://localhost:{handler.webhook_port}/webhook',
                data=payload_bytes,
                headers=headers
            ) as response:
                return response


class TestBitbucketWebhookIntegration:
    """Integration tests for Bitbucket webhooks"""
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_bitbucket_pr_merged_webhook(self, bitbucket_webhook_config):
        """Test receiving Bitbucket PR merged webhook"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=bitbucket_webhook_config,
            on_pr_merged=collector.on_pr_merged,
        )
        
        handler.start()
        
        try:
            await asyncio.sleep(0.5)
            
            payload = {
                "pullrequest": {
                    "id": 42,
                    "closed_by": {
                        "username": "testuser"
                    }
                },
                "repository": {
                    "full_name": "workspace/repo"
                }
            }
            
            await self._send_bitbucket_webhook(
                handler,
                event_type="pullrequest:fulfilled",
                payload=payload,
                secret=bitbucket_webhook_config.webhook.secret
            )
            
            await asyncio.sleep(0.5)
            
            # Verify event was received
            assert len(collector.pr_merged_events) == 1
            event = collector.pr_merged_events[0]
            assert event.event_type == WebhookEventType.PR_MERGED
            assert event.pr_number == 42
            assert event.merged_by == "testuser"
            
            print(f"✓ Received and processed Bitbucket PR webhook")
            
        finally:
            handler.stop()
    
    async def _send_bitbucket_webhook(
        self,
        handler: WebhookHandler,
        event_type: str,
        payload: dict,
        secret: str
    ):
        """Helper to send Bitbucket webhook request"""
        import aiohttp
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Generate signature
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-Event-Key': event_type,
            'X-Hub-Signature': f'sha256={signature}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://localhost:{handler.webhook_port}/webhook',
                data=payload_bytes,
                headers=headers
            ) as response:
                return response


class TestWebhookServerLifecycle:
    """Test webhook server lifecycle management"""
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_server_start_stop(self, github_webhook_config):
        """Test starting and stopping webhook server"""
        handler = WebhookHandler(config=github_webhook_config)
        
        # Start server
        handler.start()
        await asyncio.sleep(0.5)
        
        # Verify server is running
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'http://localhost:{handler.webhook_port}/health'
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "healthy"
        
        print(f"✓ Server started successfully")
        
        # Stop server
        handler.stop()
        await asyncio.sleep(0.5)
        
        # Verify server is stopped
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'http://localhost:{handler.webhook_port}/health',
                    timeout=aiohttp.ClientTimeout(total=1)
                ) as response:
                    pytest.fail("Server should be stopped")
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass  # Expected
        
        print(f"✓ Server stopped successfully")
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_multiple_webhooks_concurrent(self, github_webhook_config):
        """Test handling multiple concurrent webhook requests"""
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=github_webhook_config,
            on_pr_merged=collector.on_pr_merged,
            on_ci_status_changed=collector.on_ci_status_changed
        )
        
        handler.start()
        
        try:
            await asyncio.sleep(0.5)
            
            # Send multiple webhooks concurrently
            tasks = []
            
            for i in range(5):
                payload = {
                    "action": "closed",
                    "pull_request": {
                        "id": 1000 + i,
                        "number": 10 + i,
                        "merged": True,
                        "merged_by": {"login": f"user{i}"}
                    },
                    "repository": {"full_name": "owner/repo"}
                }
                
                task = self._send_github_webhook(
                    handler,
                    event_type="pull_request",
                    payload=payload,
                    secret=github_webhook_config.webhook.secret
                )
                tasks.append(task)
            
            # Wait for all requests to complete
            responses = await asyncio.gather(*tasks)
            
            # Verify all were accepted
            for response in responses:
                assert response.status == 202
            
            # Wait for processing
            await asyncio.sleep(1.0)
            
            # Verify all events were processed
            assert len(collector.pr_merged_events) == 5
            
            print(f"✓ Processed 5 concurrent webhooks successfully")
            
        finally:
            handler.stop()
    
    async def _send_github_webhook(
        self,
        handler: WebhookHandler,
        event_type: str,
        payload: dict,
        secret: str
    ):
        """Helper to send GitHub webhook request"""
        import aiohttp
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-GitHub-Event': event_type,
            'X-Hub-Signature-256': f'sha256={signature}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://localhost:{handler.webhook_port}/webhook',
                data=payload_bytes,
                headers=headers
            ) as response:
                return response


@pytest.mark.skipif(
    TEST_MODE != "live",
    reason="Live webhook tests require WEBHOOK_TEST_MODE=live"
)
class TestLiveWebhookDelivery:
    """
    Live webhook delivery tests.
    
    These tests start a webhook server and wait for actual webhook
    deliveries from the Git host. You need to manually trigger events
    (create PR, merge PR, etc.) during the test.
    """
    
    @pytest.mark.integration
    @pytest.mark.webhook
    @pytest.mark.live
    def test_live_github_webhook_delivery(self, github_webhook_config):
        """
        Test receiving live GitHub webhooks.
        
        Instructions:
        1. Configure webhook in GitHub repository settings
        2. Set webhook URL to http://your-server:{port}/webhook
        3. Set webhook secret to match WEBHOOK_SECRET env var
        4. Run this test
        5. Trigger events in GitHub (create/merge PR, etc.)
        6. Test will wait 60 seconds for events
        """
        collector = EventCollector()
        
        handler = WebhookHandler(
            config=github_webhook_config,
            on_pr_merged=collector.on_pr_merged,
            on_ci_status_changed=collector.on_ci_status_changed
        )
        
        print(f"\n{'='*60}")
        print(f"Webhook server listening on port {handler.webhook_port}")
        print(f"Configure GitHub webhook to: http://your-server:{handler.webhook_port}/webhook")
        print(f"Webhook secret: {github_webhook_config.webhook.secret}")
        print(f"Waiting 60 seconds for webhook deliveries...")
        print(f"Trigger events in GitHub now!")
        print(f"{'='*60}\n")
        
        handler.start()
        
        try:
            # Wait for webhook deliveries
            time.sleep(60)
            
            # Report results
            print(f"\n{'='*60}")
            print(f"Received {len(collector.events)} total events:")
            print(f"  - PR merged: {len(collector.pr_merged_events)}")
            print(f"  - CI status: {len(collector.ci_status_events)}")
            
            for event in collector.events:
                print(f"\nEvent: {event.event_type.value}")
                print(f"  PR: #{event.pr_number}")
                print(f"  Repository: {event.repository}")
                if event.merged_by:
                    print(f"  Merged by: {event.merged_by}")
                if event.ci_status:
                    print(f"  CI Status: {event.ci_status.value}")
            
            print(f"{'='*60}\n")
            
            # Verify at least one event was received
            assert len(collector.events) > 0, "No webhook events received"
            
        finally:
            handler.stop()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration and webhook"])

"""
Tests for WebhookHandler

Tests webhook endpoint, signature verification, event parsing, and async processing.
"""

import pytest
import json
import hmac
import hashlib
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    WebhookConfig
)
from necrocode.review_pr_service.webhook_handler import (
    WebhookHandler,
    WebhookEvent,
    WebhookEventType
)
from necrocode.review_pr_service.models import CIStatus
from necrocode.review_pr_service.exceptions import WebhookSignatureError


class TestWebhookHandler(AioHTTPTestCase):
    """Test WebhookHandler functionality"""
    
    async def get_application(self):
        """Create test application"""
        self.config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(
                enabled=True,
                port=8080,
                secret="test_secret_key"
            )
        )
        
        self.pr_merged_called = False
        self.ci_status_called = False
        self.last_event = None
        
        def on_pr_merged(event):
            self.pr_merged_called = True
            self.last_event = event
        
        def on_ci_status(event):
            self.ci_status_called = True
            self.last_event = event
        
        self.handler = WebhookHandler(
            config=self.config,
            on_pr_merged=on_pr_merged,
            on_ci_status_changed=on_ci_status
        )
        
        # Create app manually for testing
        app = web.Application()
        app.router.add_post('/webhook', self.handler._handle_webhook)
        app.router.add_get('/health', self.handler._handle_health)
        
        return app
    
    def _generate_github_signature(self, payload: bytes) -> str:
        """Generate GitHub webhook signature"""
        signature = hmac.new(
            self.config.webhook.secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        resp = await self.client.get('/health')
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "healthy"
    
    @unittest_run_loop
    async def test_github_pr_merged_event(self):
        """Test GitHub PR merged event"""
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
        signature = self._generate_github_signature(payload_bytes)
        
        resp = await self.client.post(
            '/webhook',
            data=payload_bytes,
            headers={
                'X-GitHub-Event': 'pull_request',
                'X-Hub-Signature-256': signature,
                'Content-Type': 'application/json'
            }
        )
        
        assert resp.status == 202
        data = await resp.json()
        assert data["status"] == "accepted"
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # Verify callback was called
        assert self.pr_merged_called
        assert self.last_event is not None
        assert self.last_event.event_type == WebhookEventType.PR_MERGED
        assert self.last_event.pr_number == 42
        assert self.last_event.merged_by == "testuser"
    
    @unittest_run_loop
    async def test_github_ci_status_event(self):
        """Test GitHub CI status change event"""
        payload = {
            "state": "success",
            "sha": "abc123",
            "repository": {
                "full_name": "owner/repo"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_github_signature(payload_bytes)
        
        resp = await self.client.post(
            '/webhook',
            data=payload_bytes,
            headers={
                'X-GitHub-Event': 'status',
                'X-Hub-Signature-256': signature,
                'Content-Type': 'application/json'
            }
        )
        
        assert resp.status == 202
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # Verify callback was called
        assert self.ci_status_called
        assert self.last_event.event_type == WebhookEventType.CI_STATUS_CHANGED
        assert self.last_event.ci_status == CIStatus.SUCCESS
    
    @unittest_run_loop
    async def test_invalid_signature(self):
        """Test webhook with invalid signature"""
        payload = {"test": "data"}
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        resp = await self.client.post(
            '/webhook',
            data=payload_bytes,
            headers={
                'X-GitHub-Event': 'pull_request',
                'X-Hub-Signature-256': 'sha256=invalid_signature',
                'Content-Type': 'application/json'
            }
        )
        
        assert resp.status == 401
        data = await resp.json()
        assert "error" in data
    
    @unittest_run_loop
    async def test_missing_signature(self):
        """Test webhook without signature"""
        payload = {"test": "data"}
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        resp = await self.client.post(
            '/webhook',
            data=payload_bytes,
            headers={
                'X-GitHub-Event': 'pull_request',
                'Content-Type': 'application/json'
            }
        )
        
        assert resp.status == 401


class TestWebhookSignatureVerification:
    """Test signature verification for different Git hosts"""
    
    def test_github_signature_verification(self):
        """Test GitHub signature verification"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="test_secret")
        )
        handler = WebhookHandler(config)
        
        payload = b'{"test": "data"}'
        signature = hmac.new(
            b"test_secret",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert handler._verify_github_signature(payload, f"sha256={signature}")
        assert not handler._verify_github_signature(payload, "sha256=invalid")
    
    def test_gitlab_signature_verification(self):
        """Test GitLab token verification"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITLAB,
            webhook=WebhookConfig(secret="test_token")
        )
        handler = WebhookHandler(config)
        
        assert handler._verify_gitlab_signature("test_token")
        assert not handler._verify_gitlab_signature("wrong_token")
    
    def test_no_secret_skips_verification(self):
        """Test that missing secret skips verification"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret=None)
        )
        handler = WebhookHandler(config)
        
        # Should return True when no secret is configured
        assert handler._verify_signature(b"any_payload", None)


class TestWebhookEventParsing:
    """Test event parsing for different Git hosts"""
    
    def test_parse_github_pr_merged(self):
        """Test parsing GitHub PR merged event"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        headers = {"X-GitHub-Event": "pull_request"}
        payload = {
            "action": "closed",
            "pull_request": {
                "id": 123,
                "number": 42,
                "merged": True,
                "merged_by": {"login": "user"}
            },
            "repository": {"full_name": "owner/repo"}
        }
        
        event = handler._parse_github_event(headers, payload)
        
        assert event.event_type == WebhookEventType.PR_MERGED
        assert event.pr_number == 42
        assert event.merged_by == "user"
        assert event.repository == "owner/repo"
    
    def test_parse_github_pr_closed_not_merged(self):
        """Test parsing GitHub PR closed (not merged) event"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        headers = {"X-GitHub-Event": "pull_request"}
        payload = {
            "action": "closed",
            "pull_request": {
                "id": 123,
                "number": 42,
                "merged": False
            },
            "repository": {"full_name": "owner/repo"}
        }
        
        event = handler._parse_github_event(headers, payload)
        
        assert event.event_type == WebhookEventType.PR_CLOSED
        assert event.pr_number == 42
    
    def test_parse_github_ci_status(self):
        """Test parsing GitHub CI status event"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        headers = {"X-GitHub-Event": "status"}
        payload = {
            "state": "success",
            "sha": "abc123",
            "repository": {"full_name": "owner/repo"}
        }
        
        event = handler._parse_github_event(headers, payload)
        
        assert event.event_type == WebhookEventType.CI_STATUS_CHANGED
        assert event.ci_status == CIStatus.SUCCESS
    
    def test_parse_gitlab_merge_request(self):
        """Test parsing GitLab merge request event"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITLAB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        headers = {"X-Gitlab-Event": "Merge Request Hook"}
        payload = {
            "object_attributes": {
                "action": "merge",
                "iid": 42
            },
            "project": {"path_with_namespace": "group/project"},
            "user": {"username": "user"}
        }
        
        event = handler._parse_gitlab_event(headers, payload)
        
        assert event.event_type == WebhookEventType.PR_MERGED
        assert event.pr_number == 42
        assert event.merged_by == "user"
    
    def test_parse_gitlab_pipeline(self):
        """Test parsing GitLab pipeline event"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITLAB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        headers = {"X-Gitlab-Event": "Pipeline Hook"}
        payload = {
            "object_attributes": {"status": "success"},
            "merge_request": {"iid": 42},
            "project": {"path_with_namespace": "group/project"}
        }
        
        event = handler._parse_gitlab_event(headers, payload)
        
        assert event.event_type == WebhookEventType.CI_STATUS_CHANGED
        assert event.ci_status == CIStatus.SUCCESS
    
    def test_parse_bitbucket_pr_merged(self):
        """Test parsing Bitbucket PR merged event"""
        config = PRServiceConfig(
            git_host_type=GitHostType.BITBUCKET,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        headers = {"X-Event-Key": "pullrequest:fulfilled"}
        payload = {
            "pullrequest": {
                "id": 42,
                "closed_by": {"username": "user"}
            },
            "repository": {"full_name": "owner/repo"}
        }
        
        event = handler._parse_bitbucket_event(headers, payload)
        
        assert event.event_type == WebhookEventType.PR_MERGED
        assert event.pr_number == 42
        assert event.merged_by == "user"


class TestWebhookStatusMapping:
    """Test CI status mapping for different Git hosts"""
    
    def test_github_status_mapping(self):
        """Test GitHub status to CIStatus mapping"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        assert handler._map_github_status("success") == CIStatus.SUCCESS
        assert handler._map_github_status("failure") == CIStatus.FAILURE
        assert handler._map_github_status("pending") == CIStatus.PENDING
        assert handler._map_github_status("error") == CIStatus.FAILURE
    
    def test_gitlab_status_mapping(self):
        """Test GitLab status to CIStatus mapping"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITLAB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        assert handler._map_gitlab_status("success") == CIStatus.SUCCESS
        assert handler._map_gitlab_status("failed") == CIStatus.FAILURE
        assert handler._map_gitlab_status("running") == CIStatus.PENDING
        assert handler._map_gitlab_status("canceled") == CIStatus.FAILURE
    
    def test_bitbucket_status_mapping(self):
        """Test Bitbucket status to CIStatus mapping"""
        config = PRServiceConfig(
            git_host_type=GitHostType.BITBUCKET,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        assert handler._map_bitbucket_status("SUCCESSFUL") == CIStatus.SUCCESS
        assert handler._map_bitbucket_status("FAILED") == CIStatus.FAILURE
        assert handler._map_bitbucket_status("INPROGRESS") == CIStatus.PENDING


class TestWebhookHandlerRegistration:
    """Test dynamic handler registration"""
    
    def test_register_pr_merged_handler(self):
        """Test registering PR merged handler"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        called = []
        
        def callback(event):
            called.append(event)
        
        handler.register_pr_merged_handler(callback)
        assert handler._on_pr_merged == callback
    
    def test_register_ci_status_handler(self):
        """Test registering CI status handler"""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            webhook=WebhookConfig(secret="secret")
        )
        handler = WebhookHandler(config)
        
        called = []
        
        def callback(event):
            called.append(event)
        
        handler.register_ci_status_handler(callback)
        assert handler._on_ci_status_changed == callback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

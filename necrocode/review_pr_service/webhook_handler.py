"""
Webhook Handler for Review & PR Service

Provides HTTP server for receiving webhooks from Git hosts (GitHub, GitLab, Bitbucket).
Handles PR merge events and CI status change events with signature verification.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, List
from aiohttp import web
import threading

from necrocode.review_pr_service.config import PRServiceConfig
from necrocode.review_pr_service.exceptions import (
    WebhookError,
    WebhookSignatureError
)
from necrocode.review_pr_service.models import CIStatus, PRState


logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """Webhook event types"""
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    PR_OPENED = "pr_opened"
    CI_STATUS_CHANGED = "ci_status_changed"
    UNKNOWN = "unknown"


@dataclass
class WebhookEvent:
    """Webhook event data"""
    event_type: WebhookEventType
    pr_id: str
    pr_number: int
    repository: str
    payload: Dict[str, Any]
    timestamp: datetime
    ci_status: Optional[CIStatus] = None
    merged_by: Optional[str] = None


class WebhookHandler:
    """
    Webhook handler for Git host events
    
    Provides HTTP server endpoint for receiving webhooks from GitHub, GitLab, and Bitbucket.
    Verifies webhook signatures and processes events asynchronously.
    
    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """
    
    def __init__(
        self,
        config: PRServiceConfig,
        on_pr_merged: Optional[Callable[[WebhookEvent], None]] = None,
        on_ci_status_changed: Optional[Callable[[WebhookEvent], None]] = None
    ):
        """
        Initialize webhook handler
        
        Args:
            config: PR service configuration
            on_pr_merged: Callback for PR merge events
            on_ci_status_changed: Callback for CI status change events
        """
        self.config = config
        self.webhook_secret = config.webhook.secret
        self.webhook_port = config.webhook.port
        self.git_host_type = config.git_host_type.value
        
        # Event handlers
        self._on_pr_merged = on_pr_merged
        self._on_ci_status_changed = on_ci_status_changed
        
        # Server state
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._server_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info(
            f"WebhookHandler initialized for {git_host_type} on port {webhook_port}"
        )
    
    def start(self) -> None:
        """
        Start webhook HTTP server
        
        Requirements: 11.1
        """
        if self._server_thread and self._server_thread.is_alive():
            logger.warning("Webhook server already running")
            return
        
        # Start server in separate thread
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        
        logger.info(f"Webhook server started on port {self.webhook_port}")
    
    def stop(self) -> None:
        """Stop webhook HTTP server"""
        if self._loop and self._runner:
            asyncio.run_coroutine_threadsafe(self._stop_server(), self._loop)
            if self._server_thread:
                self._server_thread.join(timeout=5)
        
        logger.info("Webhook server stopped")
    
    def _run_server(self) -> None:
        """Run aiohttp server in thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        self._app = web.Application()
        self._app.router.add_post('/webhook', self._handle_webhook)
        self._app.router.add_get('/health', self._handle_health)
        
        self._loop.run_until_complete(self._start_server())
        self._loop.run_forever()
    
    async def _start_server(self) -> None:
        """Start aiohttp server"""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, '0.0.0.0', self.webhook_port)
        await self._site.start()
    
    async def _stop_server(self) -> None:
        """Stop aiohttp server"""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        if self._loop:
            self._loop.stop()
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({"status": "healthy"})
    
    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming webhook requests
        
        Requirements: 11.1, 11.5
        """
        try:
            # Read payload
            payload_bytes = await request.read()
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # Verify signature
            signature = request.headers.get(self._get_signature_header())
            if not self._verify_signature(payload_bytes, signature):
                logger.warning("Webhook signature verification failed")
                raise WebhookSignatureError("Invalid webhook signature")
            
            # Parse event
            event = self._parse_event(request.headers, payload)
            
            # Process event asynchronously
            asyncio.create_task(self._process_event(event))
            
            return web.json_response({"status": "accepted"}, status=202)
            
        except WebhookSignatureError as e:
            logger.error(f"Signature verification failed: {e}")
            return web.json_response(
                {"error": "Invalid signature"},
                status=401
            )
        except Exception as e:
            logger.error(f"Webhook processing error: {e}", exc_info=True)
            return web.json_response(
                {"error": "Internal server error"},
                status=500
            )
    
    def _get_signature_header(self) -> str:
        """Get signature header name for git host"""
        headers = {
            "github": "X-Hub-Signature-256",
            "gitlab": "X-Gitlab-Token",
            "bitbucket": "X-Hub-Signature"
        }
        return headers.get(self.git_host_type, "X-Hub-Signature")
    
    def _verify_signature(self, payload: bytes, signature: Optional[str]) -> bool:
        """
        Verify webhook signature
        
        Requirements: 11.2
        """
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True
        
        if not signature:
            return False
        
        if self.git_host_type == "github":
            return self._verify_github_signature(payload, signature)
        elif self.git_host_type == "gitlab":
            return self._verify_gitlab_signature(signature)
        elif self.git_host_type == "bitbucket":
            return self._verify_bitbucket_signature(payload, signature)
        
        return False
    
    def _verify_github_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature (HMAC SHA256)"""
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # GitHub sends "sha256=<signature>"
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _verify_gitlab_signature(self, token: str) -> bool:
        """Verify GitLab webhook token"""
        return hmac.compare_digest(token, self.webhook_secret)
    
    def _verify_bitbucket_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Bitbucket webhook signature (HMAC SHA256)"""
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Bitbucket sends "sha256=<signature>"
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _parse_event(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse webhook event based on git host type"""
        if self.git_host_type == "github":
            return self._parse_github_event(headers, payload)
        elif self.git_host_type == "gitlab":
            return self._parse_gitlab_event(headers, payload)
        elif self.git_host_type == "bitbucket":
            return self._parse_bitbucket_event(headers, payload)
        
        raise WebhookError(f"Unsupported git host: {self.git_host_type}")
    
    def _parse_github_event(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """
        Parse GitHub webhook event
        
        Requirements: 11.3, 11.4
        """
        event_type_header = headers.get("X-GitHub-Event", "")
        
        # PR merged event
        if event_type_header == "pull_request":
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            
            if action == "closed" and pr.get("merged"):
                return WebhookEvent(
                    event_type=WebhookEventType.PR_MERGED,
                    pr_id=str(pr.get("id")),
                    pr_number=pr.get("number"),
                    repository=payload.get("repository", {}).get("full_name"),
                    payload=payload,
                    timestamp=datetime.utcnow(),
                    merged_by=pr.get("merged_by", {}).get("login")
                )
            elif action == "closed":
                return WebhookEvent(
                    event_type=WebhookEventType.PR_CLOSED,
                    pr_id=str(pr.get("id")),
                    pr_number=pr.get("number"),
                    repository=payload.get("repository", {}).get("full_name"),
                    payload=payload,
                    timestamp=datetime.utcnow()
                )
            elif action == "opened":
                return WebhookEvent(
                    event_type=WebhookEventType.PR_OPENED,
                    pr_id=str(pr.get("id")),
                    pr_number=pr.get("number"),
                    repository=payload.get("repository", {}).get("full_name"),
                    payload=payload,
                    timestamp=datetime.utcnow()
                )
        
        # CI status change event
        elif event_type_header == "status" or event_type_header == "check_suite":
            state = payload.get("state") or payload.get("check_suite", {}).get("conclusion")
            ci_status = self._map_github_status(state)
            
            # Get PR number from commit
            commit_sha = payload.get("sha") or payload.get("check_suite", {}).get("head_sha")
            
            return WebhookEvent(
                event_type=WebhookEventType.CI_STATUS_CHANGED,
                pr_id=commit_sha,  # Use commit SHA as identifier
                pr_number=0,  # Will be resolved later
                repository=payload.get("repository", {}).get("full_name"),
                payload=payload,
                timestamp=datetime.utcnow(),
                ci_status=ci_status
            )
        
        return WebhookEvent(
            event_type=WebhookEventType.UNKNOWN,
            pr_id="",
            pr_number=0,
            repository=payload.get("repository", {}).get("full_name", ""),
            payload=payload,
            timestamp=datetime.utcnow()
        )
    
    def _parse_gitlab_event(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse GitLab webhook event"""
        event_type_header = headers.get("X-Gitlab-Event", "")
        
        if event_type_header == "Merge Request Hook":
            action = payload.get("object_attributes", {}).get("action")
            mr = payload.get("object_attributes", {})
            
            if action == "merge":
                return WebhookEvent(
                    event_type=WebhookEventType.PR_MERGED,
                    pr_id=str(mr.get("iid")),
                    pr_number=mr.get("iid"),
                    repository=payload.get("project", {}).get("path_with_namespace"),
                    payload=payload,
                    timestamp=datetime.utcnow(),
                    merged_by=payload.get("user", {}).get("username")
                )
        
        elif event_type_header == "Pipeline Hook":
            status = payload.get("object_attributes", {}).get("status")
            ci_status = self._map_gitlab_status(status)
            
            return WebhookEvent(
                event_type=WebhookEventType.CI_STATUS_CHANGED,
                pr_id=str(payload.get("merge_request", {}).get("iid", "")),
                pr_number=payload.get("merge_request", {}).get("iid", 0),
                repository=payload.get("project", {}).get("path_with_namespace"),
                payload=payload,
                timestamp=datetime.utcnow(),
                ci_status=ci_status
            )
        
        return WebhookEvent(
            event_type=WebhookEventType.UNKNOWN,
            pr_id="",
            pr_number=0,
            repository="",
            payload=payload,
            timestamp=datetime.utcnow()
        )
    
    def _parse_bitbucket_event(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse Bitbucket webhook event"""
        event_type_header = headers.get("X-Event-Key", "")
        
        if event_type_header == "pullrequest:fulfilled":
            pr = payload.get("pullrequest", {})
            return WebhookEvent(
                event_type=WebhookEventType.PR_MERGED,
                pr_id=str(pr.get("id")),
                pr_number=pr.get("id"),
                repository=payload.get("repository", {}).get("full_name"),
                payload=payload,
                timestamp=datetime.utcnow(),
                merged_by=pr.get("closed_by", {}).get("username")
            )
        
        elif "build" in event_type_header:
            status = payload.get("commit_status", {}).get("state")
            ci_status = self._map_bitbucket_status(status)
            
            return WebhookEvent(
                event_type=WebhookEventType.CI_STATUS_CHANGED,
                pr_id=payload.get("commit_status", {}).get("commit", {}).get("hash", ""),
                pr_number=0,
                repository=payload.get("repository", {}).get("full_name"),
                payload=payload,
                timestamp=datetime.utcnow(),
                ci_status=ci_status
            )
        
        return WebhookEvent(
            event_type=WebhookEventType.UNKNOWN,
            pr_id="",
            pr_number=0,
            repository="",
            payload=payload,
            timestamp=datetime.utcnow()
        )
    
    def _map_github_status(self, status: str) -> CIStatus:
        """Map GitHub status to CIStatus"""
        status_map = {
            "pending": CIStatus.PENDING,
            "success": CIStatus.SUCCESS,
            "failure": CIStatus.FAILURE,
            "error": CIStatus.FAILURE,
            "queued": CIStatus.PENDING,
            "in_progress": CIStatus.PENDING,
            "completed": CIStatus.SUCCESS,
        }
        return status_map.get(status, CIStatus.PENDING)
    
    def _map_gitlab_status(self, status: str) -> CIStatus:
        """Map GitLab status to CIStatus"""
        status_map = {
            "pending": CIStatus.PENDING,
            "running": CIStatus.PENDING,
            "success": CIStatus.SUCCESS,
            "failed": CIStatus.FAILURE,
            "canceled": CIStatus.FAILURE,
            "skipped": CIStatus.PENDING,
        }
        return status_map.get(status, CIStatus.PENDING)
    
    def _map_bitbucket_status(self, status: str) -> CIStatus:
        """Map Bitbucket status to CIStatus"""
        status_map = {
            "INPROGRESS": CIStatus.PENDING,
            "SUCCESSFUL": CIStatus.SUCCESS,
            "FAILED": CIStatus.FAILURE,
            "STOPPED": CIStatus.FAILURE,
        }
        return status_map.get(status, CIStatus.PENDING)
    
    async def _process_event(self, event: WebhookEvent) -> None:
        """
        Process webhook event asynchronously
        
        Requirements: 11.5
        """
        try:
            logger.info(
                f"Processing webhook event: {event.event_type.value} "
                f"for PR #{event.pr_number}"
            )
            
            if event.event_type == WebhookEventType.PR_MERGED:
                if self._on_pr_merged:
                    # Run callback in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._on_pr_merged, event)
            
            elif event.event_type == WebhookEventType.CI_STATUS_CHANGED:
                if self._on_ci_status_changed:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._on_ci_status_changed, event)
            
            logger.info(f"Successfully processed event: {event.event_type.value}")
            
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}", exc_info=True)
    
    def register_pr_merged_handler(
        self,
        handler: Callable[[WebhookEvent], None]
    ) -> None:
        """Register callback for PR merge events"""
        self._on_pr_merged = handler
    
    def register_ci_status_handler(
        self,
        handler: Callable[[WebhookEvent], None]
    ) -> None:
        """Register callback for CI status change events"""
        self._on_ci_status_changed = handler

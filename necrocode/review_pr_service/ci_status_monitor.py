"""
CI Status Monitor - Monitors CI/CD status for pull requests.

This module provides the CIStatusMonitor class that polls CI status,
records status changes to Task Registry, and handles CI success/failure events.
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from threading import Thread, Event

from necrocode.review_pr_service.config import PRServiceConfig
from necrocode.review_pr_service.models import PullRequest, CIStatus
from necrocode.review_pr_service.git_host_client import GitHostClient
from necrocode.review_pr_service.exceptions import PRServiceError
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import TaskEvent, EventType


logger = logging.getLogger(__name__)


class CIStatusMonitor:
    """
    CI Status Monitor for pull requests.
    
    Monitors CI/CD pipeline status for PRs, records status changes
    to Task Registry, and triggers callbacks on status changes.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    
    def __init__(
        self,
        git_host_client: GitHostClient,
        config: PRServiceConfig,
        task_registry: Optional[TaskRegistry] = None
    ):
        """
        Initialize CI Status Monitor.
        
        Args:
            git_host_client: Git host client for fetching CI status
            config: PR Service configuration
            task_registry: Task Registry for recording events (optional)
            
        Requirements: 4.1
        """
        self.git_host_client = git_host_client
        self.config = config
        self.task_registry = task_registry
        
        # Monitoring state
        self._monitoring_threads: Dict[str, Thread] = {}
        self._stop_events: Dict[str, Event] = {}
        self._last_status: Dict[str, CIStatus] = {}
        
        # Callbacks for status changes
        self._on_success_callbacks: Dict[str, Callable] = {}
        self._on_failure_callbacks: Dict[str, Callable] = {}
        self._on_status_change_callbacks: Dict[str, Callable] = {}
        
        logger.info(
            f"CIStatusMonitor initialized: "
            f"polling_interval={config.ci.polling_interval}s, "
            f"timeout={config.ci.timeout}s"
        )
    
    def monitor_ci_status(
        self,
        pr: PullRequest,
        on_success: Optional[Callable[[PullRequest, CIStatus], None]] = None,
        on_failure: Optional[Callable[[PullRequest, CIStatus], None]] = None,
        on_status_change: Optional[Callable[[PullRequest, CIStatus, CIStatus], None]] = None
    ) -> CIStatus:
        """
        Get current CI status for a pull request.
        
        This is a synchronous method that fetches the current CI status
        without starting background monitoring.
        
        Args:
            pr: PullRequest object
            on_success: Optional callback for CI success
            on_failure: Optional callback for CI failure
            on_status_change: Optional callback for any status change
            
        Returns:
            Current CIStatus
            
        Raises:
            PRServiceError: If status fetch fails
            
        Requirements: 4.1
        """
        try:
            logger.debug(f"Fetching CI status for PR {pr.pr_number}")
            
            # Get CI status from Git host
            ci_status = self.git_host_client.get_ci_status(pr.pr_id)
            
            logger.info(
                f"CI status for PR {pr.pr_number}: {ci_status.value}"
            )
            
            # Check if status changed
            old_status = self._last_status.get(pr.pr_id)
            if old_status and old_status != ci_status:
                logger.info(
                    f"CI status changed for PR {pr.pr_number}: "
                    f"{old_status.value} -> {ci_status.value}"
                )
                
                # Record status change
                self._record_ci_status_change(pr, old_status, ci_status)
                
                # Trigger callbacks
                if on_status_change:
                    on_status_change(pr, old_status, ci_status)
            
            # Update last known status
            self._last_status[pr.pr_id] = ci_status
            
            # Trigger success/failure callbacks
            if ci_status == CIStatus.SUCCESS and on_success:
                on_success(pr, ci_status)
            elif ci_status == CIStatus.FAILURE and on_failure:
                on_failure(pr, ci_status)
            
            return ci_status
        
        except Exception as e:
            logger.error(f"Failed to fetch CI status for PR {pr.pr_number}: {e}")
            raise PRServiceError(f"CI status fetch failed: {e}") from e
    
    def start_monitoring(
        self,
        pr: PullRequest,
        on_success: Optional[Callable[[PullRequest, CIStatus], None]] = None,
        on_failure: Optional[Callable[[PullRequest, CIStatus], None]] = None,
        on_status_change: Optional[Callable[[PullRequest, CIStatus, CIStatus], None]] = None
    ) -> None:
        """
        Start background monitoring of CI status for a PR.
        
        Polls CI status at configured intervals until success, failure,
        or timeout is reached.
        
        Args:
            pr: PullRequest object
            on_success: Optional callback for CI success
            on_failure: Optional callback for CI failure
            on_status_change: Optional callback for any status change
            
        Requirements: 4.3
        """
        if not self.config.ci.enabled:
            logger.debug("CI monitoring is disabled")
            return
        
        # Check if already monitoring this PR
        if pr.pr_id in self._monitoring_threads:
            logger.warning(f"Already monitoring PR {pr.pr_number}")
            return
        
        # Store callbacks
        if on_success:
            self._on_success_callbacks[pr.pr_id] = on_success
        if on_failure:
            self._on_failure_callbacks[pr.pr_id] = on_failure
        if on_status_change:
            self._on_status_change_callbacks[pr.pr_id] = on_status_change
        
        # Create stop event
        stop_event = Event()
        self._stop_events[pr.pr_id] = stop_event
        
        # Start monitoring thread
        thread = Thread(
            target=self._monitor_loop,
            args=(pr, stop_event),
            daemon=True,
            name=f"CI-Monitor-PR-{pr.pr_number}"
        )
        self._monitoring_threads[pr.pr_id] = thread
        thread.start()
        
        logger.info(
            f"Started CI monitoring for PR {pr.pr_number} "
            f"(interval={self.config.ci.polling_interval}s, "
            f"timeout={self.config.ci.timeout}s)"
        )
    
    def stop_monitoring(self, pr_id: str) -> None:
        """
        Stop monitoring CI status for a PR.
        
        Args:
            pr_id: Pull request identifier
            
        Requirements: 4.3
        """
        if pr_id not in self._monitoring_threads:
            logger.debug(f"Not monitoring PR {pr_id}")
            return
        
        # Signal thread to stop
        if pr_id in self._stop_events:
            self._stop_events[pr_id].set()
        
        # Wait for thread to finish (with timeout)
        thread = self._monitoring_threads[pr_id]
        thread.join(timeout=5.0)
        
        # Clean up
        self._monitoring_threads.pop(pr_id, None)
        self._stop_events.pop(pr_id, None)
        self._on_success_callbacks.pop(pr_id, None)
        self._on_failure_callbacks.pop(pr_id, None)
        self._on_status_change_callbacks.pop(pr_id, None)
        
        logger.info(f"Stopped CI monitoring for PR {pr_id}")
    
    def stop_all_monitoring(self) -> None:
        """
        Stop all active monitoring threads.
        
        Requirements: 4.3
        """
        pr_ids = list(self._monitoring_threads.keys())
        for pr_id in pr_ids:
            self.stop_monitoring(pr_id)
        
        logger.info("Stopped all CI monitoring")
    
    def _monitor_loop(self, pr: PullRequest, stop_event: Event) -> None:
        """
        Background monitoring loop for a PR.
        
        Polls CI status at configured intervals until terminal state
        (success/failure) or timeout is reached.
        
        Args:
            pr: PullRequest object
            stop_event: Event to signal loop termination
            
        Requirements: 4.3
        """
        start_time = time.time()
        timeout = self.config.ci.timeout
        interval = self.config.ci.polling_interval
        
        logger.debug(
            f"Starting monitoring loop for PR {pr.pr_number} "
            f"(timeout={timeout}s, interval={interval}s)"
        )
        
        while not stop_event.is_set():
            try:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(
                        f"CI monitoring timeout for PR {pr.pr_number} "
                        f"after {elapsed:.1f}s"
                    )
                    self._record_ci_timeout(pr)
                    break
                
                # Fetch current CI status
                old_status = self._last_status.get(pr.pr_id)
                ci_status = self.git_host_client.get_ci_status(pr.pr_id)
                
                # Update last known status
                self._last_status[pr.pr_id] = ci_status
                
                # Check for status change
                if old_status and old_status != ci_status:
                    logger.info(
                        f"CI status changed for PR {pr.pr_number}: "
                        f"{old_status.value} -> {ci_status.value}"
                    )
                    
                    # Record status change
                    self._record_ci_status_change(pr, old_status, ci_status)
                    
                    # Trigger status change callback
                    callback = self._on_status_change_callbacks.get(pr.pr_id)
                    if callback:
                        try:
                            callback(pr, old_status, ci_status)
                        except Exception as e:
                            logger.error(
                                f"Status change callback failed for PR {pr.pr_number}: {e}"
                            )
                
                # Handle terminal states
                if ci_status == CIStatus.SUCCESS:
                    logger.info(f"CI succeeded for PR {pr.pr_number}")
                    self._handle_ci_success(pr, ci_status)
                    break
                
                elif ci_status == CIStatus.FAILURE:
                    logger.info(f"CI failed for PR {pr.pr_number}")
                    self._handle_ci_failure(pr, ci_status)
                    break
                
                # Wait for next poll (with early exit on stop signal)
                stop_event.wait(interval)
            
            except Exception as e:
                logger.error(
                    f"Error in monitoring loop for PR {pr.pr_number}: {e}"
                )
                # Continue monitoring despite errors
                stop_event.wait(interval)
        
        logger.debug(f"Monitoring loop ended for PR {pr.pr_number}")
    
    def _record_ci_status_change(
        self,
        pr: PullRequest,
        old_status: CIStatus,
        new_status: CIStatus
    ) -> None:
        """
        Record CI status change to Task Registry.
        
        Args:
            pr: PullRequest object
            old_status: Previous CI status
            new_status: New CI status
            
        Requirements: 4.2
        """
        if not self.task_registry:
            logger.debug("Task Registry not configured, skipping status recording")
            return
        
        try:
            # Determine spec_name and task_id from PR metadata
            spec_name = pr.spec_id or "unknown"
            task_id = pr.task_id or pr.pr_id
            
            # Create status change event
            event = TaskEvent(
                event_type=EventType.TASK_UPDATED,
                spec_name=spec_name,
                task_id=task_id,
                timestamp=datetime.now(),
                details={
                    "event": "ci_status_changed",
                    "pr_id": pr.pr_id,
                    "pr_number": pr.pr_number,
                    "pr_url": pr.url,
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                }
            )
            
            # Record event
            self.task_registry.event_store.record_event(event)
            
            logger.debug(
                f"Recorded CI status change for PR {pr.pr_number}: "
                f"{old_status.value} -> {new_status.value}"
            )
        
        except Exception as e:
            logger.error(f"Failed to record CI status change: {e}")
            # Don't raise exception, just log the error
    
    def _handle_ci_success(self, pr: PullRequest, ci_status: CIStatus) -> None:
        """
        Handle CI success event.
        
        Records TaskCompleted event to Task Registry and triggers callback.
        
        Args:
            pr: PullRequest object
            ci_status: CI status (should be SUCCESS)
            
        Requirements: 4.5
        """
        logger.info(f"Handling CI success for PR {pr.pr_number}")
        
        # Record to Task Registry
        if self.task_registry:
            try:
                spec_name = pr.spec_id or "unknown"
                task_id = pr.task_id or pr.pr_id
                
                event = TaskEvent(
                    event_type=EventType.TASK_COMPLETED,
                    spec_name=spec_name,
                    task_id=task_id,
                    timestamp=datetime.now(),
                    details={
                        "event": "ci_success",
                        "pr_id": pr.pr_id,
                        "pr_number": pr.pr_number,
                        "pr_url": pr.url,
                        "ci_status": ci_status.value,
                    }
                )
                
                self.task_registry.event_store.record_event(event)
                
                logger.info(
                    f"Recorded TaskCompleted event for PR {pr.pr_number}"
                )
            
            except Exception as e:
                logger.error(f"Failed to record CI success event: {e}")
        
        # Trigger success callback
        callback = self._on_success_callbacks.get(pr.pr_id)
        if callback:
            try:
                callback(pr, ci_status)
            except Exception as e:
                logger.error(
                    f"Success callback failed for PR {pr.pr_number}: {e}"
                )
    
    def _handle_ci_failure(self, pr: PullRequest, ci_status: CIStatus) -> None:
        """
        Handle CI failure event.
        
        Records TaskFailed event to Task Registry and triggers callback.
        
        Args:
            pr: PullRequest object
            ci_status: CI status (should be FAILURE)
            
        Requirements: 4.4
        """
        logger.info(f"Handling CI failure for PR {pr.pr_number}")
        
        # Record to Task Registry
        if self.task_registry:
            try:
                spec_name = pr.spec_id or "unknown"
                task_id = pr.task_id or pr.pr_id
                
                event = TaskEvent(
                    event_type=EventType.TASK_FAILED,
                    spec_name=spec_name,
                    task_id=task_id,
                    timestamp=datetime.now(),
                    details={
                        "event": "ci_failure",
                        "pr_id": pr.pr_id,
                        "pr_number": pr.pr_number,
                        "pr_url": pr.url,
                        "ci_status": ci_status.value,
                    }
                )
                
                self.task_registry.event_store.record_event(event)
                
                logger.info(
                    f"Recorded TaskFailed event for PR {pr.pr_number}"
                )
            
            except Exception as e:
                logger.error(f"Failed to record CI failure event: {e}")
        
        # Trigger failure callback
        callback = self._on_failure_callbacks.get(pr.pr_id)
        if callback:
            try:
                callback(pr, ci_status)
            except Exception as e:
                logger.error(
                    f"Failure callback failed for PR {pr.pr_number}: {e}"
                )
    
    def _record_ci_timeout(self, pr: PullRequest) -> None:
        """
        Record CI monitoring timeout to Task Registry.
        
        Args:
            pr: PullRequest object
            
        Requirements: 4.2
        """
        if not self.task_registry:
            return
        
        try:
            spec_name = pr.spec_id or "unknown"
            task_id = pr.task_id or pr.pr_id
            
            event = TaskEvent(
                event_type=EventType.TASK_UPDATED,
                spec_name=spec_name,
                task_id=task_id,
                timestamp=datetime.now(),
                details={
                    "event": "ci_monitoring_timeout",
                    "pr_id": pr.pr_id,
                    "pr_number": pr.pr_number,
                    "pr_url": pr.url,
                    "timeout": self.config.ci.timeout,
                }
            )
            
            self.task_registry.event_store.record_event(event)
            
            logger.info(
                f"Recorded CI monitoring timeout for PR {pr.pr_number}"
            )
        
        except Exception as e:
            logger.error(f"Failed to record CI timeout: {e}")
    
    def get_monitoring_status(self, pr_id: str) -> Optional[Dict[str, Any]]:
        """
        Get monitoring status for a PR.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            Dictionary with monitoring status, or None if not monitoring
        """
        if pr_id not in self._monitoring_threads:
            return None
        
        thread = self._monitoring_threads[pr_id]
        last_status = self._last_status.get(pr_id)
        
        return {
            "pr_id": pr_id,
            "is_alive": thread.is_alive(),
            "last_status": last_status.value if last_status else None,
            "has_success_callback": pr_id in self._on_success_callbacks,
            "has_failure_callback": pr_id in self._on_failure_callbacks,
            "has_status_change_callback": pr_id in self._on_status_change_callbacks,
        }
    
    def get_all_monitoring_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get monitoring status for all PRs.
        
        Returns:
            Dictionary mapping PR IDs to their monitoring status
        """
        return {
            pr_id: self.get_monitoring_status(pr_id)
            for pr_id in self._monitoring_threads.keys()
        }

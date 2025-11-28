"""
Tests for CI Status Monitor.

Tests CI status monitoring, polling, event recording, and callback handling.
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from threading import Event

from necrocode.review_pr_service.ci_status_monitor import CIStatusMonitor
from necrocode.review_pr_service.config import PRServiceConfig, CIConfig
from necrocode.review_pr_service.models import PullRequest, CIStatus, PRState
from necrocode.review_pr_service.git_host_client import GitHostClient
from necrocode.review_pr_service.exceptions import PRServiceError
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import TaskEvent, EventType


@pytest.fixture
def mock_git_host_client():
    """Create a mock Git host client."""
    client = Mock(spec=GitHostClient)
    client.get_ci_status = Mock(return_value=CIStatus.PENDING)
    return client


@pytest.fixture
def config():
    """Create test configuration."""
    config = PRServiceConfig()
    config.ci = CIConfig(
        enabled=True,
        polling_interval=1,  # Short interval for testing
        timeout=10,
        auto_comment_on_failure=True,
        update_pr_on_status_change=True
    )
    return config


@pytest.fixture
def task_registry(tmp_path):
    """Create a test Task Registry."""
    registry_dir = tmp_path / "task_registry"
    return TaskRegistry(registry_dir=registry_dir)


@pytest.fixture
def sample_pr():
    """Create a sample pull request."""
    return PullRequest(
        pr_id="123",
        pr_number=42,
        title="Test PR",
        description="Test description",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/test/repo/pull/42",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
        spec_id="test-spec",
        task_id="1.1"
    )


class TestCIStatusMonitorInit:
    """Test CI Status Monitor initialization."""
    
    def test_init_basic(self, mock_git_host_client, config):
        """Test basic initialization."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        assert monitor.git_host_client == mock_git_host_client
        assert monitor.config == config
        assert monitor.task_registry is None
        assert len(monitor._monitoring_threads) == 0
    
    def test_init_with_task_registry(self, mock_git_host_client, config, task_registry):
        """Test initialization with Task Registry."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config,
            task_registry=task_registry
        )
        
        assert monitor.task_registry == task_registry


class TestMonitorCIStatus:
    """Test synchronous CI status monitoring."""
    
    def test_monitor_ci_status_success(self, mock_git_host_client, config, sample_pr):
        """Test getting CI status successfully."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.SUCCESS
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        status = monitor.monitor_ci_status(sample_pr)
        
        assert status == CIStatus.SUCCESS
        mock_git_host_client.get_ci_status.assert_called_once_with(sample_pr.pr_id)
    
    def test_monitor_ci_status_pending(self, mock_git_host_client, config, sample_pr):
        """Test getting pending CI status."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.PENDING
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        status = monitor.monitor_ci_status(sample_pr)
        
        assert status == CIStatus.PENDING
    
    def test_monitor_ci_status_failure(self, mock_git_host_client, config, sample_pr):
        """Test getting failed CI status."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.FAILURE
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        status = monitor.monitor_ci_status(sample_pr)
        
        assert status == CIStatus.FAILURE
    
    def test_monitor_ci_status_with_callbacks(self, mock_git_host_client, config, sample_pr):
        """Test CI status monitoring with callbacks."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.SUCCESS
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        success_callback = Mock()
        failure_callback = Mock()
        
        status = monitor.monitor_ci_status(
            sample_pr,
            on_success=success_callback,
            on_failure=failure_callback
        )
        
        assert status == CIStatus.SUCCESS
        success_callback.assert_called_once_with(sample_pr, CIStatus.SUCCESS)
        failure_callback.assert_not_called()
    
    def test_monitor_ci_status_error(self, mock_git_host_client, config, sample_pr):
        """Test error handling in CI status monitoring."""
        mock_git_host_client.get_ci_status.side_effect = Exception("API error")
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        with pytest.raises(PRServiceError):
            monitor.monitor_ci_status(sample_pr)


class TestStatusChangeDetection:
    """Test CI status change detection."""
    
    def test_status_change_detected(self, mock_git_host_client, config, sample_pr):
        """Test that status changes are detected."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        # First call: PENDING
        mock_git_host_client.get_ci_status.return_value = CIStatus.PENDING
        status1 = monitor.monitor_ci_status(sample_pr)
        assert status1 == CIStatus.PENDING
        
        # Second call: SUCCESS (status changed)
        mock_git_host_client.get_ci_status.return_value = CIStatus.SUCCESS
        change_callback = Mock()
        
        status2 = monitor.monitor_ci_status(
            sample_pr,
            on_status_change=change_callback
        )
        
        assert status2 == CIStatus.SUCCESS
        change_callback.assert_called_once_with(sample_pr, CIStatus.PENDING, CIStatus.SUCCESS)
    
    def test_no_change_no_callback(self, mock_git_host_client, config, sample_pr):
        """Test that callback is not triggered when status doesn't change."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.PENDING
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        change_callback = Mock()
        
        # First call
        monitor.monitor_ci_status(sample_pr)
        
        # Second call with same status
        monitor.monitor_ci_status(
            sample_pr,
            on_status_change=change_callback
        )
        
        # Callback should not be triggered
        change_callback.assert_not_called()


class TestBackgroundMonitoring:
    """Test background CI status monitoring."""
    
    def test_start_monitoring(self, mock_git_host_client, config, sample_pr):
        """Test starting background monitoring."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        monitor.start_monitoring(sample_pr)
        
        # Check that monitoring thread was created
        assert sample_pr.pr_id in monitor._monitoring_threads
        assert sample_pr.pr_id in monitor._stop_events
        
        # Clean up
        monitor.stop_monitoring(sample_pr.pr_id)
    
    def test_stop_monitoring(self, mock_git_host_client, config, sample_pr):
        """Test stopping background monitoring."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        monitor.start_monitoring(sample_pr)
        assert sample_pr.pr_id in monitor._monitoring_threads
        
        monitor.stop_monitoring(sample_pr.pr_id)
        
        # Check that monitoring was stopped
        assert sample_pr.pr_id not in monitor._monitoring_threads
        assert sample_pr.pr_id not in monitor._stop_events
    
    def test_stop_all_monitoring(self, mock_git_host_client, config):
        """Test stopping all monitoring threads."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        # Start monitoring multiple PRs
        prs = [
            PullRequest(
                pr_id=str(i),
                pr_number=i,
                title=f"PR {i}",
                description="Test",
                source_branch=f"feature/{i}",
                target_branch="main",
                url=f"https://github.com/test/repo/pull/{i}",
                state=PRState.OPEN,
                draft=False,
                created_at=datetime.now()
            )
            for i in range(1, 4)
        ]
        
        for pr in prs:
            monitor.start_monitoring(pr)
        
        assert len(monitor._monitoring_threads) == 3
        
        monitor.stop_all_monitoring()
        
        assert len(monitor._monitoring_threads) == 0
    
    def test_monitoring_disabled(self, mock_git_host_client, config, sample_pr):
        """Test that monitoring doesn't start when disabled."""
        config.ci.enabled = False
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        monitor.start_monitoring(sample_pr)
        
        # No monitoring thread should be created
        assert len(monitor._monitoring_threads) == 0


class TestTaskRegistryIntegration:
    """Test Task Registry integration."""
    
    def test_record_ci_status_change(self, mock_git_host_client, config, task_registry, sample_pr):
        """Test recording CI status change to Task Registry."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config,
            task_registry=task_registry
        )
        
        # Simulate status change
        monitor._last_status[sample_pr.pr_id] = CIStatus.PENDING
        monitor._record_ci_status_change(sample_pr, CIStatus.PENDING, CIStatus.SUCCESS)
        
        # Verify event was recorded
        events = task_registry.event_store.get_events(
            spec_name=sample_pr.spec_id,
            task_id=sample_pr.task_id
        )
        
        assert len(events) > 0
        event = events[-1]
        assert event.event_type == EventType.TASK_UPDATED
        assert event.details["event"] == "ci_status_changed"
        assert event.details["old_status"] == "pending"
        assert event.details["new_status"] == "success"
    
    def test_record_ci_success(self, mock_git_host_client, config, task_registry, sample_pr):
        """Test recording CI success to Task Registry."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config,
            task_registry=task_registry
        )
        
        monitor._handle_ci_success(sample_pr, CIStatus.SUCCESS)
        
        # Verify TaskCompleted event was recorded
        events = task_registry.event_store.get_events(
            spec_name=sample_pr.spec_id,
            task_id=sample_pr.task_id
        )
        
        assert len(events) > 0
        event = events[-1]
        assert event.event_type == EventType.TASK_COMPLETED
        assert event.details["event"] == "ci_success"
    
    def test_record_ci_failure(self, mock_git_host_client, config, task_registry, sample_pr):
        """Test recording CI failure to Task Registry."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config,
            task_registry=task_registry
        )
        
        monitor._handle_ci_failure(sample_pr, CIStatus.FAILURE)
        
        # Verify TaskFailed event was recorded
        events = task_registry.event_store.get_events(
            spec_name=sample_pr.spec_id,
            task_id=sample_pr.task_id
        )
        
        assert len(events) > 0
        event = events[-1]
        assert event.event_type == EventType.TASK_FAILED
        assert event.details["event"] == "ci_failure"
    
    def test_no_task_registry(self, mock_git_host_client, config, sample_pr):
        """Test that monitoring works without Task Registry."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config,
            task_registry=None
        )
        
        # These should not raise exceptions
        monitor._record_ci_status_change(sample_pr, CIStatus.PENDING, CIStatus.SUCCESS)
        monitor._handle_ci_success(sample_pr, CIStatus.SUCCESS)
        monitor._handle_ci_failure(sample_pr, CIStatus.FAILURE)


class TestMonitoringStatus:
    """Test monitoring status queries."""
    
    def test_get_monitoring_status(self, mock_git_host_client, config, sample_pr):
        """Test getting monitoring status for a PR."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        # Not monitoring yet
        status = monitor.get_monitoring_status(sample_pr.pr_id)
        assert status is None
        
        # Start monitoring
        monitor.start_monitoring(sample_pr)
        
        status = monitor.get_monitoring_status(sample_pr.pr_id)
        assert status is not None
        assert status["pr_id"] == sample_pr.pr_id
        assert "is_alive" in status
        
        # Clean up
        monitor.stop_monitoring(sample_pr.pr_id)
    
    def test_get_all_monitoring_status(self, mock_git_host_client, config):
        """Test getting status for all monitored PRs."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        # Create multiple PRs
        prs = [
            PullRequest(
                pr_id=str(i),
                pr_number=i,
                title=f"PR {i}",
                description="Test",
                source_branch=f"feature/{i}",
                target_branch="main",
                url=f"https://github.com/test/repo/pull/{i}",
                state=PRState.OPEN,
                draft=False,
                created_at=datetime.now()
            )
            for i in range(1, 3)
        ]
        
        # Start monitoring
        for pr in prs:
            monitor.start_monitoring(pr)
        
        all_status = monitor.get_all_monitoring_status()
        
        assert len(all_status) == 2
        assert "1" in all_status
        assert "2" in all_status
        
        # Clean up
        monitor.stop_all_monitoring()


class TestCallbacks:
    """Test callback handling."""
    
    def test_success_callback_triggered(self, mock_git_host_client, config, sample_pr):
        """Test that success callback is triggered."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        success_callback = Mock()
        
        monitor._on_success_callbacks[sample_pr.pr_id] = success_callback
        monitor._handle_ci_success(sample_pr, CIStatus.SUCCESS)
        
        success_callback.assert_called_once_with(sample_pr, CIStatus.SUCCESS)
    
    def test_failure_callback_triggered(self, mock_git_host_client, config, sample_pr):
        """Test that failure callback is triggered."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        failure_callback = Mock()
        
        monitor._on_failure_callbacks[sample_pr.pr_id] = failure_callback
        monitor._handle_ci_failure(sample_pr, CIStatus.FAILURE)
        
        failure_callback.assert_called_once_with(sample_pr, CIStatus.FAILURE)
    
    def test_callback_exception_handled(self, mock_git_host_client, config, sample_pr):
        """Test that callback exceptions are handled gracefully."""
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        # Callback that raises exception
        def bad_callback(pr, status):
            raise Exception("Callback error")
        
        monitor._on_success_callbacks[sample_pr.pr_id] = bad_callback
        
        # Should not raise exception
        monitor._handle_ci_success(sample_pr, CIStatus.SUCCESS)


class TestMonitoringLoop:
    """Test monitoring loop behavior."""
    
    def test_monitoring_loop_stops_on_success(self, mock_git_host_client, config, sample_pr):
        """Test that monitoring loop stops when CI succeeds."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.SUCCESS
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        success_callback = Mock()
        monitor.start_monitoring(sample_pr, on_success=success_callback)
        
        # Wait for monitoring to complete
        time.sleep(2)
        
        # Monitoring should have stopped
        assert sample_pr.pr_id not in monitor._monitoring_threads or \
               not monitor._monitoring_threads[sample_pr.pr_id].is_alive()
        
        # Success callback should have been called
        success_callback.assert_called()
        
        # Clean up
        monitor.stop_monitoring(sample_pr.pr_id)
    
    def test_monitoring_loop_stops_on_failure(self, mock_git_host_client, config, sample_pr):
        """Test that monitoring loop stops when CI fails."""
        mock_git_host_client.get_ci_status.return_value = CIStatus.FAILURE
        
        monitor = CIStatusMonitor(
            git_host_client=mock_git_host_client,
            config=config
        )
        
        failure_callback = Mock()
        monitor.start_monitoring(sample_pr, on_failure=failure_callback)
        
        # Wait for monitoring to complete
        time.sleep(2)
        
        # Monitoring should have stopped
        assert sample_pr.pr_id not in monitor._monitoring_threads or \
               not monitor._monitoring_threads[sample_pr.pr_id].is_alive()
        
        # Failure callback should have been called
        failure_callback.assert_called()
        
        # Clean up
        monitor.stop_monitoring(sample_pr.pr_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for DispatcherCore.

Tests the main orchestration component including:
- Initialization
- Main loop
- Task assignment
- Slot allocation
- Task Registry updates
- Graceful shutdown
"""

import pytest
import time
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from necrocode.dispatcher import (
    DispatcherCore,
    DispatcherConfig,
    SchedulingPolicy,
    AgentPool,
    PoolType,
    Runner,
    RunnerState,
)
from necrocode.task_registry.models import Task, TaskState
from necrocode.repo_pool.models import Slot, SlotState


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = DispatcherConfig(
        poll_interval=1,  # Short interval for testing
        scheduling_policy=SchedulingPolicy.FIFO,
        max_global_concurrency=5,
        heartbeat_timeout=30,
        retry_max_attempts=2,
        graceful_shutdown_timeout=10,
    )
    
    # Add test pools
    config.agent_pools = [
        AgentPool(
            name="test-local",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=2,
            enabled=True,
        ),
    ]
    
    config.skill_mapping = {
        "default": ["test-local"],
    }
    
    return config


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return Task(
        id="task-1",
        title="Test Task",
        description="Test task description",
        state=TaskState.READY,
        priority=5,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={"spec_name": "test-spec", "repo_name": "test-repo"},
    )


@pytest.fixture
def mock_slot():
    """Create a mock slot for testing."""
    return Slot(
        slot_id="test-slot-1",
        repo_name="test-repo",
        repo_url="https://github.com/test/repo.git",
        slot_path=Path("/tmp/test-slot-1"),
        state=SlotState.AVAILABLE,
        current_branch="main",
        current_commit="abc123",
    )


@pytest.fixture
def mock_runner():
    """Create a mock runner for testing."""
    return Runner(
        runner_id="runner-1",
        task_id="task-1",
        pool_name="test-local",
        slot_id="test-slot-1",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        pid=12345,
    )


class TestDispatcherCoreInitialization:
    """Test DispatcherCore initialization."""
    
    def test_init_with_config(self, mock_config):
        """Test initialization with provided configuration."""
        dispatcher = DispatcherCore(config=mock_config)
        
        assert dispatcher.config == mock_config
        assert not dispatcher.running
        assert dispatcher.task_monitor is not None
        assert dispatcher.task_queue is not None
        assert dispatcher.scheduler is not None
        assert dispatcher.agent_pool_manager is not None
        assert dispatcher.runner_launcher is not None
        assert dispatcher.runner_monitor is not None
        assert dispatcher.metrics_collector is not None
    
    def test_init_without_config(self):
        """Test initialization with default configuration."""
        dispatcher = DispatcherCore()
        
        assert dispatcher.config is not None
        assert isinstance(dispatcher.config, DispatcherConfig)
        assert not dispatcher.running
    
    def test_component_integration(self, mock_config):
        """Test that all components are properly integrated."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Check metrics collector has references
        assert dispatcher.metrics_collector._task_queue is not None
        assert dispatcher.metrics_collector._agent_pool_manager is not None
        assert dispatcher.metrics_collector._runner_monitor is not None


class TestDispatcherCoreMainLoop:
    """Test DispatcherCore main loop."""
    
    @patch('necrocode.dispatcher.dispatcher_core.TaskMonitor')
    @patch('necrocode.dispatcher.dispatcher_core.Scheduler')
    def test_main_loop_iteration(self, mock_scheduler_class, mock_monitor_class, mock_config):
        """Test a single iteration of the main loop."""
        # Setup mocks
        mock_monitor = Mock()
        mock_monitor.poll_ready_tasks.return_value = []
        mock_monitor_class.return_value = mock_monitor
        
        mock_scheduler = Mock()
        mock_scheduler.schedule.return_value = []
        mock_scheduler_class.return_value = mock_scheduler
        
        dispatcher = DispatcherCore(config=mock_config)
        dispatcher.task_monitor = mock_monitor
        dispatcher.scheduler = mock_scheduler
        
        # Run one iteration
        dispatcher.running = True
        
        # Start in thread and stop after short time
        thread = threading.Thread(target=dispatcher._main_loop)
        thread.start()
        
        time.sleep(2)  # Let it run for 2 seconds
        dispatcher.running = False
        thread.join(timeout=5)
        
        # Verify methods were called
        assert mock_monitor.poll_ready_tasks.called
        assert mock_scheduler.schedule.called


class TestDispatcherCoreTaskAssignment:
    """Test task assignment functionality."""
    
    def test_assign_task_success(self, mock_config, mock_task, mock_slot, mock_runner):
        """Test successful task assignment."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock dependencies
        dispatcher._allocate_slot = Mock(return_value=mock_slot)
        dispatcher.runner_launcher.launch = Mock(return_value=mock_runner)
        dispatcher._update_task_registry = Mock()
        dispatcher.runner_monitor.add_runner = Mock()
        dispatcher.metrics_collector.record_assignment = Mock()
        
        pool = dispatcher.agent_pool_manager.get_pool_by_name("test-local")
        
        # Execute assignment
        dispatcher._assign_task(mock_task, pool)
        
        # Verify calls
        dispatcher._allocate_slot.assert_called_once_with(mock_task)
        dispatcher.runner_launcher.launch.assert_called_once()
        dispatcher._update_task_registry.assert_called_once()
        dispatcher.runner_monitor.add_runner.assert_called_once_with(mock_runner)
        dispatcher.metrics_collector.record_assignment.assert_called_once()
    
    def test_assign_task_no_slot(self, mock_config, mock_task):
        """Test task assignment when no slot is available."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock no slot available
        dispatcher._allocate_slot = Mock(return_value=None)
        dispatcher.task_queue.enqueue = Mock()
        
        pool = dispatcher.agent_pool_manager.get_pool_by_name("test-local")
        
        # Execute assignment
        dispatcher._assign_task(mock_task, pool)
        
        # Verify task was re-queued
        dispatcher.task_queue.enqueue.assert_called_once_with(mock_task)
    
    def test_assign_task_runner_launch_failure(self, mock_config, mock_task, mock_slot):
        """Test task assignment when runner launch fails."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock slot allocation success but runner launch failure
        dispatcher._allocate_slot = Mock(return_value=mock_slot)
        from necrocode.dispatcher.exceptions import RunnerLaunchError
        dispatcher.runner_launcher.launch = Mock(side_effect=RunnerLaunchError("Launch failed"))
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.task_queue.enqueue = Mock()
        
        pool = dispatcher.agent_pool_manager.get_pool_by_name("test-local")
        
        # Execute assignment (should handle the error internally)
        dispatcher._assign_task(mock_task, pool)
        
        # Verify slot was released and task re-queued
        dispatcher.repo_pool_manager.release_slot.assert_called_once()
        dispatcher.task_queue.enqueue.assert_called_once_with(mock_task)


class TestDispatcherCoreSlotAllocation:
    """Test slot allocation functionality."""
    
    def test_allocate_slot_success(self, mock_config, mock_task, mock_slot):
        """Test successful slot allocation."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock repo pool manager
        dispatcher.repo_pool_manager.allocate_slot = Mock(return_value=mock_slot)
        
        # Execute allocation
        result = dispatcher._allocate_slot(mock_task)
        
        # Verify
        assert result == mock_slot
        dispatcher.repo_pool_manager.allocate_slot.assert_called_once()
    
    def test_allocate_slot_failure(self, mock_config, mock_task):
        """Test slot allocation failure."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock allocation failure
        dispatcher.repo_pool_manager.allocate_slot = Mock(side_effect=Exception("No slots"))
        
        # Execute allocation
        result = dispatcher._allocate_slot(mock_task)
        
        # Verify returns None on failure
        assert result is None


class TestDispatcherCoreTaskRegistryUpdate:
    """Test Task Registry update functionality."""
    
    def test_update_task_registry(self, mock_config, mock_task, mock_runner, mock_slot):
        """Test Task Registry update."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock task registry
        dispatcher.task_registry.update_task_state = Mock()
        
        # Execute update
        dispatcher._update_task_registry(mock_task, mock_runner, mock_slot)
        
        # Verify update was called
        dispatcher.task_registry.update_task_state.assert_called_once()
        
        # Check arguments
        call_args = dispatcher.task_registry.update_task_state.call_args
        assert call_args[1]['task_id'] == mock_task.id
        assert call_args[1]['new_state'] == TaskState.RUNNING
        assert 'runner_id' in call_args[1]['metadata']
        assert 'assigned_slot' in call_args[1]['metadata']


class TestDispatcherCoreGracefulShutdown:
    """Test graceful shutdown functionality."""
    
    def test_stop_when_not_running(self, mock_config):
        """Test stop when dispatcher is not running."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Should not raise error
        dispatcher.stop(timeout=5)
        
        assert not dispatcher.running
    
    def test_wait_for_runners_no_runners(self, mock_config):
        """Test waiting for runners when none are running."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock no running runners
        dispatcher.runner_monitor.get_running_count = Mock(return_value=0)
        
        # Should return immediately
        start_time = time.time()
        dispatcher._wait_for_runners(timeout=10)
        elapsed = time.time() - start_time
        
        assert elapsed < 1  # Should be very fast
    
    def test_wait_for_runners_timeout(self, mock_config):
        """Test waiting for runners with timeout."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock runners that never complete
        dispatcher.runner_monitor.get_running_count = Mock(return_value=2)
        dispatcher._force_stop_runners = Mock()
        
        # Should timeout and force stop
        start_time = time.time()
        dispatcher._wait_for_runners(timeout=2)
        elapsed = time.time() - start_time
        
        assert elapsed >= 2  # Should wait for timeout
        dispatcher._force_stop_runners.assert_called_once()


class TestDispatcherCoreRunnerTimeout:
    """Test runner timeout handling."""
    
    def test_handle_runner_timeout_with_retry(self, mock_config, mock_runner):
        """Test handling runner timeout with retry."""
        dispatcher = DispatcherCore(config=mock_config)
        dispatcher.retry_manager.initial_delay = 0.1  # Short delay for testing
        
        # Mock dependencies
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.agent_pool_manager.get_pool_by_name = Mock()
        dispatcher.agent_pool_manager.decrement_running_count = Mock()
        dispatcher.task_monitor.task_registry_client.get_task = Mock(return_value=Mock(id=mock_runner.task_id))
        dispatcher.task_queue.enqueue = Mock()
        
        # Create runner info
        from necrocode.dispatcher.models import RunnerInfo
        runner_info = RunnerInfo(
            runner=mock_runner,
            last_heartbeat=datetime.now(),
            state=RunnerState.RUNNING
        )
        
        # Execute timeout handler
        dispatcher._handle_runner_timeout(mock_runner.runner_id, runner_info)
        
        # Verify slot was released
        dispatcher.repo_pool_manager.release_slot.assert_called_once()
        
        # Verify retry count was incremented
        assert dispatcher.retry_manager.get_retry_count(mock_runner.task_id) == 1
        
        # Verify task was re-queued
        dispatcher.task_queue.enqueue.assert_called_once()
    
    def test_handle_runner_timeout_max_retries(self, mock_config, mock_runner):
        """Test handling runner timeout when max retries reached."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Record failures up to max
        for _ in range(mock_config.retry_max_attempts):
            dispatcher.retry_manager.record_failure(mock_runner.task_id, "timeout")
        
        # Mock dependencies
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.agent_pool_manager.get_pool_by_name = Mock()
        dispatcher.agent_pool_manager.decrement_running_count = Mock()
        dispatcher.task_registry.update_task_state = Mock()
        
        # Create runner info
        from necrocode.dispatcher.models import RunnerInfo
        runner_info = RunnerInfo(
            runner=mock_runner,
            last_heartbeat=datetime.now(),
            state=RunnerState.RUNNING
        )
        
        # Execute timeout handler
        dispatcher._handle_runner_timeout(mock_runner.runner_id, runner_info)
        
        # Verify task was marked as failed
        dispatcher.task_registry.update_task_state.assert_called_once()
        call_args = dispatcher.task_registry.update_task_state.call_args
        assert call_args[1]['new_state'] == TaskState.FAILED


class TestDispatcherCoreStatus:
    """Test status reporting."""
    
    def test_get_status(self, mock_config):
        """Test getting dispatcher status."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock some state
        dispatcher.running = True
        dispatcher.task_queue.enqueue(Mock(id="task-1", priority=5, created_at=datetime.now()))
        
        # Get status
        status = dispatcher.get_status()
        
        # Verify status structure
        assert 'running' in status
        assert 'queue_size' in status
        assert 'running_tasks' in status
        assert 'pool_statuses' in status
        assert 'metrics' in status
        assert 'retry_info' in status
        
        assert status['running'] is True
        assert status['queue_size'] >= 0


class TestDispatcherCoreRetry:
    """Test retry functionality."""
    
    def test_handle_task_failure_first_attempt(self, mock_config):
        """Test handling task failure on first attempt."""
        # Use shorter initial delay for testing
        mock_config.retry_backoff_base = 2.0
        dispatcher = DispatcherCore(config=mock_config)
        dispatcher.retry_manager.initial_delay = 0.1  # Very short delay for testing
        
        # Mock dependencies
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.agent_pool_manager.get_pool_by_name = Mock()
        dispatcher.agent_pool_manager.decrement_running_count = Mock()
        dispatcher.task_monitor.task_registry_client.get_task = Mock(return_value=Mock(id="task-1"))
        dispatcher.task_queue.enqueue = Mock()
        
        # Handle failure
        dispatcher.handle_task_failure(
            task_id="task-1",
            spec_name="test-spec",
            failure_reason="timeout",
            slot_id="slot-1",
            pool_name="test-local"
        )
        
        # Verify retry was recorded
        assert dispatcher.retry_manager.get_retry_count("task-1") == 1
        
        # Task should be re-queued (even though backoff hasn't elapsed yet)
        # The queue will hold it until backoff elapses
        dispatcher.task_queue.enqueue.assert_called_once()
        
        # Verify slot was released
        dispatcher.repo_pool_manager.release_slot.assert_called_once()
    
    def test_handle_task_failure_max_retries(self, mock_config):
        """Test handling task failure when max retries reached."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Record failures up to max
        for _ in range(mock_config.retry_max_attempts):
            dispatcher.retry_manager.record_failure("task-1", "error")
        
        # Mock dependencies
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.agent_pool_manager.get_pool_by_name = Mock()
        dispatcher.agent_pool_manager.decrement_running_count = Mock()
        dispatcher.task_registry.update_task_state = Mock()
        
        # Handle failure (should mark as FAILED)
        dispatcher.handle_task_failure(
            task_id="task-1",
            spec_name="test-spec",
            failure_reason="timeout",
            slot_id="slot-1",
            pool_name="test-local"
        )
        
        # Verify task was marked as FAILED
        dispatcher.task_registry.update_task_state.assert_called_once()
        call_args = dispatcher.task_registry.update_task_state.call_args
        assert call_args[1]['new_state'] == TaskState.FAILED
        
        # Verify retry info was cleared
        assert dispatcher.retry_manager.get_retry_info("task-1") is None
    
    def test_handle_runner_completion_success(self, mock_config):
        """Test handling successful runner completion."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Mock dependencies
        dispatcher.runner_monitor.remove_runner = Mock()
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.agent_pool_manager.get_pool_by_name = Mock()
        dispatcher.agent_pool_manager.decrement_running_count = Mock()
        dispatcher.task_registry.update_task_state = Mock()
        
        # Handle successful completion
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="task-1",
            spec_name="test-spec",
            success=True,
            slot_id="slot-1",
            pool_name="test-local"
        )
        
        # Verify runner was removed
        dispatcher.runner_monitor.remove_runner.assert_called_once_with("runner-1")
        
        # Verify task was marked as DONE
        dispatcher.task_registry.update_task_state.assert_called_once()
        call_args = dispatcher.task_registry.update_task_state.call_args
        assert call_args[1]['new_state'] == TaskState.DONE
        
        # Verify slot was released
        dispatcher.repo_pool_manager.release_slot.assert_called_once()
    
    def test_handle_runner_completion_failure(self, mock_config):
        """Test handling failed runner completion."""
        dispatcher = DispatcherCore(config=mock_config)
        dispatcher.retry_manager.initial_delay = 0.1  # Very short delay for testing
        
        # Mock dependencies
        dispatcher.runner_monitor.remove_runner = Mock()
        dispatcher.repo_pool_manager.release_slot = Mock()
        dispatcher.agent_pool_manager.get_pool_by_name = Mock()
        dispatcher.agent_pool_manager.decrement_running_count = Mock()
        dispatcher.task_monitor.task_registry_client.get_task = Mock(return_value=Mock(id="task-1"))
        dispatcher.task_queue.enqueue = Mock()
        
        # Handle failed completion
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="task-1",
            spec_name="test-spec",
            success=False,
            slot_id="slot-1",
            pool_name="test-local",
            failure_reason="execution error"
        )
        
        # Verify runner was removed
        dispatcher.runner_monitor.remove_runner.assert_called_once_with("runner-1")
        
        # Verify retry was recorded
        assert dispatcher.retry_manager.get_retry_count("task-1") == 1
        
        # Verify task was re-queued
        dispatcher.task_queue.enqueue.assert_called_once()
    
    def test_exponential_backoff_integration(self, mock_config):
        """Test exponential backoff is applied correctly."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Record first failure
        dispatcher.retry_manager.record_failure("task-1", "error")
        
        # Immediately after, should not retry (backoff not elapsed)
        assert dispatcher.retry_manager.should_retry("task-1") is False
        
        # Wait for backoff
        time.sleep(1.5)
        
        # Now should be ready for retry
        assert dispatcher.retry_manager.should_retry("task-1") is True
    
    def test_retry_info_in_status(self, mock_config):
        """Test retry info is included in status."""
        dispatcher = DispatcherCore(config=mock_config)
        
        # Record some failures
        dispatcher.retry_manager.record_failure("task-1", "error")
        dispatcher.retry_manager.record_failure("task-2", "timeout")
        
        # Get status
        status = dispatcher.get_status()
        
        # Verify retry info is present
        assert 'retry_info' in status
        assert 'task-1' in status['retry_info']
        assert 'task-2' in status['retry_info']
        
        # Verify retry info structure
        task1_info = status['retry_info']['task-1']
        assert 'retry_count' in task1_info
        assert 'failure_reason' in task1_info
        assert task1_info['retry_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for the RunnerMonitor component.

Tests runner monitoring, heartbeat tracking, timeout detection, and state management.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

from necrocode.dispatcher.runner_monitor import RunnerMonitor
from necrocode.dispatcher.models import Runner, RunnerState, RunnerInfo


@pytest.fixture
def runner_monitor():
    """Create a RunnerMonitor instance for testing."""
    return RunnerMonitor(heartbeat_timeout=2)


@pytest.fixture
def sample_runner():
    """Create a sample Runner for testing."""
    return Runner(
        runner_id="runner-001",
        task_id="task-123",
        pool_name="test-pool",
        slot_id="slot-001",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        pid=12345
    )


def test_add_runner(runner_monitor, sample_runner):
    """Test adding a runner to monitoring."""
    runner_monitor.add_runner(sample_runner)
    
    # Verify runner was added
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info is not None
    assert runner_info.runner.runner_id == sample_runner.runner_id
    assert runner_info.runner.task_id == sample_runner.task_id
    assert runner_info.state == RunnerState.RUNNING
    assert runner_info.last_heartbeat is not None


def test_remove_runner(runner_monitor, sample_runner):
    """Test removing a runner from monitoring."""
    runner_monitor.add_runner(sample_runner)
    
    # Verify runner exists
    assert runner_monitor.get_runner_status(sample_runner.runner_id) is not None
    
    # Remove runner
    runner_monitor.remove_runner(sample_runner.runner_id)
    
    # Verify runner was removed
    assert runner_monitor.get_runner_status(sample_runner.runner_id) is None


def test_remove_unknown_runner(runner_monitor):
    """Test removing a runner that doesn't exist."""
    # Should not raise an error
    runner_monitor.remove_runner("unknown-runner")


def test_update_heartbeat(runner_monitor, sample_runner):
    """Test updating runner heartbeat."""
    runner_monitor.add_runner(sample_runner)
    
    # Get initial heartbeat
    initial_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    initial_heartbeat = initial_info.last_heartbeat
    
    # Wait a bit and update heartbeat
    time.sleep(0.1)
    runner_monitor.update_heartbeat(sample_runner.runner_id)
    
    # Verify heartbeat was updated
    updated_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert updated_info.last_heartbeat > initial_heartbeat


def test_update_heartbeat_unknown_runner(runner_monitor):
    """Test updating heartbeat for unknown runner."""
    # Should not raise an error
    runner_monitor.update_heartbeat("unknown-runner")


def test_check_heartbeats_no_timeout(runner_monitor, sample_runner):
    """Test heartbeat check when no timeout occurs."""
    runner_monitor.add_runner(sample_runner)
    
    # Check heartbeats immediately (no timeout)
    runner_monitor.check_heartbeats()
    
    # Verify runner is still running
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.RUNNING


def test_check_heartbeats_with_timeout(runner_monitor, sample_runner):
    """Test heartbeat check when timeout occurs."""
    timeout_handler = Mock()
    runner_monitor.timeout_handler = timeout_handler
    
    runner_monitor.add_runner(sample_runner)
    
    # Wait for timeout
    time.sleep(2.5)
    
    # Check heartbeats (should detect timeout)
    runner_monitor.check_heartbeats()
    
    # Verify runner state changed to FAILED
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.FAILED
    
    # Verify timeout handler was called
    timeout_handler.assert_called_once()
    call_args = timeout_handler.call_args[0]
    assert call_args[0] == sample_runner.runner_id
    assert isinstance(call_args[1], RunnerInfo)


def test_check_heartbeats_with_recent_update(runner_monitor, sample_runner):
    """Test heartbeat check with recent heartbeat update."""
    runner_monitor.add_runner(sample_runner)
    
    # Wait a bit but update heartbeat before timeout
    time.sleep(1.5)
    runner_monitor.update_heartbeat(sample_runner.runner_id)
    
    # Check heartbeats (should not timeout)
    runner_monitor.check_heartbeats()
    
    # Verify runner is still running
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.RUNNING


def test_get_runner_status(runner_monitor, sample_runner):
    """Test getting runner status."""
    # Non-existent runner
    assert runner_monitor.get_runner_status("unknown") is None
    
    # Add runner and get status
    runner_monitor.add_runner(sample_runner)
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    
    assert runner_info is not None
    assert runner_info.runner.runner_id == sample_runner.runner_id
    assert runner_info.state == RunnerState.RUNNING


def test_get_all_runners(runner_monitor):
    """Test getting all monitored runners."""
    # Initially empty
    assert len(runner_monitor.get_all_runners()) == 0
    
    # Add multiple runners
    runner1 = Runner(
        runner_id="runner-001",
        task_id="task-001",
        pool_name="pool-1",
        slot_id="slot-001",
        state=RunnerState.RUNNING,
        started_at=datetime.now()
    )
    runner2 = Runner(
        runner_id="runner-002",
        task_id="task-002",
        pool_name="pool-2",
        slot_id="slot-002",
        state=RunnerState.RUNNING,
        started_at=datetime.now()
    )
    
    runner_monitor.add_runner(runner1)
    runner_monitor.add_runner(runner2)
    
    # Get all runners
    all_runners = runner_monitor.get_all_runners()
    assert len(all_runners) == 2
    assert "runner-001" in all_runners
    assert "runner-002" in all_runners


def test_get_running_count(runner_monitor):
    """Test getting count of running runners."""
    # Initially zero
    assert runner_monitor.get_running_count() == 0
    
    # Add runners
    runner1 = Runner(
        runner_id="runner-001",
        task_id="task-001",
        pool_name="pool-1",
        slot_id="slot-001",
        state=RunnerState.RUNNING,
        started_at=datetime.now()
    )
    runner2 = Runner(
        runner_id="runner-002",
        task_id="task-002",
        pool_name="pool-2",
        slot_id="slot-002",
        state=RunnerState.RUNNING,
        started_at=datetime.now()
    )
    
    runner_monitor.add_runner(runner1)
    runner_monitor.add_runner(runner2)
    
    assert runner_monitor.get_running_count() == 2
    
    # Update one to COMPLETED
    runner_monitor.update_runner_state("runner-001", RunnerState.COMPLETED)
    assert runner_monitor.get_running_count() == 1
    
    # Update another to FAILED
    runner_monitor.update_runner_state("runner-002", RunnerState.FAILED)
    assert runner_monitor.get_running_count() == 0


def test_update_runner_state(runner_monitor, sample_runner):
    """Test updating runner state."""
    runner_monitor.add_runner(sample_runner)
    
    # Verify initial state
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.RUNNING
    
    # Update to COMPLETED
    runner_monitor.update_runner_state(
        sample_runner.runner_id,
        RunnerState.COMPLETED
    )
    
    # Verify state changed
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.COMPLETED
    assert runner_info.runner.state == RunnerState.COMPLETED


def test_update_state_unknown_runner(runner_monitor):
    """Test updating state for unknown runner."""
    # Should not raise an error
    runner_monitor.update_runner_state("unknown", RunnerState.COMPLETED)


def test_timeout_handler_exception(runner_monitor, sample_runner):
    """Test timeout handler that raises an exception."""
    def failing_handler(runner_id, info):
        raise ValueError("Handler error")
    
    runner_monitor.timeout_handler = failing_handler
    runner_monitor.add_runner(sample_runner)
    
    # Wait for timeout
    time.sleep(2.5)
    
    # Check heartbeats (should handle exception gracefully)
    runner_monitor.check_heartbeats()
    
    # Verify runner state still changed to FAILED
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.FAILED


def test_concurrent_operations(runner_monitor):
    """Test thread-safe concurrent operations."""
    import threading
    
    runners = [
        Runner(
            runner_id=f"runner-{i:03d}",
            task_id=f"task-{i:03d}",
            pool_name="pool-1",
            slot_id=f"slot-{i:03d}",
            state=RunnerState.RUNNING,
            started_at=datetime.now()
        )
        for i in range(10)
    ]
    
    def add_runners():
        for runner in runners[:5]:
            runner_monitor.add_runner(runner)
    
    def update_heartbeats():
        for runner in runners[:5]:
            runner_monitor.update_heartbeat(runner.runner_id)
    
    # Run operations concurrently
    threads = [
        threading.Thread(target=add_runners),
        threading.Thread(target=update_heartbeats),
    ]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Verify all runners were added
    assert runner_monitor.get_running_count() == 5


def test_multiple_timeout_checks(runner_monitor, sample_runner):
    """Test multiple heartbeat checks over time."""
    runner_monitor.add_runner(sample_runner)
    
    # First check - no timeout
    runner_monitor.check_heartbeats()
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.RUNNING
    
    # Update heartbeat
    time.sleep(1)
    runner_monitor.update_heartbeat(sample_runner.runner_id)
    
    # Second check - still no timeout
    runner_monitor.check_heartbeats()
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.RUNNING
    
    # Wait for timeout
    time.sleep(2.5)
    
    # Third check - timeout detected
    runner_monitor.check_heartbeats()
    runner_info = runner_monitor.get_runner_status(sample_runner.runner_id)
    assert runner_info.state == RunnerState.FAILED


def test_runner_with_different_pool_types(runner_monitor):
    """Test monitoring runners from different pool types."""
    local_runner = Runner(
        runner_id="local-001",
        task_id="task-001",
        pool_name="local-pool",
        slot_id="slot-001",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        pid=12345
    )
    
    docker_runner = Runner(
        runner_id="docker-001",
        task_id="task-002",
        pool_name="docker-pool",
        slot_id="slot-002",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        container_id="container-abc"
    )
    
    k8s_runner = Runner(
        runner_id="k8s-001",
        task_id="task-003",
        pool_name="k8s-pool",
        slot_id="slot-003",
        state=RunnerState.RUNNING,
        started_at=datetime.now(),
        job_name="job-xyz"
    )
    
    runner_monitor.add_runner(local_runner)
    runner_monitor.add_runner(docker_runner)
    runner_monitor.add_runner(k8s_runner)
    
    assert runner_monitor.get_running_count() == 3
    
    # Verify each runner
    assert runner_monitor.get_runner_status("local-001").runner.pid == 12345
    assert runner_monitor.get_runner_status("docker-001").runner.container_id == "container-abc"
    assert runner_monitor.get_runner_status("k8s-001").runner.job_name == "job-xyz"

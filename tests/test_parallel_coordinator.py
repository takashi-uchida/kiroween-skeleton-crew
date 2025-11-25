"""
Tests for parallel execution coordination in Agent Runner.

Tests cover:
- ParallelCoordinator registration and tracking
- Resource conflict detection
- Concurrent runner limits
- Wait time estimation
- Metrics recording

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

import time
from pathlib import Path
from threading import Thread

import pytest

from necrocode.agent_runner.parallel_coordinator import (
    ParallelCoordinator,
    ParallelExecutionContext,
    RunnerInstance,
)


@pytest.fixture
def temp_coordination_dir(tmp_path):
    """Create temporary coordination directory."""
    coord_dir = tmp_path / "coordination"
    coord_dir.mkdir()
    return coord_dir


@pytest.fixture
def coordinator(temp_coordination_dir):
    """Create ParallelCoordinator instance."""
    return ParallelCoordinator(
        coordination_dir=temp_coordination_dir,
        max_parallel_runners=3,
        heartbeat_timeout_seconds=5.0,
    )


# ============================================================================
# Registration Tests
# ============================================================================

def test_register_runner(coordinator, tmp_path):
    """Test registering a runner instance."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    success = coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    )
    
    assert success
    assert coordinator.get_concurrent_count() == 1


def test_register_multiple_runners(coordinator, tmp_path):
    """Test registering multiple runner instances."""
    for i in range(3):
        workspace = tmp_path / f"workspace{i}"
        workspace.mkdir()
        
        success = coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
        assert success
    
    assert coordinator.get_concurrent_count() == 3


def test_register_exceeds_max_limit(coordinator, tmp_path):
    """Test registration fails when exceeding max parallel runners."""
    # Register 3 runners (at limit)
    for i in range(3):
        workspace = tmp_path / f"workspace{i}"
        workspace.mkdir()
        coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
    
    # Try to register 4th runner
    workspace4 = tmp_path / "workspace4"
    workspace4.mkdir()
    
    success = coordinator.register_runner(
        runner_id="runner-4",
        task_id="task-4",
        spec_name="test-spec",
        workspace_path=workspace4,
    )
    
    assert not success
    assert coordinator.get_concurrent_count() == 3


def test_unregister_runner(coordinator, tmp_path):
    """Test unregistering a runner instance."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    )
    
    assert coordinator.get_concurrent_count() == 1
    
    coordinator.unregister_runner("runner-1")
    
    assert coordinator.get_concurrent_count() == 0


# ============================================================================
# Resource Conflict Detection Tests
# ============================================================================

def test_detect_file_conflicts(coordinator, tmp_path):
    """Test detecting file conflicts between runners."""
    # Register runner 1 with files
    workspace1 = tmp_path / "workspace1"
    workspace1.mkdir()
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace1,
    )
    coordinator.update_resources(
        runner_id="runner-1",
        files=["src/main.py", "src/utils.py"],
    )
    
    # Register runner 2
    workspace2 = tmp_path / "workspace2"
    workspace2.mkdir()
    coordinator.register_runner(
        runner_id="runner-2",
        task_id="task-2",
        spec_name="test-spec",
        workspace_path=workspace2,
    )
    
    # Check for conflicts
    conflicts = coordinator.detect_conflicts(
        runner_id="runner-2",
        files=["src/main.py", "src/config.py"],  # main.py conflicts
    )
    
    assert len(conflicts) == 1
    assert "main.py" in conflicts[0]


def test_detect_branch_conflicts(coordinator, tmp_path):
    """Test detecting branch conflicts between runners."""
    # Register runner 1 with branch
    workspace1 = tmp_path / "workspace1"
    workspace1.mkdir()
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace1,
    )
    coordinator.update_resources(
        runner_id="runner-1",
        branches=["feature/task-1"],
    )
    
    # Register runner 2
    workspace2 = tmp_path / "workspace2"
    workspace2.mkdir()
    coordinator.register_runner(
        runner_id="runner-2",
        task_id="task-2",
        spec_name="test-spec",
        workspace_path=workspace2,
    )
    
    # Check for conflicts
    conflicts = coordinator.detect_conflicts(
        runner_id="runner-2",
        branches=["feature/task-1", "feature/task-2"],  # task-1 conflicts
    )
    
    assert len(conflicts) == 1
    assert "feature/task-1" in conflicts[0]


def test_no_conflicts_different_resources(coordinator, tmp_path):
    """Test no conflicts when using different resources."""
    # Register runner 1
    workspace1 = tmp_path / "workspace1"
    workspace1.mkdir()
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace1,
    )
    coordinator.update_resources(
        runner_id="runner-1",
        files=["src/main.py"],
        branches=["feature/task-1"],
    )
    
    # Register runner 2
    workspace2 = tmp_path / "workspace2"
    workspace2.mkdir()
    coordinator.register_runner(
        runner_id="runner-2",
        task_id="task-2",
        spec_name="test-spec",
        workspace_path=workspace2,
    )
    
    # Check for conflicts with different resources
    conflicts = coordinator.detect_conflicts(
        runner_id="runner-2",
        files=["src/config.py"],
        branches=["feature/task-2"],
    )
    
    assert len(conflicts) == 0


def test_workspace_conflict_detection(coordinator, tmp_path):
    """Test detecting workspace conflicts."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    # Register runner 1
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    )
    
    # Try to register runner 2 with same workspace
    success = coordinator.register_runner(
        runner_id="runner-2",
        task_id="task-2",
        spec_name="test-spec",
        workspace_path=workspace,  # Same workspace
    )
    
    assert not success


# ============================================================================
# Heartbeat and Cleanup Tests
# ============================================================================

def test_heartbeat_update(coordinator, tmp_path):
    """Test updating runner heartbeat."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    )
    
    # Update heartbeat
    coordinator.update_heartbeat("runner-1")
    
    # Should still be active
    assert coordinator.get_concurrent_count() == 1


def test_stale_runner_cleanup(coordinator, tmp_path):
    """Test cleanup of stale runners."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    # Create coordinator with short timeout
    short_timeout_coordinator = ParallelCoordinator(
        coordination_dir=coordinator.coordination_dir,
        max_parallel_runners=3,
        heartbeat_timeout_seconds=0.5,  # 0.5 seconds
    )
    
    short_timeout_coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    )
    
    assert short_timeout_coordinator.get_concurrent_count() == 1
    
    # Wait for timeout
    time.sleep(1.0)
    
    # Stale runner should be cleaned up
    assert short_timeout_coordinator.get_concurrent_count() == 0


# ============================================================================
# Wait Time and Status Tests
# ============================================================================

def test_get_wait_time_under_limit(coordinator, tmp_path):
    """Test wait time when under limit."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    )
    
    # Under limit, no wait time
    wait_time = coordinator.get_wait_time()
    assert wait_time == 0.0


def test_get_wait_time_at_limit(coordinator, tmp_path):
    """Test wait time when at limit."""
    # Register 3 runners (at limit)
    for i in range(3):
        workspace = tmp_path / f"workspace{i}"
        workspace.mkdir()
        coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
    
    # At limit, should have wait time
    wait_time = coordinator.get_wait_time()
    assert wait_time > 0


def test_get_status(coordinator, tmp_path):
    """Test getting coordinator status."""
    # Register 2 runners
    for i in range(2):
        workspace = tmp_path / f"workspace{i}"
        workspace.mkdir()
        coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
    
    status = coordinator.get_status()
    
    assert status["active_runners"] == 2
    assert status["max_parallel_runners"] == 3
    assert len(status["runners"]) == 2


# ============================================================================
# Parallel Execution Context Tests
# ============================================================================

def test_parallel_execution_context(coordinator, tmp_path):
    """Test ParallelExecutionContext context manager."""
    workspace = tmp_path / "workspace1"
    workspace.mkdir()
    
    with ParallelExecutionContext(
        coordinator=coordinator,
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=workspace,
    ):
        # Inside context, runner should be registered
        assert coordinator.get_concurrent_count() == 1
    
    # Outside context, runner should be unregistered
    assert coordinator.get_concurrent_count() == 0


def test_parallel_execution_context_failure(coordinator, tmp_path):
    """Test ParallelExecutionContext handles registration failure."""
    # Register 3 runners (at limit)
    for i in range(3):
        workspace = tmp_path / f"workspace{i}"
        workspace.mkdir()
        coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
    
    # Try to enter context when at limit
    workspace4 = tmp_path / "workspace4"
    workspace4.mkdir()
    
    with pytest.raises(RuntimeError):
        with ParallelExecutionContext(
            coordinator=coordinator,
            runner_id="runner-4",
            task_id="task-4",
            spec_name="test-spec",
            workspace_path=workspace4,
        ):
            pass


# ============================================================================
# Concurrent Access Tests
# ============================================================================

def test_concurrent_registration(coordinator, tmp_path):
    """Test concurrent runner registration."""
    results = []
    
    def register_runner(runner_id: int):
        workspace = tmp_path / f"workspace{runner_id}"
        workspace.mkdir()
        
        success = coordinator.register_runner(
            runner_id=f"runner-{runner_id}",
            task_id=f"task-{runner_id}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
        results.append(success)
    
    # Try to register 5 runners concurrently (limit is 3)
    threads = []
    for i in range(5):
        thread = Thread(target=register_runner, args=(i,))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    # Exactly 3 should succeed
    assert sum(results) == 3
    assert coordinator.get_concurrent_count() == 3


def test_concurrent_heartbeat_updates(coordinator, tmp_path):
    """Test concurrent heartbeat updates."""
    # Register runners
    for i in range(3):
        workspace = tmp_path / f"workspace{i}"
        workspace.mkdir()
        coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=workspace,
        )
    
    def update_heartbeat(runner_id: int):
        for _ in range(10):
            coordinator.update_heartbeat(f"runner-{runner_id}")
            time.sleep(0.01)
    
    # Update heartbeats concurrently
    threads = []
    for i in range(3):
        thread = Thread(target=update_heartbeat, args=(i,))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    # All runners should still be active
    assert coordinator.get_concurrent_count() == 3

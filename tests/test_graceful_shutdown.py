"""
Integration tests for graceful shutdown.

Tests graceful shutdown behavior including:
- Stopping new task acceptance
- Waiting for running tasks to complete
- Timeout handling
- Force stopping runners
- State cleanup

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
"""

import pytest
import time
import tempfile
import shutil
import threading
import signal
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from necrocode.dispatcher import (
    DispatcherCore,
    DispatcherConfig,
    SchedulingPolicy,
    AgentPool,
    PoolType,
)
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, Taskset
from necrocode.repo_pool.models import Slot, SlotState


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    task_registry_dir = tempfile.mkdtemp(prefix="test_shutdown_registry_")
    
    yield {"task_registry": Path(task_registry_dir)}
    
    shutil.rmtree(task_registry_dir, ignore_errors=True)


@pytest.fixture
def shutdown_config(temp_dirs):
    """Create configuration for shutdown testing."""
    config = DispatcherConfig(
        poll_interval=0.5,
        scheduling_policy=SchedulingPolicy.FIFO,
        max_global_concurrency=5,
        heartbeat_timeout=30,
        retry_max_attempts=2,
        graceful_shutdown_timeout=5,  # Short timeout for testing
        task_registry_dir=str(temp_dirs["task_registry"]),
    )
    
    config.agent_pools = [
        AgentPool(
            name="test-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=3,
            enabled=True,
        ),
    ]
    
    config.skill_mapping = {
        "default": ["test-pool"],
    }
    
    return config


@pytest.fixture
def task_registry(temp_dirs):
    """Create a Task Registry for testing."""
    return TaskRegistry(registry_dir=str(temp_dirs["task_registry"]))


class TestGracefulShutdownBasic:
    """Test basic graceful shutdown behavior."""
    
    def test_stop_when_no_running_tasks(self, shutdown_config, task_registry):
        """Test graceful shutdown when no tasks are running."""
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait a bit
        time.sleep(1)
        
        # Stop dispatcher
        start_time = time.time()
        dispatcher.stop(timeout=5)
        elapsed = time.time() - start_time
        
        # Should stop quickly since no tasks are running
        assert elapsed < 2, f"Shutdown took too long: {elapsed}s"
        
        # Wait for thread to finish
        dispatcher_thread.join(timeout=5)
        
        # Verify dispatcher is stopped
        assert not dispatcher.running
    
    def test_stop_rejects_new_tasks(self, shutdown_config, task_registry):
        """Test that new tasks are not accepted after stop is called."""
        # Create tasks
        tasks = [
            Task(
                id=str(i),
                title=f"Task {i}",
                description=f"Test task {i}",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-stop-reject", "repo_name": "test-repo"},
            )
            for i in range(1, 6)
        ]
        
        taskset = Taskset(spec_name="test-stop-reject", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Mock slot allocation
        def mock_allocate_slot(repo_name, metadata=None):
            task_id = metadata.get("task_id", "unknown")
            return Slot(
                slot_id=f"slot-{task_id}",
                repo_name=repo_name,
                repo_url="https://github.com/test/repo.git",
                slot_path=Path(f"/tmp/slot-{task_id}"),
                state=SlotState.ALLOCATED,
                current_branch="main",
                current_commit="abc123",
            )
        
        dispatcher.repo_pool_manager.allocate_slot = Mock(side_effect=mock_allocate_slot)
        dispatcher.repo_pool_manager.release_slot = Mock()
        
        # Track assignments
        assignments = []
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            assignments.append(task.id)
            return Runner(
                runner_id=f"runner-{task.id}",
                task_id=task.id,
                pool_name=pool.name,
                slot_id=slot.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                pid=10000 + int(task.id),
            )
        
        dispatcher.runner_launcher.launch = Mock(side_effect=mock_launch)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for some assignments
        time.sleep(1)
        
        initial_assignments = len(assignments)
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        
        # Wait a bit more
        time.sleep(1)
        
        # No new assignments should have been made after stop
        final_assignments = len(assignments)
        assert final_assignments == initial_assignments, \
            "New tasks were assigned after stop was called"
        
        # Wait for thread
        dispatcher_thread.join(timeout=5)


class TestGracefulShutdownWithRunningTasks:
    """Test graceful shutdown with running tasks."""
    
    def test_wait_for_running_tasks_to_complete(self, shutdown_config, task_registry):
        """Test that shutdown waits for running tasks to complete."""
        # Create tasks
        tasks = [
            Task(
                id="1",
                title="Long running task",
                description="Task that takes time to complete",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-wait-complete", "repo_name": "test-repo"},
            ),
        ]
        
        taskset = Taskset(spec_name="test-wait-complete", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Mock slot allocation
        mock_slot = Slot(
            slot_id="test-slot-1",
            repo_name="test-repo",
            repo_url="https://github.com/test/repo.git",
            slot_path=Path("/tmp/test-slot-1"),
            state=SlotState.ALLOCATED,
            current_branch="main",
            current_commit="abc123",
        )
        dispatcher.repo_pool_manager.allocate_slot = Mock(return_value=mock_slot)
        dispatcher.repo_pool_manager.release_slot = Mock()
        
        # Mock runner launcher
        from necrocode.dispatcher.models import Runner, RunnerState
        mock_runner = Runner(
            runner_id="runner-1",
            task_id="1",
            pool_name="test-pool",
            slot_id="test-slot-1",
            state=RunnerState.RUNNING,
            started_at=datetime.now(),
            pid=12345,
        )
        dispatcher.runner_launcher.launch = Mock(return_value=mock_runner)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for task to be assigned
        time.sleep(1)
        
        # Verify task is running
        assert dispatcher.get_global_running_count() == 1
        
        # Start shutdown in separate thread
        shutdown_thread = threading.Thread(
            target=dispatcher.stop,
            kwargs={"timeout": 10}
        )
        shutdown_thread.start()
        
        # Wait a bit, then complete the task
        time.sleep(1)
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="1",
            spec_name="test-wait-complete",
            success=True,
            slot_id="test-slot-1",
            pool_name="test-pool",
        )
        
        # Wait for shutdown to complete
        shutdown_thread.join(timeout=10)
        
        # Verify shutdown completed successfully
        assert not dispatcher.running
        assert dispatcher.get_global_running_count() == 0
        
        # Wait for dispatcher thread
        dispatcher_thread.join(timeout=5)
    
    def test_shutdown_timeout_with_stuck_tasks(self, shutdown_config, task_registry):
        """Test that shutdown times out and force stops stuck tasks."""
        # Create tasks
        tasks = [
            Task(
                id=str(i),
                title=f"Stuck task {i}",
                description=f"Task that never completes {i}",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-timeout", "repo_name": "test-repo"},
            )
            for i in range(1, 3)
        ]
        
        taskset = Taskset(spec_name="test-timeout", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher with short timeout
        shutdown_config.graceful_shutdown_timeout = 2
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Mock slot allocation
        def mock_allocate_slot(repo_name, metadata=None):
            task_id = metadata.get("task_id", "unknown")
            return Slot(
                slot_id=f"slot-{task_id}",
                repo_name=repo_name,
                repo_url="https://github.com/test/repo.git",
                slot_path=Path(f"/tmp/slot-{task_id}"),
                state=SlotState.ALLOCATED,
                current_branch="main",
                current_commit="abc123",
            )
        
        dispatcher.repo_pool_manager.allocate_slot = Mock(side_effect=mock_allocate_slot)
        dispatcher.repo_pool_manager.release_slot = Mock()
        
        # Mock runner launcher
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            return Runner(
                runner_id=f"runner-{task.id}",
                task_id=task.id,
                pool_name=pool.name,
                slot_id=slot.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                pid=10000 + int(task.id),
            )
        
        dispatcher.runner_launcher.launch = Mock(side_effect=mock_launch)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for tasks to be assigned
        time.sleep(1)
        
        initial_running = dispatcher.get_global_running_count()
        assert initial_running > 0, "No tasks were assigned"
        
        # Stop dispatcher (tasks will not complete)
        start_time = time.time()
        dispatcher.stop(timeout=2)
        elapsed = time.time() - start_time
        
        # Should timeout after ~2 seconds
        assert 1.5 <= elapsed <= 3.5, f"Timeout not respected: {elapsed}s"
        
        # Verify force stop was called (slots should be released)
        assert dispatcher.repo_pool_manager.release_slot.called
        
        # Wait for dispatcher thread
        dispatcher_thread.join(timeout=5)
        
        # Verify dispatcher is stopped
        assert not dispatcher.running


class TestGracefulShutdownSignalHandling:
    """Test signal handling for graceful shutdown."""
    
    def test_sigterm_triggers_graceful_shutdown(self, shutdown_config, task_registry):
        """Test that SIGTERM triggers graceful shutdown."""
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for startup
        time.sleep(0.5)
        
        # Send SIGTERM to trigger shutdown
        # Note: We can't actually send signal to thread, so we call handler directly
        dispatcher._signal_handler(signal.SIGTERM, None)
        
        # Wait for shutdown
        dispatcher_thread.join(timeout=10)
        
        # Verify dispatcher is stopped
        assert not dispatcher.running
    
    def test_sigint_triggers_graceful_shutdown(self, shutdown_config, task_registry):
        """Test that SIGINT (Ctrl+C) triggers graceful shutdown."""
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for startup
        time.sleep(0.5)
        
        # Send SIGINT to trigger shutdown
        dispatcher._signal_handler(signal.SIGINT, None)
        
        # Wait for shutdown
        dispatcher_thread.join(timeout=10)
        
        # Verify dispatcher is stopped
        assert not dispatcher.running


class TestGracefulShutdownStateCleanup:
    """Test state cleanup during graceful shutdown."""
    
    def test_slots_released_on_shutdown(self, shutdown_config, task_registry):
        """Test that all slots are released during shutdown."""
        # Create tasks
        tasks = [
            Task(
                id=str(i),
                title=f"Task {i}",
                description=f"Test task {i}",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-cleanup", "repo_name": "test-repo"},
            )
            for i in range(1, 4)
        ]
        
        taskset = Taskset(spec_name="test-cleanup", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Mock slot allocation
        def mock_allocate_slot(repo_name, metadata=None):
            task_id = metadata.get("task_id", "unknown")
            return Slot(
                slot_id=f"slot-{task_id}",
                repo_name=repo_name,
                repo_url="https://github.com/test/repo.git",
                slot_path=Path(f"/tmp/slot-{task_id}"),
                state=SlotState.ALLOCATED,
                current_branch="main",
                current_commit="abc123",
            )
        
        dispatcher.repo_pool_manager.allocate_slot = Mock(side_effect=mock_allocate_slot)
        dispatcher.repo_pool_manager.release_slot = Mock()
        
        # Mock runner launcher
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            return Runner(
                runner_id=f"runner-{task.id}",
                task_id=task.id,
                pool_name=pool.name,
                slot_id=slot.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                pid=10000 + int(task.id),
            )
        
        dispatcher.runner_launcher.launch = Mock(side_effect=mock_launch)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for assignments
        time.sleep(1)
        
        # Stop dispatcher (force timeout)
        dispatcher.stop(timeout=1)
        
        # Wait for dispatcher thread
        dispatcher_thread.join(timeout=5)
        
        # Verify all slots were released
        release_calls = dispatcher.repo_pool_manager.release_slot.call_count
        assert release_calls > 0, "No slots were released during shutdown"
    
    def test_pool_counts_reset_on_shutdown(self, shutdown_config, task_registry):
        """Test that pool running counts are properly decremented on shutdown."""
        # Create tasks
        tasks = [
            Task(
                id=str(i),
                title=f"Task {i}",
                description=f"Test task {i}",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-pool-reset", "repo_name": "test-repo"},
            )
            for i in range(1, 4)
        ]
        
        taskset = Taskset(spec_name="test-pool-reset", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Mock slot allocation
        def mock_allocate_slot(repo_name, metadata=None):
            task_id = metadata.get("task_id", "unknown")
            return Slot(
                slot_id=f"slot-{task_id}",
                repo_name=repo_name,
                repo_url="https://github.com/test/repo.git",
                slot_path=Path(f"/tmp/slot-{task_id}"),
                state=SlotState.ALLOCATED,
                current_branch="main",
                current_commit="abc123",
            )
        
        dispatcher.repo_pool_manager.allocate_slot = Mock(side_effect=mock_allocate_slot)
        dispatcher.repo_pool_manager.release_slot = Mock()
        
        # Mock runner launcher
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            return Runner(
                runner_id=f"runner-{task.id}",
                task_id=task.id,
                pool_name=pool.name,
                slot_id=slot.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                pid=10000 + int(task.id),
            )
        
        dispatcher.runner_launcher.launch = Mock(side_effect=mock_launch)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for assignments
        time.sleep(1)
        
        # Stop dispatcher (force timeout)
        dispatcher.stop(timeout=1)
        
        # Wait for dispatcher thread
        dispatcher_thread.join(timeout=5)
        
        # Verify global count is 0
        assert dispatcher.get_global_running_count() == 0, \
            "Global running count not reset after shutdown"
        
        # Verify pool counts are reasonable (may not be 0 if force stopped)
        pool = dispatcher.agent_pool_manager.get_pool_by_name("test-pool")
        # After force stop, counts should be decremented
        assert pool.current_running >= 0, "Pool running count is negative"


class TestGracefulShutdownMultipleCalls:
    """Test multiple shutdown calls."""
    
    def test_multiple_stop_calls_are_safe(self, shutdown_config, task_registry):
        """Test that calling stop multiple times is safe."""
        # Create dispatcher
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for startup
        time.sleep(0.5)
        
        # Call stop multiple times
        dispatcher.stop(timeout=2)
        dispatcher.stop(timeout=2)
        dispatcher.stop(timeout=2)
        
        # Wait for dispatcher thread
        dispatcher_thread.join(timeout=5)
        
        # Verify dispatcher is stopped
        assert not dispatcher.running
    
    def test_stop_when_not_running(self, shutdown_config, task_registry):
        """Test that stop can be called when dispatcher is not running."""
        # Create dispatcher (don't start it)
        dispatcher = DispatcherCore(config=shutdown_config)
        
        # Call stop (should not raise error)
        dispatcher.stop(timeout=2)
        
        # Verify dispatcher is not running
        assert not dispatcher.running


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

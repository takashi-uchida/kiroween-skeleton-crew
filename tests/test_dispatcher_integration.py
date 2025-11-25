"""
Integration tests for Dispatcher - Real task assignment flow.

Tests the complete end-to-end flow of task assignment including:
- Task monitoring and polling
- Task queueing
- Scheduling
- Slot allocation
- Runner launching
- Task Registry updates
- Event recording
- Runner monitoring
- Task completion

Requirements: All dispatcher requirements
"""

import pytest
import time
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from necrocode.dispatcher import (
    DispatcherCore,
    DispatcherConfig,
    SchedulingPolicy,
    AgentPool,
    PoolType,
)
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, Taskset
from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.models import Slot, SlotState


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    task_registry_dir = tempfile.mkdtemp(prefix="test_dispatcher_registry_")
    repo_pool_dir = tempfile.mkdtemp(prefix="test_dispatcher_pool_")
    
    yield {
        "task_registry": Path(task_registry_dir),
        "repo_pool": Path(repo_pool_dir),
    }
    
    # Cleanup
    shutil.rmtree(task_registry_dir, ignore_errors=True)
    shutil.rmtree(repo_pool_dir, ignore_errors=True)


@pytest.fixture
def integration_config(temp_dirs):
    """Create integration test configuration."""
    config = DispatcherConfig(
        poll_interval=0.5,  # Fast polling for tests
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=5,
        heartbeat_timeout=10,
        retry_max_attempts=2,
        graceful_shutdown_timeout=10,
        task_registry_dir=str(temp_dirs["task_registry"]),
    )
    
    # Add test pools
    config.agent_pools = [
        AgentPool(
            name="test-local",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=2,
            enabled=True,
        ),
        AgentPool(
            name="test-docker",
            type=PoolType.DOCKER,
            max_concurrency=3,
            enabled=True,
            config={"image": "test:latest"},
        ),
    ]
    
    config.skill_mapping = {
        "backend": ["test-docker"],
        "frontend": ["test-docker"],
        "default": ["test-local"],
    }
    
    return config


@pytest.fixture
def task_registry(temp_dirs):
    """Create a Task Registry for testing."""
    return TaskRegistry(registry_dir=str(temp_dirs["task_registry"]))


@pytest.fixture
def test_taskset():
    """Create a test taskset with multiple tasks."""
    return Taskset(
        spec_name="test-integration",
        tasks=[
            Task(
                id="1",
                title="Setup database",
                description="Initialize database schema",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-integration", "repo_name": "test-repo"},
            ),
            Task(
                id="2",
                title="Implement API",
                description="Create REST API endpoints",
                state=TaskState.PENDING,
                priority=8,
                dependencies=["1"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-integration", "repo_name": "test-repo"},
            ),
            Task(
                id="3",
                title="Add tests",
                description="Write unit tests",
                state=TaskState.PENDING,
                priority=5,
                dependencies=["2"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"spec_name": "test-integration", "repo_name": "test-repo"},
            ),
        ],
    )


class TestDispatcherIntegrationBasicFlow:
    """Test basic task assignment flow."""
    
    def test_single_task_assignment_flow(self, integration_config, task_registry, test_taskset):
        """Test complete flow for a single task assignment."""
        # Setup: Create taskset in registry
        task_registry.create_taskset(test_taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=integration_config)
        
        # Mock slot allocation and runner launch
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
        
        # Mock runner launcher to return immediately
        from necrocode.dispatcher.models import Runner, RunnerState
        mock_runner = Runner(
            runner_id="runner-1",
            task_id="1",
            pool_name="test-local",
            slot_id="test-slot-1",
            state=RunnerState.RUNNING,
            started_at=datetime.now(),
            pid=12345,
        )
        dispatcher.runner_launcher.launch = Mock(return_value=mock_runner)
        
        # Start dispatcher in background
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for task to be assigned
        max_wait = 5
        start_time = time.time()
        task_assigned = False
        
        while time.time() - start_time < max_wait:
            # Check if task was assigned
            taskset = task_registry.get_taskset("test-integration")
            task = next((t for t in taskset.tasks if t.id == "1"), None)
            
            if task and task.state == TaskState.RUNNING:
                task_assigned = True
                break
            
            time.sleep(0.2)
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
        
        # Verify task was assigned
        assert task_assigned, "Task should have been assigned"
        
        # Verify slot was allocated
        dispatcher.repo_pool_manager.allocate_slot.assert_called()
        
        # Verify runner was launched
        dispatcher.runner_launcher.launch.assert_called_once()
        
        # Verify task state was updated
        taskset = task_registry.get_taskset("test-integration")
        task = next((t for t in taskset.tasks if t.id == "1"), None)
        assert task.state == TaskState.RUNNING
        assert "runner_id" in task.metadata
    
    def test_multiple_tasks_sequential_assignment(
        self, integration_config, task_registry, test_taskset
    ):
        """Test sequential assignment of multiple tasks with dependencies."""
        # Setup: Create taskset in registry
        task_registry.create_taskset(test_taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=integration_config)
        
        # Mock slot allocation
        def mock_allocate_slot(repo_name, metadata=None):
            slot_id = f"slot-{metadata.get('task_id', 'unknown')}"
            return Slot(
                slot_id=slot_id,
                repo_name=repo_name,
                repo_url="https://github.com/test/repo.git",
                slot_path=Path(f"/tmp/{slot_id}"),
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
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for first task to be assigned
        time.sleep(2)
        
        # Complete first task to unblock second task
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="1",
            spec_name="test-integration",
            success=True,
            slot_id="slot-1",
            pool_name="test-local",
        )
        
        # Wait for second task to be assigned
        time.sleep(2)
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
        
        # Verify both tasks were processed
        taskset = task_registry.get_taskset("test-integration")
        task1 = next((t for t in taskset.tasks if t.id == "1"), None)
        task2 = next((t for t in taskset.tasks if t.id == "2"), None)
        
        assert task1.state == TaskState.DONE
        assert task2.state in [TaskState.RUNNING, TaskState.READY]  # May still be running


class TestDispatcherIntegrationRetry:
    """Test retry logic in integration."""
    
    def test_task_retry_on_failure(self, integration_config, task_registry):
        """Test that failed tasks are retried."""
        # Create simple taskset
        taskset = Taskset(
            spec_name="test-retry",
            tasks=[
                Task(
                    id="1",
                    title="Flaky task",
                    description="Task that may fail",
                    state=TaskState.READY,
                    priority=10,
                    dependencies=[],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    metadata={"spec_name": "test-retry", "repo_name": "test-repo"},
                ),
            ],
        )
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=integration_config)
        dispatcher.retry_manager.initial_delay = 0.5  # Short delay for testing
        
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
        launch_count = [0]
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            launch_count[0] += 1
            return Runner(
                runner_id=f"runner-{launch_count[0]}",
                task_id=task.id,
                pool_name=pool.name,
                slot_id=slot.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                pid=10000 + launch_count[0],
            )
        
        dispatcher.runner_launcher.launch = Mock(side_effect=mock_launch)
        
        # Start dispatcher
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for first assignment
        time.sleep(1)
        
        # Simulate first failure
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="1",
            spec_name="test-retry",
            success=False,
            slot_id="test-slot-1",
            pool_name="test-local",
            failure_reason="simulated failure",
        )
        
        # Wait for retry (with backoff)
        time.sleep(2)
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
        
        # Verify task was retried
        assert launch_count[0] >= 2, "Task should have been retried at least once"
        
        # Verify retry info was recorded
        retry_info = dispatcher.retry_manager.get_retry_info("1")
        assert retry_info is not None
        assert retry_info.retry_count >= 1


class TestDispatcherIntegrationConcurrency:
    """Test concurrency control in integration."""
    
    def test_global_concurrency_limit(self, integration_config, task_registry):
        """Test that global concurrency limit is enforced."""
        # Set low global limit
        integration_config.max_global_concurrency = 2
        
        # Create taskset with many tasks
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
                metadata={"spec_name": "test-concurrency", "repo_name": "test-repo"},
            )
            for i in range(1, 6)  # 5 tasks
        ]
        
        taskset = Taskset(spec_name="test-concurrency", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=integration_config)
        
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
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for tasks to be assigned
        time.sleep(2)
        
        # Check that only 2 tasks are running (global limit)
        running_count = dispatcher.get_global_running_count()
        assert running_count <= 2, f"Global limit exceeded: {running_count} > 2"
        
        # Complete one task
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="1",
            spec_name="test-concurrency",
            success=True,
            slot_id="slot-1",
            pool_name="test-local",
        )
        
        # Wait for another task to be assigned
        time.sleep(1)
        
        # Check that limit is still enforced
        running_count = dispatcher.get_global_running_count()
        assert running_count <= 2, f"Global limit exceeded after completion: {running_count} > 2"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestDispatcherIntegrationEvents:
    """Test event recording in integration."""
    
    def test_events_recorded_during_assignment(self, integration_config, task_registry):
        """Test that all events are recorded during task assignment."""
        # Create simple taskset
        taskset = Taskset(
            spec_name="test-events",
            tasks=[
                Task(
                    id="1",
                    title="Test task",
                    description="Task for event testing",
                    state=TaskState.READY,
                    priority=10,
                    dependencies=[],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    metadata={"spec_name": "test-events", "repo_name": "test-repo"},
                ),
            ],
        )
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=integration_config)
        
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
            pool_name="test-local",
            slot_id="test-slot-1",
            state=RunnerState.RUNNING,
            started_at=datetime.now(),
            pid=12345,
        )
        dispatcher.runner_launcher.launch = Mock(return_value=mock_runner)
        
        # Start dispatcher
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for assignment
        time.sleep(2)
        
        # Complete task
        dispatcher.handle_runner_completion(
            runner_id="runner-1",
            task_id="1",
            spec_name="test-events",
            success=True,
            slot_id="test-slot-1",
            pool_name="test-local",
        )
        
        # Wait for completion processing
        time.sleep(1)
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
        
        # Verify events were recorded
        stats = dispatcher.event_recorder.get_statistics()
        assert stats["total_events"] >= 3  # TaskAssigned, RunnerStarted, RunnerFinished, TaskCompleted
        assert stats["successful_records"] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

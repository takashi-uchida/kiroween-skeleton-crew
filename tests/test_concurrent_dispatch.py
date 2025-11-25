"""
Integration tests for concurrent task dispatching.

Tests concurrent execution control including:
- Pool-level concurrency limits
- Global concurrency limits
- Concurrent task assignment
- Pool utilization tracking
- Concurrent completion handling

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
import time
import tempfile
import shutil
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

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
    task_registry_dir = tempfile.mkdtemp(prefix="test_concurrent_registry_")
    
    yield {"task_registry": Path(task_registry_dir)}
    
    shutil.rmtree(task_registry_dir, ignore_errors=True)


@pytest.fixture
def concurrent_config(temp_dirs):
    """Create configuration for concurrent testing."""
    config = DispatcherConfig(
        poll_interval=0.3,
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=10,
        heartbeat_timeout=30,
        retry_max_attempts=2,
        graceful_shutdown_timeout=10,
        task_registry_dir=str(temp_dirs["task_registry"]),
    )
    
    # Multiple pools with different concurrency limits
    config.agent_pools = [
        AgentPool(
            name="pool-small",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=2,
            enabled=True,
        ),
        AgentPool(
            name="pool-medium",
            type=PoolType.DOCKER,
            max_concurrency=5,
            enabled=True,
        ),
        AgentPool(
            name="pool-large",
            type=PoolType.KUBERNETES,
            max_concurrency=10,
            enabled=True,
        ),
    ]
    
    config.skill_mapping = {
        "backend": ["pool-medium", "pool-large"],
        "frontend": ["pool-medium"],
        "default": ["pool-small"],
    }
    
    return config


@pytest.fixture
def task_registry(temp_dirs):
    """Create a Task Registry for testing."""
    return TaskRegistry(registry_dir=str(temp_dirs["task_registry"]))


class TestPoolConcurrencyLimits:
    """Test pool-level concurrency limits."""
    
    def test_pool_max_concurrency_enforced(self, concurrent_config, task_registry):
        """Test that pool max concurrency is enforced."""
        # Create tasks for small pool (max_concurrency=2)
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
                metadata={"spec_name": "test-pool-limit", "repo_name": "test-repo"},
            )
            for i in range(1, 6)  # 5 tasks for pool with limit 2
        ]
        
        taskset = Taskset(spec_name="test-pool-limit", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=concurrent_config)
        
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
        time.sleep(2)
        
        # Check pool running count
        pool = dispatcher.agent_pool_manager.get_pool_by_name("pool-small")
        assert pool.current_running <= pool.max_concurrency, \
            f"Pool limit exceeded: {pool.current_running} > {pool.max_concurrency}"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
    
    def test_multiple_pools_concurrent_execution(self, concurrent_config, task_registry):
        """Test concurrent execution across multiple pools."""
        # Create tasks for different pools
        tasks = []
        
        # Tasks for pool-small (2 concurrent)
        for i in range(1, 4):
            tasks.append(Task(
                id=f"small-{i}",
                title=f"Small task {i}",
                description=f"Task for small pool {i}",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={
                    "spec_name": "test-multi-pool",
                    "repo_name": "test-repo",
                    "required_skill": "default",
                },
            ))
        
        # Tasks for pool-medium (5 concurrent)
        for i in range(1, 7):
            tasks.append(Task(
                id=f"medium-{i}",
                title=f"Medium task {i}",
                description=f"Task for medium pool {i}",
                state=TaskState.READY,
                priority=10,
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={
                    "spec_name": "test-multi-pool",
                    "repo_name": "test-repo",
                    "required_skill": "frontend",
                },
            ))
        
        taskset = Taskset(spec_name="test-multi-pool", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=concurrent_config)
        
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
                pid=10000,
            )
        
        dispatcher.runner_launcher.launch = Mock(side_effect=mock_launch)
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for assignments
        time.sleep(2)
        
        # Check each pool's limits
        pool_small = dispatcher.agent_pool_manager.get_pool_by_name("pool-small")
        pool_medium = dispatcher.agent_pool_manager.get_pool_by_name("pool-medium")
        
        assert pool_small.current_running <= pool_small.max_concurrency
        assert pool_medium.current_running <= pool_medium.max_concurrency
        
        # Verify total running is within global limit
        total_running = dispatcher.get_global_running_count()
        assert total_running <= concurrent_config.max_global_concurrency
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestGlobalConcurrencyLimits:
    """Test global concurrency limits."""
    
    def test_global_limit_across_pools(self, concurrent_config, task_registry):
        """Test that global limit is enforced across all pools."""
        # Set strict global limit
        concurrent_config.max_global_concurrency = 3
        
        # Create many tasks
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
                metadata={"spec_name": "test-global-limit", "repo_name": "test-repo"},
            )
            for i in range(1, 11)  # 10 tasks
        ]
        
        taskset = Taskset(spec_name="test-global-limit", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=concurrent_config)
        
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
        
        # Monitor global running count over time
        max_observed = 0
        for _ in range(10):
            time.sleep(0.3)
            current = dispatcher.get_global_running_count()
            max_observed = max(max_observed, current)
            
            # Verify limit is never exceeded
            assert current <= concurrent_config.max_global_concurrency, \
                f"Global limit exceeded: {current} > {concurrent_config.max_global_concurrency}"
        
        # Verify we actually reached the limit (tasks were assigned)
        assert max_observed >= 1, "No tasks were assigned"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
    
    def test_global_limit_with_completions(self, concurrent_config, task_registry):
        """Test global limit with task completions allowing new assignments."""
        # Set global limit
        concurrent_config.max_global_concurrency = 2
        
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
                metadata={"spec_name": "test-global-completion", "repo_name": "test-repo"},
            )
            for i in range(1, 6)  # 5 tasks
        ]
        
        taskset = Taskset(spec_name="test-global-completion", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=concurrent_config)
        
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
        
        # Track launched tasks
        launched_tasks = []
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            launched_tasks.append(task.id)
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
        
        # Wait for initial assignments
        time.sleep(1)
        
        # Should have 2 tasks running (global limit)
        assert dispatcher.get_global_running_count() == 2
        
        # Complete first task
        if len(launched_tasks) >= 1:
            dispatcher.handle_runner_completion(
                runner_id=f"runner-{launched_tasks[0]}",
                task_id=launched_tasks[0],
                spec_name="test-global-completion",
                success=True,
                slot_id=f"slot-{launched_tasks[0]}",
                pool_name="pool-small",
            )
        
        # Wait for new assignment
        time.sleep(1)
        
        # Should still be at limit (new task assigned)
        current_running = dispatcher.get_global_running_count()
        assert current_running <= 2
        
        # Verify more than 2 tasks were launched total
        assert len(launched_tasks) >= 3, "New tasks should have been assigned after completion"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestConcurrentCompletionHandling:
    """Test handling of concurrent task completions."""
    
    def test_concurrent_completion_notifications(self, concurrent_config, task_registry):
        """Test handling multiple completion notifications concurrently."""
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
                metadata={"spec_name": "test-concurrent-completion", "repo_name": "test-repo"},
            )
            for i in range(1, 6)
        ]
        
        taskset = Taskset(spec_name="test-concurrent-completion", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=concurrent_config)
        
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
        
        # Send multiple completion notifications concurrently
        completion_threads = []
        for i in range(1, 4):
            thread = threading.Thread(
                target=dispatcher.handle_runner_completion,
                kwargs={
                    "runner_id": f"runner-{i}",
                    "task_id": str(i),
                    "spec_name": "test-concurrent-completion",
                    "success": True,
                    "slot_id": f"slot-{i}",
                    "pool_name": "pool-small",
                }
            )
            completion_threads.append(thread)
            thread.start()
        
        # Wait for all completions
        for thread in completion_threads:
            thread.join(timeout=5)
        
        # Wait a bit for processing
        time.sleep(1)
        
        # Verify counts are consistent
        global_count = dispatcher.get_global_running_count()
        assert global_count >= 0, "Global count should not be negative"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestPoolUtilizationTracking:
    """Test pool utilization tracking during concurrent execution."""
    
    def test_pool_utilization_metrics(self, concurrent_config, task_registry):
        """Test that pool utilization is tracked correctly."""
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
                metadata={"spec_name": "test-utilization", "repo_name": "test-repo"},
            )
            for i in range(1, 6)
        ]
        
        taskset = Taskset(spec_name="test-utilization", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=concurrent_config)
        
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
        
        # Get pool statuses
        pool_statuses = dispatcher.agent_pool_manager.get_all_pool_statuses()
        
        # Verify utilization is calculated
        for status in pool_statuses:
            assert 0.0 <= status.utilization <= 1.0, \
                f"Invalid utilization for {status.pool_name}: {status.utilization}"
            
            # If pool has running tasks, utilization should be > 0
            if status.current_running > 0:
                assert status.utilization > 0, \
                    f"Pool {status.pool_name} has running tasks but 0 utilization"
        
        # Get metrics
        metrics = dispatcher.metrics_collector.get_metrics()
        assert "pool_utilization" in metrics
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

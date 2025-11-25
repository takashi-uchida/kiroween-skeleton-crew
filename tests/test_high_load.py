"""
High load tests for Dispatcher.

Tests dispatcher behavior under high load including:
- Many concurrent tasks
- Rapid task submissions
- Pool saturation
- Resource exhaustion scenarios
- Stress testing

Requirements: All dispatcher requirements
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
    task_registry_dir = tempfile.mkdtemp(prefix="test_highload_registry_")
    
    yield {"task_registry": Path(task_registry_dir)}
    
    shutil.rmtree(task_registry_dir, ignore_errors=True)


@pytest.fixture
def highload_config(temp_dirs):
    """Create configuration for high load testing."""
    config = DispatcherConfig(
        poll_interval=0.1,
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=100,
        heartbeat_timeout=60,
        retry_max_attempts=3,
        graceful_shutdown_timeout=30,
        task_registry_dir=str(temp_dirs["task_registry"]),
    )
    
    # Multiple large pools
    config.agent_pools = [
        AgentPool(
            name="pool-1",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=30,
            enabled=True,
        ),
        AgentPool(
            name="pool-2",
            type=PoolType.DOCKER,
            max_concurrency=40,
            enabled=True,
        ),
        AgentPool(
            name="pool-3",
            type=PoolType.KUBERNETES,
            max_concurrency=50,
            enabled=True,
        ),
    ]
    
    config.skill_mapping = {
        "backend": ["pool-2", "pool-3"],
        "frontend": ["pool-2"],
        "default": ["pool-1"],
    }
    
    return config


@pytest.fixture
def task_registry(temp_dirs):
    """Create a Task Registry for testing."""
    return TaskRegistry(registry_dir=str(temp_dirs["task_registry"]))


def create_large_taskset(count: int, spec_name: str = "highload-test") -> Taskset:
    """Create a large taskset for testing."""
    tasks = [
        Task(
            id=str(i),
            title=f"Task {i}",
            description=f"High load test task {i}",
            state=TaskState.READY,
            priority=(i % 10) + 1,
            dependencies=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"spec_name": spec_name, "repo_name": "test-repo"},
        )
        for i in range(1, count + 1)
    ]
    return Taskset(spec_name=spec_name, tasks=tasks)


class TestHighVolumeTaskSubmission:
    """Test high volume task submission."""
    
    def test_many_tasks_submitted_at_once(self, highload_config, task_registry):
        """Test handling of many tasks submitted simultaneously."""
        # Create large taskset
        task_count = 500
        taskset = create_large_taskset(task_count, "volume-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        
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
        assignment_lock = threading.Lock()
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            with assignment_lock:
                assignments.append(task.id)
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
        
        # Wait for assignments to reach global limit
        max_wait = 10
        start_time = time.time()
        while len(assignments) < highload_config.max_global_concurrency \
                and time.time() - start_time < max_wait:
            time.sleep(0.2)
        
        # Verify we reached the limit
        with assignment_lock:
            assigned_count = len(assignments)
        
        print(f"\nAssigned {assigned_count} tasks out of {task_count}")
        
        # Should have assigned up to global limit
        assert assigned_count > 0, "No tasks were assigned"
        assert assigned_count <= highload_config.max_global_concurrency
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
    
    def test_rapid_task_completion_and_reassignment(self, highload_config, task_registry):
        """Test rapid task completions triggering new assignments."""
        # Create taskset
        task_count = 200
        taskset = create_large_taskset(task_count, "rapid-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        
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
        assignment_lock = threading.Lock()
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            with assignment_lock:
                assignments.append(task.id)
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
        
        # Wait for initial assignments
        time.sleep(1)
        
        # Rapidly complete tasks to trigger reassignments
        completion_count = 0
        for i in range(50):
            with assignment_lock:
                if i < len(assignments):
                    task_id = assignments[i]
                    dispatcher.handle_runner_completion(
                        runner_id=f"runner-{task_id}",
                        task_id=task_id,
                        spec_name="rapid-test",
                        success=True,
                        slot_id=f"slot-{task_id}",
                        pool_name="pool-1",
                    )
                    completion_count += 1
            time.sleep(0.01)  # Very short delay
        
        # Wait for reassignments
        time.sleep(2)
        
        # Verify more tasks were assigned after completions
        with assignment_lock:
            final_count = len(assignments)
        
        print(f"\nCompleted {completion_count} tasks, total assigned: {final_count}")
        
        # Should have assigned more than initial batch
        assert final_count > completion_count, "No reassignments occurred"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestPoolSaturation:
    """Test behavior when pools are saturated."""
    
    def test_all_pools_saturated(self, highload_config, task_registry):
        """Test behavior when all pools reach max concurrency."""
        # Create many tasks
        task_count = 200
        taskset = create_large_taskset(task_count, "saturation-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        
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
        
        # Wait for saturation
        time.sleep(2)
        
        # Check pool utilization
        pool_statuses = dispatcher.agent_pool_manager.get_all_pool_statuses()
        
        saturated_pools = 0
        for status in pool_statuses:
            print(f"\nPool {status.pool_name}: {status.current_running}/{status.max_concurrency} "
                  f"(utilization: {status.utilization:.1%})")
            
            if status.utilization >= 0.8:  # 80% or more
                saturated_pools += 1
        
        # At least one pool should be highly utilized
        assert saturated_pools > 0, "No pools reached high utilization"
        
        # Queue should have remaining tasks
        queue_size = dispatcher.task_queue.size()
        print(f"\nQueue size: {queue_size}")
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
    
    def test_queue_growth_under_saturation(self, highload_config, task_registry):
        """Test that queue grows appropriately when pools are saturated."""
        # Create many tasks
        task_count = 300
        taskset = create_large_taskset(task_count, "queue-growth-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        
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
        
        # Monitor queue size over time
        queue_sizes = []
        for _ in range(10):
            time.sleep(0.3)
            queue_sizes.append(dispatcher.task_queue.size())
        
        print(f"\nQueue sizes over time: {queue_sizes}")
        
        # Queue should have grown initially as pools saturated
        max_queue_size = max(queue_sizes)
        assert max_queue_size > 0, "Queue never grew"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestStressScenarios:
    """Test stress scenarios."""
    
    def test_continuous_operation_under_load(self, highload_config, task_registry):
        """Test continuous operation under sustained load."""
        # Create large taskset
        task_count = 100
        taskset = create_large_taskset(task_count, "stress-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        
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
        assignment_lock = threading.Lock()
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            with assignment_lock:
                assignments.append(task.id)
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
        
        # Run for extended period with continuous completions
        duration = 5  # seconds
        start_time = time.time()
        completion_count = 0
        
        while time.time() - start_time < duration:
            # Complete some tasks
            with assignment_lock:
                if len(assignments) > completion_count:
                    task_id = assignments[completion_count]
                    dispatcher.handle_runner_completion(
                        runner_id=f"runner-{task_id}",
                        task_id=task_id,
                        spec_name="stress-test",
                        success=True,
                        slot_id=f"slot-{task_id}",
                        pool_name="pool-1",
                    )
                    completion_count += 1
            
            time.sleep(0.1)
        
        elapsed = time.time() - start_time
        
        # Get final stats
        with assignment_lock:
            total_assigned = len(assignments)
        
        print(f"\nStress test results:")
        print(f"  Duration: {elapsed:.1f}s")
        print(f"  Total assigned: {total_assigned}")
        print(f"  Completed: {completion_count}")
        print(f"  Rate: {total_assigned/elapsed:.1f} assignments/sec")
        
        # Should have processed many tasks
        assert total_assigned > 20, "Too few tasks processed"
        assert completion_count > 10, "Too few completions"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)
    
    def test_mixed_success_and_failure_under_load(self, highload_config, task_registry):
        """Test handling mixed success and failures under load."""
        # Create taskset
        task_count = 100
        taskset = create_large_taskset(task_count, "mixed-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        dispatcher.retry_manager.initial_delay = 0.1  # Fast retries
        
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
        assignment_lock = threading.Lock()
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            with assignment_lock:
                assignments.append(task.id)
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
        time.sleep(1)
        
        # Complete tasks with mixed results
        success_count = 0
        failure_count = 0
        
        for i in range(min(30, len(assignments))):
            with assignment_lock:
                if i < len(assignments):
                    task_id = assignments[i]
                    # Alternate success and failure
                    success = (i % 2 == 0)
                    
                    dispatcher.handle_runner_completion(
                        runner_id=f"runner-{task_id}",
                        task_id=task_id,
                        spec_name="mixed-test",
                        success=success,
                        slot_id=f"slot-{task_id}",
                        pool_name="pool-1",
                        failure_reason="simulated failure" if not success else None,
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
            
            time.sleep(0.05)
        
        # Wait for retries
        time.sleep(2)
        
        print(f"\nMixed results:")
        print(f"  Successes: {success_count}")
        print(f"  Failures: {failure_count}")
        print(f"  Total assignments: {len(assignments)}")
        
        # Verify both successes and failures were handled
        assert success_count > 0, "No successful completions"
        assert failure_count > 0, "No failures"
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


class TestResourceExhaustion:
    """Test behavior under resource exhaustion."""
    
    def test_no_available_slots(self, highload_config, task_registry):
        """Test behavior when no slots are available."""
        # Create tasks
        task_count = 50
        taskset = create_large_taskset(task_count, "no-slots-test")
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=highload_config)
        
        # Mock slot allocation to fail
        dispatcher.repo_pool_manager.allocate_slot = Mock(return_value=None)
        dispatcher.repo_pool_manager.release_slot = Mock()
        
        # Mock runner launcher (should not be called)
        dispatcher.runner_launcher.launch = Mock()
        
        # Start dispatcher
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait
        time.sleep(2)
        
        # Verify no runners were launched
        assert not dispatcher.runner_launcher.launch.called, \
            "Runners were launched despite no slots"
        
        # Queue should have tasks
        queue_size = dispatcher.task_queue.size()
        assert queue_size > 0, "Queue should have tasks waiting for slots"
        
        print(f"\nNo slots scenario: {queue_size} tasks queued")
        
        # Stop dispatcher
        dispatcher.stop(timeout=5)
        dispatcher_thread.join(timeout=10)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print output

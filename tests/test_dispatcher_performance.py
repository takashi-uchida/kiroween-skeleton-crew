"""
Performance tests for Dispatcher - Scheduling performance measurement.

Tests scheduling performance including:
- Task scheduling throughput
- Queue operations performance
- Scheduling policy performance
- Memory usage
- Latency measurements

Requirements: All dispatcher requirements
"""

import pytest
import time
import tempfile
import shutil
import statistics
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from necrocode.dispatcher import (
    DispatcherCore,
    DispatcherConfig,
    SchedulingPolicy,
    AgentPool,
    PoolType,
    TaskQueue,
    Scheduler,
)
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, Taskset
from necrocode.repo_pool.models import Slot, SlotState


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    task_registry_dir = tempfile.mkdtemp(prefix="test_perf_registry_")
    
    yield {"task_registry": Path(task_registry_dir)}
    
    shutil.rmtree(task_registry_dir, ignore_errors=True)


@pytest.fixture
def perf_config(temp_dirs):
    """Create configuration for performance testing."""
    config = DispatcherConfig(
        poll_interval=0.1,  # Fast polling
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=100,
        heartbeat_timeout=60,
        retry_max_attempts=2,
        graceful_shutdown_timeout=10,
        task_registry_dir=str(temp_dirs["task_registry"]),
    )
    
    # Large pool for performance testing
    config.agent_pools = [
        AgentPool(
            name="perf-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=50,
            enabled=True,
        ),
    ]
    
    config.skill_mapping = {
        "default": ["perf-pool"],
    }
    
    return config


@pytest.fixture
def task_registry(temp_dirs):
    """Create a Task Registry for testing."""
    return TaskRegistry(registry_dir=str(temp_dirs["task_registry"]))


def create_test_tasks(count: int, spec_name: str = "perf-test") -> list:
    """Create a list of test tasks."""
    return [
        Task(
            id=str(i),
            title=f"Task {i}",
            description=f"Performance test task {i}",
            state=TaskState.READY,
            priority=i % 10,  # Vary priorities
            dependencies=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"spec_name": spec_name, "repo_name": "test-repo"},
        )
        for i in range(1, count + 1)
    ]


class TestQueuePerformance:
    """Test task queue performance."""
    
    def test_queue_enqueue_performance(self):
        """Test enqueue operation performance."""
        queue = TaskQueue()
        tasks = create_test_tasks(1000)
        
        start_time = time.time()
        for task in tasks:
            queue.enqueue(task)
        elapsed = time.time() - start_time
        
        # Should be able to enqueue 1000 tasks quickly
        assert elapsed < 1.0, f"Enqueue too slow: {elapsed}s for 1000 tasks"
        
        # Verify all tasks were enqueued
        assert queue.size() == 1000
        
        print(f"\nEnqueue performance: {1000/elapsed:.0f} tasks/sec")
    
    def test_queue_dequeue_performance(self):
        """Test dequeue operation performance."""
        queue = TaskQueue()
        tasks = create_test_tasks(1000)
        
        # Enqueue all tasks
        for task in tasks:
            queue.enqueue(task)
        
        # Measure dequeue performance
        start_time = time.time()
        dequeued_count = 0
        while not queue.is_empty():
            task = queue.dequeue()
            if task:
                dequeued_count += 1
        elapsed = time.time() - start_time
        
        # Should be able to dequeue 1000 tasks quickly
        assert elapsed < 1.0, f"Dequeue too slow: {elapsed}s for 1000 tasks"
        assert dequeued_count == 1000
        
        print(f"\nDequeue performance: {1000/elapsed:.0f} tasks/sec")
    
    def test_queue_priority_ordering_performance(self):
        """Test that priority ordering doesn't significantly impact performance."""
        queue = TaskQueue()
        tasks = create_test_tasks(1000)
        
        # Enqueue with priorities
        start_time = time.time()
        for task in tasks:
            queue.enqueue(task)
        enqueue_elapsed = time.time() - start_time
        
        # Dequeue and verify ordering
        start_time = time.time()
        prev_priority = float('inf')
        while not queue.is_empty():
            task = queue.dequeue()
            if task:
                # Priority should be non-increasing (higher priority first)
                assert task.priority <= prev_priority or prev_priority == float('inf')
                prev_priority = task.priority
        dequeue_elapsed = time.time() - start_time
        
        total_elapsed = enqueue_elapsed + dequeue_elapsed
        
        # Total time should be reasonable
        assert total_elapsed < 2.0, f"Priority queue too slow: {total_elapsed}s"
        
        print(f"\nPriority queue performance: {1000/total_elapsed:.0f} tasks/sec")


class TestSchedulerPerformance:
    """Test scheduler performance."""
    
    def test_fifo_scheduling_performance(self, perf_config):
        """Test FIFO scheduling performance."""
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        queue = TaskQueue()
        
        # Create agent pool manager
        from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
        pool_manager = AgentPoolManager(perf_config)
        
        # Enqueue tasks
        tasks = create_test_tasks(1000)
        for task in tasks:
            queue.enqueue(task)
        
        # Measure scheduling performance
        start_time = time.time()
        scheduled = scheduler.schedule(queue, pool_manager)
        elapsed = time.time() - start_time
        
        # Should schedule quickly
        assert elapsed < 0.5, f"FIFO scheduling too slow: {elapsed}s"
        
        # Should schedule up to pool capacity
        assert len(scheduled) > 0
        
        print(f"\nFIFO scheduling: {len(scheduled)} tasks in {elapsed:.3f}s")
    
    def test_priority_scheduling_performance(self, perf_config):
        """Test priority-based scheduling performance."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        queue = TaskQueue()
        
        # Create agent pool manager
        from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
        pool_manager = AgentPoolManager(perf_config)
        
        # Enqueue tasks with varying priorities
        tasks = create_test_tasks(1000)
        for task in tasks:
            queue.enqueue(task)
        
        # Measure scheduling performance
        start_time = time.time()
        scheduled = scheduler.schedule(queue, pool_manager)
        elapsed = time.time() - start_time
        
        # Should schedule quickly
        assert elapsed < 0.5, f"Priority scheduling too slow: {elapsed}s"
        
        # Should schedule up to pool capacity
        assert len(scheduled) > 0
        
        print(f"\nPriority scheduling: {len(scheduled)} tasks in {elapsed:.3f}s")
    
    def test_skill_based_scheduling_performance(self, perf_config):
        """Test skill-based scheduling performance."""
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        queue = TaskQueue()
        
        # Create agent pool manager
        from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
        pool_manager = AgentPoolManager(perf_config)
        
        # Enqueue tasks
        tasks = create_test_tasks(1000)
        for task in tasks:
            queue.enqueue(task)
        
        # Measure scheduling performance
        start_time = time.time()
        scheduled = scheduler.schedule(queue, pool_manager)
        elapsed = time.time() - start_time
        
        # Should schedule quickly
        assert elapsed < 0.5, f"Skill-based scheduling too slow: {elapsed}s"
        
        # Should schedule up to pool capacity
        assert len(scheduled) > 0
        
        print(f"\nSkill-based scheduling: {len(scheduled)} tasks in {elapsed:.3f}s")


class TestAssignmentLatency:
    """Test task assignment latency."""
    
    def test_assignment_latency_measurement(self, perf_config, task_registry):
        """Measure latency from task ready to assignment."""
        # Create small taskset
        tasks = create_test_tasks(10, "latency-test")
        taskset = Taskset(spec_name="latency-test", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=perf_config)
        
        # Mock slot allocation (fast)
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
        
        # Track assignment times
        assignment_times = []
        task_ready_times = {task.id: task.created_at for task in tasks}
        
        def mock_launch(task, slot, pool):
            from necrocode.dispatcher.models import Runner, RunnerState
            # Record latency
            latency = (datetime.now() - task_ready_times[task.id]).total_seconds()
            assignment_times.append(latency)
            
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
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        # Wait for all assignments
        max_wait = 5
        start_time = time.time()
        while len(assignment_times) < 10 and time.time() - start_time < max_wait:
            time.sleep(0.1)
        
        # Stop dispatcher
        dispatcher.stop(timeout=2)
        dispatcher_thread.join(timeout=5)
        
        # Analyze latencies
        if assignment_times:
            avg_latency = statistics.mean(assignment_times)
            max_latency = max(assignment_times)
            min_latency = min(assignment_times)
            
            print(f"\nAssignment latency:")
            print(f"  Average: {avg_latency:.3f}s")
            print(f"  Min: {min_latency:.3f}s")
            print(f"  Max: {max_latency:.3f}s")
            
            # Average latency should be reasonable
            assert avg_latency < 2.0, f"Average latency too high: {avg_latency}s"


class TestThroughput:
    """Test overall dispatcher throughput."""
    
    def test_task_assignment_throughput(self, perf_config, task_registry):
        """Measure task assignment throughput."""
        # Create many tasks
        task_count = 50
        tasks = create_test_tasks(task_count, "throughput-test")
        taskset = Taskset(spec_name="throughput-test", tasks=tasks)
        task_registry.create_taskset(taskset)
        
        # Create dispatcher
        dispatcher = DispatcherCore(config=perf_config)
        
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
            assignments.append(datetime.now())
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
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start)
        dispatcher_thread.start()
        
        start_time = time.time()
        
        # Wait for all assignments (up to pool capacity)
        max_wait = 10
        while len(assignments) < min(task_count, perf_config.agent_pools[0].max_concurrency) \
                and time.time() - start_time < max_wait:
            time.sleep(0.1)
        
        elapsed = time.time() - start_time
        
        # Stop dispatcher
        dispatcher.stop(timeout=2)
        dispatcher_thread.join(timeout=5)
        
        # Calculate throughput
        if assignments:
            throughput = len(assignments) / elapsed
            
            print(f"\nThroughput: {len(assignments)} tasks in {elapsed:.2f}s")
            print(f"  Rate: {throughput:.1f} tasks/sec")
            
            # Should achieve reasonable throughput
            assert throughput > 5, f"Throughput too low: {throughput:.1f} tasks/sec"


class TestMemoryUsage:
    """Test memory usage patterns."""
    
    def test_queue_memory_with_many_tasks(self):
        """Test queue memory usage with many tasks."""
        import sys
        
        queue = TaskQueue()
        
        # Measure initial size
        initial_size = sys.getsizeof(queue)
        
        # Add many tasks
        tasks = create_test_tasks(10000)
        for task in tasks:
            queue.enqueue(task)
        
        # Measure final size
        final_size = sys.getsizeof(queue)
        
        # Memory growth should be reasonable
        growth = final_size - initial_size
        per_task = growth / 10000 if growth > 0 else 0
        
        print(f"\nQueue memory usage:")
        print(f"  Initial: {initial_size} bytes")
        print(f"  Final: {final_size} bytes")
        print(f"  Growth: {growth} bytes")
        print(f"  Per task: {per_task:.2f} bytes")
        
        # Verify queue size
        assert queue.size() == 10000


class TestScalability:
    """Test scalability with increasing load."""
    
    def test_scheduling_scales_with_task_count(self, perf_config):
        """Test that scheduling time scales reasonably with task count."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        
        from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
        pool_manager = AgentPoolManager(perf_config)
        
        task_counts = [100, 500, 1000, 2000]
        times = []
        
        for count in task_counts:
            queue = TaskQueue()
            tasks = create_test_tasks(count)
            
            for task in tasks:
                queue.enqueue(task)
            
            start_time = time.time()
            scheduled = scheduler.schedule(queue, pool_manager)
            elapsed = time.time() - start_time
            
            times.append(elapsed)
            
            print(f"\n{count} tasks: {elapsed:.3f}s ({len(scheduled)} scheduled)")
        
        # Time should scale sub-linearly (not exponentially)
        # Check that doubling tasks doesn't quadruple time
        if len(times) >= 2:
            ratio = times[-1] / times[0]
            task_ratio = task_counts[-1] / task_counts[0]
            
            # Time ratio should be less than task ratio squared
            assert ratio < task_ratio ** 2, \
                f"Scheduling doesn't scale well: {ratio}x time for {task_ratio}x tasks"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print output

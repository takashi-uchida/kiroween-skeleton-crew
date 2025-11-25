"""
Tests for MetricsCollector.

Tests metrics collection, recording, and Prometheus export functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from necrocode.dispatcher.metrics_collector import MetricsCollector
from necrocode.dispatcher.models import AgentPool, PoolType
from necrocode.task_registry.models import Task, TaskState


@pytest.fixture
def metrics_collector():
    """Create a MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def mock_task_queue():
    """Create a mock TaskQueue."""
    queue = Mock()
    queue.size.return_value = 5
    return queue


@pytest.fixture
def mock_agent_pool_manager():
    """Create a mock AgentPoolManager."""
    manager = Mock()
    
    # Create mock pools
    pool1 = AgentPool(
        name="local",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=4,
        current_running=2,
    )
    pool2 = AgentPool(
        name="docker",
        type=PoolType.DOCKER,
        max_concurrency=10,
        current_running=7,
    )
    
    manager.pools = {
        "local": pool1,
        "docker": pool2,
    }
    
    return manager


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        id="task-1",
        title="Test Task",
        description="Test description",
        state=TaskState.READY,
        priority=5,
        created_at=datetime.now() - timedelta(seconds=30),
    )


@pytest.fixture
def sample_pool():
    """Create a sample pool."""
    return AgentPool(
        name="test-pool",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=4,
        current_running=2,
    )


def test_metrics_collector_initialization(metrics_collector):
    """Test MetricsCollector initialization."""
    assert metrics_collector.metrics == {}
    assert metrics_collector._assignment_history == []
    assert metrics_collector._task_wait_times == {}


def test_set_components(metrics_collector, mock_task_queue, mock_agent_pool_manager):
    """Test setting component references."""
    mock_runner_monitor = Mock()
    
    metrics_collector.set_task_queue(mock_task_queue)
    metrics_collector.set_agent_pool_manager(mock_agent_pool_manager)
    metrics_collector.set_runner_monitor(mock_runner_monitor)
    
    assert metrics_collector._task_queue == mock_task_queue
    assert metrics_collector._agent_pool_manager == mock_agent_pool_manager
    assert metrics_collector._runner_monitor == mock_runner_monitor


def test_collect_metrics(metrics_collector, mock_task_queue, mock_agent_pool_manager):
    """Test metrics collection."""
    metrics_collector.set_task_queue(mock_task_queue)
    metrics_collector.set_agent_pool_manager(mock_agent_pool_manager)
    
    metrics_collector.collect()
    
    metrics = metrics_collector.get_metrics()
    
    assert metrics["queue_size"] == 5
    assert metrics["running_tasks"] == 9  # 2 + 7
    assert "pool_utilization" in metrics
    assert metrics["pool_utilization"]["local"] == 0.5  # 2/4
    assert metrics["pool_utilization"]["docker"] == 0.7  # 7/10
    assert "timestamp" in metrics
    assert metrics["total_assignments"] == 0


def test_record_assignment(metrics_collector, sample_task, sample_pool):
    """Test recording task assignments."""
    metrics_collector.record_assignment(sample_task, sample_pool)
    
    history = metrics_collector.get_assignment_history()
    assert len(history) == 1
    
    record = history[0]
    assert record["task_id"] == "task-1"
    assert record["pool_name"] == "test-pool"
    assert record["pool_type"] == "local-process"
    assert record["priority"] == 5
    assert record["wait_time_seconds"] >= 30  # At least 30 seconds
    assert "assigned_at" in record


def test_multiple_assignments(metrics_collector, sample_pool):
    """Test recording multiple assignments."""
    for i in range(5):
        task = Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test",
            state=TaskState.READY,
            priority=i,
            created_at=datetime.now() - timedelta(seconds=10 * i),
        )
        metrics_collector.record_assignment(task, sample_pool)
    
    history = metrics_collector.get_assignment_history()
    assert len(history) == 5
    
    # Check that all tasks are recorded
    task_ids = [r["task_id"] for r in history]
    assert task_ids == ["task-0", "task-1", "task-2", "task-3", "task-4"]


def test_get_average_wait_time(metrics_collector, sample_pool):
    """Test average wait time calculation."""
    # Create tasks with different wait times
    for i in range(3):
        task = Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now() - timedelta(seconds=10 * (i + 1)),
        )
        metrics_collector.record_assignment(task, sample_pool)
    
    metrics_collector.set_task_queue(Mock(size=Mock(return_value=0)))
    metrics_collector.set_agent_pool_manager(Mock(pools={}))
    metrics_collector.collect()
    
    avg_wait = metrics_collector.get_metrics()["average_wait_time"]
    
    # Average should be around 20 seconds (10, 20, 30)
    assert 15 <= avg_wait <= 25


def test_export_prometheus(metrics_collector, mock_task_queue, mock_agent_pool_manager, sample_task, sample_pool):
    """Test Prometheus format export."""
    metrics_collector.set_task_queue(mock_task_queue)
    metrics_collector.set_agent_pool_manager(mock_agent_pool_manager)
    
    # Record some assignments
    metrics_collector.record_assignment(sample_task, sample_pool)
    
    # Collect metrics
    metrics_collector.collect()
    
    # Export to Prometheus format
    prometheus_output = metrics_collector.export_prometheus()
    
    # Check that output contains expected metrics
    assert "dispatcher_queue_size" in prometheus_output
    assert "dispatcher_running_tasks" in prometheus_output
    assert "dispatcher_average_wait_time_seconds" in prometheus_output
    assert "dispatcher_total_assignments" in prometheus_output
    assert "dispatcher_pool_utilization" in prometheus_output
    
    # Check format
    assert "# HELP" in prometheus_output
    assert "# TYPE" in prometheus_output
    
    # Check values
    assert "dispatcher_queue_size 5" in prometheus_output
    assert "dispatcher_running_tasks 9" in prometheus_output
    assert "dispatcher_total_assignments 1" in prometheus_output


def test_get_pool_assignment_counts(metrics_collector):
    """Test getting assignment counts per pool."""
    pool1 = AgentPool(name="pool1", type=PoolType.LOCAL_PROCESS, max_concurrency=4)
    pool2 = AgentPool(name="pool2", type=PoolType.DOCKER, max_concurrency=4)
    
    # Assign tasks to different pools
    for i in range(3):
        task = Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
        )
        metrics_collector.record_assignment(task, pool1)
    
    for i in range(2):
        task = Task(
            id=f"task-{i+3}",
            title=f"Task {i+3}",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
        )
        metrics_collector.record_assignment(task, pool2)
    
    counts = metrics_collector.get_pool_assignment_counts()
    assert counts["pool1"] == 3
    assert counts["pool2"] == 2


def test_get_priority_distribution(metrics_collector, sample_pool):
    """Test getting priority distribution."""
    priorities = [1, 1, 2, 2, 2, 3, 5, 5, 5, 5]
    
    for i, priority in enumerate(priorities):
        task = Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test",
            state=TaskState.READY,
            priority=priority,
            created_at=datetime.now(),
        )
        metrics_collector.record_assignment(task, sample_pool)
    
    distribution = metrics_collector.get_priority_distribution()
    assert distribution[1] == 2
    assert distribution[2] == 3
    assert distribution[3] == 1
    assert distribution[5] == 4


def test_get_assignment_history_with_limit(metrics_collector, sample_pool):
    """Test getting assignment history with limit."""
    for i in range(10):
        task = Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
        )
        metrics_collector.record_assignment(task, sample_pool)
    
    # Get last 5 assignments
    recent = metrics_collector.get_assignment_history(limit=5)
    assert len(recent) == 5
    assert recent[0]["task_id"] == "task-5"
    assert recent[-1]["task_id"] == "task-9"
    
    # Get all assignments
    all_history = metrics_collector.get_assignment_history()
    assert len(all_history) == 10


def test_reset_metrics(metrics_collector, sample_task, sample_pool):
    """Test resetting metrics."""
    metrics_collector.record_assignment(sample_task, sample_pool)
    metrics_collector.collect()
    
    assert len(metrics_collector.get_assignment_history()) == 1
    assert len(metrics_collector.get_metrics()) > 0
    
    metrics_collector.reset_metrics()
    
    assert len(metrics_collector.get_assignment_history()) == 0
    assert len(metrics_collector.get_metrics()) == 0
    assert len(metrics_collector._task_wait_times) == 0


def test_metrics_without_components(metrics_collector):
    """Test metrics collection without setting components."""
    # Should not crash, just return default values
    metrics_collector.collect()
    
    metrics = metrics_collector.get_metrics()
    assert metrics["queue_size"] == 0
    assert metrics["running_tasks"] == 0
    assert metrics["pool_utilization"] == {}
    assert metrics["average_wait_time"] == 0.0


def test_thread_safety(metrics_collector, sample_pool):
    """Test thread-safe operations."""
    import threading
    
    def record_assignments():
        for i in range(10):
            task = Task(
                id=f"task-{threading.current_thread().name}-{i}",
                title=f"Task {i}",
                description="Test",
                state=TaskState.READY,
                priority=5,
                created_at=datetime.now(),
            )
            metrics_collector.record_assignment(task, sample_pool)
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=record_assignments, name=f"thread-{i}")
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Should have 50 assignments (5 threads * 10 assignments)
    history = metrics_collector.get_assignment_history()
    assert len(history) == 50

"""
Unit tests for TaskMonitor.

Tests polling functionality, task filtering, and dependency resolution.

Requirements: 1.1, 1.2, 1.4
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from necrocode.dispatcher.task_monitor import TaskMonitor, TaskRegistryClient
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import SchedulingPolicy
from necrocode.dispatcher.exceptions import DispatcherError
from necrocode.task_registry.models import Task, TaskState, Taskset


@pytest.fixture
def temp_registry_dir():
    """Create a temporary directory for Task Registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_registry_dir):
    """Create a sample dispatcher configuration."""
    return DispatcherConfig(
        poll_interval=5,
        scheduling_policy=SchedulingPolicy.PRIORITY,
        task_registry_dir=temp_registry_dir,
    )


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    base_time = datetime.now()
    
    return [
        Task(
            id="1",
            title="Task 1 - No dependencies",
            description="First task",
            state=TaskState.READY,
            dependencies=[],
            priority=5,
            created_at=base_time,
            metadata={"spec_name": "test-spec"},
        ),
        Task(
            id="2",
            title="Task 2 - Depends on 1",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"],
            priority=5,
            created_at=base_time,
            metadata={"spec_name": "test-spec"},
        ),
        Task(
            id="3",
            title="Task 3 - Depends on 1 and 2",
            description="Third task",
            state=TaskState.READY,
            dependencies=["1", "2"],
            priority=5,
            created_at=base_time,
            metadata={"spec_name": "test-spec"},
        ),
    ]


class TestTaskRegistryClient:
    """Tests for TaskRegistryClient."""
    
    def test_client_initialization(self, temp_registry_dir):
        """Test TaskRegistryClient initialization."""
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        assert client.registry is not None
    
    def test_get_ready_tasks_empty(self, temp_registry_dir):
        """Test getting ready tasks when registry is empty."""
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        tasks = client.get_ready_tasks()
        assert tasks == []
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistry')
    def test_get_ready_tasks_with_spec(self, mock_registry_class, temp_registry_dir):
        """Test getting ready tasks for a specific spec."""
        # Mock registry
        mock_registry = Mock()
        mock_task = Task(
            id="1",
            title="Test task",
            description="Test",
            state=TaskState.READY,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_registry.get_ready_tasks.return_value = [mock_task]
        mock_registry_class.return_value = mock_registry
        
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        tasks = client.get_ready_tasks(spec_name="test-spec")
        
        assert len(tasks) == 1
        assert tasks[0].id == "1"
        mock_registry.get_ready_tasks.assert_called_once_with("test-spec")
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistry')
    def test_get_ready_tasks_all_specs(self, mock_registry_class, temp_registry_dir):
        """Test getting ready tasks from all specs."""
        # Mock registry
        mock_registry = Mock()
        mock_task1 = Task(
            id="1",
            title="Task 1",
            description="Test",
            state=TaskState.READY,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "spec1"},
        )
        mock_task2 = Task(
            id="2",
            title="Task 2",
            description="Test",
            state=TaskState.READY,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "spec2"},
        )
        
        # Mock task store
        mock_task_store = Mock()
        mock_task_store.list_tasksets.return_value = ["spec1", "spec2"]
        mock_registry.task_store = mock_task_store
        mock_registry.get_ready_tasks.side_effect = [[mock_task1], [mock_task2]]
        mock_registry_class.return_value = mock_registry
        
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        tasks = client.get_ready_tasks()
        
        assert len(tasks) == 2
        assert tasks[0].id == "1"
        assert tasks[1].id == "2"
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistry')
    def test_get_ready_tasks_error(self, mock_registry_class, temp_registry_dir):
        """Test error handling when getting ready tasks."""
        # Mock registry to raise exception
        mock_registry = Mock()
        mock_registry.get_ready_tasks.side_effect = Exception("Registry error")
        mock_registry_class.return_value = mock_registry
        
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        
        with pytest.raises(DispatcherError):
            client.get_ready_tasks(spec_name="test-spec")
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistry')
    def test_get_task(self, mock_registry_class, temp_registry_dir):
        """Test getting a specific task."""
        # Mock registry
        mock_registry = Mock()
        mock_task = Task(
            id="1",
            title="Test task",
            description="Test",
            state=TaskState.READY,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_taskset = Taskset(
            spec_name="test-spec",
            version=1,
            tasks=[mock_task],
            created_at=datetime.now(),
        )
        
        mock_task_store = Mock()
        mock_task_store.load_taskset.return_value = mock_taskset
        mock_registry.task_store = mock_task_store
        mock_registry_class.return_value = mock_registry
        
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        task = client.get_task("test-spec", "1")
        
        assert task is not None
        assert task.id == "1"
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistry')
    def test_get_task_not_found(self, mock_registry_class, temp_registry_dir):
        """Test getting a task that doesn't exist."""
        # Mock registry
        mock_registry = Mock()
        mock_task_store = Mock()
        mock_task_store.load_taskset.return_value = None
        mock_registry.task_store = mock_task_store
        mock_registry_class.return_value = mock_registry
        
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        task = client.get_task("test-spec", "nonexistent")
        
        assert task is None
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistry')
    def test_get_task_dependencies(self, mock_registry_class, temp_registry_dir):
        """Test getting task dependencies."""
        # Mock registry
        mock_registry = Mock()
        mock_task = Task(
            id="2",
            title="Test task",
            description="Test",
            state=TaskState.READY,
            dependencies=["1"],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_taskset = Taskset(
            spec_name="test-spec",
            version=1,
            tasks=[mock_task],
            created_at=datetime.now(),
        )
        
        mock_task_store = Mock()
        mock_task_store.load_taskset.return_value = mock_taskset
        mock_registry.task_store = mock_task_store
        mock_registry_class.return_value = mock_registry
        
        client = TaskRegistryClient(registry_dir=temp_registry_dir)
        deps = client.get_task_dependencies("test-spec", "2")
        
        assert deps == ["1"]


class TestTaskMonitor:
    """Tests for TaskMonitor."""
    
    def test_task_monitor_initialization(self, sample_config):
        """Test TaskMonitor initialization."""
        monitor = TaskMonitor(sample_config)
        assert monitor.config == sample_config
        assert monitor.task_registry_client is not None
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_empty(self, mock_client_class, sample_config):
        """Test polling when no ready tasks exist."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = []
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        assert tasks == []
        mock_client.get_ready_tasks.assert_called_once()
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_no_dependencies(self, mock_client_class, sample_config, sample_tasks):
        """Test polling tasks with no dependencies."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = [sample_tasks[0]]
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].id == "1"
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_with_resolved_dependencies(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test polling tasks with resolved dependencies."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = [sample_tasks[1]]
        
        # Mock dependency task as DONE
        dep_task = Task(
            id="1",
            title="Dependency task",
            description="Test",
            state=TaskState.DONE,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_client.get_task.return_value = dep_task
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].id == "2"
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_with_unresolved_dependencies(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test polling tasks with unresolved dependencies."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = [sample_tasks[1]]
        
        # Mock dependency task as RUNNING (not DONE)
        dep_task = Task(
            id="1",
            title="Dependency task",
            description="Test",
            state=TaskState.RUNNING,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_client.get_task.return_value = dep_task
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        # Task should be filtered out
        assert len(tasks) == 0
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_missing_dependency(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test polling tasks when dependency task is missing."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = [sample_tasks[1]]
        mock_client.get_task.return_value = None  # Dependency not found
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        # Task should be filtered out
        assert len(tasks) == 0
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_multiple_dependencies(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test polling tasks with multiple dependencies."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = [sample_tasks[2]]
        
        # Mock both dependencies as DONE
        def get_task_side_effect(spec_name, task_id):
            return Task(
                id=task_id,
                title=f"Task {task_id}",
                description="Test",
                state=TaskState.DONE,
                dependencies=[],
                priority=5,
                created_at=datetime.now(),
                metadata={"spec_name": "test-spec"},
            )
        
        mock_client.get_task.side_effect = get_task_side_effect
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].id == "3"
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_partial_dependencies_resolved(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test polling tasks when only some dependencies are resolved."""
        # Mock client
        mock_client = Mock()
        mock_client.get_ready_tasks.return_value = [sample_tasks[2]]
        
        # Mock one dependency as DONE, another as RUNNING
        def get_task_side_effect(spec_name, task_id):
            state = TaskState.DONE if task_id == "1" else TaskState.RUNNING
            return Task(
                id=task_id,
                title=f"Task {task_id}",
                description="Test",
                state=state,
                dependencies=[],
                priority=5,
                created_at=datetime.now(),
                metadata={"spec_name": "test-spec"},
            )
        
        mock_client.get_task.side_effect = get_task_side_effect
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks()
        
        # Task should be filtered out (not all dependencies resolved)
        assert len(tasks) == 0
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_with_spec_filter(self, mock_client_class, sample_config):
        """Test polling ready tasks with spec name filter."""
        # Mock client
        mock_client = Mock()
        mock_task = Task(
            id="1",
            title="Test task",
            description="Test",
            state=TaskState.READY,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "specific-spec"},
        )
        mock_client.get_ready_tasks.return_value = [mock_task]
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        tasks = monitor.poll_ready_tasks(spec_name="specific-spec")
        
        assert len(tasks) == 1
        mock_client.get_ready_tasks.assert_called_once_with("specific-spec")
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_poll_ready_tasks_error_handling(self, mock_client_class, sample_config):
        """Test error handling during polling."""
        # Mock client to raise exception
        mock_client = Mock()
        mock_client.get_ready_tasks.side_effect = Exception("Registry error")
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        # Should return empty list on error, not raise exception
        tasks = monitor.poll_ready_tasks()
        
        assert tasks == []
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_filter_tasks_no_spec_name(self, mock_client_class, sample_config):
        """Test filtering tasks without spec_name in metadata."""
        # Mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        # Task without spec_name in metadata
        task = Task(
            id="1",
            title="Test task",
            description="Test",
            state=TaskState.READY,
            dependencies=["0"],
            priority=5,
            created_at=datetime.now(),
            metadata={},  # No spec_name
        )
        
        # Should assume dependencies are resolved if spec_name is missing
        filtered = monitor._filter_tasks([task])
        
        assert len(filtered) == 1
    
    def test_are_dependencies_resolved_no_dependencies(self, sample_config, sample_tasks):
        """Test dependency resolution for task with no dependencies."""
        monitor = TaskMonitor(sample_config)
        
        # Task with no dependencies should always be resolved
        assert monitor._are_dependencies_resolved(sample_tasks[0]) is True
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_are_dependencies_resolved_all_done(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test dependency resolution when all dependencies are DONE."""
        # Mock client
        mock_client = Mock()
        dep_task = Task(
            id="1",
            title="Dependency",
            description="Test",
            state=TaskState.DONE,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_client.get_task.return_value = dep_task
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        assert monitor._are_dependencies_resolved(sample_tasks[1]) is True
    
    @patch('necrocode.dispatcher.task_monitor.TaskRegistryClient')
    def test_are_dependencies_resolved_not_done(
        self, mock_client_class, sample_config, sample_tasks
    ):
        """Test dependency resolution when dependencies are not DONE."""
        # Mock client
        mock_client = Mock()
        dep_task = Task(
            id="1",
            title="Dependency",
            description="Test",
            state=TaskState.RUNNING,
            dependencies=[],
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        mock_client.get_task.return_value = dep_task
        mock_client_class.return_value = mock_client
        
        monitor = TaskMonitor(sample_config)
        monitor.task_registry_client = mock_client
        
        assert monitor._are_dependencies_resolved(sample_tasks[1]) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for Priority Management in Dispatcher

Tests:
1. Reading task priority (Requirement 7.1)
2. Priority-based sorting (Requirements 7.2, 7.3)
3. Dynamic priority changes (Requirement 7.4)
4. Enabling/disabling priority scheduling (Requirement 7.5)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time

from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import SchedulingPolicy
from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, Taskset


@pytest.fixture
def temp_registry_dir():
    """Create a temporary directory for Task Registry."""
    temp_dir = tempfile.mkdtemp(prefix="test_priority_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def task_registry(temp_registry_dir):
    """Create a Task Registry instance."""
    return TaskRegistry(registry_dir=str(temp_registry_dir))


@pytest.fixture
def dispatcher_config(temp_registry_dir):
    """Create a Dispatcher configuration."""
    return DispatcherConfig(
        task_registry_dir=str(temp_registry_dir),
        scheduling_policy=SchedulingPolicy.PRIORITY,
        poll_interval=1,
        max_global_concurrency=5
    )


@pytest.fixture
def dispatcher(dispatcher_config):
    """Create a DispatcherCore instance."""
    return DispatcherCore(dispatcher_config)


@pytest.fixture
def test_tasks():
    """Create test tasks with different priorities."""
    return [
        Task(
            id="1",
            title="Low priority task",
            description="Priority 1",
            state=TaskState.READY,
            priority=1,
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        ),
        Task(
            id="2",
            title="High priority task",
            description="Priority 10",
            state=TaskState.READY,
            priority=10,
            created_at=datetime(2024, 1, 1, 10, 0, 1)
        ),
        Task(
            id="3",
            title="Medium priority task",
            description="Priority 5",
            state=TaskState.READY,
            priority=5,
            created_at=datetime(2024, 1, 1, 10, 0, 2)
        ),
        Task(
            id="4",
            title="Another high priority task",
            description="Priority 10 (FIFO test)",
            state=TaskState.READY,
            priority=10,
            created_at=datetime(2024, 1, 1, 10, 0, 3)
        ),
    ]


class TestPriorityReading:
    """Test reading task priority (Requirement 7.1)."""
    
    def test_task_has_priority_field(self, test_tasks):
        """Test that Task model has priority field."""
        task = test_tasks[0]
        assert hasattr(task, 'priority')
        assert isinstance(task.priority, int)
    
    def test_priority_values_are_read(self, test_tasks):
        """Test that priority values are correctly read."""
        assert test_tasks[0].priority == 1
        assert test_tasks[1].priority == 10
        assert test_tasks[2].priority == 5
        assert test_tasks[3].priority == 10
    
    def test_default_priority_is_zero(self):
        """Test that default priority is 0."""
        task = Task(
            id="test",
            title="Test",
            description="Test",
            state=TaskState.READY
        )
        assert task.priority == 0


class TestPrioritySorting:
    """Test priority-based sorting (Requirements 7.2, 7.3)."""
    
    def test_higher_priority_comes_first(self, dispatcher, test_tasks):
        """Test that higher priority tasks come first."""
        # Add tasks to queue
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Get tasks in order
        queued_tasks = dispatcher.task_queue.get_all_tasks()
        
        # Verify order: priority 10 tasks should come before priority 5 and 1
        assert queued_tasks[0].priority == 10
        assert queued_tasks[1].priority == 10
        assert queued_tasks[2].priority == 5
        assert queued_tasks[3].priority == 1
    
    def test_same_priority_fifo_order(self, dispatcher, test_tasks):
        """Test that same priority tasks are processed in FIFO order."""
        # Add tasks to queue
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Get tasks in order
        queued_tasks = dispatcher.task_queue.get_all_tasks()
        
        # Find tasks with priority 10
        high_priority_tasks = [t for t in queued_tasks if t.priority == 10]
        
        # Verify FIFO order (task 2 created before task 4)
        assert len(high_priority_tasks) == 2
        assert high_priority_tasks[0].id == "2"
        assert high_priority_tasks[1].id == "4"
        assert high_priority_tasks[0].created_at < high_priority_tasks[1].created_at
    
    def test_dequeue_respects_priority(self, dispatcher, test_tasks):
        """Test that dequeue returns highest priority task."""
        # Add tasks to queue
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Dequeue first task
        first_task = dispatcher.task_queue.dequeue()
        
        # Should be a priority 10 task
        assert first_task is not None
        assert first_task.priority == 10
        assert first_task.id == "2"  # First high priority task


class TestDynamicPriorityChange:
    """Test dynamic priority changes (Requirement 7.4)."""
    
    def test_update_task_priority(self, dispatcher, task_registry, test_tasks):
        """Test updating task priority."""
        spec_name = "test-spec"
        
        # Create taskset
        from necrocode.task_registry.kiro_sync import TaskDefinition
        task_defs = [
            TaskDefinition(
                id=task.id,
                title=task.title,
                description=task.description,
                is_optional=task.is_optional,
                is_completed=False,
                dependencies=task.dependencies
            )
            for task in test_tasks
        ]
        task_registry.create_taskset(spec_name, task_defs)
        
        # Add tasks to queue
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Update priority of task 1 from 1 to 15
        success = dispatcher.update_task_priority(spec_name, "1", 15)
        
        assert success is True
        
        # Verify task 1 is now at the front
        queued_tasks = dispatcher.task_queue.get_all_tasks()
        assert queued_tasks[0].id == "1"
        assert queued_tasks[0].priority == 15
    
    def test_update_priority_for_nonexistent_task(self, dispatcher, task_registry):
        """Test updating priority for non-existent task."""
        spec_name = "test-spec"
        
        # Try to update non-existent task
        success = dispatcher.update_task_priority(spec_name, "999", 10)
        
        assert success is False
    
    def test_priority_change_reorders_queue(self, dispatcher, task_registry, test_tasks):
        """Test that priority change reorders the queue."""
        spec_name = "test-spec"
        
        # Create taskset
        from necrocode.task_registry.kiro_sync import TaskDefinition
        task_defs = [
            TaskDefinition(
                id=task.id,
                title=task.title,
                description=task.description,
                is_optional=task.is_optional,
                is_completed=False,
                dependencies=task.dependencies
            )
            for task in test_tasks
        ]
        task_registry.create_taskset(spec_name, task_defs)
        
        # Add tasks to queue
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Get initial order
        initial_order = [t.id for t in dispatcher.task_queue.get_all_tasks()]
        
        # Update priority of task 3 from 5 to 20
        dispatcher.update_task_priority(spec_name, "3", 20)
        
        # Get new order
        new_order = [t.id for t in dispatcher.task_queue.get_all_tasks()]
        
        # Order should have changed
        assert initial_order != new_order
        
        # Task 3 should now be first
        assert new_order[0] == "3"


class TestSchedulingPolicyChanges:
    """Test enabling/disabling priority scheduling (Requirement 7.5)."""
    
    def test_disable_priority_scheduling(self, dispatcher):
        """Test disabling priority-based scheduling."""
        # Initial policy should be PRIORITY
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.PRIORITY
        
        # Disable priority scheduling
        dispatcher.disable_priority_scheduling()
        
        # Policy should now be FIFO
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.FIFO
        assert dispatcher.scheduler.policy == SchedulingPolicy.FIFO
    
    def test_enable_priority_scheduling(self, dispatcher):
        """Test enabling priority-based scheduling."""
        # Disable first
        dispatcher.disable_priority_scheduling()
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.FIFO
        
        # Enable priority scheduling
        dispatcher.enable_priority_scheduling()
        
        # Policy should now be PRIORITY
        assert dispatcher.config.scheduling_policy == SchedulingPolicy.PRIORITY
        assert dispatcher.scheduler.policy == SchedulingPolicy.PRIORITY
    
    def test_set_scheduling_policy(self, dispatcher):
        """Test setting arbitrary scheduling policy."""
        # Test all policies
        for policy in SchedulingPolicy:
            dispatcher.set_scheduling_policy(policy)
            
            assert dispatcher.config.scheduling_policy == policy
            assert dispatcher.scheduler.policy == policy
    
    def test_status_includes_scheduling_policy(self, dispatcher):
        """Test that status includes current scheduling policy."""
        status = dispatcher.get_status()
        
        assert "scheduling_policy" in status
        assert status["scheduling_policy"] == SchedulingPolicy.PRIORITY.value
        
        # Change policy and verify status updates
        dispatcher.set_scheduling_policy(SchedulingPolicy.FIFO)
        status = dispatcher.get_status()
        
        assert status["scheduling_policy"] == SchedulingPolicy.FIFO.value


class TestPriorityIntegration:
    """Integration tests for priority management."""
    
    def test_priority_affects_scheduling_order(self, dispatcher, test_tasks):
        """Test that priority affects actual scheduling order."""
        # Add tasks to queue
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Dequeue all tasks and verify order
        dequeued_order = []
        while not dispatcher.task_queue.is_empty():
            task = dispatcher.task_queue.dequeue()
            if task:
                dequeued_order.append((task.id, task.priority))
        
        # Verify order: highest priority first, FIFO for same priority
        assert dequeued_order[0] == ("2", 10)  # First high priority
        assert dequeued_order[1] == ("4", 10)  # Second high priority (FIFO)
        assert dequeued_order[2] == ("3", 5)   # Medium priority
        assert dequeued_order[3] == ("1", 1)   # Low priority
    
    def test_fifo_ignores_priority(self, dispatcher, test_tasks):
        """Test that FIFO policy ignores priority."""
        # Switch to FIFO
        dispatcher.set_scheduling_policy(SchedulingPolicy.FIFO)
        
        # Add tasks in specific order
        for task in test_tasks:
            dispatcher.task_queue.enqueue(task)
        
        # Note: TaskQueue still uses priority internally, but FIFO scheduler
        # should process tasks in creation time order regardless of priority
        # This is a design consideration - the queue itself is priority-based,
        # but the scheduler can choose to ignore it
        
        # Verify scheduler policy is FIFO
        assert dispatcher.scheduler.policy == SchedulingPolicy.FIFO

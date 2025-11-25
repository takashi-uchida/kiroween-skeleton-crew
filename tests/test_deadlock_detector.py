"""
Tests for DeadlockDetector.

Tests deadlock detection in task dependency graphs.
"""

import pytest
from datetime import datetime

from necrocode.dispatcher.deadlock_detector import DeadlockDetector
from necrocode.dispatcher.exceptions import DeadlockDetectedError
from necrocode.task_registry.models import Task, TaskState


def test_no_deadlock_linear_dependencies():
    """Test that linear dependencies don't trigger deadlock detection."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=[]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        Task(
            id="3",
            title="Task 3",
            description="Third task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 0
    assert not detector.check_for_deadlock(tasks)


def test_no_deadlock_parallel_dependencies():
    """Test that parallel dependencies don't trigger deadlock detection."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=[]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        Task(
            id="3",
            title="Task 3",
            description="Third task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        Task(
            id="4",
            title="Task 4",
            description="Fourth task",
            state=TaskState.READY,
            dependencies=["2", "3"]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 0


def test_simple_circular_dependency():
    """Test detection of simple circular dependency (A -> B -> A)."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 1
    assert "1" in cycles[0]
    assert "2" in cycles[0]


def test_three_way_circular_dependency():
    """Test detection of three-way circular dependency (A -> B -> C -> A)."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["3"]
        ),
        Task(
            id="3",
            title="Task 3",
            description="Third task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 1
    assert len(cycles[0]) == 4  # Cycle includes return to start
    assert "1" in cycles[0]
    assert "2" in cycles[0]
    assert "3" in cycles[0]


def test_multiple_cycles():
    """Test detection of multiple independent cycles."""
    detector = DeadlockDetector()
    
    tasks = [
        # Cycle 1: 1 -> 2 -> 1
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        # Cycle 2: 3 -> 4 -> 3
        Task(
            id="3",
            title="Task 3",
            description="Third task",
            state=TaskState.READY,
            dependencies=["4"]
        ),
        Task(
            id="4",
            title="Task 4",
            description="Fourth task",
            state=TaskState.READY,
            dependencies=["3"]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) >= 1  # At least one cycle detected


def test_completed_tasks_ignored():
    """Test that completed tasks are ignored in deadlock detection."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.DONE,  # Completed
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.DONE,  # Completed
            dependencies=["1"]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 0  # Completed tasks should be ignored


def test_raise_on_deadlock():
    """Test that exception is raised when requested."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
    ]
    
    with pytest.raises(DeadlockDetectedError) as exc_info:
        detector.check_for_deadlock(tasks, raise_on_deadlock=True)
    
    assert "Deadlock detected" in str(exc_info.value)
    assert "circular" in str(exc_info.value).lower()


def test_get_blocked_tasks():
    """Test getting tasks involved in circular dependencies."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
        Task(
            id="3",
            title="Task 3",
            description="Third task",
            state=TaskState.READY,
            dependencies=[]
        ),
    ]
    
    blocked_tasks = detector.get_blocked_tasks(tasks)
    
    assert len(blocked_tasks) == 2
    blocked_ids = {task.id for task in blocked_tasks}
    assert "1" in blocked_ids
    assert "2" in blocked_ids
    assert "3" not in blocked_ids


def test_suggest_resolution():
    """Test resolution suggestions for detected cycles."""
    detector = DeadlockDetector()
    
    cycles = [
        ["1", "2", "1"],
        ["3", "4", "5", "3"],
    ]
    
    suggestions = detector.suggest_resolution(cycles)
    
    assert len(suggestions) == 2
    assert "Cycle 1" in suggestions[0]
    assert "Cycle 2" in suggestions[1]
    assert "Remove dependency" in suggestions[0]


def test_last_check_time():
    """Test that last check time is recorded."""
    detector = DeadlockDetector()
    
    assert detector.get_last_check_time() is None
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=[]
        ),
    ]
    
    detector.detect_deadlock(tasks)
    
    last_check = detector.get_last_check_time()
    assert last_check is not None
    assert isinstance(last_check, datetime)


def test_get_detected_cycles():
    """Test getting detected cycles from last check."""
    detector = DeadlockDetector()
    
    assert len(detector.get_detected_cycles()) == 0
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["2"]
        ),
        Task(
            id="2",
            title="Task 2",
            description="Second task",
            state=TaskState.READY,
            dependencies=["1"]
        ),
    ]
    
    detector.detect_deadlock(tasks)
    
    cycles = detector.get_detected_cycles()
    assert len(cycles) == 1


def test_self_dependency():
    """Test detection of self-dependency (A -> A)."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.READY,
            dependencies=["1"]  # Self-dependency
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 1
    assert "1" in cycles[0]


def test_complex_graph_with_cycle():
    """Test complex dependency graph with one cycle."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(id="1", title="Task 1", description="", state=TaskState.READY, dependencies=[]),
        Task(id="2", title="Task 2", description="", state=TaskState.READY, dependencies=["1"]),
        Task(id="3", title="Task 3", description="", state=TaskState.READY, dependencies=["2"]),
        Task(id="4", title="Task 4", description="", state=TaskState.READY, dependencies=["3"]),
        Task(id="5", title="Task 5", description="", state=TaskState.READY, dependencies=["4", "6"]),
        Task(id="6", title="Task 6", description="", state=TaskState.READY, dependencies=["5"]),  # Cycle: 5 <-> 6
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) >= 1
    
    # Check that the cycle involves tasks 5 and 6
    cycle_tasks = set()
    for cycle in cycles:
        cycle_tasks.update(cycle)
    
    assert "5" in cycle_tasks
    assert "6" in cycle_tasks


def test_empty_task_list():
    """Test deadlock detection with empty task list."""
    detector = DeadlockDetector()
    
    cycles = detector.detect_deadlock([])
    assert len(cycles) == 0
    assert not detector.check_for_deadlock([])


def test_single_task_no_dependencies():
    """Test single task with no dependencies."""
    detector = DeadlockDetector()
    
    tasks = [
        Task(
            id="1",
            title="Task 1",
            description="Single task",
            state=TaskState.READY,
            dependencies=[]
        ),
    ]
    
    cycles = detector.detect_deadlock(tasks)
    assert len(cycles) == 0

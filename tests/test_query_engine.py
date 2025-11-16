"""Unit tests for QueryEngine.

Tests filtering, sorting, and pagination.
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.query_engine import QueryEngine
from necrocode.task_registry.task_store import TaskStore
from necrocode.task_registry.models import Task, TaskState, Taskset


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def storage_dir(tmp_path):
    """Create temporary storage directory."""
    return tmp_path / "tasksets"


@pytest.fixture
def task_store(storage_dir):
    """Create TaskStore instance."""
    return TaskStore(storage_dir)


@pytest.fixture
def query_engine(task_store):
    """Create QueryEngine instance."""
    return QueryEngine(task_store)


@pytest.fixture
def sample_taskset(task_store):
    """Create sample taskset with multiple tasks."""
    tasks = [
        Task(
            id="1.1",
            title="Backend Task 1",
            description="Backend description",
            state=TaskState.READY,
            dependencies=[],
            required_skill="backend",
            priority=1,
            is_optional=False,
        ),
        Task(
            id="1.2",
            title="Backend Task 2",
            description="Backend description",
            state=TaskState.RUNNING,
            dependencies=["1.1"],
            required_skill="backend",
            priority=2,
            is_optional=False,
        ),
        Task(
            id="2.1",
            title="Frontend Task 1",
            description="Frontend description",
            state=TaskState.READY,
            dependencies=[],
            required_skill="frontend",
            priority=1,
            is_optional=False,
        ),
        Task(
            id="2.2",
            title="Frontend Task 2",
            description="Frontend description",
            state=TaskState.BLOCKED,
            dependencies=["2.1"],
            required_skill="frontend",
            priority=3,
            is_optional=True,
        ),
        Task(
            id="3.1",
            title="Database Task",
            description="Database description",
            state=TaskState.DONE,
            dependencies=[],
            required_skill="database",
            priority=1,
            is_optional=False,
        ),
    ]
    
    taskset = Taskset(
        spec_name="test-spec",
        version=1,
        tasks=tasks,
        metadata={},
    )
    
    task_store.save_taskset(taskset)
    return taskset


# ============================================================================
# Filter by State Tests
# ============================================================================

def test_filter_by_state_ready(query_engine, sample_taskset):
    """Test filter_by_state returns READY tasks."""
    tasks = query_engine.filter_by_state("test-spec", TaskState.READY)
    
    assert len(tasks) == 2
    assert all(t.state == TaskState.READY for t in tasks)
    assert "1.1" in [t.id for t in tasks]
    assert "2.1" in [t.id for t in tasks]


def test_filter_by_state_running(query_engine, sample_taskset):
    """Test filter_by_state returns RUNNING tasks."""
    tasks = query_engine.filter_by_state("test-spec", TaskState.RUNNING)
    
    assert len(tasks) == 1
    assert tasks[0].state == TaskState.RUNNING
    assert tasks[0].id == "1.2"


def test_filter_by_state_blocked(query_engine, sample_taskset):
    """Test filter_by_state returns BLOCKED tasks."""
    tasks = query_engine.filter_by_state("test-spec", TaskState.BLOCKED)
    
    assert len(tasks) == 1
    assert tasks[0].state == TaskState.BLOCKED
    assert tasks[0].id == "2.2"


def test_filter_by_state_done(query_engine, sample_taskset):
    """Test filter_by_state returns DONE tasks."""
    tasks = query_engine.filter_by_state("test-spec", TaskState.DONE)
    
    assert len(tasks) == 1
    assert tasks[0].state == TaskState.DONE
    assert tasks[0].id == "3.1"


def test_filter_by_state_no_matches(query_engine, sample_taskset):
    """Test filter_by_state returns empty list when no matches."""
    tasks = query_engine.filter_by_state("test-spec", TaskState.FAILED)
    
    assert tasks == []


def test_filter_by_state_nonexistent_spec(query_engine):
    """Test filter_by_state handles nonexistent spec."""
    tasks = query_engine.filter_by_state("nonexistent-spec", TaskState.READY)
    
    assert tasks == []


# ============================================================================
# Filter by Skill Tests
# ============================================================================

def test_filter_by_skill_backend(query_engine, sample_taskset):
    """Test filter_by_skill returns backend tasks."""
    tasks = query_engine.filter_by_skill("test-spec", "backend")
    
    assert len(tasks) == 2
    assert all(t.required_skill == "backend" for t in tasks)
    assert "1.1" in [t.id for t in tasks]
    assert "1.2" in [t.id for t in tasks]


def test_filter_by_skill_frontend(query_engine, sample_taskset):
    """Test filter_by_skill returns frontend tasks."""
    tasks = query_engine.filter_by_skill("test-spec", "frontend")
    
    assert len(tasks) == 2
    assert all(t.required_skill == "frontend" for t in tasks)
    assert "2.1" in [t.id for t in tasks]
    assert "2.2" in [t.id for t in tasks]


def test_filter_by_skill_database(query_engine, sample_taskset):
    """Test filter_by_skill returns database tasks."""
    tasks = query_engine.filter_by_skill("test-spec", "database")
    
    assert len(tasks) == 1
    assert tasks[0].required_skill == "database"
    assert tasks[0].id == "3.1"


def test_filter_by_skill_no_matches(query_engine, sample_taskset):
    """Test filter_by_skill returns empty list when no matches."""
    tasks = query_engine.filter_by_skill("test-spec", "devops")
    
    assert tasks == []


def test_filter_by_skill_nonexistent_spec(query_engine):
    """Test filter_by_skill handles nonexistent spec."""
    tasks = query_engine.filter_by_skill("nonexistent-spec", "backend")
    
    assert tasks == []


# ============================================================================
# Sort by Priority Tests
# ============================================================================

def test_sort_by_priority_descending(query_engine, sample_taskset):
    """Test sort_by_priority sorts in descending order."""
    taskset = query_engine.task_store.load_taskset("test-spec")
    tasks = query_engine.sort_by_priority(taskset.tasks, descending=True)
    
    # Should be sorted by priority: 3, 2, 1, 1, 1
    priorities = [t.priority for t in tasks]
    assert priorities == sorted(priorities, reverse=True)
    assert tasks[0].priority == 3


def test_sort_by_priority_ascending(query_engine, sample_taskset):
    """Test sort_by_priority sorts in ascending order."""
    taskset = query_engine.task_store.load_taskset("test-spec")
    tasks = query_engine.sort_by_priority(taskset.tasks, descending=False)
    
    # Should be sorted by priority: 1, 1, 1, 2, 3
    priorities = [t.priority for t in tasks]
    assert priorities == sorted(priorities)
    assert tasks[0].priority == 1


def test_sort_by_priority_empty_list(query_engine):
    """Test sort_by_priority handles empty list."""
    tasks = query_engine.sort_by_priority([], descending=True)
    
    assert tasks == []


def test_sort_by_priority_single_task(query_engine):
    """Test sort_by_priority handles single task."""
    task = Task(
        id="1.1",
        title="Task",
        description="Description",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1,
        is_optional=False,
    )
    
    tasks = query_engine.sort_by_priority([task], descending=True)
    
    assert len(tasks) == 1
    assert tasks[0].id == "1.1"


# ============================================================================
# Complex Query Tests
# ============================================================================

def test_query_with_state_filter(query_engine, sample_taskset):
    """Test query with state filter."""
    tasks = query_engine.query(
        "test-spec",
        filters={"state": TaskState.READY}
    )
    
    assert len(tasks) == 2
    assert all(t.state == TaskState.READY for t in tasks)


def test_query_with_skill_filter(query_engine, sample_taskset):
    """Test query with skill filter."""
    tasks = query_engine.query(
        "test-spec",
        filters={"required_skill": "backend"}
    )
    
    assert len(tasks) == 2
    assert all(t.required_skill == "backend" for t in tasks)


def test_query_with_multiple_filters(query_engine, sample_taskset):
    """Test query with multiple filters."""
    tasks = query_engine.query(
        "test-spec",
        filters={
            "state": TaskState.READY,
            "required_skill": "backend"
        }
    )
    
    assert len(tasks) == 1
    assert tasks[0].id == "1.1"
    assert tasks[0].state == TaskState.READY
    assert tasks[0].required_skill == "backend"


def test_query_with_optional_filter(query_engine, sample_taskset):
    """Test query with is_optional filter."""
    tasks = query_engine.query(
        "test-spec",
        filters={"is_optional": True}
    )
    
    assert len(tasks) == 1
    assert tasks[0].is_optional


def test_query_with_sort_by_priority(query_engine, sample_taskset):
    """Test query with sort_by priority."""
    tasks = query_engine.query(
        "test-spec",
        filters={},
        sort_by="priority"
    )
    
    # Should be sorted by priority descending
    priorities = [t.priority for t in tasks]
    assert priorities == sorted(priorities, reverse=True)


def test_query_with_sort_by_id(query_engine, sample_taskset):
    """Test query with sort_by id."""
    tasks = query_engine.query(
        "test-spec",
        filters={},
        sort_by="id"
    )
    
    # Should be sorted by id
    ids = [t.id for t in tasks]
    assert ids == sorted(ids)


# ============================================================================
# Pagination Tests
# ============================================================================

def test_query_with_limit(query_engine, sample_taskset):
    """Test query with limit."""
    tasks = query_engine.query(
        "test-spec",
        filters={},
        limit=2
    )
    
    assert len(tasks) == 2


def test_query_with_offset(query_engine, sample_taskset):
    """Test query with offset."""
    # Get all tasks
    all_tasks = query_engine.query("test-spec", filters={})
    
    # Get tasks with offset
    offset_tasks = query_engine.query(
        "test-spec",
        filters={},
        offset=2
    )
    
    # Should skip first 2 tasks
    assert len(offset_tasks) == len(all_tasks) - 2
    assert offset_tasks[0].id == all_tasks[2].id


def test_query_with_limit_and_offset(query_engine, sample_taskset):
    """Test query with both limit and offset."""
    tasks = query_engine.query(
        "test-spec",
        filters={},
        limit=2,
        offset=1
    )
    
    assert len(tasks) == 2
    # Should get tasks at index 1 and 2


def test_query_pagination_beyond_results(query_engine, sample_taskset):
    """Test query pagination beyond available results."""
    tasks = query_engine.query(
        "test-spec",
        filters={},
        limit=10,
        offset=10
    )
    
    assert tasks == []


def test_query_limit_zero(query_engine, sample_taskset):
    """Test query with limit=0."""
    tasks = query_engine.query(
        "test-spec",
        filters={},
        limit=0
    )
    
    # Limit 0 might return all or none depending on implementation
    # This test documents expected behavior


def test_query_negative_offset(query_engine, sample_taskset):
    """Test query with negative offset."""
    # Negative offset should be treated as 0
    tasks = query_engine.query(
        "test-spec",
        filters={},
        offset=-1
    )
    
    # Should return all tasks
    assert len(tasks) == 5


# ============================================================================
# Combined Filters, Sort, and Pagination Tests
# ============================================================================

def test_query_filter_sort_paginate(query_engine, sample_taskset):
    """Test query with filter, sort, and pagination."""
    tasks = query_engine.query(
        "test-spec",
        filters={"state": TaskState.READY},
        sort_by="priority",
        limit=1,
        offset=0
    )
    
    assert len(tasks) == 1
    assert tasks[0].state == TaskState.READY


def test_query_multiple_filters_with_pagination(query_engine, sample_taskset):
    """Test query with multiple filters and pagination."""
    # Add more backend tasks for better testing
    taskset = query_engine.task_store.load_taskset("test-spec")
    for i in range(3, 6):
        taskset.tasks.append(
            Task(
                id=f"1.{i}",
                title=f"Backend Task {i}",
                description="Backend description",
                state=TaskState.READY,
                dependencies=[],
                required_skill="backend",
                priority=i,
                is_optional=False,
            )
        )
    query_engine.task_store.save_taskset(taskset)
    
    # Query with filters and pagination
    tasks = query_engine.query(
        "test-spec",
        filters={
            "state": TaskState.READY,
            "required_skill": "backend"
        },
        sort_by="priority",
        limit=2,
        offset=1
    )
    
    assert len(tasks) == 2
    assert all(t.state == TaskState.READY for t in tasks)
    assert all(t.required_skill == "backend" for t in tasks)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_query_nonexistent_spec(query_engine):
    """Test query handles nonexistent spec."""
    tasks = query_engine.query("nonexistent-spec", filters={})
    
    assert tasks == []


def test_query_empty_filters(query_engine, sample_taskset):
    """Test query with empty filters returns all tasks."""
    tasks = query_engine.query("test-spec", filters={})
    
    assert len(tasks) == 5


def test_query_invalid_filter_key(query_engine, sample_taskset):
    """Test query with invalid filter key."""
    # Should ignore invalid filter keys
    tasks = query_engine.query(
        "test-spec",
        filters={"invalid_key": "value"}
    )
    
    # Should return all tasks (invalid filter ignored)
    assert len(tasks) == 5


def test_query_invalid_sort_by(query_engine, sample_taskset):
    """Test query with invalid sort_by."""
    # Should handle gracefully
    tasks = query_engine.query(
        "test-spec",
        filters={},
        sort_by="invalid_field"
    )
    
    # Should return tasks (possibly unsorted)
    assert len(tasks) == 5


def test_filter_by_state_with_dependencies(query_engine, sample_taskset):
    """Test filter_by_state considers dependencies."""
    # BLOCKED tasks have dependencies
    blocked_tasks = query_engine.filter_by_state("test-spec", TaskState.BLOCKED)
    
    assert len(blocked_tasks) == 1
    assert len(blocked_tasks[0].dependencies) > 0


def test_query_preserves_task_order_when_no_sort(query_engine, sample_taskset):
    """Test query preserves original task order when no sort specified."""
    tasks = query_engine.query("test-spec", filters={})
    
    # Should preserve order from taskset
    assert tasks[0].id == "1.1"
    assert tasks[1].id == "1.2"


def test_query_with_none_values(query_engine, sample_taskset):
    """Test query handles None values in filters."""
    tasks = query_engine.query(
        "test-spec",
        filters={"required_skill": None}
    )
    
    # Should handle None gracefully
    assert isinstance(tasks, list)


def test_large_result_set_pagination(query_engine, task_store):
    """Test pagination with large result set."""
    # Create taskset with many tasks
    tasks = []
    for i in range(100):
        tasks.append(
            Task(
                id=f"{i}.1",
                title=f"Task {i}",
                description="Description",
                state=TaskState.READY,
                dependencies=[],
                required_skill="backend",
                priority=i % 10,
                is_optional=False,
            )
        )
    
    taskset = Taskset(
        spec_name="large-spec",
        version=1,
        tasks=tasks,
        metadata={},
    )
    task_store.save_taskset(taskset)
    
    # Test pagination
    page1 = query_engine.query("large-spec", filters={}, limit=10, offset=0)
    page2 = query_engine.query("large-spec", filters={}, limit=10, offset=10)
    
    assert len(page1) == 10
    assert len(page2) == 10
    assert page1[0].id != page2[0].id

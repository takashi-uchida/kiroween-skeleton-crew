"""Performance tests for large tasksets.

Tests TaskRegistry performance with 1000+ tasks.
Requirements: All
"""

import time
from pathlib import Path
import sys
import pytest
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import (
    Task,
    TaskState,
    ArtifactType,
)
from necrocode.task_registry.kiro_sync import TaskDefinition


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def registry_dir(tmp_path):
    """Create temporary registry directory."""
    return tmp_path / "registry"


@pytest.fixture
def task_registry(registry_dir):
    """Create TaskRegistry instance."""
    return TaskRegistry(registry_dir)


def generate_large_taskset(num_tasks: int = 1000) -> List[TaskDefinition]:
    """Generate a large taskset for testing."""
    tasks = []
    
    for i in range(num_tasks):
        # Create dependency chain (every 10th task depends on previous)
        dependencies = []
        if i > 0 and i % 10 == 0:
            dependencies = [str(i)]
        
        task = TaskDefinition(
            id=str(i + 1),
            title=f"Task {i + 1}",
            description=f"Description for task {i + 1}",
            is_optional=i % 5 == 0,
            is_completed=False,
            dependencies=dependencies,
        )
        tasks.append(task)
    
    return tasks


# ============================================================================
# Large Taskset Creation Tests
# ============================================================================

def test_create_large_taskset_1000_tasks(task_registry):
    """Test creating taskset with 1000 tasks."""
    tasks = generate_large_taskset(1000)
    
    start = time.time()
    taskset = task_registry.create_taskset("large-spec", tasks)
    elapsed = time.time() - start
    
    assert len(taskset.tasks) == 1000
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nCreated 1000 tasks in {elapsed:.2f} seconds")


def test_create_large_taskset_5000_tasks(task_registry):
    """Test creating taskset with 5000 tasks."""
    tasks = generate_large_taskset(5000)
    
    start = time.time()
    taskset = task_registry.create_taskset("xlarge-spec", tasks)
    elapsed = time.time() - start
    
    assert len(taskset.tasks) == 5000
    assert elapsed < 60.0  # Should complete within 60 seconds
    print(f"\nCreated 5000 tasks in {elapsed:.2f} seconds")


# ============================================================================
# Large Taskset Query Tests
# ============================================================================

def test_query_large_taskset_by_state(task_registry):
    """Test querying large taskset by state."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    ready_tasks = task_registry.query_engine.filter_by_state("large-spec", TaskState.READY)
    elapsed = time.time() - start
    
    assert len(ready_tasks) > 0
    assert elapsed < 1.0  # Should complete within 1 second
    print(f"\nQueried 1000 tasks by state in {elapsed:.3f} seconds")


def test_query_large_taskset_by_skill(task_registry):
    """Test querying large taskset by skill."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    # Set required_skill on some tasks manually
    taskset = task_registry.get_taskset("large-spec")
    for i, task in enumerate(taskset.tasks):
        task.required_skill = "backend" if i % 2 == 0 else "frontend"
    task_registry.task_store.save_taskset(taskset)
    
    start = time.time()
    backend_tasks = task_registry.query_engine.filter_by_skill("large-spec", "backend")
    elapsed = time.time() - start
    
    assert len(backend_tasks) > 0
    assert elapsed < 1.0  # Should complete within 1 second
    print(f"\nQueried 1000 tasks by skill in {elapsed:.3f} seconds")


def test_complex_query_large_taskset(task_registry):
    """Test complex query on large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    results = task_registry.query_engine.query(
        "large-spec",
        filters={"state": TaskState.READY, "required_skill": "backend"},
        sort_by="priority",
        limit=50
    )
    elapsed = time.time() - start
    
    assert len(results) <= 50
    assert elapsed < 2.0  # Should complete within 2 seconds
    print(f"\nComplex query on 1000 tasks in {elapsed:.3f} seconds")


# ============================================================================
# Large Taskset Update Tests
# ============================================================================

def test_update_many_tasks_sequentially(task_registry):
    """Test updating many tasks sequentially."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    
    # Update first 100 tasks
    for i in range(100):
        task_registry.update_task_state("large-spec", str(i + 1), TaskState.RUNNING)
    
    elapsed = time.time() - start
    
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nUpdated 100 tasks sequentially in {elapsed:.2f} seconds")


def test_get_ready_tasks_from_large_taskset(task_registry):
    """Test getting ready tasks from large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    ready_tasks = task_registry.get_ready_tasks("large-spec")
    elapsed = time.time() - start
    
    assert len(ready_tasks) > 0
    assert elapsed < 2.0  # Should complete within 2 seconds
    print(f"\nGot ready tasks from 1000 tasks in {elapsed:.3f} seconds")


def test_add_artifacts_to_many_tasks(task_registry):
    """Test adding artifacts to many tasks."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    
    # Add artifacts to first 100 tasks
    for i in range(100):
        task_registry.add_artifact(
            "large-spec",
            str(i + 1),
            ArtifactType.LOG,
            f"file://log-{i}.txt"
        )
    
    elapsed = time.time() - start
    
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nAdded 100 artifacts in {elapsed:.2f} seconds")


# ============================================================================
# Large Taskset Load/Save Tests
# ============================================================================

def test_load_large_taskset_performance(task_registry):
    """Test loading large taskset performance."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    # Measure load time
    start = time.time()
    taskset = task_registry.get_taskset("large-spec")
    elapsed = time.time() - start
    
    assert len(taskset.tasks) == 1000
    assert elapsed < 2.0  # Should load within 2 seconds
    print(f"\nLoaded 1000 tasks in {elapsed:.3f} seconds")


def test_save_large_taskset_performance(task_registry):
    """Test saving large taskset performance."""
    tasks = generate_large_taskset(1000)
    taskset = task_registry.create_taskset("large-spec", tasks)
    
    # Modify taskset
    for task in taskset.tasks[:100]:
        task.state = TaskState.RUNNING
    
    # Measure save time
    start = time.time()
    task_registry.task_store.save_taskset(taskset)
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # Should save within 5 seconds
    print(f"\nSaved 1000 tasks in {elapsed:.3f} seconds")


def test_repeated_loads_performance(task_registry):
    """Test repeated loads of large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    
    # Load 10 times
    for _ in range(10):
        task_registry.get_taskset("large-spec")
    
    elapsed = time.time() - start
    
    assert elapsed < 10.0  # 10 loads within 10 seconds
    print(f"\nLoaded 1000 tasks 10 times in {elapsed:.2f} seconds")


# ============================================================================
# Memory Usage Tests
# ============================================================================

def test_memory_usage_large_taskset(task_registry):
    """Test memory usage with large taskset."""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large taskset
        tasks = generate_large_taskset(5000)
        task_registry.create_taskset("large-spec", tasks)
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory increase for 5000 tasks: {memory_increase:.2f} MB")
        
        # Should not use excessive memory (< 500 MB for 5000 tasks)
        assert memory_increase < 500
    except ImportError:
        pytest.skip("psutil not available")


# ============================================================================
# Dependency Resolution Performance Tests
# ============================================================================

def test_dependency_resolution_large_taskset(task_registry):
    """Test dependency resolution performance with large taskset."""
    # Create tasks with complex dependencies
    tasks = []
    for i in range(1000):
        dependencies = []
        if i > 0:
            # Each task depends on previous 3 tasks
            for j in range(max(0, i - 3), i):
                dependencies.append(str(j + 1))
        
        task = TaskDefinition(
            id=str(i + 1),
            title=f"Task {i + 1}",
            description=f"Task with dependencies",
            is_optional=False,
            is_completed=False,
            dependencies=dependencies,
        )
        tasks.append(task)
    
    task_registry.create_taskset("dep-spec", tasks)
    
    # Complete first task and measure unblocking time
    start = time.time()
    task_registry.update_task_state("dep-spec", "1", TaskState.RUNNING)
    task_registry.update_task_state("dep-spec", "1", TaskState.DONE)
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # Should complete within 5 seconds
    print(f"\nDependency resolution in {elapsed:.3f} seconds")


def test_execution_order_large_taskset(task_registry):
    """Test execution order calculation for large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    execution_order = task_registry.get_execution_order("large-spec")
    elapsed = time.time() - start
    
    assert len(execution_order) > 0
    assert elapsed < 5.0  # Should complete within 5 seconds
    print(f"\nCalculated execution order for 1000 tasks in {elapsed:.3f} seconds")


# ============================================================================
# Graph Visualization Performance Tests
# ============================================================================

def test_graph_visualization_large_taskset(task_registry):
    """Test graph visualization performance with large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    dot_graph = task_registry.export_dependency_graph_dot("large-spec")
    elapsed = time.time() - start
    
    assert len(dot_graph) > 0
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nGenerated DOT graph for 1000 tasks in {elapsed:.2f} seconds")


def test_mermaid_visualization_large_taskset(task_registry):
    """Test Mermaid visualization performance with large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    start = time.time()
    mermaid_graph = task_registry.export_dependency_graph_mermaid("large-spec")
    elapsed = time.time() - start
    
    assert len(mermaid_graph) > 0
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nGenerated Mermaid graph for 1000 tasks in {elapsed:.2f} seconds")


# ============================================================================
# Backup/Restore Performance Tests
# ============================================================================

def test_backup_large_taskset_performance(task_registry, tmp_path):
    """Test backup performance with large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    backup_dir = tmp_path / "backups"
    
    start = time.time()
    backup_path = task_registry.task_store.backup_taskset("large-spec", backup_dir)
    elapsed = time.time() - start
    
    assert backup_path.exists()
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nBacked up 1000 tasks in {elapsed:.2f} seconds")


def test_restore_large_taskset_performance(task_registry, tmp_path):
    """Test restore performance with large taskset."""
    tasks = generate_large_taskset(1000)
    task_registry.create_taskset("large-spec", tasks)
    
    # Create backup
    backup_dir = tmp_path / "backups"
    backup_path = task_registry.task_store.backup_taskset("large-spec", backup_dir)
    
    # Restore
    start = time.time()
    spec_name = task_registry.task_store.restore_taskset(backup_path)
    elapsed = time.time() - start
    
    assert spec_name == "large-spec"
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nRestored 1000 tasks in {elapsed:.2f} seconds")


# ============================================================================
# Scalability Tests
# ============================================================================

def test_scalability_increasing_taskset_sizes(task_registry):
    """Test scalability with increasing taskset sizes."""
    sizes = [100, 500, 1000, 2000]
    times = []
    
    for size in sizes:
        tasks = generate_large_taskset(size)
        
        start = time.time()
        task_registry.create_taskset(f"spec-{size}", tasks)
        elapsed = time.time() - start
        
        times.append(elapsed)
        print(f"\nCreated {size} tasks in {elapsed:.2f} seconds")
    
    # Time should scale roughly linearly (not exponentially)
    # Check that doubling size doesn't quadruple time
    if len(times) >= 2:
        ratio = times[-1] / times[0]
        size_ratio = sizes[-1] / sizes[0]
        assert ratio < size_ratio * 2  # Should be roughly linear


def test_multiple_large_tasksets(task_registry):
    """Test managing multiple large tasksets."""
    num_tasksets = 5
    tasks_per_set = 500
    
    start = time.time()
    
    # Create multiple large tasksets
    for i in range(num_tasksets):
        tasks = generate_large_taskset(tasks_per_set)
        task_registry.create_taskset(f"spec-{i}", tasks)
    
    elapsed = time.time() - start
    
    total_tasks = num_tasksets * tasks_per_set
    assert elapsed < 60.0  # Should complete within 60 seconds
    print(f"\nCreated {num_tasksets} tasksets with {total_tasks} total tasks in {elapsed:.2f} seconds")


# ============================================================================
# Stress Tests
# ============================================================================

@pytest.mark.slow
def test_extreme_large_taskset_10000_tasks(task_registry):
    """Stress test with 10000 tasks (marked as slow)."""
    tasks = generate_large_taskset(10000)
    
    start = time.time()
    taskset = task_registry.create_taskset("extreme-spec", tasks)
    elapsed = time.time() - start
    
    assert len(taskset.tasks) == 10000
    assert elapsed < 120.0  # Should complete within 2 minutes
    print(f"\nCreated 10000 tasks in {elapsed:.2f} seconds")


@pytest.mark.slow
def test_extreme_query_performance_10000_tasks(task_registry):
    """Stress test query performance with 10000 tasks."""
    tasks = generate_large_taskset(10000)
    task_registry.create_taskset("extreme-spec", tasks)
    
    start = time.time()
    ready_tasks = task_registry.get_ready_tasks("extreme-spec")
    elapsed = time.time() - start
    
    assert len(ready_tasks) > 0
    assert elapsed < 5.0  # Should complete within 5 seconds
    print(f"\nQueried 10000 tasks in {elapsed:.3f} seconds")

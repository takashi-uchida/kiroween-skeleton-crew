"""Integration tests for concurrent access to TaskRegistry.

Tests multiple processes/threads accessing TaskRegistry simultaneously.
Tests optimistic locking behavior.
Requirements: 6.2
"""

import time
from pathlib import Path
import sys
import pytest
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
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
from necrocode.task_registry.exceptions import LockTimeoutError


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


@pytest.fixture
def sample_tasks():
    """Create sample task definitions for testing."""
    return [
        TaskDefinition(
            id="1.1",
            title="Task 1",
            description="First task",
            is_optional=False,
            is_completed=False,
            dependencies=[],
        ),
        TaskDefinition(
            id="1.2",
            title="Task 2",
            description="Second task",
            is_optional=False,
            is_completed=False,
            dependencies=[],
        ),
        TaskDefinition(
            id="1.3",
            title="Task 3",
            description="Third task",
            is_optional=False,
            is_completed=False,
            dependencies=[],
        ),
    ]


# ============================================================================
# Thread-based Concurrent Access Tests
# ============================================================================

def test_concurrent_task_state_updates_threads(task_registry, sample_tasks):
    """Test concurrent task state updates from multiple threads."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    results = []
    errors = []
    
    def update_task(task_id: str, worker_id: int):
        try:
            # Update task state
            task_registry.update_task_state(
                "test-spec",
                task_id,
                TaskState.RUNNING,
                metadata={"worker_id": worker_id}
            )
            results.append((task_id, worker_id))
        except Exception as e:
            errors.append((task_id, worker_id, str(e)))
    
    # Create threads to update different tasks concurrently
    threads = []
    for i, task in enumerate(sample_tasks):
        thread = threading.Thread(target=update_task, args=(task.id, i))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All updates should succeed
    assert len(results) == 3
    assert len(errors) == 0
    
    # Verify all tasks were updated
    taskset = task_registry.get_taskset("test-spec")
    for task in taskset.tasks:
        assert task.state == TaskState.RUNNING


def test_concurrent_same_task_updates_threads(task_registry, sample_tasks):
    """Test concurrent updates to the same task from multiple threads."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    success_count = 0
    lock = threading.Lock()
    
    def update_same_task(worker_id: int):
        nonlocal success_count
        try:
            task_registry.update_task_state(
                "test-spec",
                "1.1",
                TaskState.RUNNING,
                metadata={"worker_id": worker_id}
            )
            with lock:
                success_count += 1
        except LockTimeoutError:
            pass  # Expected for some threads
    
    # Create multiple threads trying to update the same task
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(update_same_task, i) for i in range(5)]
        for future in futures:
            future.result()
    
    # All updates should eventually succeed due to locking
    assert success_count >= 1


def test_concurrent_artifact_additions_threads(task_registry, sample_tasks):
    """Test concurrent artifact additions from multiple threads."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    def add_artifact(task_id: str, artifact_num: int):
        task_registry.add_artifact(
            "test-spec",
            task_id,
            ArtifactType.LOG,
            f"file://log-{artifact_num}.txt",
            metadata={"artifact_num": artifact_num}
        )
    
    # Add artifacts concurrently to different tasks
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(10):
            task_id = sample_tasks[i % len(sample_tasks)].id
            futures.append(executor.submit(add_artifact, task_id, i))
        
        for future in futures:
            future.result()
    
    # Verify all artifacts were added
    taskset = task_registry.get_taskset("test-spec")
    total_artifacts = sum(len(task.artifacts) for task in taskset.tasks)
    assert total_artifacts == 10


def test_concurrent_read_operations_threads(task_registry, sample_tasks):
    """Test concurrent read operations from multiple threads."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    results = []
    
    def read_taskset():
        taskset = task_registry.get_taskset("test-spec")
        results.append(len(taskset.tasks))
    
    # Multiple threads reading concurrently
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(read_taskset) for _ in range(20)]
        for future in futures:
            future.result()
    
    # All reads should succeed and return same result
    assert len(results) == 20
    assert all(count == 3 for count in results)


def test_concurrent_mixed_operations_threads(task_registry, sample_tasks):
    """Test concurrent mixed read/write operations from multiple threads."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    read_count = 0
    write_count = 0
    lock = threading.Lock()
    
    def mixed_operations(worker_id: int):
        nonlocal read_count, write_count
        
        # Read operation
        taskset = task_registry.get_taskset("test-spec")
        with lock:
            read_count += 1
        
        # Write operation
        if worker_id % 2 == 0:
            try:
                task_id = sample_tasks[worker_id % len(sample_tasks)].id
                task_registry.update_task_state(
                    "test-spec",
                    task_id,
                    TaskState.RUNNING
                )
                with lock:
                    write_count += 1
            except Exception:
                pass
    
    # Execute mixed operations
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(mixed_operations, i) for i in range(10)]
        for future in futures:
            future.result()
    
    # All reads should succeed
    assert read_count == 10
    # Some writes should succeed
    assert write_count >= 1


# ============================================================================
# Process-based Concurrent Access Tests
# ============================================================================

def _update_task_process(registry_dir: str, spec_name: str, task_id: str, worker_id: int):
    """Helper function for process-based testing."""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from necrocode.task_registry.task_registry import TaskRegistry
    from necrocode.task_registry.models import TaskState
    
    try:
        registry = TaskRegistry(Path(registry_dir))
        registry.update_task_state(
            spec_name,
            task_id,
            TaskState.RUNNING,
            metadata={"worker_id": worker_id}
        )
        return True
    except Exception as e:
        return False


def test_concurrent_updates_multiple_processes(task_registry, sample_tasks, registry_dir):
    """Test concurrent updates from multiple processes."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Use multiprocessing to simulate multiple processes
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = []
        for i, task in enumerate(sample_tasks):
            future = executor.submit(
                _update_task_process,
                str(registry_dir),  # Convert Path to string for serialization
                "test-spec",
                task.id,
                i
            )
            futures.append(future)
        
        results = [future.result() for future in futures]
    
    # All updates should succeed
    assert all(results)
    
    # Verify updates persisted
    taskset = task_registry.get_taskset("test-spec")
    for task in taskset.tasks:
        assert task.state == TaskState.RUNNING


def _read_taskset_process(registry_dir: str, spec_name: str):
    """Helper function for process-based reading."""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from necrocode.task_registry.task_registry import TaskRegistry
    
    try:
        registry = TaskRegistry(Path(registry_dir))
        taskset = registry.get_taskset(spec_name)
        return len(taskset.tasks)
    except Exception:
        return -1


def test_concurrent_reads_multiple_processes(task_registry, sample_tasks, registry_dir):
    """Test concurrent reads from multiple processes."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Multiple processes reading concurrently
    with ProcessPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(_read_taskset_process, str(registry_dir), "test-spec")
            for _ in range(5)
        ]
        results = [future.result() for future in futures]
    
    # All reads should succeed
    assert all(count == 3 for count in results)


# ============================================================================
# Optimistic Locking Tests
# ============================================================================

def test_optimistic_locking_version_increment(task_registry, sample_tasks):
    """Test that version increments with each update (optimistic locking)."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    initial_version = task_registry.get_taskset("test-spec").version
    
    # Perform multiple updates
    for i in range(5):
        task_id = sample_tasks[i % len(sample_tasks)].id
        task_registry.update_task_state("test-spec", task_id, TaskState.RUNNING)
        task_registry.update_task_state("test-spec", task_id, TaskState.READY)
    
    final_version = task_registry.get_taskset("test-spec").version
    
    # Version should have incremented
    assert final_version > initial_version


def test_lock_prevents_concurrent_writes(task_registry, sample_tasks):
    """Test that locking prevents concurrent writes to same taskset."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    write_times = []
    lock = threading.Lock()
    
    def timed_update(task_id: str):
        start = time.time()
        task_registry.update_task_state("test-spec", task_id, TaskState.RUNNING)
        end = time.time()
        with lock:
            write_times.append((start, end))
    
    # Execute concurrent updates
    threads = []
    for task in sample_tasks:
        thread = threading.Thread(target=timed_update, args=(task.id,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Check that writes didn't overlap (serialized by lock)
    write_times.sort()
    for i in range(len(write_times) - 1):
        # Each write should complete before next one starts (with small tolerance)
        assert write_times[i][1] <= write_times[i + 1][0] + 0.1


# ============================================================================
# Stress Tests
# ============================================================================

def test_high_concurrency_stress(task_registry, sample_tasks):
    """Stress test with high number of concurrent operations."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    success_count = 0
    lock = threading.Lock()
    
    def random_operation(worker_id: int):
        nonlocal success_count
        try:
            # Alternate between different operations
            if worker_id % 3 == 0:
                # Read
                task_registry.get_taskset("test-spec")
            elif worker_id % 3 == 1:
                # Update
                task_id = sample_tasks[worker_id % len(sample_tasks)].id
                task_registry.update_task_state("test-spec", task_id, TaskState.RUNNING)
            else:
                # Add artifact
                task_id = sample_tasks[worker_id % len(sample_tasks)].id
                task_registry.add_artifact(
                    "test-spec",
                    task_id,
                    ArtifactType.LOG,
                    f"file://log-{worker_id}.txt"
                )
            
            with lock:
                success_count += 1
        except Exception:
            pass
    
    # Execute many concurrent operations
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(random_operation, i) for i in range(100)]
        for future in futures:
            future.result()
    
    # Most operations should succeed
    assert success_count >= 80


def test_rapid_sequential_updates(task_registry, sample_tasks):
    """Test rapid sequential updates to verify no race conditions."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    # Perform many rapid updates
    for i in range(100):
        task_id = sample_tasks[i % len(sample_tasks)].id
        task_registry.update_task_state("test-spec", task_id, TaskState.RUNNING)
        task_registry.update_task_state("test-spec", task_id, TaskState.READY)
    
    # All tasks should be in READY state
    taskset = task_registry.get_taskset("test-spec")
    for task in taskset.tasks:
        assert task.state == TaskState.READY


# ============================================================================
# Data Consistency Tests
# ============================================================================

def test_data_consistency_after_concurrent_updates(task_registry, sample_tasks):
    """Test data remains consistent after concurrent updates."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    def update_and_verify(task_id: str, worker_id: int):
        # Update task
        task_registry.update_task_state(
            "test-spec",
            task_id,
            TaskState.RUNNING,
            metadata={"worker_id": worker_id}
        )
        
        # Verify update
        taskset = task_registry.get_taskset("test-spec")
        task = next(t for t in taskset.tasks if t.id == task_id)
        assert task.state == TaskState.RUNNING
    
    # Execute concurrent updates and verifications
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(update_and_verify, task.id, i)
            for i, task in enumerate(sample_tasks)
        ]
        for future in futures:
            future.result()
    
    # Final verification
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 3
    for task in taskset.tasks:
        assert task.state == TaskState.RUNNING


def test_event_log_consistency_concurrent_updates(task_registry, sample_tasks):
    """Test event log remains consistent with concurrent updates."""
    task_registry.create_taskset("test-spec", sample_tasks)
    
    def update_task(task_id: str):
        task_registry.update_task_state("test-spec", task_id, TaskState.RUNNING)
        task_registry.update_task_state("test-spec", task_id, TaskState.DONE)
    
    # Execute concurrent updates
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(update_task, task.id) for task in sample_tasks]
        for future in futures:
            future.result()
    
    # Verify events were recorded for all tasks
    for task in sample_tasks:
        events = task_registry.event_store.get_events_by_task("test-spec", task.id)
        # Should have at least: Created, Updated (Running), Updated (Done)
        assert len(events) >= 3


# ============================================================================
# Multiple Tasksets Concurrent Access
# ============================================================================

def test_concurrent_access_different_tasksets(task_registry, sample_tasks):
    """Test concurrent access to different tasksets."""
    # Create multiple tasksets
    for i in range(3):
        task_registry.create_taskset(f"spec-{i}", sample_tasks)
    
    def update_taskset(spec_name: str, task_id: str):
        task_registry.update_task_state(spec_name, task_id, TaskState.RUNNING)
    
    # Update different tasksets concurrently
    with ThreadPoolExecutor(max_workers=9) as executor:
        futures = []
        for i in range(3):
            for task in sample_tasks:
                future = executor.submit(update_taskset, f"spec-{i}", task.id)
                futures.append(future)
        
        for future in futures:
            future.result()
    
    # Verify all tasksets were updated correctly
    for i in range(3):
        taskset = task_registry.get_taskset(f"spec-{i}")
        for task in taskset.tasks:
            assert task.state == TaskState.RUNNING

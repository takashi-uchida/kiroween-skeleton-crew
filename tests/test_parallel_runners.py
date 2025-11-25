"""Performance tests for parallel Agent Runner execution.

Tests parallel execution performance, resource conflicts, and coordination.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.models import TaskContext, ImplementationResult
from necrocode.agent_runner.parallel_coordinator import ParallelCoordinator
from necrocode.agent_runner.runner_orchestrator import RunnerOrchestrator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_workspaces(tmp_path):
    """Create multiple temporary Git workspaces."""
    workspaces = []
    
    for i in range(5):
        workspace = tmp_path / f"workspace_{i}"
        workspace.mkdir()
        
        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        
        # Configure Git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        
        # Create initial commit
        readme = workspace / "README.md"
        readme.write_text(f"# Test Project {i}\n")
        
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        
        workspaces.append(workspace)
    
    return workspaces


@pytest.fixture
def parallel_coordinator(tmp_path):
    """Create ParallelCoordinator instance."""
    return ParallelCoordinator(
        coordination_dir=tmp_path / "coordination",
        max_parallel_runners=3,
    )


@pytest.fixture
def runner_config(tmp_path):
    """Create runner configuration with parallel support."""
    return RunnerConfig(
        log_level="INFO",
        artifact_store_url=f"file://{tmp_path / 'artifacts'}",
        task_registry_path=tmp_path / "task_registry",
        max_parallel_runners=3,
    )


def create_task_context(workspace, task_id):
    """Create a task context."""
    return TaskContext(
        task_id=task_id,
        spec_name="parallel-test",
        title=f"Parallel test task {task_id}",
        description="Task for parallel testing",
        acceptance_criteria=["Task should complete"],
        dependencies=[],
        required_skill="backend",
        slot_path=workspace,
        slot_id=f"slot-{task_id}",
        branch_name=f"feature/task-{task_id}",
        timeout_seconds=60,
    )


def mock_simple_implementation(runner):
    """Mock a simple implementation."""
    def mock_execute(task_context, workspace):
        # Simulate some work
        time.sleep(0.5)
        
        test_file = workspace.path / f"test_{task_context.task_id}.py"
        test_file.write_text(f"print('test {task_context.task_id}')")
        
        return ImplementationResult(
            success=True,
            diff=f"+ test_{task_context.task_id}.py",
            files_changed=[f"test_{task_context.task_id}.py"],
            duration_seconds=0.5,
        )
    
    runner.task_executor.execute = mock_execute


# ============================================================================
# Parallel Coordinator Tests
# ============================================================================

@pytest.mark.performance
def test_parallel_coordinator_registration(parallel_coordinator, temp_workspaces):
    """Test parallel coordinator registration."""
    # Register multiple runners
    for i in range(3):
        success = parallel_coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=temp_workspaces[i],
        )
        assert success
    
    # Check concurrent count
    count = parallel_coordinator.get_concurrent_count()
    assert count == 3
    
    # Try to register beyond limit
    success = parallel_coordinator.register_runner(
        runner_id="runner-4",
        task_id="task-4",
        spec_name="test-spec",
        workspace_path=temp_workspaces[3],
    )
    assert not success  # Should be rejected


@pytest.mark.performance
def test_parallel_coordinator_wait_time(parallel_coordinator, temp_workspaces):
    """Test wait time calculation."""
    # Initially no wait time
    wait_time = parallel_coordinator.get_wait_time()
    assert wait_time == 0.0
    
    # Register runners up to limit
    for i in range(3):
        parallel_coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=temp_workspaces[i],
        )
    
    # Now should have wait time
    wait_time = parallel_coordinator.get_wait_time()
    assert wait_time > 0.0
    
    print(f"\nEstimated wait time: {wait_time:.2f}s")


@pytest.mark.performance
def test_parallel_coordinator_conflict_detection(parallel_coordinator, temp_workspaces):
    """Test resource conflict detection."""
    # Register runner with resources
    parallel_coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="test-spec",
        workspace_path=temp_workspaces[0],
    )
    
    # Update resources
    parallel_coordinator.update_resources(
        runner_id="runner-1",
        files=["file1.py", "file2.py"],
        branches=["feature/branch-1"],
    )
    
    # Check for conflicts
    conflicts = parallel_coordinator.detect_conflicts(
        runner_id="runner-2",
        files=["file1.py"],  # Conflict
        branches=["feature/branch-2"],
    )
    
    assert len(conflicts) > 0
    assert "file1.py" in conflicts[0]


# ============================================================================
# Parallel Execution Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_parallel_task_execution(runner_config, temp_workspaces):
    """Test parallel execution of multiple tasks."""
    num_tasks = 3
    results = []
    threads = []
    
    def run_task(workspace, task_id):
        runner = RunnerOrchestrator(config=runner_config)
        task_context = create_task_context(workspace, task_id)
        mock_simple_implementation(runner)
        
        result = runner.run(task_context)
        results.append(result)
    
    # Start tasks in parallel
    start_time = time.time()
    
    for i in range(num_tasks):
        thread = threading.Thread(
            target=run_task,
            args=(temp_workspaces[i], f"parallel-{i}")
        )
        thread.start()
        threads.append(thread)
    
    # Wait for all tasks to complete
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Verify all tasks succeeded
    assert len(results) == num_tasks
    assert all(r.success for r in results)
    
    # Parallel execution should be faster than sequential
    # (3 tasks * 0.5s work + overhead should be < 3 * sequential time)
    print(f"\nParallel execution of {num_tasks} tasks:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Expected sequential time: ~{num_tasks * 1.5:.2f}s")
    
    # Should complete in less time than sequential
    assert total_time < num_tasks * 2.0


@pytest.mark.performance
@pytest.mark.slow
def test_parallel_vs_sequential_performance(runner_config, temp_workspaces):
    """Compare parallel vs sequential execution performance."""
    num_tasks = 3
    
    # Sequential execution
    sequential_results = []
    sequential_start = time.time()
    
    for i in range(num_tasks):
        runner = RunnerOrchestrator(config=runner_config)
        task_context = create_task_context(temp_workspaces[i], f"seq-{i}")
        mock_simple_implementation(runner)
        
        result = runner.run(task_context)
        sequential_results.append(result)
    
    sequential_time = time.time() - sequential_start
    
    # Parallel execution
    parallel_results = []
    threads = []
    
    def run_task(workspace, task_id):
        runner = RunnerOrchestrator(config=runner_config)
        task_context = create_task_context(workspace, task_id)
        mock_simple_implementation(runner)
        
        result = runner.run(task_context)
        parallel_results.append(result)
    
    parallel_start = time.time()
    
    for i in range(num_tasks):
        thread = threading.Thread(
            target=run_task,
            args=(temp_workspaces[i], f"par-{i}")
        )
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    parallel_time = time.time() - parallel_start
    
    # Calculate speedup
    speedup = sequential_time / parallel_time
    
    print(f"\nParallel vs Sequential performance:")
    print(f"  Sequential time: {sequential_time:.2f}s")
    print(f"  Parallel time: {parallel_time:.2f}s")
    print(f"  Speedup: {speedup:.2f}x")
    
    # Parallel should be faster
    assert parallel_time < sequential_time
    
    # Should have some speedup (at least 1.5x)
    assert speedup > 1.5


# ============================================================================
# Scalability Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_parallel_execution_scalability(runner_config, temp_workspaces):
    """Test how parallel execution scales with number of tasks."""
    task_counts = [1, 2, 3]
    execution_times = []
    
    for num_tasks in task_counts:
        results = []
        threads = []
        
        def run_task(workspace, task_id):
            runner = RunnerOrchestrator(config=runner_config)
            task_context = create_task_context(workspace, task_id)
            mock_simple_implementation(runner)
            
            result = runner.run(task_context)
            results.append(result)
        
        start_time = time.time()
        
        for i in range(num_tasks):
            thread = threading.Thread(
                target=run_task,
                args=(temp_workspaces[i], f"scale-{num_tasks}-{i}")
            )
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        execution_time = time.time() - start_time
        execution_times.append(execution_time)
        
        assert all(r.success for r in results)
    
    print(f"\nParallel execution scalability:")
    for count, time_taken in zip(task_counts, execution_times):
        print(f"  {count} tasks: {time_taken:.2f}s")
    
    # Time should not increase linearly
    # 3 tasks should take less than 3x time of 1 task
    assert execution_times[2] < execution_times[0] * 3


# ============================================================================
# Resource Conflict Tests
# ============================================================================

@pytest.mark.performance
def test_parallel_execution_with_conflicts(runner_config, temp_workspaces):
    """Test parallel execution with resource conflicts."""
    # Use same workspace for multiple tasks (conflict)
    workspace = temp_workspaces[0]
    
    results = []
    threads = []
    
    def run_task(task_id):
        runner = RunnerOrchestrator(config=runner_config)
        task_context = create_task_context(workspace, task_id)
        mock_simple_implementation(runner)
        
        try:
            result = runner.run(task_context)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e)})
    
    # Try to run 2 tasks on same workspace
    for i in range(2):
        thread = threading.Thread(
            target=run_task,
            args=(f"conflict-{i}",)
        )
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    # At least one should complete
    # (The other may be rejected or queued)
    assert len(results) > 0


# ============================================================================
# Throughput Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_parallel_throughput(runner_config, temp_workspaces):
    """Test parallel execution throughput."""
    num_tasks = 6  # More than max parallel (3)
    
    results = []
    threads = []
    
    def run_task(workspace, task_id):
        runner = RunnerOrchestrator(config=runner_config)
        task_context = create_task_context(workspace, task_id)
        mock_simple_implementation(runner)
        
        result = runner.run(task_context)
        results.append(result)
    
    start_time = time.time()
    
    # Start all tasks
    for i in range(num_tasks):
        workspace_idx = i % len(temp_workspaces)
        thread = threading.Thread(
            target=run_task,
            args=(temp_workspaces[workspace_idx], f"throughput-{i}")
        )
        thread.start()
        threads.append(thread)
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Calculate throughput
    throughput = num_tasks / total_time
    
    print(f"\nParallel throughput:")
    print(f"  Total tasks: {num_tasks}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Throughput: {throughput:.2f} tasks/second")
    
    # Should have reasonable throughput
    assert throughput > 0.2


# ============================================================================
# Load Balancing Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_parallel_load_distribution(runner_config, temp_workspaces):
    """Test load distribution across parallel runners."""
    num_tasks = 9  # 3x max parallel
    
    task_start_times = {}
    task_end_times = {}
    
    def run_task(workspace, task_id):
        task_start_times[task_id] = time.time()
        
        runner = RunnerOrchestrator(config=runner_config)
        task_context = create_task_context(workspace, task_id)
        mock_simple_implementation(runner)
        
        runner.run(task_context)
        
        task_end_times[task_id] = time.time()
    
    threads = []
    
    for i in range(num_tasks):
        workspace_idx = i % len(temp_workspaces)
        task_id = f"load-{i}"
        thread = threading.Thread(
            target=run_task,
            args=(temp_workspaces[workspace_idx], task_id)
        )
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    # Analyze load distribution
    # Tasks should be distributed in waves (3 at a time)
    print(f"\nLoad distribution:")
    for task_id in sorted(task_start_times.keys()):
        start = task_start_times[task_id]
        end = task_end_times[task_id]
        duration = end - start
        print(f"  {task_id}: {duration:.2f}s")


# ============================================================================
# Stress Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_parallel_stress_test(runner_config, temp_workspaces):
    """Stress test with many parallel tasks."""
    num_tasks = 15
    
    results = []
    threads = []
    
    def run_task(workspace, task_id):
        try:
            runner = RunnerOrchestrator(config=runner_config)
            task_context = create_task_context(workspace, task_id)
            mock_simple_implementation(runner)
            
            result = runner.run(task_context)
            results.append({"success": result.success, "task_id": task_id})
        except Exception as e:
            results.append({"success": False, "task_id": task_id, "error": str(e)})
    
    start_time = time.time()
    
    for i in range(num_tasks):
        workspace_idx = i % len(temp_workspaces)
        thread = threading.Thread(
            target=run_task,
            args=(temp_workspaces[workspace_idx], f"stress-{i}")
        )
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Calculate success rate
    successful = sum(1 for r in results if r.get("success", False))
    success_rate = (successful / num_tasks) * 100
    
    print(f"\nParallel stress test:")
    print(f"  Total tasks: {num_tasks}")
    print(f"  Successful: {successful}")
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Total time: {total_time:.2f}s")
    
    # Should have reasonable success rate
    assert success_rate > 80.0


# ============================================================================
# Coordination Overhead Tests
# ============================================================================

@pytest.mark.performance
def test_coordination_overhead(parallel_coordinator, temp_workspaces):
    """Test overhead of parallel coordination."""
    num_operations = 100
    
    # Measure registration time
    start_time = time.time()
    
    for i in range(num_operations):
        parallel_coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="test-spec",
            workspace_path=temp_workspaces[i % len(temp_workspaces)],
        )
        parallel_coordinator.unregister_runner(f"runner-{i}")
    
    total_time = time.time() - start_time
    avg_time = total_time / num_operations
    
    print(f"\nCoordination overhead:")
    print(f"  Operations: {num_operations}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Average per operation: {avg_time * 1000:.2f}ms")
    
    # Coordination should be fast (< 10ms per operation)
    assert avg_time < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])

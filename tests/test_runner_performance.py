"""Performance tests for Agent Runner.

Tests execution time, resource usage, and throughput of the Agent Runner.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.models import TaskContext, ImplementationResult
from necrocode.agent_runner.runner_orchestrator import RunnerOrchestrator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary Git workspace."""
    workspace = tmp_path / "workspace"
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
    readme.write_text("# Test Project\n")
    
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
    
    return workspace


@pytest.fixture
def runner_config(tmp_path):
    """Create runner configuration."""
    return RunnerConfig(
        log_level="INFO",
        artifact_store_url=f"file://{tmp_path / 'artifacts'}",
        task_registry_path=tmp_path / "task_registry",
        default_timeout_seconds=300,
    )


@pytest.fixture
def runner_orchestrator(runner_config):
    """Create RunnerOrchestrator instance."""
    return RunnerOrchestrator(config=runner_config)


def create_task_context(temp_workspace, task_id="perf-test-1"):
    """Create a task context for performance testing."""
    return TaskContext(
        task_id=task_id,
        spec_name="perf-test",
        title="Performance test task",
        description="Task for performance testing",
        acceptance_criteria=["Task should complete"],
        dependencies=[],
        required_skill="backend",
        slot_path=temp_workspace,
        slot_id="slot-1",
        branch_name=f"feature/task-{task_id}",
        timeout_seconds=300,
    )


def mock_simple_implementation(runner_orchestrator):
    """Mock a simple implementation."""
    def mock_execute(task_context, workspace):
        # Create a simple file
        test_file = workspace.path / "test.py"
        test_file.write_text("print('test')")
        
        return ImplementationResult(
            success=True,
            diff="+ test.py",
            files_changed=["test.py"],
            duration_seconds=0.1,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute


# ============================================================================
# Basic Performance Tests
# ============================================================================

@pytest.mark.performance
def test_single_task_execution_time(runner_orchestrator, temp_workspace):
    """Test execution time for a single task."""
    task_context = create_task_context(temp_workspace)
    mock_simple_implementation(runner_orchestrator)
    
    # Measure execution time
    start_time = time.time()
    result = runner_orchestrator.run(task_context)
    execution_time = time.time() - start_time
    
    # Verify success
    assert result.success
    
    # Execution should complete in reasonable time (< 30 seconds)
    assert execution_time < 30.0
    
    print(f"\nSingle task execution time: {execution_time:.2f}s")


@pytest.mark.performance
def test_workspace_preparation_time(runner_orchestrator, temp_workspace):
    """Test workspace preparation time."""
    task_context = create_task_context(temp_workspace)
    
    # Measure workspace preparation time
    start_time = time.time()
    workspace = runner_orchestrator._prepare_workspace(task_context)
    prep_time = time.time() - start_time
    
    # Verify workspace was prepared
    assert workspace is not None
    
    # Preparation should be fast (< 5 seconds)
    assert prep_time < 5.0
    
    print(f"\nWorkspace preparation time: {prep_time:.2f}s")


@pytest.mark.performance
def test_commit_and_push_time(runner_orchestrator, temp_workspace):
    """Test commit and push time."""
    task_context = create_task_context(temp_workspace)
    
    # Prepare workspace
    workspace = runner_orchestrator._prepare_workspace(task_context)
    
    # Create a test file
    test_file = workspace.path / "test.py"
    test_file.write_text("print('test')")
    
    # Measure commit and push time
    start_time = time.time()
    push_result = runner_orchestrator._commit_and_push(task_context, workspace)
    commit_time = time.time() - start_time
    
    # Verify success
    assert push_result.success
    
    # Commit should be fast (< 5 seconds)
    assert commit_time < 5.0
    
    print(f"\nCommit and push time: {commit_time:.2f}s")


@pytest.mark.performance
def test_artifact_upload_time(runner_orchestrator, temp_workspace):
    """Test artifact upload time."""
    task_context = create_task_context(temp_workspace)
    
    # Create mock results
    impl_result = ImplementationResult(
        success=True,
        diff="+ test.py\n+ print('test')",
        files_changed=["test.py"],
        duration_seconds=1.0,
    )
    
    from necrocode.agent_runner.models import TestResult
    test_result = TestResult(
        success=True,
        test_results=[],
        total_duration_seconds=0.0,
    )
    
    # Measure upload time
    start_time = time.time()
    artifacts = runner_orchestrator._upload_artifacts(
        task_context,
        impl_result,
        test_result
    )
    upload_time = time.time() - start_time
    
    # Verify artifacts were uploaded
    assert len(artifacts) > 0
    
    # Upload should be fast (< 10 seconds)
    assert upload_time < 10.0
    
    print(f"\nArtifact upload time: {upload_time:.2f}s")


# ============================================================================
# Sequential Execution Performance Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_sequential_task_execution(runner_orchestrator, temp_workspace):
    """Test sequential execution of multiple tasks."""
    num_tasks = 5
    execution_times = []
    
    for i in range(num_tasks):
        task_context = create_task_context(temp_workspace, f"seq-test-{i}")
        mock_simple_implementation(runner_orchestrator)
        
        # Measure execution time
        start_time = time.time()
        result = runner_orchestrator.run(task_context)
        execution_time = time.time() - start_time
        
        assert result.success
        execution_times.append(execution_time)
        
        # Reset state for next task
        runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    # Calculate statistics
    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)
    
    print(f"\nSequential execution of {num_tasks} tasks:")
    print(f"  Average: {avg_time:.2f}s")
    print(f"  Min: {min_time:.2f}s")
    print(f"  Max: {max_time:.2f}s")
    print(f"  Total: {sum(execution_times):.2f}s")
    
    # Average should be reasonable
    assert avg_time < 30.0


@pytest.mark.performance
def test_execution_overhead(runner_orchestrator, temp_workspace):
    """Test execution overhead (time spent in orchestration vs actual work)."""
    task_context = create_task_context(temp_workspace)
    
    # Mock implementation with known duration
    implementation_duration = 1.0
    
    def mock_execute(task_context, workspace):
        time.sleep(implementation_duration)
        test_file = workspace.path / "test.py"
        test_file.write_text("print('test')")
        
        return ImplementationResult(
            success=True,
            diff="+ test.py",
            files_changed=["test.py"],
            duration_seconds=implementation_duration,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Measure total execution time
    start_time = time.time()
    result = runner_orchestrator.run(task_context)
    total_time = time.time() - start_time
    
    assert result.success
    
    # Calculate overhead
    overhead = total_time - implementation_duration
    overhead_percent = (overhead / total_time) * 100
    
    print(f"\nExecution overhead:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Implementation time: {implementation_duration:.2f}s")
    print(f"  Overhead: {overhead:.2f}s ({overhead_percent:.1f}%)")
    
    # Overhead should be reasonable (< 50% of total time)
    assert overhead_percent < 50.0


# ============================================================================
# Resource Usage Tests
# ============================================================================

@pytest.mark.performance
def test_memory_usage_single_task(runner_orchestrator, temp_workspace):
    """Test memory usage for a single task."""
    import psutil
    import os
    
    task_context = create_task_context(temp_workspace)
    mock_simple_implementation(runner_orchestrator)
    
    # Get initial memory
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Execute task
    result = runner_orchestrator.run(task_context)
    assert result.success
    
    # Get final memory
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"\nMemory usage:")
    print(f"  Initial: {initial_memory:.2f} MB")
    print(f"  Final: {final_memory:.2f} MB")
    print(f"  Increase: {memory_increase:.2f} MB")
    
    # Memory increase should be reasonable (< 100 MB)
    assert memory_increase < 100.0


@pytest.mark.performance
@pytest.mark.slow
def test_memory_usage_multiple_tasks(runner_orchestrator, temp_workspace):
    """Test memory usage for multiple tasks."""
    import psutil
    import os
    
    num_tasks = 10
    process = psutil.Process(os.getpid())
    
    # Get initial memory
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Execute multiple tasks
    for i in range(num_tasks):
        task_context = create_task_context(temp_workspace, f"mem-test-{i}")
        mock_simple_implementation(runner_orchestrator)
        
        result = runner_orchestrator.run(task_context)
        assert result.success
        
        # Reset state
        runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    # Get final memory
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    memory_per_task = memory_increase / num_tasks
    
    print(f"\nMemory usage for {num_tasks} tasks:")
    print(f"  Initial: {initial_memory:.2f} MB")
    print(f"  Final: {final_memory:.2f} MB")
    print(f"  Total increase: {memory_increase:.2f} MB")
    print(f"  Per task: {memory_per_task:.2f} MB")
    
    # Memory per task should be reasonable (< 10 MB)
    assert memory_per_task < 10.0


# ============================================================================
# Throughput Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_task_throughput(runner_orchestrator, temp_workspace):
    """Test task execution throughput."""
    num_tasks = 10
    
    # Execute tasks and measure time
    start_time = time.time()
    
    for i in range(num_tasks):
        task_context = create_task_context(temp_workspace, f"throughput-test-{i}")
        mock_simple_implementation(runner_orchestrator)
        
        result = runner_orchestrator.run(task_context)
        assert result.success
        
        # Reset state
        runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    total_time = time.time() - start_time
    
    # Calculate throughput
    throughput = num_tasks / total_time  # tasks per second
    avg_time_per_task = total_time / num_tasks
    
    print(f"\nTask throughput:")
    print(f"  Total tasks: {num_tasks}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Throughput: {throughput:.2f} tasks/second")
    print(f"  Average time per task: {avg_time_per_task:.2f}s")
    
    # Should be able to process at least 0.1 tasks per second
    assert throughput > 0.1


# ============================================================================
# Scalability Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_execution_time_scaling(runner_orchestrator, temp_workspace):
    """Test how execution time scales with task complexity."""
    # Test with different file counts
    file_counts = [1, 5, 10]
    execution_times = []
    
    for file_count in file_counts:
        task_context = create_task_context(
            temp_workspace,
            f"scale-test-{file_count}"
        )
        
        # Mock implementation with multiple files
        def mock_execute(task_context, workspace):
            files = []
            for i in range(file_count):
                test_file = workspace.path / f"test_{i}.py"
                test_file.write_text(f"print('test {i}')")
                files.append(f"test_{i}.py")
            
            return ImplementationResult(
                success=True,
                diff=f"+ {file_count} files",
                files_changed=files,
                duration_seconds=0.1 * file_count,
            )
        
        runner_orchestrator.task_executor.execute = mock_execute
        
        # Measure execution time
        start_time = time.time()
        result = runner_orchestrator.run(task_context)
        execution_time = time.time() - start_time
        
        assert result.success
        execution_times.append(execution_time)
        
        # Reset state
        runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    print(f"\nExecution time scaling:")
    for file_count, exec_time in zip(file_counts, execution_times):
        print(f"  {file_count} files: {exec_time:.2f}s")
    
    # Execution time should scale reasonably (not exponentially)
    # Time for 10 files should be less than 10x time for 1 file
    assert execution_times[2] < execution_times[0] * 10


# ============================================================================
# Stress Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_rapid_task_execution(runner_orchestrator, temp_workspace):
    """Test rapid execution of many tasks."""
    num_tasks = 20
    failures = 0
    
    start_time = time.time()
    
    for i in range(num_tasks):
        task_context = create_task_context(temp_workspace, f"rapid-test-{i}")
        mock_simple_implementation(runner_orchestrator)
        
        try:
            result = runner_orchestrator.run(task_context)
            if not result.success:
                failures += 1
        except Exception as e:
            failures += 1
            print(f"Task {i} failed: {e}")
        
        # Reset state
        runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    total_time = time.time() - start_time
    success_rate = ((num_tasks - failures) / num_tasks) * 100
    
    print(f"\nRapid task execution:")
    print(f"  Total tasks: {num_tasks}")
    print(f"  Failures: {failures}")
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Total time: {total_time:.2f}s")
    
    # Should have high success rate (> 90%)
    assert success_rate > 90.0


# ============================================================================
# Comparison Tests
# ============================================================================

@pytest.mark.performance
def test_performance_with_vs_without_tests(runner_orchestrator, temp_workspace):
    """Compare performance with and without test execution."""
    # Test without tests
    task_context_no_tests = create_task_context(temp_workspace, "no-tests")
    task_context_no_tests.test_commands = None
    mock_simple_implementation(runner_orchestrator)
    
    start_time = time.time()
    result_no_tests = runner_orchestrator.run(task_context_no_tests)
    time_no_tests = time.time() - start_time
    
    assert result_no_tests.success
    
    # Reset
    runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    # Test with tests
    task_context_with_tests = create_task_context(temp_workspace, "with-tests")
    task_context_with_tests.test_commands = ["echo 'test'"]
    mock_simple_implementation(runner_orchestrator)
    
    start_time = time.time()
    result_with_tests = runner_orchestrator.run(task_context_with_tests)
    time_with_tests = time.time() - start_time
    
    assert result_with_tests.success
    
    print(f"\nPerformance comparison:")
    print(f"  Without tests: {time_no_tests:.2f}s")
    print(f"  With tests: {time_with_tests:.2f}s")
    print(f"  Difference: {time_with_tests - time_no_tests:.2f}s")
    
    # With tests should take longer but not excessively
    assert time_with_tests > time_no_tests
    assert time_with_tests < time_no_tests * 3  # Less than 3x


@pytest.mark.performance
def test_performance_with_artifacts(runner_orchestrator, temp_workspace):
    """Test performance impact of artifact upload."""
    task_context = create_task_context(temp_workspace)
    mock_simple_implementation(runner_orchestrator)
    
    # Execute task
    start_time = time.time()
    result = runner_orchestrator.run(task_context)
    total_time = time.time() - start_time
    
    assert result.success
    
    # Check artifact upload time from result
    if result.artifacts:
        print(f"\nPerformance with artifacts:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Artifacts uploaded: {len(result.artifacts)}")
        print(f"  Total artifact size: {sum(a.size_bytes for a in result.artifacts)} bytes")


# ============================================================================
# Benchmark Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.benchmark
def test_baseline_performance_benchmark(runner_orchestrator, temp_workspace):
    """Establish baseline performance benchmark."""
    task_context = create_task_context(temp_workspace, "benchmark")
    mock_simple_implementation(runner_orchestrator)
    
    # Run multiple times to get average
    num_runs = 5
    execution_times = []
    
    for i in range(num_runs):
        start_time = time.time()
        result = runner_orchestrator.run(task_context)
        execution_time = time.time() - start_time
        
        assert result.success
        execution_times.append(execution_time)
        
        # Reset state
        runner_orchestrator.state = runner_orchestrator.state.__class__.IDLE
    
    # Calculate statistics
    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)
    
    print(f"\nBaseline performance benchmark ({num_runs} runs):")
    print(f"  Average: {avg_time:.2f}s")
    print(f"  Min: {min_time:.2f}s")
    print(f"  Max: {max_time:.2f}s")
    print(f"  Std dev: {(max_time - min_time):.2f}s")
    
    # Store benchmark for comparison
    # In a real scenario, this would be saved to a file
    benchmark = {
        "average": avg_time,
        "min": min_time,
        "max": max_time,
    }
    
    # Verify reasonable performance
    assert avg_time < 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])

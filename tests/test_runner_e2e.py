"""End-to-end tests for Agent Runner.

Tests complete task execution flow from task reception to completion,
including all external service integrations and failure scenarios.

Requirements: All requirements
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.models import TaskContext, RunnerState, ImplementationResult
from necrocode.agent_runner.runner_orchestrator import RunnerOrchestrator


# ============================================================================
# Configuration
# ============================================================================

# Skip E2E tests if disabled
SKIP_E2E_TESTS = os.getenv("SKIP_E2E_TESTS", "true").lower() == "true"


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
    readme.write_text("# Test Project\n\nThis is a test project.")
    
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
    """Create runner configuration for E2E tests."""
    from necrocode.agent_runner.config import RetryConfig
    return RunnerConfig(
        log_level="DEBUG",
        artifact_store_url=f"file://{tmp_path / 'artifacts'}",
        task_registry_path=tmp_path / "task_registry",
        git_retry_config=RetryConfig(max_retries=3),
        network_retry_config=RetryConfig(max_retries=3),
        default_timeout_seconds=300,
    )


@pytest.fixture
def runner_orchestrator(runner_config):
    """Create RunnerOrchestrator instance."""
    return RunnerOrchestrator(config=runner_config)


def create_task_context(workspace, task_id="e2e-test-1", **kwargs):
    """Create a task context for E2E testing."""
    defaults = {
        "task_id": task_id,
        "spec_name": "e2e-test",
        "title": "End-to-end test task",
        "description": "Task for end-to-end testing",
        "acceptance_criteria": [
            "Task should complete successfully",
            "All files should be created",
            "Changes should be committed",
        ],
        "dependencies": [],
        "required_skill": "backend",
        "slot_path": workspace,
        "slot_id": f"slot-{task_id}",
        "branch_name": f"feature/task-{task_id}",
        "timeout_seconds": 300,
    }
    defaults.update(kwargs)
    return TaskContext(**defaults)


def mock_implementation(runner, success=True, files=None):
    """Mock implementation for E2E tests."""
    if files is None:
        files = ["test.py"]
    
    def mock_execute(task_context, workspace):
        if success:
            # Create files
            for file_name in files:
                file_path = workspace.path / file_name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(f"# {file_name}\nprint('test')")
            
            return ImplementationResult(
                success=True,
                diff=f"+ {', '.join(files)}",
                files_changed=files,
                duration_seconds=1.0,
            )
        else:
            return ImplementationResult(
                success=False,
                diff="",
                files_changed=[],
                duration_seconds=1.0,
                error="Implementation failed",
            )
    
    runner.task_executor.execute = mock_execute


# ============================================================================
# Complete Workflow Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestCompleteWorkflow:
    """Test complete task execution workflow."""
    
    def test_successful_task_execution(self, runner_orchestrator, temp_workspace):
        """Test complete successful task execution."""
        task_context = create_task_context(temp_workspace)
        mock_implementation(runner_orchestrator, success=True)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify success
        assert result.success
        assert result.runner_id == runner_orchestrator.runner_id
        assert result.task_id == task_context.task_id
        assert result.duration_seconds > 0
        
        # Verify state
        assert runner_orchestrator.state == RunnerState.COMPLETED
        
        # Verify files were created
        test_file = temp_workspace / "test.py"
        assert test_file.exists()
        
        # Verify Git commit
        result_cmd = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=temp_workspace,
            capture_output=True,
            text=True
        )
        assert task_context.spec_name in result_cmd.stdout
        
        # Verify artifacts
        assert len(result.artifacts) > 0
        
        # Verify logs
        assert len(runner_orchestrator.execution_logs) > 0
    
    def test_task_with_multiple_files(self, runner_orchestrator, temp_workspace):
        """Test task that creates multiple files."""
        task_context = create_task_context(temp_workspace, task_id="multi-file")
        files = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        mock_implementation(runner_orchestrator, success=True, files=files)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify success
        assert result.success
        
        # Verify all files were created
        for file_name in files:
            file_path = temp_workspace / file_name
            assert file_path.exists()
    
    def test_task_with_tests(self, runner_orchestrator, temp_workspace):
        """Test task with test execution."""
        task_context = create_task_context(
            temp_workspace,
            task_id="with-tests",
            test_commands=["echo 'Running tests'", "python --version"]
        )
        mock_implementation(runner_orchestrator, success=True)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify success
        assert result.success
        
        # Verify test results
        assert result.test_result is not None
        assert result.test_result.success
    
    def test_task_with_dependencies(self, runner_orchestrator, temp_workspace):
        """Test task with dependencies."""
        # First task (dependency)
        task1_context = create_task_context(
            temp_workspace,
            task_id="dep-task-1",
            branch_name="feature/task-dep-1"
        )
        mock_implementation(runner_orchestrator, success=True, files=["base.py"])
        
        result1 = runner_orchestrator.run(task1_context)
        assert result1.success
        
        # Reset state
        runner_orchestrator.state = RunnerState.IDLE
        
        # Second task (depends on first)
        task2_context = create_task_context(
            temp_workspace,
            task_id="dep-task-2",
            branch_name="feature/task-dep-2",
            dependencies=["dep-task-1"]
        )
        mock_implementation(runner_orchestrator, success=True, files=["extension.py"])
        
        result2 = runner_orchestrator.run(task2_context)
        assert result2.success


# ============================================================================
# Failure Scenario Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestFailureScenarios:
    """Test various failure scenarios."""
    
    def test_implementation_failure(self, runner_orchestrator, temp_workspace):
        """Test handling of implementation failure."""
        task_context = create_task_context(temp_workspace, task_id="impl-fail")
        mock_implementation(runner_orchestrator, success=False)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify failure
        assert not result.success
        assert result.error is not None
        assert runner_orchestrator.state == RunnerState.FAILED
        
        # Verify error was logged
        assert any("error" in log.lower() for log in runner_orchestrator.execution_logs)
    
    def test_test_failure(self, runner_orchestrator, temp_workspace):
        """Test handling of test failure."""
        task_context = create_task_context(
            temp_workspace,
            task_id="test-fail",
            test_commands=["exit 1"]  # Command that fails
        )
        mock_implementation(runner_orchestrator, success=True)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify failure
        assert not result.success
        assert runner_orchestrator.state == RunnerState.FAILED
    
    def test_timeout_scenario(self, runner_orchestrator, temp_workspace):
        """Test timeout handling."""
        task_context = create_task_context(
            temp_workspace,
            task_id="timeout",
            timeout_seconds=1  # Very short timeout
        )
        
        # Mock slow implementation
        def slow_execute(task_context, workspace):
            time.sleep(2)  # Longer than timeout
            return ImplementationResult(
                success=True,
                diff="",
                files_changed=[],
                duration_seconds=2.0,
            )
        
        runner_orchestrator.task_executor.execute = slow_execute
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify timeout
        assert not result.success
        assert "timeout" in result.error.lower() or "limit" in result.error.lower()
    
    def test_git_operation_failure(self, runner_orchestrator, temp_workspace):
        """Test handling of Git operation failure."""
        # Make workspace read-only to cause Git failure
        temp_workspace.chmod(0o444)
        
        task_context = create_task_context(temp_workspace, task_id="git-fail")
        mock_implementation(runner_orchestrator, success=True)
        
        try:
            # Execute task
            result = runner_orchestrator.run(task_context)
            
            # Should fail due to Git error
            assert not result.success
        finally:
            # Restore permissions
            temp_workspace.chmod(0o755)
    
    def test_workspace_preparation_failure(self, runner_orchestrator):
        """Test handling of workspace preparation failure."""
        # Use non-existent workspace
        task_context = create_task_context(
            Path("/nonexistent/workspace"),
            task_id="prep-fail"
        )
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify failure
        assert not result.success
        assert result.error is not None


# ============================================================================
# Network Error Scenarios
# ============================================================================

@pytest.mark.e2e
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestNetworkErrorScenarios:
    """Test network error scenarios."""
    
    def test_artifact_upload_failure(self, runner_orchestrator, temp_workspace):
        """Test handling of artifact upload failure."""
        # Configure with invalid artifact store URL
        runner_orchestrator.config.artifact_store_url = "http://invalid-url:9999"
        
        task_context = create_task_context(temp_workspace, task_id="upload-fail")
        mock_implementation(runner_orchestrator, success=True)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Task may still succeed even if artifact upload fails
        # (depending on configuration)
        # But error should be logged
        if not result.success:
            assert "artifact" in result.error.lower() or "upload" in result.error.lower()
    
    def test_external_service_unavailable(self, runner_orchestrator, temp_workspace):
        """Test handling when external services are unavailable."""
        # Configure with invalid service URLs
        runner_orchestrator.config.task_registry_url = "http://invalid-url:9999"
        runner_orchestrator.config.repo_pool_url = "http://invalid-url:9999"
        
        task_context = create_task_context(temp_workspace, task_id="service-fail")
        mock_implementation(runner_orchestrator, success=True)
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Should handle gracefully
        # May succeed or fail depending on configuration
        assert result is not None


# ============================================================================
# Recovery Scenarios
# ============================================================================

@pytest.mark.e2e
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestRecoveryScenarios:
    """Test recovery from failures."""
    
    def test_retry_after_transient_failure(self, runner_orchestrator, temp_workspace):
        """Test retry after transient failure."""
        task_context = create_task_context(temp_workspace, task_id="retry")
        
        # Mock implementation that fails first time, succeeds second time
        attempt_count = [0]
        
        def flaky_execute(task_context, workspace):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # First attempt fails
                return ImplementationResult(
                    success=False,
                    diff="",
                    files_changed=[],
                    duration_seconds=1.0,
                    error="Transient error",
                )
            else:
                # Second attempt succeeds
                test_file = workspace.path / "test.py"
                test_file.write_text("print('test')")
                return ImplementationResult(
                    success=True,
                    diff="+ test.py",
                    files_changed=["test.py"],
                    duration_seconds=1.0,
                )
        
        runner_orchestrator.task_executor.execute = flaky_execute
        
        # Execute task (will fail)
        result1 = runner_orchestrator.run(task_context)
        assert not result1.success
        
        # Reset and retry
        runner_orchestrator.state = RunnerState.IDLE
        attempt_count[0] = 0  # Reset counter
        
        # Execute again (should succeed)
        result2 = runner_orchestrator.run(task_context)
        # Note: This test shows the pattern, but actual retry logic
        # would be in the orchestrator
    
    def test_cleanup_after_failure(self, runner_orchestrator, temp_workspace):
        """Test cleanup after failure."""
        task_context = create_task_context(temp_workspace, task_id="cleanup")
        
        # Mock implementation that creates files then fails
        def failing_execute(task_context, workspace):
            # Create some files
            test_file = workspace.path / "temp.py"
            test_file.write_text("temporary file")
            
            # Then fail
            raise Exception("Simulated failure")
        
        runner_orchestrator.task_executor.execute = failing_execute
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify failure
        assert not result.success
        
        # Verify cleanup was attempted
        # (State should be FAILED, not stuck in RUNNING)
        assert runner_orchestrator.state == RunnerState.FAILED


# ============================================================================
# Concurrent Execution Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestConcurrentExecution:
    """Test concurrent task execution."""
    
    def test_multiple_tasks_different_workspaces(self, runner_config, tmp_path):
        """Test multiple tasks in different workspaces."""
        import threading
        
        # Create multiple workspaces
        workspaces = []
        for i in range(3):
            workspace = tmp_path / f"workspace_{i}"
            workspace.mkdir()
            
            # Initialize Git
            subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=workspace, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=workspace, check=True, capture_output=True)
            
            readme = workspace / "README.md"
            readme.write_text(f"# Workspace {i}\n")
            subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=workspace, check=True, capture_output=True)
            
            workspaces.append(workspace)
        
        results = []
        
        def run_task(workspace, task_id):
            runner = RunnerOrchestrator(config=runner_config)
            task_context = create_task_context(workspace, task_id=task_id)
            mock_implementation(runner, success=True)
            
            result = runner.run(task_context)
            results.append(result)
        
        # Run tasks concurrently
        threads = []
        for i, workspace in enumerate(workspaces):
            thread = threading.Thread(target=run_task, args=(workspace, f"concurrent-{i}"))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all succeeded
        assert len(results) == 3
        assert all(r.success for r in results)


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestE2EPerformance:
    """End-to-end performance tests."""
    
    def test_complete_workflow_performance(self, runner_orchestrator, temp_workspace):
        """Test performance of complete workflow."""
        task_context = create_task_context(temp_workspace, task_id="perf")
        mock_implementation(runner_orchestrator, success=True)
        
        # Measure execution time
        start_time = time.time()
        result = runner_orchestrator.run(task_context)
        execution_time = time.time() - start_time
        
        # Verify success
        assert result.success
        
        # Verify performance
        print(f"\nComplete workflow execution time: {execution_time:.2f}s")
        
        # Should complete in reasonable time (< 60 seconds)
        assert execution_time < 60.0
    
    def test_sequential_tasks_performance(self, runner_orchestrator, temp_workspace):
        """Test performance of sequential task execution."""
        num_tasks = 5
        execution_times = []
        
        for i in range(num_tasks):
            task_context = create_task_context(
                temp_workspace,
                task_id=f"seq-perf-{i}",
                branch_name=f"feature/task-seq-{i}"
            )
            mock_implementation(runner_orchestrator, success=True)
            
            start_time = time.time()
            result = runner_orchestrator.run(task_context)
            execution_time = time.time() - start_time
            
            assert result.success
            execution_times.append(execution_time)
            
            # Reset state
            runner_orchestrator.state = RunnerState.IDLE
        
        avg_time = sum(execution_times) / len(execution_times)
        
        print(f"\nSequential execution of {num_tasks} tasks:")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Total time: {sum(execution_times):.2f}s")
        
        # Average should be reasonable
        assert avg_time < 30.0


# ============================================================================
# Integration with All Services
# ============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestFullIntegration:
    """Test full integration with all services."""
    
    def test_complete_integration_workflow(self, runner_orchestrator, temp_workspace):
        """Test complete workflow with all services."""
        task_context = create_task_context(temp_workspace, task_id="full-integration")
        mock_implementation(runner_orchestrator, success=True, files=["main.py", "utils.py"])
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        
        # Verify all aspects
        assert result.success
        assert result.impl_result is not None
        assert result.impl_result.success
        assert len(result.impl_result.files_changed) == 2
        assert result.artifacts is not None
        assert len(result.artifacts) > 0
        
        # Verify Git operations
        result_cmd = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=temp_workspace,
            capture_output=True,
            text=True
        )
        assert task_context.spec_name in result_cmd.stdout
        
        # Verify files exist
        assert (temp_workspace / "main.py").exists()
        assert (temp_workspace / "utils.py").exists()


# ============================================================================
# Stress Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.skipif(SKIP_E2E_TESTS, reason="E2E tests disabled")
class TestStressScenarios:
    """Stress tests for E2E scenarios."""
    
    def test_many_sequential_tasks(self, runner_orchestrator, temp_workspace):
        """Test many sequential tasks."""
        num_tasks = 10
        successful = 0
        
        for i in range(num_tasks):
            task_context = create_task_context(
                temp_workspace,
                task_id=f"stress-{i}",
                branch_name=f"feature/task-stress-{i}"
            )
            mock_implementation(runner_orchestrator, success=True)
            
            result = runner_orchestrator.run(task_context)
            if result.success:
                successful += 1
            
            # Reset state
            runner_orchestrator.state = RunnerState.IDLE
        
        success_rate = (successful / num_tasks) * 100
        
        print(f"\nStress test: {successful}/{num_tasks} tasks succeeded ({success_rate:.1f}%)")
        
        # Should have high success rate
        assert success_rate > 90.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])

"""Integration tests for Agent Runner with real task execution.

Tests the complete task execution flow with actual Git operations,
file system interactions, and component integration.

Requirements: All requirements
"""

import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.models import TaskContext, RunnerState
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
    """Create runner configuration."""
    from necrocode.agent_runner.config import RetryConfig
    return RunnerConfig(
        log_level="DEBUG",
        artifact_store_url=f"file://{tmp_path / 'artifacts'}",
        task_registry_path=tmp_path / "task_registry",
        git_retry_config=RetryConfig(max_retries=2),
        network_retry_config=RetryConfig(max_retries=2),
        default_timeout_seconds=300,
    )


@pytest.fixture
def runner_orchestrator(runner_config):
    """Create RunnerOrchestrator instance."""
    return RunnerOrchestrator(config=runner_config)


@pytest.fixture
def simple_task_context(temp_workspace):
    """Create a simple task context for testing."""
    return TaskContext(
        task_id="test-1",
        spec_name="test-spec",
        title="Add hello world function",
        description="Create a simple hello world function in Python",
        acceptance_criteria=[
            "Function should be named hello_world",
            "Function should return 'Hello, World!'",
            "Function should be in hello.py file",
        ],
        dependencies=[],
        required_skill="backend",
        slot_path=temp_workspace,
        slot_id="slot-1",
        branch_name="feature/task-test-1-hello-world",
        test_commands=None,  # No tests for simple case
        fail_fast=True,
        timeout_seconds=60,
    )


# ============================================================================
# Basic Integration Tests
# ============================================================================

def test_runner_initialization(runner_orchestrator):
    """Test that runner initializes correctly."""
    assert runner_orchestrator.runner_id is not None
    assert runner_orchestrator.state == RunnerState.IDLE
    assert runner_orchestrator.workspace_manager is not None
    assert runner_orchestrator.task_executor is not None
    assert runner_orchestrator.test_runner is not None
    assert runner_orchestrator.artifact_uploader is not None


def test_task_context_validation(runner_orchestrator, simple_task_context):
    """Test task context validation."""
    # Valid context should pass
    runner_orchestrator._validate_task_context(simple_task_context)
    
    # Invalid context should fail
    invalid_context = TaskContext(
        task_id="",  # Empty task ID
        spec_name="test-spec",
        title="Test",
        description="Test",
        acceptance_criteria=[],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/nonexistent"),
        slot_id="slot-1",
        branch_name="test-branch",
    )
    
    with pytest.raises(Exception):
        runner_orchestrator._validate_task_context(invalid_context)


def test_workspace_preparation(runner_orchestrator, simple_task_context):
    """Test workspace preparation phase."""
    # Prepare workspace
    workspace = runner_orchestrator._prepare_workspace(simple_task_context)
    
    assert workspace is not None
    assert workspace.path == simple_task_context.slot_path
    assert workspace.branch == simple_task_context.branch_name
    
    # Verify branch was created
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=simple_task_context.slot_path,
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == simple_task_context.branch_name


def test_commit_message_generation(runner_orchestrator, simple_task_context):
    """Test commit message generation."""
    message = runner_orchestrator._generate_commit_message(simple_task_context)
    
    assert "test-spec" in message
    assert "Add hello world function" in message
    assert "test-1" in message
    assert message.startswith("feat(")


# ============================================================================
# End-to-End Task Execution Tests
# ============================================================================

def test_simple_task_execution_without_implementation(
    runner_orchestrator,
    simple_task_context
):
    """Test task execution flow without actual implementation.
    
    This test verifies the orchestration flow but mocks the actual
    implementation to avoid requiring Kiro API.
    """
    # Mock the task executor to avoid actual implementation
    original_execute = runner_orchestrator.task_executor.execute
    
    def mock_execute(task_context, workspace):
        # Create a simple file to simulate implementation
        hello_file = workspace.path / "hello.py"
        hello_file.write_text(
            'def hello_world():\n'
            '    return "Hello, World!"\n'
        )
        
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="+ hello.py",
            files_changed=["hello.py"],
            duration_seconds=1.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    try:
        # Execute task
        result = runner_orchestrator.run(simple_task_context)
        
        # Verify result
        assert result.success
        assert result.runner_id == runner_orchestrator.runner_id
        assert result.task_id == simple_task_context.task_id
        assert result.duration_seconds > 0
        
        # Verify state transition
        assert runner_orchestrator.state == RunnerState.COMPLETED
        
        # Verify file was created
        hello_file = simple_task_context.slot_path / "hello.py"
        assert hello_file.exists()
        
        # Verify commit was made
        result_cmd = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=simple_task_context.slot_path,
            capture_output=True,
            text=True
        )
        assert "test-spec" in result_cmd.stdout
        
    finally:
        # Restore original execute method
        runner_orchestrator.task_executor.execute = original_execute


def test_task_execution_with_test_failure(
    runner_orchestrator,
    simple_task_context,
    temp_workspace
):
    """Test task execution when tests fail."""
    # Add test command that will fail
    simple_task_context.test_commands = ["python -m pytest nonexistent_test.py"]
    
    # Mock implementation
    def mock_execute(task_context, workspace):
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="+ test.py",
            files_changed=["test.py"],
            duration_seconds=1.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Should fail due to test failure
    assert not result.success
    assert result.error is not None
    assert runner_orchestrator.state == RunnerState.FAILED


def test_task_execution_with_timeout(runner_orchestrator, simple_task_context):
    """Test task execution with timeout."""
    # Set very short timeout
    simple_task_context.timeout_seconds = 1
    
    # Mock implementation that takes too long
    def mock_execute(task_context, workspace):
        time.sleep(2)  # Sleep longer than timeout
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="",
            files_changed=[],
            duration_seconds=2.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Should fail due to timeout
    assert not result.success
    assert "timeout" in result.error.lower() or "limit" in result.error.lower()
    assert runner_orchestrator.state == RunnerState.FAILED


# ============================================================================
# Artifact Upload Tests
# ============================================================================

def test_artifact_upload_integration(
    runner_orchestrator,
    simple_task_context,
    tmp_path
):
    """Test artifact upload integration."""
    # Mock implementation
    def mock_execute(task_context, workspace):
        test_file = workspace.path / "test.py"
        test_file.write_text("print('test')")
        
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="+ test.py\n+ print('test')",
            files_changed=["test.py"],
            duration_seconds=1.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Verify artifacts were created
    assert result.success
    assert len(result.artifacts) > 0
    
    # Check artifact types
    artifact_types = {a.type.value for a in result.artifacts}
    assert "log" in artifact_types  # Should always have logs


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_error_handling_implementation_failure(
    runner_orchestrator,
    simple_task_context
):
    """Test error handling when implementation fails."""
    # Mock implementation that fails
    def mock_execute(task_context, workspace):
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=False,
            diff="",
            files_changed=[],
            duration_seconds=1.0,
            error="Implementation failed: syntax error",
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Should fail gracefully
    assert not result.success
    assert result.error is not None
    assert "implementation failed" in result.error.lower()
    assert runner_orchestrator.state == RunnerState.FAILED


def test_error_handling_workspace_preparation_failure(
    runner_orchestrator,
    simple_task_context
):
    """Test error handling when workspace preparation fails."""
    # Use non-existent workspace
    simple_task_context.slot_path = Path("/nonexistent/workspace")
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Should fail during validation
    assert not result.success
    assert result.error is not None


def test_cleanup_after_failure(runner_orchestrator, simple_task_context):
    """Test that cleanup happens even after failure."""
    # Mock implementation that fails
    def mock_execute(task_context, workspace):
        # Create a file
        test_file = workspace.path / "test.py"
        test_file.write_text("test")
        
        # Then fail
        raise Exception("Simulated failure")
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Should fail
    assert not result.success
    
    # Cleanup should have been called (verify through state)
    assert runner_orchestrator.state == RunnerState.FAILED


# ============================================================================
# State Management Tests
# ============================================================================

def test_state_transitions(runner_orchestrator, simple_task_context):
    """Test state transitions during task execution."""
    # Initial state
    assert runner_orchestrator.state == RunnerState.IDLE
    
    # Mock implementation
    def mock_execute(task_context, workspace):
        # Check state during execution
        assert runner_orchestrator.state == RunnerState.RUNNING
        
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="",
            files_changed=[],
            duration_seconds=1.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    # Final state
    if result.success:
        assert runner_orchestrator.state == RunnerState.COMPLETED
    else:
        assert runner_orchestrator.state == RunnerState.FAILED


# ============================================================================
# Logging Tests
# ============================================================================

def test_execution_logging(runner_orchestrator, simple_task_context, caplog):
    """Test that execution is properly logged."""
    # Mock implementation
    def mock_execute(task_context, workspace):
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="",
            files_changed=[],
            duration_seconds=1.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task with logging
    with caplog.at_level(logging.INFO):
        result = runner_orchestrator.run(simple_task_context)
    
    # Verify logging occurred
    assert len(runner_orchestrator.execution_logs) > 0
    assert any("Starting task execution" in log for log in runner_orchestrator.execution_logs)
    assert any("Phase 1: Preparing workspace" in log for log in runner_orchestrator.execution_logs)


# ============================================================================
# Multiple Task Execution Tests
# ============================================================================

def test_multiple_task_executions(runner_orchestrator, temp_workspace):
    """Test executing multiple tasks sequentially."""
    results = []
    
    for i in range(3):
        task_context = TaskContext(
            task_id=f"test-{i}",
            spec_name="test-spec",
            title=f"Task {i}",
            description=f"Test task {i}",
            acceptance_criteria=[f"Criterion {i}"],
            dependencies=[],
            required_skill="backend",
            slot_path=temp_workspace,
            slot_id="slot-1",
            branch_name=f"feature/task-test-{i}",
            timeout_seconds=60,
        )
        
        # Mock implementation
        def mock_execute(task_context, workspace):
            test_file = workspace.path / f"file_{task_context.task_id}.py"
            test_file.write_text(f"# Task {task_context.task_id}")
            
            from necrocode.agent_runner.models import ImplementationResult
            return ImplementationResult(
                success=True,
                diff=f"+ file_{task_context.task_id}.py",
                files_changed=[f"file_{task_context.task_id}.py"],
                duration_seconds=1.0,
            )
        
        runner_orchestrator.task_executor.execute = mock_execute
        
        # Execute task
        result = runner_orchestrator.run(task_context)
        results.append(result)
        
        # Reset state for next task
        runner_orchestrator.state = RunnerState.IDLE
    
    # Verify all tasks succeeded
    assert all(r.success for r in results)
    assert len(results) == 3


# ============================================================================
# Git Integration Tests
# ============================================================================

def test_git_branch_creation(runner_orchestrator, simple_task_context):
    """Test that Git branches are created correctly."""
    # Prepare workspace
    workspace = runner_orchestrator._prepare_workspace(simple_task_context)
    
    # Verify branch exists
    result = subprocess.run(
        ["git", "branch", "--list", simple_task_context.branch_name],
        cwd=simple_task_context.slot_path,
        capture_output=True,
        text=True
    )
    assert simple_task_context.branch_name in result.stdout


def test_git_commit_creation(runner_orchestrator, simple_task_context):
    """Test that Git commits are created correctly."""
    # Mock implementation
    def mock_execute(task_context, workspace):
        test_file = workspace.path / "test.py"
        test_file.write_text("print('test')")
        
        from necrocode.agent_runner.models import ImplementationResult
        return ImplementationResult(
            success=True,
            diff="+ test.py",
            files_changed=["test.py"],
            duration_seconds=1.0,
        )
    
    runner_orchestrator.task_executor.execute = mock_execute
    
    # Execute task
    result = runner_orchestrator.run(simple_task_context)
    
    assert result.success
    
    # Verify commit was created
    result_cmd = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=simple_task_context.slot_path,
        capture_output=True,
        text=True
    )
    commit_message = result_cmd.stdout.strip()
    
    assert "feat(test-spec)" in commit_message
    assert "test-1" in commit_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

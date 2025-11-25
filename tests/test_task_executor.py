"""
Tests for TaskExecutor.

This module tests the task execution functionality including
Kiro integration, prompt building, and implementation verification.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from necrocode.agent_runner.task_executor import TaskExecutor, KiroClient
from necrocode.agent_runner.models import TaskContext, Workspace, ImplementationResult
from necrocode.agent_runner.exceptions import ImplementationError


@pytest.fixture
def task_context():
    """Create a sample task context for testing."""
    return TaskContext(
        task_id="1.1",
        spec_name="test-spec",
        title="Implement user authentication",
        description="Add JWT-based authentication to the API",
        acceptance_criteria=[
            "User can register with email and password",
            "User can login and receive JWT token",
            "Protected endpoints validate JWT token",
        ],
        dependencies=["1.0"],
        required_skill="backend",
        slot_path=Path("/tmp/test-workspace"),
        slot_id="slot-1",
        branch_name="feature/task-1.1-auth",
        complexity="medium",
        require_review=False,
    )


@pytest.fixture
def workspace(tmp_path):
    """Create a sample workspace for testing."""
    return Workspace(
        path=tmp_path,
        branch_name="feature/task-1.1-auth",
        base_branch="main",
    )


@pytest.fixture
def mock_kiro_client():
    """Create a mock Kiro client."""
    client = Mock(spec=KiroClient)
    client.implement.return_value = {
        "files_changed": ["src/auth.py", "tests/test_auth.py"],
        "duration": 45.2,
        "notes": "Implemented JWT authentication with bcrypt password hashing",
    }
    return client


def test_task_executor_initialization():
    """Test TaskExecutor can be initialized."""
    executor = TaskExecutor()
    assert executor is not None
    assert executor.kiro_client is not None


def test_task_executor_with_custom_client():
    """Test TaskExecutor can be initialized with custom Kiro client."""
    custom_client = Mock(spec=KiroClient)
    executor = TaskExecutor(kiro_client=custom_client)
    assert executor.kiro_client is custom_client


def test_build_implementation_prompt(task_context):
    """Test implementation prompt building."""
    executor = TaskExecutor()
    prompt = executor._build_implementation_prompt(task_context)
    
    # Check that prompt contains key information
    assert task_context.title in prompt
    assert task_context.task_id in prompt
    assert task_context.description in prompt
    assert all(criterion in prompt for criterion in task_context.acceptance_criteria)
    assert task_context.required_skill in prompt
    assert task_context.complexity in prompt


def test_build_implementation_prompt_with_dependencies(task_context):
    """Test prompt building includes dependencies."""
    task_context.dependencies = ["1.0", "1.1"]
    executor = TaskExecutor()
    prompt = executor._build_implementation_prompt(task_context)
    
    assert "Dependencies" in prompt
    assert "Task 1.0" in prompt
    assert "Task 1.1" in prompt


def test_verify_implementation_success(task_context):
    """Test implementation verification with valid response."""
    executor = TaskExecutor()
    
    impl_response = {
        "files_changed": ["src/auth.py"],
        "notes": "Implementation complete",
    }
    
    result = executor._verify_implementation(impl_response, task_context)
    assert result is True


def test_verify_implementation_missing_files_changed(task_context):
    """Test verification fails when files_changed is missing."""
    executor = TaskExecutor()
    
    impl_response = {
        "notes": "Implementation complete",
    }
    
    result = executor._verify_implementation(impl_response, task_context)
    assert result is False


def test_verify_implementation_with_error(task_context):
    """Test verification fails when response contains error."""
    executor = TaskExecutor()
    
    impl_response = {
        "files_changed": ["src/auth.py"],
        "error": "Compilation failed",
    }
    
    result = executor._verify_implementation(impl_response, task_context)
    assert result is False


def test_execute_success(task_context, workspace, mock_kiro_client):
    """Test successful task execution."""
    executor = TaskExecutor(kiro_client=mock_kiro_client)
    
    # Mock git diff
    with patch.object(executor, '_get_workspace_diff', return_value="diff content"):
        result = executor.execute(task_context, workspace)
    
    assert result.success is True
    assert result.error is None
    assert len(result.files_changed) == 2
    assert result.duration_seconds > 0
    assert result.diff == "diff content"
    
    # Verify Kiro was called
    mock_kiro_client.implement.assert_called_once()


def test_execute_verification_failure(task_context, workspace, mock_kiro_client):
    """Test execution handles verification failure."""
    executor = TaskExecutor(kiro_client=mock_kiro_client)
    
    # Make verification fail
    with patch.object(executor, '_verify_implementation', return_value=False):
        result = executor.execute(task_context, workspace)
    
    assert result.success is False
    assert "verification failed" in result.error.lower()


def test_execute_kiro_failure(task_context, workspace, mock_kiro_client):
    """Test execution handles Kiro failure."""
    mock_kiro_client.implement.side_effect = ImplementationError("Kiro crashed")
    executor = TaskExecutor(kiro_client=mock_kiro_client)
    
    result = executor.execute(task_context, workspace)
    
    assert result.success is False
    assert "Kiro crashed" in result.error


def test_kiro_client_initialization():
    """Test KiroClient can be initialized."""
    client = KiroClient()
    assert client is not None


def test_kiro_client_with_workspace():
    """Test KiroClient can be initialized with workspace path."""
    workspace_path = Path("/tmp/test")
    client = KiroClient(workspace_path=workspace_path)
    assert client.workspace_path == workspace_path

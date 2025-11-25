"""
Tests for TaskExecutor.

This module tests the task execution functionality including
LLM integration, prompt building, and implementation verification.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from necrocode.agent_runner.task_executor import TaskExecutor
from necrocode.agent_runner.models import (
    TaskContext,
    Workspace,
    ImplementationResult,
    LLMConfig,
    LLMResponse,
    CodeChange,
)
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
def llm_config():
    """Create a sample LLM config for testing."""
    return LLMConfig(
        api_key="test-api-key",
        model="gpt-4",
        timeout_seconds=120,
    )


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    return LLMResponse(
        code_changes=[
            CodeChange(
                file_path="src/auth.py",
                operation="create",
                content="# Authentication module\n",
            ),
            CodeChange(
                file_path="tests/test_auth.py",
                operation="create",
                content="# Test authentication\n",
            ),
        ],
        explanation="Implemented JWT authentication with bcrypt password hashing",
        model="gpt-4",
        tokens_used=1500,
    )


def test_task_executor_initialization(llm_config):
    """Test TaskExecutor can be initialized."""
    executor = TaskExecutor(llm_config)
    assert executor is not None
    assert executor.llm_client is not None


def test_build_implementation_prompt(task_context, workspace, llm_config):
    """Test implementation prompt building."""
    executor = TaskExecutor(llm_config)
    prompt = executor._build_implementation_prompt(task_context, workspace)
    
    # Check that prompt contains key information
    assert task_context.title in prompt
    # Task ID might not be explicitly in prompt, but title and description are
    assert task_context.description in prompt
    assert all(criterion in prompt for criterion in task_context.acceptance_criteria)
    assert task_context.required_skill in prompt
    assert task_context.complexity in prompt
    assert "JSON" in prompt  # Should include JSON format instructions


def test_build_implementation_prompt_with_dependencies(task_context, workspace, llm_config):
    """Test prompt building includes dependencies."""
    task_context.dependencies = ["1.0", "1.1"]
    executor = TaskExecutor(llm_config)
    prompt = executor._build_implementation_prompt(task_context, workspace)
    
    assert "Dependencies" in prompt
    assert "Task 1.0" in prompt
    assert "Task 1.1" in prompt


def test_build_implementation_prompt_with_related_files(task_context, workspace, llm_config, tmp_path):
    """Test prompt building includes related files."""
    # Create a related file
    test_file = tmp_path / "config.py"
    test_file.write_text("# Configuration\nDEBUG = True")
    
    task_context.related_files = ["config.py"]
    workspace.path = tmp_path
    
    executor = TaskExecutor(llm_config)
    prompt = executor._build_implementation_prompt(task_context, workspace)
    
    assert "Related Files" in prompt
    assert "config.py" in prompt
    assert "DEBUG = True" in prompt


def test_apply_code_changes_create(workspace, llm_config):
    """Test applying code changes - create operation."""
    executor = TaskExecutor(llm_config)
    
    code_changes = [
        CodeChange(
            file_path="src/auth.py",
            operation="create",
            content="# Authentication module\n",
        ),
    ]
    
    files_changed = executor._apply_code_changes(workspace, code_changes)
    
    assert len(files_changed) == 1
    assert "src/auth.py" in files_changed
    assert (workspace.path / "src/auth.py").exists()
    assert (workspace.path / "src/auth.py").read_text() == "# Authentication module\n"


def test_apply_code_changes_modify(workspace, llm_config, tmp_path):
    """Test applying code changes - modify operation."""
    # Create an existing file
    test_file = tmp_path / "existing.py"
    test_file.write_text("# Original content")
    workspace.path = tmp_path
    
    executor = TaskExecutor(llm_config)
    
    code_changes = [
        CodeChange(
            file_path="existing.py",
            operation="modify",
            content="# Modified content\n",
        ),
    ]
    
    files_changed = executor._apply_code_changes(workspace, code_changes)
    
    assert len(files_changed) == 1
    assert "existing.py" in files_changed
    assert test_file.read_text() == "# Modified content\n"


def test_apply_code_changes_delete(workspace, llm_config, tmp_path):
    """Test applying code changes - delete operation."""
    # Create a file to delete
    test_file = tmp_path / "to_delete.py"
    test_file.write_text("# To be deleted")
    workspace.path = tmp_path
    
    executor = TaskExecutor(llm_config)
    
    code_changes = [
        CodeChange(
            file_path="to_delete.py",
            operation="delete",
            content="",
        ),
    ]
    
    files_changed = executor._apply_code_changes(workspace, code_changes)
    
    assert len(files_changed) == 1
    assert "to_delete.py" in files_changed
    assert not test_file.exists()


def test_apply_code_changes_invalid_operation(workspace, llm_config):
    """Test applying code changes with invalid operation."""
    executor = TaskExecutor(llm_config)
    
    code_changes = [
        CodeChange(
            file_path="test.py",
            operation="invalid",
            content="",
        ),
    ]
    
    with pytest.raises(ImplementationError, match="Unknown operation"):
        executor._apply_code_changes(workspace, code_changes)


def test_verify_implementation_success(workspace, llm_config):
    """Test implementation verification with valid files."""
    executor = TaskExecutor(llm_config)
    
    files_changed = ["src/auth.py", "tests/test_auth.py"]
    
    result = executor._verify_implementation(workspace, files_changed)
    assert result is True


def test_verify_implementation_no_files(workspace, llm_config):
    """Test verification with no files changed (warning but passes)."""
    executor = TaskExecutor(llm_config)
    
    files_changed = []
    
    result = executor._verify_implementation(workspace, files_changed)
    assert result is True  # Should pass with warning


def test_execute_success(task_context, workspace, llm_config, mock_llm_response):
    """Test successful task execution."""
    executor = TaskExecutor(llm_config)
    
    # Mock LLM client and git diff
    with patch.object(executor.llm_client, 'generate_code', return_value=mock_llm_response):
        with patch.object(executor, '_get_workspace_diff', return_value="diff content"):
            result = executor.execute(task_context, workspace)
    
    assert result.success is True
    assert result.error is None
    assert len(result.files_changed) == 2
    assert result.duration_seconds > 0
    assert result.diff == "diff content"
    assert result.llm_model == "gpt-4"
    assert result.tokens_used == 1500


def test_execute_verification_failure(task_context, workspace, llm_config, mock_llm_response):
    """Test execution handles verification failure."""
    executor = TaskExecutor(llm_config)
    
    # Mock LLM client
    with patch.object(executor.llm_client, 'generate_code', return_value=mock_llm_response):
        # Make verification fail
        with patch.object(executor, '_verify_implementation', return_value=False):
            result = executor.execute(task_context, workspace)
    
    assert result.success is False
    assert "verification failed" in result.error.lower()


def test_execute_llm_failure(task_context, workspace, llm_config):
    """Test execution handles LLM failure."""
    executor = TaskExecutor(llm_config)
    
    # Mock LLM client to raise error
    with patch.object(executor.llm_client, 'generate_code', side_effect=ImplementationError("LLM API error")):
        result = executor.execute(task_context, workspace)
    
    assert result.success is False
    assert "LLM API error" in result.error


def test_get_workspace_structure(workspace, llm_config, tmp_path):
    """Test workspace structure generation."""
    # Create some files and directories
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# Main")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("# Test")
    (tmp_path / "README.md").write_text("# README")
    
    workspace.path = tmp_path
    executor = TaskExecutor(llm_config)
    
    structure = executor._get_workspace_structure(workspace)
    
    assert "src" in structure
    assert "tests" in structure
    assert "README.md" in structure


def test_read_workspace_file(workspace, llm_config, tmp_path):
    """Test reading workspace file."""
    test_file = tmp_path / "config.py"
    test_file.write_text("# Configuration\nDEBUG = True")
    
    workspace.path = tmp_path
    executor = TaskExecutor(llm_config)
    
    content = executor._read_workspace_file(workspace, "config.py")
    
    assert "Configuration" in content
    assert "DEBUG = True" in content


def test_read_workspace_file_not_found(workspace, llm_config):
    """Test reading non-existent file raises error."""
    executor = TaskExecutor(llm_config)
    
    with pytest.raises(FileNotFoundError):
        executor._read_workspace_file(workspace, "nonexistent.py")

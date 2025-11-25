"""
Tests for Agent Runner WorkspaceManager.

This module tests the Git operations provided by WorkspaceManager,
including workspace preparation, commits, pushes with retry, and rollback.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from necrocode.agent_runner import (
    WorkspaceManager,
    Workspace,
    PushResult,
    RetryConfig,
    WorkspacePreparationError,
    PushError,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        yield workspace_path


@pytest.fixture
def workspace_manager():
    """Create a WorkspaceManager instance with default config."""
    return WorkspaceManager()


@pytest.fixture
def workspace_manager_with_retry():
    """Create a WorkspaceManager with custom retry config."""
    retry_config = RetryConfig(
        max_retries=2,
        initial_delay_seconds=0.1,
        max_delay_seconds=1.0,
        exponential_base=2.0
    )
    return WorkspaceManager(retry_config=retry_config)


class TestWorkspaceManager:
    """Test suite for WorkspaceManager."""
    
    def test_prepare_workspace_success(self, workspace_manager, temp_workspace):
        """Test successful workspace preparation."""
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            # Mock successful git commands
            mock_git.return_value = subprocess.CompletedProcess([], 0)
            
            workspace = workspace_manager.prepare_workspace(
                slot_path=temp_workspace,
                branch_name="feature/task-1-test",
                base_branch="main"
            )
            
            # Verify workspace object
            assert workspace.path == temp_workspace
            assert workspace.branch_name == "feature/task-1-test"
            assert workspace.base_branch == "main"
            
            # Verify git commands were called in correct order
            assert mock_git.call_count == 4
            mock_git.assert_any_call(
                ["checkout", "main"],
                cwd=temp_workspace,
                error_msg="Failed to checkout main"
            )
            mock_git.assert_any_call(
                ["fetch", "origin"],
                cwd=temp_workspace,
                error_msg="Failed to fetch from origin"
            )
            mock_git.assert_any_call(
                ["rebase", "origin/main"],
                cwd=temp_workspace,
                error_msg="Failed to rebase on origin/main"
            )
            mock_git.assert_any_call(
                ["checkout", "-b", "feature/task-1-test"],
                cwd=temp_workspace,
                error_msg="Failed to create branch feature/task-1-test"
            )
    
    def test_prepare_workspace_failure(self, workspace_manager, temp_workspace):
        """Test workspace preparation failure."""
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            # Mock git command failure
            mock_git.side_effect = subprocess.CalledProcessError(1, "git")
            
            with pytest.raises(WorkspacePreparationError):
                workspace_manager.prepare_workspace(
                    slot_path=temp_workspace,
                    branch_name="feature/task-1-test"
                )
    
    def test_commit_changes_success(self, workspace_manager, temp_workspace):
        """Test successful commit operation."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            # Mock git commands
            mock_result = MagicMock()
            mock_result.stdout = "abc123def456"
            mock_git.return_value = mock_result
            
            commit_hash = workspace_manager.commit_changes(
                workspace=workspace,
                commit_message="feat: implement feature"
            )
            
            # Verify commit hash
            assert commit_hash == "abc123def456"
            
            # Verify git commands
            assert mock_git.call_count == 3
            mock_git.assert_any_call(
                ["add", "."],
                cwd=temp_workspace,
                error_msg="Failed to stage changes"
            )
            mock_git.assert_any_call(
                ["commit", "-m", "feat: implement feature"],
                cwd=temp_workspace,
                error_msg="Failed to commit changes"
            )
    
    def test_get_diff_success(self, workspace_manager, temp_workspace):
        """Test getting diff successfully."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            # Mock diff output
            mock_result = MagicMock()
            mock_result.stdout = "diff --git a/file.py b/file.py\n+new line"
            mock_git.return_value = mock_result
            
            diff = workspace_manager.get_diff(workspace)
            
            # Verify diff content
            assert "diff --git" in diff
            assert "+new line" in diff
            
            # Verify git command
            mock_git.assert_called_once_with(
                ["diff", "origin/main...HEAD"],
                cwd=temp_workspace,
                error_msg="Failed to get diff",
                capture_output=True
            )
    
    def test_push_branch_success_first_try(self, workspace_manager, temp_workspace):
        """Test successful push on first attempt."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            # Mock successful push
            mock_result = MagicMock()
            mock_result.stdout = "abc123def456"
            mock_git.return_value = mock_result
            
            result = workspace_manager.push_branch(
                workspace=workspace,
                branch_name="feature/task-1-test"
            )
            
            # Verify result
            assert result.success is True
            assert result.branch_name == "feature/task-1-test"
            assert result.commit_hash == "abc123def456"
            assert result.retry_count == 0
            assert result.error is None
    
    def test_push_branch_success_after_retry(self, workspace_manager_with_retry, temp_workspace):
        """Test successful push after retry."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager_with_retry, '_run_git_command') as mock_git:
            # Mock first attempt fails, second succeeds
            mock_result = MagicMock()
            mock_result.stdout = "abc123def456"
            
            call_count = 0
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise subprocess.CalledProcessError(1, "git")
                return mock_result
            
            mock_git.side_effect = side_effect
            
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = workspace_manager_with_retry.push_branch(
                    workspace=workspace,
                    branch_name="feature/task-1-test"
                )
            
            # Verify result
            assert result.success is True
            assert result.retry_count == 1
    
    def test_push_branch_failure_after_max_retries(self, workspace_manager_with_retry, temp_workspace):
        """Test push failure after exhausting retries."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager_with_retry, '_run_git_command') as mock_git:
            # Mock all attempts fail
            mock_git.side_effect = subprocess.CalledProcessError(1, "git", stderr="network error")
            
            with patch('time.sleep'):  # Mock sleep to speed up test
                with pytest.raises(PushError) as exc_info:
                    workspace_manager_with_retry.push_branch(
                        workspace=workspace,
                        branch_name="feature/task-1-test"
                    )
            
            # Verify error message
            assert "after 3 attempts" in str(exc_info.value)
    
    def test_rollback_success(self, workspace_manager, temp_workspace):
        """Test successful rollback operation."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            workspace_manager.rollback(workspace)
            
            # Verify git commands
            assert mock_git.call_count == 2
            mock_git.assert_any_call(
                ["reset", "--hard", "origin/main"],
                cwd=temp_workspace,
                error_msg="Failed to rollback changes"
            )
            mock_git.assert_any_call(
                ["clean", "-fd"],
                cwd=temp_workspace,
                error_msg="Failed to clean untracked files"
            )
    
    def test_rollback_failure(self, workspace_manager, temp_workspace):
        """Test rollback failure."""
        workspace = Workspace(
            path=temp_workspace,
            branch_name="feature/task-1-test",
            base_branch="main"
        )
        
        with patch.object(workspace_manager, '_run_git_command') as mock_git:
            mock_git.side_effect = subprocess.CalledProcessError(1, "git")
            
            with pytest.raises(WorkspacePreparationError):
                workspace_manager.rollback(workspace)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

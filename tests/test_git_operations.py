"""Tests for GitOperations class."""

import tempfile
import subprocess
from pathlib import Path
import pytest

from necrocode.repo_pool.git_operations import GitOperations
from necrocode.repo_pool.exceptions import GitOperationError


@pytest.fixture
def git_ops():
    """Create GitOperations instance."""
    return GitOperations(max_retries=2, retry_delay=0.1)


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Create initial commit
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
    
    return repo_dir


def test_fetch_all(git_ops, temp_repo):
    """Test fetch_all operation."""
    result = git_ops.fetch_all(temp_repo)
    assert result.success
    assert result.exit_code == 0
    assert "git fetch --all --prune" in result.command


def test_clean(git_ops, temp_repo):
    """Test clean operation."""
    # Create an untracked file
    (temp_repo / "untracked.txt").write_text("untracked content")
    
    result = git_ops.clean(temp_repo, force=True)
    assert result.success
    assert result.exit_code == 0
    assert not (temp_repo / "untracked.txt").exists()


def test_reset_hard(git_ops, temp_repo):
    """Test reset_hard operation."""
    # Modify a tracked file
    (temp_repo / "README.md").write_text("Modified content")
    
    result = git_ops.reset_hard(temp_repo)
    assert result.success
    assert result.exit_code == 0
    assert (temp_repo / "README.md").read_text() == "# Test Repo"


def test_get_current_branch(git_ops, temp_repo):
    """Test get_current_branch operation."""
    branch = git_ops.get_current_branch(temp_repo)
    # Default branch could be 'master' or 'main' depending on git config
    assert branch in ["master", "main"]


def test_get_current_commit(git_ops, temp_repo):
    """Test get_current_commit operation."""
    commit = git_ops.get_current_commit(temp_repo)
    assert len(commit) == 40  # Full SHA hash
    assert all(c in "0123456789abcdef" for c in commit)


def test_checkout(git_ops, temp_repo):
    """Test checkout operation."""
    # Create a new branch
    subprocess.run(["git", "checkout", "-b", "test-branch"], cwd=temp_repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "master"], cwd=temp_repo, capture_output=True)
    
    # Test checkout
    result = git_ops.checkout(temp_repo, "test-branch")
    assert result.success
    assert git_ops.get_current_branch(temp_repo) == "test-branch"


def test_list_remote_branches(git_ops, temp_repo):
    """Test list_remote_branches operation."""
    branches = git_ops.list_remote_branches(temp_repo)
    # Local repo without remotes should return empty list
    assert isinstance(branches, list)


def test_is_clean_working_tree(git_ops, temp_repo):
    """Test is_clean_working_tree operation."""
    # Clean working tree
    assert git_ops.is_clean_working_tree(temp_repo) is True
    
    # Dirty working tree
    (temp_repo / "new_file.txt").write_text("new content")
    assert git_ops.is_clean_working_tree(temp_repo) is False


def test_git_operation_error_on_invalid_repo(git_ops, tmp_path):
    """Test that GitOperationError is raised for invalid operations."""
    invalid_repo = tmp_path / "nonexistent"
    
    with pytest.raises(GitOperationError):
        git_ops.fetch_all(invalid_repo)


def test_retry_mechanism(git_ops, tmp_path):
    """Test that retry mechanism works."""
    # This should fail and retry
    invalid_repo = tmp_path / "nonexistent"
    
    with pytest.raises(GitOperationError) as exc_info:
        git_ops.fetch_all(invalid_repo)
    
    # Check that error message mentions retries
    assert "attempts" in str(exc_info.value).lower()

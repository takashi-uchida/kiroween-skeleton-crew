"""Worktree Managerのテスト"""
import pytest
from pathlib import Path
import subprocess
import tempfile
import shutil

from necrocode.worktree_manager import WorktreeManager


@pytest.fixture
def temp_repo():
    """一時的なGitリポジトリを作成"""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Gitリポジトリを初期化
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
    
    # 初期コミットを作成
    readme = temp_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)
    
    yield temp_dir
    
    # クリーンアップ
    shutil.rmtree(temp_dir)


def test_create_worktree(temp_repo):
    """Worktree作成のテスト"""
    mgr = WorktreeManager(temp_repo)
    
    worktree_path = mgr.create_worktree("1", "feature/task-1-test")
    
    assert worktree_path.exists()
    assert worktree_path.name == "task-1"
    assert (worktree_path / "README.md").exists()


def test_list_worktrees(temp_repo):
    """Worktreeリストのテスト"""
    mgr = WorktreeManager(temp_repo)
    
    mgr.create_worktree("1", "feature/task-1-test")
    mgr.create_worktree("2", "feature/task-2-test")
    
    worktrees = mgr.list_worktrees()
    
    # メインworktree + 2つのタスクworktree
    assert len(worktrees) >= 3


def test_remove_worktree(temp_repo):
    """Worktree削除のテスト"""
    mgr = WorktreeManager(temp_repo)
    
    worktree_path = mgr.create_worktree("1", "feature/task-1-test")
    assert worktree_path.exists()
    
    mgr.remove_worktree("1")
    assert not worktree_path.exists()


def test_cleanup_all(temp_repo):
    """全Worktreeクリーンアップのテスト"""
    mgr = WorktreeManager(temp_repo)
    
    mgr.create_worktree("1", "feature/task-1-test")
    mgr.create_worktree("2", "feature/task-2-test")
    
    mgr.cleanup_all()
    
    worktrees = mgr.list_worktrees()
    # メインworktreeのみ残る
    task_worktrees = [wt for wt in worktrees if 'task-' in wt.get('path', '')]
    assert len(task_worktrees) == 0

"""統合テスト"""
import pytest
from pathlib import Path
import subprocess
import tempfile
import shutil
import json

from necrocode.worktree_manager import WorktreeManager
from necrocode.task_context import TaskContextGenerator
from necrocode.parallel_orchestrator import execute_task_in_worktree


@pytest.fixture
def temp_repo():
    """一時的なGitリポジトリを作成"""
    temp_dir = Path(tempfile.mkdtemp())
    
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
    
    readme = temp_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)
    
    # タスク定義を作成
    tasks_dir = temp_dir / ".kiro/tasks/test-project"
    tasks_dir.mkdir(parents=True)
    
    tasks = {
        "project": "test-project",
        "tasks": [
            {
                "id": "1",
                "title": "テストファイル作成",
                "description": "test.txtを作成",
                "dependencies": [],
                "type": "test",
                "files_to_create": ["test.txt"],
                "acceptance_criteria": ["test.txtが存在する"]
            }
        ]
    }
    
    with open(tasks_dir / "tasks.json", 'w') as f:
        json.dump(tasks, f)
    
    yield temp_dir
    
    shutil.rmtree(temp_dir)


def test_task_context_generation(temp_repo):
    """タスクコンテキスト生成のテスト"""
    mgr = WorktreeManager(temp_repo)
    gen = TaskContextGenerator()
    
    worktree_path = mgr.create_worktree("1", "feature/task-1-test")
    
    task = {
        "id": "1",
        "title": "テストタスク",
        "description": "これはテストです",
        "dependencies": [],
        "type": "test",
        "files_to_create": ["test.txt"],
        "acceptance_criteria": ["テストが通る"]
    }
    
    gen.generate(worktree_path, task)
    
    context_file = worktree_path / ".kiro/current-task.md"
    assert context_file.exists()
    
    content = context_file.read_text()
    assert "テストタスク" in content
    assert "test.txt" in content
    
    mgr.remove_worktree("1", force=True)


def test_worktree_isolation(temp_repo):
    """Worktree分離のテスト"""
    mgr = WorktreeManager(temp_repo)
    
    wt1 = mgr.create_worktree("1", "feature/task-1")
    wt2 = mgr.create_worktree("2", "feature/task-2")
    
    # 各worktreeで独立したファイルを作成
    (wt1 / "file1.txt").write_text("Task 1")
    (wt2 / "file2.txt").write_text("Task 2")
    
    # 相互に影響しないことを確認
    assert (wt1 / "file1.txt").exists()
    assert not (wt1 / "file2.txt").exists()
    
    assert (wt2 / "file2.txt").exists()
    assert not (wt2 / "file1.txt").exists()
    
    mgr.cleanup_all()

"""Git Worktreeベースの並列実行管理"""
from pathlib import Path
import subprocess
from typing import Optional, List, Dict
import json


class WorktreeManager:
    """Git worktreeの作成・削除・管理"""
    
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.worktree_base = self.repo_root / "worktrees"
        self.worktree_base.mkdir(exist_ok=True)
    
    def create_worktree(self, task_id: str, branch_name: str) -> Path:
        """タスク専用worktreeを作成"""
        worktree_path = self.worktree_base / f"task-{task_id}"
        
        if worktree_path.exists():
            raise ValueError(f"Worktree already exists: {worktree_path}")
        
        subprocess.run([
            "git", "worktree", "add",
            str(worktree_path),
            "-b", branch_name
        ], cwd=self.repo_root, check=True, capture_output=True)
        
        return worktree_path
    
    def remove_worktree(self, task_id: str, force: bool = False):
        """worktreeをクリーンアップ"""
        worktree_path = self.worktree_base / f"task-{task_id}"
        
        if not worktree_path.exists():
            return
        
        cmd = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            cmd.append("--force")
        
        subprocess.run(cmd, cwd=self.repo_root, check=True, capture_output=True)
    
    def list_worktrees(self) -> List[Dict[str, str]]:
        """アクティブなworktreeをリスト"""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        return self._parse_worktree_list(result.stdout)
    
    def _parse_worktree_list(self, output: str) -> List[Dict[str, str]]:
        """git worktree list --porcelainの出力をパース"""
        worktrees = []
        current = {}
        
        for line in output.strip().split('\n'):
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
                continue
            
            if line.startswith('worktree '):
                current['path'] = line.split(' ', 1)[1]
            elif line.startswith('HEAD '):
                current['head'] = line.split(' ', 1)[1]
            elif line.startswith('branch '):
                current['branch'] = line.split(' ', 1)[1]
        
        if current:
            worktrees.append(current)
        
        return worktrees
    
    def cleanup_all(self):
        """全てのタスクworktreeをクリーンアップ"""
        worktrees = self.list_worktrees()
        worktree_base_resolved = self.worktree_base.resolve()
        
        for wt in worktrees:
            path = Path(wt['path']).resolve()
            # worktrees/配下のtask-*ディレクトリのみを削除
            if path.parent == worktree_base_resolved and path.name.startswith('task-'):
                task_id = path.name.replace('task-', '')
                try:
                    self.remove_worktree(task_id, force=True)
                except Exception as e:
                    print(f"Warning: Failed to remove worktree {task_id}: {e}")

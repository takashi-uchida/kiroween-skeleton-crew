"""Git Worktreeベースの並列実行管理"""
from pathlib import Path
import subprocess
from typing import Optional, List, Dict, Any
import json


class WorktreeManager:
    """Git worktreeの作成・削除・管理"""
    
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.common_repo_root = self._detect_common_root()
        self.worktree_base = self.common_repo_root / "worktrees"
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
            # worktrees/配下の全ディレクトリを削除（メインworktreeは除く）
            if path.parent == worktree_base_resolved:
                try:
                    # git worktree removeで削除
                    import subprocess
                    subprocess.run(['git', 'worktree', 'remove', '--force', str(path)], 
                                 check=True, capture_output=True)
                    print(f"✓ Removed worktree: {path.name}")
                except Exception as e:
                    print(f"Warning: Failed to remove worktree {path.name}: {e}")

    def summarize_worktrees(self) -> List[Dict[str, Any]]:
        """worktreeメタデータを集約して返す"""
        summaries = []
        for entry in self.list_worktrees():
            path = Path(entry['path'])
            branch_ref = entry.get('branch')
            category = self._categorize_worktree(path)
            summaries.append({
                **entry,
                'category': category,
                'is_task_worktree': category == 'task',
                'branch_missing': not self._branch_exists(branch_ref) if branch_ref else False,
                'path_exists': path.exists()
            })
        return summaries

    def _categorize_worktree(self, path: Path) -> str:
        """worktreeの種類 (root/task/external) を判定"""
        if path == self.repo_root:
            return 'root'
        try:
            path.relative_to(self.worktree_base)
            return 'task'
        except ValueError:
            return 'external'

    def _branch_exists(self, branch_ref: Optional[str]) -> bool:
        """ブランチ参照が存在するか確認"""
        if not branch_ref:
            return True
        result = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", branch_ref],
            cwd=self.repo_root
        )
        return result.returncode == 0

    def _detect_common_root(self) -> Path:
        """共有gitディレクトリから共通ルートを推定"""
        try:
            # .gitがファイル（worktree）かディレクトリ（通常のリポジトリ）かを確認
            git_path = self.repo_root / ".git"
            if not git_path.exists():
                # .gitが存在しない場合はrepo_rootを返す
                return self.repo_root
            
            if git_path.is_file():
                # worktreeの場合、共通ルートを検出
                result = subprocess.run(
                    ["git", "rev-parse", "--git-common-dir"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                git_dir = Path(result.stdout.strip()).resolve()
                return git_dir.parent
            else:
                # 通常のリポジトリの場合はrepo_rootを返す
                return self.repo_root
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Gitコマンドが失敗した場合はrepo_rootを返す
            return self.repo_root

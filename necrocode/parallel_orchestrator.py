"""並列タスク実行のオーケストレーション"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Set
import json
import subprocess

from necrocode.worktree_manager import WorktreeManager
from necrocode.task_registry import TaskRegistry


class ParallelOrchestrator:
    """並列タスク実行の調整"""
    
    def __init__(self, project_dir: Path, max_workers: int = 3):
        self.project_dir = Path(project_dir)
        self.max_workers = max_workers
        self.worktree_mgr = WorktreeManager(project_dir)
        self.task_registry = TaskRegistry(project_dir / ".kiro/registry")
    
    def execute_parallel(self, project_name: str):
        """依存関係を解決して並列実行"""
        tasks = self._load_tasks(project_name)
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            completed_tasks = set()
            
            while len(completed_tasks) < len(tasks):
                # 実行可能なタスクを取得
                ready_tasks = self._get_ready_tasks(tasks, completed_tasks)
                
                # 並列実行を開始
                for task in ready_tasks:
                    if task["id"] not in futures and task["id"] not in completed_tasks:
                        future = executor.submit(
                            execute_task_in_worktree,
                            self.project_dir,
                            task
                        )
                        futures[task["id"]] = future
                
                # 完了を待機
                done_ids = []
                for task_id, future in futures.items():
                    if future.done():
                        try:
                            result = future.result()
                            completed_tasks.add(task_id)
                            done_ids.append(task_id)
                            print(f"✓ Task {task_id} completed: {result.get('pr_url', 'N/A')}")
                        except Exception as e:
                            print(f"✗ Task {task_id} failed: {e}")
                            completed_tasks.add(task_id)  # 失敗してもスキップ
                            done_ids.append(task_id)
                
                for task_id in done_ids:
                    del futures[task_id]
    
    def _load_tasks(self, project_name: str) -> List[Dict]:
        """タスク定義を読み込み"""
        tasks_file = self.project_dir / ".kiro/tasks" / project_name / "tasks.json"
        with open(tasks_file) as f:
            data = json.load(f)
        return data["tasks"]
    
    def _get_ready_tasks(self, tasks: List[Dict], completed: Set[str]) -> List[Dict]:
        """依存関係が満たされたタスクを返す"""
        ready = []
        for task in tasks:
            if task["id"] in completed:
                continue
            deps = set(task.get("dependencies", []))
            if deps.issubset(completed):
                ready.append(task)
        return ready


def execute_task_in_worktree(project_dir: Path, task: Dict) -> Dict:
    """独立したworktreeでタスクを実行（プロセス分離用）"""
    from necrocode.worktree_manager import WorktreeManager
    from necrocode.task_context import TaskContextGenerator
    
    task_id = task["id"]
    slug = task["title"].lower().replace(" ", "-")[:30]
    branch_name = f"feature/task-{task_id}-{slug}"
    
    worktree_mgr = WorktreeManager(project_dir)
    context_gen = TaskContextGenerator()
    
    try:
        # 1. Worktreeを作成
        worktree_path = worktree_mgr.create_worktree(task_id, branch_name)
        
        # 2. タスクコンテキストを書き込み
        context_gen.generate(worktree_path, task)
        
        # 3. Kiroを呼び出し（現時点ではスタブ）
        # TODO: 実際のKiro呼び出しを実装
        print(f"[Task {task_id}] Kiro実行中...")
        
        # 4. 変更をコミット
        _commit_changes(worktree_path, task)
        
        # 5. ブランチをプッシュ
        _push_branch(worktree_path, branch_name)
        
        # 6. PRを作成（スタブ）
        pr_url = f"https://github.com/user/repo/pull/{task_id}"
        
        return {
            "task_id": task_id,
            "status": "success",
            "pr_url": pr_url
        }
    
    finally:
        # 7. Worktreeをクリーンアップ
        worktree_mgr.remove_worktree(task_id, force=True)


def _commit_changes(worktree_path: Path, task: Dict):
    """変更をコミット"""
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    
    commit_msg = f"feat(task-{task['id']}): {task['title']}\n\nTask: {task['id']}"
    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=worktree_path,
        check=True,
        capture_output=True
    )


def _push_branch(worktree_path: Path, branch_name: str):
    """ブランチをプッシュ"""
    subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        cwd=worktree_path,
        check=True,
        capture_output=True
    )

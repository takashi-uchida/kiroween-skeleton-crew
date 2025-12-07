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
    
    def __init__(self, project_dir: Path, max_workers: int = 3, kiro_mode: str = "manual"):
        self.project_dir = Path(project_dir)
        self.max_workers = max_workers
        self.kiro_mode = kiro_mode
        self.worktree_mgr = WorktreeManager(project_dir)
        self.task_registry = TaskRegistry(project_dir / ".kiro/registry")
    
    def execute_parallel(self, project_name: str):
        """依存関係を解決して並列実行"""
        tasks = self._load_tasks(project_name)
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            completed_tasks = set()
            
            while len(completed_tasks) < len(tasks):
                ready_tasks = self._get_ready_tasks(tasks, completed_tasks)
                
                for task in ready_tasks:
                    if task["id"] not in futures and task["id"] not in completed_tasks:
                        future = executor.submit(
                            execute_task_in_worktree,
                            self.project_dir,
                            task,
                            self.kiro_mode
                        )
                        futures[task["id"]] = future
                
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
                            completed_tasks.add(task_id)
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


def execute_task_in_worktree(project_dir: Path, task: Dict, kiro_mode: str = "manual") -> Dict:
    """独立したworktreeでタスクを実行（プロセス分離用）"""
    from necrocode.worktree_manager import WorktreeManager
    from necrocode.task_context import TaskContextGenerator
    from necrocode.kiro_invoker import KiroInvoker
    
    task_id = task["id"]
    slug = task["title"].lower().replace(" ", "-")[:30]
    branch_name = f"feature/task-{task_id}-{slug}"
    
    worktree_mgr = WorktreeManager(project_dir)
    context_gen = TaskContextGenerator()
    kiro = KiroInvoker()
    
    try:
        # 1. Worktreeを作成
        print(f"[Task {task_id}] Worktreeを作成中...")
        worktree_path = worktree_mgr.create_worktree(task_id, branch_name)
        
        # 2. タスクコンテキストを書き込み
        print(f"[Task {task_id}] タスクコンテキストを生成中...")
        context_gen.generate(worktree_path, task)
        
        # 3. Kiroを呼び出し
        print(f"[Task {task_id}] Kiroを実行中...")
        kiro_result = kiro.invoke(worktree_path, task, mode=kiro_mode)
        
        if not kiro_result.get("success"):
            raise RuntimeError(f"Kiro execution failed: {kiro_result.get('stderr', 'Unknown error')}")
        
        # 4. 変更をコミット
        print(f"[Task {task_id}] 変更をコミット中...")
        _commit_changes(worktree_path, task)
        
        # 5. ブランチをプッシュ（オプション）
        # print(f"[Task {task_id}] ブランチをプッシュ中...")
        # _push_branch(worktree_path, branch_name)
        
        # 6. PRを作成（スタブ）
        pr_url = f"https://github.com/user/repo/pull/{task_id}"
        
        return {
            "task_id": task_id,
            "status": "success",
            "pr_url": pr_url,
            "branch": branch_name,
            "worktree": str(worktree_path)
        }
    
    except Exception as e:
        print(f"[Task {task_id}] エラー: {e}")
        raise
    
    finally:
        # 7. Worktreeをクリーンアップ（オプション）
        # worktree_mgr.remove_worktree(task_id, force=True)
        pass


def _commit_changes(worktree_path: Path, task: Dict):
    """変更をコミット"""
    # 変更があるか確認
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True
    )
    
    if not status.stdout.strip():
        print(f"  変更なし、コミットをスキップ")
        return
    
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

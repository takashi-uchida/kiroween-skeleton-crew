"""NecroCode - Kiroネイティブ並列実行フレームワーク

Git Worktreeを活用して複数のKiroインスタンスを並列実行し、
ソフトウェア開発タスクを自動化するフレームワーク。
"""

__version__ = "0.1.0"
__author__ = "NecroCode Team"

from necrocode.cli import cli
from necrocode.worktree_manager import WorktreeManager
from necrocode.parallel_orchestrator import ParallelOrchestrator
from necrocode.task_planner import TaskPlanner
from necrocode.progress_monitor import ProgressMonitor

__all__ = [
    "cli",
    "WorktreeManager",
    "ParallelOrchestrator",
    "TaskPlanner",
    "ProgressMonitor",
]

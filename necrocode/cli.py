"""NecroCode CLI - Kiro並列実行オーケストレーター"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import click

from necrocode.parallel_orchestrator import ParallelOrchestrator
from necrocode.task_planner import Task, TaskPlanner
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.kiro_sync import TaskDefinition
from necrocode.task_registry.exceptions import TaskRegistryError, TasksetNotFoundError
from necrocode.task_registry.models import TaskState


def _register_tasks_with_registry(project: str, description: str, tasks: Sequence[Task]) -> None:
    """Task Registry にタスクを登録して status から参照できるようにする."""
    if not tasks:
        return
    
    registry_root = Path(".kiro/registry")
    registry = TaskRegistry(registry_root)
    
    task_definitions = [
        TaskDefinition(
            id=str(task.id),
            title=task.title,
            description=task.description,
            is_optional=getattr(task, "is_optional", False),
            is_completed=False,
            dependencies=list(task.dependencies),
        )
        for task in tasks
    ]
    metadata = {
        "description": description,
        "project": project,
        "source": "necrocode.cli",
    }
    
    try:
        registry.create_taskset(
            spec_name=project,
            tasks=task_definitions,
            metadata=metadata,
        )
    except TaskRegistryError as exc:
        click.echo(f"⚠️ Task Registryへの登録に失敗しました: {exc}")


def _print_task_summary(tasks: Iterable[Task]) -> None:
    """生成済みタスクを一覧表示."""
    click.echo("\nタスク一覧:")
    for task in tasks:
        deps = list(task.dependencies)
        deps_str = f" (依存: {', '.join(deps)})" if deps else ""
        click.echo(f"  - Task {task.id}: {task.title}{deps_str}")


def _generate_fallback_tasks(job_description: str, project: str) -> List[Task]:
    """LLMなし時に最低限のタスクを返す."""
    return [
        Task(
            id="1",
            title="プロジェクト初期化",
            description="基本的なプロジェクト構造を作成",
            dependencies=[],
            type="setup",
            files_to_create=["README.md", ".gitignore"],
            acceptance_criteria=[
                "README.mdにプロジェクト説明がある",
                ".gitignoreに基本的な除外設定がある",
            ],
            technical_context={
                "job_description": job_description,
                "project": project,
            },
        )
    ]


@click.group()
def cli():
    """NecroCode - Kiro並列実行オーケストレーター"""
    pass


@cli.command()
@click.argument('job_description')
@click.option('--project', default='default', help='プロジェクト名')
@click.option('--use-llm/--no-llm', default=True, help='LLMを使用してタスクを生成')
def plan(job_description: str, project: str, use_llm: bool):
    """ジョブ記述からタスクを計画して Task Registry に登録"""
    planner = TaskPlanner()
    tasks: List[Task] = []
    
    if use_llm:
        click.echo("LLMを使用してタスクを生成中...")
        try:
            tasks = planner.plan(job_description, project)
        except Exception as exc:  # pragma: no cover - defensive
            click.echo(f"エラー: LLMでのタスク生成に失敗しました: {exc}")
            click.echo("フォールバックタスクを使用します...")
            use_llm = False
    
    if not use_llm:
        tasks = _generate_fallback_tasks(job_description, project)
        planner.save_tasks(project, tasks)
    
    if not tasks:
        click.echo("エラー: タスク生成に失敗しました")
        return
    
    tasks_file = planner.tasks_dir / project / "tasks.json"
    click.echo(f"✓ {len(tasks)}個のタスクを作成しました")
    click.echo(f"  保存先: {tasks_file}")
    _print_task_summary(tasks)
    
    _register_tasks_with_registry(project, job_description, tasks)


@cli.command()
@click.argument('project_name')
@click.option('--workers', default=3, help='並列実行数')
@click.option('--mode', type=click.Choice(['auto', 'manual', 'api']), default='manual', 
              help='Kiro実行モード (auto: 自動実行, manual: 手動実行, api: API経由)')
@click.option('--show-progress/--no-progress', default=True, help='進捗を表示')
def execute(project_name: str, workers: int, mode: str, show_progress: bool):
    """タスクを並列実行"""
    click.echo(f"プロジェクト '{project_name}' を実行中...")
    click.echo(f"並列ワーカー数: {workers}")
    click.echo(f"Kiroモード: {mode}")
    
    orchestrator = ParallelOrchestrator(
        Path("."), 
        max_workers=workers, 
        kiro_mode=mode,
        show_progress=show_progress
    )
    orchestrator.execute_parallel(project_name)
    
    click.echo("\n✓ 全タスク完了")


_STATUS_ICONS = {
    TaskState.DONE.value: "✓",
    TaskState.RUNNING.value: "⚙",
    TaskState.READY.value: "⏳",
    TaskState.BLOCKED.value: "🔒",
    TaskState.FAILED.value: "✗",
}


def _summarize_taskset(taskset, include_tasks: bool = True) -> dict:
    """Taskset を CLI 用に要約."""
    total = len(taskset.tasks)
    counts = Counter(task.state for task in taskset.tasks)
    
    summary = {
        "project": taskset.spec_name,
        "version": taskset.version,
        "total_tasks": total,
        "completed": counts.get(TaskState.DONE, 0),
        "running": counts.get(TaskState.RUNNING, 0),
        "ready": counts.get(TaskState.READY, 0),
        "blocked": counts.get(TaskState.BLOCKED, 0),
        "failed": counts.get(TaskState.FAILED, 0),
        "progress": (counts.get(TaskState.DONE, 0) / total * 100) if total else 0.0,
        "created_at": taskset.created_at.isoformat(),
        "updated_at": taskset.updated_at.isoformat(),
        "metadata": taskset.metadata,
    }
    
    if include_tasks:
        summary["tasks"] = [
            {
                "id": task.id,
                "title": task.title,
                "state": task.state.value,
                "dependencies": task.dependencies,
                "updated_at": task.updated_at.isoformat(),
            }
            for task in taskset.tasks
        ]
    
    return summary


def _load_taskset_summary(registry: TaskRegistry, project: str, include_tasks: bool) -> Optional[dict]:
    """Taskset を安全に読み込み."""
    try:
        taskset = registry.get_taskset(project)
    except TasksetNotFoundError:
        return None
    return _summarize_taskset(taskset, include_tasks=include_tasks)


def _print_project_status(summary: dict) -> None:
    """単一プロジェクトのステータスをテーブル表示."""
    click.echo(f"\nプロジェクト: {summary['project']} (version {summary['version']})")
    click.echo(
        f"進捗: {summary['progress']:.1f}% "
        f"({summary['completed']}/{summary['total_tasks']} 完了, 失敗 {summary['failed']})"
    )
    click.echo(
        "状態内訳: "
        f"完了 {summary['completed']} / 実行中 {summary['running']} / "
        f"準備済 {summary['ready']} / ブロック {summary['blocked']} / 失敗 {summary['failed']}"
    )
    click.echo(f"作成: {summary['created_at']} | 最終更新: {summary['updated_at']}")
    
    description = summary.get("metadata", {}).get("description")
    if description:
        click.echo(f"説明: {description}")
    
    tasks = summary.get("tasks", [])
    if not tasks:
        click.echo("タスクが登録されていません")
        return
    
    click.echo("\nタスク詳細:")
    for task in tasks:
        icon = _STATUS_ICONS.get(task["state"], "•")
        deps = task.get("dependencies") or []
        deps_str = f" (依存: {', '.join(deps)})" if deps else ""
        click.echo(f"  {icon} [{task['state']}] Task {task['id']}: {task['title']}{deps_str}")


@cli.command()
@click.option('--project', default=None, help='プロジェクト名')
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['table', 'json']),
    default='table',
    help='表示形式 (table/json)',
)
def status(project: str, output_format: str):
    """Task Registryを元に実行状況を表示"""
    registry = TaskRegistry(Path(".kiro/registry"))
    
    if project:
        summary = _load_taskset_summary(registry, project, include_tasks=True)
        if summary is None:
            click.echo(f"エラー: プロジェクト '{project}' は Task Registry に登録されていません")
            return
        
        if output_format == 'json':
            click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            _print_project_status(summary)
        return
    
    projects = registry.task_store.list_tasksets()
    if not projects:
        click.echo("Task Registryに登録されたプロジェクトがありません")
        return
    
    summaries = []
    for spec_name in projects:
        summary = _load_taskset_summary(registry, spec_name, include_tasks=False)
        if summary:
            summaries.append(summary)
    
    if output_format == 'json':
        payload = {"projects": summaries}
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    
    click.echo("全プロジェクトの状況:")
    for summary in summaries:
        click.echo(
            f"  - {summary['project']}: {summary['progress']:.1f}% "
            f"({summary['completed']}/{summary['total_tasks']} 完了, 失敗 {summary['failed']})"
        )


@cli.command()
@click.option('--force', is_flag=True, help='強制的にクリーンアップ')
def cleanup(force: bool):
    """全てのworktreeをクリーンアップ"""
    from necrocode.worktree_manager import WorktreeManager
    
    mgr = WorktreeManager(Path("."))
    
    if not force:
        worktrees = mgr.list_worktrees()
        task_worktrees = [wt for wt in worktrees if 'task-' in wt.get('path', '')]
        
        if task_worktrees:
            click.echo(f"{len(task_worktrees)}個のタスクworktreeが見つかりました:")
            for wt in task_worktrees:
                click.echo(f"  - {wt.get('path')}")
            
            if not click.confirm('これらを削除しますか？'):
                click.echo("キャンセルしました")
                return
    
    mgr.cleanup_all()
    click.echo("✓ 全worktreeをクリーンアップしました")


@cli.command()
@click.argument('project_name')
def list_tasks(project_name: str):
    """プロジェクトのタスク一覧を表示"""
    tasks_file = Path(".kiro/tasks") / project_name / "tasks.json"
    
    if not tasks_file.exists():
        click.echo(f"エラー: プロジェクト '{project_name}' が見つかりません")
        return
    
    with open(tasks_file) as f:
        data = json.load(f)
    
    click.echo(f"\nプロジェクト: {data['project']}")
    if 'description' in data:
        click.echo(f"説明: {data['description']}")
    click.echo(f"タスク数: {len(data['tasks'])}\n")
    
    for task in data['tasks']:
        deps = task.get('dependencies', [])
        deps_str = f" (依存: {', '.join(deps)})" if deps else ""
        click.echo(f"Task {task['id']}: {task['title']}{deps_str}")
        click.echo(f"  タイプ: {task.get('type', 'N/A')}")
        click.echo(f"  説明: {task['description']}")
        click.echo()


if __name__ == "__main__":
    cli()

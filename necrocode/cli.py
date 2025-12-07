"""NecroCode CLI - Kiro並列実行オーケストレーター"""
import click
from pathlib import Path
import json

from necrocode.parallel_orchestrator import ParallelOrchestrator
from necrocode.task_registry import TaskRegistry


@click.group()
def cli():
    """NecroCode - Kiro並列実行オーケストレーター"""
    pass


@cli.command()
@click.argument('job_description')
@click.option('--project', default='default', help='プロジェクト名')
def plan(job_description: str, project: str):
    """ジョブ記述からタスクを計画"""
    # TODO: LLMを使用してタスクを生成
    # 現時点ではサンプルタスクを生成
    
    tasks_dir = Path(".kiro/tasks") / project
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    sample_tasks = {
        "project": project,
        "tasks": [
            {
                "id": "1",
                "title": "プロジェクト初期化",
                "description": "基本的なプロジェクト構造を作成",
                "dependencies": [],
                "type": "setup",
                "files_to_create": ["README.md", ".gitignore"],
                "acceptance_criteria": [
                    "README.mdにプロジェクト説明がある",
                    ".gitignoreに基本的な除外設定がある"
                ]
            }
        ]
    }
    
    tasks_file = tasks_dir / "tasks.json"
    with open(tasks_file, 'w') as f:
        json.dump(sample_tasks, f, indent=2, ensure_ascii=False)
    
    click.echo(f"✓ {len(sample_tasks['tasks'])}個のタスクを作成しました")
    click.echo(f"  保存先: {tasks_file}")


@cli.command()
@click.argument('project_name')
@click.option('--workers', default=3, help='並列実行数')
def execute(project_name: str, workers: int):
    """タスクを並列実行"""
    click.echo(f"プロジェクト '{project_name}' を実行中...")
    click.echo(f"並列ワーカー数: {workers}")
    
    orchestrator = ParallelOrchestrator(Path("."), max_workers=workers)
    orchestrator.execute_parallel(project_name)
    
    click.echo("✓ 全タスク完了")


@cli.command()
@click.option('--project', default=None, help='プロジェクト名')
def status(project: str):
    """実行状況を表示"""
    registry = TaskRegistry(Path(".kiro/registry"))
    
    if project:
        click.echo(f"プロジェクト '{project}' の状況:")
    else:
        click.echo("全プロジェクトの状況:")
    
    # TODO: タスクレジストリから状況を取得して表示
    click.echo("  実装予定")


@cli.command()
def cleanup():
    """全てのworktreeをクリーンアップ"""
    from necrocode.worktree_manager import WorktreeManager
    
    mgr = WorktreeManager(Path("."))
    mgr.cleanup_all()
    click.echo("✓ 全worktreeをクリーンアップしました")


if __name__ == "__main__":
    cli()

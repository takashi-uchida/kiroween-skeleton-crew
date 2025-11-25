#!/usr/bin/env python3
"""
Custom Playbook Example

このサンプルは、カスタムPlaybookを使用したAgent Runnerの実行方法を示します。
外部サービス統合とLLM設定も含まれています。
"""

import os
from pathlib import Path
from necrocode.agent_runner import (
    TaskContext,
    RunnerOrchestrator,
    RunnerConfig,
    LLMConfig,
    PlaybookEngine,
    Playbook,
    PlaybookStep
)


def create_custom_playbook() -> Playbook:
    """カスタムPlaybookを作成"""
    
    return Playbook(
        name="Custom Backend Task Playbook",
        steps=[
            PlaybookStep(
                name="Install dependencies",
                command="npm install",
                timeout_seconds=300,
                retry_count=2,
                fail_fast=True
            ),
            PlaybookStep(
                name="Run linter",
                command="npm run lint",
                condition="lint_enabled == true",
                timeout_seconds=120,
                fail_fast=False
            ),
            PlaybookStep(
                name="Run type checker",
                command="npm run type-check",
                condition="typescript == true",
                timeout_seconds=180,
                fail_fast=False
            ),
            PlaybookStep(
                name="Run unit tests",
                command="npm test -- --coverage",
                timeout_seconds=600,
                fail_fast=True
            ),
            PlaybookStep(
                name="Build project",
                command="npm run build",
                timeout_seconds=300,
                fail_fast=True
            )
        ],
        metadata={
            "author": "NecroCode Team",
            "version": "1.0.0",
            "description": "Backend task playbook with linting and type checking"
        }
    )


def main():
    """カスタムPlaybookを使用したAgent Runnerの実行例"""
    
    print("=== カスタムPlaybookの作成 ===")
    
    # 1. カスタムPlaybookを作成
    playbook = create_custom_playbook()
    print(f"Playbook名: {playbook.name}")
    print(f"ステップ数: {len(playbook.steps)}")
    print("\nステップ:")
    for i, step in enumerate(playbook.steps, 1):
        condition = f" (条件: {step.condition})" if step.condition else ""
        print(f"  {i}. {step.name}{condition}")
    print()
    
    # 2. PlaybookをYAMLファイルに保存
    playbook_path = Path("playbooks/custom-backend-task.yaml")
    playbook_path.parent.mkdir(parents=True, exist_ok=True)
    
    import yaml
    playbook_dict = {
        "name": playbook.name,
        "steps": [
            {
                "name": step.name,
                "command": step.command,
                "condition": step.condition,
                "timeout_seconds": step.timeout_seconds,
                "retry_count": step.retry_count,
                "fail_fast": step.fail_fast
            }
            for step in playbook.steps
        ],
        "metadata": playbook.metadata
    }
    
    with open(playbook_path, "w") as f:
        yaml.dump(playbook_dict, f, default_flow_style=False, allow_unicode=True)
    
    print(f"Playbookを保存しました: {playbook_path}")
    print()
    
    # 3. タスクコンテキストを作成（Playbookを指定）
    print("=== タスクコンテキストの作成 ===")
    task_context = TaskContext(
        task_id="2.1",
        spec_name="chat-app",
        title="認証APIの実装",
        description="JWT認証を使用したログイン・登録エンドポイントを実装",
        acceptance_criteria=[
            "POST /api/auth/register で新規ユーザーを作成できる",
            "POST /api/auth/login でJWTトークンを取得できる",
            "認証ミドルウェアがJWTを検証する",
            "パスワードはbcryptでハッシュ化される"
        ],
        dependencies=["1.1"],
        required_skill="backend",
        slot_path=Path("/tmp/necrocode/workspaces/chat-app/slot-1"),
        slot_id="slot-1",
        branch_name="feature/task-2.1-auth-api",
        playbook_path=playbook_path,  # カスタムPlaybookを指定
        timeout_seconds=2400,
        metadata={
            "lint_enabled": True,
            "typescript": True
        }
    )
    
    print(f"タスクID: {task_context.task_id}")
    print(f"Playbook: {task_context.playbook_path}")
    print()
    
    # 4. LLM設定を作成
    llm_config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        model="gpt-4",
        timeout_seconds=120
    )
    
    # 5. Runner設定を作成（外部サービス統合）
    config = RunnerConfig(
        execution_mode="local-process",
        default_timeout_seconds=2400,
        log_level="INFO",
        task_registry_url=os.getenv("TASK_REGISTRY_URL", "http://localhost:8001"),
        repo_pool_url=os.getenv("REPO_POOL_URL", "http://localhost:8002"),
        artifact_store_url=os.getenv("ARTIFACT_STORE_URL", "http://localhost:8003"),
        llm_config=llm_config
    )
    
    # 6. Runnerを作成して実行
    print("=== タスクの実行 ===")
    orchestrator = RunnerOrchestrator(config)
    
    try:
        result = orchestrator.run(task_context)
        
        print()
        print("=== 実行結果 ===")
        print(f"成功: {result.success}")
        print(f"実行時間: {result.duration_seconds:.2f}秒")
        
        if result.success:
            print("\nPlaybookの実行が完了しました！")
            print(f"成果物数: {len(result.artifacts)}")
        else:
            print(f"\nエラー: {result.error}")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_playbook_engine():
    """PlaybookEngineの直接使用例"""
    
    print("\n=== PlaybookEngineの直接使用 ===")
    
    # PlaybookEngineを作成
    engine = PlaybookEngine()
    
    # Playbookを読み込み
    playbook_path = Path("playbooks/custom-backend-task.yaml")
    if playbook_path.exists():
        playbook = engine.load_playbook(playbook_path)
        print(f"Playbookを読み込みました: {playbook.name}")
        
        # Playbookを実行
        context = {
            "lint_enabled": True,
            "typescript": True,
            "workspace_path": "/tmp/necrocode/workspaces/chat-app/slot-1"
        }
        
        print("\nPlaybookを実行中...")
        result = engine.execute_playbook(playbook, context)
        
        print(f"\n実行結果: {'成功' if result.success else '失敗'}")
        print(f"実行ステップ数: {len(result.step_results)}")
        
        for step_result in result.step_results:
            status = "✓" if step_result.success else "✗"
            print(f"  {status} {step_result.step_name} ({step_result.duration_seconds:.2f}秒)")


if __name__ == "__main__":
    main()
    # demonstrate_playbook_engine()

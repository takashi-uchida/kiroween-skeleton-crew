#!/usr/bin/env python3
"""
Basic Agent Runner Usage Example

このサンプルは、Agent Runnerの基本的な使用方法を示します。
"""

from pathlib import Path
from necrocode.agent_runner import (
    TaskContext,
    RunnerOrchestrator,
    RunnerConfig,
    ExecutionMode
)


def main():
    """基本的なAgent Runnerの使用例"""
    
    # 1. タスクコンテキストを作成
    print("=== タスクコンテキストの作成 ===")
    task_context = TaskContext(
        task_id="1.1",
        spec_name="chat-app",
        title="データベーススキーマの実装",
        description="UserとMessageモデルをMongoDBで作成する",
        acceptance_criteria=[
            "Userモデルにemail、password、usernameフィールドがある",
            "Messageモデルにsender、content、timestampフィールドがある",
            "適切なインデックスが設定されている"
        ],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp/necrocode/workspaces/chat-app/slot-1"),
        slot_id="slot-1",
        branch_name="feature/task-1.1-database-schema",
        test_commands=["npm test"],
        fail_fast=True,
        timeout_seconds=1800
    )
    
    print(f"タスクID: {task_context.task_id}")
    print(f"タイトル: {task_context.title}")
    print(f"ブランチ: {task_context.branch_name}")
    print()
    
    # 2. Runner設定を作成
    print("=== Runner設定の作成 ===")
    config = RunnerConfig(
        execution_mode=ExecutionMode.LOCAL_PROCESS,
        default_timeout_seconds=1800,
        git_retry_count=3,
        network_retry_count=3,
        log_level="INFO",
        structured_logging=True,
        mask_secrets=True,
        artifact_store_url="file://~/.necrocode/artifacts"
    )
    
    print(f"実行モード: {config.execution_mode}")
    print(f"タイムアウト: {config.default_timeout_seconds}秒")
    print(f"ログレベル: {config.log_level}")
    print()
    
    # 3. Runnerを作成
    print("=== Runnerの作成 ===")
    orchestrator = RunnerOrchestrator(config)
    print(f"Runner ID: {orchestrator.runner_id}")
    print(f"初期状態: {orchestrator.state}")
    print()
    
    # 4. タスクを実行
    print("=== タスクの実行 ===")
    print("タスクを実行中...")
    
    try:
        result = orchestrator.run(task_context)
        
        # 5. 結果を表示
        print()
        print("=== 実行結果 ===")
        print(f"成功: {result.success}")
        print(f"実行時間: {result.duration_seconds:.2f}秒")
        
        if result.success:
            print(f"成果物数: {len(result.artifacts)}")
            print("\n成果物:")
            for artifact in result.artifacts:
                print(f"  - {artifact.type}: {artifact.uri} ({artifact.size_bytes} bytes)")
            
            if result.impl_result:
                print(f"\n実装結果:")
                print(f"  - 変更ファイル数: {len(result.impl_result.files_changed)}")
                print(f"  - 実装時間: {result.impl_result.duration_seconds:.2f}秒")
            
            if result.test_result:
                print(f"\nテスト結果:")
                print(f"  - 成功: {result.test_result.success}")
                print(f"  - テスト数: {len(result.test_result.test_results)}")
                print(f"  - テスト時間: {result.test_result.total_duration_seconds:.2f}秒")
            
            if result.push_result:
                print(f"\nプッシュ結果:")
                print(f"  - ブランチ: {result.push_result.branch_name}")
                print(f"  - コミットハッシュ: {result.push_result.commit_hash}")
                print(f"  - リトライ回数: {result.push_result.retry_count}")
        else:
            print(f"エラー: {result.error}")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

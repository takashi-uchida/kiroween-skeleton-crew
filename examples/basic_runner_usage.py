"""
Basic Agent Runner Usage Example

This example demonstrates the basic usage of Agent Runner with external service integration.
"""

import os
from pathlib import Path
from necrocode.agent_runner import (
    TaskContext,
    RunnerOrchestrator,
    RunnerConfig,
    LLMConfig
)


def main():
    # 1. LLM設定を作成
    llm_config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        model="gpt-4",
        timeout_seconds=120
    )
    
    # 2. Runner設定を作成（外部サービスのURLを指定）
    config = RunnerConfig(
        execution_mode="local-process",
        default_timeout_seconds=1800,
        log_level="INFO",
        task_registry_url=os.getenv("TASK_REGISTRY_URL", "http://localhost:8001"),
        repo_pool_url=os.getenv("REPO_POOL_URL", "http://localhost:8002"),
        artifact_store_url=os.getenv("ARTIFACT_STORE_URL", "http://localhost:8003"),
        llm_config=llm_config
    )
    
    # 3. タスクコンテキストを作成
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
        slot_path=Path("/tmp/necrocode/workspaces/slot-1"),
        slot_id="slot-1",
        branch_name="feature/task-1.1-database-schema",
        test_commands=["npm test"],
        related_files=["package.json", "README.md"]
    )
    
    # 4. Runnerを作成して実行
    print("Starting Agent Runner...")
    orchestrator = RunnerOrchestrator(config)
    
    try:
        result = orchestrator.run(task_context)
        
        if result.success:
            print("\n✓ タスク完了!")
            print(f"  実行時間: {result.duration_seconds:.2f}秒")
            print(f"  成果物数: {len(result.artifacts)}")
            
            if result.impl_result:
                print(f"\n実装結果:")
                print(f"  LLMモデル: {result.impl_result.llm_model}")
                print(f"  トークン使用量: {result.impl_result.tokens_used}")
                print(f"  変更ファイル数: {len(result.impl_result.files_changed)}")
            
            if result.test_result:
                print(f"\nテスト結果:")
                print(f"  成功: {result.test_result.success}")
                print(f"  実行時間: {result.test_result.total_duration_seconds:.2f}秒")
            
            print(f"\n成果物:")
            for artifact in result.artifacts:
                print(f"  - {artifact.type.value}: {artifact.uri}")
        else:
            print(f"\n✗ タスク失敗: {result.error}")
    
    except Exception as e:
        print(f"\n✗ エラー: {e}")
        raise


if __name__ == "__main__":
    main()

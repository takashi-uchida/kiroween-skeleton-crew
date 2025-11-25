#!/usr/bin/env python3
"""
Docker Runner Example

このサンプルは、DockerコンテナでAgent Runnerを実行する方法を示します。
"""

from pathlib import Path
from necrocode.agent_runner import (
    TaskContext,
    DockerRunner,
    RunnerConfig,
    ExecutionMode
)


def main():
    """DockerコンテナでAgent Runnerを実行する例"""
    
    print("=== Docker Runner Example ===")
    print()
    
    # 1. タスクコンテキストを作成
    print("=== タスクコンテキストの作成 ===")
    task_context = TaskContext(
        task_id="3.1",
        spec_name="chat-app",
        title="WebSocketサーバーの実装",
        description="Socket.ioを使用したリアルタイム通信サーバーを実装",
        acceptance_criteria=[
            "WebSocketサーバーが起動する",
            "クライアントが接続できる",
            "メッセージの送受信ができる",
            "接続・切断イベントが処理される"
        ],
        dependencies=["1.1", "2.1"],
        required_skill="backend",
        slot_path=Path("/workspace"),  # コンテナ内のパス
        slot_id="slot-1",
        branch_name="feature/task-3.1-websocket-server",
        test_commands=["npm test"],
        timeout_seconds=1800
    )
    
    print(f"タスクID: {task_context.task_id}")
    print(f"タイトル: {task_context.title}")
    print()
    
    # 2. Docker Runner設定を作成
    print("=== Docker Runner設定の作成 ===")
    config = RunnerConfig(
        execution_mode=ExecutionMode.DOCKER,
        default_timeout_seconds=1800,
        log_level="INFO",
        
        # Docker固有の設定
        docker_image="necrocode/agent-runner:latest",
        docker_volumes={
            # ホストのワークスペースをコンテナにマウント
            "/tmp/necrocode/workspaces/chat-app/slot-1": "/workspace"
        },
        docker_environment={
            "GIT_TOKEN": "${GIT_TOKEN}",  # 環境変数から取得
            "NODE_ENV": "test",
            "LOG_LEVEL": "INFO"
        },
        docker_network="necrocode-network",
        docker_memory_limit="2g",
        docker_cpu_limit="2.0"
    )
    
    print(f"Dockerイメージ: {config.docker_image}")
    print(f"メモリ制限: {config.docker_memory_limit}")
    print(f"CPU制限: {config.docker_cpu_limit}")
    print()
    
    # 3. Docker Runnerを作成
    print("=== Docker Runnerの作成 ===")
    runner = DockerRunner(config)
    print(f"Runner ID: {runner.runner_id}")
    print(f"実行モード: {runner.execution_mode}")
    print()
    
    # 4. タスクを実行
    print("=== タスクの実行 ===")
    print("Dockerコンテナを起動してタスクを実行中...")
    print()
    
    try:
        result = runner.run(task_context)
        
        # 5. 結果を表示
        print("=== 実行結果 ===")
        print(f"成功: {result.success}")
        print(f"実行時間: {result.duration_seconds:.2f}秒")
        
        if result.success:
            print(f"\nコンテナID: {runner.container_id}")
            print(f"成果物数: {len(result.artifacts)}")
            
            print("\n成果物:")
            for artifact in result.artifacts:
                print(f"  - {artifact.type}: {artifact.uri}")
            
            if result.impl_result:
                print(f"\n実装結果:")
                print(f"  - 変更ファイル: {', '.join(result.impl_result.files_changed)}")
            
            if result.test_result:
                print(f"\nテスト結果:")
                print(f"  - 成功: {result.test_result.success}")
                for test in result.test_result.test_results:
                    status = "✓" if test.success else "✗"
                    print(f"    {status} {test.command}")
        else:
            print(f"\nエラー: {result.error}")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # コンテナのクリーンアップ
        if hasattr(runner, 'container_id') and runner.container_id:
            print(f"\nコンテナをクリーンアップ中: {runner.container_id}")
            # runner.cleanup()


def demonstrate_docker_build():
    """Dockerイメージのビルド例"""
    
    print("\n=== Dockerイメージのビルド ===")
    print()
    
    # Dockerfileの内容
    dockerfile_content = """
FROM python:3.11-slim

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \\
    git \\
    nodejs \\
    npm \\
    && rm -rf /var/lib/apt/lists/*

# Agent Runnerをインストール
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Agent Runnerのコードをコピー
COPY necrocode/ necrocode/
COPY framework/ framework/

# ワークスペースディレクトリを作成
RUN mkdir -p /workspace

# エントリーポイント
ENTRYPOINT ["python", "-m", "necrocode.agent_runner"]
"""
    
    print("Dockerfile:")
    print(dockerfile_content)
    print()
    
    print("ビルドコマンド:")
    print("  docker build -t necrocode/agent-runner:latest .")
    print()
    
    print("実行コマンド:")
    print("  docker run -v /path/to/workspace:/workspace \\")
    print("    -e GIT_TOKEN=$GIT_TOKEN \\")
    print("    necrocode/agent-runner:latest")


def demonstrate_docker_compose():
    """Docker Composeの使用例"""
    
    print("\n=== Docker Composeの使用 ===")
    print()
    
    # docker-compose.ymlの内容
    compose_content = """
version: '3.8'

services:
  agent-runner:
    image: necrocode/agent-runner:latest
    volumes:
      - ./workspaces:/workspaces
    environment:
      - GIT_TOKEN=${GIT_TOKEN}
      - ARTIFACT_STORE_URL=http://artifact-store:8080
      - LOG_LEVEL=INFO
    networks:
      - necrocode-network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
  
  artifact-store:
    image: necrocode/artifact-store:latest
    ports:
      - "8080:8080"
    volumes:
      - ./artifacts:/artifacts
    networks:
      - necrocode-network

networks:
  necrocode-network:
    driver: bridge
"""
    
    print("docker-compose.yml:")
    print(compose_content)
    print()
    
    print("起動コマンド:")
    print("  docker-compose up -d")
    print()
    
    print("ログ確認:")
    print("  docker-compose logs -f agent-runner")
    print()
    
    print("停止コマンド:")
    print("  docker-compose down")


if __name__ == "__main__":
    main()
    # demonstrate_docker_build()
    # demonstrate_docker_compose()

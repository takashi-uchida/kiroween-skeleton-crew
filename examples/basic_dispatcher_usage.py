#!/usr/bin/env python3
"""
Basic Dispatcher Usage Example

このサンプルは、Dispatcherの基本的な使用方法を示します。
"""

import time
from pathlib import Path
from necrocode.dispatcher import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import (
    AgentPool,
    PoolType,
    SchedulingPolicy
)


def main():
    """基本的なDispatcherの使用例"""
    
    print("=" * 60)
    print("Basic Dispatcher Usage Example")
    print("=" * 60)
    
    # 1. 設定を作成
    print("\n1. Creating dispatcher configuration...")
    config = DispatcherConfig(
        poll_interval=5,  # 5秒ごとにポーリング
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=10,
        heartbeat_timeout=60,
        retry_max_attempts=3,
        retry_backoff_base=2.0,
        graceful_shutdown_timeout=300
    )
    
    # 2. Agent Poolを設定
    print("2. Setting up agent pools...")
    
    # ローカルプロセスプール
    local_pool = AgentPool(
        name="local",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=2,
        enabled=True,
        config={}
    )
    config.agent_pools.append(local_pool)
    
    # Dockerプール
    docker_pool = AgentPool(
        name="docker",
        type=PoolType.DOCKER,
        max_concurrency=4,
        cpu_quota=4,
        memory_quota=8192,
        enabled=True,
        config={
            "image": "necrocode/runner:latest",
            "mount_repo_pool": True
        }
    )
    config.agent_pools.append(docker_pool)
    
    # 3. スキルマッピングを設定
    print("3. Configuring skill mapping...")
    config.skill_mapping = {
        "backend": ["docker"],
        "frontend": ["docker"],
        "database": ["docker"],
        "default": ["local"]
    }
    
    print(f"\nConfiguration:")
    print(f"  - Poll interval: {config.poll_interval}s")
    print(f"  - Scheduling policy: {config.scheduling_policy.value}")
    print(f"  - Max global concurrency: {config.max_global_concurrency}")
    print(f"  - Agent pools: {len(config.agent_pools)}")
    for pool in config.agent_pools:
        print(f"    * {pool.name} ({pool.type.value}): max_concurrency={pool.max_concurrency}")
    
    # 4. Dispatcherを作成
    print("\n4. Creating dispatcher...")
    dispatcher = DispatcherCore(config)
    
    # 5. Dispatcherを起動（バックグラウンドスレッドで実行）
    print("5. Starting dispatcher...")
    print("   (Press Ctrl+C to stop)")
    
    try:
        # 非ブロッキングで起動
        import threading
        dispatcher_thread = threading.Thread(target=dispatcher.start, daemon=True)
        dispatcher_thread.start()
        
        # メインスレッドで状態を監視
        print("\n6. Monitoring dispatcher status...")
        for i in range(10):
            time.sleep(5)
            status = dispatcher.get_status()
            print(f"\n[{i+1}] Dispatcher Status:")
            print(f"  - Running: {status['running']}")
            print(f"  - Queue size: {status['queue_size']}")
            print(f"  - Running tasks: {status['running_tasks']}")
            print(f"  - Global running: {status['global_running_count']}/{status['max_global_concurrency']}")
            
            # プール状態を表示
            for pool_status in status['pool_statuses']:
                print(f"  - Pool '{pool_status['pool_name']}': {pool_status['current_running']}/{pool_status['max_concurrency']} running")
        
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal...")
    
    # 6. グレースフルシャットダウン
    print("\n7. Shutting down dispatcher...")
    dispatcher.stop(timeout=60)
    print("   Dispatcher stopped successfully")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

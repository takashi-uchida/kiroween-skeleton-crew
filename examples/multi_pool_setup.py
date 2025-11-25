#!/usr/bin/env python3
"""
Multi-Pool Setup Example

このサンプルは、複数のAgent Pool（local-process、Docker、Kubernetes）を
設定し、スキルベースのルーティングを行う方法を示します。
"""

from pathlib import Path
from necrocode.dispatcher import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import (
    AgentPool,
    PoolType,
    SchedulingPolicy
)


def create_local_pool() -> AgentPool:
    """ローカルプロセスプールを作成"""
    return AgentPool(
        name="local",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=2,
        enabled=True,
        config={
            "python_path": "/usr/bin/python3",
            "working_dir": "/tmp/necrocode/local"
        }
    )


def create_docker_pool() -> AgentPool:
    """Dockerプールを作成"""
    return AgentPool(
        name="docker",
        type=PoolType.DOCKER,
        max_concurrency=5,
        cpu_quota=8,
        memory_quota=16384,  # 16GB
        enabled=True,
        config={
            "image": "necrocode/runner:latest",
            "mount_repo_pool": True,
            "network": "necrocode-network",
            "volumes": {
                "/var/run/docker.sock": "/var/run/docker.sock"
            },
            "environment": {
                "NECROCODE_ENV": "docker",
                "LOG_LEVEL": "INFO"
            }
        }
    )


def create_docker_gpu_pool() -> AgentPool:
    """GPU対応Dockerプールを作成"""
    return AgentPool(
        name="docker-gpu",
        type=PoolType.DOCKER,
        max_concurrency=2,
        cpu_quota=16,
        memory_quota=32768,  # 32GB
        enabled=True,
        config={
            "image": "necrocode/runner:gpu",
            "mount_repo_pool": True,
            "runtime": "nvidia",
            "gpus": "all",
            "environment": {
                "NECROCODE_ENV": "docker-gpu",
                "CUDA_VISIBLE_DEVICES": "0,1"
            }
        }
    )


def create_kubernetes_pool() -> AgentPool:
    """Kubernetesプールを作成"""
    return AgentPool(
        name="k8s",
        type=PoolType.KUBERNETES,
        max_concurrency=10,
        cpu_quota=20,
        memory_quota=40960,  # 40GB
        enabled=True,
        config={
            "namespace": "necrocode-agents",
            "job_template": "manifests/runner-job.yaml",
            "service_account": "necrocode-runner",
            "image_pull_secrets": ["necrocode-registry"],
            "node_selector": {
                "workload": "necrocode"
            },
            "tolerations": [
                {
                    "key": "necrocode",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoSchedule"
                }
            ]
        }
    )


def create_kubernetes_spot_pool() -> AgentPool:
    """Kubernetesスポットインスタンスプールを作成"""
    return AgentPool(
        name="k8s-spot",
        type=PoolType.KUBERNETES,
        max_concurrency=20,
        cpu_quota=40,
        memory_quota=81920,  # 80GB
        enabled=True,
        config={
            "namespace": "necrocode-agents-spot",
            "job_template": "manifests/runner-job-spot.yaml",
            "service_account": "necrocode-runner",
            "node_selector": {
                "workload": "necrocode",
                "instance-type": "spot"
            },
            "tolerations": [
                {
                    "key": "spot",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoSchedule"
                }
            ]
        }
    )


def setup_skill_mapping() -> dict:
    """スキルマッピングを設定"""
    return {
        # 開発スキル
        "backend": ["docker", "k8s"],
        "frontend": ["docker", "k8s"],
        "database": ["docker"],
        "devops": ["k8s"],
        
        # 特殊スキル
        "ml": ["docker-gpu", "k8s"],  # 機械学習タスク
        "data-processing": ["k8s", "k8s-spot"],  # データ処理タスク
        "integration-test": ["docker"],  # 統合テスト
        
        # バッチ処理（スポットインスタンス優先）
        "batch": ["k8s-spot", "k8s"],
        
        # デフォルト
        "default": ["local", "docker"]
    }


def main():
    """複数Agent Poolの設定例"""
    
    print("=" * 60)
    print("Multi-Pool Setup Example")
    print("=" * 60)
    
    # 1. 設定を作成
    print("\n1. Creating dispatcher configuration...")
    config = DispatcherConfig(
        poll_interval=5,
        scheduling_policy=SchedulingPolicy.SKILL_BASED,
        max_global_concurrency=30,
        heartbeat_timeout=60,
        retry_max_attempts=3,
        retry_backoff_base=2.0
    )
    
    # 2. 複数のAgent Poolを作成
    print("\n2. Creating multiple agent pools...")
    
    pools = [
        create_local_pool(),
        create_docker_pool(),
        create_docker_gpu_pool(),
        create_kubernetes_pool(),
        create_kubernetes_spot_pool()
    ]
    
    for pool in pools:
        config.agent_pools.append(pool)
        print(f"\n  Pool: {pool.name}")
        print(f"    Type: {pool.type.value}")
        print(f"    Max Concurrency: {pool.max_concurrency}")
        if pool.cpu_quota:
            print(f"    CPU Quota: {pool.cpu_quota} cores")
        if pool.memory_quota:
            print(f"    Memory Quota: {pool.memory_quota} MB")
        print(f"    Enabled: {pool.enabled}")
    
    # 3. スキルマッピングを設定
    print("\n3. Configuring skill mapping...")
    config.skill_mapping = setup_skill_mapping()
    
    print("\n  Skill Mapping:")
    for skill, pool_names in config.skill_mapping.items():
        print(f"    {skill}: {', '.join(pool_names)}")
    
    # 4. Dispatcherを作成
    print("\n4. Creating dispatcher...")
    dispatcher = DispatcherCore(config)
    
    # 5. プール状態を表示
    print("\n5. Agent Pool Status:")
    for pool in config.agent_pools:
        status = dispatcher.agent_pool_manager.get_pool_status(pool.name)
        print(f"\n  {status.pool_name}:")
        print(f"    Type: {status.type.value}")
        print(f"    Enabled: {status.enabled}")
        print(f"    Capacity: {status.current_running}/{status.max_concurrency}")
        print(f"    Utilization: {status.utilization * 100:.1f}%")
    
    # 6. スキルベースのプール選択をテスト
    print("\n6. Testing skill-based pool selection...")
    
    test_skills = [
        "backend",
        "frontend",
        "ml",
        "batch",
        "unknown-skill"
    ]
    
    for skill in test_skills:
        pool = dispatcher.agent_pool_manager.get_pool_for_skill(skill)
        if pool:
            print(f"  Skill '{skill}' -> Pool '{pool.name}' ({pool.type.value})")
        else:
            print(f"  Skill '{skill}' -> No pool found")
    
    # 7. リソースクォータの確認
    print("\n7. Resource Quotas:")
    total_cpu = sum(p.cpu_quota or 0 for p in config.agent_pools)
    total_memory = sum(p.memory_quota or 0 for p in config.agent_pools)
    total_concurrency = sum(p.max_concurrency for p in config.agent_pools)
    
    print(f"  Total CPU Quota: {total_cpu} cores")
    print(f"  Total Memory Quota: {total_memory} MB ({total_memory / 1024:.1f} GB)")
    print(f"  Total Max Concurrency: {total_concurrency} tasks")
    
    # 8. プールの有効/無効を切り替え
    print("\n8. Testing pool enable/disable...")
    
    # スポットプールを無効化
    spot_pool = next(p for p in config.agent_pools if p.name == "k8s-spot")
    spot_pool.enabled = False
    print(f"  Disabled pool: {spot_pool.name}")
    
    # 再度スキル選択をテスト
    pool = dispatcher.agent_pool_manager.get_pool_for_skill("batch")
    print(f"  Skill 'batch' now routes to: {pool.name if pool else 'None'}")
    
    # プールを再度有効化
    spot_pool.enabled = True
    print(f"  Re-enabled pool: {spot_pool.name}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    
    print("\nKey takeaways:")
    print("  - Multiple pool types can coexist (local, Docker, K8s)")
    print("  - Each pool has its own resource quotas and concurrency limits")
    print("  - Skill mapping enables intelligent task routing")
    print("  - Pools can be dynamically enabled/disabled")
    print("  - Load balancing across multiple pools for the same skill")
    print("\nProduction considerations:")
    print("  - Use K8s for scalable, production workloads")
    print("  - Use spot instances for cost-effective batch processing")
    print("  - Use GPU pools for ML/AI tasks")
    print("  - Use local pools for development and testing")
    print("  - Monitor resource utilization and adjust quotas accordingly")


if __name__ == "__main__":
    main()

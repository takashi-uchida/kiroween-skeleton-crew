#!/usr/bin/env python3
"""
Custom Scheduling Policy Example

このサンプルは、カスタムスケジューリングポリシーの実装方法を示します。
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from necrocode.dispatcher import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import (
    AgentPool,
    PoolType,
    SchedulingPolicy
)
from necrocode.dispatcher.scheduler import Scheduler
from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
from necrocode.task_registry.models import Task


class CustomScheduler(Scheduler):
    """
    カスタムスケジューラー
    
    このスケジューラーは以下のルールでタスクを選択します：
    1. 優先度が最も高いタスクを選択
    2. 同じ優先度の場合、推定実行時間が短いタスクを優先
    3. スキルに基づいて適切なプールを選択
    """
    
    def __init__(self, policy: SchedulingPolicy = SchedulingPolicy.PRIORITY):
        super().__init__(policy)
        self.scheduled_count = 0
    
    def schedule(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """
        カスタムスケジューリングロジック
        
        Args:
            task_queue: タスクキュー
            agent_pool_manager: Agent Pool Manager
        
        Returns:
            (タスク, Agent Pool)のタプルのリスト
        """
        scheduled_tasks = []
        
        # キューからタスクを取得（優先度順）
        tasks_to_schedule = []
        while task_queue.size() > 0:
            task = task_queue.dequeue()
            if task:
                tasks_to_schedule.append(task)
        
        # 推定実行時間でソート（短い順）
        tasks_to_schedule.sort(
            key=lambda t: (
                -t.priority,  # 優先度が高い順
                self._estimate_duration(t)  # 実行時間が短い順
            )
        )
        
        # 各タスクに対してプールを割り当て
        for task in tasks_to_schedule:
            pool = self._select_pool_for_task(task, agent_pool_manager)
            
            if pool and agent_pool_manager.can_accept_task(pool):
                scheduled_tasks.append((task, pool))
                agent_pool_manager.increment_running_count(pool)
                self.scheduled_count += 1
                print(f"  [Custom Scheduler] Scheduled task {task.id} to pool '{pool.name}' "
                      f"(priority={task.priority}, estimated_duration={self._estimate_duration(task)}s)")
            else:
                # プールが利用できない場合はキューに戻す
                task_queue.enqueue(task)
        
        return scheduled_tasks
    
    def _estimate_duration(self, task: Task) -> int:
        """
        タスクの推定実行時間を計算
        
        Args:
            task: タスク
        
        Returns:
            推定実行時間（秒）
        """
        # メタデータから推定時間を取得、なければデフォルト値
        if task.metadata and "estimated_duration" in task.metadata:
            return task.metadata["estimated_duration"]
        
        # タスクの複雑度に基づいて推定
        complexity = task.metadata.get("complexity", "medium") if task.metadata else "medium"
        duration_map = {
            "low": 300,      # 5分
            "medium": 900,   # 15分
            "high": 1800     # 30分
        }
        return duration_map.get(complexity, 900)
    
    def _select_pool_for_task(
        self,
        task: Task,
        agent_pool_manager: AgentPoolManager
    ) -> Optional[AgentPool]:
        """
        タスクに最適なプールを選択
        
        Args:
            task: タスク
            agent_pool_manager: Agent Pool Manager
        
        Returns:
            選択されたAgent Pool
        """
        # スキルベースでプールを選択
        skill = task.metadata.get("required_skill", "default") if task.metadata else "default"
        pool = agent_pool_manager.get_pool_for_skill(skill)
        
        if not pool:
            # デフォルトプールを使用
            pool = agent_pool_manager.get_pool_for_skill("default")
        
        return pool


def main():
    """カスタムスケジューリングポリシーの使用例"""
    
    print("=" * 60)
    print("Custom Scheduling Policy Example")
    print("=" * 60)
    
    # 1. 設定を作成
    print("\n1. Creating dispatcher configuration...")
    config = DispatcherConfig(
        poll_interval=5,
        scheduling_policy=SchedulingPolicy.PRIORITY,  # カスタムスケジューラーで上書き
        max_global_concurrency=10
    )
    
    # 2. Agent Poolを設定
    print("2. Setting up agent pools...")
    
    local_pool = AgentPool(
        name="local",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=2,
        enabled=True
    )
    config.agent_pools.append(local_pool)
    
    docker_pool = AgentPool(
        name="docker",
        type=PoolType.DOCKER,
        max_concurrency=4,
        enabled=True,
        config={"image": "necrocode/runner:latest"}
    )
    config.agent_pools.append(docker_pool)
    
    # 3. スキルマッピングを設定
    config.skill_mapping = {
        "backend": ["docker"],
        "frontend": ["docker"],
        "default": ["local"]
    }
    
    # 4. Dispatcherを作成
    print("3. Creating dispatcher with custom scheduler...")
    dispatcher = DispatcherCore(config)
    
    # カスタムスケジューラーに置き換え
    custom_scheduler = CustomScheduler()
    dispatcher.scheduler = custom_scheduler
    
    print(f"\nUsing custom scheduler: {custom_scheduler.__class__.__name__}")
    print("Scheduling rules:")
    print("  1. Higher priority tasks first")
    print("  2. Shorter estimated duration first (for same priority)")
    print("  3. Skill-based pool selection")
    
    # 5. テストタスクを作成してキューに追加（デモ用）
    print("\n4. Adding test tasks to queue...")
    from necrocode.task_registry.models import Task, TaskState
    from datetime import datetime
    
    test_tasks = [
        Task(
            id="task-1",
            spec_id="test-spec",
            title="High priority, short task",
            description="Quick backend task",
            state=TaskState.READY,
            priority=10,
            created_at=datetime.now(),
            metadata={
                "required_skill": "backend",
                "estimated_duration": 300,
                "complexity": "low"
            }
        ),
        Task(
            id="task-2",
            spec_id="test-spec",
            title="High priority, long task",
            description="Complex backend task",
            state=TaskState.READY,
            priority=10,
            created_at=datetime.now(),
            metadata={
                "required_skill": "backend",
                "estimated_duration": 1800,
                "complexity": "high"
            }
        ),
        Task(
            id="task-3",
            spec_id="test-spec",
            title="Low priority task",
            description="Simple frontend task",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={
                "required_skill": "frontend",
                "estimated_duration": 600,
                "complexity": "medium"
            }
        )
    ]
    
    for task in test_tasks:
        dispatcher.task_queue.enqueue(task)
        print(f"  Added: {task.title} (priority={task.priority}, duration={task.metadata['estimated_duration']}s)")
    
    # 6. スケジューリングをテスト
    print("\n5. Testing custom scheduling...")
    scheduled = custom_scheduler.schedule(
        dispatcher.task_queue,
        dispatcher.agent_pool_manager
    )
    
    print(f"\nScheduled {len(scheduled)} tasks:")
    for task, pool in scheduled:
        print(f"  - Task '{task.title}' -> Pool '{pool.name}'")
    
    print(f"\nTotal scheduled by custom scheduler: {custom_scheduler.scheduled_count}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    print("\nKey takeaways:")
    print("  - Custom schedulers can implement complex scheduling logic")
    print("  - Tasks are sorted by priority and estimated duration")
    print("  - Pool selection is based on task skills")
    print("  - Scheduler can track custom metrics (scheduled_count)")


if __name__ == "__main__":
    main()

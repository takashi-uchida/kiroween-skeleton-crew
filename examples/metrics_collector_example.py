"""
Example usage of MetricsCollector.

Demonstrates how to collect and export dispatcher metrics.
"""

import time
from datetime import datetime, timedelta

from necrocode.dispatcher import (
    MetricsCollector,
    TaskQueue,
    AgentPoolManager,
    RunnerMonitor,
    DispatcherConfig,
    AgentPool,
    PoolType,
    SchedulingPolicy,
)
from necrocode.task_registry.models import Task, TaskState


def main():
    """Demonstrate MetricsCollector usage."""
    print("=== MetricsCollector Example ===\n")
    
    # 1. Create dispatcher components
    print("1. Creating dispatcher components...")
    
    config = DispatcherConfig(
        poll_interval=5,
        scheduling_policy=SchedulingPolicy.PRIORITY,
        agent_pools=[
            AgentPool(
                name="local",
                type=PoolType.LOCAL_PROCESS,
                max_concurrency=2,
            ),
            AgentPool(
                name="docker",
                type=PoolType.DOCKER,
                max_concurrency=4,
            ),
        ],
        skill_mapping={
            "backend": ["docker"],
            "frontend": ["docker"],
            "default": ["local"],
        },
    )
    
    task_queue = TaskQueue()
    agent_pool_manager = AgentPoolManager(config)
    runner_monitor = RunnerMonitor()
    metrics_collector = MetricsCollector()
    
    # 2. Connect components to metrics collector
    print("2. Connecting components to metrics collector...")
    metrics_collector.set_task_queue(task_queue)
    metrics_collector.set_agent_pool_manager(agent_pool_manager)
    metrics_collector.set_runner_monitor(runner_monitor)
    
    # 3. Simulate task assignments
    print("\n3. Simulating task assignments...")
    
    # Add some tasks to queue
    for i in range(5):
        task = Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description=f"Description for task {i}",
            state=TaskState.READY,
            priority=i % 3,
            created_at=datetime.now() - timedelta(seconds=10 * i),
        )
        task_queue.enqueue(task)
        print(f"  Enqueued: {task.id} (priority={task.priority})")
    
    # Simulate some assignments
    print("\n4. Recording task assignments...")
    for i in range(3):
        task = task_queue.dequeue()
        if task:
            pool = agent_pool_manager.get_default_pool()
            if pool:
                metrics_collector.record_assignment(task, pool)
                agent_pool_manager.increment_running_count(pool)
                print(f"  Assigned: {task.id} to pool '{pool.name}'")
    
    # 5. Collect metrics
    print("\n5. Collecting metrics...")
    metrics_collector.collect()
    
    metrics = metrics_collector.get_metrics()
    print(f"\nCurrent Metrics:")
    print(f"  Queue Size: {metrics['queue_size']}")
    print(f"  Running Tasks: {metrics['running_tasks']}")
    print(f"  Average Wait Time: {metrics['average_wait_time']:.2f}s")
    print(f"  Total Assignments: {metrics['total_assignments']}")
    print(f"  Pool Utilization:")
    for pool_name, utilization in metrics['pool_utilization'].items():
        print(f"    {pool_name}: {utilization:.1%}")
    
    # 6. Get assignment history
    print("\n6. Assignment History:")
    history = metrics_collector.get_assignment_history()
    for record in history:
        print(f"  Task: {record['task_id']}")
        print(f"    Pool: {record['pool_name']}")
        print(f"    Priority: {record['priority']}")
        print(f"    Wait Time: {record['wait_time_seconds']:.2f}s")
        print(f"    Assigned At: {record['assigned_at']}")
        print()
    
    # 7. Get pool assignment counts
    print("7. Pool Assignment Counts:")
    counts = metrics_collector.get_pool_assignment_counts()
    for pool_name, count in counts.items():
        print(f"  {pool_name}: {count} assignments")
    
    # 8. Get priority distribution
    print("\n8. Priority Distribution:")
    distribution = metrics_collector.get_priority_distribution()
    for priority, count in sorted(distribution.items()):
        print(f"  Priority {priority}: {count} tasks")
    
    # 9. Export to Prometheus format
    print("\n9. Prometheus Export:")
    print("-" * 60)
    prometheus_output = metrics_collector.export_prometheus()
    print(prometheus_output)
    print("-" * 60)
    
    # 10. Continuous monitoring simulation
    print("\n10. Simulating continuous monitoring...")
    print("(Collecting metrics every 2 seconds for 6 seconds)")
    
    for i in range(3):
        time.sleep(2)
        metrics_collector.collect()
        metrics = metrics_collector.get_metrics()
        print(f"\n  Iteration {i+1}:")
        print(f"    Queue: {metrics['queue_size']}, Running: {metrics['running_tasks']}")
        print(f"    Avg Wait: {metrics['average_wait_time']:.2f}s")
    
    # 11. Reset metrics
    print("\n11. Resetting metrics...")
    metrics_collector.reset_metrics()
    print("  Metrics reset complete")
    
    metrics = metrics_collector.get_metrics()
    print(f"  Queue Size after reset: {metrics.get('queue_size', 'N/A')}")
    print(f"  Assignment history length: {len(metrics_collector.get_assignment_history())}")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

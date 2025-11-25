#!/usr/bin/env python3
"""
Example demonstrating Dispatcher concurrency control features.

This example shows:
1. Global concurrency limit enforcement
2. Per-pool concurrency tracking
3. Concurrency metrics collection
4. Completion notification handling
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolType


def print_status(dispatcher: DispatcherCore, title: str):
    """Print current dispatcher status."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    
    status = dispatcher.get_status()
    
    print(f"Running: {status['running']}")
    print(f"Queue Size: {status['queue_size']}")
    print(f"Global Running: {status['global_running_count']}/{status['max_global_concurrency']}")
    
    print("\nPool Status:")
    for pool_status in status['pool_statuses']:
        print(f"  {pool_status.pool_name}:")
        print(f"    Type: {pool_status.type.value}")
        print(f"    Running: {pool_status.current_running}/{pool_status.max_concurrency}")
        print(f"    Utilization: {pool_status.utilization:.1%}")
        print(f"    Enabled: {pool_status.enabled}")
    
    metrics = status['metrics']
    if metrics:
        print("\nConcurrency Metrics:")
        print(f"  Global Running: {metrics.get('global_running_count', 0)}")
        print(f"  Global Utilization: {metrics.get('global_utilization', 0):.1%}")
        print(f"  Pool Running Counts: {metrics.get('pool_running_counts', {})}")


def example_basic_concurrency():
    """Example 1: Basic concurrency tracking."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Concurrency Tracking")
    print("=" * 60)
    
    # Create config with moderate global limit
    config = DispatcherConfig(
        max_global_concurrency=5,
        poll_interval=1,
        task_registry_dir="/tmp/dispatcher_example"
    )
    
    # Add pools
    config.agent_pools = [
        AgentPool(
            name="local-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=3
        ),
        AgentPool(
            name="docker-pool",
            type=PoolType.DOCKER,
            max_concurrency=5
        ),
    ]
    
    # Create dispatcher
    dispatcher = DispatcherCore(config)
    
    print_status(dispatcher, "Initial State")
    
    # Simulate task assignments
    print("\n--- Simulating 3 task assignments ---")
    local_pool = dispatcher.agent_pool_manager.get_pool_by_name("local-pool")
    
    for i in range(3):
        dispatcher.agent_pool_manager.increment_running_count(local_pool)
        dispatcher._increment_global_running_count()
        print(f"Assigned task {i+1}")
    
    dispatcher.metrics_collector.collect()
    print_status(dispatcher, "After 3 Assignments")
    
    # Check if can accept more
    can_accept_global = dispatcher.can_accept_task_globally()
    can_accept_pool = dispatcher.agent_pool_manager.can_accept_task(local_pool)
    
    print(f"\nCan accept globally: {can_accept_global}")
    print(f"Can accept in local-pool: {can_accept_pool}")
    
    # Simulate completion
    print("\n--- Simulating 1 task completion ---")
    dispatcher.agent_pool_manager.decrement_running_count(local_pool)
    dispatcher._decrement_global_running_count()
    
    dispatcher.metrics_collector.collect()
    print_status(dispatcher, "After 1 Completion")


def example_global_limit():
    """Example 2: Global concurrency limit enforcement."""
    print("\n" + "=" * 60)
    print("Example 2: Global Limit Enforcement")
    print("=" * 60)
    
    # Create config with low global limit
    config = DispatcherConfig(
        max_global_concurrency=3,
        poll_interval=1,
        task_registry_dir="/tmp/dispatcher_example"
    )
    
    # Add pool with higher capacity
    config.agent_pools = [
        AgentPool(
            name="high-capacity-pool",
            type=PoolType.DOCKER,
            max_concurrency=10  # Pool can handle 10, but global limit is 3
        ),
    ]
    
    dispatcher = DispatcherCore(config)
    pool = dispatcher.agent_pool_manager.get_pool_by_name("high-capacity-pool")
    
    print_status(dispatcher, "Initial State")
    
    # Fill to global limit
    print("\n--- Filling to global limit (3 tasks) ---")
    for i in range(3):
        if dispatcher.can_accept_task_globally():
            dispatcher.agent_pool_manager.increment_running_count(pool)
            dispatcher._increment_global_running_count()
            print(f"✓ Assigned task {i+1}")
        else:
            print(f"✗ Cannot assign task {i+1} - global limit reached")
    
    dispatcher.metrics_collector.collect()
    print_status(dispatcher, "At Global Limit")
    
    # Try to assign one more
    print("\n--- Attempting to exceed global limit ---")
    if dispatcher.can_accept_task_globally():
        print("✗ Should not accept - global limit reached!")
    else:
        print("✓ Correctly blocked - global limit reached")
    
    # Pool still has capacity
    if dispatcher.agent_pool_manager.can_accept_task(pool):
        print("✓ Pool has capacity (7/10 slots free)")
    else:
        print("✗ Pool should have capacity")


def example_multi_pool_distribution():
    """Example 3: Multi-pool concurrency distribution."""
    print("\n" + "=" * 60)
    print("Example 3: Multi-Pool Distribution")
    print("=" * 60)
    
    config = DispatcherConfig(
        max_global_concurrency=10,
        task_registry_dir="/tmp/dispatcher_example"
    )
    
    # Add multiple pools
    config.agent_pools = [
        AgentPool(name="pool-a", type=PoolType.LOCAL_PROCESS, max_concurrency=3),
        AgentPool(name="pool-b", type=PoolType.DOCKER, max_concurrency=4),
        AgentPool(name="pool-c", type=PoolType.KUBERNETES, max_concurrency=5),
    ]
    
    dispatcher = DispatcherCore(config)
    
    print_status(dispatcher, "Initial State")
    
    # Distribute tasks across pools
    print("\n--- Distributing tasks across pools ---")
    
    pool_a = dispatcher.agent_pool_manager.get_pool_by_name("pool-a")
    pool_b = dispatcher.agent_pool_manager.get_pool_by_name("pool-b")
    pool_c = dispatcher.agent_pool_manager.get_pool_by_name("pool-c")
    
    # Assign to pool-a
    for i in range(2):
        dispatcher.agent_pool_manager.increment_running_count(pool_a)
        dispatcher._increment_global_running_count()
    print("Assigned 2 tasks to pool-a")
    
    # Assign to pool-b
    for i in range(3):
        dispatcher.agent_pool_manager.increment_running_count(pool_b)
        dispatcher._increment_global_running_count()
    print("Assigned 3 tasks to pool-b")
    
    # Assign to pool-c
    for i in range(1):
        dispatcher.agent_pool_manager.increment_running_count(pool_c)
        dispatcher._increment_global_running_count()
    print("Assigned 1 task to pool-c")
    
    dispatcher.metrics_collector.collect()
    print_status(dispatcher, "After Distribution")


def example_prometheus_metrics():
    """Example 4: Prometheus metrics export."""
    print("\n" + "=" * 60)
    print("Example 4: Prometheus Metrics Export")
    print("=" * 60)
    
    config = DispatcherConfig(
        max_global_concurrency=10,
        task_registry_dir="/tmp/dispatcher_example"
    )
    
    config.agent_pools = [
        AgentPool(name="pool-1", type=PoolType.LOCAL_PROCESS, max_concurrency=5),
        AgentPool(name="pool-2", type=PoolType.DOCKER, max_concurrency=5),
    ]
    
    dispatcher = DispatcherCore(config)
    
    # Simulate some activity
    pool_1 = dispatcher.agent_pool_manager.get_pool_by_name("pool-1")
    pool_2 = dispatcher.agent_pool_manager.get_pool_by_name("pool-2")
    
    for i in range(3):
        dispatcher.agent_pool_manager.increment_running_count(pool_1)
        dispatcher._increment_global_running_count()
    
    for i in range(2):
        dispatcher.agent_pool_manager.increment_running_count(pool_2)
        dispatcher._increment_global_running_count()
    
    # Collect metrics
    dispatcher.metrics_collector.collect()
    
    # Export to Prometheus format
    print("\nPrometheus Metrics:")
    print("-" * 60)
    prometheus_output = dispatcher.metrics_collector.export_prometheus()
    print(prometheus_output)


def main():
    """Run all examples."""
    print("=" * 60)
    print("Dispatcher Concurrency Control Examples")
    print("=" * 60)
    
    try:
        example_basic_concurrency()
        time.sleep(1)
        
        example_global_limit()
        time.sleep(1)
        
        example_multi_pool_distribution()
        time.sleep(1)
        
        example_prometheus_metrics()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

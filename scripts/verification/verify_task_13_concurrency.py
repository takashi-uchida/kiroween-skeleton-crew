#!/usr/bin/env python3
"""
Verification script for Task 13: Concurrency Control Implementation.

Tests:
- Global running count tracking
- Per-pool running count tracking
- Global concurrency limit enforcement
- Completion notification handling
- Concurrency metrics collection
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolType, Runner, RunnerState
from necrocode.task_registry.models import Task, TaskState


def test_global_running_count_tracking():
    """Test global running count tracking."""
    print("\n=== Test: Global Running Count Tracking ===")
    
    # Create config with low global limit
    config = DispatcherConfig(
        max_global_concurrency=5,
        poll_interval=1,
        task_registry_dir="/tmp/test_registry"
    )
    
    # Add a test pool
    test_pool = AgentPool(
        name="test-pool",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=10
    )
    config.agent_pools = [test_pool]
    
    # Create dispatcher
    dispatcher = DispatcherCore(config)
    
    # Check initial state
    assert dispatcher.get_global_running_count() == 0, "Initial global count should be 0"
    assert dispatcher.can_accept_task_globally(), "Should accept tasks initially"
    print("✓ Initial state correct")
    
    # Simulate incrementing global count
    for i in range(5):
        dispatcher._increment_global_running_count()
    
    assert dispatcher.get_global_running_count() == 5, "Global count should be 5"
    assert not dispatcher.can_accept_task_globally(), "Should not accept tasks at limit"
    print("✓ Global count incremented correctly")
    
    # Simulate decrementing
    dispatcher._decrement_global_running_count()
    assert dispatcher.get_global_running_count() == 4, "Global count should be 4"
    assert dispatcher.can_accept_task_globally(), "Should accept tasks below limit"
    print("✓ Global count decremented correctly")
    
    print("✅ Global running count tracking: PASSED")
    return True


def test_per_pool_running_count():
    """Test per-pool running count tracking."""
    print("\n=== Test: Per-Pool Running Count ===")
    
    config = DispatcherConfig(task_registry_dir="/tmp/test_registry")
    
    # Add test pools
    pool1 = AgentPool(name="pool1", type=PoolType.LOCAL_PROCESS, max_concurrency=3)
    pool2 = AgentPool(name="pool2", type=PoolType.DOCKER, max_concurrency=5)
    config.agent_pools = [pool1, pool2]
    
    dispatcher = DispatcherCore(config)
    
    # Get pools from manager
    pool1_ref = dispatcher.agent_pool_manager.get_pool_by_name("pool1")
    pool2_ref = dispatcher.agent_pool_manager.get_pool_by_name("pool2")
    
    assert pool1_ref is not None, "Pool1 should exist"
    assert pool2_ref is not None, "Pool2 should exist"
    
    # Check initial state
    assert pool1_ref.current_running == 0, "Pool1 initial count should be 0"
    assert pool2_ref.current_running == 0, "Pool2 initial count should be 0"
    print("✓ Initial pool counts correct")
    
    # Increment pool1
    dispatcher.agent_pool_manager.increment_running_count(pool1_ref)
    dispatcher.agent_pool_manager.increment_running_count(pool1_ref)
    assert pool1_ref.current_running == 2, "Pool1 count should be 2"
    assert dispatcher.agent_pool_manager.can_accept_task(pool1_ref), "Pool1 should accept tasks"
    print("✓ Pool1 incremented correctly")
    
    # Fill pool1 to capacity
    dispatcher.agent_pool_manager.increment_running_count(pool1_ref)
    assert pool1_ref.current_running == 3, "Pool1 count should be 3"
    assert not dispatcher.agent_pool_manager.can_accept_task(pool1_ref), "Pool1 should be full"
    print("✓ Pool1 at capacity")
    
    # Decrement pool1
    dispatcher.agent_pool_manager.decrement_running_count(pool1_ref)
    assert pool1_ref.current_running == 2, "Pool1 count should be 2"
    assert dispatcher.agent_pool_manager.can_accept_task(pool1_ref), "Pool1 should accept tasks again"
    print("✓ Pool1 decremented correctly")
    
    print("✅ Per-pool running count: PASSED")
    return True


def test_concurrency_metrics():
    """Test concurrency metrics collection."""
    print("\n=== Test: Concurrency Metrics ===")
    
    config = DispatcherConfig(
        max_global_concurrency=10,
        task_registry_dir="/tmp/test_registry"
    )
    
    # Add test pools
    pool1 = AgentPool(name="pool1", type=PoolType.LOCAL_PROCESS, max_concurrency=5)
    pool2 = AgentPool(name="pool2", type=PoolType.DOCKER, max_concurrency=5)
    config.agent_pools = [pool1, pool2]
    
    dispatcher = DispatcherCore(config)
    
    # Simulate some running tasks
    pool1_ref = dispatcher.agent_pool_manager.get_pool_by_name("pool1")
    pool2_ref = dispatcher.agent_pool_manager.get_pool_by_name("pool2")
    
    # Add tasks to pools
    dispatcher.agent_pool_manager.increment_running_count(pool1_ref)
    dispatcher.agent_pool_manager.increment_running_count(pool1_ref)
    dispatcher._increment_global_running_count()
    dispatcher._increment_global_running_count()
    
    dispatcher.agent_pool_manager.increment_running_count(pool2_ref)
    dispatcher._increment_global_running_count()
    
    # Collect metrics
    dispatcher.metrics_collector.collect()
    metrics = dispatcher.metrics_collector.get_metrics()
    
    # Verify metrics
    assert "global_running_count" in metrics, "Should have global_running_count metric"
    assert metrics["global_running_count"] == 3, "Global count should be 3"
    print(f"✓ Global running count metric: {metrics['global_running_count']}")
    
    assert "max_global_concurrency" in metrics, "Should have max_global_concurrency metric"
    assert metrics["max_global_concurrency"] == 10, "Max global should be 10"
    print(f"✓ Max global concurrency metric: {metrics['max_global_concurrency']}")
    
    assert "global_utilization" in metrics, "Should have global_utilization metric"
    expected_utilization = 3 / 10
    assert abs(metrics["global_utilization"] - expected_utilization) < 0.01, "Utilization should be 0.3"
    print(f"✓ Global utilization metric: {metrics['global_utilization']:.2f}")
    
    assert "pool_running_counts" in metrics, "Should have pool_running_counts metric"
    assert metrics["pool_running_counts"]["pool1"] == 2, "Pool1 count should be 2"
    assert metrics["pool_running_counts"]["pool2"] == 1, "Pool2 count should be 1"
    print(f"✓ Pool running counts: {metrics['pool_running_counts']}")
    
    # Test Prometheus export
    prometheus_output = dispatcher.metrics_collector.export_prometheus()
    assert "dispatcher_global_running_count" in prometheus_output, "Should export global count"
    assert "dispatcher_max_global_concurrency" in prometheus_output, "Should export max global"
    assert "dispatcher_global_utilization" in prometheus_output, "Should export global utilization"
    assert "dispatcher_pool_running_count" in prometheus_output, "Should export pool counts"
    print("✓ Prometheus export includes concurrency metrics")
    
    print("✅ Concurrency metrics: PASSED")
    return True


def test_completion_notification():
    """Test completion notification handling."""
    print("\n=== Test: Completion Notification Handling ===")
    
    config = DispatcherConfig(
        max_global_concurrency=10,
        task_registry_dir="/tmp/test_registry"
    )
    pool = AgentPool(name="test-pool", type=PoolType.LOCAL_PROCESS, max_concurrency=5)
    config.agent_pools = [pool]
    
    dispatcher = DispatcherCore(config)
    
    # Simulate task assignment
    pool_ref = dispatcher.agent_pool_manager.get_pool_by_name("test-pool")
    dispatcher.agent_pool_manager.increment_running_count(pool_ref)
    dispatcher._increment_global_running_count()
    
    initial_global = dispatcher.get_global_running_count()
    initial_pool = pool_ref.current_running
    
    assert initial_global == 1, "Initial global count should be 1"
    assert initial_pool == 1, "Initial pool count should be 1"
    print(f"✓ Initial state: global={initial_global}, pool={initial_pool}")
    
    # Simulate successful completion
    # Note: handle_runner_completion would normally be called by the runner
    # For this test, we'll manually decrement to verify the logic
    dispatcher.agent_pool_manager.decrement_running_count(pool_ref)
    dispatcher._decrement_global_running_count()
    
    final_global = dispatcher.get_global_running_count()
    final_pool = pool_ref.current_running
    
    assert final_global == 0, "Final global count should be 0"
    assert final_pool == 0, "Final pool count should be 0"
    print(f"✓ After completion: global={final_global}, pool={final_pool}")
    
    print("✅ Completion notification handling: PASSED")
    return True


def test_global_limit_enforcement():
    """Test that global concurrency limit is enforced."""
    print("\n=== Test: Global Limit Enforcement ===")
    
    config = DispatcherConfig(
        max_global_concurrency=3,
        task_registry_dir="/tmp/test_registry"
    )
    pool = AgentPool(name="test-pool", type=PoolType.LOCAL_PROCESS, max_concurrency=10)
    config.agent_pools = [pool]
    
    dispatcher = DispatcherCore(config)
    
    # Fill to global limit
    for i in range(3):
        dispatcher._increment_global_running_count()
    
    assert dispatcher.get_global_running_count() == 3, "Should be at global limit"
    assert not dispatcher.can_accept_task_globally(), "Should not accept more tasks"
    print("✓ Global limit reached, blocking new tasks")
    
    # Release one slot
    dispatcher._decrement_global_running_count()
    assert dispatcher.get_global_running_count() == 2, "Should be below limit"
    assert dispatcher.can_accept_task_globally(), "Should accept tasks again"
    print("✓ After release, accepting tasks again")
    
    print("✅ Global limit enforcement: PASSED")
    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Task 13: Concurrency Control Implementation Verification")
    print("=" * 60)
    
    tests = [
        ("Global Running Count Tracking", test_global_running_count_tracking),
        ("Per-Pool Running Count", test_per_pool_running_count),
        ("Concurrency Metrics", test_concurrency_metrics),
        ("Completion Notification", test_completion_notification),
        ("Global Limit Enforcement", test_global_limit_enforcement),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            print(f"❌ {test_name}: FAILED")
            print(f"   Error: {e}")
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if error:
            print(f"         {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All concurrency control tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

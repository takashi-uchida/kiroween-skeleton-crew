#!/usr/bin/env python3
"""
Verification script for Task 10: タスク再試行の実装

Verifies that the retry implementation is working correctly.
"""

import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/Users/takashi/Documents/kiroween-skeleton-crew')

from necrocode.dispatcher.retry_manager import RetryManager


def test_retry_manager():
    """Test RetryManager functionality."""
    print("=" * 70)
    print("Task 10 Verification: Retry Manager")
    print("=" * 70)
    print()
    
    # Test 1: Basic retry counting
    print("Test 1: Basic Retry Counting")
    print("-" * 70)
    manager = RetryManager(max_attempts=3, backoff_base=2.0, initial_delay=0.5)
    
    task_id = "test-task-1"
    manager.record_failure(task_id, "timeout")
    
    count = manager.get_retry_count(task_id)
    print(f"✓ Retry count after first failure: {count}")
    assert count == 1, f"Expected 1, got {count}"
    
    manager.record_failure(task_id, "error")
    count = manager.get_retry_count(task_id)
    print(f"✓ Retry count after second failure: {count}")
    assert count == 2, f"Expected 2, got {count}"
    print()
    
    # Test 2: Exponential backoff
    print("Test 2: Exponential Backoff Calculation")
    print("-" * 70)
    delays = []
    for i in range(1, 6):
        delay = manager._calculate_backoff_delay(i)
        delays.append(delay)
        print(f"✓ Retry {i}: {delay:.2f}s")
    
    # Verify exponential growth
    assert delays[0] == 0.5, "First delay should be initial_delay"
    assert delays[1] == 1.0, "Second delay should be 0.5 * 2^1"
    assert delays[2] == 2.0, "Third delay should be 0.5 * 2^2"
    print()
    
    # Test 3: Max attempts enforcement
    print("Test 3: Max Attempts Enforcement")
    print("-" * 70)
    manager2 = RetryManager(max_attempts=2, initial_delay=0.1)
    
    task_id2 = "test-task-2"
    manager2.record_failure(task_id2, "error")
    time.sleep(0.15)
    
    should_retry = manager2.should_retry(task_id2)
    print(f"✓ After 1 failure, should retry: {should_retry}")
    assert should_retry, "Should retry after 1 failure"
    
    manager2.record_failure(task_id2, "error")
    time.sleep(0.15)
    
    should_retry = manager2.should_retry(task_id2)
    print(f"✓ After 2 failures (max), should retry: {should_retry}")
    assert not should_retry, "Should not retry after max attempts"
    print()
    
    # Test 4: Retry info management
    print("Test 4: Retry Info Management")
    print("-" * 70)
    manager3 = RetryManager()
    
    task_id3 = "test-task-3"
    manager3.record_failure(task_id3, "connection timeout")
    
    info = manager3.get_retry_info(task_id3)
    print(f"✓ Task ID: {info.task_id}")
    print(f"✓ Retry count: {info.retry_count}")
    print(f"✓ Failure reason: {info.failure_reason}")
    print(f"✓ Last retry at: {info.last_retry_at.strftime('%H:%M:%S')}")
    print(f"✓ Next retry at: {info.next_retry_at.strftime('%H:%M:%S')}")
    
    assert info.task_id == task_id3
    assert info.retry_count == 1
    assert info.failure_reason == "connection timeout"
    print()
    
    # Test 5: Clear retry info
    print("Test 5: Clear Retry Info")
    print("-" * 70)
    manager3.clear_retry_info(task_id3)
    
    count = manager3.get_retry_count(task_id3)
    info = manager3.get_retry_info(task_id3)
    
    print(f"✓ Retry count after clear: {count}")
    print(f"✓ Retry info after clear: {info}")
    
    assert count == 0, "Retry count should be 0 after clear"
    assert info is None, "Retry info should be None after clear"
    print()
    
    # Test 6: Multiple tasks
    print("Test 6: Multiple Tasks Management")
    print("-" * 70)
    manager4 = RetryManager(max_attempts=3, initial_delay=0.1)
    
    for i in range(1, 4):
        task_id = f"task-{i}"
        for j in range(i):
            manager4.record_failure(task_id, f"error-{j}")
    
    all_info = manager4.get_all_retry_info()
    print(f"✓ Total tasks with retry info: {len(all_info)}")
    
    for task_id, info in all_info.items():
        print(f"  - {task_id}: {info.retry_count} retries")
    
    assert len(all_info) == 3, "Should have 3 tasks"
    assert all_info["task-1"].retry_count == 1
    assert all_info["task-2"].retry_count == 2
    assert all_info["task-3"].retry_count == 3
    print()
    
    # Test 7: Backoff timing
    print("Test 7: Backoff Timing Enforcement")
    print("-" * 70)
    manager5 = RetryManager(max_attempts=3, initial_delay=0.2)
    
    task_id5 = "test-task-5"
    manager5.record_failure(task_id5, "timeout")
    
    # Immediately after failure, should not retry (backoff not elapsed)
    should_retry = manager5.should_retry(task_id5)
    print(f"✓ Immediately after failure, should retry: {should_retry}")
    assert not should_retry, "Should not retry immediately (backoff not elapsed)"
    
    # Wait for backoff
    print("  Waiting for backoff delay...")
    time.sleep(0.3)
    
    should_retry = manager5.should_retry(task_id5)
    print(f"✓ After backoff delay, should retry: {should_retry}")
    assert should_retry, "Should retry after backoff elapsed"
    print()
    
    print("=" * 70)
    print("All Tests Passed! ✓")
    print("=" * 70)
    print()
    print("Task 10 Implementation Verified:")
    print("  ✓ 10.1: Retry counter management")
    print("  ✓ 10.2: Retry logic (failure notification, checks, state transitions)")
    print("  ✓ 10.3: Exponential backoff")
    print()


if __name__ == "__main__":
    try:
        test_retry_manager()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

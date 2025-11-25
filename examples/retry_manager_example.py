"""
Example: RetryManager Usage

Demonstrates task retry management with exponential backoff.
"""

import time
from datetime import datetime

from necrocode.dispatcher.retry_manager import RetryManager


def main():
    """Demonstrate RetryManager functionality."""
    
    print("=" * 60)
    print("RetryManager Example")
    print("=" * 60)
    print()
    
    # Initialize RetryManager
    print("1. Initialize RetryManager")
    print("-" * 60)
    manager = RetryManager(
        max_attempts=3,
        backoff_base=2.0,
        initial_delay=1.0,
        max_delay=60.0
    )
    print(f"Max attempts: {manager.max_attempts}")
    print(f"Backoff base: {manager.backoff_base}")
    print(f"Initial delay: {manager.initial_delay}s")
    print(f"Max delay: {manager.max_delay}s")
    print()
    
    # Simulate task failures
    print("2. Simulate Task Failures")
    print("-" * 60)
    
    task_id = "task-123"
    
    # First failure
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Task {task_id} failed (attempt 1)")
    manager.record_failure(task_id, "connection timeout")
    
    retry_count = manager.get_retry_count(task_id)
    retry_info = manager.get_retry_info(task_id)
    
    print(f"  Retry count: {retry_count}/{manager.max_attempts}")
    print(f"  Failure reason: {retry_info.failure_reason}")
    print(f"  Next retry at: {retry_info.next_retry_at.strftime('%H:%M:%S')}")
    print(f"  Should retry: {manager.should_retry(task_id)}")
    
    # Wait for backoff
    print(f"\n  Waiting for backoff delay...")
    time.sleep(1.5)
    
    print(f"  Should retry now: {manager.should_retry(task_id)}")
    
    # Second failure
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Task {task_id} failed (attempt 2)")
    manager.record_failure(task_id, "database error")
    
    retry_count = manager.get_retry_count(task_id)
    retry_info = manager.get_retry_info(task_id)
    
    print(f"  Retry count: {retry_count}/{manager.max_attempts}")
    print(f"  Failure reason: {retry_info.failure_reason}")
    print(f"  Next retry at: {retry_info.next_retry_at.strftime('%H:%M:%S')}")
    print(f"  Backoff delay: ~2.0s (exponential)")
    
    # Wait for backoff
    print(f"\n  Waiting for backoff delay...")
    time.sleep(2.5)
    
    # Third failure
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Task {task_id} failed (attempt 3)")
    manager.record_failure(task_id, "service unavailable")
    
    retry_count = manager.get_retry_count(task_id)
    retry_info = manager.get_retry_info(task_id)
    
    print(f"  Retry count: {retry_count}/{manager.max_attempts}")
    print(f"  Failure reason: {retry_info.failure_reason}")
    print(f"  Should retry: {manager.should_retry(task_id)}")
    print(f"  Status: MAX RETRIES REACHED - Task should be marked as FAILED")
    print()
    
    # Demonstrate exponential backoff calculation
    print("3. Exponential Backoff Calculation")
    print("-" * 60)
    print("\nBackoff delays for different retry counts:")
    for i in range(1, 8):
        delay = manager._calculate_backoff_delay(i)
        print(f"  Retry {i}: {delay:.2f}s")
    print()
    
    # Demonstrate multiple tasks
    print("4. Multiple Tasks with Different Retry States")
    print("-" * 60)
    
    manager2 = RetryManager(max_attempts=3, initial_delay=0.5)
    
    # Task 1: 1 failure
    manager2.record_failure("task-1", "timeout")
    
    # Task 2: 2 failures
    manager2.record_failure("task-2", "error")
    time.sleep(0.6)
    manager2.record_failure("task-2", "error")
    
    # Task 3: 3 failures (max reached)
    manager2.record_failure("task-3", "crash")
    time.sleep(0.6)
    manager2.record_failure("task-3", "crash")
    time.sleep(0.6)
    manager2.record_failure("task-3", "crash")
    
    print("\nRetry status for all tasks:")
    all_info = manager2.get_all_retry_info()
    for task_id, info in all_info.items():
        should_retry = manager2.should_retry(task_id)
        status = "READY FOR RETRY" if should_retry else "MAX RETRIES REACHED"
        print(f"  {task_id}: {info.retry_count} retries - {status}")
    
    # Wait for backoff
    time.sleep(1.0)
    
    print("\nTasks ready for retry after backoff:")
    ready_tasks = manager2.get_tasks_ready_for_retry()
    for task_id in ready_tasks:
        print(f"  - {task_id}")
    print()
    
    # Demonstrate successful task completion
    print("5. Task Success - Clear Retry Info")
    print("-" * 60)
    
    task_id = "task-success"
    manager2.record_failure(task_id, "temporary error")
    print(f"\nTask {task_id} failed once")
    print(f"  Retry count: {manager2.get_retry_count(task_id)}")
    
    # Simulate successful retry
    print(f"\nTask {task_id} succeeded on retry")
    manager2.clear_retry_info(task_id)
    print(f"  Retry count after success: {manager2.get_retry_count(task_id)}")
    print(f"  Retry info cleared: {manager2.get_retry_info(task_id) is None}")
    print()
    
    # Demonstrate retry info serialization
    print("6. Retry Info Serialization")
    print("-" * 60)
    
    manager3 = RetryManager()
    manager3.record_failure("task-serialize", "network error")
    
    info = manager3.get_retry_info("task-serialize")
    data = info.to_dict()
    
    print("\nSerialized retry info:")
    for key, value in data.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

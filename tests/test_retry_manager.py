"""
Tests for RetryManager

Tests retry counting, exponential backoff, and retry eligibility logic.
"""

import pytest
import time
from datetime import datetime, timedelta

from necrocode.dispatcher.retry_manager import RetryManager, RetryInfo


class TestRetryManager:
    """Test RetryManager functionality."""
    
    def test_initialization(self):
        """Test RetryManager initialization."""
        manager = RetryManager(
            max_attempts=3,
            backoff_base=2.0,
            initial_delay=1.0,
            max_delay=300.0
        )
        
        assert manager.max_attempts == 3
        assert manager.backoff_base == 2.0
        assert manager.initial_delay == 1.0
        assert manager.max_delay == 300.0
    
    def test_get_retry_count_new_task(self):
        """Test getting retry count for a new task."""
        manager = RetryManager()
        
        count = manager.get_retry_count("task-1")
        assert count == 0
    
    def test_record_failure_increments_count(self):
        """Test that recording failure increments retry count."""
        manager = RetryManager(max_attempts=3)
        
        manager.record_failure("task-1", "timeout")
        assert manager.get_retry_count("task-1") == 1
        
        manager.record_failure("task-1", "error")
        assert manager.get_retry_count("task-1") == 2
        
        manager.record_failure("task-1", "crash")
        assert manager.get_retry_count("task-1") == 3
    
    def test_should_retry_below_max_attempts(self):
        """Test that tasks below max attempts should be retried."""
        manager = RetryManager(max_attempts=3, initial_delay=0.1)
        
        # First failure
        manager.record_failure("task-1", "error")
        time.sleep(0.2)  # Wait for backoff
        assert manager.should_retry("task-1") is True
        
        # Second failure
        manager.record_failure("task-1", "error")
        time.sleep(0.3)  # Wait for backoff
        assert manager.should_retry("task-1") is True
    
    def test_should_not_retry_at_max_attempts(self):
        """Test that tasks at max attempts should not be retried."""
        manager = RetryManager(max_attempts=2)
        
        manager.record_failure("task-1", "error")
        manager.record_failure("task-1", "error")
        
        assert manager.get_retry_count("task-1") == 2
        assert manager.should_retry("task-1") is False
    
    def test_should_not_retry_during_backoff(self):
        """Test that tasks should not retry during backoff period."""
        manager = RetryManager(max_attempts=3, initial_delay=10.0)
        
        manager.record_failure("task-1", "error")
        
        # Immediately after failure, should not retry (backoff not elapsed)
        assert manager.should_retry("task-1") is False
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        manager = RetryManager(
            max_attempts=5,
            backoff_base=2.0,
            initial_delay=1.0,
            max_delay=100.0
        )
        
        # Test backoff delays
        assert manager._calculate_backoff_delay(0) == 1.0  # initial
        assert manager._calculate_backoff_delay(1) == 1.0  # 1 * 2^0
        assert manager._calculate_backoff_delay(2) == 2.0  # 1 * 2^1
        assert manager._calculate_backoff_delay(3) == 4.0  # 1 * 2^2
        assert manager._calculate_backoff_delay(4) == 8.0  # 1 * 2^3
        assert manager._calculate_backoff_delay(5) == 16.0  # 1 * 2^4
    
    def test_exponential_backoff_max_delay(self):
        """Test that backoff delay is capped at max_delay."""
        manager = RetryManager(
            max_attempts=10,
            backoff_base=2.0,
            initial_delay=1.0,
            max_delay=10.0
        )
        
        # Large retry count should be capped
        assert manager._calculate_backoff_delay(10) == 10.0
        assert manager._calculate_backoff_delay(20) == 10.0
    
    def test_get_retry_info(self):
        """Test getting retry information."""
        manager = RetryManager()
        
        # No info for new task
        assert manager.get_retry_info("task-1") is None
        
        # Record failure
        manager.record_failure("task-1", "timeout")
        
        # Get info
        info = manager.get_retry_info("task-1")
        assert info is not None
        assert info.task_id == "task-1"
        assert info.retry_count == 1
        assert info.failure_reason == "timeout"
        assert info.last_retry_at is not None
        assert info.next_retry_at is not None
    
    def test_clear_retry_info(self):
        """Test clearing retry information."""
        manager = RetryManager()
        
        manager.record_failure("task-1", "error")
        assert manager.get_retry_count("task-1") == 1
        
        manager.clear_retry_info("task-1")
        assert manager.get_retry_count("task-1") == 0
        assert manager.get_retry_info("task-1") is None
    
    def test_get_all_retry_info(self):
        """Test getting all retry information."""
        manager = RetryManager()
        
        manager.record_failure("task-1", "error")
        manager.record_failure("task-2", "timeout")
        manager.record_failure("task-3", "crash")
        
        all_info = manager.get_all_retry_info()
        assert len(all_info) == 3
        assert "task-1" in all_info
        assert "task-2" in all_info
        assert "task-3" in all_info
    
    def test_get_tasks_ready_for_retry(self):
        """Test getting tasks ready for retry."""
        manager = RetryManager(max_attempts=3, initial_delay=0.1)
        
        # Record failures
        manager.record_failure("task-1", "error")
        manager.record_failure("task-2", "error")
        manager.record_failure("task-3", "error")
        
        # Immediately after, no tasks ready (backoff not elapsed)
        ready = manager.get_tasks_ready_for_retry()
        assert len(ready) == 0
        
        # Wait for backoff
        time.sleep(0.2)
        
        # Now all tasks should be ready
        ready = manager.get_tasks_ready_for_retry()
        assert len(ready) == 3
        assert "task-1" in ready
        assert "task-2" in ready
        assert "task-3" in ready
    
    def test_get_tasks_ready_excludes_max_attempts(self):
        """Test that tasks at max attempts are excluded from ready list."""
        manager = RetryManager(max_attempts=2, initial_delay=0.1)
        
        # Task 1: 1 failure (should be ready)
        manager.record_failure("task-1", "error")
        
        # Task 2: 2 failures (should not be ready - at max)
        manager.record_failure("task-2", "error")
        manager.record_failure("task-2", "error")
        
        # Wait for backoff
        time.sleep(0.2)
        
        ready = manager.get_tasks_ready_for_retry()
        assert len(ready) == 1
        assert "task-1" in ready
        assert "task-2" not in ready
    
    def test_retry_info_serialization(self):
        """Test RetryInfo serialization."""
        now = datetime.now()
        info = RetryInfo(
            task_id="task-1",
            retry_count=2,
            last_retry_at=now,
            next_retry_at=now + timedelta(seconds=10),
            failure_reason="timeout"
        )
        
        data = info.to_dict()
        assert data["task_id"] == "task-1"
        assert data["retry_count"] == 2
        assert data["last_retry_at"] == now.isoformat()
        assert data["next_retry_at"] == (now + timedelta(seconds=10)).isoformat()
        assert data["failure_reason"] == "timeout"
    
    def test_multiple_failures_same_task(self):
        """Test multiple failures for the same task."""
        manager = RetryManager(max_attempts=5, initial_delay=0.1)
        
        # Record multiple failures
        for i in range(3):
            manager.record_failure("task-1", f"error-{i}")
            time.sleep(0.15)  # Wait for backoff
        
        assert manager.get_retry_count("task-1") == 3
        
        info = manager.get_retry_info("task-1")
        assert info.failure_reason == "error-2"  # Last failure reason
    
    def test_different_backoff_bases(self):
        """Test different backoff base values."""
        # Base 2
        manager2 = RetryManager(backoff_base=2.0, initial_delay=1.0)
        assert manager2._calculate_backoff_delay(3) == 4.0  # 1 * 2^2
        
        # Base 3
        manager3 = RetryManager(backoff_base=3.0, initial_delay=1.0)
        assert manager3._calculate_backoff_delay(3) == 9.0  # 1 * 3^2
        
        # Base 1.5
        manager15 = RetryManager(backoff_base=1.5, initial_delay=1.0)
        assert manager15._calculate_backoff_delay(3) == 2.25  # 1 * 1.5^2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

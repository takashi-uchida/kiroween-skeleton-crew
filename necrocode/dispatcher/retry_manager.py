"""
RetryManager - Manages task retry logic with exponential backoff

Tracks retry counts, calculates backoff intervals, and determines
whether tasks should be retried or marked as failed.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from necrocode.task_registry.models import Task


logger = logging.getLogger(__name__)


@dataclass
class RetryInfo:
    """
    Information about task retry attempts.
    
    Tracks the number of retries, last retry time, and next retry time
    for exponential backoff.
    """
    task_id: str
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "retry_count": self.retry_count,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "failure_reason": self.failure_reason,
        }


class RetryManager:
    """
    Manages task retry logic with exponential backoff.
    
    Tracks retry counts for tasks, calculates exponential backoff intervals,
    and determines whether tasks should be retried or marked as failed.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 300.0
    ):
        """
        Initialize RetryManager.
        
        Args:
            max_attempts: Maximum number of retry attempts
            backoff_base: Base for exponential backoff calculation
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            
        Requirements: 9.2, 9.5
        """
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        
        # Track retry information for each task
        self._retry_info: Dict[str, RetryInfo] = {}
        
        logger.info(
            f"RetryManager initialized: max_attempts={max_attempts}, "
            f"backoff_base={backoff_base}, initial_delay={initial_delay}s, "
            f"max_delay={max_delay}s"
        )
    
    def get_retry_count(self, task_id: str) -> int:
        """
        Get the current retry count for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Number of retry attempts made
            
        Requirements: 9.2
        """
        if task_id in self._retry_info:
            return self._retry_info[task_id].retry_count
        return 0
    
    def should_retry(self, task_id: str) -> bool:
        """
        Check if a task should be retried.
        
        A task should be retried if:
        1. Retry count is below max_attempts
        2. Enough time has passed since last retry (for exponential backoff)
        
        Args:
            task_id: Task ID
            
        Returns:
            True if task should be retried, False otherwise
            
        Requirements: 9.3, 9.5
        """
        retry_count = self.get_retry_count(task_id)
        
        # Check if max attempts reached
        if retry_count >= self.max_attempts:
            logger.info(
                f"Task {task_id} has reached max retry attempts "
                f"({retry_count}/{self.max_attempts})"
            )
            return False
        
        # Check if enough time has passed for exponential backoff
        if task_id in self._retry_info:
            retry_info = self._retry_info[task_id]
            if retry_info.next_retry_at:
                now = datetime.now()
                if now < retry_info.next_retry_at:
                    wait_seconds = (retry_info.next_retry_at - now).total_seconds()
                    logger.debug(
                        f"Task {task_id} must wait {wait_seconds:.1f}s before retry"
                    )
                    return False
        
        return True
    
    def record_failure(
        self,
        task_id: str,
        failure_reason: Optional[str] = None
    ) -> None:
        """
        Record a task failure and update retry information.
        
        Increments retry count and calculates next retry time using
        exponential backoff.
        
        Args:
            task_id: Task ID
            failure_reason: Optional reason for failure
            
        Requirements: 9.1, 9.2, 9.5
        """
        now = datetime.now()
        
        if task_id not in self._retry_info:
            self._retry_info[task_id] = RetryInfo(task_id=task_id)
        
        retry_info = self._retry_info[task_id]
        retry_info.retry_count += 1
        retry_info.last_retry_at = now
        retry_info.failure_reason = failure_reason
        
        # Calculate next retry time with exponential backoff
        delay = self._calculate_backoff_delay(retry_info.retry_count)
        retry_info.next_retry_at = now + timedelta(seconds=delay)
        
        logger.info(
            f"Recorded failure for task {task_id}: "
            f"retry_count={retry_info.retry_count}/{self.max_attempts}, "
            f"next_retry_at={retry_info.next_retry_at.isoformat()}, "
            f"delay={delay:.1f}s"
        )
        
        if failure_reason:
            logger.debug(f"Failure reason for task {task_id}: {failure_reason}")
    
    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Formula: delay = initial_delay * (backoff_base ^ (retry_count - 1))
        Capped at max_delay.
        
        Args:
            retry_count: Current retry count (1-indexed)
            
        Returns:
            Delay in seconds before next retry
            
        Requirements: 9.5
        """
        if retry_count <= 0:
            return self.initial_delay
        
        # Calculate exponential backoff
        delay = self.initial_delay * (self.backoff_base ** (retry_count - 1))
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        logger.debug(
            f"Calculated backoff delay for retry {retry_count}: {delay:.1f}s "
            f"(base={self.backoff_base}, initial={self.initial_delay}s)"
        )
        
        return delay
    
    def get_retry_info(self, task_id: str) -> Optional[RetryInfo]:
        """
        Get retry information for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            RetryInfo if task has retry history, None otherwise
        """
        return self._retry_info.get(task_id)
    
    def clear_retry_info(self, task_id: str) -> None:
        """
        Clear retry information for a task.
        
        Called when a task completes successfully or is permanently failed.
        
        Args:
            task_id: Task ID
        """
        if task_id in self._retry_info:
            del self._retry_info[task_id]
            logger.debug(f"Cleared retry info for task {task_id}")
    
    def get_all_retry_info(self) -> Dict[str, RetryInfo]:
        """
        Get retry information for all tasks.
        
        Returns:
            Dictionary mapping task IDs to RetryInfo
        """
        return self._retry_info.copy()
    
    def get_tasks_ready_for_retry(self) -> list[str]:
        """
        Get list of task IDs that are ready for retry.
        
        Returns tasks that:
        1. Have not exceeded max retry attempts
        2. Have passed their exponential backoff delay
        
        Returns:
            List of task IDs ready for retry
        """
        ready_tasks = []
        now = datetime.now()
        
        for task_id, retry_info in self._retry_info.items():
            # Check if max attempts reached
            if retry_info.retry_count >= self.max_attempts:
                continue
            
            # Check if backoff delay has passed
            if retry_info.next_retry_at and now < retry_info.next_retry_at:
                continue
            
            ready_tasks.append(task_id)
        
        return ready_tasks

"""
Task Queue implementation for the Dispatcher component.

Provides a thread-safe priority queue for managing tasks awaiting execution.
"""

import threading
from queue import PriorityQueue, Empty
from typing import Optional, List, Tuple
from datetime import datetime

from necrocode.task_registry.models import Task


class TaskQueue:
    """
    Thread-safe priority queue for tasks.
    
    Tasks are ordered by:
    1. Priority (higher priority first)
    2. Creation time (older tasks first for same priority - FIFO)
    
    Requirements: 1.3, 1.5
    """
    
    def __init__(self):
        """Initialize the task queue."""
        self._queue: PriorityQueue = PriorityQueue()
        self._lock = threading.Lock()
        self._counter = 0  # Monotonic counter for FIFO ordering within same priority
    
    def enqueue(self, task: Task) -> None:
        """
        Add a task to the queue.
        
        Tasks are prioritized by:
        - Higher priority value = higher priority (processed first)
        - Same priority = FIFO order (older tasks first)
        
        Args:
            task: Task to add to the queue
            
        Requirements: 1.3, 1.5
        """
        with self._lock:
            # Negate priority so higher values come first (PriorityQueue is min-heap)
            priority = -task.priority
            
            # Use counter for FIFO ordering within same priority
            # Use task creation time as secondary sort key
            timestamp = task.created_at.timestamp()
            
            # Increment counter for tie-breaking
            self._counter += 1
            
            # Tuple: (priority, timestamp, counter, task)
            # PriorityQueue will sort by these in order
            self._queue.put((priority, timestamp, self._counter, task))
    
    def dequeue(self) -> Optional[Task]:
        """
        Remove and return the highest priority task from the queue.
        
        Returns:
            The highest priority task, or None if queue is empty
            
        Requirements: 1.3, 1.5
        """
        with self._lock:
            if self._queue.empty():
                return None
            
            try:
                _, _, _, task = self._queue.get_nowait()
                return task
            except Empty:
                return None
    
    def peek(self) -> Optional[Task]:
        """
        View the highest priority task without removing it.
        
        Returns:
            The highest priority task, or None if queue is empty
            
        Requirements: 1.3
        """
        with self._lock:
            if self._queue.empty():
                return None
            
            # Get all items, peek at first, then put them all back
            items: List[Tuple[int, float, int, Task]] = []
            result_task: Optional[Task] = None
            
            try:
                # Drain the queue
                while not self._queue.empty():
                    item = self._queue.get_nowait()
                    items.append(item)
                
                # First item is the highest priority
                if items:
                    result_task = items[0][3]
                
                # Put everything back
                for item in items:
                    self._queue.put(item)
                
                return result_task
            except Empty:
                # Restore items if something went wrong
                for item in items:
                    self._queue.put(item)
                return None
    
    def size(self) -> int:
        """
        Get the number of tasks in the queue.
        
        Returns:
            Number of tasks currently in the queue
            
        Requirements: 1.3
        """
        return self._queue.qsize()
    
    def clear(self) -> None:
        """
        Remove all tasks from the queue.
        
        Requirements: 1.3
        """
        with self._lock:
            # Create a new empty queue
            self._queue = PriorityQueue()
            self._counter = 0
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            True if queue is empty, False otherwise
        """
        return self._queue.empty()
    
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks in the queue without removing them.
        
        Returns:
            List of all tasks in priority order
            
        Note: This is a utility method for inspection/debugging.
        """
        with self._lock:
            items: List[Tuple[int, float, int, Task]] = []
            
            try:
                # Drain the queue
                while not self._queue.empty():
                    item = self._queue.get_nowait()
                    items.append(item)
                
                # Extract tasks in priority order
                tasks = [item[3] for item in items]
                
                # Put everything back
                for item in items:
                    self._queue.put(item)
                
                return tasks
            except Empty:
                # Restore items if something went wrong
                for item in items:
                    self._queue.put(item)
                return []

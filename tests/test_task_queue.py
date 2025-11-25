"""
Unit tests for TaskQueue.

Tests priority queue operations, thread safety, and FIFO ordering.
"""

import pytest
import threading
import time
from datetime import datetime, timedelta

from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.task_registry.models import Task, TaskState


@pytest.fixture
def task_queue():
    """Create a fresh TaskQueue instance."""
    return TaskQueue()


@pytest.fixture
def sample_tasks():
    """Create sample tasks with different priorities."""
    base_time = datetime.now()
    
    return [
        Task(
            id="1",
            title="Low priority task",
            description="Test task",
            state=TaskState.READY,
            priority=1,
            created_at=base_time,
        ),
        Task(
            id="2",
            title="High priority task",
            description="Test task",
            state=TaskState.READY,
            priority=10,
            created_at=base_time + timedelta(seconds=1),
        ),
        Task(
            id="3",
            title="Medium priority task",
            description="Test task",
            state=TaskState.READY,
            priority=5,
            created_at=base_time + timedelta(seconds=2),
        ),
        Task(
            id="4",
            title="Another high priority task",
            description="Test task",
            state=TaskState.READY,
            priority=10,
            created_at=base_time + timedelta(seconds=3),
        ),
    ]


def test_enqueue_dequeue(task_queue, sample_tasks):
    """Test basic enqueue and dequeue operations."""
    task = sample_tasks[0]
    
    # Enqueue a task
    task_queue.enqueue(task)
    assert task_queue.size() == 1
    
    # Dequeue the task
    dequeued = task_queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == task.id
    assert task_queue.size() == 0


def test_priority_ordering(task_queue, sample_tasks):
    """Test that tasks are dequeued in priority order."""
    # Enqueue tasks in random order
    for task in sample_tasks:
        task_queue.enqueue(task)
    
    # Dequeue should return highest priority first (priority=10)
    first = task_queue.dequeue()
    assert first is not None
    assert first.priority == 10
    assert first.id == "2"  # Older of the two priority=10 tasks
    
    # Second should be the other priority=10 task
    second = task_queue.dequeue()
    assert second is not None
    assert second.priority == 10
    assert second.id == "4"
    
    # Third should be priority=5
    third = task_queue.dequeue()
    assert third is not None
    assert third.priority == 5
    assert third.id == "3"
    
    # Last should be priority=1
    fourth = task_queue.dequeue()
    assert fourth is not None
    assert fourth.priority == 1
    assert fourth.id == "1"


def test_fifo_within_same_priority(task_queue):
    """Test FIFO ordering for tasks with same priority."""
    base_time = datetime.now()
    
    tasks = [
        Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=base_time + timedelta(seconds=i),
        )
        for i in range(5)
    ]
    
    # Enqueue all tasks
    for task in tasks:
        task_queue.enqueue(task)
    
    # Dequeue should return in FIFO order (oldest first)
    for i in range(5):
        dequeued = task_queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == f"task-{i}"


def test_peek(task_queue, sample_tasks):
    """Test peek operation doesn't remove tasks."""
    task_queue.enqueue(sample_tasks[0])
    task_queue.enqueue(sample_tasks[1])
    
    # Peek should return highest priority without removing
    peeked = task_queue.peek()
    assert peeked is not None
    assert peeked.id == sample_tasks[1].id
    assert task_queue.size() == 2
    
    # Peek again should return same task
    peeked_again = task_queue.peek()
    assert peeked_again is not None
    assert peeked_again.id == peeked.id


def test_size(task_queue, sample_tasks):
    """Test size tracking."""
    assert task_queue.size() == 0
    
    task_queue.enqueue(sample_tasks[0])
    assert task_queue.size() == 1
    
    task_queue.enqueue(sample_tasks[1])
    assert task_queue.size() == 2
    
    task_queue.dequeue()
    assert task_queue.size() == 1
    
    task_queue.dequeue()
    assert task_queue.size() == 0


def test_clear(task_queue, sample_tasks):
    """Test clearing the queue."""
    for task in sample_tasks:
        task_queue.enqueue(task)
    
    assert task_queue.size() == len(sample_tasks)
    
    task_queue.clear()
    assert task_queue.size() == 0
    assert task_queue.is_empty()


def test_is_empty(task_queue, sample_tasks):
    """Test empty check."""
    assert task_queue.is_empty()
    
    task_queue.enqueue(sample_tasks[0])
    assert not task_queue.is_empty()
    
    task_queue.dequeue()
    assert task_queue.is_empty()


def test_dequeue_empty_queue(task_queue):
    """Test dequeuing from empty queue returns None."""
    assert task_queue.dequeue() is None


def test_peek_empty_queue(task_queue):
    """Test peeking at empty queue returns None."""
    assert task_queue.peek() is None


def test_get_all_tasks(task_queue, sample_tasks):
    """Test getting all tasks without removing them."""
    for task in sample_tasks:
        task_queue.enqueue(task)
    
    all_tasks = task_queue.get_all_tasks()
    assert len(all_tasks) == len(sample_tasks)
    assert task_queue.size() == len(sample_tasks)  # Tasks still in queue
    
    # Should be in priority order
    assert all_tasks[0].priority == 10
    assert all_tasks[1].priority == 10
    assert all_tasks[2].priority == 5
    assert all_tasks[3].priority == 1


def test_thread_safety(task_queue):
    """Test thread-safe operations."""
    num_threads = 10
    tasks_per_thread = 10
    
    def enqueue_tasks(thread_id):
        for i in range(tasks_per_thread):
            task = Task(
                id=f"thread-{thread_id}-task-{i}",
                title=f"Task {i}",
                description="Test",
                state=TaskState.READY,
                priority=thread_id,
                created_at=datetime.now(),
            )
            task_queue.enqueue(task)
    
    # Start multiple threads enqueueing tasks
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=enqueue_tasks, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Should have all tasks
    assert task_queue.size() == num_threads * tasks_per_thread
    
    # Dequeue all tasks
    dequeued_count = 0
    while not task_queue.is_empty():
        task = task_queue.dequeue()
        if task:
            dequeued_count += 1
    
    assert dequeued_count == num_threads * tasks_per_thread


def test_concurrent_enqueue_dequeue(task_queue):
    """Test concurrent enqueue and dequeue operations."""
    num_producers = 5
    num_consumers = 3
    tasks_per_producer = 20
    
    enqueued_ids = []
    dequeued_ids = []
    lock = threading.Lock()
    
    def producer(producer_id):
        for i in range(tasks_per_producer):
            task = Task(
                id=f"producer-{producer_id}-task-{i}",
                title=f"Task {i}",
                description="Test",
                state=TaskState.READY,
                priority=i % 5,
                created_at=datetime.now(),
            )
            task_queue.enqueue(task)
            with lock:
                enqueued_ids.append(task.id)
            time.sleep(0.001)  # Small delay
    
    def consumer():
        while True:
            task = task_queue.dequeue()
            if task:
                with lock:
                    dequeued_ids.append(task.id)
            else:
                time.sleep(0.01)  # Wait if queue is empty
            
            # Check if we're done
            with lock:
                if len(dequeued_ids) >= num_producers * tasks_per_producer:
                    break
    
    # Start producers
    producer_threads = []
    for i in range(num_producers):
        thread = threading.Thread(target=producer, args=(i,))
        producer_threads.append(thread)
        thread.start()
    
    # Start consumers
    consumer_threads = []
    for _ in range(num_consumers):
        thread = threading.Thread(target=consumer)
        consumer_threads.append(thread)
        thread.start()
    
    # Wait for producers to finish
    for thread in producer_threads:
        thread.join()
    
    # Wait for consumers to finish
    for thread in consumer_threads:
        thread.join(timeout=5)
    
    # All enqueued tasks should be dequeued
    assert len(dequeued_ids) == len(enqueued_ids)
    assert set(dequeued_ids) == set(enqueued_ids)

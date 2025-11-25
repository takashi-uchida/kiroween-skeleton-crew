"""
Example usage of TaskQueue for the Dispatcher component.

Demonstrates priority-based task queuing with FIFO ordering within same priority.
"""

from datetime import datetime, timedelta
from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.task_registry.models import Task, TaskState


def main():
    """Demonstrate TaskQueue operations."""
    print("=== TaskQueue Example ===\n")
    
    # Create a task queue
    queue = TaskQueue()
    
    # Create sample tasks with different priorities
    base_time = datetime.now()
    tasks = [
        Task(
            id="1",
            title="Setup database schema",
            description="Create User and Message models",
            state=TaskState.READY,
            priority=5,
            created_at=base_time,
        ),
        Task(
            id="2",
            title="Critical security fix",
            description="Patch authentication vulnerability",
            state=TaskState.READY,
            priority=10,  # High priority
            created_at=base_time + timedelta(seconds=1),
        ),
        Task(
            id="3",
            title="Update documentation",
            description="Add API documentation",
            state=TaskState.READY,
            priority=1,  # Low priority
            created_at=base_time + timedelta(seconds=2),
        ),
        Task(
            id="4",
            title="Another critical fix",
            description="Fix data corruption bug",
            state=TaskState.READY,
            priority=10,  # High priority (same as task 2)
            created_at=base_time + timedelta(seconds=3),
        ),
        Task(
            id="5",
            title="Implement JWT auth",
            description="Add login/register endpoints",
            state=TaskState.READY,
            priority=5,  # Medium priority (same as task 1)
            created_at=base_time + timedelta(seconds=4),
        ),
    ]
    
    # Enqueue tasks
    print("Enqueueing tasks:")
    for task in tasks:
        queue.enqueue(task)
        print(f"  - Task {task.id}: {task.title} (priority={task.priority})")
    
    print(f"\nQueue size: {queue.size()}")
    
    # Peek at highest priority task
    print("\nPeeking at highest priority task:")
    peeked = queue.peek()
    if peeked:
        print(f"  - Task {peeked.id}: {peeked.title} (priority={peeked.priority})")
    print(f"Queue size after peek: {queue.size()}")
    
    # Dequeue tasks in priority order
    print("\nDequeuing tasks in priority order:")
    while not queue.is_empty():
        task = queue.dequeue()
        if task:
            print(f"  - Task {task.id}: {task.title} (priority={task.priority})")
    
    print(f"\nQueue size after dequeuing all: {queue.size()}")
    
    # Demonstrate FIFO within same priority
    print("\n=== FIFO Ordering Demo ===")
    queue.clear()
    
    # Add multiple tasks with same priority
    same_priority_tasks = [
        Task(
            id=f"task-{i}",
            title=f"Task {i}",
            description="Test task",
            state=TaskState.READY,
            priority=5,
            created_at=base_time + timedelta(seconds=i),
        )
        for i in range(5)
    ]
    
    print("\nEnqueueing tasks with same priority (5):")
    for task in same_priority_tasks:
        queue.enqueue(task)
        print(f"  - {task.id} (created at {task.created_at.strftime('%H:%M:%S.%f')})")
    
    print("\nDequeuing (should be in FIFO order):")
    while not queue.is_empty():
        task = queue.dequeue()
        if task:
            print(f"  - {task.id}")
    
    # Demonstrate thread-safe operations
    print("\n=== Thread Safety Demo ===")
    queue.clear()
    
    import threading
    
    def enqueue_tasks(thread_id, count):
        for i in range(count):
            task = Task(
                id=f"thread-{thread_id}-task-{i}",
                title=f"Task from thread {thread_id}",
                description="Test",
                state=TaskState.READY,
                priority=thread_id,
                created_at=datetime.now(),
            )
            queue.enqueue(task)
    
    # Start multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=enqueue_tasks, args=(i, 5))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    print(f"\nEnqueued {queue.size()} tasks from 3 threads")
    print("All tasks in queue (by priority):")
    all_tasks = queue.get_all_tasks()
    for task in all_tasks:
        print(f"  - {task.id} (priority={task.priority})")


if __name__ == "__main__":
    main()

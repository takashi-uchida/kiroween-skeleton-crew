"""
Example demonstrating the Dispatcher Scheduler component.

This example shows how to use different scheduling policies to assign tasks
to Agent Pools.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.dispatcher.scheduler import Scheduler
from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.dispatcher.models import (
    AgentPool,
    PoolType,
    SchedulingPolicy,
)
from necrocode.task_registry.models import Task, TaskState


class MockAgentPoolManager:
    """Mock Agent Pool Manager for demonstration."""
    
    def __init__(self):
        self.pools = {
            "local": AgentPool(
                name="local",
                type=PoolType.LOCAL_PROCESS,
                max_concurrency=2,
                current_running=0,
                enabled=True,
            ),
            "docker": AgentPool(
                name="docker",
                type=PoolType.DOCKER,
                max_concurrency=4,
                current_running=1,
                enabled=True,
            ),
            "k8s": AgentPool(
                name="k8s",
                type=PoolType.KUBERNETES,
                max_concurrency=10,
                current_running=3,
                enabled=True,
            ),
        }
        
        # Skill mapping
        self.skill_mapping = {
            "backend": ["docker", "k8s"],
            "frontend": ["docker", "k8s"],
            "database": ["docker"],
            "devops": ["k8s"],
        }
    
    def can_accept_task(self, pool: AgentPool) -> bool:
        """Check if pool can accept a task."""
        return pool.can_accept_task()
    
    def get_pool_for_skill(self, skill: str) -> AgentPool:
        """Get pool for a specific skill."""
        pool_names = self.skill_mapping.get(skill, [])
        if not pool_names:
            return self.get_default_pool()
        
        # Return least loaded pool
        available_pools = [self.pools[name] for name in pool_names if name in self.pools]
        if not available_pools:
            return self.get_default_pool()
        
        return min(available_pools, key=lambda p: p.current_running)
    
    def get_default_pool(self) -> AgentPool:
        """Get default pool."""
        return self.pools["local"]
    
    def get_all_pools(self) -> list:
        """Get all pools."""
        return list(self.pools.values())


def create_sample_tasks() -> list:
    """Create sample tasks for demonstration."""
    now = datetime.now()
    
    tasks = [
        Task(
            id="task-1",
            title="Setup database schema",
            description="Create User and Message models",
            state=TaskState.READY,
            priority=5,
            created_at=now,
            metadata={"required_skill": "database", "spec_id": "chat-app"},
        ),
        Task(
            id="task-2",
            title="Implement JWT authentication",
            description="Add login/register endpoints",
            state=TaskState.READY,
            priority=10,  # High priority
            created_at=now,
            metadata={"required_skill": "backend", "spec_id": "chat-app"},
        ),
        Task(
            id="task-3",
            title="Create login UI",
            description="Build login form component",
            state=TaskState.READY,
            priority=3,
            created_at=now,
            metadata={"required_skill": "frontend", "spec_id": "chat-app"},
        ),
        Task(
            id="task-4",
            title="Setup CI/CD pipeline",
            description="Configure deployment automation",
            state=TaskState.READY,
            priority=7,
            created_at=now,
            metadata={"required_skill": "devops", "spec_id": "chat-app"},
        ),
    ]
    
    return tasks


def demonstrate_policy(policy: SchedulingPolicy):
    """Demonstrate a specific scheduling policy."""
    print(f"\n{'='*60}")
    print(f"Demonstrating {policy.value.upper()} Scheduling Policy")
    print(f"{'='*60}\n")
    
    # Create scheduler
    scheduler = Scheduler(policy)
    
    # Create task queue and add tasks
    task_queue = TaskQueue()
    tasks = create_sample_tasks()
    
    print("Adding tasks to queue:")
    for task in tasks:
        task_queue.enqueue(task)
        skill = task.metadata.get("required_skill", "none")
        print(f"  - {task.id}: {task.title} (priority={task.priority}, skill={skill})")
    
    # Create mock pool manager
    pool_manager = MockAgentPoolManager()
    
    print("\nAvailable Agent Pools:")
    for pool in pool_manager.get_all_pools():
        print(f"  - {pool.name}: {pool.current_running}/{pool.max_concurrency} running")
    
    # Schedule tasks
    scheduled = scheduler.schedule(task_queue, pool_manager)
    
    print(f"\nScheduled {len(scheduled)} tasks:")
    for task, pool in scheduled:
        skill = task.metadata.get("required_skill", "none")
        print(f"  - {task.id} → {pool.name} (priority={task.priority}, skill={skill})")
    
    remaining = task_queue.size()
    print(f"\nRemaining in queue: {remaining} tasks")


def main():
    """Run the scheduler demonstration."""
    print("Dispatcher Scheduler Example")
    print("=" * 60)
    
    # Demonstrate each scheduling policy
    demonstrate_policy(SchedulingPolicy.FIFO)
    demonstrate_policy(SchedulingPolicy.PRIORITY)
    demonstrate_policy(SchedulingPolicy.SKILL_BASED)
    demonstrate_policy(SchedulingPolicy.FAIR_SHARE)
    
    print("\n" + "="*60)
    print("Demonstration complete!")
    print("="*60)


if __name__ == "__main__":
    main()

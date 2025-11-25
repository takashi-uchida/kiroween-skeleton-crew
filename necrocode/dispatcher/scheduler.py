"""
Scheduler implementation for the Dispatcher component.

Provides various scheduling policies for task assignment to Agent Pools.
"""

import logging
from typing import List, Tuple, Optional, Dict
from collections import defaultdict

from necrocode.task_registry.models import Task
from necrocode.dispatcher.models import AgentPool, SchedulingPolicy
from necrocode.dispatcher.task_queue import TaskQueue


logger = logging.getLogger(__name__)


class Scheduler:
    """
    Task scheduler with multiple scheduling policies.
    
    Supports FIFO, Priority-based, Skill-based, and Fair-share scheduling.
    
    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """
    
    def __init__(self, policy: SchedulingPolicy):
        """
        Initialize the scheduler with a specific policy.
        
        Args:
            policy: Scheduling policy to use
            
        Requirements: 11.5
        """
        self.policy = policy
        logger.info(f"Scheduler initialized with policy: {policy.value}")
    
    def schedule(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: "AgentPoolManager"  # Forward reference
    ) -> List[Tuple[Task, AgentPool]]:
        """
        Schedule tasks from the queue to available Agent Pools.
        
        Selects tasks based on the configured scheduling policy and assigns
        them to appropriate Agent Pools that can accept them.
        
        Args:
            task_queue: Queue containing tasks to schedule
            agent_pool_manager: Manager for Agent Pools
            
        Returns:
            List of (Task, AgentPool) tuples ready for assignment
            
        Requirements: 11.1, 11.5
        """
        if self.policy == SchedulingPolicy.FIFO:
            return self._schedule_fifo(task_queue, agent_pool_manager)
        elif self.policy == SchedulingPolicy.PRIORITY:
            return self._schedule_priority(task_queue, agent_pool_manager)
        elif self.policy == SchedulingPolicy.SKILL_BASED:
            return self._schedule_skill_based(task_queue, agent_pool_manager)
        elif self.policy == SchedulingPolicy.FAIR_SHARE:
            return self._schedule_fair_share(task_queue, agent_pool_manager)
        else:
            logger.error(f"Unknown scheduling policy: {self.policy}")
            return []
    
    def _schedule_fifo(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: "AgentPoolManager"
    ) -> List[Tuple[Task, AgentPool]]:
        """
        FIFO (First In First Out) scheduling.
        
        Assigns tasks in the order they were added to the queue,
        regardless of priority or skill requirements.
        
        Args:
            task_queue: Queue containing tasks
            agent_pool_manager: Manager for Agent Pools
            
        Returns:
            List of (Task, AgentPool) tuples
            
        Requirements: 11.1
        """
        scheduled: List[Tuple[Task, AgentPool]] = []
        
        # Get all tasks in FIFO order (by creation time)
        all_tasks = task_queue.get_all_tasks()
        
        # Sort by creation time to ensure FIFO
        all_tasks.sort(key=lambda t: t.created_at)
        
        for task in all_tasks:
            # Try to find any available pool
            pool = agent_pool_manager.get_default_pool()
            
            if pool and agent_pool_manager.can_accept_task(pool):
                # Remove from queue and schedule
                task_queue.dequeue()
                scheduled.append((task, pool))
                logger.debug(f"FIFO scheduled task {task.id} to pool {pool.name}")
            else:
                # No available pool, stop scheduling
                break
        
        return scheduled
    
    def _schedule_priority(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: "AgentPoolManager"
    ) -> List[Tuple[Task, AgentPool]]:
        """
        Priority-based scheduling.
        
        Assigns tasks based on their priority value. Higher priority tasks
        are scheduled first. Tasks with the same priority are processed in
        FIFO order.
        
        Args:
            task_queue: Queue containing tasks
            agent_pool_manager: Manager for Agent Pools
            
        Returns:
            List of (Task, AgentPool) tuples
            
        Requirements: 7.1, 7.2, 7.3, 11.2
        """
        scheduled: List[Tuple[Task, AgentPool]] = []
        
        # Get all tasks (already sorted by priority in the queue)
        all_tasks = task_queue.get_all_tasks()
        
        # Tasks are already sorted by priority (high to low) and then by creation time
        for task in all_tasks:
            # Try to find a pool for this task
            pool = self._find_pool_for_task(task, agent_pool_manager)
            
            if pool and agent_pool_manager.can_accept_task(pool):
                # Remove from queue and schedule
                task_queue.dequeue()
                scheduled.append((task, pool))
                logger.debug(
                    f"Priority scheduled task {task.id} (priority={task.priority}) "
                    f"to pool {pool.name}"
                )
            else:
                # No available pool for this task, try next task
                continue
        
        return scheduled
    
    def _schedule_skill_based(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: "AgentPoolManager"
    ) -> List[Tuple[Task, AgentPool]]:
        """
        Skill-based scheduling.
        
        Assigns tasks to Agent Pools based on required skills. Tasks are
        matched to pools that have the necessary skills, with load balancing
        across multiple capable pools.
        
        Args:
            task_queue: Queue containing tasks
            agent_pool_manager: Manager for Agent Pools
            
        Returns:
            List of (Task, AgentPool) tuples
            
        Requirements: 3.1, 11.3
        """
        scheduled: List[Tuple[Task, AgentPool]] = []
        
        # Get all tasks
        all_tasks = task_queue.get_all_tasks()
        
        for task in all_tasks:
            # Get the required skill from task metadata
            required_skill = task.metadata.get("required_skill") if task.metadata else None
            
            if required_skill:
                # Find pool that matches the skill
                pool = agent_pool_manager.get_pool_for_skill(required_skill)
            else:
                # No skill specified, use default pool
                pool = agent_pool_manager.get_default_pool()
            
            if pool and agent_pool_manager.can_accept_task(pool):
                # Remove from queue and schedule
                task_queue.dequeue()
                scheduled.append((task, pool))
                logger.debug(
                    f"Skill-based scheduled task {task.id} "
                    f"(skill={required_skill}) to pool {pool.name}"
                )
            else:
                # No available pool with required skill
                if required_skill:
                    logger.warning(
                        f"No available pool for task {task.id} "
                        f"with skill {required_skill}"
                    )
                continue
        
        return scheduled
    
    def _schedule_fair_share(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: "AgentPoolManager"
    ) -> List[Tuple[Task, AgentPool]]:
        """
        Fair-share scheduling.
        
        Distributes tasks evenly across all available Agent Pools to ensure
        fair resource utilization. Prioritizes pools with lower current load.
        
        Args:
            task_queue: Queue containing tasks
            agent_pool_manager: Manager for Agent Pools
            
        Returns:
            List of (Task, AgentPool) tuples
            
        Requirements: 11.4
        """
        scheduled: List[Tuple[Task, AgentPool]] = []
        
        # Get all tasks
        all_tasks = task_queue.get_all_tasks()
        
        # Track assignments per pool for fair distribution
        pool_assignments: Dict[str, int] = defaultdict(int)
        
        for task in all_tasks:
            # Get all available pools
            available_pools = agent_pool_manager.get_all_pools()
            
            # Filter to pools that can accept tasks
            capable_pools = [
                pool for pool in available_pools
                if agent_pool_manager.can_accept_task(pool)
            ]
            
            if not capable_pools:
                # No available pools
                break
            
            # Select pool with lowest current load (fair distribution)
            # Consider both current running tasks and assignments in this round
            selected_pool = min(
                capable_pools,
                key=lambda p: (
                    p.current_running + pool_assignments[p.name],
                    p.name  # Tie-breaker: alphabetical
                )
            )
            
            # Remove from queue and schedule
            task_queue.dequeue()
            scheduled.append((task, selected_pool))
            pool_assignments[selected_pool.name] += 1
            
            logger.debug(
                f"Fair-share scheduled task {task.id} to pool {selected_pool.name} "
                f"(load={selected_pool.current_running + pool_assignments[selected_pool.name]})"
            )
        
        return scheduled
    
    def _find_pool_for_task(
        self,
        task: Task,
        agent_pool_manager: "AgentPoolManager"
    ) -> Optional[AgentPool]:
        """
        Find an appropriate Agent Pool for a task.
        
        Considers skill requirements if available, otherwise returns default pool.
        
        Args:
            task: Task to find a pool for
            agent_pool_manager: Manager for Agent Pools
            
        Returns:
            Appropriate AgentPool or None if not found
        """
        # Check if task has skill requirement
        required_skill = task.metadata.get("required_skill") if task.metadata else None
        
        if required_skill:
            return agent_pool_manager.get_pool_for_skill(required_skill)
        else:
            return agent_pool_manager.get_default_pool()

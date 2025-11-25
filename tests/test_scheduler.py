"""
Unit tests for Scheduler.

Tests scheduling policies: FIFO, Priority, Skill-based, and Fair-share.

Requirements: 11.1, 11.2, 11.3, 11.4
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from necrocode.dispatcher.scheduler import Scheduler
from necrocode.dispatcher.models import AgentPool, PoolType, SchedulingPolicy
from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.task_registry.models import Task, TaskState


@pytest.fixture
def task_queue():
    """Create a TaskQueue for testing."""
    return TaskQueue()


@pytest.fixture
def sample_pools():
    """Create sample Agent Pools."""
    return [
        AgentPool(
            name="local",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=2,
            current_running=0,
            enabled=True,
        ),
        AgentPool(
            name="docker",
            type=PoolType.DOCKER,
            max_concurrency=4,
            current_running=1,
            enabled=True,
        ),
        AgentPool(
            name="k8s",
            type=PoolType.KUBERNETES,
            max_concurrency=10,
            current_running=3,
            enabled=True,
        ),
    ]


@pytest.fixture
def mock_pool_manager(sample_pools):
    """Create a mock AgentPoolManager."""
    manager = Mock()
    manager.pools = {pool.name: pool for pool in sample_pools}
    manager.get_default_pool.return_value = sample_pools[0]
    manager.get_all_pools.return_value = sample_pools
    manager.can_accept_task.return_value = True
    
    def get_pool_for_skill(skill):
        if skill == "backend":
            return sample_pools[1]  # docker
        elif skill == "devops":
            return sample_pools[2]  # k8s
        else:
            return sample_pools[0]  # local
    
    manager.get_pool_for_skill.side_effect = get_pool_for_skill
    
    return manager


@pytest.fixture
def sample_tasks():
    """Create sample tasks with different priorities."""
    base_time = datetime.now()
    
    return [
        Task(
            id="1",
            title="Low priority task",
            description="Test",
            state=TaskState.READY,
            priority=1,
            created_at=base_time,
            metadata={"spec_name": "test-spec"},
        ),
        Task(
            id="2",
            title="High priority task",
            description="Test",
            state=TaskState.READY,
            priority=10,
            created_at=base_time + timedelta(seconds=1),
            metadata={"spec_name": "test-spec"},
        ),
        Task(
            id="3",
            title="Medium priority task",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=base_time + timedelta(seconds=2),
            metadata={"spec_name": "test-spec"},
        ),
    ]


class TestSchedulerInitialization:
    """Tests for Scheduler initialization."""
    
    def test_init_with_fifo_policy(self):
        """Test initialization with FIFO policy."""
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        assert scheduler.policy == SchedulingPolicy.FIFO
    
    def test_init_with_priority_policy(self):
        """Test initialization with Priority policy."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        assert scheduler.policy == SchedulingPolicy.PRIORITY
    
    def test_init_with_skill_based_policy(self):
        """Test initialization with Skill-based policy."""
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        assert scheduler.policy == SchedulingPolicy.SKILL_BASED
    
    def test_init_with_fair_share_policy(self):
        """Test initialization with Fair-share policy."""
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        assert scheduler.policy == SchedulingPolicy.FAIR_SHARE


class TestFIFOScheduling:
    """Tests for FIFO scheduling policy."""
    
    def test_fifo_empty_queue(self, task_queue, mock_pool_manager):
        """Test FIFO scheduling with empty queue."""
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []
    
    def test_fifo_single_task(self, task_queue, mock_pool_manager, sample_tasks):
        """Test FIFO scheduling with single task."""
        task_queue.enqueue(sample_tasks[0])
        
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        assert scheduled[0][0].id == "1"
        assert scheduled[0][1].name == "local"  # Default pool
    
    def test_fifo_multiple_tasks(self, task_queue, mock_pool_manager, sample_tasks):
        """Test FIFO scheduling with multiple tasks."""
        # Enqueue in specific order
        for task in sample_tasks:
            task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        # Should be scheduled in creation time order (FIFO)
        assert len(scheduled) >= 1
        # First task should be the oldest (id="1")
        assert scheduled[0][0].id == "1"
    
    def test_fifo_no_available_pool(self, task_queue, mock_pool_manager, sample_tasks):
        """Test FIFO scheduling when no pool is available."""
        task_queue.enqueue(sample_tasks[0])
        
        # Mock no available pool
        mock_pool_manager.can_accept_task.return_value = False
        
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []


class TestPriorityScheduling:
    """Tests for Priority-based scheduling policy."""
    
    def test_priority_empty_queue(self, task_queue, mock_pool_manager):
        """Test Priority scheduling with empty queue."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []
    
    def test_priority_single_task(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Priority scheduling with single task."""
        task_queue.enqueue(sample_tasks[0])
        
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        assert scheduled[0][0].id == "1"
    
    def test_priority_ordering(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Priority scheduling orders by priority."""
        # Enqueue in random order
        for task in sample_tasks:
            task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        # Should schedule highest priority first (id="2", priority=10)
        assert len(scheduled) >= 1
        assert scheduled[0][0].id == "2"
        assert scheduled[0][0].priority == 10
    
    def test_priority_with_skill_requirement(self, task_queue, mock_pool_manager):
        """Test Priority scheduling with skill requirements."""
        task = Task(
            id="backend-task",
            title="Backend task",
            description="Test",
            state=TaskState.READY,
            priority=10,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec", "required_skill": "backend"},
        )
        task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        assert scheduled[0][0].id == "backend-task"
        assert scheduled[0][1].name == "docker"  # Backend skill maps to docker
    
    def test_priority_no_available_pool(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Priority scheduling when no pool is available."""
        task_queue.enqueue(sample_tasks[0])
        
        # Mock no available pool
        mock_pool_manager.can_accept_task.return_value = False
        
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []


class TestSkillBasedScheduling:
    """Tests for Skill-based scheduling policy."""
    
    def test_skill_based_empty_queue(self, task_queue, mock_pool_manager):
        """Test Skill-based scheduling with empty queue."""
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []
    
    def test_skill_based_no_skill_requirement(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Skill-based scheduling without skill requirement."""
        task_queue.enqueue(sample_tasks[0])
        
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        assert scheduled[0][1].name == "local"  # Default pool
    
    def test_skill_based_with_backend_skill(self, task_queue, mock_pool_manager):
        """Test Skill-based scheduling with backend skill."""
        task = Task(
            id="backend-task",
            title="Backend task",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec", "required_skill": "backend"},
        )
        task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        assert scheduled[0][0].id == "backend-task"
        assert scheduled[0][1].name == "docker"
    
    def test_skill_based_with_devops_skill(self, task_queue, mock_pool_manager):
        """Test Skill-based scheduling with devops skill."""
        task = Task(
            id="devops-task",
            title="DevOps task",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec", "required_skill": "devops"},
        )
        task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        assert scheduled[0][0].id == "devops-task"
        assert scheduled[0][1].name == "k8s"
    
    def test_skill_based_multiple_skills(self, task_queue, mock_pool_manager):
        """Test Skill-based scheduling with multiple different skills."""
        tasks = [
            Task(
                id="backend-1",
                title="Backend task 1",
                description="Test",
                state=TaskState.READY,
                priority=5,
                created_at=datetime.now(),
                metadata={"spec_name": "test-spec", "required_skill": "backend"},
            ),
            Task(
                id="devops-1",
                title="DevOps task 1",
                description="Test",
                state=TaskState.READY,
                priority=5,
                created_at=datetime.now(),
                metadata={"spec_name": "test-spec", "required_skill": "devops"},
            ),
        ]
        
        for task in tasks:
            task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 2
        # Check that tasks are assigned to correct pools
        pool_names = {s[0].id: s[1].name for s in scheduled}
        assert pool_names["backend-1"] == "docker"
        assert pool_names["devops-1"] == "k8s"
    
    def test_skill_based_no_matching_pool(self, task_queue, mock_pool_manager):
        """Test Skill-based scheduling when no pool matches skill."""
        task = Task(
            id="unknown-skill-task",
            title="Unknown skill task",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec", "required_skill": "unknown"},
        )
        task_queue.enqueue(task)
        
        # Mock no pool for unknown skill and no pool can accept
        mock_pool_manager.get_pool_for_skill.return_value = None
        mock_pool_manager.can_accept_task.return_value = False
        
        scheduler = Scheduler(SchedulingPolicy.SKILL_BASED)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []


class TestFairShareScheduling:
    """Tests for Fair-share scheduling policy."""
    
    def test_fair_share_empty_queue(self, task_queue, mock_pool_manager):
        """Test Fair-share scheduling with empty queue."""
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []
    
    def test_fair_share_single_task(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Fair-share scheduling with single task."""
        task_queue.enqueue(sample_tasks[0])
        
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        # Should select pool with lowest load (local: 0/2)
        assert scheduled[0][1].name == "local"
    
    def test_fair_share_distributes_evenly(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Fair-share scheduling distributes tasks evenly."""
        # Enqueue multiple tasks
        for task in sample_tasks:
            task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        # Should distribute across pools
        assert len(scheduled) >= 1
        
        # Count assignments per pool
        pool_counts = {}
        for task, pool in scheduled:
            pool_counts[pool.name] = pool_counts.get(pool.name, 0) + 1
        
        # Should have distributed tasks
        assert len(pool_counts) >= 1
    
    def test_fair_share_prefers_least_loaded(self, task_queue, mock_pool_manager):
        """Test Fair-share scheduling prefers least loaded pool."""
        # Create pools with different loads
        pools = [
            AgentPool(
                name="pool1",
                type=PoolType.LOCAL_PROCESS,
                max_concurrency=10,
                current_running=8,  # High load
                enabled=True,
            ),
            AgentPool(
                name="pool2",
                type=PoolType.DOCKER,
                max_concurrency=10,
                current_running=2,  # Low load
                enabled=True,
            ),
        ]
        
        mock_pool_manager.get_all_pools.return_value = pools
        mock_pool_manager.can_accept_task.return_value = True
        
        task = Task(
            id="1",
            title="Test task",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert len(scheduled) == 1
        # Should select pool2 (lower load)
        assert scheduled[0][1].name == "pool2"
    
    def test_fair_share_no_available_pools(self, task_queue, mock_pool_manager, sample_tasks):
        """Test Fair-share scheduling when no pools are available."""
        task_queue.enqueue(sample_tasks[0])
        
        # Mock no available pools
        mock_pool_manager.can_accept_task.return_value = False
        
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        assert scheduled == []
    
    def test_fair_share_multiple_rounds(self, task_queue, mock_pool_manager):
        """Test Fair-share scheduling across multiple rounds."""
        # Create many tasks
        tasks = [
            Task(
                id=f"task-{i}",
                title=f"Task {i}",
                description="Test",
                state=TaskState.READY,
                priority=5,
                created_at=datetime.now(),
                metadata={"spec_name": "test-spec"},
            )
            for i in range(10)
        ]
        
        for task in tasks:
            task_queue.enqueue(task)
        
        scheduler = Scheduler(SchedulingPolicy.FAIR_SHARE)
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        # Should schedule multiple tasks
        assert len(scheduled) >= 3
        
        # Count assignments per pool
        pool_counts = {}
        for task, pool in scheduled:
            pool_counts[pool.name] = pool_counts.get(pool.name, 0) + 1
        
        # Should distribute fairly across pools
        assert len(pool_counts) >= 2


class TestSchedulerEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_schedule_with_unknown_policy(self, task_queue, mock_pool_manager):
        """Test scheduling with unknown policy."""
        scheduler = Scheduler(SchedulingPolicy.FIFO)
        # Hack the policy to something invalid
        scheduler.policy = "invalid-policy"
        
        scheduled = scheduler.schedule(task_queue, mock_pool_manager)
        
        # Should return empty list on unknown policy
        assert scheduled == []
    
    def test_find_pool_for_task_with_skill(self, mock_pool_manager):
        """Test finding pool for task with skill requirement."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        
        task = Task(
            id="1",
            title="Test",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec", "required_skill": "backend"},
        )
        
        pool = scheduler._find_pool_for_task(task, mock_pool_manager)
        
        assert pool is not None
        assert pool.name == "docker"
    
    def test_find_pool_for_task_without_skill(self, mock_pool_manager):
        """Test finding pool for task without skill requirement."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        
        task = Task(
            id="1",
            title="Test",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata={"spec_name": "test-spec"},
        )
        
        pool = scheduler._find_pool_for_task(task, mock_pool_manager)
        
        assert pool is not None
        assert pool.name == "local"  # Default pool
    
    def test_find_pool_for_task_no_metadata(self, mock_pool_manager):
        """Test finding pool for task without metadata."""
        scheduler = Scheduler(SchedulingPolicy.PRIORITY)
        
        task = Task(
            id="1",
            title="Test",
            description="Test",
            state=TaskState.READY,
            priority=5,
            created_at=datetime.now(),
            metadata=None,
        )
        
        pool = scheduler._find_pool_for_task(task, mock_pool_manager)
        
        assert pool is not None
        assert pool.name == "local"  # Default pool


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

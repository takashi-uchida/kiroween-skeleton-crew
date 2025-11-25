"""
Unit tests for Dispatcher data models.

Tests serialization/deserialization and validation of AgentPool, Runner,
RunnerInfo, and PoolStatus models.

Requirements: 2.1
"""

import pytest
from datetime import datetime
from necrocode.dispatcher.models import (
    AgentPool,
    PoolType,
    Runner,
    RunnerState,
    RunnerInfo,
    PoolStatus,
    SchedulingPolicy,
)


class TestPoolType:
    """Tests for PoolType enum."""
    
    def test_pool_type_values(self):
        """Test PoolType enum values."""
        assert PoolType.LOCAL_PROCESS.value == "local-process"
        assert PoolType.DOCKER.value == "docker"
        assert PoolType.KUBERNETES.value == "kubernetes"
    
    def test_pool_type_from_string(self):
        """Test creating PoolType from string."""
        assert PoolType("local-process") == PoolType.LOCAL_PROCESS
        assert PoolType("docker") == PoolType.DOCKER
        assert PoolType("kubernetes") == PoolType.KUBERNETES


class TestRunnerState:
    """Tests for RunnerState enum."""
    
    def test_runner_state_values(self):
        """Test RunnerState enum values."""
        assert RunnerState.RUNNING.value == "running"
        assert RunnerState.COMPLETED.value == "completed"
        assert RunnerState.FAILED.value == "failed"
    
    def test_runner_state_from_string(self):
        """Test creating RunnerState from string."""
        assert RunnerState("running") == RunnerState.RUNNING
        assert RunnerState("completed") == RunnerState.COMPLETED
        assert RunnerState("failed") == RunnerState.FAILED


class TestSchedulingPolicy:
    """Tests for SchedulingPolicy enum."""
    
    def test_scheduling_policy_values(self):
        """Test SchedulingPolicy enum values."""
        assert SchedulingPolicy.FIFO.value == "fifo"
        assert SchedulingPolicy.PRIORITY.value == "priority"
        assert SchedulingPolicy.SKILL_BASED.value == "skill-based"
        assert SchedulingPolicy.FAIR_SHARE.value == "fair-share"


class TestAgentPool:
    """Tests for AgentPool model."""
    
    def test_agent_pool_creation(self):
        """Test creating an AgentPool."""
        pool = AgentPool(
            name="test-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=4,
            current_running=2,
            cpu_quota=2,
            memory_quota=4096,
            enabled=True,
            config={"log_level": "DEBUG"},
        )
        
        assert pool.name == "test-pool"
        assert pool.type == PoolType.LOCAL_PROCESS
        assert pool.max_concurrency == 4
        assert pool.current_running == 2
        assert pool.cpu_quota == 2
        assert pool.memory_quota == 4096
        assert pool.enabled is True
        assert pool.config == {"log_level": "DEBUG"}
    
    def test_agent_pool_defaults(self):
        """Test AgentPool default values."""
        pool = AgentPool(
            name="minimal-pool",
            type=PoolType.DOCKER,
            max_concurrency=2,
        )
        
        assert pool.current_running == 0
        assert pool.cpu_quota is None
        assert pool.memory_quota is None
        assert pool.enabled is True
        assert pool.config == {}
    
    def test_can_accept_task_enabled_with_capacity(self):
        """Test can_accept_task when pool is enabled and has capacity."""
        pool = AgentPool(
            name="test-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=4,
            current_running=2,
            enabled=True,
        )
        
        assert pool.can_accept_task() is True
    
    def test_can_accept_task_at_max_concurrency(self):
        """Test can_accept_task when pool is at max concurrency."""
        pool = AgentPool(
            name="test-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=4,
            current_running=4,
            enabled=True,
        )
        
        assert pool.can_accept_task() is False
    
    def test_can_accept_task_disabled(self):
        """Test can_accept_task when pool is disabled."""
        pool = AgentPool(
            name="test-pool",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=4,
            current_running=0,
            enabled=False,
        )
        
        assert pool.can_accept_task() is False
    
    def test_agent_pool_to_dict(self):
        """Test serializing AgentPool to dictionary."""
        pool = AgentPool(
            name="test-pool",
            type=PoolType.DOCKER,
            max_concurrency=4,
            current_running=2,
            cpu_quota=2,
            memory_quota=4096,
            enabled=True,
            config={"image": "test:latest"},
        )
        
        data = pool.to_dict()
        
        assert data["name"] == "test-pool"
        assert data["type"] == "docker"
        assert data["max_concurrency"] == 4
        assert data["current_running"] == 2
        assert data["cpu_quota"] == 2
        assert data["memory_quota"] == 4096
        assert data["enabled"] is True
        assert data["config"] == {"image": "test:latest"}
    
    def test_agent_pool_from_dict(self):
        """Test deserializing AgentPool from dictionary."""
        data = {
            "name": "test-pool",
            "type": "kubernetes",
            "max_concurrency": 10,
            "current_running": 5,
            "cpu_quota": 8,
            "memory_quota": 16384,
            "enabled": True,
            "config": {"namespace": "test"},
        }
        
        pool = AgentPool.from_dict(data)
        
        assert pool.name == "test-pool"
        assert pool.type == PoolType.KUBERNETES
        assert pool.max_concurrency == 10
        assert pool.current_running == 5
        assert pool.cpu_quota == 8
        assert pool.memory_quota == 16384
        assert pool.enabled is True
        assert pool.config == {"namespace": "test"}
    
    def test_agent_pool_roundtrip(self):
        """Test serialization roundtrip."""
        original = AgentPool(
            name="roundtrip-pool",
            type=PoolType.DOCKER,
            max_concurrency=6,
            current_running=3,
            cpu_quota=4,
            memory_quota=8192,
            enabled=True,
            config={"mount": "/data"},
        )
        
        data = original.to_dict()
        restored = AgentPool.from_dict(data)
        
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.max_concurrency == original.max_concurrency
        assert restored.current_running == original.current_running
        assert restored.cpu_quota == original.cpu_quota
        assert restored.memory_quota == original.memory_quota
        assert restored.enabled == original.enabled
        assert restored.config == original.config


class TestRunner:
    """Tests for Runner model."""
    
    def test_runner_creation_local_process(self):
        """Test creating a Runner for local process."""
        started = datetime.now()
        runner = Runner(
            runner_id="runner-001",
            task_id="task-123",
            pool_name="local-pool",
            slot_id="slot-001",
            state=RunnerState.RUNNING,
            started_at=started,
            pid=12345,
        )
        
        assert runner.runner_id == "runner-001"
        assert runner.task_id == "task-123"
        assert runner.pool_name == "local-pool"
        assert runner.slot_id == "slot-001"
        assert runner.state == RunnerState.RUNNING
        assert runner.started_at == started
        assert runner.pid == 12345
        assert runner.container_id is None
        assert runner.job_name is None
    
    def test_runner_creation_docker(self):
        """Test creating a Runner for Docker."""
        started = datetime.now()
        runner = Runner(
            runner_id="runner-002",
            task_id="task-456",
            pool_name="docker-pool",
            slot_id="slot-002",
            state=RunnerState.RUNNING,
            started_at=started,
            container_id="container-abc123",
        )
        
        assert runner.container_id == "container-abc123"
        assert runner.pid is None
        assert runner.job_name is None
    
    def test_runner_creation_kubernetes(self):
        """Test creating a Runner for Kubernetes."""
        started = datetime.now()
        runner = Runner(
            runner_id="runner-003",
            task_id="task-789",
            pool_name="k8s-pool",
            slot_id="slot-003",
            state=RunnerState.RUNNING,
            started_at=started,
            job_name="job-xyz",
        )
        
        assert runner.job_name == "job-xyz"
        assert runner.pid is None
        assert runner.container_id is None
    
    def test_runner_to_dict(self):
        """Test serializing Runner to dictionary."""
        started = datetime(2024, 1, 15, 10, 30, 0)
        runner = Runner(
            runner_id="runner-001",
            task_id="task-123",
            pool_name="local-pool",
            slot_id="slot-001",
            state=RunnerState.RUNNING,
            started_at=started,
            pid=12345,
        )
        
        data = runner.to_dict()
        
        assert data["runner_id"] == "runner-001"
        assert data["task_id"] == "task-123"
        assert data["pool_name"] == "local-pool"
        assert data["slot_id"] == "slot-001"
        assert data["state"] == "running"
        assert data["started_at"] == "2024-01-15T10:30:00"
        assert data["pid"] == 12345
        assert data["container_id"] is None
        assert data["job_name"] is None
    
    def test_runner_from_dict(self):
        """Test deserializing Runner from dictionary."""
        data = {
            "runner_id": "runner-002",
            "task_id": "task-456",
            "pool_name": "docker-pool",
            "slot_id": "slot-002",
            "state": "completed",
            "started_at": "2024-01-15T11:00:00",
            "container_id": "container-xyz",
        }
        
        runner = Runner.from_dict(data)
        
        assert runner.runner_id == "runner-002"
        assert runner.task_id == "task-456"
        assert runner.pool_name == "docker-pool"
        assert runner.slot_id == "slot-002"
        assert runner.state == RunnerState.COMPLETED
        assert runner.started_at == datetime(2024, 1, 15, 11, 0, 0)
        assert runner.container_id == "container-xyz"
        assert runner.pid is None
    
    def test_runner_roundtrip(self):
        """Test serialization roundtrip."""
        started = datetime.now()
        original = Runner(
            runner_id="runner-roundtrip",
            task_id="task-roundtrip",
            pool_name="test-pool",
            slot_id="slot-roundtrip",
            state=RunnerState.FAILED,
            started_at=started,
            pid=99999,
        )
        
        data = original.to_dict()
        restored = Runner.from_dict(data)
        
        assert restored.runner_id == original.runner_id
        assert restored.task_id == original.task_id
        assert restored.pool_name == original.pool_name
        assert restored.slot_id == original.slot_id
        assert restored.state == original.state
        # Compare timestamps with tolerance for microseconds
        assert abs((restored.started_at - original.started_at).total_seconds()) < 0.001
        assert restored.pid == original.pid


class TestRunnerInfo:
    """Tests for RunnerInfo model."""
    
    def test_runner_info_creation(self):
        """Test creating RunnerInfo."""
        started = datetime.now()
        heartbeat = datetime.now()
        
        runner = Runner(
            runner_id="runner-001",
            task_id="task-123",
            pool_name="local-pool",
            slot_id="slot-001",
            state=RunnerState.RUNNING,
            started_at=started,
            pid=12345,
        )
        
        info = RunnerInfo(
            runner=runner,
            last_heartbeat=heartbeat,
            state=RunnerState.RUNNING,
        )
        
        assert info.runner == runner
        assert info.last_heartbeat == heartbeat
        assert info.state == RunnerState.RUNNING
    
    def test_runner_info_to_dict(self):
        """Test serializing RunnerInfo to dictionary."""
        started = datetime(2024, 1, 15, 10, 0, 0)
        heartbeat = datetime(2024, 1, 15, 10, 5, 0)
        
        runner = Runner(
            runner_id="runner-001",
            task_id="task-123",
            pool_name="local-pool",
            slot_id="slot-001",
            state=RunnerState.RUNNING,
            started_at=started,
            pid=12345,
        )
        
        info = RunnerInfo(
            runner=runner,
            last_heartbeat=heartbeat,
            state=RunnerState.RUNNING,
        )
        
        data = info.to_dict()
        
        assert "runner" in data
        assert data["runner"]["runner_id"] == "runner-001"
        assert data["last_heartbeat"] == "2024-01-15T10:05:00"
        assert data["state"] == "running"
    
    def test_runner_info_from_dict(self):
        """Test deserializing RunnerInfo from dictionary."""
        data = {
            "runner": {
                "runner_id": "runner-002",
                "task_id": "task-456",
                "pool_name": "docker-pool",
                "slot_id": "slot-002",
                "state": "completed",
                "started_at": "2024-01-15T11:00:00",
                "container_id": "container-xyz",
            },
            "last_heartbeat": "2024-01-15T11:10:00",
            "state": "completed",
        }
        
        info = RunnerInfo.from_dict(data)
        
        assert info.runner.runner_id == "runner-002"
        assert info.last_heartbeat == datetime(2024, 1, 15, 11, 10, 0)
        assert info.state == RunnerState.COMPLETED
    
    def test_runner_info_roundtrip(self):
        """Test serialization roundtrip."""
        started = datetime.now()
        heartbeat = datetime.now()
        
        runner = Runner(
            runner_id="runner-roundtrip",
            task_id="task-roundtrip",
            pool_name="test-pool",
            slot_id="slot-roundtrip",
            state=RunnerState.RUNNING,
            started_at=started,
            pid=88888,
        )
        
        original = RunnerInfo(
            runner=runner,
            last_heartbeat=heartbeat,
            state=RunnerState.RUNNING,
        )
        
        data = original.to_dict()
        restored = RunnerInfo.from_dict(data)
        
        assert restored.runner.runner_id == original.runner.runner_id
        assert restored.state == original.state
        # Compare timestamps with tolerance
        assert abs((restored.last_heartbeat - original.last_heartbeat).total_seconds()) < 0.001


class TestPoolStatus:
    """Tests for PoolStatus model."""
    
    def test_pool_status_creation(self):
        """Test creating PoolStatus."""
        status = PoolStatus(
            pool_name="test-pool",
            type=PoolType.DOCKER,
            enabled=True,
            max_concurrency=10,
            current_running=6,
            utilization=0.6,
            cpu_usage=3.5,
            memory_usage=7168.0,
        )
        
        assert status.pool_name == "test-pool"
        assert status.type == PoolType.DOCKER
        assert status.enabled is True
        assert status.max_concurrency == 10
        assert status.current_running == 6
        assert status.utilization == 0.6
        assert status.cpu_usage == 3.5
        assert status.memory_usage == 7168.0
    
    def test_pool_status_defaults(self):
        """Test PoolStatus default values."""
        status = PoolStatus(
            pool_name="minimal-pool",
            type=PoolType.LOCAL_PROCESS,
            enabled=True,
            max_concurrency=4,
            current_running=2,
            utilization=0.5,
        )
        
        assert status.cpu_usage is None
        assert status.memory_usage is None
    
    def test_pool_status_to_dict(self):
        """Test serializing PoolStatus to dictionary."""
        status = PoolStatus(
            pool_name="test-pool",
            type=PoolType.KUBERNETES,
            enabled=True,
            max_concurrency=20,
            current_running=15,
            utilization=0.75,
            cpu_usage=12.0,
            memory_usage=24576.0,
        )
        
        data = status.to_dict()
        
        assert data["pool_name"] == "test-pool"
        assert data["type"] == "kubernetes"
        assert data["enabled"] is True
        assert data["max_concurrency"] == 20
        assert data["current_running"] == 15
        assert data["utilization"] == 0.75
        assert data["cpu_usage"] == 12.0
        assert data["memory_usage"] == 24576.0
    
    def test_pool_status_from_dict(self):
        """Test deserializing PoolStatus from dictionary."""
        data = {
            "pool_name": "test-pool",
            "type": "docker",
            "enabled": False,
            "max_concurrency": 8,
            "current_running": 0,
            "utilization": 0.0,
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
        }
        
        status = PoolStatus.from_dict(data)
        
        assert status.pool_name == "test-pool"
        assert status.type == PoolType.DOCKER
        assert status.enabled is False
        assert status.max_concurrency == 8
        assert status.current_running == 0
        assert status.utilization == 0.0
        assert status.cpu_usage == 0.0
        assert status.memory_usage == 0.0
    
    def test_pool_status_roundtrip(self):
        """Test serialization roundtrip."""
        original = PoolStatus(
            pool_name="roundtrip-pool",
            type=PoolType.LOCAL_PROCESS,
            enabled=True,
            max_concurrency=4,
            current_running=3,
            utilization=0.75,
            cpu_usage=2.8,
            memory_usage=3072.0,
        )
        
        data = original.to_dict()
        restored = PoolStatus.from_dict(data)
        
        assert restored.pool_name == original.pool_name
        assert restored.type == original.type
        assert restored.enabled == original.enabled
        assert restored.max_concurrency == original.max_concurrency
        assert restored.current_running == original.current_running
        assert restored.utilization == original.utilization
        assert restored.cpu_usage == original.cpu_usage
        assert restored.memory_usage == original.memory_usage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

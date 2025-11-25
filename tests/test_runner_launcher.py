"""
Tests for Runner Launcher component.

Tests the launching of Agent Runners in different execution environments.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from necrocode.dispatcher.runner_launcher import (
    RunnerLauncher,
    TaskContext,
    LocalProcessLauncher,
    DockerLauncher,
    KubernetesLauncher,
)
from necrocode.dispatcher.models import AgentPool, PoolType, RunnerState
from necrocode.dispatcher.exceptions import RunnerLaunchError
from necrocode.task_registry.models import Task, TaskState


@pytest.fixture
def mock_task():
    """Create a mock task."""
    return Task(
        id="1.1",
        title="Test task",
        description="Test task description",
        state=TaskState.READY,
        dependencies=["1.0"],
        required_skill="backend",
        reserved_branch="feature/task-1.1-test",
        metadata={"spec_name": "test-spec"}
    )


@pytest.fixture
def mock_slot():
    """Create a mock slot."""
    slot = Mock()
    slot.slot_id = "slot-001"
    slot.slot_path = Path("/tmp/test-slot")
    slot.repo_url = "https://github.com/test/repo.git"
    return slot


@pytest.fixture
def local_pool():
    """Create a local process pool."""
    return AgentPool(
        name="local-test",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=2,
        config={"log_level": "DEBUG"}
    )


@pytest.fixture
def docker_pool():
    """Create a Docker pool."""
    return AgentPool(
        name="docker-test",
        type=PoolType.DOCKER,
        max_concurrency=4,
        cpu_quota=2,
        memory_quota=4096,
        config={
            "image": "necrocode/runner:test",
            "mount_repo_pool": True,
        }
    )


@pytest.fixture
def k8s_pool():
    """Create a Kubernetes pool."""
    return AgentPool(
        name="k8s-test",
        type=PoolType.KUBERNETES,
        max_concurrency=10,
        cpu_quota=4,
        memory_quota=8192,
        config={
            "namespace": "test-namespace",
            "image": "necrocode/runner:test",
        }
    )


class TestTaskContext:
    """Tests for TaskContext."""
    
    def test_task_context_creation(self, mock_task, mock_slot):
        """Test creating a task context."""
        context = TaskContext(
            task_id=mock_task.id,
            spec_name="test-spec",
            task_title=mock_task.title,
            task_description=mock_task.description,
            dependencies=mock_task.dependencies,
            required_skill=mock_task.required_skill,
            slot_id=mock_slot.slot_id,
            slot_path=str(mock_slot.slot_path),
            repo_url=mock_slot.repo_url,
            branch_name=mock_task.reserved_branch,
            metadata=mock_task.metadata,
        )
        
        assert context.task_id == "1.1"
        assert context.spec_name == "test-spec"
        assert context.slot_id == "slot-001"
        assert context.required_skill == "backend"
    
    def test_task_context_to_dict(self, mock_task, mock_slot):
        """Test serializing task context to dict."""
        context = TaskContext(
            task_id=mock_task.id,
            spec_name="test-spec",
            task_title=mock_task.title,
            task_description=mock_task.description,
            dependencies=mock_task.dependencies,
            required_skill=mock_task.required_skill,
            slot_id=mock_slot.slot_id,
            slot_path=str(mock_slot.slot_path),
            repo_url=mock_slot.repo_url,
            branch_name=mock_task.reserved_branch,
            metadata=mock_task.metadata,
        )
        
        data = context.to_dict()
        assert data["task_id"] == "1.1"
        assert data["spec_name"] == "test-spec"
        assert data["slot_id"] == "slot-001"
    
    def test_task_context_to_json(self, mock_task, mock_slot):
        """Test serializing task context to JSON."""
        context = TaskContext(
            task_id=mock_task.id,
            spec_name="test-spec",
            task_title=mock_task.title,
            task_description=mock_task.description,
            dependencies=mock_task.dependencies,
            required_skill=mock_task.required_skill,
            slot_id=mock_slot.slot_id,
            slot_path=str(mock_slot.slot_path),
            repo_url=mock_slot.repo_url,
            branch_name=mock_task.reserved_branch,
            metadata=mock_task.metadata,
        )
        
        json_str = context.to_json()
        data = json.loads(json_str)
        assert data["task_id"] == "1.1"
        assert data["spec_name"] == "test-spec"


class TestLocalProcessLauncher:
    """Tests for LocalProcessLauncher."""
    
    @patch('subprocess.Popen')
    def test_local_launch_success(self, mock_popen, local_pool, mock_task, mock_slot):
        """Test successful local process launch."""
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        launcher = LocalProcessLauncher()
        
        # Build context
        context = TaskContext(
            task_id=mock_task.id,
            spec_name="test-spec",
            task_title=mock_task.title,
            task_description=mock_task.description,
            dependencies=mock_task.dependencies,
            required_skill=mock_task.required_skill,
            slot_id=mock_slot.slot_id,
            slot_path=str(mock_slot.slot_path),
            repo_url=mock_slot.repo_url,
            branch_name=mock_task.reserved_branch,
            metadata=mock_task.metadata,
        )
        
        runner = launcher.launch("runner-123", context, local_pool)
        
        assert runner.runner_id == "runner-123"
        assert runner.task_id == "1.1"
        assert runner.pool_name == "local-test"
        assert runner.state == RunnerState.RUNNING
        assert runner.pid == 12345
        
        # Verify Popen was called
        mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_local_launch_failure(self, mock_popen, local_pool, mock_task, mock_slot):
        """Test local process launch failure."""
        # Mock failure
        mock_popen.side_effect = Exception("Launch failed")
        
        launcher = LocalProcessLauncher()
        
        context = TaskContext(
            task_id=mock_task.id,
            spec_name="test-spec",
            task_title=mock_task.title,
            task_description=mock_task.description,
            dependencies=mock_task.dependencies,
            required_skill=mock_task.required_skill,
            slot_id=mock_slot.slot_id,
            slot_path=str(mock_slot.slot_path),
            repo_url=mock_slot.repo_url,
            branch_name=mock_task.reserved_branch,
            metadata=mock_task.metadata,
        )
        
        with pytest.raises(RunnerLaunchError):
            launcher.launch("runner-123", context, local_pool)


try:
    import docker
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

try:
    import kubernetes
    HAS_KUBERNETES = True
except ImportError:
    HAS_KUBERNETES = False


class TestDockerLauncher:
    """Tests for DockerLauncher."""
    
    @pytest.mark.skipif(not HAS_DOCKER, reason="docker library not installed")
    def test_docker_launch_success(self, docker_pool, mock_task, mock_slot):
        """Test successful Docker container launch."""
        with patch('docker.from_env') as mock_from_env:
            # Mock Docker client
            mock_client = Mock()
            mock_container = Mock()
            mock_container.id = "container-abc123"
            mock_client.containers.run.return_value = mock_container
            mock_from_env.return_value = mock_client
            
            launcher = DockerLauncher()
            
            context = TaskContext(
                task_id=mock_task.id,
                spec_name="test-spec",
                task_title=mock_task.title,
                task_description=mock_task.description,
                dependencies=mock_task.dependencies,
                required_skill=mock_task.required_skill,
                slot_id=mock_slot.slot_id,
                slot_path=str(mock_slot.slot_path),
                repo_url=mock_slot.repo_url,
                branch_name=mock_task.reserved_branch,
                metadata=mock_task.metadata,
            )
            
            runner = launcher.launch("runner-456", context, docker_pool)
            
            assert runner.runner_id == "runner-456"
            assert runner.task_id == "1.1"
            assert runner.pool_name == "docker-test"
            assert runner.state == RunnerState.RUNNING
            assert runner.container_id == "container-abc123"
            
            # Verify container was created
            mock_client.containers.run.assert_called_once()


class TestKubernetesLauncher:
    """Tests for KubernetesLauncher."""
    
    @pytest.mark.skipif(not HAS_KUBERNETES, reason="kubernetes library not installed")
    def test_k8s_launch_success(self, k8s_pool, mock_task, mock_slot):
        """Test successful Kubernetes Job launch."""
        with patch('kubernetes.client.BatchV1Api') as mock_batch_api_class, \
             patch('kubernetes.client.CoreV1Api') as mock_core_api_class, \
             patch('kubernetes.config.load_kube_config'):
            
            # Mock Kubernetes client
            mock_batch_api = Mock()
            mock_batch_api_class.return_value = mock_batch_api
            
            launcher = KubernetesLauncher()
            
            context = TaskContext(
                task_id=mock_task.id,
                spec_name="test-spec",
                task_title=mock_task.title,
                task_description=mock_task.description,
                dependencies=mock_task.dependencies,
                required_skill=mock_task.required_skill,
                slot_id=mock_slot.slot_id,
                slot_path=str(mock_slot.slot_path),
                repo_url=mock_slot.repo_url,
                branch_name=mock_task.reserved_branch,
                metadata=mock_task.metadata,
            )
            
            runner = launcher.launch("runner-789", context, k8s_pool)
            
            assert runner.runner_id == "runner-789"
            assert runner.task_id == "1.1"
            assert runner.pool_name == "k8s-test"
            assert runner.state == RunnerState.RUNNING
            assert runner.job_name is not None
            
            # Verify Job was created
            mock_batch_api.create_namespaced_job.assert_called_once()


class TestRunnerLauncher:
    """Tests for main RunnerLauncher."""
    
    def test_generate_runner_id(self):
        """Test runner ID generation."""
        launcher = RunnerLauncher()
        
        runner_id1 = launcher._generate_runner_id()
        runner_id2 = launcher._generate_runner_id()
        
        assert runner_id1.startswith("runner-")
        assert runner_id2.startswith("runner-")
        assert runner_id1 != runner_id2
    
    def test_build_task_context(self, mock_task, mock_slot):
        """Test building task context."""
        launcher = RunnerLauncher()
        
        context = launcher._build_task_context(mock_task, mock_slot)
        
        assert context.task_id == "1.1"
        assert context.spec_name == "test-spec"
        assert context.task_title == "Test task"
        assert context.slot_id == "slot-001"
        assert context.required_skill == "backend"
    
    @patch('subprocess.Popen')
    def test_launch_local_process(self, mock_popen, local_pool, mock_task, mock_slot):
        """Test launching with local process pool."""
        mock_process = Mock()
        mock_process.pid = 99999
        mock_popen.return_value = mock_process
        
        launcher = RunnerLauncher()
        runner = launcher.launch(mock_task, mock_slot, local_pool)
        
        assert runner.pool_name == "local-test"
        assert runner.state == RunnerState.RUNNING
        assert runner.pid == 99999
    
    @patch('subprocess.Popen')
    def test_launch_with_retry(self, mock_popen, local_pool, mock_task, mock_slot):
        """Test launch retry on failure."""
        # First two attempts fail, third succeeds
        mock_process = Mock()
        mock_process.pid = 88888
        mock_popen.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            mock_process,
        ]
        
        launcher = RunnerLauncher(retry_attempts=3)
        runner = launcher.launch(mock_task, mock_slot, local_pool)
        
        assert runner.pid == 88888
        assert mock_popen.call_count == 3
    
    @patch('subprocess.Popen')
    def test_launch_exhausted_retries(self, mock_popen, local_pool, mock_task, mock_slot):
        """Test launch failure after exhausting retries."""
        mock_popen.side_effect = Exception("Persistent failure")
        
        launcher = RunnerLauncher(retry_attempts=2)
        
        with pytest.raises(RunnerLaunchError) as exc_info:
            launcher.launch(mock_task, mock_slot, local_pool)
        
        assert "after 2 attempts" in str(exc_info.value)
        assert mock_popen.call_count == 2
    
    def test_launch_unknown_pool_type(self, mock_task, mock_slot):
        """Test launch with unknown pool type."""
        # Create pool with invalid type by bypassing enum
        pool = AgentPool(
            name="invalid",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=1,
        )
        # Hack the type to something invalid
        pool.type = "invalid-type"
        
        launcher = RunnerLauncher()
        
        with pytest.raises(RunnerLaunchError):
            launcher.launch(mock_task, mock_slot, pool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

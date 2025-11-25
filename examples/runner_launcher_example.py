"""
Example demonstrating the Runner Launcher functionality.

Shows how to launch Agent Runners in different execution environments.
"""

import logging
from datetime import datetime
from pathlib import Path

from necrocode.dispatcher.runner_launcher import RunnerLauncher, TaskContext
from necrocode.dispatcher.models import AgentPool, PoolType
from necrocode.task_registry.models import Task, TaskState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class MockSlot:
    """Mock slot for demonstration."""
    def __init__(self):
        self.slot_id = "slot-001"
        self.slot_path = Path("/tmp/necrocode/slots/slot-001")
        self.repo_url = "https://github.com/example/repo.git"


def example_local_process_launch():
    """Example: Launch runner as local process."""
    logger.info("=== Local Process Launch Example ===")
    
    # Create a local process pool
    pool = AgentPool(
        name="local-dev",
        type=PoolType.LOCAL_PROCESS,
        max_concurrency=2,
        config={
            "log_level": "DEBUG",
        }
    )
    
    # Create a mock task
    task = Task(
        id="1.1",
        title="Implement authentication",
        description="Add JWT authentication to the API",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        metadata={"spec_name": "auth-service"}
    )
    
    # Create mock slot
    slot = MockSlot()
    
    # Launch runner
    launcher = RunnerLauncher()
    
    try:
        runner = launcher.launch(task, slot, pool)
        logger.info(f"✓ Launched runner: {runner.runner_id}")
        logger.info(f"  PID: {runner.pid}")
        logger.info(f"  Task: {runner.task_id}")
        logger.info(f"  Pool: {runner.pool_name}")
        logger.info(f"  State: {runner.state.value}")
    except Exception as e:
        logger.error(f"✗ Launch failed: {e}")


def example_docker_launch():
    """Example: Launch runner as Docker container."""
    logger.info("\n=== Docker Launch Example ===")
    
    # Create a Docker pool
    pool = AgentPool(
        name="docker-pool",
        type=PoolType.DOCKER,
        max_concurrency=4,
        cpu_quota=2,
        memory_quota=4096,
        config={
            "image": "necrocode/runner:latest",
            "mount_repo_pool": True,
        }
    )
    
    # Create a mock task
    task = Task(
        id="2.1",
        title="Build frontend components",
        description="Create React components for the dashboard",
        state=TaskState.READY,
        dependencies=["1.1"],
        required_skill="frontend",
        metadata={"spec_name": "dashboard"}
    )
    
    # Create mock slot
    slot = MockSlot()
    
    # Launch runner
    launcher = RunnerLauncher()
    
    try:
        runner = launcher.launch(task, slot, pool)
        logger.info(f"✓ Launched runner: {runner.runner_id}")
        logger.info(f"  Container ID: {runner.container_id}")
        logger.info(f"  Task: {runner.task_id}")
        logger.info(f"  Pool: {runner.pool_name}")
        logger.info(f"  State: {runner.state.value}")
    except Exception as e:
        logger.error(f"✗ Launch failed: {e}")
        logger.info("  Note: Docker must be installed and running")


def example_kubernetes_launch():
    """Example: Launch runner as Kubernetes Job."""
    logger.info("\n=== Kubernetes Launch Example ===")
    
    # Create a Kubernetes pool
    pool = AgentPool(
        name="k8s-pool",
        type=PoolType.KUBERNETES,
        max_concurrency=10,
        cpu_quota=4,
        memory_quota=8192,
        config={
            "namespace": "necrocode-agents",
            "image": "necrocode/runner:latest",
        }
    )
    
    # Create a mock task
    task = Task(
        id="3.1",
        title="Deploy microservice",
        description="Deploy the authentication microservice to staging",
        state=TaskState.READY,
        dependencies=["1.1", "2.1"],
        required_skill="devops",
        metadata={"spec_name": "deployment"}
    )
    
    # Create mock slot
    slot = MockSlot()
    
    # Launch runner
    launcher = RunnerLauncher()
    
    try:
        runner = launcher.launch(task, slot, pool)
        logger.info(f"✓ Launched runner: {runner.runner_id}")
        logger.info(f"  Job Name: {runner.job_name}")
        logger.info(f"  Task: {runner.task_id}")
        logger.info(f"  Pool: {runner.pool_name}")
        logger.info(f"  State: {runner.state.value}")
    except Exception as e:
        logger.error(f"✗ Launch failed: {e}")
        logger.info("  Note: Kubernetes cluster must be configured")


def example_retry_on_failure():
    """Example: Automatic retry on launch failure."""
    logger.info("\n=== Retry on Failure Example ===")
    
    # Create a pool with invalid configuration to trigger failure
    pool = AgentPool(
        name="invalid-pool",
        type=PoolType.DOCKER,
        max_concurrency=1,
        config={
            "image": "nonexistent/image:latest",
        }
    )
    
    task = Task(
        id="4.1",
        title="Test task",
        description="This will fail",
        state=TaskState.READY,
        dependencies=[],
        metadata={"spec_name": "test"}
    )
    
    slot = MockSlot()
    
    # Launch with retry
    launcher = RunnerLauncher(retry_attempts=3)
    
    try:
        runner = launcher.launch(task, slot, pool)
        logger.info(f"✓ Launched runner: {runner.runner_id}")
    except Exception as e:
        logger.error(f"✗ Launch failed after retries: {e}")
        logger.info("  This is expected - the image doesn't exist")


def example_task_context():
    """Example: Building task context."""
    logger.info("\n=== Task Context Example ===")
    
    task = Task(
        id="5.1",
        title="Example task",
        description="Demonstrates task context building",
        state=TaskState.READY,
        dependencies=["4.1"],
        required_skill="backend",
        reserved_branch="feature/task-5.1-example",
        metadata={
            "spec_name": "example-spec",
            "priority": "high",
        }
    )
    
    slot = MockSlot()
    
    launcher = RunnerLauncher()
    context = launcher._build_task_context(task, slot)
    
    logger.info("Task Context:")
    logger.info(f"  Task ID: {context.task_id}")
    logger.info(f"  Spec Name: {context.spec_name}")
    logger.info(f"  Title: {context.task_title}")
    logger.info(f"  Dependencies: {context.dependencies}")
    logger.info(f"  Required Skill: {context.required_skill}")
    logger.info(f"  Slot ID: {context.slot_id}")
    logger.info(f"  Slot Path: {context.slot_path}")
    logger.info(f"  Branch: {context.branch_name}")
    
    logger.info("\nJSON representation:")
    logger.info(context.to_json())


if __name__ == "__main__":
    # Run examples
    example_local_process_launch()
    example_task_context()
    
    # Uncomment to test Docker (requires Docker installed)
    # example_docker_launch()
    
    # Uncomment to test Kubernetes (requires K8s configured)
    # example_kubernetes_launch()
    
    # Uncomment to test retry behavior
    # example_retry_on_failure()
    
    logger.info("\n=== Examples Complete ===")

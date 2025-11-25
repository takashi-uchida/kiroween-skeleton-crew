"""
Example demonstrating different execution environments for Agent Runner.

This example shows how to use:
- LocalProcessRunner: Run tasks as local processes
- DockerRunner: Run tasks in Docker containers
- KubernetesRunner: Run tasks as Kubernetes Jobs
- create_runner: Factory function to create runners based on config

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
from pathlib import Path

from necrocode.agent_runner import (
    TaskContext,
    RunnerConfig,
    ExecutionMode,
    LocalProcessRunner,
    DockerRunner,
    KubernetesRunner,
    create_runner,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_task_context() -> TaskContext:
    """Create a sample task context for testing."""
    return TaskContext(
        task_id="1.1",
        spec_name="example-spec",
        title="Example Task",
        description="This is an example task for testing execution environments",
        acceptance_criteria=[
            "Task should execute successfully",
            "All tests should pass",
        ],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp/test-workspace"),
        slot_id="slot-1",
        branch_name="feature/task-1.1-example",
        timeout_seconds=300,
    )


def example_local_process_runner():
    """
    Example 1: Local Process Runner
    
    Runs tasks as local processes on the host machine.
    This is the simplest execution mode.
    """
    logger.info("=" * 60)
    logger.info("Example 1: Local Process Runner")
    logger.info("=" * 60)
    
    # Create configuration for local process mode
    config = RunnerConfig(
        execution_mode=ExecutionMode.LOCAL_PROCESS,
        log_level="INFO",
        default_timeout_seconds=300,
        artifact_store_url=f"file://{Path.home()}/.necrocode/artifacts",
    )
    
    # Create local process runner
    runner = LocalProcessRunner(config)
    
    # Validate environment
    try:
        runner.validate_environment()
        logger.info("✓ Environment validation passed")
    except Exception as e:
        logger.error(f"✗ Environment validation failed: {e}")
        return
    
    # Get environment info
    env_info = runner.get_environment_info()
    logger.info(f"Environment info: {env_info}")
    
    # Note: Actual execution would require a valid workspace
    # task_context = create_sample_task_context()
    # result = runner.execute(task_context)
    
    logger.info("Local process runner example completed\n")


def example_docker_runner():
    """
    Example 2: Docker Runner
    
    Runs tasks inside Docker containers for isolation and consistency.
    """
    logger.info("=" * 60)
    logger.info("Example 2: Docker Runner")
    logger.info("=" * 60)
    
    # Create configuration for Docker mode
    config = RunnerConfig(
        execution_mode=ExecutionMode.DOCKER,
        docker_image="necrocode/agent-runner:latest",
        docker_network="necrocode-network",
        docker_volumes={
            "/tmp/artifacts": "/artifacts",
        },
        max_memory_mb=2048,
        max_cpu_percent=80,
        log_level="INFO",
    )
    
    # Create Docker runner
    runner = DockerRunner(config)
    
    # Validate environment
    try:
        runner.validate_environment()
        logger.info("✓ Docker environment validation passed")
    except Exception as e:
        logger.error(f"✗ Docker environment validation failed: {e}")
        logger.info("Make sure Docker is installed and running")
        return
    
    # Get environment info
    env_info = runner.get_environment_info()
    logger.info(f"Environment info: {env_info}")
    
    # Note: Actual execution would require a valid workspace and Docker image
    # task_context = create_sample_task_context()
    # result = runner.execute(task_context)
    
    logger.info("Docker runner example completed\n")


def example_kubernetes_runner():
    """
    Example 3: Kubernetes Runner
    
    Runs tasks as Kubernetes Jobs for cloud-native execution.
    """
    logger.info("=" * 60)
    logger.info("Example 3: Kubernetes Runner")
    logger.info("=" * 60)
    
    # Create configuration for Kubernetes mode
    config = RunnerConfig(
        execution_mode=ExecutionMode.KUBERNETES,
        k8s_namespace="necrocode",
        k8s_service_account="necrocode-runner",
        k8s_resource_requests={
            "cpu": "500m",
            "memory": "512Mi",
        },
        k8s_resource_limits={
            "cpu": "2000m",
            "memory": "2Gi",
        },
        docker_image="necrocode/agent-runner:latest",
        log_level="INFO",
    )
    
    # Create Kubernetes runner
    runner = KubernetesRunner(config)
    
    # Validate environment
    try:
        runner.validate_environment()
        logger.info("✓ Kubernetes environment validation passed")
    except Exception as e:
        logger.error(f"✗ Kubernetes environment validation failed: {e}")
        logger.info("Make sure kubectl is installed and configured")
        return
    
    # Get environment info
    env_info = runner.get_environment_info()
    logger.info(f"Environment info: {env_info}")
    
    # Note: Actual execution would require a valid workspace and K8s cluster
    # task_context = create_sample_task_context()
    # result = runner.execute(task_context)
    
    logger.info("Kubernetes runner example completed\n")


def example_factory_function():
    """
    Example 4: Factory Function
    
    Use the create_runner factory function to create runners based on config.
    """
    logger.info("=" * 60)
    logger.info("Example 4: Factory Function")
    logger.info("=" * 60)
    
    # Create runners for different modes using factory function
    modes = [
        ExecutionMode.LOCAL_PROCESS,
        ExecutionMode.DOCKER,
        ExecutionMode.KUBERNETES,
    ]
    
    for mode in modes:
        config = RunnerConfig(
            execution_mode=mode,
            artifact_store_url=f"file://{Path.home()}/.necrocode/artifacts",
        )
        runner = create_runner(config)
        
        logger.info(f"Created runner for mode: {mode.value}")
        logger.info(f"  Runner type: {type(runner).__name__}")
        
        # Get environment info
        env_info = runner.get_environment_info()
        logger.info(f"  Execution mode: {env_info['execution_mode']}")
    
    logger.info("\nFactory function example completed\n")


def example_environment_switching():
    """
    Example 5: Environment Switching
    
    Demonstrates how to switch between execution environments dynamically.
    """
    logger.info("=" * 60)
    logger.info("Example 5: Environment Switching")
    logger.info("=" * 60)
    
    # Start with local process mode
    config = RunnerConfig(
        execution_mode=ExecutionMode.LOCAL_PROCESS,
        artifact_store_url=f"file://{Path.home()}/.necrocode/artifacts",
    )
    runner = create_runner(config)
    logger.info(f"Initial mode: {config.execution_mode.value}")
    
    # Switch to Docker mode
    config.execution_mode = ExecutionMode.DOCKER
    config.docker_image = "necrocode/agent-runner:latest"
    runner = create_runner(config)
    logger.info(f"Switched to: {config.execution_mode.value}")
    
    # Switch to Kubernetes mode
    config.execution_mode = ExecutionMode.KUBERNETES
    config.k8s_namespace = "necrocode"
    runner = create_runner(config)
    logger.info(f"Switched to: {config.execution_mode.value}")
    
    logger.info("\nEnvironment switching example completed\n")


def example_custom_configuration():
    """
    Example 6: Custom Configuration
    
    Shows how to customize runner configuration for different environments.
    """
    logger.info("=" * 60)
    logger.info("Example 6: Custom Configuration")
    logger.info("=" * 60)
    
    # Local process with custom settings
    local_config = RunnerConfig(
        execution_mode=ExecutionMode.LOCAL_PROCESS,
        default_timeout_seconds=600,
        max_memory_mb=4096,
        max_cpu_percent=90,
        log_level="DEBUG",
        persist_state=True,
    )
    logger.info("Local process config:")
    logger.info(f"  Timeout: {local_config.default_timeout_seconds}s")
    logger.info(f"  Max memory: {local_config.max_memory_mb}MB")
    logger.info(f"  Max CPU: {local_config.max_cpu_percent}%")
    
    # Docker with custom settings
    docker_config = RunnerConfig(
        execution_mode=ExecutionMode.DOCKER,
        docker_image="custom/runner:v1.0",
        docker_network="custom-network",
        docker_volumes={
            "/host/data": "/container/data",
            "/host/cache": "/container/cache",
        },
        max_memory_mb=2048,
    )
    logger.info("\nDocker config:")
    logger.info(f"  Image: {docker_config.docker_image}")
    logger.info(f"  Network: {docker_config.docker_network}")
    logger.info(f"  Volumes: {len(docker_config.docker_volumes)}")
    
    # Kubernetes with custom settings
    k8s_config = RunnerConfig(
        execution_mode=ExecutionMode.KUBERNETES,
        k8s_namespace="production",
        k8s_service_account="runner-sa",
        k8s_image_pull_secrets=["registry-secret"],
        k8s_resource_requests={
            "cpu": "1000m",
            "memory": "1Gi",
        },
        k8s_resource_limits={
            "cpu": "4000m",
            "memory": "4Gi",
        },
    )
    logger.info("\nKubernetes config:")
    logger.info(f"  Namespace: {k8s_config.k8s_namespace}")
    logger.info(f"  Service account: {k8s_config.k8s_service_account}")
    logger.info(f"  CPU request: {k8s_config.k8s_resource_requests['cpu']}")
    logger.info(f"  Memory limit: {k8s_config.k8s_resource_limits['memory']}")
    
    logger.info("\nCustom configuration example completed\n")


def main():
    """Run all examples."""
    logger.info("Agent Runner Execution Environment Examples")
    logger.info("=" * 60)
    logger.info("")
    
    # Run examples
    example_local_process_runner()
    example_docker_runner()
    example_kubernetes_runner()
    example_factory_function()
    example_environment_switching()
    example_custom_configuration()
    
    logger.info("=" * 60)
    logger.info("All examples completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

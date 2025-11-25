"""
Example usage of AgentPoolManager.

Demonstrates:
- Loading pool configurations
- Skill-based routing
- Load balancing
- Concurrency control
- Resource quota management
- Pool status monitoring
"""

import logging
from pathlib import Path
import tempfile
import yaml

from necrocode.dispatcher import (
    AgentPoolManager,
    DispatcherConfig,
    AgentPool,
    PoolType,
    SchedulingPolicy,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_config() -> Path:
    """Create a sample YAML configuration file."""
    config_data = {
        "dispatcher": {
            "poll_interval": 5,
            "scheduling_policy": "priority",
            "max_global_concurrency": 10,
            "heartbeat_timeout": 60,
            "retry_max_attempts": 3,
            "retry_backoff_base": 2.0,
        },
        "agent_pools": {
            "local": {
                "type": "local-process",
                "max_concurrency": 2,
                "enabled": True,
            },
            "docker": {
                "type": "docker",
                "max_concurrency": 4,
                "cpu_quota": 4,
                "memory_quota": 8192,
                "enabled": True,
                "config": {
                    "image": "necrocode/runner:latest",
                    "mount_repo_pool": True,
                },
            },
            "k8s": {
                "type": "kubernetes",
                "max_concurrency": 10,
                "cpu_quota": 10,
                "memory_quota": 20480,
                "enabled": True,
                "config": {
                    "namespace": "necrocode-agents",
                    "job_template": "manifests/runner-job.yaml",
                },
            },
        },
        "skill_mapping": {
            "backend": ["docker", "k8s"],
            "frontend": ["docker", "k8s"],
            "database": ["docker"],
            "devops": ["k8s"],
            "default": ["local"],
        },
    }
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        return Path(f.name)


def example_basic_usage():
    """Example: Basic AgentPoolManager usage."""
    logger.info("=== Basic Usage Example ===")
    
    # Create configuration
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        # List all pools
        logger.info(f"Loaded {len(manager.pools)} pools:")
        for pool_name, pool in manager.pools.items():
            logger.info(
                f"  - {pool_name}: type={pool.type.value}, "
                f"max_concurrency={pool.max_concurrency}, enabled={pool.enabled}"
            )
        
        # Get pool for specific skill
        backend_pool = manager.get_pool_for_skill("backend")
        if backend_pool:
            logger.info(f"Backend skill mapped to pool: {backend_pool.name}")
        
        # Get default pool
        default_pool = manager.get_default_pool()
        if default_pool:
            logger.info(f"Default pool: {default_pool.name}")
    
    finally:
        config_path.unlink()


def example_skill_routing():
    """Example: Skill-based routing."""
    logger.info("\n=== Skill-Based Routing Example ===")
    
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        # Test different skills
        skills = ["backend", "frontend", "database", "devops", "unknown-skill"]
        
        for skill in skills:
            pool = manager.get_pool_for_skill(skill)
            if pool:
                logger.info(f"Skill '{skill}' -> Pool '{pool.name}'")
            else:
                logger.warning(f"No pool available for skill '{skill}'")
    
    finally:
        config_path.unlink()


def example_load_balancing():
    """Example: Load balancing across pools."""
    logger.info("\n=== Load Balancing Example ===")
    
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        # Simulate different loads
        manager.pools["docker"].current_running = 3  # 75% utilization
        manager.pools["k8s"].current_running = 5  # 50% utilization
        
        logger.info("Current pool utilization:")
        logger.info(f"  docker: {manager.pools['docker'].current_running}/4 (75%)")
        logger.info(f"  k8s: {manager.pools['k8s'].current_running}/10 (50%)")
        
        # Get pool for backend skill (should select k8s - lower utilization)
        pool = manager.get_pool_for_skill("backend")
        logger.info(f"Selected pool for backend: {pool.name} (least loaded)")
    
    finally:
        config_path.unlink()


def example_concurrency_control():
    """Example: Concurrency control."""
    logger.info("\n=== Concurrency Control Example ===")
    
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        pool = manager.pools["local"]
        logger.info(f"Pool '{pool.name}' max_concurrency: {pool.max_concurrency}")
        
        # Simulate task assignments
        for i in range(3):
            if manager.can_accept_task(pool):
                manager.increment_running_count(pool)
                logger.info(
                    f"Task {i+1} assigned. Running: {pool.current_running}/{pool.max_concurrency}"
                )
            else:
                logger.warning(
                    f"Task {i+1} rejected. Pool at capacity: {pool.current_running}/{pool.max_concurrency}"
                )
        
        # Simulate task completions
        for i in range(2):
            manager.decrement_running_count(pool)
            logger.info(
                f"Task completed. Running: {pool.current_running}/{pool.max_concurrency}"
            )
    
    finally:
        config_path.unlink()


def example_resource_quotas():
    """Example: Resource quota management."""
    logger.info("\n=== Resource Quota Management Example ===")
    
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        pool = manager.pools["docker"]
        logger.info(f"Pool '{pool.name}' quotas:")
        logger.info(f"  CPU: {pool.cpu_quota} cores")
        logger.info(f"  Memory: {pool.memory_quota} MB")
        
        # Simulate resource usage
        manager.update_resource_usage("docker", cpu_delta=2.0, memory_delta=4096.0)
        logger.info("Allocated 2 CPU cores and 4096 MB memory")
        logger.info(
            f"Current usage: CPU={manager.resource_usage['docker']['cpu']}, "
            f"Memory={manager.resource_usage['docker']['memory']}"
        )
        
        # Check if pool can accept more tasks
        if manager.can_accept_task(pool):
            logger.info("Pool can accept more tasks")
        else:
            logger.warning("Pool cannot accept tasks (quota or concurrency limit reached)")
        
        # Try to exceed quota
        manager.update_resource_usage("docker", cpu_delta=3.0, memory_delta=5000.0)
        logger.info("Attempted to allocate 3 more CPU cores and 5000 MB memory")
        logger.info(
            f"Current usage: CPU={manager.resource_usage['docker']['cpu']}, "
            f"Memory={manager.resource_usage['docker']['memory']}"
        )
        
        if not manager.can_accept_task(pool):
            logger.warning("Pool rejected due to quota limits")
    
    finally:
        config_path.unlink()


def example_pool_status():
    """Example: Pool status monitoring."""
    logger.info("\n=== Pool Status Monitoring Example ===")
    
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        # Simulate some activity
        manager.pools["docker"].current_running = 2
        manager.update_resource_usage("docker", cpu_delta=2.5, memory_delta=4096.0)
        
        # Get status for specific pool
        status = manager.get_pool_status("docker")
        logger.info(f"Pool '{status.pool_name}' status:")
        logger.info(f"  Type: {status.type.value}")
        logger.info(f"  Enabled: {status.enabled}")
        logger.info(f"  Running: {status.current_running}/{status.max_concurrency}")
        logger.info(f"  Utilization: {status.utilization:.1%}")
        logger.info(f"  CPU Usage: {status.cpu_usage} cores")
        logger.info(f"  Memory Usage: {status.memory_usage} MB")
        
        # Get all pool statuses
        logger.info("\nAll pool statuses:")
        for status in manager.get_all_pool_statuses():
            logger.info(
                f"  {status.pool_name}: {status.current_running}/{status.max_concurrency} "
                f"({status.utilization:.1%})"
            )
    
    finally:
        config_path.unlink()


def example_pool_management():
    """Example: Enabling/disabling pools."""
    logger.info("\n=== Pool Management Example ===")
    
    config_path = create_sample_config()
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        # Disable a pool
        logger.info("Disabling 'docker' pool")
        manager.disable_pool("docker")
        
        # Try to get pool for backend skill
        pool = manager.get_pool_for_skill("backend")
        logger.info(f"Backend skill now routes to: {pool.name if pool else 'None'}")
        
        # Re-enable the pool
        logger.info("Re-enabling 'docker' pool")
        manager.enable_pool("docker")
        
        pool = manager.get_pool_for_skill("backend")
        logger.info(f"Backend skill now routes to: {pool.name if pool else 'None'}")
    
    finally:
        config_path.unlink()


def main():
    """Run all examples."""
    example_basic_usage()
    example_skill_routing()
    example_load_balancing()
    example_concurrency_control()
    example_resource_quotas()
    example_pool_status()
    example_pool_management()
    
    logger.info("\n=== All examples completed ===")


if __name__ == "__main__":
    main()

"""
Example: Using DispatcherCore to orchestrate task scheduling and assignment.

This example demonstrates:
1. Initializing DispatcherCore with configuration
2. Starting the dispatcher
3. Monitoring dispatcher status
4. Graceful shutdown
"""

import logging
import time
from pathlib import Path

from necrocode.dispatcher import DispatcherCore, DispatcherConfig, SchedulingPolicy
from necrocode.dispatcher.models import AgentPool, PoolType


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main example function."""
    
    logger.info("=" * 60)
    logger.info("DispatcherCore Example")
    logger.info("=" * 60)
    
    # 1. Create configuration
    logger.info("\n1. Creating Dispatcher configuration...")
    
    config = DispatcherConfig(
        poll_interval=5,
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=10,
        heartbeat_timeout=60,
        retry_max_attempts=3,
        graceful_shutdown_timeout=300,
    )
    
    # Define Agent Pools
    config.agent_pools = [
        AgentPool(
            name="local",
            type=PoolType.LOCAL_PROCESS,
            max_concurrency=2,
            enabled=True,
        ),
        AgentPool(
            name="docker",
            type=PoolType.DOCKER,
            max_concurrency=4,
            cpu_quota=4,
            memory_quota=8192,
            enabled=True,
            config={
                "image": "necrocode/runner:latest",
                "mount_repo_pool": True,
            }
        ),
    ]
    
    # Define skill mapping
    config.skill_mapping = {
        "backend": ["docker", "local"],
        "frontend": ["docker", "local"],
        "database": ["docker"],
        "default": ["local"],
    }
    
    logger.info(f"Configuration created with {len(config.agent_pools)} pools")
    
    # 2. Initialize DispatcherCore
    logger.info("\n2. Initializing DispatcherCore...")
    
    dispatcher = DispatcherCore(config=config)
    
    logger.info("DispatcherCore initialized successfully")
    
    # 3. Start the dispatcher
    logger.info("\n3. Starting Dispatcher...")
    
    dispatcher.start()
    
    logger.info("Dispatcher started and running")
    
    # 4. Monitor dispatcher status
    logger.info("\n4. Monitoring Dispatcher status...")
    
    try:
        for i in range(6):  # Monitor for 30 seconds (6 * 5 seconds)
            time.sleep(5)
            
            status = dispatcher.get_status()
            
            logger.info(f"\nDispatcher Status (iteration {i + 1}):")
            logger.info(f"  Running: {status['running']}")
            logger.info(f"  Queue Size: {status['queue_size']}")
            logger.info(f"  Running Tasks: {status['running_tasks']}")
            
            # Show pool statuses
            logger.info("  Pool Statuses:")
            for pool_status in status['pool_statuses']:
                logger.info(
                    f"    {pool_status.pool_name}: "
                    f"{pool_status.current_running}/{pool_status.max_concurrency} "
                    f"(utilization: {pool_status.utilization:.2%})"
                )
            
            # Show metrics
            metrics = status['metrics']
            if metrics:
                logger.info("  Metrics:")
                logger.info(f"    Queue Size: {metrics.get('queue_size', 0)}")
                logger.info(f"    Running Tasks: {metrics.get('running_tasks', 0)}")
                logger.info(f"    Avg Wait Time: {metrics.get('average_wait_time', 0):.2f}s")
    
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
    
    # 5. Graceful shutdown
    logger.info("\n5. Stopping Dispatcher (graceful shutdown)...")
    
    dispatcher.stop(timeout=60)
    
    logger.info("Dispatcher stopped successfully")
    
    # 6. Final status
    logger.info("\n6. Final Dispatcher status:")
    
    final_status = dispatcher.get_status()
    logger.info(f"  Running: {final_status['running']}")
    logger.info(f"  Queue Size: {final_status['queue_size']}")
    logger.info(f"  Running Tasks: {final_status['running_tasks']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Example completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

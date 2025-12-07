#!/usr/bin/env python3
"""
Dispatcher Main Entry Point

Runs the Dispatcher as a standalone service.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from necrocode.dispatcher.dispatcher_core import DispatcherCore
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolType, SchedulingPolicy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file: Path) -> DispatcherConfig:
    """
    Load Dispatcher configuration from file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        DispatcherConfig instance
    """
    logger.info(f"Loading configuration from {config_file}")
    
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    # Create config
    config = DispatcherConfig(
        poll_interval=config_data.get('poll_interval', 5),
        scheduling_policy=SchedulingPolicy(config_data.get('scheduling_policy', 'priority')),
        max_global_concurrency=config_data.get('max_global_concurrency', 10),
        heartbeat_timeout=config_data.get('heartbeat_timeout', 60),
        retry_max_attempts=config_data.get('retry_max_attempts', 3),
        retry_backoff_base=config_data.get('retry_backoff_base', 2.0),
        graceful_shutdown_timeout=config_data.get('graceful_shutdown_timeout', 300),
        task_registry_dir=config_data.get('task_registry_dir')
    )
    
    # Load agent pools
    config.agent_pools = []
    for pool_data in config_data.get('agent_pools', []):
        pool = AgentPool(
            name=pool_data['name'],
            type=PoolType(pool_data['type']),
            max_concurrency=pool_data.get('max_concurrency', 1),
            cpu_quota=pool_data.get('cpu_quota'),
            memory_quota=pool_data.get('memory_quota'),
            enabled=pool_data.get('enabled', True),
            config=pool_data.get('config', {})
        )
        config.agent_pools.append(pool)
    
    # Load skill mapping
    config.skill_mapping = config_data.get('skill_mapping', {})
    
    logger.info(f"Configuration loaded: {len(config.agent_pools)} agent pools")
    
    return config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='NecroCode Dispatcher - Task scheduling and agent management'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        required=True,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Create and start dispatcher
    logger.info("Starting Dispatcher...")
    
    try:
        dispatcher = DispatcherCore(config)
        dispatcher.start()
        
        # Keep running until interrupted
        import signal
        import time
        
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            dispatcher.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep alive
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Dispatcher failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

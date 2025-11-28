#!/usr/bin/env python3
"""
Review PR Service Main Entry Point

Runs the Review PR Service as a standalone webhook server.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from necrocode.review_pr_service.webhook_handler import WebhookHandler
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import PRServiceConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file: Path) -> PRServiceConfig:
    """
    Load PR Service configuration from file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        PRServiceConfig instance
    """
    logger.info(f"Loading configuration from {config_file}")
    
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    # Create config
    config = PRServiceConfig(
        git_host=config_data.get('git_host', 'github'),
        webhook_port=config_data.get('webhook_port', 8080),
        auto_create_pr=config_data.get('auto_create_pr', True),
        auto_assign_reviewers=config_data.get('auto_assign_reviewers', False),
        default_labels=config_data.get('default_labels', [])
    )
    
    logger.info(f"Configuration loaded: git_host={config.git_host}, port={config.webhook_port}")
    
    return config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='NecroCode Review PR Service - Automated PR management'
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
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind webhook server (default: 0.0.0.0)'
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
    
    # Create PR Service
    logger.info("Initializing PR Service...")
    
    try:
        pr_service = PRService(config=config)
        
        # Create webhook handler
        webhook_handler = WebhookHandler(pr_service=pr_service)
        
        # Start webhook server
        logger.info(f"Starting webhook server on {args.host}:{config.webhook_port}...")
        
        webhook_handler.start_server(
            host=args.host,
            port=config.webhook_port
        )
        
    except Exception as e:
        logger.error(f"PR Service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

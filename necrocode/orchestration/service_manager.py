"""
Service Manager - Manages lifecycle of all NecroCode services

Coordinates:
- Task Registry
- Repo Pool Manager
- Dispatcher
- Review PR Service
- Artifact Store
"""

import json
import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ServiceManager:
    """
    Manages lifecycle of all NecroCode services.
    
    Provides unified interface for:
    - Service configuration
    - Starting/stopping services
    - Health monitoring
    - Log aggregation
    """
    
    SERVICES = [
        'task_registry',
        'repo_pool',
        'dispatcher',
        'artifact_store',
        'review_pr_service'
    ]
    
    def __init__(
        self,
        workspace_root: Path = Path('.'),
        config_dir: Path = Path('.necrocode')
    ):
        """
        Initialize Service Manager.
        
        Args:
            workspace_root: Root directory of workspace
            config_dir: Directory for configuration files
        """
        self.workspace_root = workspace_root
        self.config_dir = workspace_root / config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.pid_dir = self.config_dir / 'pids'
        self.pid_dir.mkdir(exist_ok=True)
        
        self.log_dir = self.config_dir / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        self.data_dir = self.config_dir / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        logger.info(f"ServiceManager initialized: config_dir={self.config_dir}")
    
    def setup_all_services(self) -> None:
        """Create default configuration for all services."""
        logger.info("Setting up all services...")
        
        # Create config files
        self._create_task_registry_config()
        self._create_repo_pool_config()
        self._create_dispatcher_config()
        self._create_artifact_store_config()
        self._create_review_pr_service_config()
        
        logger.info("All service configurations created")
    
    def _create_task_registry_config(self) -> None:
        """Create Task Registry configuration."""
        config_file = self.config_dir / 'task_registry.json'
        
        if config_file.exists():
            logger.info("Task Registry config already exists")
            return
        
        config = {
            "registry_dir": str(self.data_dir / 'task_registry'),
            "enable_locking": True,
            "lock_timeout": 30,
            "enable_events": True
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created Task Registry config: {config_file}")
    
    def _create_repo_pool_config(self) -> None:
        """Create Repo Pool Manager configuration."""
        config_file = self.config_dir / 'repo_pool.json'
        
        if config_file.exists():
            logger.info("Repo Pool config already exists")
            return
        
        config = {
            "pool_root": str(self.data_dir / 'repo_pool'),
            "max_slots_per_repo": 10,
            "cleanup_on_release": True,
            "enable_locking": True
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created Repo Pool config: {config_file}")
    
    def _create_dispatcher_config(self) -> None:
        """Create Dispatcher configuration."""
        config_file = self.config_dir / 'dispatcher.json'
        
        if config_file.exists():
            logger.info("Dispatcher config already exists")
            return
        
        config = {
            "poll_interval": 5,
            "scheduling_policy": "priority",
            "max_global_concurrency": 10,
            "heartbeat_timeout": 60,
            "retry_max_attempts": 3,
            "task_registry_dir": str(self.data_dir / 'task_registry'),
            "agent_pools": [
                {
                    "name": "local",
                    "type": "local_process",
                    "max_concurrency": 2,
                    "enabled": True
                },
                {
                    "name": "docker",
                    "type": "docker",
                    "max_concurrency": 5,
                    "cpu_quota": 4,
                    "memory_quota": 8192,
                    "enabled": True,
                    "config": {
                        "image": "necrocode/runner:latest"
                    }
                }
            ],
            "skill_mapping": {
                "backend": ["docker"],
                "frontend": ["docker"],
                "database": ["docker"],
                "default": ["local"]
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created Dispatcher config: {config_file}")
    
    def _create_artifact_store_config(self) -> None:
        """Create Artifact Store configuration."""
        config_file = self.config_dir / 'artifact_store.json'
        
        if config_file.exists():
            logger.info("Artifact Store config already exists")
            return
        
        config = {
            "storage_backend": "local",
            "storage_root": str(self.data_dir / 'artifacts'),
            "enable_compression": True,
            "enable_versioning": True,
            "retention_days": 30
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created Artifact Store config: {config_file}")
    
    def _create_review_pr_service_config(self) -> None:
        """Create Review PR Service configuration."""
        config_file = self.config_dir / 'review_pr_service.json'
        
        if config_file.exists():
            logger.info("Review PR Service config already exists")
            return
        
        config = {
            "git_host": "github",
            "webhook_port": 8080,
            "auto_create_pr": True,
            "auto_assign_reviewers": False,
            "default_labels": ["necrocode", "automated"]
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created Review PR Service config: {config_file}")
    
    def start_services(
        self,
        services: Optional[List[str]] = None,
        detached: bool = False
    ) -> None:
        """
        Start NecroCode services.
        
        Args:
            services: List of services to start (None = all)
            detached: Run services in background
        """
        services_to_start = services or self.SERVICES
        
        logger.info(f"Starting services: {services_to_start}")
        
        for service in services_to_start:
            if service not in self.SERVICES:
                logger.warning(f"Unknown service: {service}")
                continue
            
            self._start_service(service, detached=detached)
        
        logger.info("All services started")
    
    def _start_service(self, service: str, detached: bool = False) -> None:
        """Start a specific service."""
        logger.info(f"Starting {service}...")
        
        # Check if already running
        if self._is_service_running(service):
            logger.warning(f"{service} is already running")
            return
        
        # Service-specific startup
        if service == 'dispatcher':
            self._start_dispatcher(detached)
        elif service == 'review_pr_service':
            self._start_review_pr_service(detached)
        else:
            logger.info(f"{service} runs as library (no daemon process)")
    
    def _start_dispatcher(self, detached: bool) -> None:
        """Start Dispatcher service."""
        config_file = self.config_dir / 'dispatcher.json'
        log_file = self.log_dir / 'dispatcher.log'
        pid_file = self.pid_dir / 'dispatcher.pid'
        
        cmd = [
            'python', '-m', 'necrocode.dispatcher.main',
            '--config', str(config_file)
        ]
        
        if detached:
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            # Save PID
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            logger.info(f"Dispatcher started (PID: {process.pid})")
        else:
            subprocess.run(cmd)
    
    def _start_review_pr_service(self, detached: bool) -> None:
        """Start Review PR Service."""
        config_file = self.config_dir / 'review_pr_service.json'
        log_file = self.log_dir / 'review_pr_service.log'
        pid_file = self.pid_dir / 'review_pr_service.pid'
        
        cmd = [
            'python', '-m', 'necrocode.review_pr_service.main',
            '--config', str(config_file)
        ]
        
        if detached:
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            # Save PID
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            logger.info(f"Review PR Service started (PID: {process.pid})")
        else:
            subprocess.run(cmd)
    
    def stop_services(
        self,
        services: Optional[List[str]] = None,
        timeout: int = 30
    ) -> None:
        """
        Stop NecroCode services.
        
        Args:
            services: List of services to stop (None = all)
            timeout: Timeout for graceful shutdown
        """
        services_to_stop = services or self.SERVICES
        
        logger.info(f"Stopping services: {services_to_stop}")
        
        for service in services_to_stop:
            if service not in self.SERVICES:
                logger.warning(f"Unknown service: {service}")
                continue
            
            self._stop_service(service, timeout)
        
        logger.info("All services stopped")
    
    def _stop_service(self, service: str, timeout: int) -> None:
        """Stop a specific service."""
        logger.info(f"Stopping {service}...")
        
        pid_file = self.pid_dir / f'{service}.pid'
        
        if not pid_file.exists():
            logger.info(f"{service} is not running")
            return
        
        # Read PID
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Send SIGTERM
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to {service} (PID: {pid})")
            
            # Wait for graceful shutdown
            for _ in range(timeout):
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(1)
                except OSError:
                    break
            else:
                # Force kill
                logger.warning(f"Force killing {service}")
                os.kill(pid, signal.SIGKILL)
            
            # Remove PID file
            pid_file.unlink()
            logger.info(f"{service} stopped")
            
        except OSError as e:
            logger.warning(f"Failed to stop {service}: {e}")
            pid_file.unlink(missing_ok=True)
    
    def _is_service_running(self, service: str) -> bool:
        """Check if a service is running."""
        pid_file = self.pid_dir / f'{service}.pid'
        
        if not pid_file.exists():
            return False
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            # Process doesn't exist or invalid PID
            pid_file.unlink(missing_ok=True)
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {}
        
        for service in self.SERVICES:
            running = self._is_service_running(service)
            
            service_status = {
                'running': running,
                'pid': None,
                'metrics': {}
            }
            
            if running:
                pid_file = self.pid_dir / f'{service}.pid'
                if pid_file.exists():
                    with open(pid_file, 'r') as f:
                        service_status['pid'] = int(f.read().strip())
            
            status[service] = service_status
        
        return status
    
    def show_logs(
        self,
        service: Optional[str] = None,
        follow: bool = False,
        lines: int = 100
    ) -> None:
        """
        Show service logs.
        
        Args:
            service: Specific service (None = all)
            follow: Follow log output
            lines: Number of lines to show
        """
        if service:
            log_file = self.log_dir / f'{service}.log'
            if not log_file.exists():
                print(f"No logs for {service}")
                return
            
            if follow:
                subprocess.run(['tail', '-f', '-n', str(lines), str(log_file)])
            else:
                subprocess.run(['tail', '-n', str(lines), str(log_file)])
        else:
            # Show all logs
            for service in self.SERVICES:
                log_file = self.log_dir / f'{service}.log'
                if log_file.exists():
                    print(f"\n{'='*60}")
                    print(f"{service.upper()} LOGS")
                    print('='*60)
                    subprocess.run(['tail', '-n', str(lines), str(log_file)])

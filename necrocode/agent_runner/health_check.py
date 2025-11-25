"""
Health check endpoint for Agent Runner.

This module provides a simple HTTP health check endpoint for Kubernetes
and other orchestration systems to monitor runner health.

Requirements: 12.5
"""

import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class HealthStatus:
    """
    Health status information.
    
    Tracks the current health state of the runner including:
    - Overall status (healthy/unhealthy)
    - Runner state
    - Current task information
    - Uptime
    - Last check time
    - External service connectivity
    """
    
    def __init__(self):
        """Initialize health status."""
        self.healthy = True
        self.runner_state = "idle"
        self.runner_id: Optional[str] = None
        self.current_task_id: Optional[str] = None
        self.current_spec_name: Optional[str] = None
        self.start_time = datetime.now()
        self.last_check_time = datetime.now()
        self.details: Dict[str, Any] = {}
        self.external_services: Dict[str, bool] = {}
    
    def update(
        self,
        healthy: bool = True,
        runner_state: str = "idle",
        runner_id: Optional[str] = None,
        current_task_id: Optional[str] = None,
        current_spec_name: Optional[str] = None,
        **details
    ) -> None:
        """
        Update health status.
        
        Args:
            healthy: Whether the runner is healthy
            runner_state: Current runner state
            runner_id: Runner ID
            current_task_id: Current task ID
            current_spec_name: Current spec name
            **details: Additional status details
        """
        self.healthy = healthy
        self.runner_state = runner_state
        if runner_id is not None:
            self.runner_id = runner_id
        self.current_task_id = current_task_id
        self.current_spec_name = current_spec_name
        self.last_check_time = datetime.now()
        self.details.update(details)
    
    def update_service_status(self, service_name: str, healthy: bool) -> None:
        """
        Update external service status.
        
        Args:
            service_name: Name of the service (e.g., "task_registry", "llm_service")
            healthy: Whether the service is healthy
        """
        self.external_services[service_name] = healthy
        self.last_check_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of health status
        """
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "status": "healthy" if self.healthy else "unhealthy",
            "runner_id": self.runner_id,
            "runner_state": self.runner_state,
            "current_task": {
                "task_id": self.current_task_id,
                "spec_name": self.current_spec_name,
            } if self.current_task_id else None,
            "uptime_seconds": uptime_seconds,
            "last_check": self.last_check_time.isoformat(),
            "external_services": self.external_services,
            "details": self.details,
        }


class HealthCheckHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for health check endpoint.
    
    Handles GET requests to /health and /ready endpoints.
    """
    
    # Class variable to store health status
    health_status: Optional[HealthStatus] = None
    
    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health" or self.path == "/healthz":
            self._handle_health()
        elif self.path == "/ready" or self.path == "/readiness":
            self._handle_readiness()
        else:
            self.send_error(404, "Not Found")
    
    def _handle_health(self) -> None:
        """
        Handle health check request.
        
        Returns 200 if healthy, 503 if unhealthy.
        """
        if not self.health_status:
            self.send_error(503, "Health status not initialized")
            return
        
        status_dict = self.health_status.to_dict()
        status_code = 200 if self.health_status.healthy else 503
        
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        response = json.dumps(status_dict, indent=2)
        self.wfile.write(response.encode())
    
    def _handle_readiness(self) -> None:
        """
        Handle readiness check request.
        
        Returns 200 if ready to accept tasks, 503 if not ready.
        """
        if not self.health_status:
            self.send_error(503, "Health status not initialized")
            return
        
        # Ready if healthy and in idle state
        ready = (
            self.health_status.healthy and
            self.health_status.runner_state in ["idle", "completed"]
        )
        
        status_code = 200 if ready else 503
        
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        response = json.dumps({
            "ready": ready,
            "runner_state": self.health_status.runner_state,
        }, indent=2)
        self.wfile.write(response.encode())
    
    def log_message(self, format: str, *args) -> None:
        """Override to use Python logging instead of stderr."""
        logger.debug(f"Health check request: {format % args}")


class HealthCheckServer:
    """
    HTTP server for health check endpoint.
    
    Runs in a background thread and provides health check endpoints
    for Kubernetes and other orchestration systems.
    
    Requirements: 12.5
    """
    
    def __init__(
        self,
        port: int = 8080,
        host: str = "0.0.0.0",
        health_status: Optional[HealthStatus] = None
    ):
        """
        Initialize health check server.
        
        Args:
            port: Port to listen on
            host: Host to bind to
            health_status: Health status object to expose
        """
        self.port = port
        self.host = host
        self.health_status = health_status or HealthStatus()
        
        # Set health status on handler class
        HealthCheckHandler.health_status = self.health_status
        
        # Server and thread
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
    
    def start(self) -> None:
        """
        Start health check server in background thread.
        
        The server will run until stop() is called.
        """
        if self.running:
            logger.warning("Health check server already running")
            return
        
        try:
            # Create server
            self.server = HTTPServer((self.host, self.port), HealthCheckHandler)
            
            # Start server in background thread
            self.thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name="HealthCheckServer"
            )
            self.running = True
            self.thread.start()
            
            logger.info(f"Health check server started on {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            self.running = False
            raise
    
    def _run_server(self) -> None:
        """Run server loop (called in background thread)."""
        if not self.server:
            return
        
        try:
            # Use serve_forever which can be interrupted by shutdown()
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Health check server error: {e}")
        finally:
            self.running = False
    
    def stop(self) -> None:
        """
        Stop health check server.
        
        Shuts down the server and waits for the background thread to exit.
        """
        if not self.running:
            return
        
        logger.info("Stopping health check server")
        self.running = False
        
        if self.server:
            try:
                # shutdown() must be called before server_close()
                # This will interrupt serve_forever() in the background thread
                self.server.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down health check server: {e}")
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        # Now close the server socket
        if self.server:
            try:
                self.server.server_close()
            except Exception as e:
                logger.warning(f"Error closing health check server: {e}")
        
        logger.info("Health check server stopped")
    
    def update_status(
        self,
        healthy: bool = True,
        runner_state: str = "idle",
        **kwargs
    ) -> None:
        """
        Update health status.
        
        Args:
            healthy: Whether the runner is healthy
            runner_state: Current runner state
            **kwargs: Additional status details
        """
        self.health_status.update(
            healthy=healthy,
            runner_state=runner_state,
            **kwargs
        )


def create_health_check_server(
    port: int = 8080,
    host: str = "0.0.0.0",
    runner_id: Optional[str] = None
) -> HealthCheckServer:
    """
    Create and configure a health check server.
    
    Args:
        port: Port to listen on
        host: Host to bind to
        runner_id: Runner ID to include in health status
        
    Returns:
        Configured health check server
        
    Requirements: 12.5
    """
    health_status = HealthStatus()
    if runner_id:
        health_status.runner_id = runner_id
    
    return HealthCheckServer(
        port=port,
        host=host,
        health_status=health_status
    )


def check_external_services(
    task_registry_client: Optional[Any] = None,
    repo_pool_client: Optional[Any] = None,
    artifact_store_client: Optional[Any] = None,
    llm_client: Optional[Any] = None
) -> Dict[str, bool]:
    """
    Check connectivity to external services.
    
    Args:
        task_registry_client: Task Registry client (optional)
        repo_pool_client: Repo Pool client (optional)
        artifact_store_client: Artifact Store client (optional)
        llm_client: LLM client (optional)
        
    Returns:
        Dictionary mapping service names to health status
        
    Requirements: 12.5, 15.5, 16.6
    """
    service_status = {}
    
    # Check Task Registry
    if task_registry_client:
        try:
            logger.debug("Checking Task Registry connectivity")
            healthy = task_registry_client.health_check()
            service_status["task_registry"] = healthy
            logger.info(f"Task Registry health check: {'healthy' if healthy else 'unhealthy'}")
        except Exception as e:
            logger.warning(f"Task Registry health check failed: {e}")
            service_status["task_registry"] = False
    
    # Check Repo Pool Manager
    if repo_pool_client:
        try:
            logger.debug("Checking Repo Pool Manager connectivity")
            healthy = repo_pool_client.health_check()
            service_status["repo_pool"] = healthy
            logger.info(f"Repo Pool Manager health check: {'healthy' if healthy else 'unhealthy'}")
        except Exception as e:
            logger.warning(f"Repo Pool Manager health check failed: {e}")
            service_status["repo_pool"] = False
    
    # Check Artifact Store
    if artifact_store_client:
        try:
            logger.debug("Checking Artifact Store connectivity")
            healthy = artifact_store_client.health_check()
            service_status["artifact_store"] = healthy
            logger.info(f"Artifact Store health check: {'healthy' if healthy else 'unhealthy'}")
        except Exception as e:
            logger.warning(f"Artifact Store health check failed: {e}")
            service_status["artifact_store"] = False
    
    # Check LLM Service
    if llm_client:
        try:
            logger.debug("Checking LLM service connectivity")
            # Simple check: try to access the client's configuration
            # A full check would require a test API call, but that may consume tokens
            healthy = hasattr(llm_client, 'client') and llm_client.client is not None
            service_status["llm_service"] = healthy
            logger.info(f"LLM service health check: {'healthy' if healthy else 'unhealthy'}")
        except Exception as e:
            logger.warning(f"LLM service health check failed: {e}")
            service_status["llm_service"] = False
    
    return service_status

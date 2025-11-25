"""
Configuration classes for Agent Runner.

This module defines configuration structures for controlling
Agent Runner behavior, including execution mode, timeouts,
retry policies, and resource limits.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class ExecutionMode(Enum):
    """
    Execution mode for Agent Runner.
    
    Determines how the runner executes tasks:
    - LOCAL_PROCESS: Run as a local process
    - DOCKER: Run inside a Docker container
    - KUBERNETES: Run as a Kubernetes Job
    """
    LOCAL_PROCESS = "local-process"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


@dataclass
class RetryConfig:
    """
    Retry configuration with exponential backoff.
    
    Defines retry behavior for transient failures such as
    network errors or temporary Git operation failures.
    """
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate retry delay using exponential backoff.
        
        Args:
            attempt: The retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds before the next retry
        """
        delay = self.initial_delay_seconds * (self.exponential_base ** attempt)
        return min(delay, self.max_delay_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_retries": self.max_retries,
            "initial_delay_seconds": self.initial_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "exponential_base": self.exponential_base,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetryConfig":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class RunnerConfig:
    """
    Main configuration for Agent Runner.
    
    Controls all aspects of runner behavior including execution mode,
    timeouts, retry policies, resource limits, logging, and security.
    """
    # Execution environment
    execution_mode: ExecutionMode = ExecutionMode.LOCAL_PROCESS
    
    # Timeout settings
    default_timeout_seconds: int = 1800  # 30 minutes
    
    # Retry policies
    git_retry_config: RetryConfig = field(default_factory=lambda: RetryConfig(max_retries=3))
    network_retry_config: RetryConfig = field(default_factory=lambda: RetryConfig(max_retries=3))
    
    # Resource limits
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[int] = None
    
    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True
    log_file: Optional[Path] = None
    
    # Security
    git_token_env_var: str = "GIT_TOKEN"
    mask_secrets: bool = True
    
    # Artifact Store
    artifact_store_url: str = "file://~/.necrocode/artifacts"
    artifact_store_api_key_env_var: str = "ARTIFACT_STORE_API_KEY"
    
    # Task Registry
    task_registry_path: Optional[Path] = None
    task_registry_url: Optional[str] = None  # REST API URL for Task Registry
    
    # Repo Pool Manager
    repo_pool_url: Optional[str] = None  # REST API URL for Repo Pool Manager
    
    # Playbook
    default_playbook_path: Optional[Path] = None
    
    # LLM Configuration
    llm_api_key: Optional[str] = None  # LLM API key (e.g., OpenAI)
    llm_api_key_env_var: str = "LLM_API_KEY"
    llm_model: str = "gpt-4"
    llm_endpoint: Optional[str] = None
    llm_timeout_seconds: int = 120
    llm_max_tokens: int = 4000
    
    # Kiro integration (legacy)
    kiro_api_url: Optional[str] = None
    kiro_api_key_env_var: str = "KIRO_API_KEY"
    
    # A2A Protocol (Agent-to-Agent communication)
    message_bus_config: Dict[str, Any] = field(default_factory=dict)
    registry_storage: Optional[Path] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    # Docker-specific settings
    docker_image: str = "necrocode/agent-runner:latest"
    docker_network: Optional[str] = None
    docker_volumes: Dict[str, str] = field(default_factory=dict)
    
    # Kubernetes-specific settings
    k8s_namespace: str = "necrocode"
    k8s_service_account: Optional[str] = None
    k8s_image_pull_secrets: list = field(default_factory=list)
    k8s_resource_requests: Dict[str, str] = field(default_factory=lambda: {
        "cpu": "500m",
        "memory": "512Mi"
    })
    k8s_resource_limits: Dict[str, str] = field(default_factory=lambda: {
        "cpu": "2000m",
        "memory": "2Gi"
    })
    
    # Monitoring and health checks
    enable_health_check: bool = False
    health_check_port: int = 8080
    metrics_enabled: bool = False
    metrics_port: int = 9090
    
    # Parallel execution
    max_parallel_runners: Optional[int] = None
    
    # State persistence
    persist_state: bool = False
    state_file_path: Optional[Path] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_mode": self.execution_mode.value,
            "default_timeout_seconds": self.default_timeout_seconds,
            "git_retry_config": self.git_retry_config.to_dict(),
            "network_retry_config": self.network_retry_config.to_dict(),
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "log_level": self.log_level,
            "structured_logging": self.structured_logging,
            "log_file": str(self.log_file) if self.log_file else None,
            "git_token_env_var": self.git_token_env_var,
            "mask_secrets": self.mask_secrets,
            "artifact_store_url": self.artifact_store_url,
            "artifact_store_api_key_env_var": self.artifact_store_api_key_env_var,
            "task_registry_path": str(self.task_registry_path) if self.task_registry_path else None,
            "task_registry_url": self.task_registry_url,
            "repo_pool_url": self.repo_pool_url,
            "default_playbook_path": str(self.default_playbook_path) if self.default_playbook_path else None,
            "llm_api_key": self.llm_api_key,
            "llm_api_key_env_var": self.llm_api_key_env_var,
            "llm_model": self.llm_model,
            "llm_endpoint": self.llm_endpoint,
            "llm_timeout_seconds": self.llm_timeout_seconds,
            "llm_max_tokens": self.llm_max_tokens,
            "kiro_api_url": self.kiro_api_url,
            "kiro_api_key_env_var": self.kiro_api_key_env_var,
            "message_bus_config": self.message_bus_config,
            "registry_storage": str(self.registry_storage) if self.registry_storage else None,
            "capabilities": self.capabilities,
            "docker_image": self.docker_image,
            "docker_network": self.docker_network,
            "docker_volumes": self.docker_volumes,
            "k8s_namespace": self.k8s_namespace,
            "k8s_service_account": self.k8s_service_account,
            "k8s_image_pull_secrets": self.k8s_image_pull_secrets,
            "k8s_resource_requests": self.k8s_resource_requests,
            "k8s_resource_limits": self.k8s_resource_limits,
            "enable_health_check": self.enable_health_check,
            "health_check_port": self.health_check_port,
            "metrics_enabled": self.metrics_enabled,
            "metrics_port": self.metrics_port,
            "max_parallel_runners": self.max_parallel_runners,
            "persist_state": self.persist_state,
            "state_file_path": str(self.state_file_path) if self.state_file_path else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerConfig":
        """Create from dictionary."""
        data = data.copy()
        
        # Convert execution mode
        if "execution_mode" in data:
            data["execution_mode"] = ExecutionMode(data["execution_mode"])
        
        # Convert retry configs
        if "git_retry_config" in data:
            data["git_retry_config"] = RetryConfig.from_dict(data["git_retry_config"])
        if "network_retry_config" in data:
            data["network_retry_config"] = RetryConfig.from_dict(data["network_retry_config"])
        
        # Convert paths
        if "log_file" in data and data["log_file"]:
            data["log_file"] = Path(data["log_file"])
        if "task_registry_path" in data and data["task_registry_path"]:
            data["task_registry_path"] = Path(data["task_registry_path"])
        if "default_playbook_path" in data and data["default_playbook_path"]:
            data["default_playbook_path"] = Path(data["default_playbook_path"])
        if "registry_storage" in data and data["registry_storage"]:
            data["registry_storage"] = Path(data["registry_storage"])
        if "state_file_path" in data and data["state_file_path"]:
            data["state_file_path"] = Path(data["state_file_path"])
        
        return cls(**data)
    
    def validate(self) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if self.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive")
        
        if self.max_memory_mb is not None and self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        
        if self.max_cpu_percent is not None and (self.max_cpu_percent <= 0 or self.max_cpu_percent > 100):
            raise ValueError("max_cpu_percent must be between 1 and 100")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log_level: {self.log_level}")
        
        if self.max_parallel_runners is not None and self.max_parallel_runners <= 0:
            raise ValueError("max_parallel_runners must be positive")

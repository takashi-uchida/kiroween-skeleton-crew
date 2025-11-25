"""
Configuration classes for the Dispatcher component.

Defines configuration structures for dispatcher behavior and Agent Pool management.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from necrocode.dispatcher.models import AgentPool, SchedulingPolicy, PoolType


def load_config(config_path: Path) -> "DispatcherConfig":
    """
    Load dispatcher configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        DispatcherConfig instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid
    """
    return DispatcherConfig.from_yaml(config_path)


@dataclass
class DispatcherConfig:
    """
    Dispatcher configuration.
    
    Controls dispatcher behavior including polling intervals, scheduling policies,
    concurrency limits, and Agent Pool definitions.
    """
    # Polling and scheduling
    poll_interval: int = 5  # seconds
    scheduling_policy: SchedulingPolicy = SchedulingPolicy.PRIORITY
    max_global_concurrency: int = 10
    
    # Monitoring
    heartbeat_timeout: int = 60  # seconds
    
    # Retry behavior
    retry_max_attempts: int = 3
    retry_backoff_base: float = 2.0
    
    # Shutdown
    graceful_shutdown_timeout: int = 300  # seconds
    
    # Task Registry
    task_registry_dir: Optional[Path] = None  # Path to Task Registry data directory
    
    # Agent Pool configuration
    agent_pools: List[AgentPool] = field(default_factory=list)
    skill_mapping: Dict[str, List[str]] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "DispatcherConfig":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            DispatcherConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config format is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Empty configuration file")
        
        dispatcher_config = data.get("dispatcher", {})
        agent_pools_config = data.get("agent_pools", {})
        skill_mapping = data.get("skill_mapping", {})
        
        # Parse scheduling policy
        policy_str = dispatcher_config.get("scheduling_policy", "priority")
        try:
            scheduling_policy = SchedulingPolicy(policy_str)
        except ValueError:
            scheduling_policy = SchedulingPolicy.PRIORITY
        
        # Parse retry configuration (support both flat and nested structure)
        retry_config = dispatcher_config.get("retry", {})
        retry_max_attempts = retry_config.get("max_attempts", dispatcher_config.get("retry_max_attempts", 3))
        retry_backoff_base = retry_config.get("backoff_base", dispatcher_config.get("retry_backoff_base", 2.0))
        
        # Parse graceful shutdown configuration
        shutdown_config = dispatcher_config.get("graceful_shutdown", {})
        graceful_shutdown_timeout = shutdown_config.get("timeout", dispatcher_config.get("graceful_shutdown_timeout", 300))
        
        # Parse agent pools
        agent_pools = []
        for pool_name, pool_config in agent_pools_config.items():
            pool_type_str = pool_config.get("type", "local-process")
            try:
                pool_type = PoolType(pool_type_str)
            except ValueError:
                pool_type = PoolType.LOCAL_PROCESS
            
            agent_pool = AgentPool(
                name=pool_name,
                type=pool_type,
                max_concurrency=pool_config.get("max_concurrency", 1),
                cpu_quota=pool_config.get("cpu_quota"),
                memory_quota=pool_config.get("memory_quota"),
                enabled=pool_config.get("enabled", True),
                config=pool_config.get("config", {}),
            )
            agent_pools.append(agent_pool)
        
        return cls(
            poll_interval=dispatcher_config.get("poll_interval", 5),
            scheduling_policy=scheduling_policy,
            max_global_concurrency=dispatcher_config.get("max_global_concurrency", 10),
            heartbeat_timeout=dispatcher_config.get("heartbeat_timeout", 60),
            retry_max_attempts=retry_max_attempts,
            retry_backoff_base=retry_backoff_base,
            graceful_shutdown_timeout=graceful_shutdown_timeout,
            agent_pools=agent_pools,
            skill_mapping=skill_mapping,
        )
    
    def to_dict(self) -> Dict:
        """
        Serialize configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "dispatcher": {
                "poll_interval": self.poll_interval,
                "scheduling_policy": self.scheduling_policy.value,
                "max_global_concurrency": self.max_global_concurrency,
                "heartbeat_timeout": self.heartbeat_timeout,
                "retry_max_attempts": self.retry_max_attempts,
                "retry_backoff_base": self.retry_backoff_base,
                "graceful_shutdown_timeout": self.graceful_shutdown_timeout,
            },
            "agent_pools": {
                pool.name: pool.to_dict() for pool in self.agent_pools
            },
            "skill_mapping": self.skill_mapping,
        }
    
    def get_pool_by_name(self, pool_name: str) -> Optional[AgentPool]:
        """
        Get Agent Pool by name.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            AgentPool if found, None otherwise
        """
        for pool in self.agent_pools:
            if pool.name == pool_name:
                return pool
        return None
    
    def get_pools_for_skill(self, skill: str) -> List[AgentPool]:
        """
        Get Agent Pools that support a specific skill.
        
        Args:
            skill: Required skill
            
        Returns:
            List of AgentPool instances that support the skill
        """
        pool_names = self.skill_mapping.get(skill, self.skill_mapping.get("default", []))
        pools = []
        for pool_name in pool_names:
            pool = self.get_pool_by_name(pool_name)
            if pool and pool.enabled:
                pools.append(pool)
        return pools

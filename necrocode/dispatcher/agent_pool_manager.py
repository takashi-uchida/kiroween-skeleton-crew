"""
Agent Pool Manager for the Dispatcher component.

Manages Agent Pools, skill-based routing, load balancing, and resource quota tracking.
"""

import logging
from typing import Dict, List, Optional

from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolStatus, PoolType
from necrocode.dispatcher.exceptions import PoolNotFoundError


logger = logging.getLogger(__name__)


class AgentPoolManager:
    """
    Agent Pool Manager.
    
    Manages Agent Pools including:
    - Loading pool configurations
    - Skill-based routing
    - Load balancing
    - Concurrency control
    - Resource quota management
    - Pool status tracking
    """
    
    def __init__(self, config: DispatcherConfig):
        """
        Initialize Agent Pool Manager.
        
        Args:
            config: Dispatcher configuration containing pool definitions
        """
        self.config = config
        self.pools: Dict[str, AgentPool] = {}
        self.skill_mapping: Dict[str, List[str]] = {}
        self.resource_usage: Dict[str, Dict[str, float]] = {}  # pool_name -> {cpu, memory}
        self._load_pools()
    
    def _load_pools(self) -> None:
        """
        Load Agent Pool configurations from config.
        
        Initializes pools dictionary and skill mapping from the dispatcher config.
        Requirements: 2.1
        """
        logger.info("Loading Agent Pool configurations")
        
        # Load pools from config
        for pool in self.config.agent_pools:
            self.pools[pool.name] = pool
            # Initialize resource usage tracking
            self.resource_usage[pool.name] = {
                "cpu": 0.0,
                "memory": 0.0,
            }
            logger.info(
                f"Loaded pool '{pool.name}': type={pool.type.value}, "
                f"max_concurrency={pool.max_concurrency}, enabled={pool.enabled}"
            )
        
        # Load skill mapping
        self.skill_mapping = self.config.skill_mapping.copy()
        logger.info(f"Loaded skill mapping: {self.skill_mapping}")
        
        if not self.pools:
            logger.warning("No Agent Pools configured")
    
    def get_pool_for_skill(self, skill: str) -> Optional[AgentPool]:
        """
        Get an Agent Pool that supports the specified skill.
        
        Uses skill mapping to find appropriate pools and performs load balancing
        if multiple pools support the skill.
        
        Args:
            skill: Required skill (e.g., 'backend', 'frontend', 'database')
            
        Returns:
            AgentPool instance if found, None otherwise
            
        Requirements: 3.1, 3.2
        """
        pool_names = self.skill_mapping.get(skill, [])
        
        if not pool_names:
            logger.warning(f"No pools found for skill '{skill}', trying default")
            pool_names = self.skill_mapping.get("default", [])
        
        if not pool_names:
            logger.warning(f"No pools available for skill '{skill}' and no default pool")
            return None
        
        # Filter to enabled pools only
        available_pools = [
            self.pools[name] for name in pool_names 
            if name in self.pools and self.pools[name].enabled
        ]
        
        if not available_pools:
            logger.warning(f"All pools for skill '{skill}' are disabled")
            return None
        
        # Load balance: select least loaded pool
        return self._select_least_loaded_pool([p.name for p in available_pools])
    
    def get_default_pool(self) -> Optional[AgentPool]:
        """
        Get the default Agent Pool.
        
        Returns the first pool from the default skill mapping, or the first
        enabled pool if no default is configured.
        
        Returns:
            AgentPool instance if found, None otherwise
        """
        default_pool_names = self.skill_mapping.get("default", [])
        
        if default_pool_names:
            for pool_name in default_pool_names:
                pool = self.pools.get(pool_name)
                if pool and pool.enabled:
                    return pool
        
        # Fallback: return first enabled pool
        for pool in self.pools.values():
            if pool.enabled:
                return pool
        
        logger.warning("No default pool available")
        return None
    
    def _select_least_loaded_pool(self, pool_names: List[str]) -> Optional[AgentPool]:
        """
        Select the least loaded pool from a list of pool names.
        
        Chooses the pool with the lowest utilization (current_running / max_concurrency).
        
        Args:
            pool_names: List of pool names to choose from
            
        Returns:
            AgentPool with lowest utilization, or None if no pools available
            
        Requirements: 3.3
        """
        if not pool_names:
            return None
        
        available_pools = []
        for pool_name in pool_names:
            pool = self.pools.get(pool_name)
            if pool and pool.enabled and self.can_accept_task(pool):
                available_pools.append(pool)
        
        if not available_pools:
            return None
        
        # Calculate utilization and select pool with lowest utilization
        least_loaded = min(
            available_pools,
            key=lambda p: p.current_running / p.max_concurrency if p.max_concurrency > 0 else 1.0
        )
        
        logger.debug(
            f"Selected least loaded pool '{least_loaded.name}': "
            f"{least_loaded.current_running}/{least_loaded.max_concurrency}"
        )
        
        return least_loaded
    
    def can_accept_task(self, pool: AgentPool) -> bool:
        """
        Check if a pool can accept a new task.
        
        Verifies:
        - Pool is enabled
        - Current running count is below max concurrency
        - Resource quotas are not exceeded (if configured)
        
        Args:
            pool: AgentPool to check
            
        Returns:
            True if pool can accept task, False otherwise
            
        Requirements: 2.2, 2.3, 6.1, 6.2, 6.3
        """
        # Check if pool is enabled
        if not pool.enabled:
            logger.debug(f"Pool '{pool.name}' is disabled")
            return False
        
        # Check concurrency limit
        if pool.current_running >= pool.max_concurrency:
            logger.debug(
                f"Pool '{pool.name}' at max concurrency: "
                f"{pool.current_running}/{pool.max_concurrency}"
            )
            return False
        
        # Check CPU quota if configured
        if pool.cpu_quota is not None:
            current_cpu = self.resource_usage.get(pool.name, {}).get("cpu", 0.0)
            if current_cpu >= pool.cpu_quota:
                logger.debug(
                    f"Pool '{pool.name}' at CPU quota: "
                    f"{current_cpu}/{pool.cpu_quota} cores"
                )
                return False
        
        # Check memory quota if configured
        if pool.memory_quota is not None:
            current_memory = self.resource_usage.get(pool.name, {}).get("memory", 0.0)
            if current_memory >= pool.memory_quota:
                logger.debug(
                    f"Pool '{pool.name}' at memory quota: "
                    f"{current_memory}/{pool.memory_quota} MB"
                )
                return False
        
        return True
    
    def increment_running_count(self, pool: AgentPool) -> None:
        """
        Increment the running task count for a pool.
        
        Args:
            pool: AgentPool to update
            
        Requirements: 2.2, 2.3, 6.1, 6.2, 6.3
        """
        pool.current_running += 1
        logger.debug(
            f"Incremented running count for pool '{pool.name}': "
            f"{pool.current_running}/{pool.max_concurrency}"
        )
    
    def decrement_running_count(self, pool: AgentPool) -> None:
        """
        Decrement the running task count for a pool.
        
        Args:
            pool: AgentPool to update
            
        Requirements: 2.2, 2.3, 6.1, 6.2, 6.3
        """
        if pool.current_running > 0:
            pool.current_running -= 1
            logger.debug(
                f"Decremented running count for pool '{pool.name}': "
                f"{pool.current_running}/{pool.max_concurrency}"
            )
        else:
            logger.warning(
                f"Attempted to decrement running count for pool '{pool.name}' "
                f"but count is already 0"
            )
    
    def update_resource_usage(
        self,
        pool_name: str,
        cpu_delta: float = 0.0,
        memory_delta: float = 0.0
    ) -> None:
        """
        Update resource usage for a pool.
        
        Args:
            pool_name: Name of the pool
            cpu_delta: Change in CPU usage (cores, can be negative)
            memory_delta: Change in memory usage (MB, can be negative)
            
        Requirements: 2.4, 12.1, 12.2, 12.3, 12.4
        """
        if pool_name not in self.resource_usage:
            self.resource_usage[pool_name] = {"cpu": 0.0, "memory": 0.0}
        
        self.resource_usage[pool_name]["cpu"] = max(
            0.0,
            self.resource_usage[pool_name]["cpu"] + cpu_delta
        )
        self.resource_usage[pool_name]["memory"] = max(
            0.0,
            self.resource_usage[pool_name]["memory"] + memory_delta
        )
        
        # Check for quota warnings
        pool = self.pools.get(pool_name)
        if pool:
            if pool.cpu_quota and self.resource_usage[pool_name]["cpu"] >= pool.cpu_quota:
                logger.warning(
                    f"Pool '{pool_name}' CPU quota exceeded: "
                    f"{self.resource_usage[pool_name]['cpu']}/{pool.cpu_quota} cores"
                )
            
            if pool.memory_quota and self.resource_usage[pool_name]["memory"] >= pool.memory_quota:
                logger.warning(
                    f"Pool '{pool_name}' memory quota exceeded: "
                    f"{self.resource_usage[pool_name]['memory']}/{pool.memory_quota} MB"
                )
    
    def get_pool_status(self, pool_name: str) -> PoolStatus:
        """
        Get the current status of a pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            PoolStatus with current state and utilization
            
        Raises:
            PoolNotFoundError: If pool doesn't exist
            
        Requirements: 2.5
        """
        pool = self.pools.get(pool_name)
        if not pool:
            raise PoolNotFoundError(f"Pool '{pool_name}' not found")
        
        utilization = (
            pool.current_running / pool.max_concurrency
            if pool.max_concurrency > 0
            else 0.0
        )
        
        resource_usage = self.resource_usage.get(pool_name, {"cpu": 0.0, "memory": 0.0})
        
        return PoolStatus(
            pool_name=pool.name,
            type=pool.type,
            enabled=pool.enabled,
            max_concurrency=pool.max_concurrency,
            current_running=pool.current_running,
            utilization=utilization,
            cpu_usage=resource_usage["cpu"],
            memory_usage=resource_usage["memory"],
        )
    
    def get_all_pool_statuses(self) -> List[PoolStatus]:
        """
        Get status for all pools.
        
        Returns:
            List of PoolStatus for all configured pools
        """
        return [self.get_pool_status(pool_name) for pool_name in self.pools.keys()]
    
    def enable_pool(self, pool_name: str) -> None:
        """
        Enable a pool.
        
        Args:
            pool_name: Name of the pool to enable
            
        Raises:
            PoolNotFoundError: If pool doesn't exist
            
        Requirements: 2.5
        """
        pool = self.pools.get(pool_name)
        if not pool:
            raise PoolNotFoundError(f"Pool '{pool_name}' not found")
        
        pool.enabled = True
        logger.info(f"Enabled pool '{pool_name}'")
    
    def disable_pool(self, pool_name: str) -> None:
        """
        Disable a pool.
        
        Args:
            pool_name: Name of the pool to disable
            
        Raises:
            PoolNotFoundError: If pool doesn't exist
            
        Requirements: 2.5
        """
        pool = self.pools.get(pool_name)
        if not pool:
            raise PoolNotFoundError(f"Pool '{pool_name}' not found")
        
        pool.enabled = False
        logger.info(f"Disabled pool '{pool_name}'")
    
    def get_pool_by_name(self, pool_name: str) -> Optional[AgentPool]:
        """
        Get a pool by name.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            AgentPool if found, None otherwise
        """
        return self.pools.get(pool_name)
    
    def get_all_pools(self) -> List[AgentPool]:
        """
        Get all configured Agent Pools.
        
        Returns:
            List of all AgentPool instances
        """
        return list(self.pools.values())

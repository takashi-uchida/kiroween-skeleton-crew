"""
Unit tests for AgentPoolManager.

Tests pool management, skill-based routing, load balancing, concurrency control,
and resource quota management.
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolType, SchedulingPolicy
from necrocode.dispatcher.exceptions import PoolNotFoundError


@pytest.fixture
def sample_config():
    """Create a sample dispatcher configuration."""
    return DispatcherConfig(
        poll_interval=5,
        scheduling_policy=SchedulingPolicy.PRIORITY,
        max_global_concurrency=10,
        agent_pools=[
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
            ),
            AgentPool(
                name="k8s",
                type=PoolType.KUBERNETES,
                max_concurrency=10,
                cpu_quota=10,
                memory_quota=20480,
                enabled=True,
            ),
            AgentPool(
                name="disabled-pool",
                type=PoolType.DOCKER,
                max_concurrency=2,
                enabled=False,
            ),
        ],
        skill_mapping={
            "backend": ["docker", "k8s"],
            "frontend": ["docker", "k8s"],
            "database": ["docker"],
            "devops": ["k8s"],
            "default": ["local"],
        },
    )


@pytest.fixture
def pool_manager(sample_config):
    """Create an AgentPoolManager instance."""
    return AgentPoolManager(sample_config)


def test_load_pools(pool_manager):
    """Test that pools are loaded correctly from config."""
    assert len(pool_manager.pools) == 4
    assert "local" in pool_manager.pools
    assert "docker" in pool_manager.pools
    assert "k8s" in pool_manager.pools
    assert "disabled-pool" in pool_manager.pools
    
    # Check skill mapping
    assert pool_manager.skill_mapping["backend"] == ["docker", "k8s"]
    assert pool_manager.skill_mapping["default"] == ["local"]


def test_get_pool_for_skill_single_pool(pool_manager):
    """Test getting a pool for a skill with single pool mapping."""
    pool = pool_manager.get_pool_for_skill("database")
    assert pool is not None
    assert pool.name == "docker"


def test_get_pool_for_skill_multiple_pools(pool_manager):
    """Test getting a pool for a skill with multiple pool mappings."""
    # Should return least loaded pool
    pool = pool_manager.get_pool_for_skill("backend")
    assert pool is not None
    assert pool.name in ["docker", "k8s"]


def test_get_pool_for_skill_load_balancing(pool_manager):
    """Test that load balancing selects least loaded pool."""
    # Set different loads on pools
    docker_pool = pool_manager.pools["docker"]
    k8s_pool = pool_manager.pools["k8s"]
    
    docker_pool.current_running = 3  # 3/4 = 75%
    k8s_pool.current_running = 5  # 5/10 = 50%
    
    # Should select k8s (lower utilization)
    pool = pool_manager.get_pool_for_skill("backend")
    assert pool is not None
    assert pool.name == "k8s"


def test_get_pool_for_skill_unknown_skill(pool_manager):
    """Test getting a pool for an unknown skill falls back to default."""
    pool = pool_manager.get_pool_for_skill("unknown-skill")
    assert pool is not None
    assert pool.name == "local"


def test_get_pool_for_skill_disabled_pools(pool_manager):
    """Test that disabled pools are not selected."""
    # Disable all backend pools
    pool_manager.pools["docker"].enabled = False
    pool_manager.pools["k8s"].enabled = False
    
    pool = pool_manager.get_pool_for_skill("backend")
    assert pool is None


def test_get_default_pool(pool_manager):
    """Test getting the default pool."""
    pool = pool_manager.get_default_pool()
    assert pool is not None
    assert pool.name == "local"


def test_get_default_pool_no_default_mapping(sample_config):
    """Test getting default pool when no default mapping exists."""
    sample_config.skill_mapping = {"backend": ["docker"]}
    manager = AgentPoolManager(sample_config)
    
    pool = manager.get_default_pool()
    assert pool is not None
    # Should return first enabled pool
    assert pool.enabled


def test_select_least_loaded_pool(pool_manager):
    """Test selecting the least loaded pool from a list."""
    # Set different loads
    pool_manager.pools["docker"].current_running = 2  # 2/4 = 50%
    pool_manager.pools["k8s"].current_running = 3  # 3/10 = 30%
    
    pool = pool_manager._select_least_loaded_pool(["docker", "k8s"])
    assert pool is not None
    assert pool.name == "k8s"


def test_select_least_loaded_pool_at_capacity(pool_manager):
    """Test that pools at capacity are not selected."""
    # Fill docker pool
    pool_manager.pools["docker"].current_running = 4  # At max
    pool_manager.pools["k8s"].current_running = 5
    
    pool = pool_manager._select_least_loaded_pool(["docker", "k8s"])
    assert pool is not None
    assert pool.name == "k8s"


def test_can_accept_task_enabled_pool(pool_manager):
    """Test that enabled pool with capacity can accept tasks."""
    pool = pool_manager.pools["docker"]
    assert pool_manager.can_accept_task(pool) is True


def test_can_accept_task_disabled_pool(pool_manager):
    """Test that disabled pool cannot accept tasks."""
    pool = pool_manager.pools["disabled-pool"]
    assert pool_manager.can_accept_task(pool) is False


def test_can_accept_task_at_max_concurrency(pool_manager):
    """Test that pool at max concurrency cannot accept tasks."""
    pool = pool_manager.pools["local"]
    pool.current_running = 2  # At max
    assert pool_manager.can_accept_task(pool) is False


def test_can_accept_task_cpu_quota_exceeded(pool_manager):
    """Test that pool with CPU quota exceeded cannot accept tasks."""
    pool = pool_manager.pools["docker"]
    pool_manager.resource_usage["docker"]["cpu"] = 4.0  # At quota
    assert pool_manager.can_accept_task(pool) is False


def test_can_accept_task_memory_quota_exceeded(pool_manager):
    """Test that pool with memory quota exceeded cannot accept tasks."""
    pool = pool_manager.pools["docker"]
    pool_manager.resource_usage["docker"]["memory"] = 8192.0  # At quota
    assert pool_manager.can_accept_task(pool) is False


def test_increment_running_count(pool_manager):
    """Test incrementing running task count."""
    pool = pool_manager.pools["docker"]
    initial_count = pool.current_running
    
    pool_manager.increment_running_count(pool)
    assert pool.current_running == initial_count + 1


def test_decrement_running_count(pool_manager):
    """Test decrementing running task count."""
    pool = pool_manager.pools["docker"]
    pool.current_running = 2
    
    pool_manager.decrement_running_count(pool)
    assert pool.current_running == 1


def test_decrement_running_count_at_zero(pool_manager):
    """Test decrementing running count when already at zero."""
    pool = pool_manager.pools["docker"]
    pool.current_running = 0
    
    pool_manager.decrement_running_count(pool)
    assert pool.current_running == 0  # Should not go negative


def test_update_resource_usage(pool_manager):
    """Test updating resource usage."""
    pool_manager.update_resource_usage("docker", cpu_delta=2.0, memory_delta=1024.0)
    
    assert pool_manager.resource_usage["docker"]["cpu"] == 2.0
    assert pool_manager.resource_usage["docker"]["memory"] == 1024.0


def test_update_resource_usage_negative_delta(pool_manager):
    """Test updating resource usage with negative delta."""
    pool_manager.resource_usage["docker"]["cpu"] = 3.0
    pool_manager.resource_usage["docker"]["memory"] = 2048.0
    
    pool_manager.update_resource_usage("docker", cpu_delta=-1.0, memory_delta=-512.0)
    
    assert pool_manager.resource_usage["docker"]["cpu"] == 2.0
    assert pool_manager.resource_usage["docker"]["memory"] == 1536.0


def test_update_resource_usage_no_negative_values(pool_manager):
    """Test that resource usage doesn't go negative."""
    pool_manager.update_resource_usage("docker", cpu_delta=-10.0, memory_delta=-10000.0)
    
    assert pool_manager.resource_usage["docker"]["cpu"] == 0.0
    assert pool_manager.resource_usage["docker"]["memory"] == 0.0


def test_get_pool_status(pool_manager):
    """Test getting pool status."""
    pool = pool_manager.pools["docker"]
    pool.current_running = 2
    pool_manager.resource_usage["docker"]["cpu"] = 2.5
    pool_manager.resource_usage["docker"]["memory"] = 4096.0
    
    status = pool_manager.get_pool_status("docker")
    
    assert status.pool_name == "docker"
    assert status.type == PoolType.DOCKER
    assert status.enabled is True
    assert status.max_concurrency == 4
    assert status.current_running == 2
    assert status.utilization == 0.5  # 2/4
    assert status.cpu_usage == 2.5
    assert status.memory_usage == 4096.0


def test_get_pool_status_not_found(pool_manager):
    """Test getting status for non-existent pool."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.get_pool_status("nonexistent")


def test_get_all_pool_statuses(pool_manager):
    """Test getting all pool statuses."""
    statuses = pool_manager.get_all_pool_statuses()
    
    assert len(statuses) == 4
    pool_names = [s.pool_name for s in statuses]
    assert "local" in pool_names
    assert "docker" in pool_names
    assert "k8s" in pool_names
    assert "disabled-pool" in pool_names


def test_enable_pool(pool_manager):
    """Test enabling a pool."""
    pool_manager.enable_pool("disabled-pool")
    assert pool_manager.pools["disabled-pool"].enabled is True


def test_enable_pool_not_found(pool_manager):
    """Test enabling a non-existent pool."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.enable_pool("nonexistent")


def test_disable_pool(pool_manager):
    """Test disabling a pool."""
    pool_manager.disable_pool("docker")
    assert pool_manager.pools["docker"].enabled is False


def test_disable_pool_not_found(pool_manager):
    """Test disabling a non-existent pool."""
    with pytest.raises(PoolNotFoundError):
        pool_manager.disable_pool("nonexistent")


def test_get_pool_by_name(pool_manager):
    """Test getting a pool by name."""
    pool = pool_manager.get_pool_by_name("docker")
    assert pool is not None
    assert pool.name == "docker"


def test_get_pool_by_name_not_found(pool_manager):
    """Test getting a non-existent pool by name."""
    pool = pool_manager.get_pool_by_name("nonexistent")
    assert pool is None


def test_load_from_yaml_config():
    """Test loading AgentPoolManager from YAML config file."""
    config_data = {
        "dispatcher": {
            "poll_interval": 5,
            "scheduling_policy": "priority",
            "max_global_concurrency": 10,
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
            },
        },
        "skill_mapping": {
            "backend": ["docker"],
            "default": ["local"],
        },
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)
    
    try:
        config = DispatcherConfig.from_yaml(config_path)
        manager = AgentPoolManager(config)
        
        assert len(manager.pools) == 2
        assert "local" in manager.pools
        assert "docker" in manager.pools
        assert manager.skill_mapping["backend"] == ["docker"]
    finally:
        config_path.unlink()


def test_resource_quota_warning(pool_manager, caplog):
    """Test that resource quota warnings are logged."""
    import logging
    caplog.set_level(logging.WARNING)
    
    # Exceed CPU quota
    pool_manager.update_resource_usage("docker", cpu_delta=5.0)
    assert "CPU quota exceeded" in caplog.text
    
    # Exceed memory quota
    pool_manager.update_resource_usage("docker", memory_delta=10000.0)
    assert "memory quota exceeded" in caplog.text

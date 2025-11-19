# Repo Pool Manager

Repo Pool Manager is a component of NecroCode that manages multiple workspace slots for parallel agent execution. It provides efficient allocation, cleanup, and monitoring of git repository clones.

## Overview

The Repo Pool Manager maintains a pool of pre-cloned git repositories (slots) that can be allocated to agents, used for work, and then returned to the pool. This eliminates the overhead of cloning repositories for each task and enables parallel execution.

## Key Features

- **Pool Management**: Create and manage pools of repository clones
- **Slot Allocation**: LRU-based allocation strategy for optimal performance
- **Automatic Cleanup**: Git operations (fetch, clean, reset) before/after allocation
- **Concurrency Control**: File-based locking prevents double allocation
- **Status Monitoring**: Track slot states, usage statistics, and pool health
- **Dynamic Scaling**: Add or remove slots at runtime

## Architecture

```
PoolManager (Main API)
    ├── SlotStore (Persistence)
    ├── SlotAllocator (Allocation Strategy)
    ├── SlotCleaner (Cleanup Operations)
    ├── GitOperations (Git Commands)
    └── LockManager (Concurrency Control)
```

## Quick Start

```python
from necrocode.repo_pool import PoolManager, PoolConfig
from pathlib import Path

# Initialize PoolManager
config = PoolConfig(
    workspaces_dir=Path.home() / ".necrocode" / "workspaces",
    lock_timeout=30.0,
)
manager = PoolManager(config)

# Create a pool with 3 slots
pool = manager.create_pool(
    repo_name="my-project",
    repo_url="https://github.com/user/my-project.git",
    num_slots=3
)

# Allocate a slot
slot = manager.allocate_slot("my-project")
print(f"Allocated: {slot.slot_id}")
print(f"Path: {slot.slot_path}")

# Use the slot for work...
# (perform git operations, run tests, etc.)

# Release the slot when done
manager.release_slot(slot.slot_id)
```

## API Reference

### PoolManager

Main API class for pool and slot management.

#### Pool Management

```python
# Create a new pool
pool = manager.create_pool(
    repo_name="my-project",
    repo_url="https://github.com/user/my-project.git",
    num_slots=3
)

# Get an existing pool
pool = manager.get_pool("my-project")

# List all pools
pools = manager.list_pools()  # Returns: ["my-project", "other-project"]
```

#### Slot Allocation

```python
# Allocate a slot (with automatic cleanup)
slot = manager.allocate_slot("my-project", metadata={"task_id": "123"})

# Release a slot (with automatic cleanup)
manager.release_slot(slot.slot_id)

# Release without cleanup (faster, but less safe)
manager.release_slot(slot.slot_id, cleanup=False)
```

#### Status Monitoring

```python
# Get detailed slot status
status = manager.get_slot_status(slot.slot_id)
print(f"State: {status.state.value}")
print(f"Locked: {status.is_locked}")
print(f"Allocations: {status.allocation_count}")
print(f"Disk usage: {status.disk_usage_mb:.2f} MB")

# Get summary of all pools
summary = manager.get_pool_summary()
for repo_name, pool_summary in summary.items():
    print(f"Pool: {repo_name}")
    print(f"  Total slots: {pool_summary.total_slots}")
    print(f"  Available: {pool_summary.available_slots}")
    print(f"  Allocated: {pool_summary.allocated_slots}")
```

#### Dynamic Slot Management

```python
# Add a new slot to an existing pool
new_slot = manager.add_slot("my-project")

# Remove a slot (must not be allocated)
manager.remove_slot(slot.slot_id)

# Force remove (even if allocated)
manager.remove_slot(slot.slot_id, force=True)
```

## Data Models

### Slot

Represents a single workspace slot.

```python
@dataclass
class Slot:
    slot_id: str                    # "workspace-my-project-slot1"
    repo_name: str                  # "my-project"
    repo_url: str                   # Repository URL
    slot_path: Path                 # Path to slot directory
    state: SlotState                # AVAILABLE, ALLOCATED, CLEANING, ERROR
    
    # Usage statistics
    allocation_count: int
    total_usage_seconds: int
    last_allocated_at: Optional[datetime]
    last_released_at: Optional[datetime]
    
    # Git information
    current_branch: Optional[str]
    current_commit: Optional[str]
```

### SlotState

Enum representing slot states:

- `AVAILABLE`: Ready for allocation
- `ALLOCATED`: Currently in use
- `CLEANING`: Cleanup in progress
- `ERROR`: Error state, needs repair

### Pool

Represents a pool of slots for a repository.

```python
@dataclass
class Pool:
    repo_name: str
    repo_url: str
    num_slots: int
    slots: List[Slot]
    created_at: datetime
    updated_at: datetime
```

## File Structure

```
~/.necrocode/workspaces/
├── my-project/
│   ├── pool.json              # Pool metadata
│   ├── slot1/
│   │   ├── .git/              # Git repository
│   │   ├── slot.json          # Slot metadata
│   │   └── ...                # Repository files
│   ├── slot2/
│   └── slot3/
├── other-project/
│   ├── pool.json
│   ├── slot1/
│   └── slot2/
└── locks/
    ├── workspace-my-project-slot1.lock
    └── workspace-my-project-slot2.lock
```

## Configuration

### Configuration Object

```python
@dataclass
class PoolConfig:
    workspaces_dir: Path = Path.home() / ".necrocode" / "workspaces"
    config_file: Path = Path.home() / ".necrocode" / "config" / "pools.yaml"
    default_num_slots: int = 2
    lock_timeout: float = 30.0
    cleanup_timeout: float = 60.0
    stale_lock_hours: int = 24
    enable_metrics: bool = True
```

### YAML Configuration File

The Repo Pool Manager supports loading configuration from YAML files for easier management and deployment.

#### Configuration File Format

Create a `pools.yaml` file at `~/.necrocode/config/pools.yaml`:

```yaml
# Default settings applied to all pools
defaults:
  num_slots: 2
  lock_timeout: 30.0
  cleanup_timeout: 60.0
  stale_lock_hours: 24
  enable_metrics: true

# Pool definitions
pools:
  my-project:
    repo_url: https://github.com/user/my-project.git
    num_slots: 3
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
  
  another-project:
    repo_url: https://github.com/user/another-project.git
    num_slots: 2
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: true
```

#### Loading Configuration

```python
from necrocode.repo_pool import PoolManager, PoolConfig
from pathlib import Path

# Load from default location (~/.necrocode/config/pools.yaml)
config = PoolConfig.load_from_file()

# Load from custom location
config = PoolConfig.load_from_file(Path("custom/pools.yaml"))

# Validate configuration
config.validate()

# Create PoolManager with loaded config
manager = PoolManager(config)
```

#### Auto-Initialize Pools

Automatically create all pools defined in configuration:

```python
# Create PoolManager and auto-initialize pools
manager = PoolManager.from_config_file(auto_init_pools=True)

# Or manually initialize after creation
manager = PoolManager(config)
created_pools = manager.initialize_pools_from_config()
```

#### Dynamic Configuration Reload

Reload configuration at runtime without restarting:

```python
# Reload configuration from file
manager.reload_config()

# Reload from custom file
manager.reload_config(Path("custom/pools.yaml"))
```

#### Configuration Watcher

Automatically detect and apply configuration changes:

```python
from necrocode.repo_pool.config import ConfigWatcher

# Create watcher with callback
def on_config_change(new_config):
    print(f"Configuration updated: {len(new_config.pools)} pools")
    manager.reload_config()

watcher = ConfigWatcher(config, on_change=on_config_change)

# Check for changes periodically
while True:
    watcher.check_and_reload()
    time.sleep(60)  # Check every minute
```

#### Saving Configuration

Save current configuration to file:

```python
# Save to default location
config.save_to_file()

# Save to custom location
config.save_to_file(Path("backup/pools.yaml"))
```

#### Configuration Validation

The configuration system validates:
- Numeric ranges (num_slots >= 1, timeouts > 0)
- Required fields (repo_url must be present)
- Pool-specific settings

```python
from necrocode.repo_pool.config import ConfigValidationError

try:
    config.validate()
except ConfigValidationError as e:
    print(f"Invalid configuration: {e}")
```

## Cleanup Operations

The PoolManager automatically performs cleanup operations:

### Before Allocation
1. `git fetch --all` - Update remote references
2. `git clean -fdx` - Remove untracked files
3. `git reset --hard` - Reset working directory

### After Release
Same operations as before allocation to ensure slot is clean for next use.

## Concurrency Control

The PoolManager uses file-based locking to prevent concurrent access to the same slot:

```python
# Locks are automatically acquired/released
with lock_manager.acquire_slot_lock(slot_id, timeout=30.0):
    # Critical section - slot is locked
    allocate_slot()
```

### Stale Lock Detection

```python
# Detect locks older than 24 hours
stale_locks = lock_manager.detect_stale_locks(max_age_hours=24)

# Clean up stale locks
cleaned = lock_manager.cleanup_stale_locks(max_age_hours=24)
```

## Error Handling and Recovery

### Exception Handling

```python
from necrocode.repo_pool import (
    PoolNotFoundError,
    SlotNotFoundError,
    NoAvailableSlotError,
    SlotAllocationError,
    LockTimeoutError,
)

try:
    slot = manager.allocate_slot("my-project")
except PoolNotFoundError:
    print("Pool doesn't exist")
except NoAvailableSlotError:
    print("All slots are currently allocated")
except LockTimeoutError:
    print("Failed to acquire lock within timeout")
except SlotAllocationError as e:
    print(f"Allocation failed: {e}")
```

### Anomaly Detection

Detect and handle various system anomalies:

```python
# Detect all anomalies
anomalies = manager.detect_anomalies(max_allocation_hours=24)

# Check specific anomaly types
long_allocated = manager.detect_long_allocated_slots(max_allocation_hours=24)
corrupted = manager.detect_corrupted_slots()
orphaned_locks = manager.detect_orphaned_locks()
```

### Automatic Recovery

Automatically recover from detected issues:

```python
# Run automatic recovery
results = manager.auto_recover(
    max_allocation_hours=24,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)

print(f"Released: {results['long_allocated_released']}")
print(f"Recovered: {results['corrupted_recovered']}")
print(f"Isolated: {results['corrupted_isolated']}")
print(f"Locks cleaned: {results['orphaned_locks_cleaned']}")
```

### Manual Recovery

Recover individual slots:

```python
# Attempt to recover a corrupted slot
success = manager.recover_slot(slot_id, force=False)

# Isolate a problematic slot
manager.isolate_slot(slot_id)
```

For detailed information on error handling and recovery, see [ERROR_RECOVERY_GUIDE.md](ERROR_RECOVERY_GUIDE.md).

## Performance Optimization

### LRU Cache Strategy

The SlotAllocator uses an LRU (Least Recently Used) cache to prioritize recently used slots:

```python
# Get allocation metrics
metrics = slot_allocator.get_allocation_metrics("my-project")
print(f"Cache hit rate: {metrics.cache_hit_rate:.2%}")
print(f"Average allocation time: {metrics.average_allocation_time_seconds:.2f}s")
```

### Slot Warmup

Pre-warm slots for faster allocation:

```python
# Warmup performs git fetch and integrity check
result = slot_cleaner.warmup_slot(slot)
```

## Integration with NecroCode

The Repo Pool Manager integrates with other NecroCode components:

- **Agent Runner**: Requests slots for task execution
- **Dispatcher**: Coordinates slot allocation across multiple agents
- **Workspace Manager**: Uses slots as base for workspace operations

## Examples

See `examples/pool_manager_example.py` for a complete usage example.

## Requirements

- Python 3.11+
- Git CLI
- filelock library

## See Also

- [Error Recovery Guide](ERROR_RECOVERY_GUIDE.md) - Comprehensive guide to error handling and recovery
- [Configuration Guide](CONFIG_GUIDE.md) - Detailed configuration documentation
- [Design Document](../../.kiro/specs/repo-pool-manager/design.md)
- [Requirements](../../.kiro/specs/repo-pool-manager/requirements.md)
- [Task List](../../.kiro/specs/repo-pool-manager/tasks.md)
- [Examples](../../examples/) - Usage examples including error recovery

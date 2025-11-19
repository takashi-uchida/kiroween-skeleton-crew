# Repo Pool Manager Configuration Guide

## Quick Start

### 1. Create Configuration File

Create `~/.necrocode/config/pools.yaml`:

```yaml
defaults:
  num_slots: 2
  lock_timeout: 30.0
  cleanup_timeout: 60.0
  stale_lock_hours: 24

pools:
  my-project:
    repo_url: https://github.com/user/my-project.git
    num_slots: 3
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
```

### 2. Initialize PoolManager

```python
from necrocode.repo_pool import PoolManager

# Load config and auto-initialize pools
manager = PoolManager.from_config_file(auto_init_pools=True)
```

### 3. Use Pools

```python
# Allocate a slot
slot = manager.allocate_slot("my-project")

# Use the slot...

# Release when done
manager.release_slot(slot.slot_id)
```

## Configuration Reference

### Defaults Section

Global settings applied to all pools:

```yaml
defaults:
  num_slots: 2              # Default number of slots per pool
  lock_timeout: 30.0        # Lock acquisition timeout (seconds)
  cleanup_timeout: 60.0     # Cleanup operation timeout (seconds)
  stale_lock_hours: 24      # Hours before lock is considered stale
  enable_metrics: true      # Enable metrics collection
```

### Pools Section

Individual pool configurations:

```yaml
pools:
  pool-name:
    repo_url: https://github.com/user/repo.git  # Required
    num_slots: 3                                 # Optional (uses default)
    cleanup_options:                             # Optional
      fetch_on_allocate: true                    # Fetch before allocation
      clean_on_release: true                     # Clean after release
      warmup_enabled: false                      # Enable slot warmup
```

## Common Patterns

### Development Environment

```yaml
defaults:
  num_slots: 1
  lock_timeout: 10.0

pools:
  dev-project:
    repo_url: https://github.com/user/dev-project.git
    num_slots: 1
    cleanup_options:
      fetch_on_allocate: false  # Skip fetch for speed
      clean_on_release: false
      warmup_enabled: false
```

### Production Environment

```yaml
defaults:
  num_slots: 5
  lock_timeout: 60.0
  cleanup_timeout: 120.0
  stale_lock_hours: 12

pools:
  prod-project:
    repo_url: https://github.com/user/prod-project.git
    num_slots: 10
    cleanup_options:
      fetch_on_allocate: true   # Always fetch latest
      clean_on_release: true    # Always clean
      warmup_enabled: true      # Pre-warm slots
```

### CI/CD Environment

```yaml
defaults:
  num_slots: 3
  lock_timeout: 30.0
  stale_lock_hours: 1  # Aggressive cleanup

pools:
  ci-project:
    repo_url: https://github.com/user/ci-project.git
    num_slots: 5
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
```

## Dynamic Configuration

### Reload Configuration

```python
# Reload from file
manager.reload_config()

# Reload from custom file
manager.reload_config(Path("custom/pools.yaml"))
```

### Watch for Changes

```python
from necrocode.repo_pool.config import ConfigWatcher
import time

# Create watcher
def on_change(new_config):
    print("Configuration changed!")
    manager.reload_config()

watcher = ConfigWatcher(manager.config, on_change=on_change)

# Check periodically
while True:
    watcher.check_and_reload()
    time.sleep(60)
```

### Programmatic Updates

```python
from necrocode.repo_pool.config import PoolDefinition, CleanupOptions

# Add new pool
pool_def = PoolDefinition(
    repo_name="new-project",
    repo_url="https://github.com/user/new-project.git",
    num_slots=3,
    cleanup_options=CleanupOptions(
        fetch_on_allocate=True,
        clean_on_release=True,
        warmup_enabled=False
    )
)
manager.config.add_pool_definition(pool_def)

# Save to file
manager.config.save_to_file()

# Initialize the new pool
manager.initialize_pools_from_config()
```

## Validation

### Automatic Validation

Configuration is automatically validated when loaded:

```python
from necrocode.repo_pool.config import ConfigValidationError

try:
    config = PoolConfig.load_from_file()
    config.validate()
except ConfigValidationError as e:
    print(f"Invalid configuration: {e}")
```

### Validation Rules

- `num_slots` must be >= 1
- `lock_timeout` must be > 0
- `cleanup_timeout` must be > 0
- `stale_lock_hours` must be >= 0
- `repo_url` is required for each pool

## Troubleshooting

### Configuration Not Loading

```python
# Check if file exists
config_file = Path.home() / ".necrocode" / "config" / "pools.yaml"
if not config_file.exists():
    print(f"Configuration file not found: {config_file}")
```

### Invalid YAML Syntax

```python
try:
    config = PoolConfig.load_from_file()
except ConfigValidationError as e:
    print(f"YAML parsing error: {e}")
```

### Pool Not Initializing

```python
# Check pool definition
pool_def = manager.config.get_pool_definition("my-project")
if pool_def is None:
    print("Pool not defined in configuration")
else:
    print(f"Pool URL: {pool_def.repo_url}")
    print(f"Slots: {pool_def.num_slots}")
```

### Configuration Changes Not Applied

```python
# Check file modification time
mtime = manager.config.get_file_mtime()
print(f"Config file last modified: {mtime}")

# Force reload
manager.reload_config()
```

## Best Practices

### 1. Use Version Control

Store your configuration in version control:

```bash
git add ~/.necrocode/config/pools.yaml
git commit -m "Update pool configuration"
```

### 2. Environment-Specific Configs

Use different configs for different environments:

```python
import os

env = os.getenv("ENVIRONMENT", "development")
config_file = Path(f"config/pools.{env}.yaml")
manager = PoolManager.from_config_file(config_file)
```

### 3. Validate Before Deployment

```python
# Validate configuration before deploying
config = PoolConfig.load_from_file()
try:
    config.validate()
    print("✓ Configuration is valid")
except ConfigValidationError as e:
    print(f"✗ Configuration error: {e}")
    exit(1)
```

### 4. Monitor Configuration Changes

```python
# Log configuration changes
def on_config_change(new_config):
    logger.info(f"Configuration reloaded: {len(new_config.pools)} pools")
    for repo_name in new_config.pools:
        logger.info(f"  - {repo_name}")
    manager.reload_config()

watcher = ConfigWatcher(manager.config, on_change=on_config_change)
```

### 5. Backup Configuration

```python
from datetime import datetime

# Backup before changes
backup_file = Path(f"config/pools.backup.{datetime.now().isoformat()}.yaml")
manager.config.save_to_file(backup_file)
```

## Examples

See `examples/config_management_example.py` for complete examples of:
- Loading configuration
- Validation
- Dynamic reload
- Configuration watcher
- Saving configuration

## See Also

- [README.md](README.md) - Main documentation
- [Design Document](../../.kiro/specs/repo-pool-manager/design.md)
- [Requirements](../../.kiro/specs/repo-pool-manager/requirements.md)

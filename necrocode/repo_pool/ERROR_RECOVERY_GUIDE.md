# Error Handling and Recovery Guide

This guide explains the error handling and recovery features in the Repo Pool Manager.

## Overview

The Repo Pool Manager includes comprehensive error detection and automatic recovery capabilities to maintain system health and prevent issues from affecting agent operations.

## Anomaly Detection

### Types of Anomalies

The system can detect three types of anomalies:

#### 1. Long-Allocated Slots

Slots that have been in the `ALLOCATED` state for an unusually long time may indicate:
- Crashed agent processes
- Forgotten allocations
- Deadlocks or hung processes

**Detection Method:**
```python
long_allocated = manager.detect_long_allocated_slots(max_allocation_hours=24)
```

**Default Threshold:** 24 hours

#### 2. Corrupted Slots

Slots with integrity issues such as:
- Missing directories
- Corrupted git repositories
- Invalid metadata
- Broken `.git` directories

**Detection Method:**
```python
corrupted = manager.detect_corrupted_slots()
```

**Verification Checks:**
- Slot directory exists
- `.git` directory exists and is valid
- Can retrieve current branch and commit
- Git repository is not corrupted

#### 3. Orphaned Locks

Lock files that:
- Don't correspond to any existing slot
- Are stale (older than configured threshold)
- Were left behind by crashed processes

**Detection Method:**
```python
orphaned = manager.detect_orphaned_locks()
```

**Default Threshold:** 24 hours (configurable via `stale_lock_hours`)

### Comprehensive Anomaly Detection

Run all detection methods at once:

```python
anomalies = manager.detect_anomalies(max_allocation_hours=24)

# Returns dictionary with:
# {
#     "long_allocated_slots": [Slot, ...],
#     "corrupted_slots": [Slot, ...],
#     "orphaned_locks": ["slot_id", ...]
# }
```

## Manual Recovery

### Recovering a Single Slot

Attempt to recover a corrupted or error-state slot:

```python
# Basic recovery
success = manager.recover_slot(slot_id, force=False)

# Force recovery (marks as available even if repair fails)
success = manager.recover_slot(slot_id, force=True)
```

**Recovery Process:**
1. Verify slot integrity
2. If corrupted, attempt repair:
   - Run `git fsck` to check for corruption
   - Attempt cleanup to restore working state
   - If repair fails, delete and re-clone repository
3. Update slot state to `AVAILABLE`

### Isolating a Problematic Slot

Mark a slot as `ERROR` to prevent allocation:

```python
manager.isolate_slot(slot_id)
```

**Effects:**
- Slot state set to `ERROR`
- Metadata added with isolation timestamp and reason
- Slot will not be allocated until manually recovered
- Requires manual intervention to restore

**Use Cases:**
- Persistent corruption that can't be auto-recovered
- Slots requiring manual inspection
- Temporary removal from pool without deletion

## Automatic Recovery

### Basic Auto-Recovery

Run automatic recovery with default settings:

```python
results = manager.auto_recover()
```

### Advanced Auto-Recovery

Customize recovery behavior:

```python
results = manager.auto_recover(
    max_allocation_hours=24,           # Threshold for long allocations
    recover_corrupted=True,            # Attempt to recover corrupted slots
    cleanup_orphaned_locks=True,       # Clean up orphaned lock files
    force_release_long_allocated=False # Force-release long-allocated slots
)
```

**Parameters:**

- `max_allocation_hours` (default: 24)
  - Maximum time a slot can be allocated before considered anomalous
  
- `recover_corrupted` (default: True)
  - Whether to attempt recovery of corrupted slots
  - Failed recoveries result in slot isolation
  
- `cleanup_orphaned_locks` (default: True)
  - Whether to remove orphaned lock files
  - Safe to enable as orphaned locks are verified
  
- `force_release_long_allocated` (default: False)
  - Whether to force-release long-allocated slots
  - **WARNING:** May interrupt active agent processes
  - Use with caution in production

**Return Value:**

```python
{
    "long_allocated_released": 2,      # Number of slots force-released
    "corrupted_recovered": 1,          # Number of slots successfully recovered
    "corrupted_isolated": 1,           # Number of slots isolated (recovery failed)
    "orphaned_locks_cleaned": 3,       # Number of orphaned locks removed
    "errors": ["error message", ...]   # List of errors encountered
}
```

## Recovery Strategies

### Strategy 1: Conservative (Recommended for Production)

Detect issues but don't force-release active allocations:

```python
results = manager.auto_recover(
    max_allocation_hours=48,           # Higher threshold
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False # Don't interrupt active work
)
```

**Best for:**
- Production environments
- When agent processes may legitimately run for long periods
- When manual review of long allocations is preferred

### Strategy 2: Aggressive (Recommended for Development)

Aggressively clean up all anomalies:

```python
results = manager.auto_recover(
    max_allocation_hours=24,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=True  # Force cleanup
)
```

**Best for:**
- Development environments
- After system crashes
- When you know no legitimate long-running processes exist

### Strategy 3: Maintenance Mode

Focus on corruption and locks, ignore allocations:

```python
results = manager.auto_recover(
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)
```

**Best for:**
- Regular maintenance
- When you want to fix infrastructure issues without affecting running agents

## Scheduled Recovery

### Cron Job Example

Run automatic recovery daily at 2 AM:

```bash
# /etc/cron.d/necrocode-recovery
0 2 * * * /usr/bin/python3 /path/to/recovery_script.py
```

**recovery_script.py:**
```python
#!/usr/bin/env python3
import logging
from pathlib import Path
from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/var/log/necrocode-recovery.log'
)

config = PoolConfig.load_from_file()
manager = PoolManager(config=config)

# Run conservative recovery
results = manager.auto_recover(
    max_allocation_hours=48,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)

logging.info(f"Recovery completed: {results}")
```

### Monitoring Integration

Integrate with monitoring systems:

```python
def health_check():
    """Check system health and alert if issues found."""
    manager = PoolManager.from_config_file()
    
    # Detect anomalies
    anomalies = manager.detect_anomalies(max_allocation_hours=24)
    
    total_issues = (
        len(anomalies['long_allocated_slots']) +
        len(anomalies['corrupted_slots']) +
        len(anomalies['orphaned_locks'])
    )
    
    if total_issues > 0:
        # Send alert to monitoring system
        send_alert(f"Repo Pool Manager: {total_issues} issues detected")
        
        # Attempt auto-recovery
        results = manager.auto_recover()
        
        # Report results
        send_metric("recovery.slots_released", results['long_allocated_released'])
        send_metric("recovery.slots_recovered", results['corrupted_recovered'])
        send_metric("recovery.slots_isolated", results['corrupted_isolated'])
        send_metric("recovery.locks_cleaned", results['orphaned_locks_cleaned'])
    
    return total_issues == 0
```

## Best Practices

### 1. Regular Health Checks

Run anomaly detection regularly (e.g., hourly):

```python
# Check for issues without taking action
anomalies = manager.detect_anomalies()
if any(len(v) > 0 for v in anomalies.values()):
    logger.warning(f"Anomalies detected: {anomalies}")
```

### 2. Gradual Recovery

For large numbers of issues, recover gradually:

```python
# First pass: Clean up locks and recover obvious corruption
results1 = manager.auto_recover(
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)

# Wait and verify
time.sleep(60)

# Second pass: Handle remaining issues if needed
anomalies = manager.detect_anomalies()
if len(anomalies['long_allocated_slots']) > 0:
    # Manual review or force-release
    pass
```

### 3. Logging and Alerting

Always log recovery actions:

```python
import logging

logger = logging.getLogger(__name__)

results = manager.auto_recover()

logger.info(
    f"Auto-recovery completed: "
    f"released={results['long_allocated_released']}, "
    f"recovered={results['corrupted_recovered']}, "
    f"isolated={results['corrupted_isolated']}, "
    f"locks_cleaned={results['orphaned_locks_cleaned']}"
)

if results['errors']:
    logger.error(f"Recovery errors: {results['errors']}")
```

### 4. Manual Intervention for Isolated Slots

Isolated slots require manual attention:

```python
# Find isolated slots
pool = manager.get_pool("my-repo")
isolated = [s for s in pool.slots if s.state == SlotState.ERROR]

for slot in isolated:
    logger.info(f"Isolated slot: {slot.slot_id}")
    logger.info(f"  Isolated at: {slot.metadata.get('isolated_at')}")
    logger.info(f"  Reason: {slot.metadata.get('isolation_reason')}")
    
    # Attempt recovery
    success = manager.recover_slot(slot.slot_id, force=True)
    if success:
        logger.info(f"  ✓ Recovered successfully")
    else:
        logger.error(f"  ✗ Recovery failed - manual intervention required")
```

## Troubleshooting

### Issue: Recovery Keeps Failing

**Symptoms:** Same slots repeatedly fail recovery

**Solutions:**
1. Check disk space: `df -h`
2. Check git repository health manually:
   ```bash
   cd /path/to/slot
   git fsck --full
   ```
3. Check file permissions
4. Consider removing and re-creating the slot:
   ```python
   manager.remove_slot(slot_id, force=True)
   manager.add_slot(repo_name)
   ```

### Issue: Too Many Long-Allocated Slots

**Symptoms:** Many slots allocated for long periods

**Possible Causes:**
- Agent processes are legitimately long-running
- Agents are crashing without releasing slots
- Threshold is too low

**Solutions:**
1. Increase threshold: `max_allocation_hours=48`
2. Check agent logs for crashes
3. Implement agent heartbeat monitoring
4. Add timeout to agent execution

### Issue: Orphaned Locks Persist

**Symptoms:** Locks keep appearing after cleanup

**Possible Causes:**
- Active processes are creating locks
- File system issues
- Concurrent access without proper locking

**Solutions:**
1. Check for running agent processes
2. Verify lock directory permissions
3. Check for file system errors
4. Review agent code for proper lock usage

## API Reference

### Detection Methods

```python
# Detect long-allocated slots
long_allocated = manager.detect_long_allocated_slots(max_allocation_hours=24)

# Detect corrupted slots
corrupted = manager.detect_corrupted_slots()

# Detect orphaned locks
orphaned = manager.detect_orphaned_locks()

# Detect all anomalies
anomalies = manager.detect_anomalies(max_allocation_hours=24)
```

### Recovery Methods

```python
# Recover single slot
success = manager.recover_slot(slot_id, force=False)

# Isolate slot
manager.isolate_slot(slot_id)

# Automatic recovery
results = manager.auto_recover(
    max_allocation_hours=24,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)
```

### Lock Management

```python
# Detect stale locks
stale = manager.lock_manager.detect_stale_locks(max_age_hours=24)

# Clean up stale locks
count = manager.lock_manager.cleanup_stale_locks(max_age_hours=24)

# Force unlock
manager.lock_manager.force_unlock(slot_id)
```

## Requirements Mapping

This implementation satisfies the following requirements:

- **Requirement 9.1**: Git operation retry mechanism (3 retries)
- **Requirement 9.2**: Slot repair and re-initialization
- **Requirement 9.3**: Detection of long-allocated slots
- **Requirement 9.4**: Detection and cleanup of orphaned locks
- **Requirement 9.5**: Slot isolation for manual intervention

## See Also

- [README.md](README.md) - Main documentation
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - Configuration guide
- [examples/error_recovery_example.py](../../examples/error_recovery_example.py) - Usage examples

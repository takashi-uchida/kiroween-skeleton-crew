# Task 9: 並行アクセスの制御 (Concurrency Control) - Implementation Summary

## Overview
Implemented file-based locking mechanism for the Artifact Store to prevent concurrent writes to the same artifact while allowing lock-free read operations for better performance.

## Implementation Details

### 1. Lock Manager (Subtask 9.1)
**File**: `necrocode/artifact_store/lock_manager.py`

Created `ArtifactLockManager` class that provides:
- File-based locking using the `filelock` library
- Context manager for automatic lock acquisition and release
- Lock status checking
- Force unlock for deadlock recovery

**Key Features**:
- Uses file locks stored in `{base_path}/locks/` directory
- Converts artifact URIs to safe filenames for lock files
- Provides `acquire_write_lock()` context manager
- Implements `is_locked()` for checking lock status
- Includes `force_unlock()` for emergency situations

**Requirements Addressed**: 11.1, 11.2

### 2. Lock Timeout and Retry (Subtask 9.2)
**File**: `necrocode/artifact_store/lock_manager.py`

Enhanced lock acquisition with:
- Configurable timeout settings
- Automatic retry mechanism with configurable intervals
- Exponential backoff support
- Detailed logging of lock acquisition attempts

**Key Features**:
- Default timeout: 30 seconds (configurable)
- Default retry interval: 0.1 seconds (configurable)
- Retry loop continues until timeout is reached
- Raises `LockTimeoutError` when timeout is exceeded
- Tracks number of attempts and elapsed time

**Configuration**:
```python
config = ArtifactStoreConfig(
    locking_enabled=True,
    lock_timeout=30.0,
    lock_retry_interval=0.1,
)
```

**Requirements Addressed**: 11.3, 11.4

### 3. Read Operations Without Locks (Subtask 9.3)
**Files**: 
- `necrocode/artifact_store/artifact_store.py`
- `necrocode/artifact_store/config.py`

Integrated locking into write operations while keeping read operations lock-free:

**Write Operations (with locking)**:
- `upload()` - Acquires write lock before uploading
- `delete()` - Acquires write lock before deleting
- `delete_by_task_id()` - Uses locks for each deletion
- `delete_by_spec_name()` - Uses locks for each deletion

**Read Operations (no locking)**:
- `download()` - No lock required
- `download_stream()` - No lock required
- `search()` - No lock required
- `get_metadata()` - No lock required
- `exists()` - No lock required
- `get_all_artifacts()` - No lock required
- `verify_checksum()` - No lock required
- `verify_all()` - No lock required
- `get_storage_usage()` - No lock required
- `get_usage_by_spec()` - No lock required
- `get_usage_by_type()` - No lock required

**Locking Control**:
- Can be enabled/disabled via `locking_enabled` config option
- When disabled, all operations proceed without locking
- Default: enabled

**Requirements Addressed**: 11.5

## Configuration Updates

### ArtifactStoreConfig
Added new configuration options:
```python
@dataclass
class ArtifactStoreConfig:
    # Locking settings
    locking_enabled: bool = True
    lock_timeout: float = 30.0
    lock_retry_interval: float = 0.1
```

## Testing

### Unit Tests
**File**: `tests/test_artifact_store_concurrency.py`

Comprehensive test suite covering:
1. Lock manager initialization
2. Concurrent uploads with locking
3. Lock acquisition and release
4. Lock timeout behavior
5. Lock retry mechanism
6. Uploads with locking disabled
7. Delete operations with locking
8. Read operations without locks
9. Force unlock functionality
10. Concurrent delete operations

**Test Results**: All 10 tests pass ✓

### Example Code
**File**: `examples/concurrency_control_artifact_example.py`

Demonstrates:
1. Concurrent uploads with locking enabled
2. Lock manager direct usage
3. Lock timeout scenarios
4. Locking disabled mode
5. Thread-safe operations

## Usage Examples

### Basic Usage with Locking
```python
from necrocode.artifact_store import ArtifactStore, ArtifactStoreConfig, ArtifactType

# Create store with locking enabled (default)
config = ArtifactStoreConfig(
    locking_enabled=True,
    lock_timeout=30.0,
)
store = ArtifactStore(config)

# Upload (uses lock)
uri = store.upload(
    task_id="1.1",
    spec_name="my-spec",
    artifact_type=ArtifactType.DIFF,
    content=b"My changes",
)

# Download (no lock required)
content = store.download(uri)
```

### Direct Lock Manager Usage
```python
# Acquire lock manually
with store.lock_manager.acquire_write_lock(uri, timeout=10.0):
    # Critical section - exclusive access
    perform_operations()

# Check if locked
is_locked = store.lock_manager.is_locked(uri)
```

### Concurrent Operations
```python
import threading

def upload_worker(worker_id):
    content = f"Worker {worker_id}".encode()
    uri = store.upload(
        task_id="1.1",
        spec_name="concurrent-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )

# Multiple threads can safely upload
threads = [threading.Thread(target=upload_worker, args=(i,)) for i in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Error Handling

### LockTimeoutError
Raised when lock acquisition times out:
```python
from necrocode.artifact_store.exceptions import LockTimeoutError

try:
    uri = store.upload(...)
except LockTimeoutError as e:
    print(f"Failed to acquire lock: {e}")
    # Handle timeout (retry, log, etc.)
```

## Performance Considerations

1. **Write Operations**: Serialized per artifact URI
   - Multiple threads writing to different artifacts: parallel
   - Multiple threads writing to same artifact: serialized

2. **Read Operations**: No locking overhead
   - All read operations are lock-free
   - Maximum read performance

3. **Lock Granularity**: Per-artifact URI
   - Fine-grained locking
   - Minimal contention

## Requirements Coverage

| Requirement | Status | Implementation |
|------------|--------|----------------|
| 11.1 | ✓ | File-based lock detection |
| 11.2 | ✓ | Lock prevents concurrent writes |
| 11.3 | ✓ | Configurable timeout |
| 11.4 | ✓ | Retry with configurable interval |
| 11.5 | ✓ | Read operations lock-free |

## Files Modified/Created

### Created:
- `necrocode/artifact_store/lock_manager.py` - Lock manager implementation
- `tests/test_artifact_store_concurrency.py` - Comprehensive tests
- `examples/concurrency_control_artifact_example.py` - Usage examples

### Modified:
- `necrocode/artifact_store/artifact_store.py` - Integrated locking
- `necrocode/artifact_store/config.py` - Added lock configuration
- `necrocode/artifact_store/__init__.py` - Exported lock manager

## Dependencies

- `filelock` library (already used by repo_pool)
- No additional dependencies required

## Next Steps

Task 9 is complete. The next tasks in the implementation plan are:
- Task 10: バージョニングの実装 (Versioning)
- Task 11: タグ付けの実装 (Tagging)
- Task 12: エクスポート機能の実装 (Export functionality)

## Notes

- The implementation follows the same pattern as the repo pool lock manager
- Lock files are stored in `{base_path}/locks/` directory
- Locking can be completely disabled via configuration
- Read operations are optimized for performance (no locking)
- Write operations are safe for concurrent access
- Force unlock is available for emergency deadlock recovery

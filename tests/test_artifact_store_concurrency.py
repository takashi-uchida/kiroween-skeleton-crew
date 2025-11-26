"""
Tests for Artifact Store concurrency control.
"""

import pytest
import threading
import time
from pathlib import Path
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import LockTimeoutError


@pytest.fixture
def temp_store(tmp_path):
    """Create a temporary artifact store with locking enabled."""
    config = ArtifactStoreConfig(
        base_path=tmp_path / "artifacts",
        compression_enabled=False,
        locking_enabled=True,
        lock_timeout=5.0,
        lock_retry_interval=0.1,
    )
    return ArtifactStore(config)


@pytest.fixture
def temp_store_no_lock(tmp_path):
    """Create a temporary artifact store with locking disabled."""
    config = ArtifactStoreConfig(
        base_path=tmp_path / "artifacts-no-lock",
        compression_enabled=False,
        locking_enabled=False,
    )
    return ArtifactStore(config)


def test_lock_manager_initialization(temp_store):
    """Test that lock manager is properly initialized."""
    assert temp_store.lock_manager is not None
    assert temp_store.lock_manager.locks_dir.exists()
    assert temp_store.lock_manager.default_timeout == 5.0
    assert temp_store.lock_manager.default_retry_interval == 0.1


def test_concurrent_uploads_with_locking(temp_store):
    """Test that concurrent uploads are serialized with locking."""
    task_id = "1.1"
    spec_name = "test-spec"
    results = []
    errors = []
    
    def upload_worker(worker_id):
        try:
            content = f"Worker {worker_id} content".encode()
            uri = temp_store.upload(
                task_id=task_id,
                spec_name=spec_name,
                artifact_type=ArtifactType.LOG,
                content=content,
            )
            results.append((worker_id, uri))
        except Exception as e:
            errors.append((worker_id, str(e)))
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=upload_worker, args=(i,))
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # All uploads should succeed
    assert len(results) == 5
    assert len(errors) == 0
    
    # Only one artifact should exist (last write wins)
    artifacts = temp_store.search(task_id=task_id, spec_name=spec_name)
    assert len(artifacts) == 1


def test_lock_acquisition_and_release(temp_store):
    """Test lock acquisition and release."""
    uri = "file:///tmp/test-artifact.txt"
    
    # Initially not locked
    assert not temp_store.lock_manager.is_locked(uri)
    
    # Acquire lock
    with temp_store.lock_manager.acquire_write_lock(uri):
        # Should be locked
        assert temp_store.lock_manager.is_locked(uri)
    
    # Should be released
    assert not temp_store.lock_manager.is_locked(uri)


def test_lock_timeout(temp_store):
    """Test that lock acquisition times out correctly."""
    uri = "file:///tmp/test-timeout.txt"
    
    def hold_lock():
        with temp_store.lock_manager.acquire_write_lock(uri, timeout=5.0):
            time.sleep(2)
    
    # Start thread that holds lock
    holder = threading.Thread(target=hold_lock)
    holder.start()
    
    # Wait for lock to be acquired
    time.sleep(0.2)
    
    # Try to acquire with short timeout
    with pytest.raises(LockTimeoutError) as exc_info:
        with temp_store.lock_manager.acquire_write_lock(uri, timeout=0.5):
            pass
    
    assert uri in str(exc_info.value)
    assert "0.5" in str(exc_info.value)
    
    # Wait for holder to finish
    holder.join()


def test_lock_retry_mechanism(temp_store):
    """Test that lock retry mechanism works."""
    uri = "file:///tmp/test-retry.txt"
    acquired = []
    
    def short_hold():
        with temp_store.lock_manager.acquire_write_lock(uri, timeout=2.0):
            acquired.append(1)
            time.sleep(0.3)
    
    def wait_and_acquire():
        time.sleep(0.1)  # Wait a bit before trying
        with temp_store.lock_manager.acquire_write_lock(uri, timeout=2.0):
            acquired.append(2)
    
    # Start both threads
    t1 = threading.Thread(target=short_hold)
    t2 = threading.Thread(target=wait_and_acquire)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Both should have acquired the lock
    assert len(acquired) == 2
    assert 1 in acquired
    assert 2 in acquired


def test_upload_with_locking_disabled(temp_store_no_lock):
    """Test that uploads work without locking."""
    uri = temp_store_no_lock.upload(
        task_id="1.1",
        spec_name="no-lock-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Test content",
    )
    
    assert uri is not None
    
    # Download should work
    content = temp_store_no_lock.download(uri)
    assert content == b"Test content"


def test_delete_with_locking(temp_store):
    """Test that delete operations use locking."""
    # Upload an artifact
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="delete-test",
        artifact_type=ArtifactType.LOG,
        content=b"Test content",
    )
    
    # Delete should succeed
    temp_store.delete(uri)
    
    # Artifact should not exist
    assert not temp_store.exists(uri)


def test_read_operations_no_lock(temp_store):
    """Test that read operations don't require locks (Requirement 11.5)."""
    # Upload an artifact
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="read-test",
        artifact_type=ArtifactType.LOG,
        content=b"Test content",
    )
    
    # Hold a write lock
    def hold_write_lock():
        # This simulates another process holding a write lock
        # (In reality, we can't test this easily without actual file locking)
        time.sleep(1)
    
    holder = threading.Thread(target=hold_write_lock)
    holder.start()
    
    # Read operations should work immediately without waiting for lock
    content = temp_store.download(uri, verify_checksum=False)
    assert content == b"Test content"
    
    # Search should also work
    artifacts = temp_store.search(task_id="1.1")
    assert len(artifacts) == 1
    
    holder.join()


def test_force_unlock(temp_store):
    """Test force unlock functionality."""
    uri = "file:///tmp/test-force-unlock.txt"
    
    # Acquire lock
    with temp_store.lock_manager.acquire_write_lock(uri):
        # Lock is held
        assert temp_store.lock_manager.is_locked(uri)
        
        # Force unlock from another context (dangerous!)
        temp_store.lock_manager.force_unlock(uri)
        
        # Lock should be released
        assert not temp_store.lock_manager.is_locked(uri)


def test_concurrent_delete_operations(temp_store):
    """Test concurrent delete operations."""
    # Upload multiple artifacts
    uris = []
    for i in range(5):
        uri = temp_store.upload(
            task_id=f"task-{i}",
            spec_name="delete-test",
            artifact_type=ArtifactType.LOG,
            content=f"Content {i}".encode(),
        )
        uris.append(uri)
    
    deleted = []
    errors = []
    
    def delete_worker(uri):
        try:
            temp_store.delete(uri)
            deleted.append(uri)
        except Exception as e:
            errors.append((uri, str(e)))
    
    # Delete concurrently
    threads = []
    for uri in uris:
        thread = threading.Thread(target=delete_worker, args=(uri,))
        threads.append(thread)
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # All deletes should succeed
    assert len(deleted) == 5
    assert len(errors) == 0
    
    # No artifacts should remain
    artifacts = temp_store.search(spec_name="delete-test")
    assert len(artifacts) == 0

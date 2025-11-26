"""
Example: Concurrency Control in Artifact Store

Demonstrates file-based locking for concurrent artifact access.
"""

import time
import threading
from pathlib import Path
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import LockTimeoutError


def upload_worker(worker_id: int, store: ArtifactStore, task_id: str):
    """Worker thread that attempts to upload an artifact."""
    try:
        print(f"Worker {worker_id}: Attempting to upload artifact for task {task_id}")
        
        content = f"Content from worker {worker_id} at {time.time()}".encode()
        
        uri = store.upload(
            task_id=task_id,
            spec_name="concurrent-test",
            artifact_type=ArtifactType.LOG,
            content=content,
        )
        
        print(f"Worker {worker_id}: Successfully uploaded to {uri}")
        
    except LockTimeoutError as e:
        print(f"Worker {worker_id}: Lock timeout - {e}")
    except Exception as e:
        print(f"Worker {worker_id}: Error - {e}")


def main():
    """Demonstrate concurrent artifact uploads with locking."""
    
    print("=" * 60)
    print("Concurrency Control Example")
    print("=" * 60)
    
    # Create temporary artifact store
    config = ArtifactStoreConfig(
        base_path=Path("/tmp/artifact-store-concurrency-test"),
        compression_enabled=False,
        locking_enabled=True,
        lock_timeout=5.0,
        lock_retry_interval=0.1,
    )
    
    store = ArtifactStore(config)
    
    print("\n1. Testing concurrent uploads with locking enabled")
    print("-" * 60)
    
    # Create multiple threads trying to upload to the same artifact
    task_id = "1.1"
    threads = []
    
    for i in range(5):
        thread = threading.Thread(
            target=upload_worker,
            args=(i, store, task_id)
        )
        threads.append(thread)
    
    # Start all threads simultaneously
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("\n2. Checking final artifact state")
    print("-" * 60)
    
    # Search for artifacts
    artifacts = store.search(task_id=task_id, spec_name="concurrent-test")
    
    print(f"Found {len(artifacts)} artifact(s) for task {task_id}")
    for artifact in artifacts:
        print(f"  - URI: {artifact.uri}")
        print(f"    Size: {artifact.size} bytes")
        print(f"    Created: {artifact.created_at}")
    
    print("\n3. Testing lock manager directly")
    print("-" * 60)
    
    uri = "file:///tmp/test-artifact.txt"
    
    # Check if locked
    is_locked = store.lock_manager.is_locked(uri)
    print(f"Artifact '{uri}' is locked: {is_locked}")
    
    # Acquire lock
    print(f"Acquiring lock for '{uri}'...")
    with store.lock_manager.acquire_write_lock(uri, timeout=2.0):
        print(f"Lock acquired!")
        
        # Check if locked from another context
        is_locked = store.lock_manager.is_locked(uri)
        print(f"Artifact is now locked: {is_locked}")
        
        # Simulate work
        time.sleep(0.5)
    
    print(f"Lock released!")
    
    # Check if still locked
    is_locked = store.lock_manager.is_locked(uri)
    print(f"Artifact is locked after release: {is_locked}")
    
    print("\n4. Testing lock timeout")
    print("-" * 60)
    
    def hold_lock():
        """Thread that holds a lock for a while."""
        with store.lock_manager.acquire_write_lock(uri, timeout=10.0):
            print("Thread 1: Lock acquired, holding for 3 seconds...")
            time.sleep(3)
            print("Thread 1: Releasing lock")
    
    # Start thread that holds lock
    holder_thread = threading.Thread(target=hold_lock)
    holder_thread.start()
    
    # Wait a bit to ensure first thread has the lock
    time.sleep(0.5)
    
    # Try to acquire lock with short timeout
    try:
        print("Thread 2: Attempting to acquire lock with 1s timeout...")
        with store.lock_manager.acquire_write_lock(uri, timeout=1.0):
            print("Thread 2: Lock acquired (unexpected!)")
    except LockTimeoutError as e:
        print(f"Thread 2: Lock timeout as expected - {e}")
    
    # Wait for holder thread to finish
    holder_thread.join()
    
    print("\n5. Testing with locking disabled")
    print("-" * 60)
    
    # Create store with locking disabled
    config_no_lock = ArtifactStoreConfig(
        base_path=Path("/tmp/artifact-store-no-lock-test"),
        compression_enabled=False,
        locking_enabled=False,
    )
    
    store_no_lock = ArtifactStore(config_no_lock)
    
    print("Uploading with locking disabled...")
    uri = store_no_lock.upload(
        task_id="2.1",
        spec_name="no-lock-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Test content without locking",
    )
    print(f"Uploaded to {uri} (no lock required)")
    
    print("\n" + "=" * 60)
    print("Concurrency Control Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

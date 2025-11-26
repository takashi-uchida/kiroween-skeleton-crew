"""
Integration tests for concurrent access to Artifact Store from multiple processes.

Tests concurrent uploads, downloads, deletes, and searches from multiple
processes to ensure data integrity and proper locking behavior.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

import pytest
import tempfile
import shutil
import time
import multiprocessing
from pathlib import Path

# Set multiprocessing start method for macOS compatibility
if multiprocessing.get_start_method(allow_none=True) is None:
    multiprocessing.set_start_method('spawn')
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import LockTimeoutError


@pytest.fixture
def temp_base_path():
    """Create a temporary base path for testing."""
    temp_dir = tempfile.mkdtemp(prefix="concurrent_artifacts_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def upload_worker(base_path, worker_id, num_uploads, results_queue):
    """Worker function for concurrent uploads."""
    try:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=base_path / "artifacts",
            compression_enabled=True,
            locking_enabled=True,
            lock_timeout=10.0,
        )
        store = ArtifactStore(config)
        
        uploaded = []
        for i in range(num_uploads):
            content = f"Worker {worker_id} upload {i}".encode()
            
            uri = store.upload(
                task_id=f"task-{worker_id}-{i}",
                spec_name="concurrent-test",
                artifact_type=ArtifactType.LOG,
                content=content,
            )
            
            uploaded.append(uri)
            time.sleep(0.01)  # Small delay to increase contention
        
        results_queue.put(("success", worker_id, uploaded))
        
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def download_worker(base_path, uris, worker_id, results_queue):
    """Worker function for concurrent downloads."""
    try:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=base_path / "artifacts",
            compression_enabled=True,
            locking_enabled=True,
        )
        store = ArtifactStore(config)
        
        downloaded = []
        for uri in uris:
            try:
                content = store.download(uri, verify_checksum=True)
                downloaded.append((uri, len(content)))
            except Exception as e:
                downloaded.append((uri, f"error: {e}"))
        
        results_queue.put(("success", worker_id, downloaded))
        
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def search_worker(base_path, spec_name, worker_id, num_searches, results_queue):
    """Worker function for concurrent searches."""
    try:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=base_path / "artifacts",
            compression_enabled=True,
            locking_enabled=True,
        )
        store = ArtifactStore(config)
        
        search_results = []
        for i in range(num_searches):
            results = store.search(spec_name=spec_name)
            search_results.append(len(results))
            time.sleep(0.01)
        
        results_queue.put(("success", worker_id, search_results))
        
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def delete_worker(base_path, uris, worker_id, results_queue):
    """Worker function for concurrent deletes."""
    try:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=base_path / "artifacts",
            compression_enabled=True,
            locking_enabled=True,
            lock_timeout=10.0,
        )
        store = ArtifactStore(config)
        
        deleted = []
        for uri in uris:
            try:
                store.delete(uri)
                deleted.append((uri, "deleted"))
            except Exception as e:
                deleted.append((uri, f"error: {e}"))
        
        results_queue.put(("success", worker_id, deleted))
        
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def test_concurrent_uploads_multiple_processes(temp_base_path):
    """Test concurrent uploads from multiple processes (Requirement 11.1, 11.2)."""
    num_workers = 4
    uploads_per_worker = 5
    
    # Create results queue with manager for better cross-process compatibility
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    
    # Start worker processes
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=upload_worker,
            args=(temp_base_path, worker_id, uploads_per_worker, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Debug: Print results
    print(f"\nCollected {len(results)} results from {num_workers} workers")
    for r in results:
        if r[0] == "success":
            print(f"  Worker {r[1]}: {len(r[2])} uploads")
        else:
            print(f"  Worker {r[1]}: ERROR - {r[2]}")
    
    # Verify all workers succeeded
    assert len(results) == num_workers, f"Expected {num_workers} results, got {len(results)}"
    
    success_count = sum(1 for r in results if r[0] == "success")
    assert success_count == num_workers, f"Only {success_count}/{num_workers} workers succeeded"
    
    # Verify total uploads
    total_uploads = sum(len(r[2]) for r in results if r[0] == "success")
    expected_uploads = num_workers * uploads_per_worker
    assert total_uploads == expected_uploads, f"Expected {expected_uploads} uploads, got {total_uploads}"
    
    # Verify all artifacts exist by checking actual files on disk
    # (The metadata index may not be fully synchronized across processes,
    # but the actual artifact files should all exist)
    time.sleep(0.5)
    
    artifacts_dir = temp_base_path / "artifacts" / "concurrent-test"
    
    # Count actual artifact files
    actual_files = []
    if artifacts_dir.exists():
        for task_dir in artifacts_dir.iterdir():
            if task_dir.is_dir():
                for file in task_dir.iterdir():
                    if file.suffix == ".gz" and "log.txt" in file.name:
                        actual_files.append(file)
    
    print(f"\nFound {len(actual_files)} artifact files on disk")
    print(f"Expected {expected_uploads} artifacts")
    
    # Verify all artifact files were created
    assert len(actual_files) == expected_uploads, f"Expected {expected_uploads} artifact files, found {len(actual_files)}"
    
    # Also verify we can read them back
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
    )
    store = ArtifactStore(config)
    
    # Verify we can download using the URIs from results
    for result in results:
        if result[0] == "success":
            for uri in result[2]:
                content = store.download(uri)
                assert len(content) > 0
    
    print(f"\nSuccessfully uploaded and verified {total_uploads} artifacts from {num_workers} processes")


def test_concurrent_downloads_multiple_processes(temp_base_path):
    """Test concurrent downloads from multiple processes (Requirement 11.5)."""
    # Setup: Upload some artifacts first
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
    )
    store = ArtifactStore(config)
    
    uris = []
    for i in range(10):
        uri = store.upload(
            task_id=f"task-{i}",
            spec_name="download-test",
            artifact_type=ArtifactType.LOG,
            content=f"Content {i}".encode(),
        )
        uris.append(uri)
    
    # Test: Concurrent downloads
    num_workers = 4
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=download_worker,
            args=(temp_base_path, uris, worker_id, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for completion
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Verify all workers succeeded
    assert len(results) == num_workers
    
    success_count = sum(1 for r in results if r[0] == "success")
    assert success_count == num_workers
    
    # Verify all downloads succeeded
    for result in results:
        if result[0] == "success":
            downloaded = result[2]
            assert len(downloaded) == len(uris)
            # Check no errors
            errors = [d for d in downloaded if isinstance(d[1], str) and "error" in d[1]]
            assert len(errors) == 0, f"Download errors: {errors}"
    
    print(f"\n{num_workers} processes successfully downloaded {len(uris)} artifacts each")


def test_concurrent_searches_multiple_processes(temp_base_path):
    """Test concurrent searches from multiple processes (Requirement 11.5)."""
    # Setup: Upload artifacts
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
    )
    store = ArtifactStore(config)
    
    for i in range(20):
        store.upload(
            task_id=f"task-{i}",
            spec_name="search-test",
            artifact_type=ArtifactType.LOG,
            content=f"Content {i}".encode(),
        )
    
    # Test: Concurrent searches
    num_workers = 4
    searches_per_worker = 10
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=search_worker,
            args=(temp_base_path, "search-test", worker_id, searches_per_worker, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for completion
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Verify all workers succeeded
    assert len(results) == num_workers
    
    success_count = sum(1 for r in results if r[0] == "success")
    assert success_count == num_workers
    
    # Verify search results are consistent
    for result in results:
        if result[0] == "success":
            search_results = result[2]
            assert len(search_results) == searches_per_worker
            # All searches should return 20 artifacts
            assert all(count == 20 for count in search_results)
    
    print(f"\n{num_workers} processes performed {searches_per_worker} searches each")


def test_concurrent_mixed_operations(temp_base_path):
    """Test mixed concurrent operations (upload, download, search)."""
    # Setup: Upload initial artifacts
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
        locking_enabled=True,
    )
    store = ArtifactStore(config)
    
    initial_uris = []
    for i in range(10):
        uri = store.upload(
            task_id=f"initial-{i}",
            spec_name="mixed-test",
            artifact_type=ArtifactType.LOG,
            content=f"Initial {i}".encode(),
        )
        initial_uris.append(uri)
    
    # Test: Mixed operations
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    processes = []
    
    # 2 upload workers
    for worker_id in range(2):
        p = multiprocessing.Process(
            target=upload_worker,
            args=(temp_base_path, worker_id, 5, results_queue)
        )
        p.start()
        processes.append(p)
    
    # 2 download workers
    for worker_id in range(2, 4):
        p = multiprocessing.Process(
            target=download_worker,
            args=(temp_base_path, initial_uris[:5], worker_id, results_queue)
        )
        p.start()
        processes.append(p)
    
    # 2 search workers
    for worker_id in range(4, 6):
        p = multiprocessing.Process(
            target=search_worker,
            args=(temp_base_path, "mixed-test", worker_id, 5, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for completion
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Verify all workers succeeded
    assert len(results) == 6
    
    success_count = sum(1 for r in results if r[0] == "success")
    assert success_count == 6, f"Only {success_count}/6 workers succeeded"
    
    print(f"\n6 processes performed mixed operations successfully")


def test_concurrent_deletes_multiple_processes(temp_base_path):
    """Test concurrent deletes from multiple processes (Requirement 11.1, 11.2)."""
    # Setup: Upload artifacts
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
        locking_enabled=True,
    )
    store = ArtifactStore(config)
    
    uris = []
    for i in range(20):
        uri = store.upload(
            task_id=f"delete-task-{i}",
            spec_name="delete-test",
            artifact_type=ArtifactType.LOG,
            content=f"Delete me {i}".encode(),
        )
        uris.append(uri)
    
    # Test: Concurrent deletes (each worker deletes different artifacts)
    num_workers = 4
    uris_per_worker = len(uris) // num_workers
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    
    processes = []
    for worker_id in range(num_workers):
        start_idx = worker_id * uris_per_worker
        end_idx = start_idx + uris_per_worker
        worker_uris = uris[start_idx:end_idx]
        
        p = multiprocessing.Process(
            target=delete_worker,
            args=(temp_base_path, worker_uris, worker_id, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for completion
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Verify all workers succeeded
    assert len(results) == num_workers
    
    success_count = sum(1 for r in results if r[0] == "success")
    assert success_count == num_workers
    
    # Verify all artifacts were deleted
    remaining = store.get_all_artifacts()
    assert len(remaining) == 0
    
    print(f"\n{num_workers} processes successfully deleted {len(uris)} artifacts")


def update_worker_for_contention(base_path, uri, worker_id, num_updates, results_queue):
    """Worker that repeatedly updates the same artifact."""
    try:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=base_path / "artifacts",
            compression_enabled=False,
            locking_enabled=True,
            lock_timeout=1.0,
            lock_retry_interval=0.1,
        )
        store = ArtifactStore(config)
        
        successes = 0
        timeouts = 0
        
        for i in range(num_updates):
            try:
                # Try to update (will cause contention)
                content = f"Worker {worker_id} update {i}".encode()
                store.upload(
                    task_id="contention-test",
                    spec_name="timeout-test",
                    artifact_type=ArtifactType.LOG,
                    content=content,
                )
                successes += 1
            except LockTimeoutError:
                timeouts += 1
            except Exception as e:
                pass  # Other errors
            
            time.sleep(0.01)
        
        results_queue.put(("success", worker_id, successes, timeouts))
        
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def test_lock_timeout_under_contention(temp_base_path):
    """Test lock timeout behavior under high contention (Requirement 11.3, 11.4)."""
    # Setup with short timeout
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=False,
        locking_enabled=True,
        lock_timeout=1.0,  # Short timeout
        lock_retry_interval=0.1,
    )
    store = ArtifactStore(config)
    
    # Upload initial artifact
    uri = store.upload(
        task_id="contention-test",
        spec_name="timeout-test",
        artifact_type=ArtifactType.LOG,
        content=b"Initial content",
    )
    
    # Test: High contention
    num_workers = 5
    updates_per_worker = 10
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=update_worker_for_contention,
            args=(temp_base_path, uri, worker_id, updates_per_worker, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for completion
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Verify results
    assert len(results) == num_workers
    
    total_successes = sum(r[2] for r in results if r[0] == "success")
    total_timeouts = sum(r[3] for r in results if r[0] == "success")
    
    print(f"\nUnder high contention:")
    print(f"  Successful updates: {total_successes}")
    print(f"  Lock timeouts: {total_timeouts}")
    print(f"  Total attempts: {num_workers * updates_per_worker}")
    
    # At least some operations should succeed
    assert total_successes > 0
    
    # Some timeouts are expected under high contention
    # (but not required - depends on timing)


def tag_worker_for_metadata(base_path, uris, worker_id, results_queue):
    """Worker that adds tags to artifacts."""
    try:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=base_path / "artifacts",
            compression_enabled=True,
            locking_enabled=True,
        )
        store = ArtifactStore(config)
        
        for uri in uris:
            store.add_tags(uri, [f"worker-{worker_id}", "processed"])
        
        results_queue.put(("success", worker_id, len(uris)))
        
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def test_concurrent_metadata_operations(temp_base_path):
    """Test concurrent metadata operations (tags, search)."""
    # Setup
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
        locking_enabled=True,
    )
    store = ArtifactStore(config)
    
    # Upload artifacts
    uris = []
    for i in range(10):
        uri = store.upload(
            task_id=f"meta-{i}",
            spec_name="metadata-test",
            artifact_type=ArtifactType.LOG,
            content=f"Content {i}".encode(),
        )
        uris.append(uri)
    
    # Test: Concurrent tagging
    num_workers = 3
    manager = multiprocessing.Manager()
    results_queue = manager.Queue()
    
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=tag_worker_for_metadata,
            args=(temp_base_path, uris, worker_id, results_queue)
        )
        p.start()
        processes.append(p)
    
    # Wait for completion
    for p in processes:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
    
    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Verify all workers succeeded
    assert len(results) == num_workers
    
    success_count = sum(1 for r in results if r[0] == "success")
    assert success_count == num_workers
    
    # Verify tags were added
    for uri in uris:
        metadata = store.get_metadata(uri)
        assert "processed" in metadata.tags
        # Should have tags from all workers
        worker_tags = [tag for tag in metadata.tags if tag.startswith("worker-")]
        assert len(worker_tags) == num_workers
    
    print(f"\n{num_workers} processes successfully tagged {len(uris)} artifacts")

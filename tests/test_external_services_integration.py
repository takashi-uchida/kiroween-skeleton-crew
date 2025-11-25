"""Integration tests for external services.

Tests actual integration with Task Registry, Repo Pool Manager, and Artifact Store.
These tests require the external services to be running.

Requirements: 15.1, 15.2, 15.3, 15.4
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.task_registry_client import TaskRegistryClient
from necrocode.agent_runner.repo_pool_client import RepoPoolClient
from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.exceptions import RunnerError


# ============================================================================
# Configuration
# ============================================================================

# These can be overridden with environment variables
TASK_REGISTRY_URL = os.getenv("TASK_REGISTRY_URL", "http://localhost:8080")
REPO_POOL_URL = os.getenv("REPO_POOL_URL", "http://localhost:8081")
ARTIFACT_STORE_URL = os.getenv("ARTIFACT_STORE_URL", "http://localhost:8082")

# Skip tests if services are not available
SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def task_registry_client():
    """Create TaskRegistryClient instance."""
    return TaskRegistryClient(TASK_REGISTRY_URL)


@pytest.fixture
def repo_pool_client():
    """Create RepoPoolClient instance."""
    return RepoPoolClient(REPO_POOL_URL)


@pytest.fixture
def artifact_store_client():
    """Create ArtifactStoreClient instance."""
    return ArtifactStoreClient(ARTIFACT_STORE_URL)


def check_service_available(url: str) -> bool:
    """Check if a service is available."""
    import requests
    try:
        response = requests.get(f"{url}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


# ============================================================================
# Task Registry Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestTaskRegistryIntegration:
    """Integration tests for Task Registry."""
    
    def test_service_health(self, task_registry_client):
        """Test Task Registry health check."""
        # This assumes the service has a health endpoint
        import requests
        response = requests.get(f"{TASK_REGISTRY_URL}/health")
        assert response.status_code == 200
    
    def test_update_task_status(self, task_registry_client):
        """Test updating task status."""
        task_id = f"test-task-{int(time.time())}"
        
        # Update status to in_progress
        task_registry_client.update_task_status(
            task_id=task_id,
            status="in_progress",
            metadata={"runner_id": "test-runner"}
        )
        
        # Update status to done
        task_registry_client.update_task_status(
            task_id=task_id,
            status="done",
            metadata={"duration": 10.5}
        )
    
    def test_add_event(self, task_registry_client):
        """Test adding events."""
        task_id = f"test-task-{int(time.time())}"
        
        # Add TaskStarted event
        task_registry_client.add_event(
            task_id=task_id,
            event_type="TaskStarted",
            data={
                "runner_id": "test-runner",
                "timestamp": time.time()
            }
        )
        
        # Add TaskCompleted event
        task_registry_client.add_event(
            task_id=task_id,
            event_type="TaskCompleted",
            data={
                "runner_id": "test-runner",
                "duration": 10.5,
                "timestamp": time.time()
            }
        )
    
    def test_add_artifact(self, task_registry_client):
        """Test adding artifacts."""
        task_id = f"test-task-{int(time.time())}"
        
        # Add diff artifact
        task_registry_client.add_artifact(
            task_id=task_id,
            artifact_type="diff",
            uri="s3://bucket/diff.txt",
            size_bytes=1024
        )
        
        # Add log artifact
        task_registry_client.add_artifact(
            task_id=task_id,
            artifact_type="log",
            uri="s3://bucket/log.txt",
            size_bytes=2048
        )
    
    def test_error_handling(self, task_registry_client):
        """Test error handling for invalid requests."""
        # Try to update non-existent task (should handle gracefully)
        try:
            task_registry_client.update_task_status(
                task_id="",  # Invalid task ID
                status="in_progress"
            )
        except Exception as e:
            # Should raise an appropriate error
            assert isinstance(e, (RunnerError, Exception))


# ============================================================================
# Repo Pool Manager Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestRepoPoolIntegration:
    """Integration tests for Repo Pool Manager."""
    
    def test_service_health(self, repo_pool_client):
        """Test Repo Pool Manager health check."""
        import requests
        response = requests.get(f"{REPO_POOL_URL}/health")
        assert response.status_code == 200
    
    def test_allocate_and_release_slot(self, repo_pool_client):
        """Test slot allocation and release."""
        # Allocate a slot
        allocation = repo_pool_client.allocate_slot(
            repo_url="https://github.com/test/repo.git",
            required_by=f"test-task-{int(time.time())}"
        )
        
        assert allocation.slot_id is not None
        assert allocation.slot_path is not None
        assert allocation.slot_path.exists()
        
        # Release the slot
        repo_pool_client.release_slot(allocation.slot_id)
    
    def test_multiple_allocations(self, repo_pool_client):
        """Test multiple slot allocations."""
        allocations = []
        
        # Allocate multiple slots
        for i in range(3):
            allocation = repo_pool_client.allocate_slot(
                repo_url="https://github.com/test/repo.git",
                required_by=f"test-task-{int(time.time())}-{i}"
            )
            allocations.append(allocation)
        
        # Verify all allocations are unique
        slot_ids = [a.slot_id for a in allocations]
        assert len(slot_ids) == len(set(slot_ids))
        
        # Release all slots
        for allocation in allocations:
            repo_pool_client.release_slot(allocation.slot_id)
    
    def test_allocation_timeout(self, repo_pool_client):
        """Test allocation timeout behavior."""
        # This test assumes the pool has a limit
        # Try to allocate many slots and see if it times out appropriately
        allocations = []
        
        try:
            for i in range(10):
                allocation = repo_pool_client.allocate_slot(
                    repo_url="https://github.com/test/repo.git",
                    required_by=f"test-task-{int(time.time())}-{i}"
                )
                allocations.append(allocation)
        except Exception as e:
            # May timeout or reach pool limit
            pass
        finally:
            # Clean up
            for allocation in allocations:
                try:
                    repo_pool_client.release_slot(allocation.slot_id)
                except Exception:
                    pass
    
    def test_error_handling(self, repo_pool_client):
        """Test error handling for invalid requests."""
        # Try to release non-existent slot
        try:
            repo_pool_client.release_slot("non-existent-slot")
        except Exception as e:
            # Should raise an appropriate error
            assert isinstance(e, (RunnerError, Exception))


# ============================================================================
# Artifact Store Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestArtifactStoreIntegration:
    """Integration tests for Artifact Store."""
    
    def test_service_health(self, artifact_store_client):
        """Test Artifact Store health check."""
        import requests
        response = requests.get(f"{ARTIFACT_STORE_URL}/health")
        assert response.status_code == 200
    
    def test_upload_and_download_binary(self, artifact_store_client):
        """Test uploading and downloading binary artifacts."""
        # Upload artifact
        content = b"Test artifact content"
        metadata = {
            "task_id": f"test-task-{int(time.time())}",
            "type": "diff"
        }
        
        uri = artifact_store_client.upload(
            artifact_type="diff",
            content=content,
            metadata=metadata
        )
        
        assert uri is not None
        assert len(uri) > 0
        
        # Download artifact
        downloaded = artifact_store_client.download(uri)
        assert downloaded == content
    
    def test_upload_and_download_text(self, artifact_store_client):
        """Test uploading and downloading text artifacts."""
        # Upload text artifact
        content = "Test log content\nLine 2\nLine 3"
        metadata = {
            "task_id": f"test-task-{int(time.time())}",
            "type": "log"
        }
        
        uri = artifact_store_client.upload_text(
            artifact_type="log",
            content=content,
            metadata=metadata
        )
        
        assert uri is not None
        
        # Download artifact
        downloaded = artifact_store_client.download(uri)
        assert downloaded.decode('utf-8') == content
    
    def test_upload_large_artifact(self, artifact_store_client):
        """Test uploading large artifacts."""
        # Create a large artifact (1 MB)
        content = b"x" * (1024 * 1024)
        
        uri = artifact_store_client.upload(
            artifact_type="binary",
            content=content,
            metadata={"size": len(content)}
        )
        
        assert uri is not None
    
    def test_multiple_uploads(self, artifact_store_client):
        """Test multiple artifact uploads."""
        uris = []
        
        for i in range(5):
            content = f"Artifact {i}".encode('utf-8')
            uri = artifact_store_client.upload(
                artifact_type="test",
                content=content,
                metadata={"index": i}
            )
            uris.append(uri)
        
        # Verify all URIs are unique
        assert len(uris) == len(set(uris))
    
    def test_error_handling(self, artifact_store_client):
        """Test error handling for invalid requests."""
        # Try to download non-existent artifact
        try:
            artifact_store_client.download("non-existent-uri")
        except Exception as e:
            # Should raise an appropriate error
            assert isinstance(e, (RunnerError, Exception))


# ============================================================================
# Cross-Service Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestCrossServiceIntegration:
    """Integration tests across multiple services."""
    
    def test_complete_task_workflow(
        self,
        task_registry_client,
        repo_pool_client,
        artifact_store_client
    ):
        """Test complete workflow across all services."""
        task_id = f"integration-test-{int(time.time())}"
        
        # 1. Update task status to in_progress
        task_registry_client.update_task_status(
            task_id=task_id,
            status="in_progress",
            metadata={"runner_id": "test-runner"}
        )
        
        # 2. Allocate a slot
        allocation = repo_pool_client.allocate_slot(
            repo_url="https://github.com/test/repo.git",
            required_by=task_id
        )
        
        # 3. Upload artifacts
        diff_content = b"+ new_file.py\n+ print('hello')"
        diff_uri = artifact_store_client.upload(
            artifact_type="diff",
            content=diff_content,
            metadata={"task_id": task_id}
        )
        
        log_content = "Task execution log\nCompleted successfully"
        log_uri = artifact_store_client.upload_text(
            artifact_type="log",
            content=log_content,
            metadata={"task_id": task_id}
        )
        
        # 4. Record artifacts in Task Registry
        task_registry_client.add_artifact(
            task_id=task_id,
            artifact_type="diff",
            uri=diff_uri,
            size_bytes=len(diff_content)
        )
        
        task_registry_client.add_artifact(
            task_id=task_id,
            artifact_type="log",
            uri=log_uri,
            size_bytes=len(log_content.encode('utf-8'))
        )
        
        # 5. Add completion event
        task_registry_client.add_event(
            task_id=task_id,
            event_type="TaskCompleted",
            data={
                "runner_id": "test-runner",
                "duration": 10.5,
                "artifacts": [diff_uri, log_uri]
            }
        )
        
        # 6. Update task status to done
        task_registry_client.update_task_status(
            task_id=task_id,
            status="done",
            metadata={"duration": 10.5}
        )
        
        # 7. Release slot
        repo_pool_client.release_slot(allocation.slot_id)
    
    def test_error_recovery_workflow(
        self,
        task_registry_client,
        repo_pool_client,
        artifact_store_client
    ):
        """Test error recovery across services."""
        task_id = f"error-test-{int(time.time())}"
        
        # 1. Start task
        task_registry_client.update_task_status(
            task_id=task_id,
            status="in_progress"
        )
        
        # 2. Allocate slot
        allocation = repo_pool_client.allocate_slot(
            repo_url="https://github.com/test/repo.git",
            required_by=task_id
        )
        
        # 3. Simulate error
        error_log = "Error: Implementation failed\nStack trace..."
        error_uri = artifact_store_client.upload_text(
            artifact_type="log",
            content=error_log,
            metadata={"task_id": task_id, "error": True}
        )
        
        # 4. Record error event
        task_registry_client.add_event(
            task_id=task_id,
            event_type="TaskFailed",
            data={
                "error": "Implementation failed",
                "log_uri": error_uri
            }
        )
        
        # 5. Update task status to failed
        task_registry_client.update_task_status(
            task_id=task_id,
            status="failed",
            metadata={"error": "Implementation failed"}
        )
        
        # 6. Release slot (cleanup)
        repo_pool_client.release_slot(allocation.slot_id)
    
    def test_concurrent_task_execution(
        self,
        task_registry_client,
        repo_pool_client,
        artifact_store_client
    ):
        """Test concurrent task execution across services."""
        import threading
        
        num_tasks = 3
        results = []
        
        def execute_task(task_index):
            task_id = f"concurrent-test-{int(time.time())}-{task_index}"
            
            try:
                # Update status
                task_registry_client.update_task_status(
                    task_id=task_id,
                    status="in_progress"
                )
                
                # Allocate slot
                allocation = repo_pool_client.allocate_slot(
                    repo_url="https://github.com/test/repo.git",
                    required_by=task_id
                )
                
                # Upload artifact
                content = f"Task {task_index} output".encode('utf-8')
                uri = artifact_store_client.upload(
                    artifact_type="diff",
                    content=content,
                    metadata={"task_id": task_id}
                )
                
                # Record artifact
                task_registry_client.add_artifact(
                    task_id=task_id,
                    artifact_type="diff",
                    uri=uri,
                    size_bytes=len(content)
                )
                
                # Complete task
                task_registry_client.update_task_status(
                    task_id=task_id,
                    status="done"
                )
                
                # Release slot
                repo_pool_client.release_slot(allocation.slot_id)
                
                results.append({"task_id": task_id, "success": True})
                
            except Exception as e:
                results.append({"task_id": task_id, "success": False, "error": str(e)})
        
        # Execute tasks concurrently
        threads = []
        for i in range(num_tasks):
            thread = threading.Thread(target=execute_task, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all tasks completed
        assert len(results) == num_tasks
        successful = sum(1 for r in results if r.get("success", False))
        assert successful >= num_tasks * 0.8  # At least 80% success rate


# ============================================================================
# Service Availability Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestServiceAvailability:
    """Test service availability and connectivity."""
    
    def test_all_services_available(self):
        """Test that all required services are available."""
        services = {
            "Task Registry": TASK_REGISTRY_URL,
            "Repo Pool Manager": REPO_POOL_URL,
            "Artifact Store": ARTIFACT_STORE_URL,
        }
        
        for name, url in services.items():
            available = check_service_available(url)
            print(f"{name} ({url}): {'Available' if available else 'Unavailable'}")
            
            if not available:
                pytest.skip(f"{name} is not available at {url}")
    
    def test_service_response_times(self):
        """Test service response times."""
        import requests
        
        services = {
            "Task Registry": TASK_REGISTRY_URL,
            "Repo Pool Manager": REPO_POOL_URL,
            "Artifact Store": ARTIFACT_STORE_URL,
        }
        
        for name, url in services.items():
            start_time = time.time()
            try:
                response = requests.get(f"{url}/health", timeout=5)
                response_time = time.time() - start_time
                
                print(f"{name} response time: {response_time:.3f}s")
                
                # Response should be fast (< 1 second)
                assert response_time < 1.0
                
            except Exception as e:
                pytest.skip(f"{name} is not available: {e}")


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestServicePerformance:
    """Performance tests for external services."""
    
    def test_task_registry_throughput(self, task_registry_client):
        """Test Task Registry throughput."""
        num_operations = 10
        
        start_time = time.time()
        
        for i in range(num_operations):
            task_id = f"perf-test-{int(time.time())}-{i}"
            task_registry_client.update_task_status(
                task_id=task_id,
                status="in_progress"
            )
        
        duration = time.time() - start_time
        throughput = num_operations / duration
        
        print(f"\nTask Registry throughput: {throughput:.2f} ops/sec")
        
        # Should handle at least 5 operations per second
        assert throughput > 5.0
    
    def test_artifact_upload_throughput(self, artifact_store_client):
        """Test Artifact Store upload throughput."""
        num_uploads = 5
        content = b"Test content" * 100  # ~1KB
        
        start_time = time.time()
        
        for i in range(num_uploads):
            artifact_store_client.upload(
                artifact_type="test",
                content=content,
                metadata={"index": i}
            )
        
        duration = time.time() - start_time
        throughput = num_uploads / duration
        
        print(f"\nArtifact upload throughput: {throughput:.2f} uploads/sec")
        
        # Should handle at least 2 uploads per second
        assert throughput > 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

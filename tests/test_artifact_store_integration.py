"""
Integration tests for Artifact Store with real storage backends.

Tests the complete workflow with actual storage backends including
filesystem, and validates end-to-end functionality.

Requirements: All
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import (
    ArtifactNotFoundError,
    IntegrityError,
    StorageFullError,
)


@pytest.fixture
def temp_base_path():
    """Create a temporary base path for testing."""
    temp_dir = tempfile.mkdtemp(prefix="artifact_store_integration_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def filesystem_store(temp_base_path):
    """Create an artifact store with filesystem backend."""
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "artifacts",
        compression_enabled=True,
        verify_checksum=True,
        locking_enabled=True,
    )
    return ArtifactStore(config)


def test_complete_workflow_filesystem(filesystem_store):
    """Test complete workflow with filesystem backend."""
    # 1. Upload artifacts
    diff_content = b"diff content for integration test"
    log_content = b"log content for integration test" * 100
    test_content = b'{"test": "result", "passed": true}'
    
    diff_uri = filesystem_store.upload(
        task_id="1.1",
        spec_name="integration-test",
        artifact_type=ArtifactType.DIFF,
        content=diff_content,
        metadata={"author": "integration-test"},
    )
    
    log_uri = filesystem_store.upload(
        task_id="1.1",
        spec_name="integration-test",
        artifact_type=ArtifactType.LOG,
        content=log_content,
    )
    
    test_uri = filesystem_store.upload(
        task_id="1.2",
        spec_name="integration-test",
        artifact_type=ArtifactType.TEST_RESULT,
        content=test_content,
    )
    
    # 2. Verify uploads
    assert filesystem_store.exists(diff_uri)
    assert filesystem_store.exists(log_uri)
    assert filesystem_store.exists(test_uri)
    
    # 3. Download and verify content
    downloaded_diff = filesystem_store.download(diff_uri)
    assert downloaded_diff == diff_content
    
    downloaded_log = filesystem_store.download(log_uri)
    assert downloaded_log == log_content
    
    downloaded_test = filesystem_store.download(test_uri)
    assert downloaded_test == test_content
    
    # 4. Search artifacts
    task_11_artifacts = filesystem_store.search(task_id="1.1")
    assert len(task_11_artifacts) == 2
    
    spec_artifacts = filesystem_store.search(spec_name="integration-test")
    assert len(spec_artifacts) == 3
    
    diff_artifacts = filesystem_store.search(artifact_type=ArtifactType.DIFF)
    assert len(diff_artifacts) == 1
    
    # 5. Verify checksums
    assert filesystem_store.verify_checksum(diff_uri)
    assert filesystem_store.verify_checksum(log_uri)
    assert filesystem_store.verify_checksum(test_uri)
    
    # 6. Get metadata
    diff_metadata = filesystem_store.get_metadata(diff_uri)
    assert diff_metadata is not None
    assert diff_metadata.task_id == "1.1"
    assert diff_metadata.spec_name == "integration-test"
    assert diff_metadata.type == ArtifactType.DIFF
    assert diff_metadata.metadata["author"] == "integration-test"
    
    # 7. Storage usage
    usage = filesystem_store.get_storage_usage()
    assert usage["artifact_count"] == 3
    assert usage["total_size_bytes"] > 0
    
    usage_by_spec = filesystem_store.get_usage_by_spec()
    assert "integration-test" in usage_by_spec
    assert usage_by_spec["integration-test"]["artifact_count"] == 3
    
    usage_by_type = filesystem_store.get_usage_by_type()
    assert "diff" in usage_by_type
    assert "log" in usage_by_type
    assert "test" in usage_by_type
    
    # 8. Delete one artifact
    filesystem_store.delete(test_uri)
    assert not filesystem_store.exists(test_uri)
    
    # 9. Delete by task ID
    deleted_count = filesystem_store.delete_by_task_id("1.1")
    assert deleted_count == 2
    
    # 10. Verify all deleted
    all_artifacts = filesystem_store.get_all_artifacts()
    assert len(all_artifacts) == 0


def test_compression_integration(filesystem_store):
    """Test compression with real storage."""
    # Create compressible content
    content = b"This is a test content that should compress well. " * 100
    
    uri = filesystem_store.upload(
        task_id="2.1",
        spec_name="compression-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Verify metadata shows compression
    metadata = filesystem_store.get_metadata(uri)
    assert metadata.compressed is True
    assert metadata.original_size == len(content)
    assert metadata.size < metadata.original_size
    
    # Download and verify decompression
    downloaded = filesystem_store.download(uri)
    assert downloaded == content
    assert len(downloaded) == metadata.original_size


def test_versioning_integration(temp_base_path):
    """Test versioning with real storage."""
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "versioned",
        versioning_enabled=True,
        compression_enabled=False,
    )
    store = ArtifactStore(config)
    
    # Upload version 1
    content_v1 = b"Version 1 content"
    uri_v1 = store.upload(
        task_id="3.1",
        spec_name="version-test",
        artifact_type=ArtifactType.DIFF,
        content=content_v1,
    )
    
    # Upload version 2 (should create new version)
    content_v2 = b"Version 2 content"
    uri_v2 = store.upload(
        task_id="3.1",
        spec_name="version-test",
        artifact_type=ArtifactType.DIFF,
        content=content_v2,
    )
    
    # URIs should be different
    assert uri_v1 != uri_v2
    
    # Both versions should exist
    assert store.exists(uri_v1)
    assert store.exists(uri_v2)
    
    # Get all versions
    versions = store.get_all_versions("3.1", "version-test", ArtifactType.DIFF)
    assert len(versions) == 2
    assert versions[0].version == 1
    assert versions[1].version == 2
    
    # Download specific versions
    downloaded_v1 = store.download_version("3.1", "version-test", ArtifactType.DIFF, 1)
    assert downloaded_v1 == content_v1
    
    downloaded_v2 = store.download_version("3.1", "version-test", ArtifactType.DIFF, 2)
    assert downloaded_v2 == content_v2
    
    # Delete old versions
    deleted = store.delete_old_versions("3.1", "version-test", ArtifactType.DIFF, keep_latest=1)
    assert deleted == 1
    
    # Only version 2 should remain
    versions = store.get_all_versions("3.1", "version-test", ArtifactType.DIFF)
    assert len(versions) == 1
    assert versions[0].version == 2


def test_tagging_integration(filesystem_store):
    """Test tagging with real storage."""
    # Upload artifact
    uri = filesystem_store.upload(
        task_id="4.1",
        spec_name="tag-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Tagged content",
        tags=["initial", "test"],
    )
    
    # Verify initial tags
    metadata = filesystem_store.get_metadata(uri)
    assert "initial" in metadata.tags
    assert "test" in metadata.tags
    
    # Add more tags
    filesystem_store.add_tags(uri, ["production", "reviewed"])
    
    metadata = filesystem_store.get_metadata(uri)
    assert len(metadata.tags) == 4
    assert "production" in metadata.tags
    assert "reviewed" in metadata.tags
    
    # Search by tags
    results = filesystem_store.search_by_tags(["production"])
    assert len(results) == 1
    assert results[0].uri == uri
    
    # Update tags (replace)
    filesystem_store.update_tags(uri, ["final", "approved"])
    
    metadata = filesystem_store.get_metadata(uri)
    assert len(metadata.tags) == 2
    assert "final" in metadata.tags
    assert "approved" in metadata.tags
    assert "initial" not in metadata.tags
    
    # Remove tags
    filesystem_store.remove_tags(uri, ["approved"])
    
    metadata = filesystem_store.get_metadata(uri)
    assert len(metadata.tags) == 1
    assert "final" in metadata.tags
    assert "approved" not in metadata.tags


def test_retention_policy_integration(filesystem_store):
    """Test retention policy with real storage."""
    # Upload artifacts with different ages
    now = datetime.now()
    
    # Recent artifact (should not be deleted)
    recent_uri = filesystem_store.upload(
        task_id="5.1",
        spec_name="retention-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Recent content",
    )
    
    # Old artifact (simulate by modifying metadata)
    old_uri = filesystem_store.upload(
        task_id="5.2",
        spec_name="retention-test",
        artifact_type=ArtifactType.LOG,
        content=b"Old content",
    )
    
    # Modify metadata to make it old
    old_metadata = filesystem_store.get_metadata(old_uri)
    old_metadata.created_at = now - timedelta(days=10)
    filesystem_store.metadata_manager.save(old_metadata)
    
    # Run cleanup with dry run
    result = filesystem_store.cleanup_expired(dry_run=True)
    assert result["expired_count"] == 1
    # In dry run mode, deleted_count shows what WOULD be deleted
    assert result["deleted_count"] == 1
    
    # Both should still exist after dry run (nothing actually deleted)
    assert filesystem_store.exists(recent_uri)
    assert filesystem_store.exists(old_uri)
    
    # Run actual cleanup
    result = filesystem_store.cleanup_expired(dry_run=False)
    assert result["expired_count"] == 1
    assert result["deleted_count"] == 1
    
    # Recent should exist, old should be deleted
    assert filesystem_store.exists(recent_uri)
    assert not filesystem_store.exists(old_uri)


def test_export_integration(filesystem_store, temp_base_path):
    """Test export functionality with real storage."""
    # Upload multiple artifacts
    filesystem_store.upload(
        task_id="6.1",
        spec_name="export-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Diff for export",
    )
    
    filesystem_store.upload(
        task_id="6.1",
        spec_name="export-test",
        artifact_type=ArtifactType.LOG,
        content=b"Log for export",
    )
    
    filesystem_store.upload(
        task_id="6.2",
        spec_name="export-test",
        artifact_type=ArtifactType.TEST_RESULT,
        content=b'{"test": "export"}',
    )
    
    # Export by spec
    output_path = temp_base_path / "export_spec.zip"
    result_path = filesystem_store.export_by_spec(
        spec_name="export-test",
        output_path=output_path,
        include_metadata=True,
    )
    
    assert result_path.exists()
    assert result_path.stat().st_size > 0
    
    # Export by task
    output_path_task = temp_base_path / "export_task.zip"
    result_path_task = filesystem_store.export_by_task(
        task_id="6.1",
        output_path=output_path_task,
        include_metadata=True,
    )
    
    assert result_path_task.exists()
    assert result_path_task.stat().st_size > 0


def test_integrity_verification_integration(filesystem_store):
    """Test integrity verification with real storage."""
    # Upload artifacts
    uri1 = filesystem_store.upload(
        task_id="7.1",
        spec_name="integrity-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Content 1",
    )
    
    uri2 = filesystem_store.upload(
        task_id="7.2",
        spec_name="integrity-test",
        artifact_type=ArtifactType.LOG,
        content=b"Content 2",
    )
    
    # Verify all
    result = filesystem_store.verify_all()
    assert result["total_artifacts"] == 2
    assert result["valid_count"] == 2
    assert result["invalid_count"] == 0
    assert result["error_count"] == 0
    
    # Corrupt one artifact's checksum
    metadata = filesystem_store.get_metadata(uri1)
    metadata.checksum = "corrupted_checksum"
    filesystem_store.metadata_manager.save(metadata)
    
    # Verify all again
    result = filesystem_store.verify_all()
    assert result["total_artifacts"] == 2
    assert result["valid_count"] == 1
    assert result["invalid_count"] == 1
    assert result["error_count"] == 0
    assert len(result["errors"]) == 1
    assert result["errors"][0]["uri"] == uri1


def test_storage_quota_integration(temp_base_path):
    """Test storage quota enforcement with real storage."""
    # Create store with small quota
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "quota",
        compression_enabled=False,
    )
    config.storage_quota.max_size_gb = 0.000001  # Very small quota (1 byte)
    
    store = ArtifactStore(config)
    
    # First upload should succeed (quota check is approximate)
    content = b"Small content"
    uri = store.upload(
        task_id="8.1",
        spec_name="quota-test",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    assert store.exists(uri)
    
    # Large upload should fail
    large_content = b"x" * (10 * 1024 * 1024)  # 10 MB
    
    with pytest.raises(StorageFullError):
        store.upload(
            task_id="8.2",
            spec_name="quota-test",
            artifact_type=ArtifactType.LOG,
            content=large_content,
        )


def test_error_recovery_integration(filesystem_store):
    """Test error recovery with real storage."""
    # Upload artifact
    uri = filesystem_store.upload(
        task_id="9.1",
        spec_name="error-test",
        artifact_type=ArtifactType.DIFF,
        content=b"Test content",
    )
    
    # Try to download non-existent artifact
    with pytest.raises(ArtifactNotFoundError):
        filesystem_store.download("file:///non/existent/path.txt")
    
    # Try to delete non-existent artifact
    with pytest.raises(ArtifactNotFoundError):
        filesystem_store.delete("file:///non/existent/path.txt")
    
    # Corrupt checksum and try to download with verification
    metadata = filesystem_store.get_metadata(uri)
    original_checksum = metadata.checksum
    metadata.checksum = "corrupted"
    filesystem_store.metadata_manager.save(metadata)
    
    with pytest.raises(IntegrityError):
        filesystem_store.download(uri, verify_checksum=True)
    
    # Create a new store with verification disabled to test download without verification
    config_no_verify = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=filesystem_store.config.base_path,
        compression_enabled=True,
        verify_checksum=False,  # Disable verification in config
    )
    store_no_verify = ArtifactStore(config_no_verify)
    
    # Download without verification should work
    content = store_no_verify.download(uri, verify_checksum=False)
    assert content == b"Test content"
    
    # Restore checksum
    metadata.checksum = original_checksum
    filesystem_store.metadata_manager.save(metadata)


def test_multi_spec_integration(filesystem_store):
    """Test handling multiple specs with real storage."""
    # Upload artifacts for multiple specs
    for spec_num in range(1, 4):
        spec_name = f"spec-{spec_num}"
        for task_num in range(1, 3):
            task_id = f"{task_num}.1"
            
            filesystem_store.upload(
                task_id=task_id,
                spec_name=spec_name,
                artifact_type=ArtifactType.DIFF,
                content=f"Content for {spec_name} task {task_id}".encode(),
            )
    
    # Verify total count
    all_artifacts = filesystem_store.get_all_artifacts()
    assert len(all_artifacts) == 6  # 3 specs * 2 tasks
    
    # Verify per-spec counts
    for spec_num in range(1, 4):
        spec_name = f"spec-{spec_num}"
        spec_artifacts = filesystem_store.search(spec_name=spec_name)
        assert len(spec_artifacts) == 2
    
    # Delete one spec
    deleted = filesystem_store.delete_by_spec_name("spec-2")
    assert deleted == 2
    
    # Verify remaining
    all_artifacts = filesystem_store.get_all_artifacts()
    assert len(all_artifacts) == 4
    
    # Verify spec-2 is gone
    spec2_artifacts = filesystem_store.search(spec_name="spec-2")
    assert len(spec2_artifacts) == 0

"""
Unit tests for main ArtifactStore functionality.

Tests core upload, download, delete, and search operations.
Requirements: All
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import (
    ArtifactNotFoundError,
    IntegrityError,
)


@pytest.fixture
def temp_store(tmp_path):
    """Create a temporary artifact store."""
    config = ArtifactStoreConfig(
        base_path=tmp_path / "artifacts",
        compression_enabled=True,
    )
    return ArtifactStore(config)


@pytest.fixture
def temp_store_no_compression(tmp_path):
    """Create a temporary artifact store without compression."""
    config = ArtifactStoreConfig(
        base_path=tmp_path / "artifacts",
        compression_enabled=False,
    )
    return ArtifactStore(config)


def test_artifact_store_initialization(tmp_path):
    """Test ArtifactStore initialization."""
    config = ArtifactStoreConfig(base_path=tmp_path / "artifacts")
    store = ArtifactStore(config)
    
    assert store.config == config
    assert store.backend is not None
    assert store.metadata_manager is not None
    assert store.compression_engine is not None
    assert store.retention_policy is not None


def test_upload_basic(temp_store):
    """Test basic artifact upload (Requirements: 1.1, 1.2)."""
    content = b"Test diff content"
    
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    assert uri is not None
    assert "test-spec" in uri
    assert "1.1" in uri


def test_upload_with_metadata(temp_store):
    """Test upload with custom metadata (Requirement: 1.3)."""
    content = b"Test content"
    custom_metadata = {"author": "test", "version": "1.0"}
    
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.LOG,
        content=content,
        metadata=custom_metadata,
    )
    
    # Verify metadata was saved
    metadata = temp_store.metadata_manager.load(uri)
    assert metadata.metadata["author"] == "test"
    assert metadata.metadata["version"] == "1.0"


def test_upload_calculates_checksum(temp_store):
    """Test that upload calculates checksum (Requirement: 9.1, 9.2)."""
    content = b"Test content"
    
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Verify checksum was calculated
    metadata = temp_store.metadata_manager.load(uri)
    assert metadata.checksum is not None
    assert len(metadata.checksum) == 64  # SHA256 hex length


def test_upload_with_compression(temp_store):
    """Test upload with compression (Requirement: 8.1)."""
    content = b"Test content to compress" * 100
    
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Verify compression metadata
    metadata = temp_store.metadata_manager.load(uri)
    assert metadata.compressed is True
    assert metadata.original_size == len(content)
    assert metadata.size < metadata.original_size


def test_upload_without_compression(temp_store_no_compression):
    """Test upload without compression."""
    content = b"Test content"
    
    uri = temp_store_no_compression.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Verify no compression
    metadata = temp_store_no_compression.metadata_manager.load(uri)
    assert metadata.compressed is False
    assert metadata.original_size is None


def test_download_basic(temp_store):
    """Test basic artifact download (Requirement: 2.1)."""
    content = b"Test content"
    
    # Upload first
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Download
    downloaded = temp_store.download(uri)
    
    assert downloaded == content


def test_download_not_found(temp_store):
    """Test download of non-existent artifact (Requirement: 2.2)."""
    with pytest.raises(ArtifactNotFoundError):
        temp_store.download("file://non-existent/file.txt")


def test_download_with_checksum_verification(temp_store):
    """Test download with checksum verification (Requirement: 9.3, 9.4)."""
    content = b"Test content"
    
    # Upload
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Download with verification
    downloaded = temp_store.download(uri, verify_checksum=True)
    
    assert downloaded == content


def test_download_with_corrupted_checksum(temp_store):
    """Test download with corrupted data raises IntegrityError."""
    content = b"Test content"
    
    # Upload
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Corrupt the checksum in metadata
    metadata = temp_store.metadata_manager.load(uri)
    metadata.checksum = "corrupted_checksum"
    temp_store.metadata_manager.save(metadata)
    
    # Download with verification should fail
    with pytest.raises(IntegrityError):
        temp_store.download(uri, verify_checksum=True)


def test_delete_basic(temp_store):
    """Test basic artifact deletion (Requirement: 5.1)."""
    content = b"Test content"
    
    # Upload
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Verify exists
    assert temp_store.exists(uri)
    
    # Delete
    temp_store.delete(uri)
    
    # Verify deleted
    assert not temp_store.exists(uri)


def test_delete_by_task_id(temp_store):
    """Test deleting artifacts by task ID (Requirement: 5.2)."""
    # Upload multiple artifacts for same task
    temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff")
    temp_store.upload("1.1", "test-spec", ArtifactType.LOG, b"log")
    temp_store.upload("1.2", "test-spec", ArtifactType.DIFF, b"diff2")
    
    # Delete by task ID
    count = temp_store.delete_by_task_id("1.1")
    
    assert count == 2
    
    # Verify only task 1.1 artifacts deleted
    remaining = temp_store.search(spec_name="test-spec")
    assert len(remaining) == 1
    assert remaining[0].task_id == "1.2"


def test_delete_by_spec_name(temp_store):
    """Test deleting artifacts by spec name (Requirement: 5.3)."""
    # Upload artifacts for different specs
    temp_store.upload("1.1", "spec-a", ArtifactType.DIFF, b"diff1")
    temp_store.upload("1.2", "spec-a", ArtifactType.LOG, b"log1")
    temp_store.upload("1.1", "spec-b", ArtifactType.DIFF, b"diff2")
    
    # Delete by spec name
    count = temp_store.delete_by_spec_name("spec-a")
    
    assert count == 2
    
    # Verify only spec-a artifacts deleted
    remaining = temp_store.get_all_artifacts()
    assert len(remaining) == 1
    assert remaining[0].spec_name == "spec-b"


def test_search_by_task_id(temp_store):
    """Test searching artifacts by task ID (Requirement: 4.1)."""
    # Upload artifacts
    temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff")
    temp_store.upload("1.1", "test-spec", ArtifactType.LOG, b"log")
    temp_store.upload("1.2", "test-spec", ArtifactType.DIFF, b"diff2")
    
    # Search by task ID
    results = temp_store.search(task_id="1.1")
    
    assert len(results) == 2
    assert all(m.task_id == "1.1" for m in results)


def test_search_by_spec_name(temp_store):
    """Test searching artifacts by spec name (Requirement: 4.2)."""
    # Upload artifacts
    temp_store.upload("1.1", "spec-a", ArtifactType.DIFF, b"diff1")
    temp_store.upload("1.2", "spec-a", ArtifactType.LOG, b"log1")
    temp_store.upload("1.1", "spec-b", ArtifactType.DIFF, b"diff2")
    
    # Search by spec name
    results = temp_store.search(spec_name="spec-a")
    
    assert len(results) == 2
    assert all(m.spec_name == "spec-a" for m in results)


def test_search_by_artifact_type(temp_store):
    """Test searching artifacts by type (Requirement: 4.3)."""
    # Upload artifacts
    temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff")
    temp_store.upload("1.2", "test-spec", ArtifactType.LOG, b"log")
    temp_store.upload("1.3", "test-spec", ArtifactType.TEST_RESULT, b"test")
    
    # Search by type
    diff_results = temp_store.search(artifact_type=ArtifactType.DIFF)
    log_results = temp_store.search(artifact_type=ArtifactType.LOG)
    
    assert len(diff_results) == 1
    assert diff_results[0].type == ArtifactType.DIFF
    
    assert len(log_results) == 1
    assert log_results[0].type == ArtifactType.LOG


def test_search_by_date_range(temp_store):
    """Test searching artifacts by date range (Requirement: 4.4)."""
    now = datetime.now()
    
    # Upload artifacts
    temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff")
    
    # Search with date range
    results = temp_store.search(
        created_after=now - timedelta(minutes=1),
        created_before=now + timedelta(minutes=1),
    )
    
    assert len(results) == 1


def test_search_with_multiple_criteria(temp_store):
    """Test searching with multiple criteria (Requirement: 4.5)."""
    # Upload artifacts
    temp_store.upload("1.1", "spec-a", ArtifactType.DIFF, b"diff1")
    temp_store.upload("1.2", "spec-a", ArtifactType.LOG, b"log1")
    temp_store.upload("1.1", "spec-b", ArtifactType.DIFF, b"diff2")
    
    # Search with multiple criteria
    results = temp_store.search(
        spec_name="spec-a",
        artifact_type=ArtifactType.DIFF,
    )
    
    assert len(results) == 1
    assert results[0].spec_name == "spec-a"
    assert results[0].type == ArtifactType.DIFF


def test_exists(temp_store):
    """Test checking if artifact exists."""
    content = b"Test content"
    
    # Upload
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=content,
    )
    
    # Should exist
    assert temp_store.exists(uri) is True
    
    # Non-existent should not exist
    assert temp_store.exists("file://non-existent.txt") is False


def test_get_all_artifacts(temp_store):
    """Test getting all artifacts."""
    # Upload multiple artifacts
    temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff1")
    temp_store.upload("1.2", "test-spec", ArtifactType.LOG, b"log1")
    temp_store.upload("1.3", "test-spec", ArtifactType.TEST_RESULT, b"test1")
    
    # Get all
    all_artifacts = temp_store.get_all_artifacts()
    
    assert len(all_artifacts) == 3


def test_upload_overwrite(temp_store):
    """Test uploading overwrites existing artifact (Requirement: 1.5)."""
    content1 = b"First content"
    content2 = b"Second content"
    
    # Upload first version
    uri1 = temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, content1)
    
    # Upload again (should overwrite)
    uri2 = temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, content2)
    
    # URIs should be the same (overwrite)
    assert uri1 == uri2
    
    # Content should be updated
    downloaded = temp_store.download(uri2)
    assert downloaded == content2


def test_upload_download_roundtrip(temp_store):
    """Test upload and download roundtrip."""
    original_content = b"Test content for roundtrip" * 100
    
    # Upload
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.LOG,
        content=original_content,
    )
    
    # Download
    downloaded_content = temp_store.download(uri)
    
    # Should match original
    assert downloaded_content == original_content


def test_upload_different_artifact_types(temp_store):
    """Test uploading different artifact types."""
    # Upload all types
    diff_uri = temp_store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff")
    log_uri = temp_store.upload("1.1", "test-spec", ArtifactType.LOG, b"log")
    test_uri = temp_store.upload("1.1", "test-spec", ArtifactType.TEST_RESULT, b"test")
    
    # All should be different URIs
    assert diff_uri != log_uri != test_uri
    
    # All should be downloadable
    assert temp_store.download(diff_uri) == b"diff"
    assert temp_store.download(log_uri) == b"log"
    assert temp_store.download(test_uri) == b"test"


def test_large_artifact_upload_download(temp_store):
    """Test uploading and downloading large artifacts."""
    # Create 5 MB content
    large_content = b"x" * (5 * 1024 * 1024)
    
    # Upload
    uri = temp_store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.LOG,
        content=large_content,
    )
    
    # Download
    downloaded = temp_store.download(uri)
    
    # Verify
    assert len(downloaded) == len(large_content)
    assert downloaded == large_content

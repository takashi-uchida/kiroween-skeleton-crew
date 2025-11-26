"""
Unit tests for Artifact Store metadata manager.

Tests metadata storage, retrieval, and indexing functionality.
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import pytest
from pathlib import Path
from datetime import datetime
from necrocode.artifact_store.metadata_manager import MetadataManager
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactMetadata, ArtifactType
from necrocode.artifact_store.exceptions import ArtifactNotFoundError


@pytest.fixture
def temp_metadata_dir(tmp_path):
    """Create a temporary metadata directory."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    return metadata_dir


@pytest.fixture
def metadata_manager(temp_metadata_dir):
    """Create a MetadataManager instance."""
    config = ArtifactStoreConfig(base_path=temp_metadata_dir)
    return MetadataManager(config)


@pytest.fixture
def sample_metadata():
    """Create sample artifact metadata."""
    return ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
    )


def test_metadata_manager_initialization(temp_metadata_dir):
    """Test MetadataManager initialization."""
    config = ArtifactStoreConfig(base_path=temp_metadata_dir)
    manager = MetadataManager(config)
    
    assert manager.metadata_dir.exists()
    assert manager.index_file.exists()


def test_save_metadata(metadata_manager, sample_metadata):
    """Test saving metadata (Requirement 3.1)."""
    metadata_manager.save(sample_metadata)
    
    # Verify metadata file exists
    metadata_file = metadata_manager._get_metadata_path(sample_metadata.uri)
    assert metadata_file.exists()


def test_load_metadata(metadata_manager, sample_metadata):
    """Test loading metadata (Requirement 3.2)."""
    # Save first
    metadata_manager.save(sample_metadata)
    
    # Load
    loaded = metadata_manager.load(sample_metadata.uri)
    
    assert loaded.uri == sample_metadata.uri
    assert loaded.task_id == sample_metadata.task_id
    assert loaded.spec_name == sample_metadata.spec_name
    assert loaded.type == sample_metadata.type
    assert loaded.size == sample_metadata.size
    assert loaded.checksum == sample_metadata.checksum


def test_load_metadata_not_found(metadata_manager):
    """Test loading non-existent metadata raises error."""
    with pytest.raises(ArtifactNotFoundError):
        metadata_manager.load("file://non-existent/file.txt")


def test_get_by_uri(metadata_manager, sample_metadata):
    """Test getting metadata by URI (Requirement 3.3)."""
    # Save first
    metadata_manager.save(sample_metadata)
    
    # Get by URI
    loaded = metadata_manager.get_by_uri(sample_metadata.uri)
    
    assert loaded.uri == sample_metadata.uri
    assert loaded.task_id == sample_metadata.task_id


def test_get_by_task_id(metadata_manager):
    """Test getting metadata by task ID (Requirement 3.4)."""
    # Create multiple artifacts for same task
    metadata1 = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
    )
    
    metadata2 = ArtifactMetadata(
        uri="file://test-spec/1.1/log.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.LOG,
        size=512,
        checksum="def456",
        created_at=datetime.now(),
    )
    
    # Save both
    metadata_manager.save(metadata1)
    metadata_manager.save(metadata2)
    
    # Get by task ID
    results = metadata_manager.get_by_task_id("1.1")
    
    assert len(results) == 2
    assert any(m.type == ArtifactType.DIFF for m in results)
    assert any(m.type == ArtifactType.LOG for m in results)


def test_get_by_spec_name(metadata_manager):
    """Test getting metadata by spec name (Requirement 3.5)."""
    # Create artifacts for same spec
    metadata1 = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
    )
    
    metadata2 = ArtifactMetadata(
        uri="file://test-spec/1.2/log.txt",
        task_id="1.2",
        spec_name="test-spec",
        type=ArtifactType.LOG,
        size=512,
        checksum="def456",
        created_at=datetime.now(),
    )
    
    # Save both
    metadata_manager.save(metadata1)
    metadata_manager.save(metadata2)
    
    # Get by spec name
    results = metadata_manager.get_by_spec_name("test-spec")
    
    assert len(results) == 2
    assert all(m.spec_name == "test-spec" for m in results)


def test_delete_metadata(metadata_manager, sample_metadata):
    """Test deleting metadata."""
    # Save first
    metadata_manager.save(sample_metadata)
    
    # Verify exists
    assert metadata_manager.exists(sample_metadata.uri)
    
    # Delete
    metadata_manager.delete(sample_metadata.uri)
    
    # Verify deleted
    assert not metadata_manager.exists(sample_metadata.uri)


def test_exists(metadata_manager, sample_metadata):
    """Test checking if metadata exists."""
    # Should not exist initially
    assert not metadata_manager.exists(sample_metadata.uri)
    
    # Save
    metadata_manager.save(sample_metadata)
    
    # Should exist now
    assert metadata_manager.exists(sample_metadata.uri)


def test_get_all_metadata(metadata_manager):
    """Test getting all metadata."""
    # Create multiple artifacts
    for i in range(3):
        metadata = ArtifactMetadata(
            uri=f"file://test-spec/{i}.1/diff.txt",
            task_id=f"{i}.1",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum=f"checksum{i}",
            created_at=datetime.now(),
        )
        metadata_manager.save(metadata)
    
    # Get all
    all_metadata = metadata_manager.get_all()
    
    assert len(all_metadata) == 3


def test_update_metadata(metadata_manager, sample_metadata):
    """Test updating existing metadata."""
    # Save initial
    metadata_manager.save(sample_metadata)
    
    # Update
    sample_metadata.tags = ["updated", "test"]
    sample_metadata.metadata["key"] = "value"
    metadata_manager.save(sample_metadata)
    
    # Load and verify
    loaded = metadata_manager.load(sample_metadata.uri)
    assert loaded.tags == ["updated", "test"]
    assert loaded.metadata["key"] == "value"


def test_metadata_index_updated_on_save(metadata_manager, sample_metadata):
    """Test that metadata index is updated when saving (Requirement 4.1)."""
    # Save metadata
    metadata_manager.save(sample_metadata)
    
    # Verify index contains the metadata
    index = metadata_manager._load_index()
    assert sample_metadata.uri in index


def test_metadata_index_updated_on_delete(metadata_manager, sample_metadata):
    """Test that metadata index is updated when deleting."""
    # Save metadata
    metadata_manager.save(sample_metadata)
    
    # Delete
    metadata_manager.delete(sample_metadata.uri)
    
    # Verify index no longer contains the metadata
    index = metadata_manager._load_index()
    assert sample_metadata.uri not in index


def test_search_by_type(metadata_manager):
    """Test searching metadata by artifact type."""
    # Create artifacts of different types
    diff_metadata = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
    )
    
    log_metadata = ArtifactMetadata(
        uri="file://test-spec/1.1/log.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.LOG,
        size=512,
        checksum="def456",
        created_at=datetime.now(),
    )
    
    metadata_manager.save(diff_metadata)
    metadata_manager.save(log_metadata)
    
    # Search by type
    diff_results = metadata_manager.search(artifact_type=ArtifactType.DIFF)
    log_results = metadata_manager.search(artifact_type=ArtifactType.LOG)
    
    assert len(diff_results) == 1
    assert diff_results[0].type == ArtifactType.DIFF
    
    assert len(log_results) == 1
    assert log_results[0].type == ArtifactType.LOG


def test_search_by_multiple_criteria(metadata_manager):
    """Test searching metadata by multiple criteria."""
    # Create artifacts
    metadata1 = ArtifactMetadata(
        uri="file://spec-a/1.1/diff.txt",
        task_id="1.1",
        spec_name="spec-a",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
    )
    
    metadata2 = ArtifactMetadata(
        uri="file://spec-a/1.2/diff.txt",
        task_id="1.2",
        spec_name="spec-a",
        type=ArtifactType.DIFF,
        size=512,
        checksum="def456",
        created_at=datetime.now(),
    )
    
    metadata3 = ArtifactMetadata(
        uri="file://spec-b/1.1/diff.txt",
        task_id="1.1",
        spec_name="spec-b",
        type=ArtifactType.DIFF,
        size=2048,
        checksum="ghi789",
        created_at=datetime.now(),
    )
    
    metadata_manager.save(metadata1)
    metadata_manager.save(metadata2)
    metadata_manager.save(metadata3)
    
    # Search by spec_name and type
    results = metadata_manager.search(
        spec_name="spec-a",
        artifact_type=ArtifactType.DIFF
    )
    
    assert len(results) == 2
    assert all(m.spec_name == "spec-a" for m in results)
    assert all(m.type == ArtifactType.DIFF for m in results)


def test_search_with_tags(metadata_manager):
    """Test searching metadata by tags."""
    # Create artifacts with tags
    metadata1 = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
        tags=["important", "production"],
    )
    
    metadata2 = ArtifactMetadata(
        uri="file://test-spec/1.2/diff.txt",
        task_id="1.2",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=512,
        checksum="def456",
        created_at=datetime.now(),
        tags=["test", "development"],
    )
    
    metadata_manager.save(metadata1)
    metadata_manager.save(metadata2)
    
    # Search by tag
    results = metadata_manager.search(tags=["important"])
    
    assert len(results) == 1
    assert "important" in results[0].tags


def test_metadata_persistence(metadata_manager, sample_metadata):
    """Test that metadata persists across manager instances."""
    # Save with first manager
    metadata_manager.save(sample_metadata)
    
    # Create new manager instance
    new_manager = MetadataManager(metadata_manager.config)
    
    # Load with new manager
    loaded = new_manager.load(sample_metadata.uri)
    
    assert loaded.uri == sample_metadata.uri
    assert loaded.task_id == sample_metadata.task_id


def test_concurrent_metadata_operations(metadata_manager):
    """Test concurrent metadata operations."""
    # Save multiple artifacts
    for i in range(10):
        metadata = ArtifactMetadata(
            uri=f"file://test-spec/{i}.1/diff.txt",
            task_id=f"{i}.1",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum=f"checksum{i}",
            created_at=datetime.now(),
        )
        metadata_manager.save(metadata)
    
    # Verify all saved
    all_metadata = metadata_manager.get_all()
    assert len(all_metadata) == 10


def test_metadata_with_special_characters(metadata_manager):
    """Test metadata with special characters in URI."""
    metadata = ArtifactMetadata(
        uri="file://test-spec/task-1.1/diff-file_v2.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now(),
    )
    
    # Save and load
    metadata_manager.save(metadata)
    loaded = metadata_manager.load(metadata.uri)
    
    assert loaded.uri == metadata.uri

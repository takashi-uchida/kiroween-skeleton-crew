"""
Tests for artifact versioning functionality.
"""

import pytest
import tempfile
from pathlib import Path

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import ArtifactNotFoundError


@pytest.fixture
def temp_store_with_versioning():
    """Create a temporary artifact store with versioning enabled."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ArtifactStoreConfig(
            base_path=Path(temp_dir) / "artifacts",
            compression_enabled=True,
            versioning_enabled=True,
        )
        yield ArtifactStore(config)


@pytest.fixture
def temp_store_without_versioning():
    """Create a temporary artifact store without versioning."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ArtifactStoreConfig(
            base_path=Path(temp_dir) / "artifacts",
            compression_enabled=True,
            versioning_enabled=False,
        )
        yield ArtifactStore(config)


def test_versioning_enabled_creates_multiple_versions(temp_store_with_versioning):
    """Test that versioning enabled creates multiple versions."""
    store = temp_store_with_versioning
    
    # Upload three versions
    content1 = b"Version 1 content"
    content2 = b"Version 2 content"
    content3 = b"Version 3 content"
    
    uri1 = store.upload("1.1", "test-spec", ArtifactType.DIFF, content1)
    uri2 = store.upload("1.1", "test-spec", ArtifactType.DIFF, content2)
    uri3 = store.upload("1.1", "test-spec", ArtifactType.DIFF, content3)
    
    # Verify URIs are different (contain version numbers)
    assert uri1 != uri2 != uri3
    assert ".v1." in uri1
    assert ".v2." in uri2
    assert ".v3." in uri3
    
    # Verify all versions exist
    versions = store.get_all_versions("1.1", "test-spec", ArtifactType.DIFF)
    assert len(versions) == 3
    assert versions[0].version == 1
    assert versions[1].version == 2
    assert versions[2].version == 3


def test_versioning_disabled_overwrites(temp_store_without_versioning):
    """Test that versioning disabled overwrites existing artifacts."""
    store = temp_store_without_versioning
    
    # Upload twice
    content1 = b"First content"
    content2 = b"Second content (should overwrite)"
    
    uri1 = store.upload("1.1", "test-spec", ArtifactType.DIFF, content1)
    uri2 = store.upload("1.1", "test-spec", ArtifactType.DIFF, content2)
    
    # URIs should be the same (no version number)
    assert uri1 == uri2
    assert ".v1." not in uri1
    assert ".v2." not in uri2
    
    # Only one version should exist
    versions = store.get_all_versions("1.1", "test-spec", ArtifactType.DIFF)
    assert len(versions) == 1
    
    # Content should be the second upload
    downloaded = store.download(uri2)
    assert downloaded == content2


def test_get_all_versions_returns_sorted(temp_store_with_versioning):
    """Test that get_all_versions returns versions in ascending order."""
    store = temp_store_with_versioning
    
    # Upload versions
    for i in range(5):
        store.upload("1.1", "test-spec", ArtifactType.LOG, f"Version {i+1}".encode())
    
    # Get all versions
    versions = store.get_all_versions("1.1", "test-spec", ArtifactType.LOG)
    
    # Verify sorted by version number
    assert len(versions) == 5
    for i, metadata in enumerate(versions):
        assert metadata.version == i + 1


def test_download_version_specific(temp_store_with_versioning):
    """Test downloading a specific version."""
    store = temp_store_with_versioning
    
    # Upload versions
    content1 = b"Version 1"
    content2 = b"Version 2"
    content3 = b"Version 3"
    
    store.upload("1.1", "test-spec", ArtifactType.DIFF, content1)
    store.upload("1.1", "test-spec", ArtifactType.DIFF, content2)
    store.upload("1.1", "test-spec", ArtifactType.DIFF, content3)
    
    # Download specific versions
    downloaded1 = store.download_version("1.1", "test-spec", ArtifactType.DIFF, 1)
    downloaded2 = store.download_version("1.1", "test-spec", ArtifactType.DIFF, 2)
    downloaded3 = store.download_version("1.1", "test-spec", ArtifactType.DIFF, 3)
    
    # Verify content
    assert downloaded1 == content1
    assert downloaded2 == content2
    assert downloaded3 == content3


def test_download_version_not_found(temp_store_with_versioning):
    """Test downloading a non-existent version raises error."""
    store = temp_store_with_versioning
    
    # Upload one version
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Version 1")
    
    # Try to download non-existent version
    with pytest.raises(ArtifactNotFoundError):
        store.download_version("1.1", "test-spec", ArtifactType.DIFF, 999)


def test_delete_old_versions_keeps_latest(temp_store_with_versioning):
    """Test deleting old versions keeps the latest N versions."""
    store = temp_store_with_versioning
    
    # Upload 5 versions
    for i in range(5):
        store.upload("1.1", "test-spec", ArtifactType.LOG, f"Version {i+1}".encode())
    
    # Delete old versions, keep latest 2
    deleted_count = store.delete_old_versions("1.1", "test-spec", ArtifactType.LOG, keep_latest=2)
    
    # Verify 3 versions were deleted
    assert deleted_count == 3
    
    # Verify only 2 versions remain
    remaining = store.get_all_versions("1.1", "test-spec", ArtifactType.LOG)
    assert len(remaining) == 2
    assert remaining[0].version == 4
    assert remaining[1].version == 5


def test_delete_old_versions_no_deletion_if_under_limit(temp_store_with_versioning):
    """Test that no versions are deleted if count is under keep_latest."""
    store = temp_store_with_versioning
    
    # Upload 2 versions
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Version 1")
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Version 2")
    
    # Try to delete old versions, keep latest 5
    deleted_count = store.delete_old_versions("1.1", "test-spec", ArtifactType.DIFF, keep_latest=5)
    
    # No versions should be deleted
    assert deleted_count == 0
    
    # All versions should remain
    remaining = store.get_all_versions("1.1", "test-spec", ArtifactType.DIFF)
    assert len(remaining) == 2


def test_version_numbers_increment_correctly(temp_store_with_versioning):
    """Test that version numbers increment correctly."""
    store = temp_store_with_versioning
    
    # Upload versions
    for i in range(10):
        uri = store.upload("1.1", "test-spec", ArtifactType.TEST_RESULT, f"Version {i+1}".encode())
        assert f".v{i+1}." in uri
    
    # Verify all versions
    versions = store.get_all_versions("1.1", "test-spec", ArtifactType.TEST_RESULT)
    assert len(versions) == 10
    for i, metadata in enumerate(versions):
        assert metadata.version == i + 1


def test_versioning_with_different_artifact_types(temp_store_with_versioning):
    """Test that versioning works independently for different artifact types."""
    store = temp_store_with_versioning
    
    # Upload versions for different types
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Diff v1")
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Diff v2")
    
    store.upload("1.1", "test-spec", ArtifactType.LOG, b"Log v1")
    store.upload("1.1", "test-spec", ArtifactType.LOG, b"Log v2")
    store.upload("1.1", "test-spec", ArtifactType.LOG, b"Log v3")
    
    # Verify versions are independent
    diff_versions = store.get_all_versions("1.1", "test-spec", ArtifactType.DIFF)
    log_versions = store.get_all_versions("1.1", "test-spec", ArtifactType.LOG)
    
    assert len(diff_versions) == 2
    assert len(log_versions) == 3


def test_versioning_with_different_tasks(temp_store_with_versioning):
    """Test that versioning works independently for different tasks."""
    store = temp_store_with_versioning
    
    # Upload versions for different tasks
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Task 1.1 v1")
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"Task 1.1 v2")
    
    store.upload("1.2", "test-spec", ArtifactType.DIFF, b"Task 1.2 v1")
    store.upload("1.2", "test-spec", ArtifactType.DIFF, b"Task 1.2 v2")
    store.upload("1.2", "test-spec", ArtifactType.DIFF, b"Task 1.2 v3")
    
    # Verify versions are independent
    task1_versions = store.get_all_versions("1.1", "test-spec", ArtifactType.DIFF)
    task2_versions = store.get_all_versions("1.2", "test-spec", ArtifactType.DIFF)
    
    assert len(task1_versions) == 2
    assert len(task2_versions) == 3

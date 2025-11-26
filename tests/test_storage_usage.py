"""
Tests for storage usage monitoring functionality.
"""

import pytest
from pathlib import Path
import shutil

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig, StorageQuotaConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import StorageFullError


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests"""
    test_dir = tmp_path / "test_artifacts"
    test_dir.mkdir()
    yield test_dir
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def store(temp_dir):
    """Create an ArtifactStore instance for testing"""
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_dir,
        compression_enabled=True,
        storage_quota=StorageQuotaConfig(
            max_size_gb=0.01,  # 10 MB limit
            warn_threshold=0.8,
        ),
    )
    return ArtifactStore(config)


def test_get_storage_usage_empty(store):
    """Test getting storage usage when no artifacts exist"""
    usage = store.get_storage_usage()
    
    assert usage["total_size_bytes"] == 0
    assert usage["total_size_mb"] == 0
    assert usage["total_size_gb"] == 0
    assert usage["artifact_count"] == 0
    assert usage["quota_used_percent"] == 0
    assert usage["quota_warning"] is False


def test_get_storage_usage_with_artifacts(store):
    """Test getting storage usage with artifacts"""
    # Upload some artifacts
    content1 = b"test content 1" * 100
    content2 = b"test content 2" * 200
    
    store.upload("1.1", "test-spec", ArtifactType.DIFF, content1)
    store.upload("1.2", "test-spec", ArtifactType.LOG, content2)
    
    usage = store.get_storage_usage()
    
    assert usage["total_size_bytes"] > 0
    assert usage["total_size_mb"] > 0
    assert usage["artifact_count"] == 2
    assert 0 <= usage["quota_used_percent"] <= 100


def test_get_usage_by_spec(store):
    """Test getting storage usage by spec"""
    # Upload artifacts for different specs
    store.upload("1.1", "spec-a", ArtifactType.DIFF, b"content a" * 100)
    store.upload("1.2", "spec-a", ArtifactType.LOG, b"content a" * 100)
    store.upload("2.1", "spec-b", ArtifactType.DIFF, b"content b" * 100)
    
    usage_by_spec = store.get_usage_by_spec()
    
    assert "spec-a" in usage_by_spec
    assert "spec-b" in usage_by_spec
    
    assert usage_by_spec["spec-a"]["artifact_count"] == 2
    assert usage_by_spec["spec-b"]["artifact_count"] == 1
    
    assert usage_by_spec["spec-a"]["size_bytes"] > 0
    assert usage_by_spec["spec-b"]["size_bytes"] > 0


def test_get_usage_by_type(store):
    """Test getting storage usage by type"""
    # Upload artifacts of different types
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"diff content" * 100)
    store.upload("1.2", "test-spec", ArtifactType.LOG, b"log content" * 100)
    store.upload("1.3", "test-spec", ArtifactType.TEST_RESULT, b"test content" * 100)
    
    usage_by_type = store.get_usage_by_type()
    
    assert "diff" in usage_by_type
    assert "log" in usage_by_type
    assert "test" in usage_by_type
    
    assert usage_by_type["diff"]["artifact_count"] == 1
    assert usage_by_type["log"]["artifact_count"] == 1
    assert usage_by_type["test"]["artifact_count"] == 1


def test_storage_quota_warning(temp_dir):
    """Test storage quota warning threshold"""
    # Create store with small quota
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_dir,
        compression_enabled=False,  # Disable compression for predictable sizes
        storage_quota=StorageQuotaConfig(
            max_size_gb=0.000001,  # 1 KB limit (1024 bytes)
            warn_threshold=0.4,  # Warn at 40%
        ),
    )
    store = ArtifactStore(config)
    
    # Upload small artifact (should not warn)
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"x" * 100)
    
    usage = store.get_storage_usage()
    # With 100 bytes and 1 KB limit, we're at ~10%, so no warning
    assert usage["quota_warning"] is False
    
    # Upload more to trigger warning (total will be 500 bytes = ~49% of 1024)
    store.upload("1.2", "test-spec", ArtifactType.LOG, b"x" * 400)
    
    usage = store.get_storage_usage()
    # Now we should be above 40%
    assert usage["quota_warning"] is True


def test_storage_quota_enforcement(temp_dir):
    """Test storage quota enforcement"""
    # Create store with very small quota
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_dir,
        compression_enabled=False,  # Disable compression for predictable sizes
        storage_quota=StorageQuotaConfig(
            max_size_gb=0.000001,  # 1 KB limit
            warn_threshold=0.8,
        ),
    )
    store = ArtifactStore(config)
    
    # Try to upload artifact that exceeds quota
    large_content = b"x" * 2000  # 2 KB
    
    with pytest.raises(StorageFullError) as exc_info:
        store.upload("1.1", "test-spec", ArtifactType.DIFF, large_content)
    
    assert "quota exceeded" in str(exc_info.value).lower()


def test_usage_after_deletion(store):
    """Test that usage is updated after deletion"""
    # Upload artifacts
    store.upload("1.1", "test-spec", ArtifactType.DIFF, b"content" * 100)
    store.upload("1.2", "test-spec", ArtifactType.LOG, b"content" * 100)
    
    usage_before = store.get_storage_usage()
    assert usage_before["artifact_count"] == 2
    
    # Delete one artifact
    store.delete_by_task_id("1.1")
    
    usage_after = store.get_storage_usage()
    assert usage_after["artifact_count"] == 1
    assert usage_after["total_size_bytes"] < usage_before["total_size_bytes"]


def test_usage_calculations(store):
    """Test that size calculations are correct"""
    # Upload artifact with known size
    content = b"x" * 1000  # 1000 bytes
    store.upload("1.1", "test-spec", ArtifactType.DIFF, content)
    
    usage = store.get_storage_usage()
    
    # Check conversions (accounting for compression)
    assert usage["total_size_bytes"] > 0
    assert usage["total_size_mb"] == round(usage["total_size_bytes"] / (1024 * 1024), 2)
    assert usage["total_size_gb"] == round(usage["total_size_bytes"] / (1024 * 1024 * 1024), 2)


def test_usage_by_spec_multiple_specs(store):
    """Test usage calculation with multiple specs"""
    # Upload artifacts for multiple specs
    specs = ["spec-a", "spec-b", "spec-c"]
    
    for spec in specs:
        for i in range(3):
            store.upload(f"{i}.1", spec, ArtifactType.DIFF, b"content" * 100)
    
    usage_by_spec = store.get_usage_by_spec()
    
    assert len(usage_by_spec) == 3
    for spec in specs:
        assert spec in usage_by_spec
        assert usage_by_spec[spec]["artifact_count"] == 3


def test_usage_by_type_all_types(store):
    """Test usage calculation with all artifact types"""
    types = [ArtifactType.DIFF, ArtifactType.LOG, ArtifactType.TEST_RESULT]
    
    for artifact_type in types:
        store.upload("1.1", "test-spec", artifact_type, b"content" * 100)
    
    usage_by_type = store.get_usage_by_type()
    
    assert len(usage_by_type) == 3
    assert "diff" in usage_by_type
    assert "log" in usage_by_type
    assert "test" in usage_by_type

"""
Unit tests for Artifact Store data models.

Tests serialization/deserialization of ArtifactMetadata and ArtifactType.
Requirements: 3.1
"""

import pytest
import json
from datetime import datetime
from necrocode.artifact_store.models import ArtifactMetadata, ArtifactType


def test_artifact_type_values():
    """Test ArtifactType enum values."""
    assert ArtifactType.DIFF.value == "diff"
    assert ArtifactType.LOG.value == "log"
    assert ArtifactType.TEST_RESULT.value == "test"


def test_artifact_type_from_string():
    """Test ArtifactType creation from string."""
    assert ArtifactType("diff") == ArtifactType.DIFF
    assert ArtifactType("log") == ArtifactType.LOG
    assert ArtifactType("test") == ArtifactType.TEST_RESULT


def test_artifact_metadata_creation():
    """Test basic ArtifactMetadata creation."""
    now = datetime.now()
    metadata = ArtifactMetadata(
        uri="file://test.diff",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=now,
    )
    
    assert metadata.uri == "file://test.diff"
    assert metadata.task_id == "1.1"
    assert metadata.spec_name == "test-spec"
    assert metadata.type == ArtifactType.DIFF
    assert metadata.size == 1024
    assert metadata.checksum == "abc123"
    assert metadata.created_at == now
    assert metadata.compressed is False
    assert metadata.original_size is None
    assert metadata.mime_type == "text/plain"
    assert metadata.tags == []
    assert metadata.version == 1
    assert metadata.metadata == {}


def test_artifact_metadata_with_optional_fields():
    """Test ArtifactMetadata with optional fields."""
    now = datetime.now()
    metadata = ArtifactMetadata(
        uri="file://test.log",
        task_id="2.1",
        spec_name="test-spec",
        type=ArtifactType.LOG,
        size=512,
        checksum="def456",
        created_at=now,
        compressed=True,
        original_size=2048,
        mime_type="application/json",
        tags=["important", "production"],
        version=3,
        metadata={"key": "value", "count": 42},
    )
    
    assert metadata.compressed is True
    assert metadata.original_size == 2048
    assert metadata.mime_type == "application/json"
    assert metadata.tags == ["important", "production"]
    assert metadata.version == 3
    assert metadata.metadata == {"key": "value", "count": 42}


def test_artifact_metadata_to_dict():
    """Test ArtifactMetadata serialization to dictionary."""
    now = datetime.now()
    metadata = ArtifactMetadata(
        uri="file://test.diff",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=now,
        compressed=True,
        original_size=2048,
        tags=["tag1", "tag2"],
        version=2,
    )
    
    data = metadata.to_dict()
    
    assert data["uri"] == "file://test.diff"
    assert data["task_id"] == "1.1"
    assert data["spec_name"] == "test-spec"
    assert data["type"] == "diff"
    assert data["size"] == 1024
    assert data["checksum"] == "abc123"
    assert data["created_at"] == now.isoformat()
    assert data["compressed"] is True
    assert data["original_size"] == 2048
    assert data["tags"] == ["tag1", "tag2"]
    assert data["version"] == 2


def test_artifact_metadata_from_dict():
    """Test ArtifactMetadata deserialization from dictionary."""
    now = datetime.now()
    data = {
        "uri": "file://test.log",
        "task_id": "2.1",
        "spec_name": "test-spec",
        "type": "log",
        "size": 512,
        "checksum": "def456",
        "created_at": now.isoformat(),
        "compressed": True,
        "original_size": 1024,
        "mime_type": "text/plain",
        "tags": ["tag1"],
        "version": 1,
        "metadata": {"key": "value"},
    }
    
    metadata = ArtifactMetadata.from_dict(data)
    
    assert metadata.uri == "file://test.log"
    assert metadata.task_id == "2.1"
    assert metadata.spec_name == "test-spec"
    assert metadata.type == ArtifactType.LOG
    assert metadata.size == 512
    assert metadata.checksum == "def456"
    assert metadata.created_at == datetime.fromisoformat(now.isoformat())
    assert metadata.compressed is True
    assert metadata.original_size == 1024
    assert metadata.tags == ["tag1"]
    assert metadata.version == 1
    assert metadata.metadata == {"key": "value"}


def test_artifact_metadata_serialization_roundtrip():
    """Test ArtifactMetadata serialization and deserialization roundtrip."""
    now = datetime.now()
    original = ArtifactMetadata(
        uri="file://test.test",
        task_id="3.1",
        spec_name="test-spec",
        type=ArtifactType.TEST_RESULT,
        size=2048,
        checksum="ghi789",
        created_at=now,
        compressed=True,
        original_size=4096,
        mime_type="application/json",
        tags=["test", "ci"],
        version=5,
        metadata={"passed": 10, "failed": 2},
    )
    
    # Serialize
    data = original.to_dict()
    
    # Deserialize
    restored = ArtifactMetadata.from_dict(data)
    
    # Verify
    assert restored.uri == original.uri
    assert restored.task_id == original.task_id
    assert restored.spec_name == original.spec_name
    assert restored.type == original.type
    assert restored.size == original.size
    assert restored.checksum == original.checksum
    assert restored.created_at.isoformat() == original.created_at.isoformat()
    assert restored.compressed == original.compressed
    assert restored.original_size == original.original_size
    assert restored.mime_type == original.mime_type
    assert restored.tags == original.tags
    assert restored.version == original.version
    assert restored.metadata == original.metadata


def test_artifact_metadata_to_json():
    """Test ArtifactMetadata JSON serialization."""
    now = datetime.now()
    metadata = ArtifactMetadata(
        uri="file://test.diff",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=now,
    )
    
    json_str = metadata.to_json()
    
    # Should be valid JSON
    data = json.loads(json_str)
    assert data["uri"] == "file://test.diff"
    assert data["task_id"] == "1.1"
    assert data["type"] == "diff"


def test_artifact_metadata_from_json():
    """Test ArtifactMetadata JSON deserialization."""
    now = datetime.now()
    json_str = json.dumps({
        "uri": "file://test.log",
        "task_id": "2.1",
        "spec_name": "test-spec",
        "type": "log",
        "size": 512,
        "checksum": "def456",
        "created_at": now.isoformat(),
        "compressed": False,
        "original_size": None,
        "mime_type": "text/plain",
        "tags": [],
        "version": 1,
        "metadata": {},
    })
    
    metadata = ArtifactMetadata.from_json(json_str)
    
    assert metadata.uri == "file://test.log"
    assert metadata.task_id == "2.1"
    assert metadata.type == ArtifactType.LOG


def test_artifact_metadata_json_roundtrip():
    """Test ArtifactMetadata JSON serialization and deserialization roundtrip."""
    now = datetime.now()
    original = ArtifactMetadata(
        uri="file://test.test",
        task_id="3.1",
        spec_name="test-spec",
        type=ArtifactType.TEST_RESULT,
        size=2048,
        checksum="ghi789",
        created_at=now,
        tags=["test"],
        version=2,
    )
    
    # Serialize to JSON
    json_str = original.to_json()
    
    # Deserialize from JSON
    restored = ArtifactMetadata.from_json(json_str)
    
    # Verify
    assert restored.uri == original.uri
    assert restored.task_id == original.task_id
    assert restored.type == original.type
    assert restored.size == original.size
    assert restored.checksum == original.checksum


def test_artifact_metadata_from_dict_with_defaults():
    """Test ArtifactMetadata deserialization with missing optional fields."""
    now = datetime.now()
    data = {
        "uri": "file://test.diff",
        "task_id": "1.1",
        "spec_name": "test-spec",
        "type": "diff",
        "size": 1024,
        "checksum": "abc123",
        "created_at": now.isoformat(),
    }
    
    metadata = ArtifactMetadata.from_dict(data)
    
    # Should use default values
    assert metadata.compressed is False
    assert metadata.original_size is None
    assert metadata.mime_type == "text/plain"
    assert metadata.tags == []
    assert metadata.version == 1
    assert metadata.metadata == {}


def test_artifact_metadata_with_empty_tags():
    """Test ArtifactMetadata with empty tags list."""
    now = datetime.now()
    metadata = ArtifactMetadata(
        uri="file://test.diff",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=now,
        tags=[],
    )
    
    assert metadata.tags == []
    
    # Roundtrip
    data = metadata.to_dict()
    restored = ArtifactMetadata.from_dict(data)
    assert restored.tags == []


def test_artifact_metadata_with_empty_metadata():
    """Test ArtifactMetadata with empty metadata dict."""
    now = datetime.now()
    metadata = ArtifactMetadata(
        uri="file://test.diff",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=now,
        metadata={},
    )
    
    assert metadata.metadata == {}
    
    # Roundtrip
    data = metadata.to_dict()
    restored = ArtifactMetadata.from_dict(data)
    assert restored.metadata == {}

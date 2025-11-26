"""
Unit tests for Artifact Store retention policy.

Tests retention period management and cleanup functionality.
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from necrocode.artifact_store.retention_policy import RetentionPolicy
from necrocode.artifact_store.config import ArtifactStoreConfig, RetentionPolicyConfig
from necrocode.artifact_store.models import ArtifactMetadata, ArtifactType


@pytest.fixture
def default_retention_policy():
    """Create a RetentionPolicy with default settings."""
    return RetentionPolicy()


@pytest.fixture
def custom_retention_policy():
    """Create a RetentionPolicy with custom settings."""
    config = RetentionPolicyConfig(
        diff_days=10,
        log_days=5,
        test_days=7,
    )
    return RetentionPolicy(retention_config=config)


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


def test_retention_policy_initialization_default():
    """Test RetentionPolicy initialization with defaults (Requirement: 6.2)."""
    policy = RetentionPolicy()
    
    assert policy.get_retention_days(ArtifactType.DIFF) == 30
    assert policy.get_retention_days(ArtifactType.LOG) == 7
    assert policy.get_retention_days(ArtifactType.TEST_RESULT) == 14


def test_retention_policy_initialization_custom():
    """Test RetentionPolicy initialization with custom config (Requirement: 6.1)."""
    config = RetentionPolicyConfig(
        diff_days=60,
        log_days=14,
        test_days=30,
    )
    policy = RetentionPolicy(retention_config=config)
    
    assert policy.get_retention_days(ArtifactType.DIFF) == 60
    assert policy.get_retention_days(ArtifactType.LOG) == 14
    assert policy.get_retention_days(ArtifactType.TEST_RESULT) == 30


def test_retention_policy_from_artifact_store_config():
    """Test RetentionPolicy initialization from ArtifactStoreConfig."""
    store_config = ArtifactStoreConfig(
        base_path="/tmp/artifacts",
        retention_policy=RetentionPolicyConfig(
            diff_days=45,
            log_days=10,
            test_days=20,
        )
    )
    policy = RetentionPolicy(config=store_config)
    
    assert policy.get_retention_days(ArtifactType.DIFF) == 45
    assert policy.get_retention_days(ArtifactType.LOG) == 10
    assert policy.get_retention_days(ArtifactType.TEST_RESULT) == 20


def test_get_retention_days(default_retention_policy):
    """Test getting retention days for artifact types."""
    assert default_retention_policy.get_retention_days(ArtifactType.DIFF) == 30
    assert default_retention_policy.get_retention_days(ArtifactType.LOG) == 7
    assert default_retention_policy.get_retention_days(ArtifactType.TEST_RESULT) == 14


def test_set_retention_days(default_retention_policy):
    """Test setting retention days for artifact types (Requirement: 6.1)."""
    # Set new retention days
    default_retention_policy.set_retention_days(ArtifactType.DIFF, 60)
    default_retention_policy.set_retention_days(ArtifactType.LOG, 14)
    
    # Verify updated
    assert default_retention_policy.get_retention_days(ArtifactType.DIFF) == 60
    assert default_retention_policy.get_retention_days(ArtifactType.LOG) == 14


def test_set_retention_days_negative():
    """Test that setting negative retention days raises error."""
    policy = RetentionPolicy()
    
    with pytest.raises(ValueError, match="Retention days must be non-negative"):
        policy.set_retention_days(ArtifactType.DIFF, -1)


def test_is_expired_not_expired(default_retention_policy, sample_metadata):
    """Test that recent artifact is not expired."""
    # Artifact created now, should not be expired
    assert default_retention_policy.is_expired(sample_metadata) is False


def test_is_expired_expired(default_retention_policy):
    """Test that old artifact is expired (Requirement: 6.3)."""
    # Create artifact from 40 days ago (DIFF retention is 30 days)
    old_metadata = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now() - timedelta(days=40),
    )
    
    assert default_retention_policy.is_expired(old_metadata) is True


def test_is_expired_with_reference_time(default_retention_policy, sample_metadata):
    """Test is_expired with custom reference time."""
    # Use future reference time
    future_time = datetime.now() + timedelta(days=40)
    
    # Artifact should be expired relative to future time
    assert default_retention_policy.is_expired(sample_metadata, future_time) is True


def test_get_expiration_date(default_retention_policy, sample_metadata):
    """Test getting expiration date."""
    expiration_date = default_retention_policy.get_expiration_date(sample_metadata)
    
    # Should be 30 days after creation (DIFF retention)
    expected_date = sample_metadata.created_at + timedelta(days=30)
    
    assert expiration_date == expected_date


def test_get_days_until_expiration(default_retention_policy):
    """Test getting days until expiration."""
    # Create artifact from 20 days ago (DIFF retention is 30 days)
    metadata = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now() - timedelta(days=20),
    )
    
    days_until = default_retention_policy.get_days_until_expiration(metadata)
    
    # Should have ~10 days remaining
    assert 9 <= days_until <= 10


def test_get_days_until_expiration_expired(default_retention_policy):
    """Test getting days until expiration for expired artifact."""
    # Create artifact from 40 days ago (DIFF retention is 30 days)
    metadata = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc123",
        created_at=datetime.now() - timedelta(days=40),
    )
    
    days_until = default_retention_policy.get_days_until_expiration(metadata)
    
    # Should be negative (expired 10 days ago)
    assert days_until < 0


def test_find_expired(default_retention_policy):
    """Test finding expired artifacts (Requirement: 6.3)."""
    now = datetime.now()
    
    # Create mix of expired and non-expired artifacts
    artifacts = [
        # Expired DIFF (40 days old, retention 30)
        ArtifactMetadata(
            uri="file://test-spec/1.1/diff.txt",
            task_id="1.1",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc1",
            created_at=now - timedelta(days=40),
        ),
        # Not expired DIFF (20 days old, retention 30)
        ArtifactMetadata(
            uri="file://test-spec/1.2/diff.txt",
            task_id="1.2",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc2",
            created_at=now - timedelta(days=20),
        ),
        # Expired LOG (10 days old, retention 7)
        ArtifactMetadata(
            uri="file://test-spec/1.3/log.txt",
            task_id="1.3",
            spec_name="test-spec",
            type=ArtifactType.LOG,
            size=512,
            checksum="abc3",
            created_at=now - timedelta(days=10),
        ),
    ]
    
    expired = default_retention_policy.find_expired(artifacts)
    
    assert len(expired) == 2
    assert expired[0].task_id == "1.1"
    assert expired[1].task_id == "1.3"


def test_find_expired_with_reference_time(default_retention_policy):
    """Test finding expired artifacts with custom reference time."""
    now = datetime.now()
    
    artifacts = [
        ArtifactMetadata(
            uri="file://test-spec/1.1/diff.txt",
            task_id="1.1",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc1",
            created_at=now - timedelta(days=20),
        ),
    ]
    
    # Use future reference time (40 days from now)
    future_time = now + timedelta(days=40)
    
    expired = default_retention_policy.find_expired(artifacts, future_time)
    
    # Should be expired relative to future time
    assert len(expired) == 1


def test_find_expiring_soon(default_retention_policy):
    """Test finding artifacts expiring soon."""
    now = datetime.now()
    
    artifacts = [
        # Expires in 5 days (created 25 days ago, retention 30)
        ArtifactMetadata(
            uri="file://test-spec/1.1/diff.txt",
            task_id="1.1",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc1",
            created_at=now - timedelta(days=25),
        ),
        # Expires in 20 days (created 10 days ago, retention 30)
        ArtifactMetadata(
            uri="file://test-spec/1.2/diff.txt",
            task_id="1.2",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc2",
            created_at=now - timedelta(days=10),
        ),
        # Already expired
        ArtifactMetadata(
            uri="file://test-spec/1.3/diff.txt",
            task_id="1.3",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc3",
            created_at=now - timedelta(days=40),
        ),
    ]
    
    # Find artifacts expiring within 7 days
    expiring_soon = default_retention_policy.find_expiring_soon(artifacts, days_threshold=7)
    
    # Only the first one should be expiring soon
    assert len(expiring_soon) == 1
    assert expiring_soon[0].task_id == "1.1"


def test_cleanup_expired_dry_run(default_retention_policy):
    """Test cleanup in dry run mode (Requirement: 6.4)."""
    # Create mock artifact store
    mock_store = Mock()
    
    now = datetime.now()
    expired_artifact = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc1",
        created_at=now - timedelta(days=40),
    )
    
    mock_store.get_all_artifacts.return_value = [expired_artifact]
    
    # Run cleanup in dry run mode
    result = default_retention_policy.cleanup_expired(mock_store, dry_run=True)
    
    # Should report what would be deleted
    assert result["expired_count"] == 1
    assert result["deleted_count"] == 1
    assert result["dry_run"] is True
    
    # Should not actually delete
    mock_store.delete.assert_not_called()


def test_cleanup_expired_actual(default_retention_policy):
    """Test actual cleanup (Requirement: 6.4, 6.5)."""
    # Create mock artifact store
    mock_store = Mock()
    
    now = datetime.now()
    expired_artifact = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc1",
        created_at=now - timedelta(days=40),
    )
    
    mock_store.get_all_artifacts.return_value = [expired_artifact]
    
    # Run actual cleanup
    result = default_retention_policy.cleanup_expired(mock_store, dry_run=False)
    
    # Should delete
    assert result["expired_count"] == 1
    assert result["deleted_count"] == 1
    assert result["dry_run"] is False
    assert result["freed_bytes"] == 1024
    
    # Should actually call delete
    mock_store.delete.assert_called_once_with(expired_artifact.uri)


def test_cleanup_expired_with_failures(default_retention_policy):
    """Test cleanup with deletion failures."""
    # Create mock artifact store
    mock_store = Mock()
    
    now = datetime.now()
    expired_artifacts = [
        ArtifactMetadata(
            uri=f"file://test-spec/1.{i}/diff.txt",
            task_id=f"1.{i}",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum=f"abc{i}",
            created_at=now - timedelta(days=40),
        )
        for i in range(3)
    ]
    
    mock_store.get_all_artifacts.return_value = expired_artifacts
    
    # Make second deletion fail
    def delete_side_effect(uri):
        if "1.1" in uri:
            raise Exception("Delete failed")
    
    mock_store.delete.side_effect = delete_side_effect
    
    # Run cleanup
    result = default_retention_policy.cleanup_expired(mock_store, dry_run=False)
    
    # Should report failure
    assert result["expired_count"] == 3
    assert result["deleted_count"] == 2
    assert result["failed_count"] == 1
    assert len(result["errors"]) == 1


def test_cleanup_expired_no_expired_artifacts(default_retention_policy):
    """Test cleanup when no artifacts are expired."""
    # Create mock artifact store
    mock_store = Mock()
    
    # All artifacts are recent
    recent_artifact = ArtifactMetadata(
        uri="file://test-spec/1.1/diff.txt",
        task_id="1.1",
        spec_name="test-spec",
        type=ArtifactType.DIFF,
        size=1024,
        checksum="abc1",
        created_at=datetime.now(),
    )
    
    mock_store.get_all_artifacts.return_value = [recent_artifact]
    
    # Run cleanup
    result = default_retention_policy.cleanup_expired(mock_store, dry_run=False)
    
    # Should not delete anything
    assert result["expired_count"] == 0
    assert result["deleted_count"] == 0
    mock_store.delete.assert_not_called()


def test_cleanup_expired_calculates_freed_space(default_retention_policy):
    """Test that cleanup calculates freed space correctly."""
    # Create mock artifact store
    mock_store = Mock()
    
    now = datetime.now()
    expired_artifacts = [
        ArtifactMetadata(
            uri=f"file://test-spec/1.{i}/diff.txt",
            task_id=f"1.{i}",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024 * (i + 1),  # Different sizes
            checksum=f"abc{i}",
            created_at=now - timedelta(days=40),
        )
        for i in range(3)
    ]
    
    mock_store.get_all_artifacts.return_value = expired_artifacts
    
    # Run cleanup
    result = default_retention_policy.cleanup_expired(mock_store, dry_run=False)
    
    # Should calculate total freed space
    expected_freed = 1024 + 2048 + 3072  # Sum of sizes
    assert result["freed_bytes"] == expected_freed
    assert result["freed_mb"] == round(expected_freed / (1024 * 1024), 2)


def test_retention_policy_different_types(default_retention_policy):
    """Test retention policy for different artifact types."""
    now = datetime.now()
    
    # Create artifacts of different types with same age
    artifacts = [
        ArtifactMetadata(
            uri="file://test-spec/1.1/diff.txt",
            task_id="1.1",
            spec_name="test-spec",
            type=ArtifactType.DIFF,
            size=1024,
            checksum="abc1",
            created_at=now - timedelta(days=20),
        ),
        ArtifactMetadata(
            uri="file://test-spec/1.2/log.txt",
            task_id="1.2",
            spec_name="test-spec",
            type=ArtifactType.LOG,
            size=512,
            checksum="abc2",
            created_at=now - timedelta(days=20),
        ),
        ArtifactMetadata(
            uri="file://test-spec/1.3/test.json",
            task_id="1.3",
            spec_name="test-spec",
            type=ArtifactType.TEST_RESULT,
            size=256,
            checksum="abc3",
            created_at=now - timedelta(days=20),
        ),
    ]
    
    # Find expired (LOG retention is 7 days, so it should be expired)
    expired = default_retention_policy.find_expired(artifacts)
    
    # Only LOG should be expired (20 days > 7 days retention)
    assert len(expired) == 1
    assert expired[0].type == ArtifactType.LOG

"""
Unit tests for Artifact Store storage backends.

Tests FilesystemBackend, S3Backend, and GCSBackend implementations.
Requirements: 7.1, 7.2, 7.3, 7.4
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from necrocode.artifact_store.storage_backend import (
    StorageBackend,
    FilesystemBackend,
    S3Backend,
    GCSBackend,
)
from necrocode.artifact_store.exceptions import (
    StorageError,
    ArtifactNotFoundError,
)


# ============================================================================
# FilesystemBackend Tests (Requirements: 7.1, 7.2)
# ============================================================================

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def filesystem_backend(temp_storage_dir):
    """Create a FilesystemBackend instance."""
    return FilesystemBackend(base_path=temp_storage_dir)


def test_filesystem_backend_initialization(temp_storage_dir):
    """Test FilesystemBackend initialization."""
    backend = FilesystemBackend(base_path=temp_storage_dir)
    assert backend.base_path == temp_storage_dir
    assert temp_storage_dir.exists()


def test_filesystem_backend_upload(filesystem_backend):
    """Test uploading to filesystem backend."""
    uri = "file://test-spec/1.1/diff.txt"
    content = b"Test content"
    
    filesystem_backend.upload(uri, content)
    
    # Verify file exists
    assert filesystem_backend.exists(uri)


def test_filesystem_backend_download(filesystem_backend):
    """Test downloading from filesystem backend."""
    uri = "file://test-spec/1.1/diff.txt"
    content = b"Test content"
    
    # Upload first
    filesystem_backend.upload(uri, content)
    
    # Download
    downloaded = filesystem_backend.download(uri)
    assert downloaded == content


def test_filesystem_backend_delete(filesystem_backend):
    """Test deleting from filesystem backend."""
    uri = "file://test-spec/1.1/diff.txt"
    content = b"Test content"
    
    # Upload first
    filesystem_backend.upload(uri, content)
    assert filesystem_backend.exists(uri)
    
    # Delete
    filesystem_backend.delete(uri)
    assert not filesystem_backend.exists(uri)


def test_filesystem_backend_exists(filesystem_backend):
    """Test checking existence in filesystem backend."""
    uri = "file://test-spec/1.1/diff.txt"
    
    # Should not exist initially
    assert not filesystem_backend.exists(uri)
    
    # Upload
    filesystem_backend.upload(uri, b"Test content")
    
    # Should exist now
    assert filesystem_backend.exists(uri)


def test_filesystem_backend_get_size(filesystem_backend):
    """Test getting size from filesystem backend."""
    uri = "file://test-spec/1.1/diff.txt"
    content = b"Test content with known size"
    
    # Upload
    filesystem_backend.upload(uri, content)
    
    # Get size
    size = filesystem_backend.get_size(uri)
    assert size == len(content)


def test_filesystem_backend_download_not_found(filesystem_backend):
    """Test downloading non-existent file raises error."""
    uri = "file://non-existent/file.txt"
    
    with pytest.raises(ArtifactNotFoundError):
        filesystem_backend.download(uri)


def test_filesystem_backend_delete_not_found(filesystem_backend):
    """Test deleting non-existent file raises error."""
    uri = "file://non-existent/file.txt"
    
    with pytest.raises(ArtifactNotFoundError):
        filesystem_backend.delete(uri)


def test_filesystem_backend_get_size_not_found(filesystem_backend):
    """Test getting size of non-existent file raises error."""
    uri = "file://non-existent/file.txt"
    
    with pytest.raises(ArtifactNotFoundError):
        filesystem_backend.get_size(uri)


def test_filesystem_backend_creates_directories(filesystem_backend):
    """Test that filesystem backend creates necessary directories."""
    uri = "file://deep/nested/path/file.txt"
    content = b"Test content"
    
    # Upload should create directories
    filesystem_backend.upload(uri, content)
    
    # Verify file exists
    assert filesystem_backend.exists(uri)
    
    # Verify content
    downloaded = filesystem_backend.download(uri)
    assert downloaded == content


def test_filesystem_backend_overwrite(filesystem_backend):
    """Test overwriting existing file."""
    uri = "file://test-spec/1.1/diff.txt"
    content1 = b"First content"
    content2 = b"Second content"
    
    # Upload first version
    filesystem_backend.upload(uri, content1)
    assert filesystem_backend.download(uri) == content1
    
    # Overwrite
    filesystem_backend.upload(uri, content2)
    assert filesystem_backend.download(uri) == content2


# ============================================================================
# S3Backend Tests (Requirements: 7.1, 7.3)
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    return Mock()


@pytest.fixture
def s3_backend(mock_s3_client):
    """Create an S3Backend instance with mocked client."""
    with patch('necrocode.artifact_store.storage_backend.boto3') as mock_boto3:
        mock_boto3.client.return_value = mock_s3_client
        backend = S3Backend(
            bucket_name="test-bucket",
            region="us-east-1",
        )
        backend.s3_client = mock_s3_client
        return backend


def test_s3_backend_initialization():
    """Test S3Backend initialization."""
    with patch('necrocode.artifact_store.storage_backend.boto3') as mock_boto3:
        backend = S3Backend(
            bucket_name="test-bucket",
            region="us-west-2",
        )
        
        mock_boto3.client.assert_called_once_with(
            's3',
            region_name='us-west-2'
        )
        assert backend.bucket_name == "test-bucket"


def test_s3_backend_upload(s3_backend, mock_s3_client):
    """Test uploading to S3 backend."""
    uri = "s3://test-bucket/test-spec/1.1/diff.txt"
    content = b"Test content"
    
    s3_backend.upload(uri, content)
    
    # Verify S3 put_object was called
    mock_s3_client.put_object.assert_called_once()
    call_args = mock_s3_client.put_object.call_args
    assert call_args[1]['Bucket'] == 'test-bucket'
    assert call_args[1]['Body'] == content


def test_s3_backend_download(s3_backend, mock_s3_client):
    """Test downloading from S3 backend."""
    uri = "s3://test-bucket/test-spec/1.1/diff.txt"
    content = b"Test content"
    
    # Mock S3 response
    mock_response = {'Body': Mock()}
    mock_response['Body'].read.return_value = content
    mock_s3_client.get_object.return_value = mock_response
    
    # Download
    downloaded = s3_backend.download(uri)
    
    assert downloaded == content
    mock_s3_client.get_object.assert_called_once()


def test_s3_backend_delete(s3_backend, mock_s3_client):
    """Test deleting from S3 backend."""
    uri = "s3://test-bucket/test-spec/1.1/diff.txt"
    
    s3_backend.delete(uri)
    
    # Verify S3 delete_object was called
    mock_s3_client.delete_object.assert_called_once()


def test_s3_backend_exists(s3_backend, mock_s3_client):
    """Test checking existence in S3 backend."""
    uri = "s3://test-bucket/test-spec/1.1/diff.txt"
    
    # Mock head_object to return successfully
    mock_s3_client.head_object.return_value = {}
    
    assert s3_backend.exists(uri) is True
    mock_s3_client.head_object.assert_called_once()


def test_s3_backend_exists_not_found(s3_backend, mock_s3_client):
    """Test checking existence of non-existent file in S3."""
    uri = "s3://test-bucket/non-existent.txt"
    
    # Mock head_object to raise ClientError
    from botocore.exceptions import ClientError
    mock_s3_client.head_object.side_effect = ClientError(
        {'Error': {'Code': '404'}},
        'HeadObject'
    )
    
    assert s3_backend.exists(uri) is False


def test_s3_backend_get_size(s3_backend, mock_s3_client):
    """Test getting size from S3 backend."""
    uri = "s3://test-bucket/test-spec/1.1/diff.txt"
    
    # Mock head_object response
    mock_s3_client.head_object.return_value = {
        'ContentLength': 1024
    }
    
    size = s3_backend.get_size(uri)
    
    assert size == 1024
    mock_s3_client.head_object.assert_called_once()


# ============================================================================
# GCSBackend Tests (Requirements: 7.1, 7.4)
# ============================================================================

@pytest.fixture
def mock_gcs_client():
    """Create a mock GCS client."""
    return Mock()


@pytest.fixture
def mock_gcs_bucket():
    """Create a mock GCS bucket."""
    return Mock()


@pytest.fixture
def gcs_backend(mock_gcs_client, mock_gcs_bucket):
    """Create a GCSBackend instance with mocked client."""
    with patch('necrocode.artifact_store.storage_backend.storage') as mock_storage:
        mock_storage.Client.return_value = mock_gcs_client
        mock_gcs_client.bucket.return_value = mock_gcs_bucket
        
        backend = GCSBackend(bucket_name="test-bucket")
        backend.client = mock_gcs_client
        backend.bucket = mock_gcs_bucket
        return backend


def test_gcs_backend_initialization():
    """Test GCSBackend initialization."""
    with patch('necrocode.artifact_store.storage_backend.storage') as mock_storage:
        mock_client = Mock()
        mock_storage.Client.return_value = mock_client
        
        backend = GCSBackend(bucket_name="test-bucket")
        
        mock_storage.Client.assert_called_once()
        mock_client.bucket.assert_called_once_with("test-bucket")


def test_gcs_backend_upload(gcs_backend, mock_gcs_bucket):
    """Test uploading to GCS backend."""
    uri = "gs://test-bucket/test-spec/1.1/diff.txt"
    content = b"Test content"
    
    mock_blob = Mock()
    mock_gcs_bucket.blob.return_value = mock_blob
    
    gcs_backend.upload(uri, content)
    
    # Verify blob upload was called
    mock_gcs_bucket.blob.assert_called_once()
    mock_blob.upload_from_string.assert_called_once_with(content)


def test_gcs_backend_download(gcs_backend, mock_gcs_bucket):
    """Test downloading from GCS backend."""
    uri = "gs://test-bucket/test-spec/1.1/diff.txt"
    content = b"Test content"
    
    mock_blob = Mock()
    mock_blob.download_as_bytes.return_value = content
    mock_gcs_bucket.blob.return_value = mock_blob
    
    downloaded = gcs_backend.download(uri)
    
    assert downloaded == content
    mock_blob.download_as_bytes.assert_called_once()


def test_gcs_backend_delete(gcs_backend, mock_gcs_bucket):
    """Test deleting from GCS backend."""
    uri = "gs://test-bucket/test-spec/1.1/diff.txt"
    
    mock_blob = Mock()
    mock_gcs_bucket.blob.return_value = mock_blob
    
    gcs_backend.delete(uri)
    
    # Verify blob delete was called
    mock_blob.delete.assert_called_once()


def test_gcs_backend_exists(gcs_backend, mock_gcs_bucket):
    """Test checking existence in GCS backend."""
    uri = "gs://test-bucket/test-spec/1.1/diff.txt"
    
    mock_blob = Mock()
    mock_blob.exists.return_value = True
    mock_gcs_bucket.blob.return_value = mock_blob
    
    assert gcs_backend.exists(uri) is True
    mock_blob.exists.assert_called_once()


def test_gcs_backend_get_size(gcs_backend, mock_gcs_bucket):
    """Test getting size from GCS backend."""
    uri = "gs://test-bucket/test-spec/1.1/diff.txt"
    
    mock_blob = Mock()
    mock_blob.size = 2048
    mock_gcs_bucket.blob.return_value = mock_blob
    
    # Mock reload to populate size
    mock_blob.reload.return_value = None
    
    size = gcs_backend.get_size(uri)
    
    assert size == 2048
    mock_blob.reload.assert_called_once()


def test_storage_backend_is_abstract():
    """Test that StorageBackend cannot be instantiated directly."""
    with pytest.raises(TypeError):
        StorageBackend()

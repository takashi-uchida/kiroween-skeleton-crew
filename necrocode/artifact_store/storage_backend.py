"""
Storage backend abstraction for Artifact Store.

This module defines the abstract interface for storage backends and provides
concrete implementations for filesystem, S3, and GCS storage.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

from necrocode.artifact_store.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract interface for storage backends.
    
    All storage backends must implement these methods to provide
    consistent upload, download, delete, and query operations.
    """
    
    @abstractmethod
    def upload(self, uri: str, content: bytes) -> None:
        """Upload artifact content to storage.
        
        Args:
            uri: Unique identifier for the artifact
            content: Binary content to upload
            
        Raises:
            StorageError: If upload fails
        """
        pass
    
    @abstractmethod
    def download(self, uri: str) -> bytes:
        """Download artifact content from storage.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Binary content of the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If download fails
        """
        pass
    
    @abstractmethod
    def delete(self, uri: str) -> None:
        """Delete artifact from storage.
        
        Args:
            uri: Unique identifier for the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If deletion fails
        """
        pass
    
    @abstractmethod
    def exists(self, uri: str) -> bool:
        """Check if artifact exists in storage.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            True if artifact exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_size(self, uri: str) -> int:
        """Get the size of an artifact in bytes.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Size in bytes
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
        """
        pass


class FilesystemBackend(StorageBackend):
    """Filesystem-based storage backend.
    
    Stores artifacts in a local directory structure organized by spec name and task ID.
    """
    
    def __init__(self, base_path: Path):
        """Initialize filesystem backend.
        
        Args:
            base_path: Root directory for artifact storage
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized FilesystemBackend at {self.base_path}")
    
    def _uri_to_path(self, uri: str) -> Path:
        """Convert URI to filesystem path.
        
        Args:
            uri: Artifact URI (e.g., "file://~/.necrocode/artifacts/chat-app/1.1/diff.txt")
            
        Returns:
            Absolute filesystem path
        """
        # Remove file:// prefix if present
        if uri.startswith("file://"):
            uri = uri[7:]
        
        # Expand user home directory
        path = Path(uri).expanduser()
        
        # If path is relative, make it relative to base_path
        if not path.is_absolute():
            path = self.base_path / path
        
        return path
    
    def upload(self, uri: str, content: bytes) -> None:
        """Upload artifact to filesystem.
        
        Args:
            uri: Unique identifier for the artifact
            content: Binary content to upload
            
        Raises:
            StorageError: If upload fails
            StorageFullError: If storage capacity is exceeded
            PermissionError: If permission is denied
            
        Requirements: 15.2, 15.3
        """
        from necrocode.artifact_store.exceptions import StorageError
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        try:
            path = self._uri_to_path(uri)
            
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            path.write_bytes(content)
            logger.debug(f"Uploaded artifact to {path} ({len(content)} bytes)")
            
        except Exception as e:
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "upload", uri)
    
    def download(self, uri: str) -> bytes:
        """Download artifact from filesystem.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Binary content of the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If download fails
            PermissionError: If permission is denied
            
        Requirements: 15.2, 15.3
        """
        from necrocode.artifact_store.exceptions import ArtifactNotFoundError, StorageError
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        try:
            path = self._uri_to_path(uri)
            
            if not path.exists():
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            content = path.read_bytes()
            logger.debug(f"Downloaded artifact from {path} ({len(content)} bytes)")
            return content
            
        except ArtifactNotFoundError:
            raise
        except Exception as e:
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "download", uri)
    
    def delete(self, uri: str) -> None:
        """Delete artifact from filesystem.
        
        Args:
            uri: Unique identifier for the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If deletion fails
            PermissionError: If permission is denied
            
        Requirements: 15.2, 15.3
        """
        from necrocode.artifact_store.exceptions import ArtifactNotFoundError, StorageError
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        try:
            path = self._uri_to_path(uri)
            
            if not path.exists():
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            path.unlink()
            logger.debug(f"Deleted artifact at {path}")
            
            # Clean up empty parent directories
            try:
                parent = path.parent
                while parent != self.base_path and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
            except Exception:
                pass  # Ignore cleanup errors
                
        except ArtifactNotFoundError:
            raise
        except Exception as e:
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "delete", uri)
    
    def exists(self, uri: str) -> bool:
        """Check if artifact exists in filesystem.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            True if artifact exists, False otherwise
        """
        try:
            path = self._uri_to_path(uri)
            return path.exists() and path.is_file()
        except Exception:
            return False
    
    def get_size(self, uri: str) -> int:
        """Get the size of an artifact in bytes.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Size in bytes
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
        """
        from necrocode.artifact_store.exceptions import ArtifactNotFoundError
        
        try:
            path = self._uri_to_path(uri)
            
            if not path.exists():
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            return path.stat().st_size
            
        except ArtifactNotFoundError:
            raise
        except Exception as e:
            from necrocode.artifact_store.exceptions import StorageError
            raise StorageError(f"Failed to get size of artifact at {uri}: {e}")



class S3Backend(StorageBackend):
    """S3-compatible storage backend.
    
    Stores artifacts in an S3 bucket using boto3.
    """
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "",
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """Initialize S3 backend.
        
        Args:
            bucket_name: S3 bucket name
            prefix: Optional prefix for all keys
            region: AWS region (defaults to environment config)
            endpoint_url: Custom endpoint URL (for S3-compatible services)
            aws_access_key_id: AWS access key (defaults to environment)
            aws_secret_access_key: AWS secret key (defaults to environment)
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("boto3 is required for S3Backend. Install with: pip install boto3")
        
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/")
        
        # Initialize S3 client
        session_kwargs = {}
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if region:
            session_kwargs["region_name"] = region
        
        client_kwargs = {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        
        self.s3_client = boto3.client("s3", **session_kwargs, **client_kwargs)
        self.ClientError = ClientError
        
        logger.info(f"Initialized S3Backend for bucket {bucket_name}")
    
    def _uri_to_key(self, uri: str) -> str:
        """Convert URI to S3 key.
        
        Args:
            uri: Artifact URI (e.g., "s3://bucket/chat-app/1.1/diff.txt" or "chat-app/1.1/diff.txt")
            
        Returns:
            S3 key with prefix applied
        """
        # Remove s3:// prefix and bucket name if present
        if uri.startswith("s3://"):
            parts = uri[5:].split("/", 1)
            key = parts[1] if len(parts) > 1 else ""
        else:
            key = uri
        
        # Apply prefix
        if self.prefix:
            key = f"{self.prefix}/{key}"
        
        return key
    
    def upload(self, uri: str, content: bytes) -> None:
        """Upload artifact to S3.
        
        Args:
            uri: Unique identifier for the artifact
            content: Binary content to upload
            
        Raises:
            StorageError: If upload fails
            StorageFullError: If storage capacity is exceeded
            PermissionError: If permission is denied
            
        Requirements: 15.1, 15.2, 15.3, 15.4
        """
        from necrocode.artifact_store.exceptions import (
            StorageError,
            ArtifactNotFoundError,
            StorageFullError,
            PermissionError as ArtifactPermissionError,
        )
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        # リトライ不可能な例外
        non_retryable = (ArtifactNotFoundError, StorageFullError, ArtifactPermissionError)
        
        @RetryHandler.with_retry(
            max_attempts=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            non_retryable_exceptions=non_retryable,
        )
        def _upload_with_retry():
            key = self._uri_to_key(uri)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content
            )
            logger.debug(f"Uploaded artifact to s3://{self.bucket_name}/{key} ({len(content)} bytes)")
        
        try:
            _upload_with_retry()
        except (StorageFullError, ArtifactPermissionError):
            # これらのエラーはそのまま再送出
            raise
        except Exception as e:
            logger.error(f"Failed to upload artifact to S3 {uri} after retries: {e}")
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "upload", uri)
    
    def download(self, uri: str) -> bytes:
        """Download artifact from S3.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Binary content of the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If download fails
            PermissionError: If permission is denied
            
        Requirements: 15.1, 15.2, 15.3, 15.4
        """
        from necrocode.artifact_store.exceptions import (
            ArtifactNotFoundError,
            StorageError,
            PermissionError as ArtifactPermissionError,
        )
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        # リトライ不可能な例外
        non_retryable = (ArtifactNotFoundError, ArtifactPermissionError)
        
        @RetryHandler.with_retry(
            max_attempts=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            non_retryable_exceptions=non_retryable,
        )
        def _download_with_retry():
            key = self._uri_to_key(uri)
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                content = response["Body"].read()
                logger.debug(f"Downloaded artifact from s3://{self.bucket_name}/{key} ({len(content)} bytes)")
                return content
            except self.ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise ArtifactNotFoundError(f"Artifact not found: {uri}")
                raise
        
        try:
            return _download_with_retry()
        except (ArtifactNotFoundError, ArtifactPermissionError):
            raise
        except Exception as e:
            logger.error(f"Failed to download artifact from S3 {uri} after retries: {e}")
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "download", uri)
    
    def delete(self, uri: str) -> None:
        """Delete artifact from S3.
        
        Args:
            uri: Unique identifier for the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If deletion fails
            PermissionError: If permission is denied
            
        Requirements: 15.1, 15.2, 15.3, 15.4
        """
        from necrocode.artifact_store.exceptions import (
            ArtifactNotFoundError,
            StorageError,
            PermissionError as ArtifactPermissionError,
        )
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        # リトライ不可能な例外
        non_retryable = (ArtifactNotFoundError, ArtifactPermissionError)
        
        @RetryHandler.with_retry(
            max_attempts=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            non_retryable_exceptions=non_retryable,
        )
        def _delete_with_retry():
            key = self._uri_to_key(uri)
            
            # Check if object exists first
            if not self.exists(uri):
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.debug(f"Deleted artifact at s3://{self.bucket_name}/{key}")
        
        try:
            _delete_with_retry()
        except (ArtifactNotFoundError, ArtifactPermissionError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete artifact from S3 {uri} after retries: {e}")
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "delete", uri)
    
    def exists(self, uri: str) -> bool:
        """Check if artifact exists in S3.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            True if artifact exists, False otherwise
        """
        try:
            key = self._uri_to_key(uri)
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except self.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise
        except Exception:
            return False
    
    def get_size(self, uri: str) -> int:
        """Get the size of an artifact in bytes.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Size in bytes
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
        """
        from necrocode.artifact_store.exceptions import ArtifactNotFoundError, StorageError
        
        try:
            key = self._uri_to_key(uri)
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response["ContentLength"]
            
        except self.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            raise StorageError(f"Failed to get size of artifact from S3 {uri}: {e}")
        except Exception as e:
            raise StorageError(f"Failed to get size of artifact from S3 {uri}: {e}")



class GCSBackend(StorageBackend):
    """Google Cloud Storage backend.
    
    Stores artifacts in a GCS bucket using google-cloud-storage.
    """
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "",
        project: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """Initialize GCS backend.
        
        Args:
            bucket_name: GCS bucket name
            prefix: Optional prefix for all blob names
            project: GCP project ID (defaults to environment config)
            credentials_path: Path to service account JSON file (defaults to environment)
        """
        try:
            from google.cloud import storage
            from google.cloud.exceptions import NotFound
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for GCSBackend. "
                "Install with: pip install google-cloud-storage"
            )
        
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/")
        
        # Initialize GCS client
        client_kwargs = {}
        if project:
            client_kwargs["project"] = project
        if credentials_path:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            client_kwargs["credentials"] = credentials
        
        self.storage_client = storage.Client(**client_kwargs)
        self.bucket = self.storage_client.bucket(bucket_name)
        self.NotFound = NotFound
        
        logger.info(f"Initialized GCSBackend for bucket {bucket_name}")
    
    def _uri_to_blob_name(self, uri: str) -> str:
        """Convert URI to GCS blob name.
        
        Args:
            uri: Artifact URI (e.g., "gs://bucket/chat-app/1.1/diff.txt" or "chat-app/1.1/diff.txt")
            
        Returns:
            Blob name with prefix applied
        """
        # Remove gs:// prefix and bucket name if present
        if uri.startswith("gs://"):
            parts = uri[5:].split("/", 1)
            blob_name = parts[1] if len(parts) > 1 else ""
        else:
            blob_name = uri
        
        # Apply prefix
        if self.prefix:
            blob_name = f"{self.prefix}/{blob_name}"
        
        return blob_name
    
    def upload(self, uri: str, content: bytes) -> None:
        """Upload artifact to GCS.
        
        Args:
            uri: Unique identifier for the artifact
            content: Binary content to upload
            
        Raises:
            StorageError: If upload fails
            StorageFullError: If storage capacity is exceeded
            PermissionError: If permission is denied
            
        Requirements: 15.1, 15.2, 15.3, 15.4
        """
        from necrocode.artifact_store.exceptions import (
            StorageError,
            ArtifactNotFoundError,
            StorageFullError,
            PermissionError as ArtifactPermissionError,
        )
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        # リトライ不可能な例外
        non_retryable = (ArtifactNotFoundError, StorageFullError, ArtifactPermissionError)
        
        @RetryHandler.with_retry(
            max_attempts=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            non_retryable_exceptions=non_retryable,
        )
        def _upload_with_retry():
            blob_name = self._uri_to_blob_name(uri)
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(content)
            logger.debug(f"Uploaded artifact to gs://{self.bucket_name}/{blob_name} ({len(content)} bytes)")
        
        try:
            _upload_with_retry()
        except (StorageFullError, ArtifactPermissionError):
            # これらのエラーはそのまま再送出
            raise
        except Exception as e:
            logger.error(f"Failed to upload artifact to GCS {uri} after retries: {e}")
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "upload", uri)
    
    def download(self, uri: str) -> bytes:
        """Download artifact from GCS.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Binary content of the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If download fails
            PermissionError: If permission is denied
            
        Requirements: 15.1, 15.2, 15.3, 15.4
        """
        from necrocode.artifact_store.exceptions import (
            ArtifactNotFoundError,
            StorageError,
            PermissionError as ArtifactPermissionError,
        )
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        # リトライ不可能な例外
        non_retryable = (ArtifactNotFoundError, ArtifactPermissionError)
        
        @RetryHandler.with_retry(
            max_attempts=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            non_retryable_exceptions=non_retryable,
        )
        def _download_with_retry():
            blob_name = self._uri_to_blob_name(uri)
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            content = blob.download_as_bytes()
            logger.debug(f"Downloaded artifact from gs://{self.bucket_name}/{blob_name} ({len(content)} bytes)")
            return content
        
        try:
            return _download_with_retry()
        except (ArtifactNotFoundError, ArtifactPermissionError):
            raise
        except self.NotFound:
            raise ArtifactNotFoundError(f"Artifact not found: {uri}")
        except Exception as e:
            logger.error(f"Failed to download artifact from GCS {uri} after retries: {e}")
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "download", uri)
    
    def delete(self, uri: str) -> None:
        """Delete artifact from GCS.
        
        Args:
            uri: Unique identifier for the artifact
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
            StorageError: If deletion fails
            PermissionError: If permission is denied
            
        Requirements: 15.1, 15.2, 15.3, 15.4
        """
        from necrocode.artifact_store.exceptions import (
            ArtifactNotFoundError,
            StorageError,
            PermissionError as ArtifactPermissionError,
        )
        from necrocode.artifact_store.error_detector import ErrorDetector
        
        # リトライ不可能な例外
        non_retryable = (ArtifactNotFoundError, ArtifactPermissionError)
        
        @RetryHandler.with_retry(
            max_attempts=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            non_retryable_exceptions=non_retryable,
        )
        def _delete_with_retry():
            blob_name = self._uri_to_blob_name(uri)
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            blob.delete()
            logger.debug(f"Deleted artifact at gs://{self.bucket_name}/{blob_name}")
        
        try:
            _delete_with_retry()
        except (ArtifactNotFoundError, ArtifactPermissionError):
            raise
        except self.NotFound:
            raise ArtifactNotFoundError(f"Artifact not found: {uri}")
        except Exception as e:
            logger.error(f"Failed to delete artifact from GCS {uri} after retries: {e}")
            # エラーを検出して適切な例外を投げる
            ErrorDetector.check_and_raise(e, "delete", uri)
    
    def exists(self, uri: str) -> bool:
        """Check if artifact exists in GCS.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            True if artifact exists, False otherwise
        """
        try:
            blob_name = self._uri_to_blob_name(uri)
            blob = self.bucket.blob(blob_name)
            return blob.exists()
        except Exception:
            return False
    
    def get_size(self, uri: str) -> int:
        """Get the size of an artifact in bytes.
        
        Args:
            uri: Unique identifier for the artifact
            
        Returns:
            Size in bytes
            
        Raises:
            ArtifactNotFoundError: If artifact does not exist
        """
        from necrocode.artifact_store.exceptions import ArtifactNotFoundError, StorageError
        
        try:
            blob_name = self._uri_to_blob_name(uri)
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                raise ArtifactNotFoundError(f"Artifact not found: {uri}")
            
            blob.reload()  # Fetch metadata
            return blob.size
            
        except ArtifactNotFoundError:
            raise
        except self.NotFound:
            raise ArtifactNotFoundError(f"Artifact not found: {uri}")
        except Exception as e:
            raise StorageError(f"Failed to get size of artifact from GCS {uri}: {e}")

"""
Artifact uploader for Agent Runner.

This module handles uploading task execution artifacts (diffs, logs, test results)
to the Artifact Store and recording artifact URIs in the Task Registry.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.exceptions import ArtifactUploadError
from necrocode.agent_runner.models import (
    Artifact,
    ArtifactType,
    ImplementationResult,
    TaskContext,
    TestResult,
)

# Import Task Registry for artifact recording
try:
    from necrocode.task_registry import TaskRegistry
    from necrocode.task_registry.models import ArtifactType as RegistryArtifactType
    TASK_REGISTRY_AVAILABLE = True
except ImportError:
    TASK_REGISTRY_AVAILABLE = False
    logger.warning("Task Registry not available - artifact recording will be skipped")

logger = logging.getLogger(__name__)


class ArtifactStoreClient:
    """
    Client for communicating with the Artifact Store.
    
    Handles uploading artifacts to various storage backends (filesystem, S3, GCS)
    based on the configured artifact_store_url.
    """
    
    def __init__(self, config: RunnerConfig):
        """
        Initialize the Artifact Store client.
        
        Args:
            config: Runner configuration containing artifact store settings
        """
        self.config = config
        self.base_url = config.artifact_store_url
        self._backend = self._initialize_backend()
        
        logger.info(f"Initialized ArtifactStoreClient with backend: {self.base_url}")
    
    def _initialize_backend(self) -> "StorageBackend":
        """
        Initialize the appropriate storage backend based on URL scheme.
        
        Returns:
            Storage backend instance
            
        Raises:
            ValueError: If URL scheme is not supported
        """
        parsed = urlparse(self.base_url)
        scheme = parsed.scheme
        
        if scheme == "file" or scheme == "":
            # Filesystem backend
            base_path = Path(parsed.path).expanduser()
            return FilesystemBackend(base_path)
        elif scheme == "s3":
            # S3 backend (future implementation)
            raise NotImplementedError("S3 backend not yet implemented")
        elif scheme == "gs":
            # GCS backend (future implementation)
            raise NotImplementedError("GCS backend not yet implemented")
        else:
            raise ValueError(f"Unsupported artifact store URL scheme: {scheme}")
    
    def upload(
        self,
        spec_name: str,
        task_id: str,
        artifact_type: ArtifactType,
        content: bytes,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Upload an artifact to the store.
        
        Args:
            spec_name: Name of the spec
            task_id: Task identifier
            artifact_type: Type of artifact (diff/log/test)
            content: Artifact content as bytes
            metadata: Optional additional metadata
            
        Returns:
            URI of the uploaded artifact
            
        Raises:
            ArtifactUploadError: If upload fails
        """
        try:
            # Generate URI
            uri = self._generate_uri(spec_name, task_id, artifact_type)
            
            # Calculate checksum
            checksum = self._calculate_checksum(content)
            
            # Upload to backend
            self._backend.upload(uri, content)
            
            # Save metadata
            artifact_metadata = {
                "uri": uri,
                "spec_name": spec_name,
                "task_id": task_id,
                "type": artifact_type.value,
                "size": len(content),
                "checksum": checksum,
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            self._backend.save_metadata(uri, artifact_metadata)
            
            logger.info(f"Uploaded artifact: {uri} ({len(content)} bytes)")
            return uri
            
        except Exception as e:
            error_msg = f"Failed to upload artifact {artifact_type.value} for task {task_id}: {e}"
            logger.error(error_msg)
            raise ArtifactUploadError(error_msg) from e
    
    def _generate_uri(self, spec_name: str, task_id: str, artifact_type: ArtifactType) -> str:
        """
        Generate a URI for an artifact.
        
        Args:
            spec_name: Name of the spec
            task_id: Task identifier
            artifact_type: Type of artifact
            
        Returns:
            Artifact URI
        """
        # Sanitize spec_name and task_id for filesystem safety
        safe_spec = spec_name.replace("/", "-").replace("\\", "-")
        safe_task = task_id.replace("/", "-").replace("\\", "-")
        
        # Determine file extension
        ext_map = {
            ArtifactType.DIFF: "diff",
            ArtifactType.LOG: "log",
            ArtifactType.TEST_RESULT: "json",
        }
        ext = ext_map.get(artifact_type, "txt")
        
        # Build URI path
        return f"{safe_spec}/{safe_task}/{artifact_type.value}.{ext}"
    
    def _calculate_checksum(self, content: bytes) -> str:
        """
        Calculate SHA256 checksum of content.
        
        Args:
            content: Content to checksum
            
        Returns:
            Hex-encoded SHA256 checksum
        """
        return hashlib.sha256(content).hexdigest()


class StorageBackend:
    """Abstract base class for storage backends."""
    
    def upload(self, uri: str, content: bytes) -> None:
        """Upload content to the given URI."""
        raise NotImplementedError
    
    def save_metadata(self, uri: str, metadata: Dict) -> None:
        """Save metadata for an artifact."""
        raise NotImplementedError


class FilesystemBackend(StorageBackend):
    """
    Filesystem-based storage backend.
    
    Stores artifacts in a local directory structure organized by
    spec name and task ID.
    """
    
    def __init__(self, base_path: Path):
        """
        Initialize filesystem backend.
        
        Args:
            base_path: Base directory for artifact storage
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized FilesystemBackend at {base_path}")
    
    def upload(self, uri: str, content: bytes) -> None:
        """
        Upload content to filesystem.
        
        Args:
            uri: Relative path for the artifact
            content: Content to write
            
        Raises:
            IOError: If write fails
        """
        file_path = self.base_path / uri
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_bytes(content)
        logger.debug(f"Wrote {len(content)} bytes to {file_path}")
    
    def save_metadata(self, uri: str, metadata: Dict) -> None:
        """
        Save metadata alongside the artifact.
        
        Args:
            uri: Artifact URI
            metadata: Metadata dictionary
            
        Raises:
            IOError: If write fails
        """
        file_path = self.base_path / uri
        metadata_path = file_path.parent / "metadata.json"
        
        # Load existing metadata if present
        existing_metadata = {}
        if metadata_path.exists():
            try:
                existing_metadata = json.loads(metadata_path.read_text())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse existing metadata at {metadata_path}")
        
        # Update with new artifact metadata
        artifact_key = file_path.name
        existing_metadata[artifact_key] = metadata
        
        # Write back
        metadata_path.write_text(json.dumps(existing_metadata, indent=2))
        logger.debug(f"Saved metadata to {metadata_path}")


class ArtifactUploader:
    """
    Manages uploading task execution artifacts to the Artifact Store.
    
    Handles uploading diffs, logs, and test results, and records
    artifact URIs in the Task Registry for later retrieval.
    """
    
    def __init__(self, config: Optional[RunnerConfig] = None, task_registry: Optional["TaskRegistry"] = None):
        """
        Initialize the artifact uploader.
        
        Args:
            config: Runner configuration. If None, uses default config.
            task_registry: Task Registry instance for recording artifacts. If None, will attempt to create one.
        """
        self.config = config or RunnerConfig()
        self.client = ArtifactStoreClient(self.config)
        
        # Initialize Task Registry if available
        self.task_registry = task_registry
        if self.task_registry is None and TASK_REGISTRY_AVAILABLE:
            try:
                registry_path = self.config.task_registry_path
                self.task_registry = TaskRegistry(registry_dir=registry_path)
                logger.info("Initialized Task Registry for artifact recording")
            except Exception as e:
                logger.warning(f"Failed to initialize Task Registry: {e}")
                self.task_registry = None
        
        logger.info("Initialized ArtifactUploader")
    
    def upload_artifacts(
        self,
        task_context: TaskContext,
        impl_result: Optional[ImplementationResult],
        test_result: Optional[TestResult],
        logs: str
    ) -> List[Artifact]:
        """
        Upload all artifacts for a task execution.
        
        Args:
            task_context: Task context information
            impl_result: Implementation result (may be None if implementation failed)
            test_result: Test result (may be None if tests not run)
            logs: Execution logs as string
            
        Returns:
            List of uploaded artifacts
            
        Note:
            Upload failures are logged as warnings but do not raise exceptions,
            allowing task execution to continue.
        """
        artifacts = []
        
        # Upload diff if available
        if impl_result and impl_result.diff:
            try:
                diff_artifact = self._upload_diff(task_context, impl_result.diff)
                artifacts.append(diff_artifact)
                self._record_artifact_in_registry(task_context, diff_artifact)
            except ArtifactUploadError as e:
                logger.warning(f"Failed to upload diff: {e}")
        
        # Upload logs
        try:
            log_artifact = self._upload_log(task_context, logs)
            artifacts.append(log_artifact)
            self._record_artifact_in_registry(task_context, log_artifact)
        except ArtifactUploadError as e:
            logger.warning(f"Failed to upload logs: {e}")
        
        # Upload test results if available
        if test_result:
            try:
                test_artifact = self._upload_test_result(task_context, test_result)
                artifacts.append(test_artifact)
                self._record_artifact_in_registry(task_context, test_artifact)
            except ArtifactUploadError as e:
                logger.warning(f"Failed to upload test results: {e}")
        
        logger.info(f"Uploaded {len(artifacts)} artifacts for task {task_context.task_id}")
        return artifacts
    
    def _upload_diff(self, task_context: TaskContext, diff: str) -> Artifact:
        """
        Upload implementation diff.
        
        Args:
            task_context: Task context
            diff: Diff content as string
            
        Returns:
            Artifact metadata
            
        Raises:
            ArtifactUploadError: If upload fails
        """
        content = diff.encode("utf-8")
        
        uri = self.client.upload(
            spec_name=task_context.spec_name,
            task_id=task_context.task_id,
            artifact_type=ArtifactType.DIFF,
            content=content,
            metadata={
                "title": task_context.title,
                "branch": task_context.branch_name,
            }
        )
        
        return Artifact(
            type=ArtifactType.DIFF,
            uri=uri,
            size_bytes=len(content),
            created_at=datetime.now()
        )
    
    def _upload_log(self, task_context: TaskContext, logs: str) -> Artifact:
        """
        Upload execution logs.
        
        Args:
            task_context: Task context
            logs: Log content as string
            
        Returns:
            Artifact metadata
            
        Raises:
            ArtifactUploadError: If upload fails
        """
        # Mask secrets if configured
        if self.config.mask_secrets:
            logs = self._mask_secrets(logs)
        
        content = logs.encode("utf-8")
        
        uri = self.client.upload(
            spec_name=task_context.spec_name,
            task_id=task_context.task_id,
            artifact_type=ArtifactType.LOG,
            content=content,
            metadata={
                "title": task_context.title,
            }
        )
        
        return Artifact(
            type=ArtifactType.LOG,
            uri=uri,
            size_bytes=len(content),
            created_at=datetime.now()
        )
    
    def _upload_test_result(self, task_context: TaskContext, test_result: TestResult) -> Artifact:
        """
        Upload test results.
        
        Args:
            task_context: Task context
            test_result: Test execution result
            
        Returns:
            Artifact metadata
            
        Raises:
            ArtifactUploadError: If upload fails
        """
        # Convert test result to JSON
        test_data = test_result.to_dict()
        content = json.dumps(test_data, indent=2).encode("utf-8")
        
        uri = self.client.upload(
            spec_name=task_context.spec_name,
            task_id=task_context.task_id,
            artifact_type=ArtifactType.TEST_RESULT,
            content=content,
            metadata={
                "title": task_context.title,
                "success": test_result.success,
                "test_count": len(test_result.test_results),
            }
        )
        
        return Artifact(
            type=ArtifactType.TEST_RESULT,
            uri=uri,
            size_bytes=len(content),
            created_at=datetime.now()
        )
    
    def _mask_secrets(self, text: str) -> str:
        """
        Mask secrets in text.
        
        Args:
            text: Text that may contain secrets
            
        Returns:
            Text with secrets masked
        """
        # Get environment variable names that likely contain secrets
        secret_env_vars = [
            self.config.git_token_env_var,
            self.config.artifact_store_api_key_env_var,
            self.config.kiro_api_key_env_var,
            "PASSWORD",
            "SECRET",
            "TOKEN",
            "API_KEY",
        ]
        
        masked_text = text
        for env_var in secret_env_vars:
            value = os.environ.get(env_var)
            if value:
                masked_text = masked_text.replace(value, "***MASKED***")
        
        return masked_text
    
    def _record_artifact_in_registry(self, task_context: TaskContext, artifact: Artifact) -> None:
        """
        Record artifact URI in the Task Registry.
        
        Args:
            task_context: Task context
            artifact: Artifact to record
            
        Note:
            Failures are logged as warnings but do not raise exceptions.
        """
        if not self.task_registry:
            logger.debug("Task Registry not available - skipping artifact recording")
            return
        
        try:
            # Convert ArtifactType to RegistryArtifactType
            registry_artifact_type = self._convert_artifact_type(artifact.type)
            
            # Record in Task Registry
            self.task_registry.add_artifact(
                spec_name=task_context.spec_name,
                task_id=task_context.task_id,
                artifact_type=registry_artifact_type,
                uri=artifact.uri,
                metadata={
                    "size_bytes": artifact.size_bytes,
                    "created_at": artifact.created_at.isoformat(),
                }
            )
            
            logger.info(f"Recorded artifact {artifact.type.value} in Task Registry for task {task_context.task_id}")
            
        except Exception as e:
            logger.warning(f"Failed to record artifact in Task Registry: {e}")
    
    def _convert_artifact_type(self, artifact_type: ArtifactType) -> "RegistryArtifactType":
        """
        Convert agent runner ArtifactType to Task Registry ArtifactType.
        
        Args:
            artifact_type: Agent runner artifact type
            
        Returns:
            Task Registry artifact type
        """
        if not TASK_REGISTRY_AVAILABLE:
            raise RuntimeError("Task Registry not available")
        
        # Map artifact types
        type_map = {
            ArtifactType.DIFF: RegistryArtifactType.DIFF,
            ArtifactType.LOG: RegistryArtifactType.LOG,
            ArtifactType.TEST_RESULT: RegistryArtifactType.TEST_RESULT,
        }
        
        return type_map[artifact_type]

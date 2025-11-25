"""
Artifact uploader for Agent Runner.

This module handles uploading task execution artifacts (diffs, logs, test results)
to the Artifact Store and recording artifact URIs in the Task Registry.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.exceptions import ArtifactUploadError
from necrocode.agent_runner.models import (
    Artifact,
    ArtifactType,
    ImplementationResult,
    TaskContext,
    TestResult,
)
from necrocode.agent_runner.task_registry_client import TaskRegistryClient

logger = logging.getLogger(__name__)





class ArtifactUploader:
    """
    Manages uploading task execution artifacts to the Artifact Store.
    
    Handles uploading diffs, logs, and test results, and records
    artifact URIs in the Task Registry for later retrieval.
    """
    
    def __init__(
        self,
        artifact_store_client: ArtifactStoreClient,
        task_registry_client: Optional[TaskRegistryClient] = None
    ):
        """
        Initialize the artifact uploader.
        
        Args:
            artifact_store_client: Client for Artifact Store service
            task_registry_client: Client for Task Registry service (optional)
        """
        self.artifact_store_client = artifact_store_client
        self.task_registry_client = task_registry_client
        
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
        
        try:
            uri = self.artifact_store_client.upload(
                artifact_type=ArtifactType.DIFF.value,
                content=content,
                metadata={
                    "spec_name": task_context.spec_name,
                    "task_id": task_context.task_id,
                    "title": task_context.title,
                    "branch": task_context.branch_name,
                }
            )
            
            logger.info(f"Uploaded diff artifact: {uri} ({len(content)} bytes)")
            
            return Artifact(
                type=ArtifactType.DIFF,
                uri=uri,
                size_bytes=len(content),
                created_at=datetime.now()
            )
        except Exception as e:
            error_msg = f"Failed to upload diff for task {task_context.task_id}: {e}"
            logger.error(error_msg)
            raise ArtifactUploadError(error_msg) from e
    
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
        content = logs.encode("utf-8")
        
        try:
            uri = self.artifact_store_client.upload(
                artifact_type=ArtifactType.LOG.value,
                content=content,
                metadata={
                    "spec_name": task_context.spec_name,
                    "task_id": task_context.task_id,
                    "title": task_context.title,
                }
            )
            
            logger.info(f"Uploaded log artifact: {uri} ({len(content)} bytes)")
            
            return Artifact(
                type=ArtifactType.LOG,
                uri=uri,
                size_bytes=len(content),
                created_at=datetime.now()
            )
        except Exception as e:
            error_msg = f"Failed to upload logs for task {task_context.task_id}: {e}"
            logger.error(error_msg)
            raise ArtifactUploadError(error_msg) from e
    
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
        
        try:
            uri = self.artifact_store_client.upload(
                artifact_type=ArtifactType.TEST_RESULT.value,
                content=content,
                metadata={
                    "spec_name": task_context.spec_name,
                    "task_id": task_context.task_id,
                    "title": task_context.title,
                    "success": test_result.success,
                    "test_count": len(test_result.test_results),
                }
            )
            
            logger.info(f"Uploaded test result artifact: {uri} ({len(content)} bytes)")
            
            return Artifact(
                type=ArtifactType.TEST_RESULT,
                uri=uri,
                size_bytes=len(content),
                created_at=datetime.now()
            )
        except Exception as e:
            error_msg = f"Failed to upload test results for task {task_context.task_id}: {e}"
            logger.error(error_msg)
            raise ArtifactUploadError(error_msg) from e
    

    
    def _record_artifact_in_registry(self, task_context: TaskContext, artifact: Artifact) -> None:
        """
        Record artifact URI in the Task Registry.
        
        Args:
            task_context: Task context
            artifact: Artifact to record
            
        Note:
            Failures are logged as warnings but do not raise exceptions.
        """
        if not self.task_registry_client:
            logger.debug("Task Registry client not available - skipping artifact recording")
            return
        
        try:
            # Record in Task Registry using the client
            self.task_registry_client.add_artifact(
                task_id=task_context.task_id,
                artifact_type=artifact.type.value,
                uri=artifact.uri,
                size_bytes=artifact.size_bytes,
                metadata={
                    "spec_name": task_context.spec_name,
                    "title": task_context.title,
                    "created_at": artifact.created_at.isoformat(),
                }
            )
            
            logger.info(f"Recorded artifact {artifact.type.value} in Task Registry for task {task_context.task_id}")
            
        except Exception as e:
            logger.warning(f"Failed to record artifact in Task Registry: {e}")

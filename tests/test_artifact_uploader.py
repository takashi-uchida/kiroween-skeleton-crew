"""
Tests for ArtifactUploader.

Tests artifact uploading functionality with external service clients,
Task Registry integration, and error handling.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

from necrocode.agent_runner.artifact_uploader import ArtifactUploader
from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.task_registry_client import TaskRegistryClient
from necrocode.agent_runner.models import (
    TaskContext,
    ImplementationResult,
    TestResult,
    SingleTestResult,
    ArtifactType,
)
from necrocode.agent_runner.exceptions import ArtifactUploadError


@pytest.fixture
def mock_artifact_store_client():
    """Create a mock ArtifactStoreClient."""
    client = Mock(spec=ArtifactStoreClient)
    client.upload.return_value = "http://artifact-store/artifacts/test-uri"
    return client


@pytest.fixture
def mock_task_registry_client():
    """Create a mock TaskRegistryClient."""
    client = Mock(spec=TaskRegistryClient)
    return client


@pytest.fixture
def task_context():
    """Create a sample task context."""
    return TaskContext(
        task_id="1.1",
        spec_name="test-spec",
        title="Test task",
        description="Test description",
        acceptance_criteria=["Criterion 1"],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp/workspace"),
        slot_id="slot-1",
        branch_name="feature/test",
    )


@pytest.fixture
def impl_result():
    """Create a sample implementation result."""
    return ImplementationResult(
        success=True,
        diff="diff --git a/test.py b/test.py\n+print('hello')",
        files_changed=["test.py"],
        duration_seconds=10.0,
    )


@pytest.fixture
def test_result():
    """Create a sample test result."""
    return TestResult(
        success=True,
        test_results=[
            SingleTestResult(
                command="pytest",
                success=True,
                stdout="All tests passed",
                stderr="",
                exit_code=0,
                duration_seconds=2.0,
            )
        ],
        total_duration_seconds=2.0,
    )





class TestArtifactUploader:
    """Tests for ArtifactUploader."""
    
    def test_initialization(self, mock_artifact_store_client, mock_task_registry_client):
        """Test uploader initialization."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=mock_task_registry_client
        )
        assert uploader.artifact_store_client == mock_artifact_store_client
        assert uploader.task_registry_client == mock_task_registry_client
    
    def test_upload_artifacts(
        self,
        mock_artifact_store_client,
        mock_task_registry_client,
        task_context,
        impl_result,
        test_result
    ):
        """Test uploading all artifacts."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=mock_task_registry_client
        )
        
        logs = "Test execution logs"
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=impl_result,
            test_result=test_result,
            logs=logs,
        )
        
        # Should have uploaded 3 artifacts: diff, log, test
        assert len(artifacts) == 3
        
        # Verify artifact types
        artifact_types = {a.type for a in artifacts}
        assert artifact_types == {ArtifactType.DIFF, ArtifactType.LOG, ArtifactType.TEST_RESULT}
        
        # Verify ArtifactStoreClient was called 3 times
        assert mock_artifact_store_client.upload.call_count == 3
        
        # Verify TaskRegistryClient was called 3 times
        assert mock_task_registry_client.add_artifact.call_count == 3
    
    def test_upload_artifacts_without_impl_result(
        self,
        mock_artifact_store_client,
        mock_task_registry_client,
        task_context,
        test_result
    ):
        """Test uploading artifacts when implementation failed."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=mock_task_registry_client
        )
        
        logs = "Test execution logs"
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=None,  # No implementation result
            test_result=test_result,
            logs=logs,
        )
        
        # Should have uploaded 2 artifacts: log, test (no diff)
        assert len(artifacts) == 2
        
        artifact_types = {a.type for a in artifacts}
        assert artifact_types == {ArtifactType.LOG, ArtifactType.TEST_RESULT}
        
        # Verify ArtifactStoreClient was called 2 times
        assert mock_artifact_store_client.upload.call_count == 2
    
    def test_upload_artifacts_without_test_result(
        self,
        mock_artifact_store_client,
        mock_task_registry_client,
        task_context,
        impl_result
    ):
        """Test uploading artifacts when tests were not run."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=mock_task_registry_client
        )
        
        logs = "Test execution logs"
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=impl_result,
            test_result=None,  # No test result
            logs=logs,
        )
        
        # Should have uploaded 2 artifacts: diff, log (no test)
        assert len(artifacts) == 2
        
        artifact_types = {a.type for a in artifacts}
        assert artifact_types == {ArtifactType.DIFF, ArtifactType.LOG}
        
        # Verify ArtifactStoreClient was called 2 times
        assert mock_artifact_store_client.upload.call_count == 2
    
    def test_upload_artifacts_without_task_registry(
        self,
        mock_artifact_store_client,
        task_context,
        impl_result,
        test_result
    ):
        """Test uploading artifacts without Task Registry client."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=None  # No Task Registry
        )
        
        logs = "Test execution logs"
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=impl_result,
            test_result=test_result,
            logs=logs,
        )
        
        # Should still upload 3 artifacts
        assert len(artifacts) == 3
        
        # Verify ArtifactStoreClient was called 3 times
        assert mock_artifact_store_client.upload.call_count == 3
    
    def test_upload_diff(self, mock_artifact_store_client, task_context, impl_result):
        """Test uploading diff artifact."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=None
        )
        
        artifact = uploader._upload_diff(task_context, impl_result.diff)
        
        assert artifact.type == ArtifactType.DIFF
        assert artifact.uri == "http://artifact-store/artifacts/test-uri"
        assert artifact.size_bytes > 0
        
        # Verify client was called with correct parameters
        mock_artifact_store_client.upload.assert_called_once()
        call_args = mock_artifact_store_client.upload.call_args
        assert call_args[1]["artifact_type"] == ArtifactType.DIFF.value
    
    def test_upload_log(self, mock_artifact_store_client, task_context):
        """Test uploading log artifact."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=None
        )
        
        logs = "Test logs"
        artifact = uploader._upload_log(task_context, logs)
        
        assert artifact.type == ArtifactType.LOG
        assert artifact.uri == "http://artifact-store/artifacts/test-uri"
        assert artifact.size_bytes > 0
        
        # Verify client was called with correct parameters
        mock_artifact_store_client.upload.assert_called_once()
        call_args = mock_artifact_store_client.upload.call_args
        assert call_args[1]["artifact_type"] == ArtifactType.LOG.value
    
    def test_upload_test_result(self, mock_artifact_store_client, task_context, test_result):
        """Test uploading test result artifact."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=None
        )
        
        artifact = uploader._upload_test_result(task_context, test_result)
        
        assert artifact.type == ArtifactType.TEST_RESULT
        assert artifact.uri == "http://artifact-store/artifacts/test-uri"
        assert artifact.size_bytes > 0
        
        # Verify client was called with correct parameters
        mock_artifact_store_client.upload.assert_called_once()
        call_args = mock_artifact_store_client.upload.call_args
        assert call_args[1]["artifact_type"] == ArtifactType.TEST_RESULT.value
    
    def test_record_artifact_in_registry(
        self,
        mock_artifact_store_client,
        mock_task_registry_client,
        task_context,
        impl_result
    ):
        """Test recording artifact in Task Registry."""
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=mock_task_registry_client
        )
        
        artifact = uploader._upload_diff(task_context, impl_result.diff)
        uploader._record_artifact_in_registry(task_context, artifact)
        
        # Verify TaskRegistryClient was called
        mock_task_registry_client.add_artifact.assert_called_once()
        call_args = mock_task_registry_client.add_artifact.call_args
        assert call_args[1]["task_id"] == task_context.task_id
        assert call_args[1]["artifact_type"] == ArtifactType.DIFF.value
        assert call_args[1]["uri"] == artifact.uri
    
    def test_upload_failure_handling(
        self,
        mock_artifact_store_client,
        mock_task_registry_client,
        task_context,
        impl_result,
        test_result
    ):
        """Test that upload failures are logged as warnings but don't stop execution."""
        # Make the first upload fail
        mock_artifact_store_client.upload.side_effect = [
            Exception("Upload failed"),  # diff upload fails
            "http://artifact-store/log-uri",  # log upload succeeds
            "http://artifact-store/test-uri",  # test upload succeeds
        ]
        
        uploader = ArtifactUploader(
            artifact_store_client=mock_artifact_store_client,
            task_registry_client=mock_task_registry_client
        )
        
        logs = "Test execution logs"
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=impl_result,
            test_result=test_result,
            logs=logs,
        )
        
        # Should have uploaded 2 artifacts (log and test, diff failed)
        assert len(artifacts) == 2
        
        artifact_types = {a.type for a in artifacts}
        assert artifact_types == {ArtifactType.LOG, ArtifactType.TEST_RESULT}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

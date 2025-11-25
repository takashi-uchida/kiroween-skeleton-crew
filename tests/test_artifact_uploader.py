"""
Tests for ArtifactUploader.

Tests artifact uploading functionality including storage backends,
Task Registry integration, and error handling.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from necrocode.agent_runner import (
    ArtifactUploader,
    ArtifactStoreClient,
    FilesystemBackend,
    TaskContext,
    ImplementationResult,
    TestResult,
    SingleTestResult,
    ArtifactType,
    RunnerConfig,
)
from necrocode.agent_runner.exceptions import ArtifactUploadError


@pytest.fixture
def temp_artifact_dir():
    """Create a temporary directory for artifacts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config(temp_artifact_dir):
    """Create a test configuration."""
    return RunnerConfig(
        artifact_store_url=f"file://{temp_artifact_dir}",
        mask_secrets=True,
    )


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


class TestFilesystemBackend:
    """Tests for FilesystemBackend."""
    
    def test_upload(self, temp_artifact_dir):
        """Test uploading content to filesystem."""
        backend = FilesystemBackend(temp_artifact_dir)
        
        content = b"test content"
        uri = "test-spec/1.1/diff.txt"
        
        backend.upload(uri, content)
        
        # Verify file was created
        file_path = temp_artifact_dir / uri
        assert file_path.exists()
        assert file_path.read_bytes() == content
    
    def test_save_metadata(self, temp_artifact_dir):
        """Test saving metadata."""
        backend = FilesystemBackend(temp_artifact_dir)
        
        # Upload a file first
        uri = "test-spec/1.1/diff.txt"
        backend.upload(uri, b"content")
        
        # Save metadata
        metadata = {
            "uri": uri,
            "size": 7,
            "checksum": "abc123",
        }
        backend.save_metadata(uri, metadata)
        
        # Verify metadata file was created
        metadata_path = temp_artifact_dir / "test-spec" / "1.1" / "metadata.json"
        assert metadata_path.exists()
        
        # Verify metadata content
        saved_metadata = json.loads(metadata_path.read_text())
        assert "diff.txt" in saved_metadata
        assert saved_metadata["diff.txt"]["uri"] == uri


class TestArtifactStoreClient:
    """Tests for ArtifactStoreClient."""
    
    def test_initialization(self, config):
        """Test client initialization."""
        client = ArtifactStoreClient(config)
        assert client.base_url == config.artifact_store_url
        assert isinstance(client._backend, FilesystemBackend)
    
    def test_upload(self, config):
        """Test uploading an artifact."""
        client = ArtifactStoreClient(config)
        
        uri = client.upload(
            spec_name="test-spec",
            task_id="1.1",
            artifact_type=ArtifactType.DIFF,
            content=b"test diff content",
        )
        
        assert uri == "test-spec/1.1/diff.diff"
    
    def test_generate_uri(self, config):
        """Test URI generation."""
        client = ArtifactStoreClient(config)
        
        uri = client._generate_uri("test-spec", "1.1", ArtifactType.DIFF)
        assert uri == "test-spec/1.1/diff.diff"
        
        uri = client._generate_uri("test-spec", "1.1", ArtifactType.LOG)
        assert uri == "test-spec/1.1/log.log"
        
        uri = client._generate_uri("test-spec", "1.1", ArtifactType.TEST_RESULT)
        assert uri == "test-spec/1.1/test.json"
    
    def test_calculate_checksum(self, config):
        """Test checksum calculation."""
        client = ArtifactStoreClient(config)
        
        content = b"test content"
        checksum = client._calculate_checksum(content)
        
        # Verify it's a valid SHA256 hex string
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)


class TestArtifactUploader:
    """Tests for ArtifactUploader."""
    
    def test_initialization(self, config):
        """Test uploader initialization."""
        uploader = ArtifactUploader(config=config)
        assert uploader.config == config
        assert isinstance(uploader.client, ArtifactStoreClient)
    
    def test_upload_artifacts(self, config, task_context, impl_result, test_result):
        """Test uploading all artifacts."""
        uploader = ArtifactUploader(config=config)
        
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
    
    def test_upload_artifacts_without_impl_result(self, config, task_context, test_result):
        """Test uploading artifacts when implementation failed."""
        uploader = ArtifactUploader(config=config)
        
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
    
    def test_upload_artifacts_without_test_result(self, config, task_context, impl_result):
        """Test uploading artifacts when tests were not run."""
        uploader = ArtifactUploader(config=config)
        
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
    
    def test_mask_secrets(self, config, task_context, impl_result, test_result, monkeypatch):
        """Test that secrets are masked in logs."""
        # Set a fake secret in environment
        monkeypatch.setenv("GIT_TOKEN", "secret-token-12345")
        
        uploader = ArtifactUploader(config=config)
        
        logs = "Connecting with token: secret-token-12345"
        artifacts = uploader.upload_artifacts(
            task_context=task_context,
            impl_result=impl_result,
            test_result=test_result,
            logs=logs,
        )
        
        # Find the log artifact
        log_artifact = next(a for a in artifacts if a.type == ArtifactType.LOG)
        
        # Read the uploaded log file
        artifact_dir = Path(config.artifact_store_url.replace("file://", ""))
        log_path = artifact_dir / log_artifact.uri
        log_content = log_path.read_text()
        
        # Verify secret was masked
        assert "secret-token-12345" not in log_content
        assert "***MASKED***" in log_content
    
    def test_upload_diff(self, config, task_context, impl_result):
        """Test uploading diff artifact."""
        uploader = ArtifactUploader(config=config)
        
        artifact = uploader._upload_diff(task_context, impl_result.diff)
        
        assert artifact.type == ArtifactType.DIFF
        assert artifact.uri == "test-spec/1.1/diff.diff"
        assert artifact.size_bytes > 0
    
    def test_upload_log(self, config, task_context):
        """Test uploading log artifact."""
        uploader = ArtifactUploader(config=config)
        
        logs = "Test logs"
        artifact = uploader._upload_log(task_context, logs)
        
        assert artifact.type == ArtifactType.LOG
        assert artifact.uri == "test-spec/1.1/log.log"
        assert artifact.size_bytes > 0
    
    def test_upload_test_result(self, config, task_context, test_result):
        """Test uploading test result artifact."""
        uploader = ArtifactUploader(config=config)
        
        artifact = uploader._upload_test_result(task_context, test_result)
        
        assert artifact.type == ArtifactType.TEST_RESULT
        assert artifact.uri == "test-spec/1.1/test.json"
        assert artifact.size_bytes > 0
        
        # Verify the JSON content is valid
        artifact_dir = Path(config.artifact_store_url.replace("file://", ""))
        test_path = artifact_dir / artifact.uri
        test_data = json.loads(test_path.read_text())
        
        assert test_data["success"] == True
        assert len(test_data["test_results"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

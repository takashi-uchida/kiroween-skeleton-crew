"""
Unit tests for external service clients.

Tests the LLMClient, TaskRegistryClient, RepoPoolClient, and ArtifactStoreClient
implementations.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from necrocode.agent_runner.llm_client import LLMClient
from necrocode.agent_runner.task_registry_client import TaskRegistryClient
from necrocode.agent_runner.repo_pool_client import RepoPoolClient
from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.models import LLMConfig, SlotAllocation, CodeChange, LLMResponse
from necrocode.agent_runner.exceptions import ImplementationError, RunnerError


class TestLLMClient:
    """Tests for LLMClient"""
    
    def test_init(self):
        """Test LLMClient initialization"""
        config = LLMConfig(
            api_key="test-key",
            model="gpt-4",
            timeout_seconds=120,
            max_tokens=4000
        )
        client = LLMClient(config)
        
        assert client.config.api_key == "test-key"
        assert client.config.model == "gpt-4"
        assert client.config.timeout_seconds == 120
        assert client.config.max_tokens == 4000
    
    @patch('necrocode.agent_runner.llm_client.OpenAI')
    def test_generate_code_success(self, mock_openai):
        """Test successful code generation"""
        # Setup mock
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({
            "code_changes": [
                {
                    "file_path": "test.py",
                    "operation": "create",
                    "content": "print('hello')"
                }
            ],
            "explanation": "Created test file"
        })))]
        mock_response.model = "gpt-4"
        mock_response.usage = Mock(total_tokens=100)
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test
        config = LLMConfig(api_key="test-key", model="gpt-4")
        client = LLMClient(config)
        
        result = client.generate_code(
            prompt="Create a test file",
            workspace_path=Path("/tmp/workspace")
        )
        
        assert isinstance(result, LLMResponse)
        assert len(result.code_changes) == 1
        assert result.code_changes[0].file_path == "test.py"
        assert result.code_changes[0].operation == "create"
        assert result.model == "gpt-4"
        assert result.tokens_used == 100
    
    @patch('necrocode.agent_runner.llm_client.OpenAI')
    def test_generate_code_invalid_json(self, mock_openai):
        """Test code generation with invalid JSON response"""
        # Setup mock
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="invalid json"))]
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test
        config = LLMConfig(api_key="test-key", model="gpt-4")
        client = LLMClient(config)
        
        with pytest.raises(ImplementationError, match="Failed to parse LLM response"):
            client.generate_code(
                prompt="Create a test file",
                workspace_path=Path("/tmp/workspace")
            )


class TestTaskRegistryClient:
    """Tests for TaskRegistryClient"""
    
    def test_init(self):
        """Test TaskRegistryClient initialization"""
        client = TaskRegistryClient("http://localhost:8080")
        
        assert client.base_url == "http://localhost:8080"
        assert client.timeout == 30
    
    @patch('necrocode.agent_runner.task_registry_client.requests.Session')
    def test_update_task_status(self, mock_session_class):
        """Test updating task status"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_session.put.return_value = mock_response
        
        client = TaskRegistryClient("http://localhost:8080")
        client.session = mock_session
        
        client.update_task_status("task-123", "in_progress", {"key": "value"})
        
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        assert "task-123" in call_args[0][0]
        assert call_args[1]["json"]["status"] == "in_progress"
    
    @patch('necrocode.agent_runner.task_registry_client.requests.Session')
    def test_add_event(self, mock_session_class):
        """Test adding an event"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TaskRegistryClient("http://localhost:8080")
        client.session = mock_session
        
        client.add_event("task-123", "TaskStarted", {"runner_id": "runner-001"})
        
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "task-123" in call_args[0][0]
        assert call_args[1]["json"]["event_type"] == "TaskStarted"


class TestRepoPoolClient:
    """Tests for RepoPoolClient"""
    
    def test_init(self):
        """Test RepoPoolClient initialization"""
        client = RepoPoolClient("http://localhost:8081")
        
        assert client.base_url == "http://localhost:8081"
        assert client.timeout == 30
    
    @patch('necrocode.agent_runner.repo_pool_client.requests.Session')
    def test_allocate_slot(self, mock_session_class):
        """Test allocating a slot"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "slot_id": "slot-123",
            "slot_path": "/tmp/slot-123"
        }
        mock_session.post.return_value = mock_response
        
        client = RepoPoolClient("http://localhost:8081")
        client.session = mock_session
        
        result = client.allocate_slot(
            repo_url="https://github.com/user/repo.git",
            required_by="task-123"
        )
        
        assert isinstance(result, SlotAllocation)
        assert result.slot_id == "slot-123"
        assert result.slot_path == Path("/tmp/slot-123")
    
    @patch('necrocode.agent_runner.repo_pool_client.requests.Session')
    def test_release_slot(self, mock_session_class):
        """Test releasing a slot"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = RepoPoolClient("http://localhost:8081")
        client.session = mock_session
        
        client.release_slot("slot-123")
        
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "slot-123" in call_args[0][0]


class TestArtifactStoreClient:
    """Tests for ArtifactStoreClient"""
    
    def test_init(self):
        """Test ArtifactStoreClient initialization"""
        client = ArtifactStoreClient("http://localhost:8082")
        
        assert client.base_url == "http://localhost:8082"
        assert client.timeout == 60
    
    @patch('necrocode.agent_runner.artifact_store_client.requests.Session')
    def test_upload(self, mock_session_class):
        """Test uploading an artifact"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"uri": "s3://bucket/artifact.txt"}
        mock_session.post.return_value = mock_response
        
        client = ArtifactStoreClient("http://localhost:8082")
        client.session = mock_session
        
        uri = client.upload(
            artifact_type="diff",
            content=b"diff content",
            metadata={"task_id": "task-123"}
        )
        
        assert uri == "s3://bucket/artifact.txt"
        mock_session.post.assert_called_once()
    
    @patch('necrocode.agent_runner.artifact_store_client.requests.Session')
    def test_upload_text(self, mock_session_class):
        """Test uploading a text artifact"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"uri": "s3://bucket/log.txt"}
        mock_session.post.return_value = mock_response
        
        client = ArtifactStoreClient("http://localhost:8082")
        client.session = mock_session
        
        uri = client.upload_text(
            artifact_type="log",
            content="log content",
            metadata={"task_id": "task-123"}
        )
        
        assert uri == "s3://bucket/log.txt"
    
    @patch('necrocode.agent_runner.artifact_store_client.requests.Session')
    def test_download(self, mock_session_class):
        """Test downloading an artifact"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.content = b"artifact content"
        mock_session.get.return_value = mock_response
        
        client = ArtifactStoreClient("http://localhost:8082")
        client.session = mock_session
        
        content = client.download("s3://bucket/artifact.txt")
        
        assert content == b"artifact content"

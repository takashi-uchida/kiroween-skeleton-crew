"""
Tests for Review Comment functionality in PR Service.

Tests automatic comment posting, test failure notifications,
and comment template customization.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import PRServiceConfig, GitHostType
from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.review_pr_service.exceptions import PRServiceError


@pytest.fixture
def mock_config():
    """Create a mock PR Service configuration."""
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="test-owner/test-repo",
        api_token="test-token"
    )
    config.ci.auto_comment_on_failure = True
    return config


@pytest.fixture
def mock_git_host_client():
    """Create a mock Git host client."""
    client = Mock()
    client.add_comment = Mock()
    return client


@pytest.fixture
def pr_service(mock_config, mock_git_host_client):
    """Create a PR Service instance with mocked dependencies."""
    with patch('necrocode.review_pr_service.pr_service.PRService._create_git_host_client') as mock_create:
        mock_create.return_value = mock_git_host_client
        service = PRService(mock_config)
        return service


class TestBasicCommentPosting:
    """Tests for basic comment posting functionality."""
    
    def test_post_simple_comment(self, pr_service, mock_git_host_client):
        """Test posting a simple comment without details."""
        # Arrange
        pr_id = "123"
        message = "This is a test comment"
        
        # Act
        pr_service.post_comment(pr_id, message, use_template=False)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        assert call_args[0][0] == pr_id
        assert message in call_args[0][1]
        assert "NecroCode" in call_args[0][1]
    
    def test_post_comment_with_details(self, pr_service, mock_git_host_client):
        """Test posting a comment with additional details."""
        # Arrange
        pr_id = "123"
        message = "Review required"
        details = {
            "Priority": "High",
            "Reviewer": "john@example.com"
        }
        
        # Act
        pr_service.post_comment(pr_id, message, details=details, use_template=False)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        assert message in comment_text
        assert "Priority" in comment_text
        assert "High" in comment_text
        assert "Reviewer" in comment_text
        assert "john@example.com" in comment_text
    
    def test_post_comment_handles_client_error(self, pr_service, mock_git_host_client):
        """Test that comment posting handles client errors gracefully."""
        # Arrange
        pr_id = "123"
        message = "Test comment"
        mock_git_host_client.add_comment.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(PRServiceError) as exc_info:
            pr_service.post_comment(pr_id, message)
        
        assert "Comment posting failed" in str(exc_info.value)


class TestTestFailureComments:
    """Tests for automatic test failure comment posting."""
    
    def test_post_test_failure_comment_basic(self, pr_service, mock_git_host_client):
        """Test posting a basic test failure comment."""
        # Arrange
        pr_id = "123"
        test_results = {
            "total": 50,
            "passed": 45,
            "failed": 5,
            "skipped": 0,
            "duration": 123.45
        }
        
        # Act
        pr_service.post_test_failure_comment(pr_id, test_results)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        assert "Test Failure" in comment_text
        assert "50" in comment_text  # total
        assert "45" in comment_text  # passed
        assert "5" in comment_text   # failed
        assert "123.45" in comment_text  # duration
    
    def test_post_test_failure_with_error_log(self, pr_service, mock_git_host_client):
        """Test posting test failure comment with error log URL."""
        # Arrange
        pr_id = "123"
        test_results = {"total": 10, "passed": 8, "failed": 2, "skipped": 0}
        error_log_url = "https://ci.example.com/logs/456"
        
        # Act
        pr_service.post_test_failure_comment(
            pr_id,
            test_results,
            error_log_url=error_log_url
        )
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        assert "Error Logs" in comment_text
        assert error_log_url in comment_text
    
    def test_post_test_failure_with_artifact_links(self, pr_service, mock_git_host_client):
        """Test posting test failure comment with artifact links."""
        # Arrange
        pr_id = "123"
        test_results = {"total": 10, "passed": 8, "failed": 2, "skipped": 0}
        artifact_links = {
            "Test Report": "https://artifacts.example.com/report.html",
            "Coverage": "https://artifacts.example.com/coverage.html"
        }
        
        # Act
        pr_service.post_test_failure_comment(
            pr_id,
            test_results,
            artifact_links=artifact_links
        )
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        assert "Related Artifacts" in comment_text
        assert "Test Report" in comment_text
        assert "Coverage" in comment_text
        assert artifact_links["Test Report"] in comment_text
        assert artifact_links["Coverage"] in comment_text
    
    def test_post_test_failure_with_failed_test_details(self, pr_service, mock_git_host_client):
        """Test posting test failure comment with detailed failed test information."""
        # Arrange
        pr_id = "123"
        test_results = {
            "total": 10,
            "passed": 8,
            "failed": 2,
            "skipped": 0,
            "failed_tests": [
                {
                    "name": "test_authentication",
                    "error": "AssertionError: Expected 200, got 401"
                },
                {
                    "name": "test_database",
                    "error": "ConnectionError: Database unavailable"
                }
            ]
        }
        
        # Act
        pr_service.post_test_failure_comment(pr_id, test_results)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        assert "Failed Tests" in comment_text
        assert "test_authentication" in comment_text
        assert "AssertionError" in comment_text
        assert "test_database" in comment_text
        assert "ConnectionError" in comment_text
    
    def test_post_test_failure_limits_failed_tests(self, pr_service, mock_git_host_client):
        """Test that failed test list is limited to prevent overly long comments."""
        # Arrange
        pr_id = "123"
        failed_tests = [
            {"name": f"test_{i}", "error": f"Error {i}"}
            for i in range(20)  # 20 failed tests
        ]
        test_results = {
            "total": 20,
            "passed": 0,
            "failed": 20,
            "skipped": 0,
            "failed_tests": failed_tests
        }
        
        # Act
        pr_service.post_test_failure_comment(pr_id, test_results)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        # Should show first 10 tests
        assert "test_0" in comment_text
        assert "test_9" in comment_text
        
        # Should indicate there are more
        assert "10 more failed tests" in comment_text
    
    def test_auto_comment_disabled(self, pr_service, mock_git_host_client):
        """Test that auto-comment is skipped when disabled in config."""
        # Arrange
        pr_service.config.ci.auto_comment_on_failure = False
        pr_id = "123"
        test_results = {"total": 10, "passed": 8, "failed": 2, "skipped": 0}
        
        # Act
        pr_service.post_test_failure_comment(pr_id, test_results)
        
        # Assert
        mock_git_host_client.add_comment.assert_not_called()


class TestCommentTemplates:
    """Tests for comment template functionality."""
    
    def test_load_comment_template_success(self, pr_service):
        """Test loading a valid comment template."""
        # Arrange
        template_content = "{{message}}\n{% if details %}Details: {{details}}{% endif %}"
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            with patch('pathlib.Path.exists', return_value=True):
                # Act
                template = pr_service._load_comment_template()
                
                # Assert
                assert template is not None
    
    def test_load_comment_template_not_found(self, pr_service):
        """Test handling of missing comment template."""
        # Arrange
        with patch('pathlib.Path.exists', return_value=False):
            # Act
            template = pr_service._load_comment_template()
            
            # Assert
            assert template is None
    
    def test_post_comment_with_template(self, pr_service, mock_git_host_client):
        """Test posting comment using template."""
        # Arrange
        pr_id = "123"
        message = "Test message"
        details = {"key": "value"}
        
        template_content = "{{message}}\n{% if details %}{{details}}{% endif %}"
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            with patch('pathlib.Path.exists', return_value=True):
                # Act
                pr_service.post_comment(pr_id, message, details=details, use_template=True)
                
                # Assert
                mock_git_host_client.add_comment.assert_called_once()
    
    def test_post_comment_template_fallback(self, pr_service, mock_git_host_client):
        """Test fallback to plain text when template fails to load."""
        # Arrange
        pr_id = "123"
        message = "Test message"
        
        with patch('pathlib.Path.exists', return_value=False):
            # Act
            pr_service.post_comment(pr_id, message, use_template=True)
            
            # Assert
            mock_git_host_client.add_comment.assert_called_once()
            call_args = mock_git_host_client.add_comment.call_args
            comment_text = call_args[0][1]
            
            # Should use plain text format
            assert message in comment_text
            assert "NecroCode" in comment_text
    
    def test_format_comment_plain(self, pr_service):
        """Test plain text comment formatting."""
        # Arrange
        message = "Test message"
        details = {
            "Status": "In Progress",
            "Priority": "High"
        }
        
        # Act
        comment_text = pr_service._format_comment_plain(message, details)
        
        # Assert
        assert message in comment_text
        assert "Status" in comment_text
        assert "In Progress" in comment_text
        assert "Priority" in comment_text
        assert "High" in comment_text
        assert "NecroCode" in comment_text
    
    def test_format_comment_plain_without_details(self, pr_service):
        """Test plain text comment formatting without details."""
        # Arrange
        message = "Simple message"
        
        # Act
        comment_text = pr_service._format_comment_plain(message, None)
        
        # Assert
        assert message in comment_text
        assert "Details" not in comment_text
        assert "NecroCode" in comment_text


class TestCommentConfiguration:
    """Tests for comment configuration options."""
    
    def test_config_auto_comment_enabled_by_default(self, mock_config):
        """Test that auto-comment is enabled by default."""
        assert mock_config.ci.auto_comment_on_failure is True
    
    def test_config_auto_comment_can_be_disabled(self, mock_config):
        """Test that auto-comment can be disabled."""
        # Arrange & Act
        mock_config.ci.auto_comment_on_failure = False
        
        # Assert
        assert mock_config.ci.auto_comment_on_failure is False
    
    def test_config_custom_comment_template_path(self, mock_config):
        """Test setting custom comment template path."""
        # Arrange & Act
        custom_path = "custom/path/to/template.md"
        mock_config.template.comment_template_path = custom_path
        
        # Assert
        assert mock_config.template.comment_template_path == custom_path


class TestCommentIntegration:
    """Integration tests for comment functionality."""
    
    def test_ci_failure_triggers_comment(self, pr_service, mock_git_host_client):
        """Test that CI failure triggers automatic comment."""
        # Arrange
        pr_id = "123"
        test_results = {
            "total": 100,
            "passed": 95,
            "failed": 5,
            "skipped": 0
        }
        
        # Ensure auto-comment is enabled
        pr_service.config.ci.auto_comment_on_failure = True
        
        # Act
        pr_service.post_test_failure_comment(pr_id, test_results)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
    
    def test_comment_includes_next_steps(self, pr_service, mock_git_host_client):
        """Test that failure comment includes helpful next steps."""
        # Arrange
        pr_id = "123"
        test_results = {"total": 10, "passed": 8, "failed": 2, "skipped": 0}
        
        # Act
        pr_service.post_test_failure_comment(pr_id, test_results)
        
        # Assert
        mock_git_host_client.add_comment.assert_called_once()
        call_args = mock_git_host_client.add_comment.call_args
        comment_text = call_args[0][1]
        
        assert "Next Steps" in comment_text
        assert "Review" in comment_text or "Fix" in comment_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

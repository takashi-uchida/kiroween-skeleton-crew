"""
Unit tests for Review & PR Service Git Host Clients.

Tests GitHostClient abstract interface and concrete implementations
(GitHub, GitLab, Bitbucket) using mocks.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from necrocode.review_pr_service.git_host_client import (
    GitHostClient,
    GitHubClient,
    GitLabClient,
    BitbucketClient
)
from necrocode.review_pr_service.models import PullRequest, CIStatus, PRState
from necrocode.review_pr_service.exceptions import (
    PRServiceError,
    AuthenticationError,
    RateLimitError,
    NetworkError
)


class TestGitHubClient:
    """Test GitHubClient implementation"""
    
    @pytest.fixture
    def github_config(self):
        """GitHub client configuration"""
        return {
            "token": "test_token",
            "repo_owner": "test_owner",
            "repo_name": "test_repo"
        }
    
    @pytest.fixture
    def mock_github(self):
        """Mock PyGithub library"""
        with patch('necrocode.review_pr_service.git_host_client.Github') as mock:
            yield mock
    
    def test_github_client_initialization(self, github_config, mock_github):
        """Test GitHubClient initialization"""
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        
        client = GitHubClient(github_config)
        
        assert client.config == github_config
        mock_github.assert_called_once_with("test_token")
        mock_github_instance.get_repo.assert_called_once_with("test_owner/test_repo")
    
    def test_github_client_missing_config(self):
        """Test GitHubClient with missing configuration"""
        with pytest.raises(PRServiceError, match="Missing required GitHub config"):
            GitHubClient({"token": "test"})
    
    def test_github_create_pull_request(self, github_config, mock_github):
        """Test creating a GitHub pull request"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pr
        
        # Configure mock PR
        mock_pr.id = 12345
        mock_pr.number = 42
        mock_pr.title = "Test PR"
        mock_pr.body = "Test description"
        mock_pr.html_url = "https://github.com/test/repo/pull/42"
        mock_pr.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_pr.merged_at = None
        
        client = GitHubClient(github_config)
        
        # Create PR
        pr = client.create_pull_request(
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            draft=False
        )
        
        # Verify
        assert pr.pr_id == "12345"
        assert pr.pr_number == 42
        assert pr.title == "Test PR"
        assert pr.source_branch == "feature/test"
        assert pr.target_branch == "main"
        assert pr.state == PRState.OPEN
        assert pr.draft is False
        
        mock_repo.create_pull.assert_called_once_with(
            title="Test PR",
            body="Test description",
            head="feature/test",
            base="main",
            draft=False
        )
    
    def test_github_get_ci_status_success(self, github_config, mock_github):
        """Test getting CI status from GitHub (success)"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_commits = Mock()
        mock_commit = Mock()
        mock_status = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        mock_pr.get_commits.return_value = mock_commits
        mock_commits.totalCount = 1
        mock_commits.reversed = [mock_commit]
        mock_commit.get_combined_status.return_value = mock_status
        mock_status.state = "success"
        
        client = GitHubClient(github_config)
        
        # Get CI status
        status = client.get_ci_status("42")
        
        assert status == CIStatus.SUCCESS
        mock_repo.get_pull.assert_called_once_with(42)
    
    def test_github_get_ci_status_pending(self, github_config, mock_github):
        """Test getting CI status from GitHub (pending)"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_commits = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        mock_pr.get_commits.return_value = mock_commits
        mock_commits.totalCount = 0
        
        client = GitHubClient(github_config)
        
        # Get CI status
        status = client.get_ci_status("42")
        
        assert status == CIStatus.PENDING
    
    def test_github_add_comment(self, github_config, mock_github):
        """Test adding comment to GitHub PR"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        
        client = GitHubClient(github_config)
        
        # Add comment
        client.add_comment("42", "Test comment")
        
        mock_pr.create_issue_comment.assert_called_once_with("Test comment")
    
    def test_github_add_labels(self, github_config, mock_github):
        """Test adding labels to GitHub PR"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_issue = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        mock_repo.get_issue.return_value = mock_issue
        mock_pr.number = 42
        
        client = GitHubClient(github_config)
        
        # Add labels
        client.add_labels("42", ["bug", "enhancement"])
        
        mock_issue.add_to_labels.assert_called_once_with("bug", "enhancement")
    
    def test_github_assign_reviewers(self, github_config, mock_github):
        """Test assigning reviewers to GitHub PR"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        
        client = GitHubClient(github_config)
        
        # Assign reviewers
        client.assign_reviewers("42", ["reviewer1", "reviewer2"])
        
        mock_pr.create_review_request.assert_called_once_with(
            reviewers=["reviewer1", "reviewer2"]
        )
    
    def test_github_authentication_error(self, github_config, mock_github):
        """Test GitHub authentication error handling"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        
        # Create exception with status attribute
        github_exception = Exception("Bad credentials")
        github_exception.status = 401
        mock_repo.get_pull.side_effect = github_exception
        
        client = GitHubClient(github_config)
        client.GithubException = Exception
        
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError):
            client.get_ci_status("42")
    
    def test_github_rate_limit_error(self, github_config, mock_github):
        """Test GitHub rate limit error handling"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        
        # Create exception with status attribute
        github_exception = Exception("API rate limit exceeded")
        github_exception.status = 403
        mock_repo.get_pull.side_effect = github_exception
        
        client = GitHubClient(github_config)
        client.GithubException = Exception
        
        # Should raise RateLimitError
        with pytest.raises(RateLimitError):
            client.get_ci_status("42")


class TestGitLabClient:
    """Test GitLabClient implementation"""
    
    @pytest.fixture
    def gitlab_config(self):
        """GitLab client configuration"""
        return {
            "token": "test_token",
            "project_id": "12345",
            "url": "https://gitlab.com"
        }
    
    @pytest.fixture
    def mock_gitlab(self):
        """Mock python-gitlab library"""
        with patch('necrocode.review_pr_service.git_host_client.gitlab') as mock:
            yield mock
    
    def test_gitlab_client_initialization(self, gitlab_config, mock_gitlab):
        """Test GitLabClient initialization"""
        mock_gitlab_instance = Mock()
        mock_project = Mock()
        
        mock_gitlab.Gitlab.return_value = mock_gitlab_instance
        mock_gitlab_instance.projects.get.return_value = mock_project
        
        client = GitLabClient(gitlab_config)
        
        assert client.config == gitlab_config
        mock_gitlab.Gitlab.assert_called_once_with(
            "https://gitlab.com",
            private_token="test_token"
        )
        mock_gitlab_instance.projects.get.assert_called_once_with("12345")
    
    def test_gitlab_client_missing_config(self):
        """Test GitLabClient with missing configuration"""
        with pytest.raises(PRServiceError, match="Missing required GitLab config"):
            GitLabClient({"token": "test"})
    
    def test_gitlab_create_pull_request(self, gitlab_config, mock_gitlab):
        """Test creating a GitLab merge request"""
        # Setup mocks
        mock_gitlab_instance = Mock()
        mock_project = Mock()
        mock_mr = Mock()
        
        mock_gitlab.Gitlab.return_value = mock_gitlab_instance
        mock_gitlab_instance.projects.get.return_value = mock_project
        mock_project.mergerequests.create.return_value = mock_mr
        
        # Configure mock MR
        mock_mr.iid = 42
        mock_mr.web_url = "https://gitlab.com/test/repo/-/merge_requests/42"
        mock_mr.created_at = "2024-01-01T12:00:00Z"
        
        client = GitLabClient(gitlab_config)
        
        # Create MR
        pr = client.create_pull_request(
            title="Test MR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            draft=False
        )
        
        # Verify
        assert pr.pr_number == 42
        assert pr.title == "Test MR"
        assert pr.source_branch == "feature/test"
        assert pr.target_branch == "main"
        assert pr.state == PRState.OPEN
        assert pr.draft is False
    
    def test_gitlab_get_ci_status(self, gitlab_config, mock_gitlab):
        """Test getting CI status from GitLab"""
        # Setup mocks
        mock_gitlab_instance = Mock()
        mock_project = Mock()
        mock_mr = Mock()
        
        mock_gitlab.Gitlab.return_value = mock_gitlab_instance
        mock_gitlab_instance.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        
        # Configure mock MR with pipeline
        mock_mr.head_pipeline = {"status": "success"}
        
        client = GitLabClient(gitlab_config)
        
        # Get CI status
        status = client.get_ci_status("42")
        
        assert status == CIStatus.SUCCESS
    
    def test_gitlab_add_comment(self, gitlab_config, mock_gitlab):
        """Test adding comment to GitLab MR"""
        # Setup mocks
        mock_gitlab_instance = Mock()
        mock_project = Mock()
        mock_mr = Mock()
        mock_notes = Mock()
        
        mock_gitlab.Gitlab.return_value = mock_gitlab_instance
        mock_gitlab_instance.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_mr.notes = mock_notes
        
        client = GitLabClient(gitlab_config)
        
        # Add comment
        client.add_comment("42", "Test comment")
        
        mock_notes.create.assert_called_once_with({'body': 'Test comment'})


class TestBitbucketClient:
    """Test BitbucketClient implementation"""
    
    @pytest.fixture
    def bitbucket_config(self):
        """Bitbucket client configuration"""
        return {
            "username": "test_user",
            "password": "test_password",
            "workspace": "test_workspace",
            "repo_slug": "test_repo",
            "url": "https://api.bitbucket.org"
        }
    
    @pytest.fixture
    def mock_bitbucket(self):
        """Mock atlassian-python-api library"""
        with patch('necrocode.review_pr_service.git_host_client.Bitbucket') as mock:
            yield mock
    
    def test_bitbucket_client_initialization(self, bitbucket_config, mock_bitbucket):
        """Test BitbucketClient initialization"""
        mock_bitbucket_instance = Mock()
        mock_bitbucket.return_value = mock_bitbucket_instance
        
        client = BitbucketClient(bitbucket_config)
        
        assert client.config == bitbucket_config
        assert client.workspace == "test_workspace"
        assert client.repo_slug == "test_repo"
    
    def test_bitbucket_client_missing_config(self):
        """Test BitbucketClient with missing configuration"""
        with pytest.raises(PRServiceError, match="Missing required Bitbucket config"):
            BitbucketClient({"username": "test"})
    
    def test_bitbucket_create_pull_request(self, bitbucket_config, mock_bitbucket):
        """Test creating a Bitbucket pull request"""
        # Setup mocks
        mock_bitbucket_instance = Mock()
        mock_bitbucket.return_value = mock_bitbucket_instance
        
        # Configure mock response
        mock_response = {
            "id": 42,
            "title": "Test PR",
            "description": "Test description",
            "links": {
                "html": {
                    "href": "https://bitbucket.org/test/repo/pull-requests/42"
                }
            },
            "created_on": "2024-01-01T12:00:00Z"
        }
        mock_bitbucket_instance.create_pullrequest.return_value = mock_response
        
        client = BitbucketClient(bitbucket_config)
        
        # Create PR
        pr = client.create_pull_request(
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            draft=False
        )
        
        # Verify
        assert pr.pr_number == 42
        assert pr.title == "Test PR"
        assert pr.source_branch == "feature/test"
        assert pr.target_branch == "main"
        assert pr.state == PRState.OPEN
    
    def test_bitbucket_get_ci_status(self, bitbucket_config, mock_bitbucket):
        """Test getting CI status from Bitbucket"""
        # Setup mocks
        mock_bitbucket_instance = Mock()
        mock_bitbucket.return_value = mock_bitbucket_instance
        
        # Configure mock PR
        mock_pr = {
            "source": {
                "commit": {
                    "hash": "abc123"
                }
            }
        }
        mock_bitbucket_instance.get_pullrequest.return_value = mock_pr
        
        # Configure mock statuses
        mock_statuses = {
            "values": [
                {"state": "SUCCESSFUL"}
            ]
        }
        mock_bitbucket_instance.get_commit_statuses.return_value = mock_statuses
        
        client = BitbucketClient(bitbucket_config)
        
        # Get CI status
        status = client.get_ci_status("42")
        
        assert status == CIStatus.SUCCESS
    
    def test_bitbucket_add_comment(self, bitbucket_config, mock_bitbucket):
        """Test adding comment to Bitbucket PR"""
        # Setup mocks
        mock_bitbucket_instance = Mock()
        mock_bitbucket.return_value = mock_bitbucket_instance
        
        client = BitbucketClient(bitbucket_config)
        
        # Add comment
        client.add_comment("42", "Test comment")
        
        mock_bitbucket_instance.add_pullrequest_comment.assert_called_once_with(
            "test_workspace",
            "test_repo",
            "42",
            "Test comment"
        )


class TestGitHostClientAbstract:
    """Test GitHostClient abstract interface"""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that GitHostClient cannot be instantiated directly"""
        with pytest.raises(TypeError):
            GitHostClient({"test": "config"})
    
    def test_abstract_methods_defined(self):
        """Test that all abstract methods are defined"""
        abstract_methods = [
            '_validate_config',
            'create_pull_request',
            'get_ci_status',
            'add_comment',
            'add_labels',
            'remove_label',
            'assign_reviewers',
            'update_pr_description',
            'get_pr',
            'merge_pr',
            'check_conflicts',
            'convert_to_ready',
            'delete_branch'
        ]
        
        for method_name in abstract_methods:
            assert hasattr(GitHostClient, method_name)

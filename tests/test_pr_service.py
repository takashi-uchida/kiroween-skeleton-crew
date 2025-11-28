"""
Tests for PRService main class.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import PRServiceConfig, GitHostType
from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.review_pr_service.exceptions import PRServiceError, PRCreationError
from necrocode.task_registry.models import Task, TaskState, Artifact, ArtifactType


@pytest.fixture
def github_config():
    """Create a GitHub configuration for testing."""
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="test-token",
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    task = Task(
        id="1.1",
        title="Test Task",
        description="Test task description",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "backend",
            "priority": "high",
        }
    )
    
    # Add sample artifacts
    task.artifacts = [
        Artifact(
            type=ArtifactType.DIFF,
            uri="https://example.com/diff.txt",
            size_bytes=1024,
            created_at=datetime.now(),
            metadata={"name": "Code Changes"}
        ),
    ]
    
    return task


@pytest.fixture
def sample_pr():
    """Create a sample PR for testing."""
    return PullRequest(
        pr_id="12345",
        pr_number=42,
        title="Test PR",
        description="Test PR description",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
    )


class TestLabelManagement:
    """Test label management functionality."""
    
    def test_apply_labels_based_on_task_type(self, github_config, sample_task, sample_pr):
        """Test applying labels based on task type."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            
            pr_service = PRService(github_config)
            pr_service._apply_labels(sample_pr, sample_task)
            
            # Verify labels were added
            mock_client.add_labels.assert_called_once()
            call_args = mock_client.add_labels.call_args
            labels = call_args[0][1]
            
            # Should include backend labels and priority label
            assert "backend" in labels or "api" in labels
            assert "priority:high" in labels
    
    def test_apply_labels_disabled(self, github_config, sample_task, sample_pr):
        """Test that labels are not applied when disabled."""
        github_config.labels.enabled = False
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            
            pr_service = PRService(github_config)
            pr_service._apply_labels(sample_pr, sample_task)
            
            # Verify labels were not added
            mock_client.add_labels.assert_not_called()
    
    def test_update_labels_for_ci_status(self, github_config, sample_pr):
        """Test updating labels based on CI status."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_pr.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.update_labels_for_ci_status(sample_pr.pr_id, CIStatus.SUCCESS)
            
            # Verify new CI label was added
            mock_client.add_labels.assert_called_once()
            call_args = mock_client.add_labels.call_args
            labels = call_args[0][1]
            
            assert "ci:success" in labels
    
    def test_update_labels_removes_old_ci_labels(self, github_config, sample_pr):
        """Test that old CI labels are removed when updating."""
        sample_pr.labels = ["ci:pending", "backend"]
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_pr.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.update_labels_for_ci_status(sample_pr.pr_id, CIStatus.FAILURE)
            
            # Verify old CI label was removed
            mock_client.remove_label.assert_called_once_with(sample_pr.pr_id, "ci:pending")
            
            # Verify new CI label was added
            mock_client.add_labels.assert_called_once()
            call_args = mock_client.add_labels.call_args
            labels = call_args[0][1]
            assert "ci:failure" in labels
    
    def test_custom_label_rules(self, github_config, sample_task, sample_pr):
        """Test custom label rules."""
        # Set custom label rules
        github_config.labels.rules = {
            "backend": ["custom-backend", "api-service"],
            "frontend": ["custom-frontend", "ui"],
        }
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            
            pr_service = PRService(github_config)
            pr_service._apply_labels(sample_pr, sample_task)
            
            # Verify custom labels were added
            mock_client.add_labels.assert_called_once()
            call_args = mock_client.add_labels.call_args
            labels = call_args[0][1]
            
            assert "custom-backend" in labels or "api-service" in labels


class TestPRServiceInitialization:
    """Test PRService initialization."""
    
    def test_init_with_github(self, github_config):
        """Test initialization with GitHub configuration."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient'):
            pr_service = PRService(github_config)
            
            assert pr_service.config == github_config
            assert pr_service.git_host_client is not None
            assert pr_service.template_engine is not None
    
    def test_init_with_gitlab(self):
        """Test initialization with GitLab configuration."""
        config = PRServiceConfig(
            git_host_type=GitHostType.GITLAB,
            repository="12345",
            api_token="test-token",
        )
        
        with patch('necrocode.review_pr_service.pr_service.GitLabClient'):
            pr_service = PRService(config)
            
            assert pr_service.config == config
            assert pr_service.git_host_client is not None
    
    def test_init_with_bitbucket(self):
        """Test initialization with Bitbucket configuration."""
        config = PRServiceConfig(
            git_host_type=GitHostType.BITBUCKET,
            repository="workspace/repo",
            api_token="username:password",
        )
        
        with patch('necrocode.review_pr_service.pr_service.BitbucketClient'):
            pr_service = PRService(config)
            
            assert pr_service.config == config
            assert pr_service.git_host_client is not None
    
    def test_init_with_task_registry(self, github_config, tmp_path):
        """Test initialization with Task Registry."""
        github_config.task_registry_path = str(tmp_path / "task_registry")
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient'):
            pr_service = PRService(github_config)
            
            assert pr_service.task_registry is not None
    
    def test_init_with_artifact_store(self, github_config):
        """Test initialization with Artifact Store."""
        github_config.artifact_store_url = "file:///tmp/artifacts"
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient'):
            pr_service = PRService(github_config)
            
            assert pr_service.artifact_store is not None


class TestPRCreation:
    """Test PR creation functionality."""
    
    def test_create_pr_success(self, github_config, sample_task, sample_pr):
        """Test successful PR creation."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            # Mock the client
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            # Create PR service
            pr_service = PRService(github_config)
            
            # Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name="feature/test",
                base_branch="main",
            )
            
            # Verify PR was created
            assert pr == sample_pr
            mock_client.create_pull_request.assert_called_once()
    
    def test_create_pr_with_acceptance_criteria(self, github_config, sample_task, sample_pr):
        """Test PR creation with acceptance criteria."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            
            acceptance_criteria = [
                "Feature works correctly",
                "Tests pass",
                "Documentation updated",
            ]
            
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name="feature/test",
                acceptance_criteria=acceptance_criteria,
            )
            
            assert pr == sample_pr
    
    def test_create_pr_with_draft(self, github_config, sample_task, sample_pr):
        """Test PR creation as draft."""
        github_config.draft.enabled = True
        github_config.draft.create_as_draft = True
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name="feature/test",
            )
            
            # Verify draft parameter was passed
            call_args = mock_client.create_pull_request.call_args
            assert call_args[1]['draft'] == True
    
    def test_create_pr_failure(self, github_config, sample_task):
        """Test PR creation failure."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.side_effect = Exception("API Error")
            
            pr_service = PRService(github_config)
            
            with pytest.raises(PRCreationError):
                pr_service.create_pr(
                    task=sample_task,
                    branch_name="feature/test",
                )


class TestPRUpdate:
    """Test PR update functionality."""
    
    def test_update_pr_description(self, github_config, sample_pr):
        """Test updating PR description."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_pr.return_value = sample_pr
            
            pr_service = PRService(github_config)
            
            updates = {
                "execution_time": 45.2,
                "test_results": {
                    "total": 10,
                    "passed": 9,
                    "failed": 1,
                },
            }
            
            pr_service.update_pr_description("12345", updates)
            
            # Verify update was called
            mock_client.update_pr_description.assert_called_once()
            
            # Verify updated description contains the updates
            call_args = mock_client.update_pr_description.call_args
            updated_desc = call_args[0][1]
            assert "Execution Time" in updated_desc
            assert "45.2" in updated_desc
            assert "Test Results Update" in updated_desc
    
    def test_update_pr_with_logs(self, github_config, sample_pr):
        """Test updating PR with execution logs."""
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get_pr.return_value = sample_pr
            
            pr_service = PRService(github_config)
            
            updates = {
                "execution_logs": [
                    {"name": "Build Log", "url": "https://example.com/build.log"},
                    {"name": "Test Log", "url": "https://example.com/test.log"},
                ],
            }
            
            pr_service.update_pr_description("12345", updates)
            
            # Verify logs were added
            call_args = mock_client.update_pr_description.call_args
            updated_desc = call_args[0][1]
            assert "Execution Logs" in updated_desc
            assert "Build Log" in updated_desc
            assert "Test Log" in updated_desc


class TestLabelManagement:
    """Test label management functionality."""
    
    def test_apply_labels_based_on_task_type(self, github_config, sample_task, sample_pr):
        """Test applying labels based on task type."""
        github_config.labels.enabled = True
        github_config.labels.rules = {
            "backend": ["backend", "api"],
            "frontend": ["frontend", "ui"],
        }
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify labels were applied
            mock_client.add_labels.assert_called_once()
            call_args = mock_client.add_labels.call_args
            labels = call_args[0][1]
            assert "backend" in labels or "api" in labels
    
    def test_apply_priority_labels(self, github_config, sample_task, sample_pr):
        """Test applying priority labels."""
        github_config.labels.enabled = True
        github_config.labels.priority_labels = True
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify priority label was applied
            call_args = mock_client.add_labels.call_args
            labels = call_args[0][1]
            assert any("priority" in label for label in labels)
    
    def test_labels_disabled(self, github_config, sample_task, sample_pr):
        """Test that labels are not applied when disabled."""
        github_config.labels.enabled = False
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify labels were not applied
            mock_client.add_labels.assert_not_called()


class TestReviewerAssignment:
    """Test reviewer assignment functionality."""
    
    def test_assign_reviewers_from_task(self, github_config, sample_task, sample_pr):
        """Test assigning reviewers from task metadata."""
        github_config.reviewers.enabled = True
        sample_task.metadata["reviewers"] = ["reviewer1", "reviewer2"]
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify reviewers were assigned
            mock_client.assign_reviewers.assert_called_once()
            call_args = mock_client.assign_reviewers.call_args
            reviewers = call_args[0][1]
            assert "reviewer1" in reviewers
            assert "reviewer2" in reviewers
    
    def test_assign_default_reviewers(self, github_config, sample_task, sample_pr):
        """Test assigning default reviewers."""
        github_config.reviewers.enabled = True
        github_config.reviewers.default_reviewers = ["default1", "default2"]
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify default reviewers were assigned
            call_args = mock_client.assign_reviewers.call_args
            reviewers = call_args[0][1]
            assert "default1" in reviewers or "default2" in reviewers
    
    def test_skip_reviewers_for_draft(self, github_config, sample_task, sample_pr):
        """Test skipping reviewer assignment for draft PRs."""
        github_config.reviewers.enabled = True
        github_config.reviewers.skip_draft_prs = True
        github_config.draft.enabled = True
        github_config.draft.create_as_draft = True
        
        sample_pr.draft = True
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify reviewers were not assigned
            mock_client.assign_reviewers.assert_not_called()
    
    def test_reviewers_disabled(self, github_config, sample_task, sample_pr):
        """Test that reviewers are not assigned when disabled."""
        github_config.reviewers.enabled = False
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify reviewers were not assigned
            mock_client.assign_reviewers.assert_not_called()


class TestTaskRegistryIntegration:
    """Test Task Registry integration."""
    
    def test_record_pr_created_event(self, github_config, sample_task, sample_pr, tmp_path):
        """Test recording PR creation event in Task Registry."""
        github_config.task_registry_path = str(tmp_path / "task_registry")
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            
            # Mock the event store
            pr_service.task_registry.event_store.record_event = Mock()
            
            pr_service.create_pr(sample_task, "feature/test")
            
            # Verify event was recorded
            pr_service.task_registry.event_store.record_event.assert_called_once()
            
            # Verify event details
            call_args = pr_service.task_registry.event_store.record_event.call_args
            event = call_args[0][0]
            assert event.details["event"] == "pr_created"
            assert event.details["pr_url"] == sample_pr.url
            assert event.details["pr_number"] == sample_pr.pr_number
    
    def test_no_task_registry_configured(self, github_config, sample_task, sample_pr):
        """Test that PR creation works without Task Registry."""
        github_config.task_registry_path = None
        
        with patch('necrocode.review_pr_service.pr_service.GitHubClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.create_pull_request.return_value = sample_pr
            
            pr_service = PRService(github_config)
            
            # Should not raise exception
            pr = pr_service.create_pr(sample_task, "feature/test")
            assert pr == sample_pr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for Draft PR Functionality

Tests the draft PR features including creation, conversion, and auto-conversion.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    DraftConfig,
    ReviewerConfig,
    LabelConfig
)
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.review_pr_service.exceptions import PRServiceError
from necrocode.task_registry.models import Task


@pytest.fixture
def draft_config():
    """Create a configuration with draft feature enabled."""
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="test-token",
        draft=DraftConfig(
            enabled=True,
            create_as_draft=True,
            convert_on_ci_success=True,
            skip_reviewers=True,
            draft_label="draft"
        ),
        reviewers=ReviewerConfig(
            enabled=True,
            skip_draft_prs=True,
            default_reviewers=["reviewer1", "reviewer2"]
        ),
        labels=LabelConfig(
            enabled=True
        )
    )


@pytest.fixture
def disabled_draft_config():
    """Create a configuration with draft feature disabled."""
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token="test-token",
        draft=DraftConfig(
            enabled=False
        )
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="1.1",
        title="Test task",
        description="Test description",
        dependencies=[],
        metadata={
            "type": "backend",
            "priority": "high"
        }
    )


@pytest.fixture
def draft_pr():
    """Create a sample draft PR."""
    return PullRequest(
        pr_id="123",
        pr_number=1,
        title="Test PR",
        description="Test description",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/owner/repo/pull/1",
        state=PRState.OPEN,
        draft=True,
        created_at=datetime.now(),
        labels=["draft", "backend"]
    )


@pytest.fixture
def ready_pr():
    """Create a sample ready (non-draft) PR."""
    return PullRequest(
        pr_id="124",
        pr_number=2,
        title="Test PR 2",
        description="Test description 2",
        source_branch="feature/test2",
        target_branch="main",
        url="https://github.com/owner/repo/pull/2",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
        labels=["backend"]
    )


class TestDraftPRCreation:
    """Test draft PR creation functionality."""
    
    def test_create_draft_pr_when_enabled(self, draft_config, sample_task):
        """
        Test creating a draft PR when draft feature is enabled.
        
        Requirements: 12.1
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            
            # Mock PR creation
            mock_pr = PullRequest(
                pr_id="123",
                pr_number=1,
                title="Task 1.1: Test task",
                description="Test description",
                source_branch="feature/test",
                target_branch="main",
                url="https://github.com/owner/repo/pull/1",
                state=PRState.OPEN,
                draft=True,
                created_at=datetime.now()
            )
            mock_client.create_pull_request.return_value = mock_pr
            mock_client.add_labels = Mock()
            mock_client.assign_reviewers = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name="feature/test",
                base_branch="main"
            )
            
            # Verify PR was created as draft
            assert pr.draft is True
            mock_client.create_pull_request.assert_called_once()
            call_args = mock_client.create_pull_request.call_args
            assert call_args[1]['draft'] is True
            
            # Verify draft label was added
            mock_client.add_labels.assert_called()
            labels_added = [call[0][1] for call in mock_client.add_labels.call_args_list]
            assert any('draft' in labels for labels in labels_added)
    
    def test_create_ready_pr_when_draft_disabled(self, disabled_draft_config, sample_task):
        """
        Test creating a ready PR when draft feature is disabled.
        
        Requirements: 12.5
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            
            # Mock PR creation
            mock_pr = PullRequest(
                pr_id="124",
                pr_number=2,
                title="Task 1.1: Test task",
                description="Test description",
                source_branch="feature/test",
                target_branch="main",
                url="https://github.com/owner/repo/pull/2",
                state=PRState.OPEN,
                draft=False,
                created_at=datetime.now()
            )
            mock_client.create_pull_request.return_value = mock_pr
            mock_client.add_labels = Mock()
            mock_client.assign_reviewers = Mock()
            
            # Create PR Service
            pr_service = PRService(disabled_draft_config)
            
            # Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name="feature/test",
                base_branch="main"
            )
            
            # Verify PR was created as ready (not draft)
            assert pr.draft is False
            mock_client.create_pull_request.assert_called_once()
            call_args = mock_client.create_pull_request.call_args
            assert call_args[1]['draft'] is False
    
    def test_skip_reviewers_for_draft_pr(self, draft_config, sample_task):
        """
        Test that reviewers are not assigned to draft PRs when configured.
        
        Requirements: 12.3
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            
            # Mock PR creation
            mock_pr = PullRequest(
                pr_id="123",
                pr_number=1,
                title="Task 1.1: Test task",
                description="Test description",
                source_branch="feature/test",
                target_branch="main",
                url="https://github.com/owner/repo/pull/1",
                state=PRState.OPEN,
                draft=True,
                created_at=datetime.now()
            )
            mock_client.create_pull_request.return_value = mock_pr
            mock_client.add_labels = Mock()
            mock_client.assign_reviewers = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Create draft PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name="feature/test",
                base_branch="main"
            )
            
            # Verify reviewers were NOT assigned
            mock_client.assign_reviewers.assert_not_called()


class TestDraftConversion:
    """Test draft PR conversion functionality."""
    
    def test_convert_draft_to_ready(self, draft_config, draft_pr, sample_task):
        """
        Test converting a draft PR to ready for review.
        
        Requirements: 12.2
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = draft_pr
            mock_client.convert_to_ready = Mock()
            mock_client.remove_label = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Convert to ready
            pr_service.convert_draft_to_ready(
                pr_id=draft_pr.pr_id,
                assign_reviewers=False,  # Skip reviewer assignment for this test
                update_labels=True
            )
            
            # Verify conversion was called
            mock_client.convert_to_ready.assert_called_once_with(draft_pr.pr_id)
            
            # Verify draft label was removed
            mock_client.remove_label.assert_called_once_with(draft_pr.pr_id, "draft")
    
    def test_convert_non_draft_pr_skips_conversion(self, draft_config, ready_pr):
        """
        Test that converting a non-draft PR is skipped.
        
        Requirements: 12.2
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = ready_pr
            mock_client.convert_to_ready = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Try to convert (should be skipped)
            pr_service.convert_draft_to_ready(pr_id=ready_pr.pr_id)
            
            # Verify conversion was NOT called
            mock_client.convert_to_ready.assert_not_called()
    
    def test_convert_draft_when_feature_disabled(self, disabled_draft_config, draft_pr):
        """
        Test that conversion is skipped when draft feature is disabled.
        
        Requirements: 12.5
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = draft_pr
            mock_client.convert_to_ready = Mock()
            
            # Create PR Service
            pr_service = PRService(disabled_draft_config)
            
            # Try to convert (should be skipped)
            pr_service.convert_draft_to_ready(pr_id=draft_pr.pr_id)
            
            # Verify conversion was NOT called
            mock_client.convert_to_ready.assert_not_called()


class TestAutoConversionOnCISuccess:
    """Test automatic draft conversion when CI succeeds."""
    
    def test_auto_convert_on_ci_success(self, draft_config, draft_pr):
        """
        Test automatic conversion of draft PR when CI succeeds.
        
        Requirements: 12.2
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = draft_pr
            mock_client.get_ci_status.return_value = CIStatus.SUCCESS
            mock_client.convert_to_ready = Mock()
            mock_client.remove_label = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Trigger auto-conversion
            result = pr_service.convert_draft_on_ci_success(draft_pr.pr_id)
            
            # Verify conversion occurred
            assert result is True
            mock_client.convert_to_ready.assert_called_once()
    
    def test_no_auto_convert_when_ci_not_success(self, draft_config, draft_pr):
        """
        Test that auto-conversion does not occur when CI is not successful.
        
        Requirements: 12.2
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = draft_pr
            mock_client.get_ci_status.return_value = CIStatus.PENDING
            mock_client.convert_to_ready = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Trigger auto-conversion
            result = pr_service.convert_draft_on_ci_success(draft_pr.pr_id)
            
            # Verify conversion did NOT occur
            assert result is False
            mock_client.convert_to_ready.assert_not_called()
    
    def test_no_auto_convert_for_ready_pr(self, draft_config, ready_pr):
        """
        Test that auto-conversion is skipped for non-draft PRs.
        
        Requirements: 12.2
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = ready_pr
            mock_client.get_ci_status.return_value = CIStatus.SUCCESS
            mock_client.convert_to_ready = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Trigger auto-conversion
            result = pr_service.convert_draft_on_ci_success(ready_pr.pr_id)
            
            # Verify conversion did NOT occur
            assert result is False
            mock_client.convert_to_ready.assert_not_called()
    
    def test_auto_convert_disabled_in_config(self, draft_pr):
        """
        Test that auto-conversion is skipped when disabled in config.
        
        Requirements: 12.5
        """
        # Create config with auto-conversion disabled
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            repository="owner/repo",
            api_token="test-token",
            draft=DraftConfig(
                enabled=True,
                convert_on_ci_success=False  # Disabled
            )
        )
        
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.get_pr.return_value = draft_pr
            mock_client.convert_to_ready = Mock()
            
            # Create PR Service
            pr_service = PRService(config)
            
            # Trigger auto-conversion
            result = pr_service.convert_draft_on_ci_success(draft_pr.pr_id)
            
            # Verify conversion did NOT occur
            assert result is False
            mock_client.convert_to_ready.assert_not_called()


class TestDraftPRHandling:
    """Test special handling for draft PRs."""
    
    def test_draft_label_added(self, draft_config, draft_pr, sample_task):
        """
        Test that draft label is added to draft PRs.
        
        Requirements: 12.4
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.add_labels = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Handle draft PR creation
            pr_service.handle_draft_pr_creation(draft_pr, sample_task)
            
            # Verify draft label was added
            mock_client.add_labels.assert_called_once()
            call_args = mock_client.add_labels.call_args
            assert "draft" in call_args[0][1]
    
    def test_draft_handling_skipped_when_disabled(self, disabled_draft_config, draft_pr, sample_task):
        """
        Test that draft handling is skipped when feature is disabled.
        
        Requirements: 12.5
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.add_labels = Mock()
            
            # Create PR Service
            pr_service = PRService(disabled_draft_config)
            
            # Handle draft PR creation (should be skipped)
            pr_service.handle_draft_pr_creation(draft_pr, sample_task)
            
            # Verify no labels were added
            mock_client.add_labels.assert_not_called()
    
    def test_draft_handling_skipped_for_ready_pr(self, draft_config, ready_pr, sample_task):
        """
        Test that draft handling is skipped for non-draft PRs.
        
        Requirements: 12.3
        """
        with patch.object(PRService, '_create_git_host_client') as mock_client_factory:
            # Setup mock client
            mock_client = Mock()
            mock_client_factory.return_value = mock_client
            mock_client.add_labels = Mock()
            
            # Create PR Service
            pr_service = PRService(draft_config)
            
            # Handle PR creation (should be skipped for non-draft)
            pr_service.handle_draft_pr_creation(ready_pr, sample_task)
            
            # Verify no labels were added
            mock_client.add_labels.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

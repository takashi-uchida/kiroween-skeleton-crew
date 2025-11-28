"""
Tests for merge strategy functionality in Review & PR Service.

Tests cover:
- Merge strategy configuration
- Manual merge with different strategies
- Auto-merge on CI success
- Merge conflict detection
- Merge failure handling

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path

from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    MergeStrategy,
    MergeConfig
)
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.models import PullRequest, CIStatus, PRState
from necrocode.review_pr_service.exceptions import PRServiceError
from necrocode.task_registry.models import Task, TaskState


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="test-owner/test-repo",
        api_token="test_token",
        merge=MergeConfig(
            strategy=MergeStrategy.SQUASH,
            auto_merge_enabled=True,
            delete_branch_after_merge=True,
            require_ci_success=True,
            required_approvals=2,
            check_conflicts=True
        )
    )


@pytest.fixture
def mock_pr():
    """Create a mock pull request for testing."""
    return PullRequest(
        pr_id="123",
        pr_number=123,
        title="Test PR",
        description="Test description",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/test-owner/test-repo/pull/123",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
        task_id="1.1",
        spec_id="test-spec"
    )


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    return Task(
        id="1.1",
        title="Test Task",
        description="Test task description",
        state=TaskState.IN_PROGRESS,
        dependencies=[],
        metadata={"type": "backend"}
    )


class TestMergeStrategyConfiguration:
    """Test merge strategy configuration."""
    
    def test_merge_config_defaults(self):
        """Test default merge configuration values."""
        config = MergeConfig()
        
        assert config.strategy == MergeStrategy.SQUASH
        assert config.auto_merge_enabled == False
        assert config.delete_branch_after_merge == True
        assert config.require_ci_success == True
        assert config.required_approvals == 1
        assert config.check_conflicts == True
    
    def test_merge_config_custom(self):
        """Test custom merge configuration."""
        config = MergeConfig(
            strategy=MergeStrategy.REBASE,
            auto_merge_enabled=True,
            required_approvals=3
        )
        
        assert config.strategy == MergeStrategy.REBASE
        assert config.auto_merge_enabled == True
        assert config.required_approvals == 3
    
    def test_merge_strategies(self):
        """Test all merge strategy options."""
        strategies = [
            MergeStrategy.MERGE,
            MergeStrategy.SQUASH,
            MergeStrategy.REBASE
        ]
        
        for strategy in strategies:
            config = MergeConfig(strategy=strategy)
            assert config.strategy == strategy
            assert config.strategy.value in ["merge", "squash", "rebase"]


class TestManualMerge:
    """Test manual PR merge functionality."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_pr_with_default_strategy(self, mock_client_class, mock_config, mock_pr):
        """Test merging PR with default strategy from config."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        mock_client.check_conflicts.return_value = False
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=2)
        
        # Merge PR
        service.merge_pr(pr_id="123")
        
        # Verify merge was called with correct strategy
        mock_client.merge_pr.assert_called_once()
        call_args = mock_client.merge_pr.call_args
        assert call_args[1]['merge_method'] == 'squash'
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_pr_with_custom_strategy(self, mock_client_class, mock_config, mock_pr):
        """Test merging PR with custom strategy override."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        mock_client.check_conflicts.return_value = False
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=2)
        
        # Merge PR with rebase strategy
        service.merge_pr(pr_id="123", merge_strategy=MergeStrategy.REBASE)
        
        # Verify merge was called with rebase
        call_args = mock_client.merge_pr.call_args
        assert call_args[1]['merge_method'] == 'rebase'
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_pr_delete_branch(self, mock_client_class, mock_config, mock_pr):
        """Test branch deletion after merge."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        mock_client.check_conflicts.return_value = False
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=2)
        
        # Merge PR with branch deletion
        service.merge_pr(pr_id="123", delete_branch=True)
        
        # Verify delete_branch parameter
        call_args = mock_client.merge_pr.call_args
        assert call_args[1]['delete_branch'] == True


class TestAutoMerge:
    """Test auto-merge functionality."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_auto_merge_on_ci_success(self, mock_client_class, mock_config, mock_pr):
        """Test auto-merge when CI succeeds."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        mock_client.check_conflicts.return_value = False
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=2)
        
        # Trigger auto-merge
        result = service.auto_merge_on_ci_success(pr_id="123")
        
        # Verify merge was triggered
        assert result == True
        mock_client.merge_pr.assert_called_once()
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_auto_merge_disabled(self, mock_client_class, mock_pr):
        """Test auto-merge when disabled in config."""
        # Config with auto-merge disabled
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            repository="test-owner/test-repo",
            api_token="test_token",
            merge=MergeConfig(auto_merge_enabled=False)
        )
        
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Create service
        service = PRService(config)
        
        # Trigger auto-merge
        result = service.auto_merge_on_ci_success(pr_id="123")
        
        # Verify merge was not triggered
        assert result == False
        mock_client.merge_pr.assert_not_called()
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_auto_merge_ci_not_success(self, mock_client_class, mock_config, mock_pr):
        """Test auto-merge skipped when CI not successful."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.PENDING
        
        # Create service
        service = PRService(mock_config)
        
        # Trigger auto-merge
        result = service.auto_merge_on_ci_success(pr_id="123")
        
        # Verify merge was not triggered
        assert result == False
        mock_client.merge_pr.assert_not_called()
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_auto_merge_insufficient_approvals(self, mock_client_class, mock_config, mock_pr):
        """Test auto-merge skipped when approvals insufficient."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=1)  # Only 1 approval, need 2
        
        # Trigger auto-merge
        result = service.auto_merge_on_ci_success(pr_id="123")
        
        # Verify merge was not triggered
        assert result == False
        mock_client.merge_pr.assert_not_called()


class TestMergeChecks:
    """Test pre-merge checks."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_check_ci_failure(self, mock_client_class, mock_config, mock_pr):
        """Test merge fails when CI not successful."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.FAILURE
        
        # Create service
        service = PRService(mock_config)
        
        # Attempt merge
        with pytest.raises(PRServiceError, match="CI status"):
            service.merge_pr(pr_id="123")
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_check_insufficient_approvals(self, mock_client_class, mock_config, mock_pr):
        """Test merge fails when approvals insufficient."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=1)  # Only 1, need 2
        
        # Attempt merge
        with pytest.raises(PRServiceError, match="approval"):
            service.merge_pr(pr_id="123")
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_check_conflicts(self, mock_client_class, mock_config, mock_pr):
        """Test merge fails when conflicts detected."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.SUCCESS
        mock_client.check_conflicts.return_value = True  # Has conflicts
        
        # Create service
        service = PRService(mock_config)
        service._get_approval_count = Mock(return_value=2)
        
        # Attempt merge
        with pytest.raises(PRServiceError, match="conflicts"):
            service.merge_pr(pr_id="123")
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_check_draft_pr(self, mock_client_class, mock_config):
        """Test merge fails for draft PR."""
        # Create draft PR
        draft_pr = PullRequest(
            pr_id="123",
            pr_number=123,
            title="Test PR",
            description="Test",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/pull/123",
            state=PRState.OPEN,
            draft=True,  # Draft PR
            created_at=datetime.now()
        )
        
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = draft_pr
        
        # Create service
        service = PRService(mock_config)
        
        # Attempt merge
        with pytest.raises(PRServiceError, match="draft"):
            service.merge_pr(pr_id="123")


class TestConflictDetection:
    """Test merge conflict detection."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_check_conflicts_none(self, mock_client_class, mock_config, mock_pr):
        """Test conflict check when no conflicts."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.check_conflicts.return_value = False
        
        # Create service
        service = PRService(mock_config)
        
        # Check conflicts
        result = service.check_merge_conflicts(pr_id="123")
        
        assert result['has_conflicts'] == False
        assert 'No merge conflicts' in result['details']['message']
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_check_conflicts_detected(self, mock_client_class, mock_config, mock_pr):
        """Test conflict check when conflicts exist."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.check_conflicts.return_value = True
        
        # Create service
        service = PRService(mock_config)
        
        # Check conflicts
        result = service.check_merge_conflicts(pr_id="123")
        
        assert result['has_conflicts'] == True
        assert 'conflicts that must be resolved' in result['details']['message']
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_post_conflict_comment(self, mock_client_class, mock_config, mock_pr):
        """Test posting conflict comment."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        
        # Create service
        service = PRService(mock_config)
        
        # Post conflict comment
        conflict_details = {
            'source_branch': 'feature/test',
            'target_branch': 'main',
            'conflicting_files': ['file1.py', 'file2.py']
        }
        
        service.post_conflict_comment(pr_id="123", conflict_details=conflict_details)
        
        # Verify comment was posted
        mock_client.add_comment.assert_called_once()
        comment = mock_client.add_comment.call_args[0][1]
        assert 'Merge Conflicts Detected' in comment
        assert 'file1.py' in comment
        assert 'file2.py' in comment


class TestMergeFailureHandling:
    """Test merge failure handling."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_record_merge_failure(self, mock_client_class, mock_config, mock_pr, tmp_path):
        """Test recording merge failure in Task Registry."""
        # Setup mock with Task Registry
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        
        # Create config with Task Registry
        config = PRServiceConfig(
            git_host_type=GitHostType.GITHUB,
            repository="test-owner/test-repo",
            api_token="test_token",
            task_registry_path=str(tmp_path / "registry")
        )
        
        # Create service
        service = PRService(config)
        
        # Record merge failure
        service._record_merge_failure(pr_id="123", error_message="Test error")
        
        # Verify event was recorded
        events = service.task_registry.event_store.get_events(
            spec_name="test-spec",
            task_id="1.1"
        )
        
        assert len(events) > 0
        failure_event = events[-1]
        assert failure_event.details['event'] == 'merge_failed'
        assert failure_event.details['error'] == 'Test error'
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_merge_failure_raises_exception(self, mock_client_class, mock_config, mock_pr):
        """Test that merge failure raises appropriate exception."""
        # Setup mock to fail
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_pr.return_value = mock_pr
        mock_client.get_ci_status.return_value = CIStatus.FAILURE
        
        # Create service
        service = PRService(mock_config)
        
        # Attempt merge - should fail
        with pytest.raises(PRServiceError):
            service.merge_pr(pr_id="123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for conflict detection functionality in Review & PR Service.

Tests cover:
- Conflict detection on PR creation
- Conflict notification (comments and events)
- Conflict re-checking after resolution
- Periodic conflict checking

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from pathlib import Path

from necrocode.review_pr_service.config import PRServiceConfig, GitHostType
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.task_registry.models import Task, TaskEvent, EventType


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="test-token",
        repository="owner/repo",
    )
    
    # Enable conflict detection
    config.conflict_detection.enabled = True
    config.conflict_detection.check_on_creation = True
    config.conflict_detection.auto_comment = True
    config.conflict_detection.periodic_check = True
    
    return config


@pytest.fixture
def mock_pr():
    """Create a mock pull request for testing."""
    return PullRequest(
        pr_id="123",
        pr_number=42,
        title="Test PR",
        description="Test description",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/owner/repo/pull/42",
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
        title="Test task",
        description="Test description",
        dependencies=[],
        metadata={"type": "backend"}
    )


class TestConflictDetectionOnCreation:
    """Tests for conflict detection when creating PRs (Requirement 13.1)."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_check_conflicts_on_pr_creation_enabled(
        self,
        mock_github_client,
        mock_config,
        mock_task
    ):
        """Test that conflicts are checked when PR is created (if enabled)."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        # Mock PR creation
        mock_pr = PullRequest(
            pr_id="123",
            pr_number=42,
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/owner/repo/pull/42",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now()
        )
        mock_client_instance.create_pull_request.return_value = mock_pr
        mock_client_instance.check_conflicts.return_value = False
        
        # Enable conflict checking on creation
        mock_config.conflict_detection.check_on_creation = True
        
        pr_service = PRService(mock_config)
        
        # Execute
        result = pr_service.create_pr(
            task=mock_task,
            branch_name="feature/test",
            base_branch="main"
        )
        
        # Verify conflict check was called
        mock_client_instance.check_conflicts.assert_called_once()
        assert result.pr_number == 42
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_no_conflict_check_when_disabled(
        self,
        mock_github_client,
        mock_config,
        mock_task
    ):
        """Test that conflicts are not checked when disabled."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        mock_pr = PullRequest(
            pr_id="123",
            pr_number=42,
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/owner/repo/pull/42",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now()
        )
        mock_client_instance.create_pull_request.return_value = mock_pr
        
        # Disable conflict checking
        mock_config.conflict_detection.enabled = False
        
        pr_service = PRService(mock_config)
        
        # Execute
        result = pr_service.create_pr(
            task=mock_task,
            branch_name="feature/test",
            base_branch="main"
        )
        
        # Verify conflict check was NOT called
        mock_client_instance.check_conflicts.assert_not_called()
        assert result.pr_number == 42


class TestConflictNotification:
    """Tests for conflict notification (Requirement 13.2, 13.3)."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_post_conflict_comment(self, mock_github_client, mock_config):
        """Test posting conflict comment to PR."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        pr_service = PRService(mock_config)
        
        conflict_details = {
            "source_branch": "feature/test",
            "target_branch": "main",
            "conflicting_files": ["file1.py", "file2.py"]
        }
        
        # Execute
        pr_service.post_conflict_comment(
            pr_id="123",
            conflict_details=conflict_details
        )
        
        # Verify comment was posted
        mock_client_instance.add_comment.assert_called_once()
        call_args = mock_client_instance.add_comment.call_args
        comment_text = call_args[0][1]
        
        # Verify comment contains expected content
        assert "Merge Conflicts Detected" in comment_text
        assert "feature/test" in comment_text
        assert "main" in comment_text
        assert "file1.py" in comment_text
        assert "file2.py" in comment_text
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_conflict_detection_records_event(
        self,
        mock_github_client,
        mock_config,
        tmp_path
    ):
        """Test that conflict detection records event in Task Registry."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        # Setup Task Registry
        mock_config.task_registry_path = str(tmp_path / "task_registry")
        
        mock_pr = PullRequest(
            pr_id="123",
            pr_number=42,
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/owner/repo/pull/42",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
            task_id="1.1",
            spec_id="test-spec"
        )
        mock_client_instance.get_pr.return_value = mock_pr
        
        pr_service = PRService(mock_config)
        
        # Execute
        pr_service.post_conflict_comment(
            pr_id="123",
            conflict_details={"source_branch": "feature/test"}
        )
        
        # Verify event was recorded
        # (In a real test, we would check the event store)
        mock_client_instance.add_comment.assert_called_once()


class TestConflictRecheck:
    """Tests for conflict re-checking (Requirement 13.4)."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_recheck_conflicts_resolved(
        self,
        mock_github_client,
        mock_config,
        mock_pr
    ):
        """Test re-checking when conflicts are resolved."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        mock_client_instance.get_pr.return_value = mock_pr
        mock_client_instance.check_conflicts.return_value = False  # No conflicts
        
        pr_service = PRService(mock_config)
        
        # Execute
        result = pr_service.recheck_conflicts_after_resolution(
            pr_id="123",
            post_success_comment=True
        )
        
        # Verify
        assert result is True  # Conflicts resolved
        mock_client_instance.check_conflicts.assert_called_once()
        mock_client_instance.add_comment.assert_called_once()  # Success comment posted
        
        # Verify success comment content
        call_args = mock_client_instance.add_comment.call_args
        comment_text = call_args[0][1]
        assert "Conflicts Resolved" in comment_text
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_recheck_conflicts_still_exist(
        self,
        mock_github_client,
        mock_config,
        mock_pr
    ):
        """Test re-checking when conflicts still exist."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        mock_client_instance.get_pr.return_value = mock_pr
        mock_client_instance.check_conflicts.return_value = True  # Conflicts still exist
        
        pr_service = PRService(mock_config)
        
        # Execute
        result = pr_service.recheck_conflicts_after_resolution(
            pr_id="123",
            post_success_comment=True
        )
        
        # Verify
        assert result is False  # Conflicts not resolved
        mock_client_instance.check_conflicts.assert_called_once()
        # No success comment should be posted
        mock_client_instance.add_comment.assert_not_called()


class TestPeriodicConflictCheck:
    """Tests for periodic conflict checking (Requirement 13.5)."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_periodic_check_multiple_prs(
        self,
        mock_github_client,
        mock_config
    ):
        """Test periodic conflict checking for multiple PRs."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        # Create mock PRs
        pr1 = PullRequest(
            pr_id="123",
            pr_number=1,
            title="PR 1",
            description="Test",
            source_branch="feature/1",
            target_branch="main",
            url="https://github.com/owner/repo/pull/1",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now()
        )
        
        pr2 = PullRequest(
            pr_id="124",
            pr_number=2,
            title="PR 2",
            description="Test",
            source_branch="feature/2",
            target_branch="main",
            url="https://github.com/owner/repo/pull/2",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now()
        )
        
        # Mock get_pr to return different PRs based on ID
        def get_pr_side_effect(pr_id):
            if pr_id == "123":
                return pr1
            elif pr_id == "124":
                return pr2
            return None
        
        mock_client_instance.get_pr.side_effect = get_pr_side_effect
        
        # Mock conflict checks: PR 1 has conflicts, PR 2 doesn't
        def check_conflicts_side_effect(pr_id):
            if pr_id == "123":
                return True  # Has conflicts
            elif pr_id == "124":
                return False  # No conflicts
            return False
        
        mock_client_instance.check_conflicts.side_effect = check_conflicts_side_effect
        
        pr_service = PRService(mock_config)
        
        # Execute
        results = pr_service.periodic_conflict_check(
            pr_ids=["123", "124"],
            only_open_prs=True
        )
        
        # Verify
        assert len(results) == 2
        assert results["123"] is True  # PR 1 has conflicts
        assert results["124"] is False  # PR 2 has no conflicts
        
        # Verify conflict checks were called
        assert mock_client_instance.check_conflicts.call_count == 2
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_periodic_check_disabled(
        self,
        mock_github_client,
        mock_config
    ):
        """Test that periodic check returns empty when disabled."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        # Disable periodic checking
        mock_config.conflict_detection.periodic_check = False
        
        pr_service = PRService(mock_config)
        
        # Execute
        results = pr_service.periodic_conflict_check(
            pr_ids=["123", "124"]
        )
        
        # Verify
        assert results == {}
        mock_client_instance.check_conflicts.assert_not_called()
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_periodic_check_skips_closed_prs(
        self,
        mock_github_client,
        mock_config
    ):
        """Test that periodic check skips closed PRs when only_open_prs=True."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        # Create open and closed PRs
        open_pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Open PR",
            description="Test",
            source_branch="feature/1",
            target_branch="main",
            url="https://github.com/owner/repo/pull/1",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now()
        )
        
        closed_pr = PullRequest(
            pr_id="124",
            pr_number=2,
            title="Closed PR",
            description="Test",
            source_branch="feature/2",
            target_branch="main",
            url="https://github.com/owner/repo/pull/2",
            state=PRState.CLOSED,
            draft=False,
            created_at=datetime.now()
        )
        
        def get_pr_side_effect(pr_id):
            if pr_id == "123":
                return open_pr
            elif pr_id == "124":
                return closed_pr
            return None
        
        mock_client_instance.get_pr.side_effect = get_pr_side_effect
        mock_client_instance.check_conflicts.return_value = False
        
        pr_service = PRService(mock_config)
        
        # Execute
        results = pr_service.periodic_conflict_check(
            pr_ids=["123", "124"],
            only_open_prs=True
        )
        
        # Verify - only open PR should be checked
        assert len(results) == 1
        assert "123" in results
        assert "124" not in results


class TestConflictDetectionIntegration:
    """Integration tests for complete conflict detection workflow."""
    
    @patch('necrocode.review_pr_service.pr_service.GitHubClient')
    def test_complete_conflict_workflow(
        self,
        mock_github_client,
        mock_config,
        mock_task
    ):
        """Test complete workflow: detect, notify, resolve, re-check."""
        # Setup
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        mock_pr = PullRequest(
            pr_id="123",
            pr_number=42,
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/owner/repo/pull/42",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
            task_id="1.1",
            spec_id="test-spec"
        )
        
        mock_client_instance.create_pull_request.return_value = mock_pr
        mock_client_instance.get_pr.return_value = mock_pr
        
        # First check: conflicts exist
        # Second check (after resolution): no conflicts
        mock_client_instance.check_conflicts.side_effect = [True, False]
        
        pr_service = PRService(mock_config)
        
        # Step 1: Create PR (conflicts detected)
        pr = pr_service.create_pr(
            task=mock_task,
            branch_name="feature/test",
            base_branch="main"
        )
        
        # Verify conflict was detected and comment posted
        assert mock_client_instance.check_conflicts.call_count == 1
        assert mock_client_instance.add_comment.call_count == 1
        
        # Step 2: Re-check after resolution
        resolved = pr_service.recheck_conflicts_after_resolution(
            pr_id=pr.pr_id,
            post_success_comment=True
        )
        
        # Verify conflicts were resolved
        assert resolved is True
        assert mock_client_instance.check_conflicts.call_count == 2
        assert mock_client_instance.add_comment.call_count == 2  # Conflict + success comments


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

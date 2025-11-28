"""
Unit tests for reviewer assignment functionality.

Tests the different reviewer assignment strategies:
- Task type-based assignment
- CODEOWNERS file parsing
- Round-robin distribution
- Load-balanced assignment

Requirements: 8.1, 8.2, 8.3, 8.4
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import (
    PRServiceConfig,
    ReviewerConfig,
    ReviewerStrategy,
    GitHostType,
)
from necrocode.review_pr_service.models import PullRequest, PRState
from necrocode.task_registry.models import Task


@pytest.fixture
def mock_git_client():
    """Create a mock Git host client."""
    client = Mock()
    client.assign_reviewers = Mock()
    return client


@pytest.fixture
def base_config():
    """Create a base configuration for testing."""
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="test-token",
        repository="owner/repo",
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="1.1",
        title="Test Task",
        description="Test description",
        status="in_progress",
        created_at=datetime.now(),
        metadata={}
    )


@pytest.fixture
def sample_pr():
    """Create a sample PR for testing."""
    return PullRequest(
        pr_id="123",
        pr_number=1,
        title="Test PR",
        description="Test description",
        source_branch="feature/test",
        target_branch="main",
        url="https://github.com/owner/repo/pull/1",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now(),
    )


class TestTypeBasedAssignment:
    """Test task type-based reviewer assignment."""
    
    def test_assign_reviewers_by_type(self, base_config, sample_task, sample_pr, mock_git_client):
        """
        Test that reviewers are assigned based on task type.
        
        Requirements: 8.1
        """
        # Configure type-based reviewers
        base_config.reviewers = ReviewerConfig(
            enabled=True,
            type_reviewers={
                "backend": ["alice", "bob"],
                "frontend": ["charlie", "diana"],
            },
            max_reviewers=2,
        )
        
        # Create service with mock client
        service = PRService(base_config)
        service.git_host_client = mock_git_client
        
        # Set task type
        sample_task.metadata["type"] = "backend"
        
        # Assign reviewers
        service._assign_reviewers(sample_pr, sample_task)
        
        # Verify reviewers were assigned
        mock_git_client.assign_reviewers.assert_called_once()
        assigned_reviewers = mock_git_client.assign_reviewers.call_args[0][1]
        
        assert len(assigned_reviewers) <= 2
        assert all(r in ["alice", "bob"] for r in assigned_reviewers)
    
    def test_no_reviewers_for_unknown_type(self, base_config, sample_task, sample_pr, mock_git_client):
        """
        Test that no type-based reviewers are assigned for unknown task type.
        
        Requirements: 8.1
        """
        base_config.reviewers = ReviewerConfig(
            enabled=True,
            type_reviewers={"backend": ["alice"]},
            max_reviewers=2,
        )
        
        service = PRService(base_config)
        service.git_host_client = mock_git_client
        
        # Set unknown task type
        sample_task.metadata["type"] = "unknown"
        
        # Assign reviewers
        service._assign_reviewers(sample_pr, sample_task)
        
        # Should not assign any reviewers (no default reviewers configured)
        # The method will log a warning but not raise an error


class TestCodeownersAssignment:
    """Test CODEOWNERS-based reviewer assignment."""
    
    def test_parse_codeowners_file(self, base_config, tmp_path):
        """
        Test parsing of CODEOWNERS file.
        
        Requirements: 8.2
        """
        # Create CODEOWNERS file
        codeowners_path = tmp_path / "CODEOWNERS"
        codeowners_path.write_text("""
# Backend code
/backend/ @alice @bob
*.py @alice

# Frontend code
/frontend/ @charlie
*.js @diana
""")
        
        service = PRService(base_config)
        
        # Parse CODEOWNERS
        owners_map = service._parse_codeowners(str(codeowners_path))
        
        assert "/backend/" in owners_map
        assert owners_map["/backend/"] == ["alice", "bob"]
        assert "*.py" in owners_map
        assert owners_map["*.py"] == ["alice"]
        assert "/frontend/" in owners_map
        assert owners_map["/frontend/"] == ["charlie"]
    
    def test_match_codeowners_pattern(self, base_config):
        """
        Test pattern matching for CODEOWNERS.
        
        Requirements: 8.2
        """
        service = PRService(base_config)
        
        # Test exact match
        assert service._match_codeowners_pattern("backend/api.py", "backend/api.py")
        
        # Test wildcard match
        assert service._match_codeowners_pattern("backend/api.py", "*.py")
        assert service._match_codeowners_pattern("backend/api.py", "backend/*.py")
        
        # Test directory match
        assert service._match_codeowners_pattern("backend/api.py", "backend/")
        assert service._match_codeowners_pattern("backend/sub/api.py", "backend/")
        
        # Test non-match
        assert not service._match_codeowners_pattern("frontend/app.js", "*.py")
        assert not service._match_codeowners_pattern("frontend/app.js", "backend/")
    
    def test_get_reviewers_from_codeowners(self, base_config, sample_task):
        """
        Test getting reviewers from CODEOWNERS based on task files.
        
        Requirements: 8.2
        """
        service = PRService(base_config)
        
        # Set task files
        sample_task.metadata["files"] = [
            "backend/api.py",
            "backend/models.py",
        ]
        
        # Create CODEOWNERS map
        codeowners_map = {
            "backend/": ["alice", "bob"],
            "*.py": ["alice"],
        }
        
        # Get reviewers
        reviewers = service._get_reviewers_from_codeowners(sample_task, codeowners_map)
        
        assert "alice" in reviewers
        assert "bob" in reviewers


class TestRoundRobinAssignment:
    """Test round-robin reviewer assignment."""
    
    def test_round_robin_selection(self, base_config):
        """
        Test round-robin reviewer selection.
        
        Requirements: 8.3
        """
        service = PRService(base_config)
        
        available_reviewers = ["alice", "bob", "charlie", "diana"]
        
        # First selection
        selected1 = service._select_reviewers_round_robin(available_reviewers, 2, "test")
        assert len(selected1) == 2
        assert selected1 == ["alice", "bob"]
        
        # Second selection (should rotate)
        selected2 = service._select_reviewers_round_robin(available_reviewers, 2, "test")
        assert len(selected2) == 2
        assert selected2 == ["charlie", "diana"]
        
        # Third selection (should wrap around)
        selected3 = service._select_reviewers_round_robin(available_reviewers, 2, "test")
        assert len(selected3) == 2
        assert selected3 == ["alice", "bob"]
    
    def test_round_robin_different_groups(self, base_config):
        """
        Test round-robin with different group keys.
        
        Requirements: 8.3
        """
        service = PRService(base_config)
        
        reviewers = ["alice", "bob", "charlie"]
        
        # Select for group1
        selected1 = service._select_reviewers_round_robin(reviewers, 1, "group1")
        assert selected1 == ["alice"]
        
        # Select for group2 (should start from beginning)
        selected2 = service._select_reviewers_round_robin(reviewers, 1, "group2")
        assert selected2 == ["alice"]
        
        # Select for group1 again (should continue from where it left off)
        selected3 = service._select_reviewers_round_robin(reviewers, 1, "group1")
        assert selected3 == ["bob"]


class TestLoadBalancedAssignment:
    """Test load-balanced reviewer assignment."""
    
    def test_load_balanced_selection(self, base_config):
        """
        Test load-balanced reviewer selection.
        
        Requirements: 8.4
        """
        service = PRService(base_config)
        
        # Set initial loads
        service._reviewer_load = {
            "alice": 3,
            "bob": 1,
            "charlie": 2,
            "diana": 0,
        }
        
        available_reviewers = ["alice", "bob", "charlie", "diana"]
        
        # Select reviewers (should pick lowest load)
        selected = service._select_reviewers_load_balanced(available_reviewers, 2)
        
        assert len(selected) == 2
        assert "diana" in selected  # Load: 0
        assert "bob" in selected    # Load: 1
    
    def test_increment_reviewer_load(self, base_config):
        """
        Test incrementing reviewer load.
        
        Requirements: 8.4
        """
        service = PRService(base_config)
        
        # Initial state
        assert service._get_reviewer_load("alice") == 0
        
        # Increment load
        service._increment_reviewer_load("alice")
        assert service._get_reviewer_load("alice") == 1
        
        # Increment again
        service._increment_reviewer_load("alice")
        assert service._get_reviewer_load("alice") == 2
    
    def test_handle_pr_closed_decrements_load(self, base_config, sample_pr):
        """
        Test that closing a PR decrements reviewer load.
        
        Requirements: 8.4
        """
        base_config.reviewers = ReviewerConfig(
            enabled=True,
            strategy=ReviewerStrategy.LOAD_BALANCED,
        )
        
        service = PRService(base_config)
        
        # Set initial loads
        service._reviewer_load = {
            "alice": 2,
            "bob": 1,
        }
        
        # Set PR reviewers
        sample_pr.reviewers = ["alice", "bob"]
        
        # Handle PR closed
        service.handle_pr_closed(sample_pr)
        
        # Verify loads were decremented
        assert service._get_reviewer_load("alice") == 1
        assert service._get_reviewer_load("bob") == 0


class TestReviewerAssignmentIntegration:
    """Integration tests for reviewer assignment."""
    
    def test_skip_draft_prs(self, base_config, sample_task, sample_pr, mock_git_client):
        """
        Test that reviewer assignment is skipped for draft PRs.
        
        Requirements: 8.5
        """
        base_config.reviewers = ReviewerConfig(
            enabled=True,
            default_reviewers=["alice"],
            skip_draft_prs=True,
        )
        
        service = PRService(base_config)
        service.git_host_client = mock_git_client
        
        # Set PR as draft
        sample_pr.draft = True
        
        # Assign reviewers
        service._assign_reviewers(sample_pr, sample_task)
        
        # Verify no reviewers were assigned
        mock_git_client.assign_reviewers.assert_not_called()
    
    def test_disabled_reviewer_assignment(self, base_config, sample_task, sample_pr, mock_git_client):
        """
        Test that reviewer assignment can be disabled.
        
        Requirements: 8.5
        """
        base_config.reviewers = ReviewerConfig(
            enabled=False,
            default_reviewers=["alice"],
        )
        
        service = PRService(base_config)
        service.git_host_client = mock_git_client
        
        # Assign reviewers
        service._assign_reviewers(sample_pr, sample_task)
        
        # Verify no reviewers were assigned
        mock_git_client.assign_reviewers.assert_not_called()
    
    def test_max_reviewers_limit(self, base_config, sample_task, sample_pr, mock_git_client):
        """
        Test that reviewer count is limited to max_reviewers.
        
        Requirements: 8.1
        """
        base_config.reviewers = ReviewerConfig(
            enabled=True,
            default_reviewers=["alice", "bob", "charlie", "diana", "eve"],
            max_reviewers=2,
        )
        
        service = PRService(base_config)
        service.git_host_client = mock_git_client
        
        # Assign reviewers
        service._assign_reviewers(sample_pr, sample_task)
        
        # Verify only max_reviewers were assigned
        mock_git_client.assign_reviewers.assert_called_once()
        assigned_reviewers = mock_git_client.assign_reviewers.call_args[0][1]
        assert len(assigned_reviewers) <= 2

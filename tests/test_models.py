"""
Unit tests for Review & PR Service data models.

Tests serialization/deserialization of PullRequest, PRState, and CIStatus.
"""

import pytest
from datetime import datetime
import json

from necrocode.review_pr_service.models import (
    PullRequest,
    PRState,
    PRComment,
    PRMetrics,
    CIStatus
)


class TestPRState:
    """Test PRState enum"""
    
    def test_pr_state_values(self):
        """Test PRState enum values"""
        assert PRState.OPEN.value == "open"
        assert PRState.MERGED.value == "merged"
        assert PRState.CLOSED.value == "closed"
        assert PRState.DRAFT.value == "draft"
    
    def test_pr_state_from_string(self):
        """Test creating PRState from string"""
        assert PRState("open") == PRState.OPEN
        assert PRState("merged") == PRState.MERGED
        assert PRState("closed") == PRState.CLOSED
        assert PRState("draft") == PRState.DRAFT


class TestCIStatus:
    """Test CIStatus enum"""
    
    def test_ci_status_values(self):
        """Test CIStatus enum values"""
        assert CIStatus.PENDING.value == "pending"
        assert CIStatus.SUCCESS.value == "success"
        assert CIStatus.FAILURE.value == "failure"
        assert CIStatus.RUNNING.value == "running"
        assert CIStatus.CANCELLED.value == "cancelled"
        assert CIStatus.SKIPPED.value == "skipped"
    
    def test_ci_status_from_string(self):
        """Test creating CIStatus from string"""
        assert CIStatus("pending") == CIStatus.PENDING
        assert CIStatus("success") == CIStatus.SUCCESS
        assert CIStatus("failure") == CIStatus.FAILURE


class TestPullRequest:
    """Test PullRequest data model"""
    
    @pytest.fixture
    def sample_pr(self):
        """Create a sample PullRequest for testing"""
        return PullRequest(
            pr_id="12345",
            pr_number=42,
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/repo/pull/42",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            merged_at=None,
            closed_at=None,
            author="testuser",
            reviewers=["reviewer1", "reviewer2"],
            labels=["backend", "priority:high"],
            ci_status=CIStatus.PENDING,
            merge_commit_sha=None,
            task_id="task-1",
            spec_id="test-spec",
            metadata={"custom": "data"}
        )
    
    def test_pr_creation(self, sample_pr):
        """Test PullRequest creation"""
        assert sample_pr.pr_id == "12345"
        assert sample_pr.pr_number == 42
        assert sample_pr.title == "Test PR"
        assert sample_pr.state == PRState.OPEN
        assert sample_pr.draft is False
        assert len(sample_pr.reviewers) == 2
        assert len(sample_pr.labels) == 2
    
    def test_pr_to_dict(self, sample_pr):
        """Test PullRequest serialization to dict"""
        pr_dict = sample_pr.to_dict()
        
        assert pr_dict["pr_id"] == "12345"
        assert pr_dict["pr_number"] == 42
        assert pr_dict["title"] == "Test PR"
        assert pr_dict["state"] == "open"
        assert pr_dict["ci_status"] == "pending"
        assert pr_dict["created_at"] == "2024-01-01T12:00:00"
        assert pr_dict["merged_at"] is None
        assert pr_dict["reviewers"] == ["reviewer1", "reviewer2"]
        assert pr_dict["labels"] == ["backend", "priority:high"]
    
    def test_pr_from_dict(self, sample_pr):
        """Test PullRequest deserialization from dict"""
        pr_dict = sample_pr.to_dict()
        restored_pr = PullRequest.from_dict(pr_dict)
        
        assert restored_pr.pr_id == sample_pr.pr_id
        assert restored_pr.pr_number == sample_pr.pr_number
        assert restored_pr.title == sample_pr.title
        assert restored_pr.state == sample_pr.state
        assert restored_pr.ci_status == sample_pr.ci_status
        assert restored_pr.created_at == sample_pr.created_at
        assert restored_pr.reviewers == sample_pr.reviewers
        assert restored_pr.labels == sample_pr.labels
    
    def test_pr_to_json(self, sample_pr):
        """Test PullRequest serialization to JSON"""
        json_str = sample_pr.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["pr_id"] == "12345"
        assert parsed["state"] == "open"
    
    def test_pr_from_json(self, sample_pr):
        """Test PullRequest deserialization from JSON"""
        json_str = sample_pr.to_json()
        restored_pr = PullRequest.from_json(json_str)
        
        assert restored_pr.pr_id == sample_pr.pr_id
        assert restored_pr.state == sample_pr.state
        assert restored_pr.ci_status == sample_pr.ci_status
    
    def test_pr_round_trip_serialization(self, sample_pr):
        """Test complete round-trip serialization"""
        # to_dict -> from_dict
        pr_dict = sample_pr.to_dict()
        restored_pr = PullRequest.from_dict(pr_dict)
        
        # Verify all fields match
        assert restored_pr.pr_id == sample_pr.pr_id
        assert restored_pr.pr_number == sample_pr.pr_number
        assert restored_pr.title == sample_pr.title
        assert restored_pr.description == sample_pr.description
        assert restored_pr.source_branch == sample_pr.source_branch
        assert restored_pr.target_branch == sample_pr.target_branch
        assert restored_pr.url == sample_pr.url
        assert restored_pr.state == sample_pr.state
        assert restored_pr.draft == sample_pr.draft
        assert restored_pr.created_at == sample_pr.created_at
        assert restored_pr.author == sample_pr.author
        assert restored_pr.reviewers == sample_pr.reviewers
        assert restored_pr.labels == sample_pr.labels
        assert restored_pr.ci_status == sample_pr.ci_status
        assert restored_pr.task_id == sample_pr.task_id
        assert restored_pr.spec_id == sample_pr.spec_id
        assert restored_pr.metadata == sample_pr.metadata
    
    def test_pr_with_merged_at(self):
        """Test PullRequest with merged_at timestamp"""
        merged_time = datetime(2024, 1, 2, 12, 0, 0)
        pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Test",
            description="Test",
            source_branch="feature",
            target_branch="main",
            url="https://test.com",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            merged_at=merged_time
        )
        
        pr_dict = pr.to_dict()
        assert pr_dict["merged_at"] == "2024-01-02T12:00:00"
        
        restored_pr = PullRequest.from_dict(pr_dict)
        assert restored_pr.merged_at == merged_time
    
    def test_is_mergeable_success(self):
        """Test is_mergeable returns True for open PR with CI success"""
        pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Test",
            description="Test",
            source_branch="feature",
            target_branch="main",
            url="https://test.com",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
            ci_status=CIStatus.SUCCESS
        )
        
        assert pr.is_mergeable() is True
    
    def test_is_mergeable_draft(self):
        """Test is_mergeable returns False for draft PR"""
        pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Test",
            description="Test",
            source_branch="feature",
            target_branch="main",
            url="https://test.com",
            state=PRState.OPEN,
            draft=True,
            created_at=datetime.now(),
            ci_status=CIStatus.SUCCESS
        )
        
        assert pr.is_mergeable() is False
    
    def test_is_mergeable_ci_pending(self):
        """Test is_mergeable returns False when CI is pending"""
        pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Test",
            description="Test",
            source_branch="feature",
            target_branch="main",
            url="https://test.com",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
            ci_status=CIStatus.PENDING
        )
        
        assert pr.is_mergeable() is False
    
    def test_is_mergeable_closed(self):
        """Test is_mergeable returns False for closed PR"""
        pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Test",
            description="Test",
            source_branch="feature",
            target_branch="main",
            url="https://test.com",
            state=PRState.CLOSED,
            draft=False,
            created_at=datetime.now(),
            ci_status=CIStatus.SUCCESS
        )
        
        assert pr.is_mergeable() is False
    
    def test_update_ci_status(self, sample_pr):
        """Test updating CI status"""
        assert sample_pr.ci_status == CIStatus.PENDING
        
        sample_pr.update_ci_status(CIStatus.SUCCESS)
        assert sample_pr.ci_status == CIStatus.SUCCESS
        
        sample_pr.update_ci_status(CIStatus.FAILURE)
        assert sample_pr.ci_status == CIStatus.FAILURE
    
    def test_mark_as_merged(self, sample_pr):
        """Test marking PR as merged"""
        assert sample_pr.state == PRState.OPEN
        assert sample_pr.merged_at is None
        assert sample_pr.merge_commit_sha is None
        
        sample_pr.mark_as_merged("abc123")
        
        assert sample_pr.state == PRState.MERGED
        assert sample_pr.merged_at is not None
        assert sample_pr.merge_commit_sha == "abc123"
    
    def test_mark_as_closed(self, sample_pr):
        """Test marking PR as closed"""
        assert sample_pr.state == PRState.OPEN
        assert sample_pr.closed_at is None
        
        sample_pr.mark_as_closed()
        
        assert sample_pr.state == PRState.CLOSED
        assert sample_pr.closed_at is not None
    
    def test_convert_from_draft(self):
        """Test converting PR from draft to ready"""
        pr = PullRequest(
            pr_id="123",
            pr_number=1,
            title="Test",
            description="Test",
            source_branch="feature",
            target_branch="main",
            url="https://test.com",
            state=PRState.DRAFT,
            draft=True,
            created_at=datetime.now()
        )
        
        assert pr.draft is True
        assert pr.state == PRState.DRAFT
        
        pr.convert_from_draft()
        
        assert pr.draft is False
        assert pr.state == PRState.OPEN


class TestPRComment:
    """Test PRComment data model"""
    
    def test_comment_creation(self):
        """Test PRComment creation"""
        comment = PRComment(
            comment_id="c123",
            pr_id="pr456",
            author="testuser",
            body="Test comment",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            is_review_comment=False
        )
        
        assert comment.comment_id == "c123"
        assert comment.pr_id == "pr456"
        assert comment.author == "testuser"
        assert comment.body == "Test comment"
        assert comment.is_review_comment is False
    
    def test_comment_to_dict(self):
        """Test PRComment serialization"""
        comment = PRComment(
            comment_id="c123",
            pr_id="pr456",
            author="testuser",
            body="Test comment",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            file_path="test.py",
            line_number=42
        )
        
        comment_dict = comment.to_dict()
        
        assert comment_dict["comment_id"] == "c123"
        assert comment_dict["pr_id"] == "pr456"
        assert comment_dict["author"] == "testuser"
        assert comment_dict["body"] == "Test comment"
        assert comment_dict["created_at"] == "2024-01-01T12:00:00"
        assert comment_dict["file_path"] == "test.py"
        assert comment_dict["line_number"] == 42
    
    def test_comment_from_dict(self):
        """Test PRComment deserialization"""
        comment_dict = {
            "comment_id": "c123",
            "pr_id": "pr456",
            "author": "testuser",
            "body": "Test comment",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
            "is_review_comment": True,
            "file_path": "test.py",
            "line_number": 42
        }
        
        comment = PRComment.from_dict(comment_dict)
        
        assert comment.comment_id == "c123"
        assert comment.pr_id == "pr456"
        assert comment.author == "testuser"
        assert comment.body == "Test comment"
        assert comment.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert comment.is_review_comment is True
        assert comment.file_path == "test.py"
        assert comment.line_number == 42


class TestPRMetrics:
    """Test PRMetrics data model"""
    
    def test_metrics_creation(self):
        """Test PRMetrics creation"""
        metrics = PRMetrics(
            pr_id="pr123",
            time_to_merge=3600.0,
            review_comment_count=5,
            ci_execution_time=120.0,
            commits_count=3,
            files_changed=10,
            lines_added=100,
            lines_deleted=50,
            review_cycles=2,
            time_to_first_review=600.0
        )
        
        assert metrics.pr_id == "pr123"
        assert metrics.time_to_merge == 3600.0
        assert metrics.review_comment_count == 5
        assert metrics.ci_execution_time == 120.0
        assert metrics.commits_count == 3
        assert metrics.files_changed == 10
        assert metrics.lines_added == 100
        assert metrics.lines_deleted == 50
        assert metrics.review_cycles == 2
        assert metrics.time_to_first_review == 600.0
    
    def test_metrics_to_dict(self):
        """Test PRMetrics serialization"""
        metrics = PRMetrics(
            pr_id="pr123",
            time_to_merge=3600.0,
            review_comment_count=5
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["pr_id"] == "pr123"
        assert metrics_dict["time_to_merge"] == 3600.0
        assert metrics_dict["review_comment_count"] == 5
    
    def test_metrics_from_dict(self):
        """Test PRMetrics deserialization"""
        metrics_dict = {
            "pr_id": "pr123",
            "time_to_merge": 3600.0,
            "review_comment_count": 5,
            "ci_execution_time": 120.0,
            "commits_count": 3,
            "files_changed": 10,
            "lines_added": 100,
            "lines_deleted": 50,
            "review_cycles": 2,
            "time_to_first_review": 600.0
        }
        
        metrics = PRMetrics.from_dict(metrics_dict)
        
        assert metrics.pr_id == "pr123"
        assert metrics.time_to_merge == 3600.0
        assert metrics.review_comment_count == 5
        assert metrics.ci_execution_time == 120.0

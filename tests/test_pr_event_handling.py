"""
Tests for PR event handling functionality.

Tests the handle_pr_merged method and related event processing.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import PRServiceConfig, GitHostType
from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, EventType


@pytest.fixture
def temp_registry():
    """Create a temporary task registry for testing."""
    temp_dir = tempfile.mkdtemp()
    registry = TaskRegistry(registry_dir=Path(temp_dir))
    yield registry
    shutil.rmtree(temp_dir)


@pytest.fixture
def pr_service_config(temp_registry):
    """Create PR service configuration for testing."""
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token="test_token",
        repository="test_owner/test_repo",
        task_registry_path=str(temp_registry.registry_dir)
    )
    return config


@pytest.fixture
def mock_git_client(monkeypatch):
    """Mock Git host client for testing."""
    class MockGitClient:
        def __init__(self, config):
            self.config = config
            self.deleted_branches = []
        
        def delete_branch(self, branch_name):
            self.deleted_branches.append(branch_name)
        
        def create_pull_request(self, *args, **kwargs):
            return PullRequest(
                pr_id="1",
                pr_number=1,
                title="Test PR",
                description="Test",
                source_branch="feature/test",
                target_branch="main",
                url="https://github.com/test/test/pull/1",
                state=PRState.OPEN,
                draft=False,
                created_at=datetime.now()
            )
        
        def get_ci_status(self, pr_id):
            return CIStatus.SUCCESS
        
        def add_comment(self, pr_id, comment):
            pass
        
        def add_labels(self, pr_id, labels):
            pass
        
        def remove_label(self, pr_id, label):
            pass
        
        def assign_reviewers(self, pr_id, reviewers):
            pass
        
        def get_pr(self, pr_id):
            return PullRequest(
                pr_id=pr_id,
                pr_number=int(pr_id),
                title="Test PR",
                description="Test",
                source_branch="feature/test",
                target_branch="main",
                url=f"https://github.com/test/test/pull/{pr_id}",
                state=PRState.OPEN,
                draft=False,
                created_at=datetime.now(),
                labels=[]
            )
        
        def update_pr_description(self, pr_id, description):
            pass
        
        def merge_pr(self, pr_id, merge_method="merge", delete_branch=False):
            pass
        
        def check_conflicts(self, pr_id):
            return False
        
        def convert_to_ready(self, pr_id):
            pass
    
    return MockGitClient


class TestPREventHandling:
    """Test PR event handling functionality."""
    
    def test_handle_pr_merged_basic(self, pr_service_config, temp_registry, mock_git_client, monkeypatch):
        """Test basic PR merged event handling."""
        # Patch the git client creation
        monkeypatch.setattr(
            "necrocode.review_pr_service.pr_service.GitHubClient",
            mock_git_client
        )
        
        # Create PR service
        service = PRService(pr_service_config)
        
        # Create a test task in registry
        spec_name = "test-spec"
        task = Task(
            id="1",
            title="Test Task",
            description="Test task description",
            state=TaskState.IN_PROGRESS,
            dependencies=[]
        )
        
        temp_registry.create_taskset(spec_name, "Test Spec", [task])
        
        # Create a merged PR
        pr = PullRequest(
            pr_id="1",
            pr_number=1,
            title="Task 1: Test Task",
            description="Test PR",
            source_branch="feature/task-1",
            target_branch="main",
            url="https://github.com/test/test/pull/1",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now(),
            merged_at=datetime.now(),
            task_id="1",
            spec_id=spec_name
        )
        
        # Handle PR merged event
        service.handle_pr_merged(pr, delete_branch=False, return_slot=False, unblock_dependencies=False)
        
        # Verify event was recorded
        events = temp_registry.event_store.get_events(spec_name, "1")
        pr_merged_events = [e for e in events if e.details.get("event") == "pr_merged"]
        
        assert len(pr_merged_events) > 0
        assert pr_merged_events[0].details["pr_number"] == 1
        assert pr_merged_events[0].details["pr_url"] == pr.url
    
    def test_handle_pr_merged_with_branch_deletion(self, pr_service_config, temp_registry, mock_git_client, monkeypatch):
        """Test PR merged event with branch deletion."""
        # Patch the git client creation
        mock_client_instance = mock_git_client(pr_service_config)
        
        def create_client(config):
            return mock_client_instance
        
        monkeypatch.setattr(
            "necrocode.review_pr_service.pr_service.GitHubClient",
            create_client
        )
        
        # Create PR service
        service = PRService(pr_service_config)
        service.git_host_client = mock_client_instance
        
        # Create a merged PR
        pr = PullRequest(
            pr_id="1",
            pr_number=1,
            title="Test PR",
            description="Test",
            source_branch="feature/test-branch",
            target_branch="main",
            url="https://github.com/test/test/pull/1",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now(),
            merged_at=datetime.now(),
            task_id="1",
            spec_id="test-spec"
        )
        
        # Handle PR merged with branch deletion
        service.handle_pr_merged(pr, delete_branch=True, return_slot=False, unblock_dependencies=False)
        
        # Verify branch was deleted
        assert "feature/test-branch" in mock_client_instance.deleted_branches
    
    def test_handle_pr_merged_unblock_dependencies(self, pr_service_config, temp_registry, mock_git_client, monkeypatch):
        """Test PR merged event unblocks dependent tasks."""
        # Patch the git client creation
        monkeypatch.setattr(
            "necrocode.review_pr_service.pr_service.GitHubClient",
            mock_git_client
        )
        
        # Create PR service
        service = PRService(pr_service_config)
        
        # Create tasks with dependencies
        spec_name = "test-spec"
        task1 = Task(
            id="1",
            title="Task 1",
            description="First task",
            state=TaskState.IN_PROGRESS,
            dependencies=[]
        )
        task2 = Task(
            id="2",
            title="Task 2",
            description="Second task depends on first",
            state=TaskState.BLOCKED,
            dependencies=["1"]
        )
        
        temp_registry.create_taskset(spec_name, "Test Spec", [task1, task2])
        
        # Create a merged PR for task 1
        pr = PullRequest(
            pr_id="1",
            pr_number=1,
            title="Task 1: First Task",
            description="Test PR",
            source_branch="feature/task-1",
            target_branch="main",
            url="https://github.com/test/test/pull/1",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now(),
            merged_at=datetime.now(),
            task_id="1",
            spec_id=spec_name
        )
        
        # Handle PR merged with dependency unblocking
        service.handle_pr_merged(pr, delete_branch=False, return_slot=False, unblock_dependencies=True)
        
        # Verify task 2 was unblocked
        taskset = temp_registry.get_taskset(spec_name)
        task2_updated = next(t for t in taskset.tasks if t.id == "2")
        
        assert task2_updated.state == TaskState.PENDING
    
    def test_handle_pr_merged_with_slot_return(self, pr_service_config, temp_registry, mock_git_client, monkeypatch):
        """Test PR merged event with slot return."""
        # Patch the git client creation
        monkeypatch.setattr(
            "necrocode.review_pr_service.pr_service.GitHubClient",
            mock_git_client
        )
        
        # Create PR service
        service = PRService(pr_service_config)
        
        # Create a test task
        spec_name = "test-spec"
        task = Task(
            id="1",
            title="Test Task",
            description="Test",
            state=TaskState.IN_PROGRESS,
            dependencies=[]
        )
        
        temp_registry.create_taskset(spec_name, "Test Spec", [task])
        
        # Create a merged PR with workspace metadata
        pr = PullRequest(
            pr_id="1",
            pr_number=1,
            title="Test PR",
            description="Test",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/test/pull/1",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now(),
            merged_at=datetime.now(),
            task_id="1",
            spec_id=spec_name,
            metadata={
                "workspace_id": "workspace-123",
                "slot_id": "slot-456"
            }
        )
        
        # Handle PR merged with slot return
        service.handle_pr_merged(pr, delete_branch=False, return_slot=True, unblock_dependencies=False)
        
        # Verify slot return event was recorded
        events = temp_registry.event_store.get_events(spec_name, "1")
        slot_return_events = [e for e in events if e.details.get("event") == "slot_returned"]
        
        assert len(slot_return_events) > 0
        assert slot_return_events[0].details["workspace_id"] == "workspace-123"
        assert slot_return_events[0].details["slot_id"] == "slot-456"
    
    def test_record_pr_merged_event(self, pr_service_config, temp_registry, mock_git_client, monkeypatch):
        """Test PR merged event recording."""
        # Patch the git client creation
        monkeypatch.setattr(
            "necrocode.review_pr_service.pr_service.GitHubClient",
            mock_git_client
        )
        
        # Create PR service
        service = PRService(pr_service_config)
        
        # Create a merged PR
        pr = PullRequest(
            pr_id="1",
            pr_number=1,
            title="Test PR",
            description="Test",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/test/pull/1",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now(),
            merged_at=datetime.now(),
            merge_commit_sha="abc123",
            task_id="1",
            spec_id="test-spec"
        )
        
        # Record PR merged event
        service._record_pr_merged(pr)
        
        # Verify event was recorded
        events = temp_registry.event_store.get_events("test-spec", "1")
        pr_merged_events = [e for e in events if e.details.get("event") == "pr_merged"]
        
        assert len(pr_merged_events) > 0
        event = pr_merged_events[0]
        assert event.event_type == EventType.TASK_COMPLETED
        assert event.details["pr_number"] == 1
        assert event.details["merge_commit_sha"] == "abc123"
        assert event.details["source_branch"] == "feature/test"
        assert event.details["target_branch"] == "main"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

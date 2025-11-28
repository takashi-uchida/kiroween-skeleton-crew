"""
Integration tests for PRService with actual Git host APIs.

These tests require actual API credentials and should be run separately
from unit tests. They test the full PR workflow including:
- PR creation
- Label management
- Reviewer assignment
- CI status monitoring
- PR updates
- Conflict detection
- Draft PR handling

Set environment variables before running:
- GITHUB_TOKEN: GitHub personal access token
- GITHUB_TEST_REPO: Test repository (owner/repo)
- GITLAB_TOKEN: GitLab personal access token
- GITLAB_TEST_PROJECT: Test project ID
- BITBUCKET_USERNAME: Bitbucket username
- BITBUCKET_APP_PASSWORD: Bitbucket app password
- BITBUCKET_TEST_REPO: Test repository (workspace/repo-slug)
"""

import os
import pytest
import time
from datetime import datetime
from pathlib import Path

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import (
    PRServiceConfig,
    GitHostType,
    LabelsConfig,
    ReviewersConfig,
    ReviewerStrategy,
    DraftConfig,
    ConflictDetectionConfig,
    MergeConfig,
    MergeStrategy
)
from necrocode.review_pr_service.models import CIStatus, PRState
from necrocode.task_registry.models import Task, TaskState, Artifact, ArtifactType


# Skip all tests if no credentials are provided
pytestmark = pytest.mark.skipif(
    not os.getenv("GITHUB_TOKEN") and not os.getenv("GITLAB_TOKEN"),
    reason="No Git host credentials provided"
)


@pytest.fixture
def github_config():
    """Create GitHub configuration from environment"""
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_TEST_REPO", "test-owner/test-repo")
    
    if not token:
        pytest.skip("GITHUB_TOKEN not set")
    
    return PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository=repo,
        api_token=token,
        labels=LabelsConfig(
            enabled=True,
            rules={
                "backend": ["backend", "api"],
                "frontend": ["frontend", "ui"],
            },
            priority_labels=True,
            ci_status_labels=True,
        ),
        reviewers=ReviewersConfig(
            enabled=True,
            strategy=ReviewerStrategy.ROUND_ROBIN,
            max_reviewers=2,
        ),
        draft=DraftConfig(
            enabled=True,
            create_as_draft=False,
        ),
        conflict_detection=ConflictDetectionConfig(
            enabled=True,
            check_on_creation=True,
        ),
    )


@pytest.fixture
def gitlab_config():
    """Create GitLab configuration from environment"""
    token = os.getenv("GITLAB_TOKEN")
    project_id = os.getenv("GITLAB_TEST_PROJECT", "12345")
    
    if not token:
        pytest.skip("GITLAB_TOKEN not set")
    
    return PRServiceConfig(
        git_host_type=GitHostType.GITLAB,
        repository=project_id,
        api_token=token,
        labels=LabelsConfig(
            enabled=True,
            rules={
                "backend": ["backend"],
                "frontend": ["frontend"],
            },
        ),
        reviewers=ReviewersConfig(
            enabled=True,
            strategy=ReviewerStrategy.LOAD_BALANCED,
        ),
    )


@pytest.fixture
def bitbucket_config():
    """Create Bitbucket configuration from environment"""
    username = os.getenv("BITBUCKET_USERNAME")
    password = os.getenv("BITBUCKET_APP_PASSWORD")
    repo = os.getenv("BITBUCKET_TEST_REPO", "workspace/repo-slug")
    
    if not username or not password:
        pytest.skip("BITBUCKET credentials not set")
    
    return PRServiceConfig(
        git_host_type=GitHostType.BITBUCKET,
        repository=repo,
        api_token=f"{username}:{password}",
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing"""
    task = Task(
        id="integration-test-1",
        title="Integration Test Task",
        description="This is a test task for integration testing",
        state=TaskState.DONE,
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "type": "backend",
            "priority": "high",
            "files": ["src/api/test.py", "src/models/test.py"],
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
        Artifact(
            type=ArtifactType.LOG,
            uri="https://example.com/test.log",
            size_bytes=2048,
            created_at=datetime.now(),
            metadata={"name": "Test Logs"}
        ),
    ]
    
    return task


class TestGitHubIntegration:
    """Integration tests for GitHub"""
    
    @pytest.mark.integration
    @pytest.mark.github
    def test_create_pr_github(self, github_config, sample_task):
        """Test creating a PR on GitHub"""
        pr_service = PRService(github_config)
        
        # Create unique branch name
        branch_name = f"test/integration-{int(time.time())}"
        
        # Note: This test requires the branch to exist in the repository
        # In a real scenario, you would create the branch first
        
        try:
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
                base_branch="main",
                acceptance_criteria=[
                    "Feature works correctly",
                    "Tests pass",
                    "Documentation updated",
                ]
            )
            
            # Verify PR was created
            assert pr is not None
            assert pr.pr_number > 0
            assert pr.url
            assert pr.state == PRState.OPEN
            assert "Integration Test Task" in pr.title
            
            # Verify labels were applied
            assert len(pr.labels) > 0
            assert any("backend" in label or "api" in label for label in pr.labels)
            
            print(f"✓ Created PR #{pr.pr_number}: {pr.url}")
            
            # Clean up: Close the PR
            pr_service.git_host_client.close_pr(pr.pr_id)
            print(f"✓ Closed PR #{pr.pr_number}")
            
        except Exception as e:
            pytest.fail(f"Failed to create PR: {e}")
    
    @pytest.mark.integration
    @pytest.mark.github
    def test_create_draft_pr_github(self, github_config, sample_task):
        """Test creating a draft PR on GitHub"""
        github_config.draft.create_as_draft = True
        pr_service = PRService(github_config)
        
        branch_name = f"test/draft-{int(time.time())}"
        
        try:
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
            )
            
            # Verify PR was created as draft
            assert pr.draft is True
            assert pr.state == PRState.OPEN
            
            # Verify draft label was applied
            assert github_config.draft.draft_label in pr.labels
            
            print(f"✓ Created draft PR #{pr.pr_number}: {pr.url}")
            
            # Test marking as ready
            pr_service.mark_pr_ready(pr.pr_id)
            
            # Verify PR is no longer draft
            updated_pr = pr_service.git_host_client.get_pr(pr.pr_id)
            assert updated_pr.draft is False
            
            print(f"✓ Marked PR #{pr.pr_number} as ready")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to create draft PR: {e}")
    
    @pytest.mark.integration
    @pytest.mark.github
    def test_update_pr_description_github(self, github_config, sample_task):
        """Test updating PR description on GitHub"""
        pr_service = PRService(github_config)
        
        branch_name = f"test/update-{int(time.time())}"
        
        try:
            # Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
            )
            
            print(f"✓ Created PR #{pr.pr_number}")
            
            # Update PR description
            updates = {
                "execution_time": 45.2,
                "test_results": {
                    "total": 10,
                    "passed": 9,
                    "failed": 1,
                },
                "execution_logs": [
                    {"name": "Build Log", "url": "https://example.com/build.log"},
                    {"name": "Test Log", "url": "https://example.com/test.log"},
                ],
            }
            
            pr_service.update_pr_description(pr.pr_id, updates)
            
            # Verify description was updated
            updated_pr = pr_service.git_host_client.get_pr(pr.pr_id)
            assert "Execution Time" in updated_pr.description
            assert "45.2" in updated_pr.description
            assert "Test Results Update" in updated_pr.description
            
            print(f"✓ Updated PR #{pr.pr_number} description")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to update PR description: {e}")
    
    @pytest.mark.integration
    @pytest.mark.github
    def test_label_management_github(self, github_config, sample_task):
        """Test label management on GitHub"""
        pr_service = PRService(github_config)
        
        branch_name = f"test/labels-{int(time.time())}"
        
        try:
            # Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
            )
            
            print(f"✓ Created PR #{pr.pr_number}")
            
            # Verify initial labels
            assert len(pr.labels) > 0
            assert any("backend" in label for label in pr.labels)
            assert "priority:high" in pr.labels
            
            # Update CI status labels
            pr_service.update_labels_for_ci_status(pr.pr_id, CIStatus.SUCCESS)
            
            # Verify CI label was added
            updated_pr = pr_service.git_host_client.get_pr(pr.pr_id)
            assert "ci:success" in updated_pr.labels
            
            print(f"✓ Updated CI status labels for PR #{pr.pr_number}")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to manage labels: {e}")
    
    @pytest.mark.integration
    @pytest.mark.github
    def test_conflict_detection_github(self, github_config, sample_task):
        """Test conflict detection on GitHub"""
        pr_service = PRService(github_config)
        
        branch_name = f"test/conflict-{int(time.time())}"
        
        try:
            # Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
            )
            
            print(f"✓ Created PR #{pr.pr_number}")
            
            # Check for conflicts
            has_conflicts = pr_service.check_pr_conflicts(pr.pr_id)
            
            print(f"✓ Conflict check: {'conflicts found' if has_conflicts else 'no conflicts'}")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to check conflicts: {e}")


class TestGitLabIntegration:
    """Integration tests for GitLab"""
    
    @pytest.mark.integration
    @pytest.mark.gitlab
    def test_create_pr_gitlab(self, gitlab_config, sample_task):
        """Test creating a merge request on GitLab"""
        pr_service = PRService(gitlab_config)
        
        branch_name = f"test/integration-{int(time.time())}"
        
        try:
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
                base_branch="main",
            )
            
            # Verify MR was created
            assert pr is not None
            assert pr.pr_number > 0
            assert pr.url
            assert pr.state == PRState.OPEN
            
            print(f"✓ Created MR !{pr.pr_number}: {pr.url}")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to create MR: {e}")
    
    @pytest.mark.integration
    @pytest.mark.gitlab
    def test_label_management_gitlab(self, gitlab_config, sample_task):
        """Test label management on GitLab"""
        pr_service = PRService(gitlab_config)
        
        branch_name = f"test/labels-{int(time.time())}"
        
        try:
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
            )
            
            # Verify labels were applied
            assert len(pr.labels) > 0
            
            print(f"✓ Created MR !{pr.pr_number} with labels: {pr.labels}")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to manage labels: {e}")


class TestBitbucketIntegration:
    """Integration tests for Bitbucket"""
    
    @pytest.mark.integration
    @pytest.mark.bitbucket
    def test_create_pr_bitbucket(self, bitbucket_config, sample_task):
        """Test creating a pull request on Bitbucket"""
        pr_service = PRService(bitbucket_config)
        
        branch_name = f"test/integration-{int(time.time())}"
        
        try:
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
                base_branch="main",
            )
            
            # Verify PR was created
            assert pr is not None
            assert pr.pr_number > 0
            assert pr.url
            assert pr.state == PRState.OPEN
            
            print(f"✓ Created PR #{pr.pr_number}: {pr.url}")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"Failed to create PR: {e}")


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.mark.integration
    @pytest.mark.e2e
    def test_full_pr_workflow_github(self, github_config, sample_task, tmp_path):
        """Test complete PR workflow from creation to merge"""
        # Configure with Task Registry
        github_config.task_registry_path = str(tmp_path / "task_registry")
        github_config.metrics_storage_path = str(tmp_path / "metrics")
        
        pr_service = PRService(github_config)
        
        branch_name = f"test/e2e-{int(time.time())}"
        
        try:
            # 1. Create PR
            pr = pr_service.create_pr(
                task=sample_task,
                branch_name=branch_name,
                acceptance_criteria=["Feature complete", "Tests pass"],
            )
            
            print(f"✓ Step 1: Created PR #{pr.pr_number}")
            
            # 2. Update PR description
            pr_service.update_pr_description(pr.pr_id, {
                "execution_time": 30.5,
                "test_results": {"total": 5, "passed": 5, "failed": 0},
            })
            
            print(f"✓ Step 2: Updated PR description")
            
            # 3. Update CI status labels
            pr_service.update_labels_for_ci_status(pr.pr_id, CIStatus.SUCCESS)
            
            print(f"✓ Step 3: Updated CI status labels")
            
            # 4. Check for conflicts
            has_conflicts = pr_service.check_pr_conflicts(pr.pr_id)
            
            print(f"✓ Step 4: Checked for conflicts: {has_conflicts}")
            
            # 5. Verify Task Registry events
            if pr_service.task_registry:
                events = pr_service.task_registry.event_store.get_events(
                    spec_name=sample_task.spec_name if hasattr(sample_task, 'spec_name') else "unknown",
                    task_id=sample_task.id
                )
                assert len(events) > 0
                print(f"✓ Step 5: Verified {len(events)} events in Task Registry")
            
            # 6. Verify metrics
            if pr_service.metrics_collector:
                metrics = pr_service.metrics_collector.get_pr_metrics(pr.pr_id)
                assert metrics is not None
                print(f"✓ Step 6: Verified metrics collection")
            
            print(f"✓ Full workflow completed successfully")
            
            # Clean up
            pr_service.git_host_client.close_pr(pr.pr_id)
            
        except Exception as e:
            pytest.fail(f"E2E workflow failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

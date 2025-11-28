"""
Git Host Client - Abstract interface and concrete implementations for GitHub, GitLab, and Bitbucket.

This module provides a unified interface for interacting with different Git hosting platforms.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .models import PullRequest, CIStatus, PRState
from .exceptions import (
    PRServiceError,
    AuthenticationError,
    RateLimitError,
    NetworkError
)
from .retry_handler import with_retry, RetryHandler

logger = logging.getLogger(__name__)


class GitHostClient(ABC):
    """
    Abstract base class for Git host API clients.
    
    Provides a unified interface for creating PRs, managing CI status,
    adding comments, labels, and assigning reviewers across different
    Git hosting platforms (GitHub, GitLab, Bitbucket).
    
    Requirements: 3.1
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Git host client.
        
        Args:
            config: Configuration dictionary containing authentication
                   credentials and repository information
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate that required configuration is present."""
        pass
    
    @abstractmethod
    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False
    ) -> PullRequest:
        """
        Create a pull request.
        
        Args:
            title: PR title
            description: PR description/body
            source_branch: Source branch name
            target_branch: Target branch name (e.g., 'main')
            draft: Whether to create as draft PR
            
        Returns:
            PullRequest object with PR details
            
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If API rate limit is exceeded
            NetworkError: If network request fails
            PRServiceError: For other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def get_ci_status(self, pr_id: str) -> CIStatus:
        """
        Get the CI/CD status for a pull request.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            CIStatus enum value (PENDING, SUCCESS, FAILURE)
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def add_comment(self, pr_id: str, comment: str) -> None:
        """
        Add a comment to a pull request.
        
        Args:
            pr_id: Pull request identifier
            comment: Comment text (supports Markdown)
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def add_labels(self, pr_id: str, labels: List[str]) -> None:
        """
        Add labels to a pull request.
        
        Args:
            pr_id: Pull request identifier
            labels: List of label names to add
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def remove_label(self, pr_id: str, label: str) -> None:
        """
        Remove a label from a pull request.
        
        Args:
            pr_id: Pull request identifier
            label: Label name to remove
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 7.3
        """
        pass
    
    @abstractmethod
    def assign_reviewers(self, pr_id: str, reviewers: List[str]) -> None:
        """
        Assign reviewers to a pull request.
        
        Args:
            pr_id: Pull request identifier
            reviewers: List of reviewer usernames
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def update_pr_description(self, pr_id: str, description: str) -> None:
        """
        Update the description/body of a pull request.
        
        Args:
            pr_id: Pull request identifier
            description: New description text
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def get_pr(self, pr_id: str) -> PullRequest:
        """
        Get pull request details.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            PullRequest object with current PR details
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def merge_pr(
        self,
        pr_id: str,
        merge_method: str = "merge",
        delete_branch: bool = False
    ) -> None:
        """
        Merge a pull request.
        
        Args:
            pr_id: Pull request identifier
            merge_method: Merge method ('merge', 'squash', 'rebase')
            delete_branch: Whether to delete source branch after merge
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If merge fails or PR not found
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def check_conflicts(self, pr_id: str) -> bool:
        """
        Check if a pull request has merge conflicts.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            True if conflicts exist, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or other errors
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def convert_to_ready(self, pr_id: str) -> None:
        """
        Convert a draft PR to ready for review.
        
        Args:
            pr_id: Pull request identifier
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If PR not found or not a draft
            
        Requirements: 3.1
        """
        pass
    
    @abstractmethod
    def delete_branch(self, branch_name: str) -> None:
        """
        Delete a branch from the repository.
        
        Args:
            branch_name: Name of the branch to delete
            
        Raises:
            AuthenticationError: If authentication fails
            PRServiceError: If branch not found or deletion fails
            
        Requirements: 5.3
        """
        pass



class GitHubClient(GitHostClient):
    """
    GitHub API client implementation.
    
    Uses PyGithub library to interact with GitHub's REST API.
    
    Requirements: 1.4, 3.2
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GitHub client.
        
        Args:
            config: Configuration with 'token', 'repo_owner', 'repo_name'
        """
        super().__init__(config)
        
        try:
            from github import Github, GithubException
            self.Github = Github
            self.GithubException = GithubException
        except ImportError:
            raise PRServiceError(
                "PyGithub is not installed. Install with: pip install PyGithub"
            )
        
        self.client = self.Github(self.config["token"])
        self.repo = self.client.get_repo(
            f"{self.config['repo_owner']}/{self.config['repo_name']}"
        )
    
    def _validate_config(self) -> None:
        """Validate GitHub configuration."""
        required = ["token", "repo_owner", "repo_name"]
        missing = [key for key in required if key not in self.config]
        if missing:
            raise PRServiceError(
                f"Missing required GitHub config: {', '.join(missing)}"
            )
    
    def _handle_github_exception(self, e: Exception) -> None:
        """
        Convert GitHub exceptions to our exception types.
        
        Requirements: 15.1, 15.2, 15.3, 15.5
        """
        error_msg = str(e)
        
        # Log all errors
        logger.error(f"GitHub API error: {error_msg}", exc_info=True)
        
        if hasattr(e, 'status'):
            # Authentication errors (401)
            if e.status == 401:
                logger.error("GitHub authentication failed - check API token")
                raise AuthenticationError(
                    f"GitHub authentication failed: {error_msg}",
                    details={"status_code": e.status}
                )
            
            # Rate limit errors (403 with rate limit message)
            elif e.status == 403 and 'rate limit' in error_msg.lower():
                # Extract rate limit reset time if available
                reset_time = None
                if hasattr(e, 'data') and isinstance(e.data, dict):
                    reset_time = e.data.get('rate', {}).get('reset')
                
                logger.warning(
                    f"GitHub rate limit exceeded, reset at: {reset_time}"
                )
                raise RateLimitError(
                    f"GitHub rate limit exceeded: {error_msg}",
                    reset_time=reset_time,
                    details={"status_code": e.status}
                )
            
            # Network/timeout errors (502, 503, 504)
            elif e.status in [502, 503, 504]:
                logger.warning(f"GitHub service unavailable (status {e.status})")
                raise NetworkError(
                    f"GitHub service unavailable: {error_msg}",
                    details={"status_code": e.status}
                )
        
        # Generic network error for other cases
        logger.error(f"Unexpected GitHub API error: {error_msg}")
        raise NetworkError(
            f"GitHub API error: {error_msg}",
            details={"exception_type": type(e).__name__}
        )
    
    @with_retry(max_retries=3, initial_delay=1.0, max_delay=60.0)
    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False
    ) -> PullRequest:
        """
        Create a GitHub pull request with automatic retry.
        
        Requirements: 15.2, 15.4
        """
        try:
            logger.info(f"Creating GitHub PR: {title} ({source_branch} -> {target_branch})")
            
            gh_pr = self.repo.create_pull(
                title=title,
                body=description,
                head=source_branch,
                base=target_branch,
                draft=draft
            )
            
            logger.info(f"Successfully created GitHub PR #{gh_pr.number}")
            
            return PullRequest(
                pr_id=str(gh_pr.id),
                pr_number=gh_pr.number,
                title=gh_pr.title,
                description=gh_pr.body or "",
                source_branch=source_branch,
                target_branch=target_branch,
                url=gh_pr.html_url,
                state=PRState.OPEN,
                draft=draft,
                created_at=gh_pr.created_at,
                merged_at=gh_pr.merged_at
            )
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    @with_retry(max_retries=3, initial_delay=1.0)
    def get_ci_status(self, pr_id: str) -> CIStatus:
        """
        Get CI status for a GitHub PR with automatic retry.
        
        Requirements: 15.2, 15.4
        """
        try:
            logger.debug(f"Getting CI status for GitHub PR {pr_id}")
            
            pr = self.repo.get_pull(int(pr_id))
            commits = pr.get_commits()
            
            if commits.totalCount == 0:
                return CIStatus.PENDING
            
            # Get the latest commit
            latest_commit = commits.reversed[0]
            combined_status = latest_commit.get_combined_status()
            
            # Map GitHub status to our CIStatus
            status_map = {
                "success": CIStatus.SUCCESS,
                "failure": CIStatus.FAILURE,
                "error": CIStatus.FAILURE,
                "pending": CIStatus.PENDING
            }
            
            status = status_map.get(combined_status.state, CIStatus.PENDING)
            logger.debug(f"GitHub PR {pr_id} CI status: {status.value}")
            
            return status
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    @with_retry(max_retries=3, initial_delay=1.0)
    def add_comment(self, pr_id: str, comment: str) -> None:
        """
        Add a comment to a GitHub PR with automatic retry.
        
        Requirements: 15.2, 15.4
        """
        try:
            logger.debug(f"Adding comment to GitHub PR {pr_id}")
            pr = self.repo.get_pull(int(pr_id))
            pr.create_issue_comment(comment)
            logger.info(f"Successfully added comment to GitHub PR {pr_id}")
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def add_labels(self, pr_id: str, labels: List[str]) -> None:
        """Add labels to a GitHub PR."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            issue = self.repo.get_issue(pr.number)
            issue.add_to_labels(*labels)
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def remove_label(self, pr_id: str, label: str) -> None:
        """Remove a label from a GitHub PR."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            issue = self.repo.get_issue(pr.number)
            issue.remove_from_labels(label)
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def assign_reviewers(self, pr_id: str, reviewers: List[str]) -> None:
        """Assign reviewers to a GitHub PR."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            pr.create_review_request(reviewers=reviewers)
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def update_pr_description(self, pr_id: str, description: str) -> None:
        """Update GitHub PR description."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            pr.edit(body=description)
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def get_pr(self, pr_id: str) -> PullRequest:
        """Get GitHub PR details."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            
            state = PRState.OPEN
            if pr.merged:
                state = PRState.MERGED
            elif pr.state == "closed":
                state = PRState.CLOSED
            
            return PullRequest(
                pr_id=str(pr.id),
                pr_number=pr.number,
                title=pr.title,
                description=pr.body or "",
                source_branch=pr.head.ref,
                target_branch=pr.base.ref,
                url=pr.html_url,
                state=state,
                draft=pr.draft,
                created_at=pr.created_at,
                merged_at=pr.merged_at
            )
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def merge_pr(
        self,
        pr_id: str,
        merge_method: str = "merge",
        delete_branch: bool = False
    ) -> None:
        """Merge a GitHub PR."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            pr.merge(merge_method=merge_method)
            
            if delete_branch:
                ref = self.repo.get_git_ref(f"heads/{pr.head.ref}")
                ref.delete()
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def check_conflicts(self, pr_id: str) -> bool:
        """Check if GitHub PR has conflicts."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            return not pr.mergeable
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def convert_to_ready(self, pr_id: str) -> None:
        """Convert draft PR to ready for review."""
        try:
            pr = self.repo.get_pull(int(pr_id))
            # GitHub API doesn't have a direct method, use GraphQL or REST API v3
            # For now, we'll edit the PR to mark it as ready
            if pr.draft:
                # This requires GraphQL API - simplified implementation
                raise PRServiceError(
                    "Converting draft to ready requires GraphQL API. "
                    "Please implement using GitHub's GraphQL endpoint."
                )
        except self.GithubException as e:
            self._handle_github_exception(e)
    
    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch from GitHub repository."""
        try:
            ref = self.repo.get_git_ref(f"heads/{branch_name}")
            ref.delete()
        except self.GithubException as e:
            self._handle_github_exception(e)



class GitLabClient(GitHostClient):
    """
    GitLab API client implementation.
    
    Uses python-gitlab library to interact with GitLab's REST API.
    
    Requirements: 3.3
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GitLab client.
        
        Args:
            config: Configuration with 'token', 'url', 'project_id'
        """
        super().__init__(config)
        
        try:
            import gitlab
            self.gitlab = gitlab
        except ImportError:
            raise PRServiceError(
                "python-gitlab is not installed. Install with: pip install python-gitlab"
            )
        
        self.client = self.gitlab.Gitlab(
            self.config.get("url", "https://gitlab.com"),
            private_token=self.config["token"]
        )
        self.project = self.client.projects.get(self.config["project_id"])
    
    def _validate_config(self) -> None:
        """Validate GitLab configuration."""
        required = ["token", "project_id"]
        missing = [key for key in required if key not in self.config]
        if missing:
            raise PRServiceError(
                f"Missing required GitLab config: {', '.join(missing)}"
            )
    
    def _handle_gitlab_exception(self, e: Exception) -> None:
        """
        Convert GitLab exceptions to our exception types.
        
        Requirements: 15.1, 15.2, 15.3, 15.5
        """
        error_msg = str(e)
        
        # Log all errors
        logger.error(f"GitLab API error: {error_msg}", exc_info=True)
        
        if hasattr(e, 'response_code'):
            # Authentication errors (401)
            if e.response_code == 401:
                logger.error("GitLab authentication failed - check API token")
                raise AuthenticationError(
                    f"GitLab authentication failed: {error_msg}",
                    details={"status_code": e.response_code}
                )
            
            # Rate limit errors (429)
            elif e.response_code == 429:
                # Extract rate limit reset time if available
                reset_time = None
                if hasattr(e, 'response_headers'):
                    reset_time_str = e.response_headers.get('RateLimit-Reset')
                    if reset_time_str:
                        try:
                            reset_time = int(reset_time_str)
                        except ValueError:
                            pass
                
                logger.warning(
                    f"GitLab rate limit exceeded, reset at: {reset_time}"
                )
                raise RateLimitError(
                    f"GitLab rate limit exceeded: {error_msg}",
                    reset_time=reset_time,
                    details={"status_code": e.response_code}
                )
            
            # Network/timeout errors (502, 503, 504)
            elif e.response_code in [502, 503, 504]:
                logger.warning(f"GitLab service unavailable (status {e.response_code})")
                raise NetworkError(
                    f"GitLab service unavailable: {error_msg}",
                    details={"status_code": e.response_code}
                )
        
        # Generic network error for other cases
        logger.error(f"Unexpected GitLab API error: {error_msg}")
        raise NetworkError(
            f"GitLab API error: {error_msg}",
            details={"exception_type": type(e).__name__}
        )
    
    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False
    ) -> PullRequest:
        """Create a GitLab merge request (PR equivalent)."""
        try:
            mr_title = f"Draft: {title}" if draft else title
            
            mr = self.project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': mr_title,
                'description': description
            })
            
            return PullRequest(
                pr_id=str(mr.iid),
                pr_number=mr.iid,
                title=title,
                description=description,
                source_branch=source_branch,
                target_branch=target_branch,
                url=mr.web_url,
                state=PRState.OPEN,
                draft=draft,
                created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00')),
                merged_at=None
            )
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def get_ci_status(self, pr_id: str) -> CIStatus:
        """Get CI status for a GitLab MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            # Get pipeline status
            if not hasattr(mr, 'head_pipeline') or mr.head_pipeline is None:
                return CIStatus.PENDING
            
            pipeline_status = mr.head_pipeline.get('status', 'pending')
            
            # Map GitLab status to our CIStatus
            status_map = {
                "success": CIStatus.SUCCESS,
                "failed": CIStatus.FAILURE,
                "canceled": CIStatus.FAILURE,
                "skipped": CIStatus.PENDING,
                "manual": CIStatus.PENDING,
                "pending": CIStatus.PENDING,
                "running": CIStatus.PENDING,
                "created": CIStatus.PENDING
            }
            
            return status_map.get(pipeline_status, CIStatus.PENDING)
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def add_comment(self, pr_id: str, comment: str) -> None:
        """Add a comment to a GitLab MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            mr.notes.create({'body': comment})
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def add_labels(self, pr_id: str, labels: List[str]) -> None:
        """Add labels to a GitLab MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            existing_labels = mr.labels if hasattr(mr, 'labels') else []
            all_labels = list(set(existing_labels + labels))
            mr.labels = all_labels
            mr.save()
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def remove_label(self, pr_id: str, label: str) -> None:
        """Remove a label from a GitLab MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            existing_labels = mr.labels if hasattr(mr, 'labels') else []
            if label in existing_labels:
                existing_labels.remove(label)
                mr.labels = existing_labels
                mr.save()
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def assign_reviewers(self, pr_id: str, reviewers: List[str]) -> None:
        """Assign reviewers to a GitLab MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            # Get user IDs from usernames
            reviewer_ids = []
            for username in reviewers:
                users = self.client.users.list(username=username)
                if users:
                    reviewer_ids.append(users[0].id)
            
            if reviewer_ids:
                mr.reviewer_ids = reviewer_ids
                mr.save()
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def update_pr_description(self, pr_id: str, description: str) -> None:
        """Update GitLab MR description."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            mr.description = description
            mr.save()
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def get_pr(self, pr_id: str) -> PullRequest:
        """Get GitLab MR details."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            state = PRState.OPEN
            if mr.state == "merged":
                state = PRState.MERGED
            elif mr.state == "closed":
                state = PRState.CLOSED
            
            draft = mr.title.startswith("Draft:") or mr.work_in_progress
            
            merged_at = None
            if mr.merged_at:
                merged_at = datetime.fromisoformat(mr.merged_at.replace('Z', '+00:00'))
            
            return PullRequest(
                pr_id=str(mr.iid),
                pr_number=mr.iid,
                title=mr.title,
                description=mr.description or "",
                source_branch=mr.source_branch,
                target_branch=mr.target_branch,
                url=mr.web_url,
                state=state,
                draft=draft,
                created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00')),
                merged_at=merged_at
            )
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def merge_pr(
        self,
        pr_id: str,
        merge_method: str = "merge",
        delete_branch: bool = False
    ) -> None:
        """Merge a GitLab MR."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            # Map merge method
            merge_params = {}
            if merge_method == "squash":
                merge_params['squash'] = True
            
            if delete_branch:
                merge_params['should_remove_source_branch'] = True
            
            mr.merge(**merge_params)
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def check_conflicts(self, pr_id: str) -> bool:
        """Check if GitLab MR has conflicts."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            return mr.has_conflicts
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def convert_to_ready(self, pr_id: str) -> None:
        """Convert draft MR to ready for review."""
        try:
            mr = self.project.mergerequests.get(int(pr_id))
            
            # Remove "Draft:" prefix from title
            if mr.title.startswith("Draft:"):
                mr.title = mr.title.replace("Draft:", "").strip()
            
            # Set work_in_progress to False
            mr.work_in_progress = False
            mr.save()
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)
    
    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch from GitLab repository."""
        try:
            self.project.branches.delete(branch_name)
        except self.gitlab.exceptions.GitlabError as e:
            self._handle_gitlab_exception(e)



class BitbucketClient(GitHostClient):
    """
    Bitbucket API client implementation.
    
    Uses atlassian-python-api library to interact with Bitbucket's REST API.
    
    Requirements: 3.4
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bitbucket client.
        
        Args:
            config: Configuration with 'username', 'password', 'url', 
                   'workspace', 'repo_slug'
        """
        super().__init__(config)
        
        try:
            from atlassian import Bitbucket
            self.Bitbucket = Bitbucket
        except ImportError:
            raise PRServiceError(
                "atlassian-python-api is not installed. "
                "Install with: pip install atlassian-python-api"
            )
        
        self.client = self.Bitbucket(
            url=self.config.get("url", "https://api.bitbucket.org"),
            username=self.config["username"],
            password=self.config["password"]
        )
        self.workspace = self.config["workspace"]
        self.repo_slug = self.config["repo_slug"]
    
    def _validate_config(self) -> None:
        """Validate Bitbucket configuration."""
        required = ["username", "password", "workspace", "repo_slug"]
        missing = [key for key in required if key not in self.config]
        if missing:
            raise PRServiceError(
                f"Missing required Bitbucket config: {', '.join(missing)}"
            )
    
    def _handle_bitbucket_exception(self, e: Exception) -> None:
        """
        Convert Bitbucket exceptions to our exception types.
        
        Requirements: 15.1, 15.2, 15.3, 15.5
        """
        error_msg = str(e)
        error_msg_lower = error_msg.lower()
        
        # Log all errors
        logger.error(f"Bitbucket API error: {error_msg}", exc_info=True)
        
        # Authentication errors (401 or "unauthorized")
        if "401" in error_msg_lower or "unauthorized" in error_msg_lower:
            logger.error("Bitbucket authentication failed - check credentials")
            raise AuthenticationError(
                f"Bitbucket authentication failed: {error_msg}",
                details={"error_message": error_msg}
            )
        
        # Rate limit errors (429 or "rate limit")
        elif "429" in error_msg_lower or "rate limit" in error_msg_lower:
            logger.warning("Bitbucket rate limit exceeded")
            raise RateLimitError(
                f"Bitbucket rate limit exceeded: {error_msg}",
                details={"error_message": error_msg}
            )
        
        # Network/timeout errors
        elif any(code in error_msg_lower for code in ["502", "503", "504", "timeout", "connection"]):
            logger.warning(f"Bitbucket network error: {error_msg}")
            raise NetworkError(
                f"Bitbucket network error: {error_msg}",
                details={"error_message": error_msg}
            )
        
        # Generic network error for other cases
        logger.error(f"Unexpected Bitbucket API error: {error_msg}")
        raise NetworkError(
            f"Bitbucket API error: {error_msg}",
            details={"exception_type": type(e).__name__}
        )
    
    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False
    ) -> PullRequest:
        """Create a Bitbucket pull request."""
        try:
            pr_data = {
                "title": title,
                "description": description,
                "source": {
                    "branch": {
                        "name": source_branch
                    }
                },
                "destination": {
                    "branch": {
                        "name": target_branch
                    }
                }
            }
            
            # Bitbucket doesn't have native draft support
            # We can add a label or prefix to indicate draft status
            if draft:
                pr_data["title"] = f"[DRAFT] {title}"
            
            response = self.client.create_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_data
            )
            
            return PullRequest(
                pr_id=str(response["id"]),
                pr_number=response["id"],
                title=title,
                description=description,
                source_branch=source_branch,
                target_branch=target_branch,
                url=response["links"]["html"]["href"],
                state=PRState.OPEN,
                draft=draft,
                created_at=datetime.fromisoformat(
                    response["created_on"].replace('Z', '+00:00')
                ),
                merged_at=None
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def get_ci_status(self, pr_id: str) -> CIStatus:
        """Get CI status for a Bitbucket PR."""
        try:
            # Get PR details
            pr = self.client.get_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id
            )
            
            # Get build statuses for the source commit
            source_commit = pr["source"]["commit"]["hash"]
            
            try:
                statuses = self.client.get_commit_statuses(
                    self.workspace,
                    self.repo_slug,
                    source_commit
                )
                
                if not statuses or "values" not in statuses:
                    return CIStatus.PENDING
                
                # Check all build statuses
                all_statuses = [s["state"] for s in statuses["values"]]
                
                if any(s in ["FAILED", "STOPPED"] for s in all_statuses):
                    return CIStatus.FAILURE
                elif all(s == "SUCCESSFUL" for s in all_statuses):
                    return CIStatus.SUCCESS
                else:
                    return CIStatus.PENDING
            except:
                # If we can't get build statuses, return pending
                return CIStatus.PENDING
                
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def add_comment(self, pr_id: str, comment: str) -> None:
        """Add a comment to a Bitbucket PR."""
        try:
            self.client.add_pullrequest_comment(
                self.workspace,
                self.repo_slug,
                pr_id,
                comment
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def add_labels(self, pr_id: str, labels: List[str]) -> None:
        """
        Add labels to a Bitbucket PR.
        
        Note: Bitbucket doesn't have native label support for PRs.
        This is a no-op or could be implemented via custom fields.
        """
        # Bitbucket doesn't support labels on PRs natively
        # Could be implemented via custom fields or tags if needed
        pass
    
    def remove_label(self, pr_id: str, label: str) -> None:
        """
        Remove a label from a Bitbucket PR.
        
        Note: Bitbucket doesn't have native label support for PRs.
        This is a no-op.
        """
        # Bitbucket doesn't support labels on PRs natively
        pass
    
    def assign_reviewers(self, pr_id: str, reviewers: List[str]) -> None:
        """Assign reviewers to a Bitbucket PR."""
        try:
            # Get current PR data
            pr = self.client.get_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id
            )
            
            # Add reviewers
            reviewer_list = [{"username": username} for username in reviewers]
            
            update_data = {
                "reviewers": reviewer_list
            }
            
            self.client.update_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id,
                update_data
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def update_pr_description(self, pr_id: str, description: str) -> None:
        """Update Bitbucket PR description."""
        try:
            update_data = {
                "description": description
            }
            
            self.client.update_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id,
                update_data
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def get_pr(self, pr_id: str) -> PullRequest:
        """Get Bitbucket PR details."""
        try:
            pr = self.client.get_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id
            )
            
            state = PRState.OPEN
            if pr["state"] == "MERGED":
                state = PRState.MERGED
            elif pr["state"] in ["DECLINED", "SUPERSEDED"]:
                state = PRState.CLOSED
            
            draft = pr["title"].startswith("[DRAFT]")
            title = pr["title"].replace("[DRAFT]", "").strip()
            
            merged_at = None
            if pr.get("merge_commit"):
                merged_at = datetime.fromisoformat(
                    pr["updated_on"].replace('Z', '+00:00')
                )
            
            return PullRequest(
                pr_id=str(pr["id"]),
                pr_number=pr["id"],
                title=title,
                description=pr.get("description", ""),
                source_branch=pr["source"]["branch"]["name"],
                target_branch=pr["destination"]["branch"]["name"],
                url=pr["links"]["html"]["href"],
                state=state,
                draft=draft,
                created_at=datetime.fromisoformat(
                    pr["created_on"].replace('Z', '+00:00')
                ),
                merged_at=merged_at
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def merge_pr(
        self,
        pr_id: str,
        merge_method: str = "merge",
        delete_branch: bool = False
    ) -> None:
        """Merge a Bitbucket PR."""
        try:
            merge_data = {}
            
            # Map merge method to Bitbucket strategy
            if merge_method == "squash":
                merge_data["merge_strategy"] = "squash"
            elif merge_method == "rebase":
                merge_data["merge_strategy"] = "fast_forward"
            else:
                merge_data["merge_strategy"] = "merge_commit"
            
            if delete_branch:
                merge_data["close_source_branch"] = True
            
            self.client.merge_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id,
                merge_data
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def check_conflicts(self, pr_id: str) -> bool:
        """Check if Bitbucket PR has conflicts."""
        try:
            pr = self.client.get_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id
            )
            
            # Check if PR has merge conflicts
            # Bitbucket API doesn't always expose this directly
            # We check the task status or merge checks
            if "task" in pr and pr["task"].get("status") == "FAILED":
                return True
            
            # Alternative: check if mergeable
            return not pr.get("mergeable", True)
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def convert_to_ready(self, pr_id: str) -> None:
        """Convert draft PR to ready for review."""
        try:
            pr = self.client.get_pullrequest(
                self.workspace,
                self.repo_slug,
                pr_id
            )
            
            # Remove [DRAFT] prefix from title
            if pr["title"].startswith("[DRAFT]"):
                new_title = pr["title"].replace("[DRAFT]", "").strip()
                
                update_data = {
                    "title": new_title
                }
                
                self.client.update_pullrequest(
                    self.workspace,
                    self.repo_slug,
                    pr_id,
                    update_data
                )
        except Exception as e:
            self._handle_bitbucket_exception(e)
    
    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch from Bitbucket repository."""
        try:
            self.client.delete_branch(
                self.workspace,
                self.repo_slug,
                branch_name
            )
        except Exception as e:
            self._handle_bitbucket_exception(e)

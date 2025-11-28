"""
PR Service - Main API for automated Pull Request management.

This module provides the main PRService class that coordinates PR creation,
CI monitoring, label management, reviewer assignment, and Task Registry integration.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from necrocode.review_pr_service.config import PRServiceConfig, GitHostType, MergeStrategy
from necrocode.review_pr_service.models import PullRequest, CIStatus, PRState
from necrocode.review_pr_service.git_host_client import (
    GitHostClient,
    GitHubClient,
    GitLabClient,
    BitbucketClient,
)
from necrocode.review_pr_service.pr_template_engine import PRTemplateEngine
from necrocode.review_pr_service.exceptions import (
    PRServiceError,
    PRCreationError,
    PRUpdateError,
)
from necrocode.review_pr_service.metrics_collector import MetricsCollector, PrometheusExporter
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskEvent, EventType, Artifact
from necrocode.artifact_store.artifact_store import ArtifactStore

try:
    from jinja2 import Template
except ImportError:
    Template = None


logger = logging.getLogger(__name__)


class PRService:
    """
    Review & PR Service main class.
    
    Coordinates PR creation, template generation, CI monitoring,
    and integration with Task Registry and Artifact Store.
    
    Requirements: 1.1
    """
    
    def __init__(self, config: PRServiceConfig):
        """
        Initialize PR Service.
        
        Args:
            config: PR Service configuration
            
        Requirements: 1.1
        """
        self.config = config
        
        # Initialize Git host client
        self.git_host_client = self._create_git_host_client()
        
        # Initialize template engine
        self.template_engine = PRTemplateEngine(config)
        
        # Initialize Task Registry if path is configured
        self.task_registry: Optional[TaskRegistry] = None
        if config.task_registry_path:
            registry_path = Path(config.task_registry_path)
            self.task_registry = TaskRegistry(registry_dir=registry_path)
            logger.info(f"Task Registry initialized: {registry_path}")
        
        # Initialize Artifact Store if URL is configured
        self.artifact_store: Optional[ArtifactStore] = None
        if config.artifact_store_url:
            # For now, we'll use filesystem backend
            # In production, this would parse the URL and configure appropriately
            self.artifact_store = ArtifactStore()
            logger.info(f"Artifact Store initialized: {config.artifact_store_url}")
        
        # Initialize round-robin state for reviewer assignment
        self._reviewer_round_robin_index: Dict[str, int] = {}
        
        # Initialize load tracking for reviewer assignment
        self._reviewer_load: Dict[str, int] = {}
        
        # Initialize metrics collector
        self.metrics_collector: Optional[MetricsCollector] = None
        if config.metrics_storage_path:
            metrics_path = Path(config.metrics_storage_path)
            self.metrics_collector = MetricsCollector(storage_path=metrics_path)
            logger.info(f"Metrics Collector initialized: {metrics_path}")
        
        # Initialize Prometheus exporter if metrics collector is available
        self.prometheus_exporter: Optional[PrometheusExporter] = None
        if self.metrics_collector:
            self.prometheus_exporter = PrometheusExporter(self.metrics_collector)
            logger.info("Prometheus Exporter initialized")
        
        logger.info(
            f"PRService initialized: git_host={config.git_host_type.value}, "
            f"repository={config.repository}"
        )
    
    def _create_git_host_client(self) -> GitHostClient:
        """
        Create Git host client based on configuration.
        
        Returns:
            GitHostClient instance for the configured platform
            
        Raises:
            PRServiceError: If client creation fails
            
        Requirements: 1.1
        """
        try:
            if self.config.git_host_type == GitHostType.GITHUB:
                # Parse repository into owner/name
                if "/" not in self.config.repository:
                    raise PRServiceError(
                        f"Invalid GitHub repository format: {self.config.repository}. "
                        "Expected format: owner/repo"
                    )
                
                owner, repo_name = self.config.repository.split("/", 1)
                
                client_config = {
                    "token": self.config.api_token,
                    "repo_owner": owner,
                    "repo_name": repo_name,
                }
                
                return GitHubClient(client_config)
            
            elif self.config.git_host_type == GitHostType.GITLAB:
                client_config = {
                    "token": self.config.api_token,
                    "url": self.config.git_host_url or "https://gitlab.com",
                    "project_id": self.config.repository,
                }
                
                return GitLabClient(client_config)
            
            elif self.config.git_host_type == GitHostType.BITBUCKET:
                # Parse repository into workspace/slug
                if "/" not in self.config.repository:
                    raise PRServiceError(
                        f"Invalid Bitbucket repository format: {self.config.repository}. "
                        "Expected format: workspace/repo-slug"
                    )
                
                workspace, repo_slug = self.config.repository.split("/", 1)
                
                # For Bitbucket, we need username/password or app password
                # The token is used as password with username from config
                client_config = {
                    "username": self.config.api_token.split(":")[0] if ":" in self.config.api_token else "x-token-auth",
                    "password": self.config.api_token.split(":")[1] if ":" in self.config.api_token else self.config.api_token,
                    "url": self.config.git_host_url or "https://api.bitbucket.org",
                    "workspace": workspace,
                    "repo_slug": repo_slug,
                }
                
                return BitbucketClient(client_config)
            
            else:
                raise PRServiceError(
                    f"Unsupported Git host type: {self.config.git_host_type}"
                )
        
        except Exception as e:
            logger.error(f"Failed to create Git host client: {e}")
            raise PRServiceError(f"Git host client creation failed: {e}") from e
    
    def _download_artifacts(self, task: Task) -> List[Artifact]:
        """
        Download artifacts for a task from Artifact Store.
        
        Args:
            task: Task object
            
        Returns:
            List of artifacts
            
        Requirements: 1.2
        """
        if not self.artifact_store:
            logger.warning("Artifact Store not configured, returning task artifacts")
            return task.artifacts
        
        # If task already has artifacts, return them
        if task.artifacts:
            logger.debug(f"Task {task.id} already has {len(task.artifacts)} artifacts")
            return task.artifacts
        
        # Otherwise, try to fetch from Artifact Store
        # This would require knowing the spec_name and task_id
        # For now, return empty list
        logger.warning(f"No artifacts found for task {task.id}")
        return []
    
    def _parse_codeowners(self, codeowners_path: str) -> Dict[str, List[str]]:
        """
        Parse CODEOWNERS file and return mapping of patterns to owners.
        
        Args:
            codeowners_path: Path to CODEOWNERS file
            
        Returns:
            Dictionary mapping file patterns to list of owners
            
        Requirements: 8.2
        """
        owners_map = {}
        
        try:
            path = Path(codeowners_path)
            if not path.exists():
                logger.warning(f"CODEOWNERS file not found: {codeowners_path}")
                return owners_map
            
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse pattern and owners
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    
                    pattern = parts[0]
                    owners = [owner.lstrip('@') for owner in parts[1:]]
                    
                    owners_map[pattern] = owners
                    logger.debug(f"CODEOWNERS: {pattern} -> {owners}")
            
            logger.info(f"Parsed {len(owners_map)} patterns from CODEOWNERS file")
            return owners_map
        
        except Exception as e:
            logger.error(f"Failed to parse CODEOWNERS file: {e}")
            return owners_map
    
    def _get_reviewers_from_codeowners(
        self,
        task: Task,
        codeowners_map: Dict[str, List[str]]
    ) -> List[str]:
        """
        Get reviewers from CODEOWNERS based on task files.
        
        Args:
            task: Task object
            codeowners_map: Mapping of file patterns to owners
            
        Returns:
            List of reviewer usernames
            
        Requirements: 8.2
        """
        reviewers = set()
        
        # Get files from task metadata
        files = task.metadata.get("files", [])
        if not files:
            logger.debug("No files specified in task metadata")
            return list(reviewers)
        
        # Match files against CODEOWNERS patterns
        for file_path in files:
            for pattern, owners in codeowners_map.items():
                # Simple pattern matching (supports * wildcard and directory patterns)
                if self._match_codeowners_pattern(file_path, pattern):
                    reviewers.update(owners)
                    logger.debug(f"File '{file_path}' matched pattern '{pattern}': {owners}")
        
        return list(reviewers)
    
    def _get_reviewer_load(self, reviewer: str) -> int:
        """
        Get current load (number of assigned PRs) for a reviewer.
        
        In a production system, this would query the Git host API
        to get actual open PR counts. For now, we track locally.
        
        Args:
            reviewer: Reviewer username
            
        Returns:
            Current load count
            
        Requirements: 8.4
        """
        return self._reviewer_load.get(reviewer, 0)
    
    def _increment_reviewer_load(self, reviewer: str) -> None:
        """
        Increment load counter for a reviewer.
        
        Args:
            reviewer: Reviewer username
            
        Requirements: 8.4
        """
        self._reviewer_load[reviewer] = self._reviewer_load.get(reviewer, 0) + 1
    
    def _select_reviewers_load_balanced(
        self,
        available_reviewers: List[str],
        count: int
    ) -> List[str]:
        """
        Select reviewers using load-balanced strategy.
        
        Selects reviewers with the lowest current workload first.
        
        Args:
            available_reviewers: List of available reviewer usernames
            count: Number of reviewers to select
            
        Returns:
            List of selected reviewers
            
        Requirements: 8.4
        """
        if not available_reviewers:
            return []
        
        # Sort reviewers by current load (ascending)
        sorted_reviewers = sorted(
            available_reviewers,
            key=lambda r: self._get_reviewer_load(r)
        )
        
        # Select reviewers with lowest load
        selected = sorted_reviewers[:count]
        
        logger.debug(
            f"Load-balanced selection: selected {selected} "
            f"(loads: {[self._get_reviewer_load(r) for r in selected]})"
        )
        
        return selected
    
    def _select_reviewers_round_robin(
        self,
        available_reviewers: List[str],
        count: int,
        group_key: str = "default"
    ) -> List[str]:
        """
        Select reviewers using round-robin strategy.
        
        Args:
            available_reviewers: List of available reviewer usernames
            count: Number of reviewers to select
            group_key: Key to track round-robin state per group (e.g., task type)
            
        Returns:
            List of selected reviewers
            
        Requirements: 8.3
        """
        if not available_reviewers:
            return []
        
        # Get current index for this group
        current_index = self._reviewer_round_robin_index.get(group_key, 0)
        
        selected = []
        reviewers_count = len(available_reviewers)
        
        # Select reviewers in round-robin fashion
        for i in range(count):
            if i >= reviewers_count:
                break
            
            index = (current_index + i) % reviewers_count
            selected.append(available_reviewers[index])
        
        # Update index for next assignment
        self._reviewer_round_robin_index[group_key] = (current_index + count) % reviewers_count
        
        logger.debug(
            f"Round-robin selection for '{group_key}': "
            f"selected {selected} from {available_reviewers}"
        )
        
        return selected
    
    def _match_codeowners_pattern(self, file_path: str, pattern: str) -> bool:
        """
        Match file path against CODEOWNERS pattern.
        
        Supports:
        - Exact matches: /path/to/file.py
        - Wildcards: *.py, /path/*.py
        - Directory patterns: /path/to/dir/
        
        Args:
            file_path: File path to match
            pattern: CODEOWNERS pattern
            
        Returns:
            True if file matches pattern
            
        Requirements: 8.2
        """
        import fnmatch
        
        # Normalize paths
        file_path = file_path.lstrip('/')
        pattern = pattern.lstrip('/')
        
        # Directory pattern (ends with /)
        if pattern.endswith('/'):
            return file_path.startswith(pattern.rstrip('/'))
        
        # Wildcard pattern
        if '*' in pattern:
            return fnmatch.fnmatch(file_path, pattern)
        
        # Exact match
        return file_path == pattern
    
    def _apply_labels(self, pr: PullRequest, task: Task) -> None:
        """
        Apply labels to PR based on task metadata and configuration.
        
        Args:
            pr: PullRequest object
            task: Task object
            
        Requirements: 7.1, 7.2
        """
        if not self.config.labels.enabled:
            logger.debug("Label management is disabled")
            return
        
        labels = []
        
        # Apply labels based on task type from metadata
        task_type = task.metadata.get("type", "").lower()
        if task_type and task_type in self.config.labels.rules:
            labels.extend(self.config.labels.rules[task_type])
        
        # Apply priority labels if enabled
        if self.config.labels.priority_labels:
            priority = task.metadata.get("priority", "").lower()
            if priority:
                labels.append(f"priority:{priority}")
        
        # Apply CI status labels if enabled
        if self.config.labels.ci_status_labels and pr.ci_status:
            labels.append(f"ci:{pr.ci_status.value}")
        
        # Apply draft label if PR is draft
        if pr.draft and self.config.draft.enabled:
            labels.append(self.config.draft.draft_label)
        
        # Apply labels to PR
        if labels:
            try:
                self.git_host_client.add_labels(pr.pr_id, labels)
                logger.info(f"Applied labels to PR {pr.pr_number}: {labels}")
            except Exception as e:
                logger.error(f"Failed to apply labels to PR {pr.pr_number}: {e}")
    
    def _assign_reviewers(self, pr: PullRequest, task: Task) -> None:
        """
        Assign reviewers to PR based on configuration and task metadata.
        
        Supports multiple assignment strategies:
        - Task type-based assignment
        - CODEOWNERS file parsing
        - Round-robin distribution
        - Load-balanced assignment
        
        Args:
            pr: PullRequest object
            task: Task object
            
        Requirements: 8.1, 8.2
        """
        if not self.config.reviewers.enabled:
            logger.debug("Reviewer assignment is disabled")
            return
        
        # Skip reviewer assignment for draft PRs if configured
        if pr.draft and self.config.reviewers.skip_draft_prs:
            logger.debug(f"Skipping reviewer assignment for draft PR {pr.pr_number}")
            return
        
        reviewers = []
        
        # Get reviewers from task metadata (highest priority)
        task_reviewers = task.metadata.get("reviewers", [])
        if task_reviewers:
            reviewers.extend(task_reviewers)
            logger.debug(f"Added reviewers from task metadata: {task_reviewers}")
        
        # Get reviewers from CODEOWNERS if strategy is CODEOWNERS
        if self.config.reviewers.strategy == ReviewerStrategy.CODEOWNERS:
            if self.config.reviewers.codeowners_path:
                codeowners_map = self._parse_codeowners(self.config.reviewers.codeowners_path)
                codeowners_reviewers = self._get_reviewers_from_codeowners(task, codeowners_map)
                if codeowners_reviewers:
                    reviewers.extend(codeowners_reviewers)
                    logger.debug(f"Added reviewers from CODEOWNERS: {codeowners_reviewers}")
            else:
                logger.warning("CODEOWNERS strategy selected but no path configured")
        
        # Get reviewers based on task type
        task_type = task.metadata.get("type", "").lower()
        if task_type and hasattr(self.config.reviewers, 'type_reviewers'):
            type_reviewers = self.config.reviewers.type_reviewers.get(task_type, [])
            if type_reviewers:
                reviewers.extend(type_reviewers)
                logger.debug(f"Added reviewers for task type '{task_type}': {type_reviewers}")
        
        # Add default reviewers if configured
        if self.config.reviewers.default_reviewers:
            reviewers.extend(self.config.reviewers.default_reviewers)
            logger.debug(f"Added default reviewers: {self.config.reviewers.default_reviewers}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_reviewers = []
        for reviewer in reviewers:
            if reviewer not in seen:
                seen.add(reviewer)
                unique_reviewers.append(reviewer)
        reviewers = unique_reviewers
        
        # Apply selection strategy if we have more reviewers than needed
        if len(reviewers) > self.config.reviewers.max_reviewers:
            if self.config.reviewers.strategy == ReviewerStrategy.ROUND_ROBIN:
                # Use task type as group key for round-robin, or "default" if no type
                group_key = task.metadata.get("type", "default")
                reviewers = self._select_reviewers_round_robin(
                    reviewers,
                    self.config.reviewers.max_reviewers,
                    group_key
                )
                logger.debug(f"Applied round-robin selection: {reviewers}")
            
            elif self.config.reviewers.strategy == ReviewerStrategy.LOAD_BALANCED:
                reviewers = self._select_reviewers_load_balanced(
                    reviewers,
                    self.config.reviewers.max_reviewers
                )
                logger.debug(f"Applied load-balanced selection: {reviewers}")
            
            else:
                # Default: just take first N reviewers
                reviewers = reviewers[:self.config.reviewers.max_reviewers]
                logger.debug(f"Limited reviewers to max {self.config.reviewers.max_reviewers}")
        
        # Assign reviewers to PR
        if reviewers:
            try:
                self.git_host_client.assign_reviewers(pr.pr_id, reviewers)
                logger.info(f"Assigned reviewers to PR {pr.pr_number}: {reviewers}")
                
                # Track load for load-balanced strategy
                if self.config.reviewers.strategy == ReviewerStrategy.LOAD_BALANCED:
                    for reviewer in reviewers:
                        self._increment_reviewer_load(reviewer)
                    logger.debug(f"Updated reviewer loads: {self._reviewer_load}")
            
            except Exception as e:
                logger.error(f"Failed to assign reviewers to PR {pr.pr_number}: {e}")
        else:
            logger.warning(f"No reviewers found for PR {pr.pr_number}")
    
    def _record_pr_created(self, task: Task, pr: PullRequest) -> None:
        """
        Record PR creation event in Task Registry.
        
        Args:
            task: Task object
            pr: PullRequest object
            
        Requirements: 1.5
        """
        if not self.task_registry:
            logger.warning("Task Registry not configured, skipping PR event recording")
            return
        
        try:
            # Create PR created event
            event = TaskEvent(
                event_type=EventType.TASK_UPDATED,
                spec_name=task.spec_name if hasattr(task, 'spec_name') else pr.spec_id or "unknown",
                task_id=task.id,
                timestamp=datetime.now(),
                details={
                    "event": "pr_created",
                    "pr_url": pr.url,
                    "pr_number": pr.pr_number,
                    "pr_id": pr.pr_id,
                    "source_branch": pr.source_branch,
                    "target_branch": pr.target_branch,
                    "draft": pr.draft,
                }
            )
            
            # Record event
            self.task_registry.event_store.record_event(event)
            
            logger.info(
                f"Recorded PR creation event for task {task.id}: "
                f"PR #{pr.pr_number} ({pr.url})"
            )
        
        except Exception as e:
            logger.error(f"Failed to record PR creation event: {e}")
            # Don't raise exception, just log the error
    
    def create_pr(
        self,
        task: Task,
        branch_name: str,
        base_branch: str = "main",
        acceptance_criteria: Optional[List[str]] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> PullRequest:
        """
        Create a pull request for a task.
        
        Args:
            task: Task object
            branch_name: Source branch name
            base_branch: Target branch name (default: "main")
            acceptance_criteria: List of acceptance criteria (optional)
            custom_data: Additional custom data for template (optional)
            
        Returns:
            PullRequest object with PR details
            
        Raises:
            PRCreationError: If PR creation fails
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 12.1
        """
        try:
            logger.info(
                f"Creating PR for task {task.id}: {branch_name} -> {base_branch}"
            )
            
            # 1. Download artifacts from Artifact Store
            artifacts = self._download_artifacts(task)
            logger.debug(f"Downloaded {len(artifacts)} artifacts for task {task.id}")
            
            # 2. Generate PR description using template engine
            description = self.template_engine.generate(
                task=task,
                artifacts=artifacts,
                acceptance_criteria=acceptance_criteria,
                custom_data=custom_data
            )
            logger.debug(f"Generated PR description ({len(description)} chars)")
            
            # 3. Create PR using Git host client
            pr_title = f"Task {task.id}: {task.title}"
            draft = self.config.draft.create_as_draft if self.config.draft.enabled else False
            
            pr = self.git_host_client.create_pull_request(
                title=pr_title,
                description=description,
                source_branch=branch_name,
                target_branch=base_branch,
                draft=draft
            )
            
            # Store task and spec IDs in PR metadata
            pr.task_id = task.id
            pr.spec_id = task.spec_name if hasattr(task, 'spec_name') else None
            
            logger.info(
                f"Created PR #{pr.pr_number} for task {task.id}: {pr.url}"
            )
            
            # 4. Apply labels based on task metadata
            self._apply_labels(pr, task)
            
            # 5. Handle draft PR creation (if draft)
            if pr.draft:
                self.handle_draft_pr_creation(pr, task)
            
            # 6. Assign reviewers based on configuration (skip if draft and configured to skip)
            if not (pr.draft and self.config.reviewers.skip_draft_prs):
                self._assign_reviewers(pr, task)
            else:
                logger.debug(f"Skipping reviewer assignment for draft PR #{pr.pr_number}")
            
            # 7. Record PR creation in Task Registry
            self._record_pr_created(task, pr)
            
            # 8. Record PR creation metrics
            if self.metrics_collector:
                self.metrics_collector.record_pr_created(pr)
                logger.debug(f"Recorded metrics for PR #{pr.pr_number}")
            
            # 9. Check for conflicts on PR creation (if enabled)
            if self.config.conflict_detection.enabled and self.config.conflict_detection.check_on_creation:
                self._check_and_handle_conflicts(pr)
            
            return pr
        
        except Exception as e:
            logger.error(f"Failed to create PR for task {task.id}: {e}")
            raise PRCreationError(f"PR creation failed: {e}") from e
    
    def update_labels_for_ci_status(
        self,
        pr_id: str,
        ci_status: CIStatus
    ) -> None:
        """
        Update PR labels based on CI status.
        
        Args:
            pr_id: Pull request identifier
            ci_status: New CI status
            
        Requirements: 7.3
        """
        if not self.config.labels.enabled or not self.config.labels.ci_status_labels:
            logger.debug("CI status labels are disabled")
            return
        
        try:
            logger.info(f"Updating labels for PR {pr_id} based on CI status: {ci_status.value}")
            
            # Get current PR to access existing labels
            pr = self.git_host_client.get_pr(pr_id)
            
            # Remove old CI status labels
            old_ci_labels = [label for label in pr.labels if label.startswith("ci:")]
            if old_ci_labels:
                for label in old_ci_labels:
                    try:
                        self.git_host_client.remove_label(pr_id, label)
                        logger.debug(f"Removed old CI label: {label}")
                    except Exception as e:
                        logger.warning(f"Failed to remove label {label}: {e}")
            
            # Add new CI status label
            new_label = f"ci:{ci_status.value}"
            self.git_host_client.add_labels(pr_id, [new_label])
            logger.info(f"Added CI status label to PR {pr_id}: {new_label}")
            
            # Update PR object's CI status
            pr.update_ci_status(ci_status)
        
        except Exception as e:
            logger.error(f"Failed to update CI status labels for PR {pr_id}: {e}")
            # Don't raise exception, just log the error
    
    def handle_pr_closed(self, pr: PullRequest) -> None:
        """
        Handle PR closed/merged event to update reviewer load.
        
        Args:
            pr: PullRequest object
            
        Requirements: 8.4
        """
        if not pr.reviewers:
            return
        
        # Decrement load for all reviewers
        if self.config.reviewers.strategy == ReviewerStrategy.LOAD_BALANCED:
            for reviewer in pr.reviewers:
                if reviewer in self._reviewer_load and self._reviewer_load[reviewer] > 0:
                    self._reviewer_load[reviewer] -= 1
            
            logger.debug(
                f"Decremented reviewer loads for PR {pr.pr_number}: "
                f"{self._reviewer_load}"
            )
    
    def update_pr_description(
        self,
        pr_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update PR description with additional information.
        
        Args:
            pr_id: Pull request identifier
            updates: Dictionary containing updates to add to PR description
                    Supported keys: execution_logs, test_results, execution_time
            
        Raises:
            PRUpdateError: If PR update fails
            
        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
        """
        try:
            logger.info(f"Updating PR description for PR {pr_id}")
            
            # Get current PR
            pr = self.git_host_client.get_pr(pr_id)
            
            # Build update sections
            update_sections = []
            
            # Add execution logs if provided
            if "execution_logs" in updates:
                logs = updates["execution_logs"]
                if isinstance(logs, str):
                    update_sections.append(f"\n### Execution Logs\n{logs}")
                elif isinstance(logs, list):
                    log_links = "\n".join([f"- [{log.get('name', 'Log')}]({log.get('url')})" for log in logs])
                    update_sections.append(f"\n### Execution Logs\n{log_links}")
            
            # Add test results if provided
            if "test_results" in updates:
                results = updates["test_results"]
                if isinstance(results, str):
                    update_sections.append(f"\n### Test Results Update\n{results}")
                elif isinstance(results, dict):
                    summary = f"""
**Test Summary:**
- Total: {results.get('total', 0)}
- Passed: {results.get('passed', 0)} ✅
- Failed: {results.get('failed', 0)} ❌
- Skipped: {results.get('skipped', 0)} ⏭️
- Duration: {results.get('duration', 0):.2f}s
"""
                    update_sections.append(f"\n### Test Results Update\n{summary}")
            
            # Add execution time if provided
            if "execution_time" in updates:
                exec_time = updates["execution_time"]
                update_sections.append(f"\n### Execution Time\n{exec_time:.2f} seconds")
            
            # Add custom updates
            for key, value in updates.items():
                if key not in ["execution_logs", "test_results", "execution_time"]:
                    update_sections.append(f"\n### {key.replace('_', ' ').title()}\n{value}")
            
            # Append updates to existing description
            if update_sections:
                updated_description = pr.description + "\n\n---\n## Updates\n" + "\n".join(update_sections)
                updated_description += f"\n\n*Updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
                
                # Update PR description
                self.git_host_client.update_pr_description(pr_id, updated_description)
                
                logger.info(f"Updated PR description for PR {pr_id}")
            else:
                logger.warning(f"No updates provided for PR {pr_id}")
        
        except Exception as e:
            logger.error(f"Failed to update PR description for PR {pr_id}: {e}")
            raise PRUpdateError(f"PR update failed: {e}") from e
    
    def handle_pr_merged(
        self,
        pr: PullRequest,
        delete_branch: Optional[bool] = None,
        return_slot: bool = True,
        unblock_dependencies: bool = True
    ) -> None:
        """
        Handle PR merged event.
        
        Performs post-merge operations including:
        - Recording PRMerged event in Task Registry
        - Deleting source branch (if configured)
        - Returning workspace slot to Repo Pool Manager
        - Unblocking dependent tasks
        
        Args:
            pr: PullRequest object that was merged
            delete_branch: Whether to delete branch (overrides config if provided)
            return_slot: Whether to return slot to Repo Pool Manager
            unblock_dependencies: Whether to unblock dependent tasks
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        try:
            logger.info(
                f"Handling PR merged event: PR #{pr.pr_number} ({pr.url})"
            )
            
            # Ensure PR is marked as merged
            if pr.state != PRState.MERGED:
                pr.mark_as_merged()
            
            # 1. Record PRMerged event in Task Registry (subtask 8.2)
            self._record_pr_merged(pr)
            
            # 1.5. Record PR merge metrics
            if self.metrics_collector:
                self.metrics_collector.record_pr_merged(pr)
                logger.debug(f"Recorded merge metrics for PR #{pr.pr_number}")
            
            # 2. Delete branch if configured (subtask 8.3)
            should_delete = delete_branch if delete_branch is not None else self.config.merge.delete_branch_after_merge
            if should_delete:
                self._delete_branch(pr)
            
            # 3. Return slot to Repo Pool Manager (subtask 8.4)
            if return_slot:
                self._return_slot(pr)
            
            # 4. Unblock dependent tasks (subtask 8.5)
            if unblock_dependencies:
                self._unblock_dependent_tasks(pr)
            
            # Update reviewer load tracking
            self.handle_pr_closed(pr)
            
            logger.info(
                f"Successfully handled PR merged event for PR #{pr.pr_number}"
            )
        
        except Exception as e:
            logger.error(f"Failed to handle PR merged event for PR #{pr.pr_number}: {e}")
            # Don't raise exception to avoid blocking other operations
    
    def _record_pr_merged(self, pr: PullRequest) -> None:
        """
        Record PR merged event in Task Registry.
        
        Args:
            pr: PullRequest object that was merged
            
        Requirements: 5.2
        """
        if not self.task_registry:
            logger.warning("Task Registry not configured, skipping PR merged event recording")
            return
        
        try:
            # Determine spec_name and task_id
            spec_name = pr.spec_id or "unknown"
            task_id = pr.task_id or "unknown"
            
            # Create PR merged event
            event = TaskEvent(
                event_type=EventType.TASK_COMPLETED,
                spec_name=spec_name,
                task_id=task_id,
                timestamp=datetime.now(),
                details={
                    "event": "pr_merged",
                    "pr_url": pr.url,
                    "pr_number": pr.pr_number,
                    "pr_id": pr.pr_id,
                    "source_branch": pr.source_branch,
                    "target_branch": pr.target_branch,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "merge_commit_sha": pr.merge_commit_sha,
                }
            )
            
            # Record event
            self.task_registry.event_store.record_event(event)
            
            logger.info(
                f"Recorded PR merged event for task {task_id}: "
                f"PR #{pr.pr_number} ({pr.url})"
            )
        
        except Exception as e:
            logger.error(f"Failed to record PR merged event: {e}")
            # Don't raise exception, just log the error
    
    def _delete_branch(self, pr: PullRequest) -> None:
        """
        Delete source branch after PR merge.
        
        Args:
            pr: PullRequest object with source branch to delete
            
        Requirements: 5.3
        """
        try:
            logger.info(f"Deleting branch '{pr.source_branch}' for PR #{pr.pr_number}")
            
            # Delete branch using Git host client
            self.git_host_client.delete_branch(pr.source_branch)
            
            logger.info(f"Successfully deleted branch '{pr.source_branch}'")
        
        except Exception as e:
            logger.error(f"Failed to delete branch '{pr.source_branch}': {e}")
            # Don't raise exception, branch deletion is not critical
    
    def _return_slot(self, pr: PullRequest) -> None:
        """
        Return workspace slot to Repo Pool Manager.
        
        This method would integrate with the Repo Pool Manager service
        to release the workspace slot that was used for this PR.
        
        Args:
            pr: PullRequest object
            
        Requirements: 5.4
        """
        try:
            # Extract workspace/slot information from PR metadata
            workspace_id = pr.metadata.get("workspace_id")
            slot_id = pr.metadata.get("slot_id")
            
            if not workspace_id and not slot_id:
                logger.debug(
                    f"No workspace/slot information in PR #{pr.pr_number} metadata, "
                    "skipping slot return"
                )
                return
            
            logger.info(
                f"Returning slot to Repo Pool Manager: "
                f"workspace_id={workspace_id}, slot_id={slot_id}"
            )
            
            # TODO: Integrate with Repo Pool Manager client
            # This would call something like:
            # self.repo_pool_client.release_slot(workspace_id, slot_id)
            
            # For now, just log the action
            logger.info(
                f"Slot return requested for PR #{pr.pr_number} "
                f"(workspace_id={workspace_id}, slot_id={slot_id})"
            )
            
            # Record slot return event in Task Registry
            if self.task_registry:
                spec_name = pr.spec_id or "unknown"
                task_id = pr.task_id or "unknown"
                
                event = TaskEvent(
                    event_type=EventType.TASK_UPDATED,
                    spec_name=spec_name,
                    task_id=task_id,
                    timestamp=datetime.now(),
                    details={
                        "event": "slot_returned",
                        "workspace_id": workspace_id,
                        "slot_id": slot_id,
                        "pr_number": pr.pr_number,
                    }
                )
                
                self.task_registry.event_store.record_event(event)
                logger.debug(f"Recorded slot return event for task {task_id}")
        
        except Exception as e:
            logger.error(f"Failed to return slot for PR #{pr.pr_number}: {e}")
            # Don't raise exception, slot return failure shouldn't block other operations
    
    def _unblock_dependent_tasks(self, pr: PullRequest) -> None:
        """
        Unblock dependent tasks after PR merge.
        
        Finds tasks that depend on the completed task and updates their
        state from BLOCKED to PENDING if all dependencies are satisfied.
        
        Args:
            pr: PullRequest object
            
        Requirements: 5.5
        """
        if not self.task_registry:
            logger.warning("Task Registry not configured, skipping dependency unblocking")
            return
        
        try:
            spec_name = pr.spec_id
            task_id = pr.task_id
            
            if not spec_name or not task_id:
                logger.warning(
                    f"PR #{pr.pr_number} missing spec_id or task_id, "
                    "cannot unblock dependencies"
                )
                return
            
            logger.info(
                f"Unblocking tasks dependent on {spec_name}/{task_id} "
                f"(PR #{pr.pr_number})"
            )
            
            # Get the taskset
            try:
                taskset = self.task_registry.get_taskset(spec_name)
            except Exception as e:
                logger.error(f"Failed to get taskset for spec '{spec_name}': {e}")
                return
            
            # Find the completed task
            completed_task = None
            for task in taskset.tasks:
                if task.id == task_id:
                    completed_task = task
                    break
            
            if not completed_task:
                logger.warning(
                    f"Task {task_id} not found in spec {spec_name}, "
                    "cannot unblock dependencies"
                )
                return
            
            # Update task state to COMPLETED if not already
            from necrocode.task_registry.models import TaskState
            if completed_task.state != TaskState.COMPLETED:
                self.task_registry.update_task_state(
                    spec_name=spec_name,
                    task_id=task_id,
                    new_state=TaskState.COMPLETED
                )
                logger.info(f"Updated task {task_id} state to COMPLETED")
            
            # Find and unblock dependent tasks
            unblocked_count = 0
            for task in taskset.tasks:
                # Check if this task depends on the completed task
                if task_id in task.dependencies:
                    # Check if task is currently blocked
                    if task.state == TaskState.BLOCKED:
                        # Check if all dependencies are now satisfied
                        all_deps_satisfied = True
                        for dep_id in task.dependencies:
                            dep_task = next((t for t in taskset.tasks if t.id == dep_id), None)
                            if dep_task and dep_task.state != TaskState.COMPLETED:
                                all_deps_satisfied = False
                                break
                        
                        # Unblock if all dependencies satisfied
                        if all_deps_satisfied:
                            self.task_registry.update_task_state(
                                spec_name=spec_name,
                                task_id=task.id,
                                new_state=TaskState.PENDING
                            )
                            unblocked_count += 1
                            logger.info(
                                f"Unblocked task {task.id} (all dependencies satisfied)"
                            )
            
            if unblocked_count > 0:
                logger.info(
                    f"Unblocked {unblocked_count} dependent task(s) "
                    f"after merging PR #{pr.pr_number}"
                )
            else:
                logger.debug(
                    f"No tasks to unblock after merging PR #{pr.pr_number}"
                )
        
        except Exception as e:
            logger.error(f"Failed to unblock dependent tasks: {e}")
            # Don't raise exception, dependency unblocking failure shouldn't block other operations
    
    def _load_comment_template(self) -> Optional[Template]:
        """
        Load comment template from file.
        
        Returns:
            Jinja2 Template object or None if template not found
            
        Requirements: 6.4
        """
        if not Template:
            logger.warning("Jinja2 not installed, comment templates not available")
            return None
        
        template_path = Path(self.config.template.comment_template_path)
        
        if not template_path.exists():
            logger.warning(f"Comment template not found: {template_path}")
            return None
        
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            return Template(template_content)
        
        except Exception as e:
            logger.error(f"Failed to load comment template: {e}")
            return None
    
    def post_comment(
        self,
        pr_id: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        use_template: bool = True
    ) -> None:
        """
        Post a comment to a pull request.
        
        Args:
            pr_id: Pull request identifier
            message: Main comment message
            details: Optional dictionary of additional details to include
            use_template: Whether to use comment template (default: True)
            
        Raises:
            PRServiceError: If comment posting fails
            
        Requirements: 6.1
        """
        try:
            logger.info(f"Posting comment to PR {pr_id}")
            
            # Build comment text
            if use_template and self.config.template.comment_template_path:
                # Try to use template
                template = self._load_comment_template()
                if template:
                    comment_text = template.render(
                        message=message,
                        details=details or {}
                    )
                else:
                    # Fallback to plain text
                    comment_text = self._format_comment_plain(message, details)
            else:
                # Use plain text format
                comment_text = self._format_comment_plain(message, details)
            
            # Post comment using Git host client
            self.git_host_client.add_comment(pr_id, comment_text)
            
            # Record comment in metrics
            if self.metrics_collector:
                self.metrics_collector.record_review_comment(pr_id)
                logger.debug(f"Recorded comment metric for PR {pr_id}")
            
            logger.info(f"Successfully posted comment to PR {pr_id}")
        
        except Exception as e:
            logger.error(f"Failed to post comment to PR {pr_id}: {e}")
            raise PRServiceError(f"Comment posting failed: {e}") from e
    
    def _format_comment_plain(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format comment in plain text (fallback when template not available).
        
        Args:
            message: Main comment message
            details: Optional dictionary of additional details
            
        Returns:
            Formatted comment text
            
        Requirements: 6.1
        """
        comment_parts = [message]
        
        if details:
            comment_parts.append("\n### Details")
            for key, value in details.items():
                comment_parts.append(f"- **{key}:** {value}")
        
        comment_parts.append("\n---")
        comment_parts.append("*Posted by NecroCode Review & PR Service*")
        
        return "\n".join(comment_parts)
    
    def post_test_failure_comment(
        self,
        pr_id: str,
        test_results: Dict[str, Any],
        error_log_url: Optional[str] = None,
        artifact_links: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Post an automatic comment when tests fail.
        
        Args:
            pr_id: Pull request identifier
            test_results: Dictionary containing test results
            error_log_url: Optional URL to error logs
            artifact_links: Optional dictionary of artifact names to URLs
            
        Requirements: 6.1, 6.2, 6.3
        """
        if not self.config.ci.auto_comment_on_failure:
            logger.debug("Auto-comment on test failure is disabled")
            return
        
        try:
            logger.info(f"Posting test failure comment to PR {pr_id}")
            
            # Build failure message
            message = "## ❌ Test Failure Detected\n\n"
            message += "The automated tests have failed for this pull request.\n"
            
            # Add test results summary
            if test_results:
                message += "\n### Test Results Summary\n"
                message += f"- **Total Tests:** {test_results.get('total', 0)}\n"
                message += f"- **Passed:** {test_results.get('passed', 0)} ✅\n"
                message += f"- **Failed:** {test_results.get('failed', 0)} ❌\n"
                message += f"- **Skipped:** {test_results.get('skipped', 0)} ⏭️\n"
                
                if 'duration' in test_results:
                    message += f"- **Duration:** {test_results['duration']:.2f}s\n"
                
                # Add failed test details if available
                if 'failed_tests' in test_results and test_results['failed_tests']:
                    message += "\n### Failed Tests\n"
                    for test in test_results['failed_tests'][:10]:  # Limit to first 10
                        test_name = test.get('name', 'Unknown')
                        test_error = test.get('error', 'No error message')
                        message += f"\n**{test_name}**\n```\n{test_error}\n```\n"
                    
                    if len(test_results['failed_tests']) > 10:
                        remaining = len(test_results['failed_tests']) - 10
                        message += f"\n*...and {remaining} more failed tests*\n"
            
            # Add error log link
            if error_log_url:
                message += f"\n### Error Logs\n"
                message += f"📋 [View Full Error Logs]({error_log_url})\n"
            
            # Add artifact links
            if artifact_links:
                message += "\n### Related Artifacts\n"
                for name, url in artifact_links.items():
                    message += f"- [{name}]({url})\n"
            
            message += "\n### Next Steps\n"
            message += "1. Review the test failures above\n"
            message += "2. Fix the failing tests\n"
            message += "3. Push your changes to trigger a new CI run\n"
            
            # Post the comment
            self.post_comment(pr_id, message, use_template=False)
            
            logger.info(f"Successfully posted test failure comment to PR {pr_id}")
        
        except Exception as e:
            logger.error(f"Failed to post test failure comment to PR {pr_id}: {e}")
            # Don't raise exception, comment posting failure shouldn't block other operations
    
    def merge_pr(
        self,
        pr_id: str,
        merge_strategy: Optional[MergeStrategy] = None,
        delete_branch: Optional[bool] = None,
        check_ci: bool = True,
        check_approvals: bool = True,
        check_conflicts: bool = True
    ) -> None:
        """
        Merge a pull request with configured strategy.
        
        Performs pre-merge checks and merges the PR using the specified
        or configured merge strategy.
        
        Args:
            pr_id: Pull request identifier
            merge_strategy: Merge strategy to use (overrides config if provided)
            delete_branch: Whether to delete branch after merge (overrides config if provided)
            check_ci: Whether to check CI status before merging
            check_approvals: Whether to check required approvals before merging
            check_conflicts: Whether to check for conflicts before merging
            
        Raises:
            PRServiceError: If merge fails or pre-merge checks fail
            
        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
        """
        try:
            logger.info(f"Attempting to merge PR {pr_id}")
            
            # Get PR details
            pr = self.git_host_client.get_pr(pr_id)
            
            # Use configured strategy if not provided
            strategy = merge_strategy or self.config.merge.strategy
            should_delete = delete_branch if delete_branch is not None else self.config.merge.delete_branch_after_merge
            
            # Perform pre-merge checks
            self._perform_merge_checks(
                pr=pr,
                check_ci=check_ci,
                check_approvals=check_approvals,
                check_conflicts=check_conflicts
            )
            
            # Map our MergeStrategy enum to git host client format
            merge_method = strategy.value  # "merge", "squash", or "rebase"
            
            logger.info(
                f"Merging PR #{pr.pr_number} with strategy '{merge_method}', "
                f"delete_branch={should_delete}"
            )
            
            # Perform the merge
            self.git_host_client.merge_pr(
                pr_id=pr_id,
                merge_method=merge_method,
                delete_branch=should_delete
            )
            
            # Update PR object
            pr.mark_as_merged()
            
            # Handle post-merge operations
            self.handle_pr_merged(
                pr=pr,
                delete_branch=should_delete,
                return_slot=True,
                unblock_dependencies=True
            )
            
            logger.info(f"Successfully merged PR #{pr.pr_number}")
        
        except Exception as e:
            logger.error(f"Failed to merge PR {pr_id}: {e}")
            self._record_merge_failure(pr_id, str(e))
            raise PRServiceError(f"PR merge failed: {e}") from e
    
    def _perform_merge_checks(
        self,
        pr: PullRequest,
        check_ci: bool = True,
        check_approvals: bool = True,
        check_conflicts: bool = True
    ) -> None:
        """
        Perform pre-merge checks on a pull request.
        
        Args:
            pr: PullRequest object
            check_ci: Whether to check CI status
            check_approvals: Whether to check required approvals
            check_conflicts: Whether to check for conflicts
            
        Raises:
            PRServiceError: If any check fails
            
        Requirements: 9.2, 9.3, 9.4
        """
        logger.debug(f"Performing merge checks for PR #{pr.pr_number}")
        
        # Check if PR is in mergeable state
        if pr.state != PRState.OPEN:
            raise PRServiceError(
                f"PR #{pr.pr_number} is not open (state: {pr.state.value})"
            )
        
        if pr.draft:
            raise PRServiceError(
                f"PR #{pr.pr_number} is still in draft state"
            )
        
        # Check CI status if required
        if check_ci and self.config.merge.require_ci_success:
            logger.debug(f"Checking CI status for PR #{pr.pr_number}")
            
            ci_status = self.git_host_client.get_ci_status(pr.pr_id)
            
            if ci_status != CIStatus.SUCCESS:
                raise PRServiceError(
                    f"PR #{pr.pr_number} CI status is {ci_status.value}, "
                    f"expected SUCCESS"
                )
            
            logger.debug(f"CI check passed for PR #{pr.pr_number}")
        
        # Check required approvals if required
        if check_approvals and self.config.merge.required_approvals > 0:
            logger.debug(
                f"Checking approvals for PR #{pr.pr_number} "
                f"(required: {self.config.merge.required_approvals})"
            )
            
            # Get current approval count
            approval_count = self._get_approval_count(pr)
            
            if approval_count < self.config.merge.required_approvals:
                raise PRServiceError(
                    f"PR #{pr.pr_number} has {approval_count} approval(s), "
                    f"but {self.config.merge.required_approvals} required"
                )
            
            logger.debug(
                f"Approval check passed for PR #{pr.pr_number} "
                f"({approval_count} approvals)"
            )
        
        # Check for conflicts if required
        if check_conflicts and self.config.merge.check_conflicts:
            logger.debug(f"Checking for conflicts in PR #{pr.pr_number}")
            
            has_conflicts = self.git_host_client.check_conflicts(pr.pr_id)
            
            if has_conflicts:
                raise PRServiceError(
                    f"PR #{pr.pr_number} has merge conflicts that must be resolved"
                )
            
            logger.debug(f"Conflict check passed for PR #{pr.pr_number}")
        
        logger.debug(f"All merge checks passed for PR #{pr.pr_number}")
    
    def _get_approval_count(self, pr: PullRequest) -> int:
        """
        Get the number of approvals for a pull request.
        
        This is a simplified implementation. In production, this would
        query the Git host API to get actual approval counts.
        
        Args:
            pr: PullRequest object
            
        Returns:
            Number of approvals
            
        Requirements: 9.3
        """
        # For now, return 0 as a placeholder
        # In production, this would query the Git host API
        # Example for GitHub: pr.get_reviews() and count APPROVED reviews
        # Example for GitLab: mr.approvals.get().approved_by
        # Example for Bitbucket: pr.participants with "approved" status
        
        # Check if approval count is stored in metadata
        if "approval_count" in pr.metadata:
            return pr.metadata["approval_count"]
        
        # Default to 0 (would need actual API implementation)
        logger.warning(
            f"Approval count not available for PR #{pr.pr_number}, "
            "returning 0 (implement Git host-specific approval checking)"
        )
        return 0
    
    def _record_merge_failure(self, pr_id: str, error_message: str) -> None:
        """
        Record merge failure event in Task Registry.
        
        Args:
            pr_id: Pull request identifier
            error_message: Error message describing the failure
            
        Requirements: 9.5
        """
        if not self.task_registry:
            logger.warning("Task Registry not configured, skipping merge failure recording")
            return
        
        try:
            # Get PR details to extract task information
            pr = self.git_host_client.get_pr(pr_id)
            
            spec_name = pr.spec_id or "unknown"
            task_id = pr.task_id or "unknown"
            
            # Create merge failure event
            event = TaskEvent(
                event_type=EventType.TASK_FAILED,
                spec_name=spec_name,
                task_id=task_id,
                timestamp=datetime.now(),
                details={
                    "event": "merge_failed",
                    "pr_url": pr.url,
                    "pr_number": pr.pr_number,
                    "pr_id": pr.pr_id,
                    "error": error_message,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            
            # Record event
            self.task_registry.event_store.record_event(event)
            
            logger.info(
                f"Recorded merge failure event for PR #{pr.pr_number}: {error_message}"
            )
        
        except Exception as e:
            logger.error(f"Failed to record merge failure event: {e}")
            # Don't raise exception, just log the error
    
    def auto_merge_on_ci_success(
        self,
        pr_id: str,
        merge_strategy: Optional[MergeStrategy] = None
    ) -> bool:
        """
        Automatically merge PR when CI succeeds.
        
        This method should be called when CI status changes to SUCCESS.
        It checks if auto-merge is enabled and all conditions are met,
        then merges the PR.
        
        Args:
            pr_id: Pull request identifier
            merge_strategy: Optional merge strategy to use
            
        Returns:
            True if PR was merged, False otherwise
            
        Requirements: 9.2
        """
        if not self.config.merge.auto_merge_enabled:
            logger.debug("Auto-merge is disabled")
            return False
        
        try:
            logger.info(f"Checking auto-merge conditions for PR {pr_id}")
            
            # Get PR details
            pr = self.git_host_client.get_pr(pr_id)
            
            # Check if PR is eligible for auto-merge
            if pr.state != PRState.OPEN:
                logger.debug(f"PR #{pr.pr_number} is not open, skipping auto-merge")
                return False
            
            if pr.draft:
                logger.debug(f"PR #{pr.pr_number} is draft, skipping auto-merge")
                return False
            
            # Check CI status
            ci_status = self.git_host_client.get_ci_status(pr.pr_id)
            if ci_status != CIStatus.SUCCESS:
                logger.debug(
                    f"PR #{pr.pr_number} CI status is {ci_status.value}, "
                    "skipping auto-merge"
                )
                return False
            
            # Check required approvals
            if self.config.merge.required_approvals > 0:
                approval_count = self._get_approval_count(pr)
                if approval_count < self.config.merge.required_approvals:
                    logger.debug(
                        f"PR #{pr.pr_number} has {approval_count} approval(s), "
                        f"but {self.config.merge.required_approvals} required, "
                        "skipping auto-merge"
                    )
                    return False
            
            # Check for conflicts
            if self.config.merge.check_conflicts:
                has_conflicts = self.git_host_client.check_conflicts(pr.pr_id)
                if has_conflicts:
                    logger.warning(
                        f"PR #{pr.pr_number} has conflicts, skipping auto-merge"
                    )
                    return False
            
            # All conditions met, perform auto-merge
            logger.info(f"Auto-merging PR #{pr.pr_number}")
            
            self.merge_pr(
                pr_id=pr_id,
                merge_strategy=merge_strategy,
                check_ci=False,  # Already checked
                check_approvals=False,  # Already checked
                check_conflicts=False  # Already checked
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Auto-merge failed for PR {pr_id}: {e}")
            return False
    
    def check_merge_conflicts(self, pr_id: str) -> Dict[str, Any]:
        """
        Check if a pull request has merge conflicts.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            Dictionary with conflict information:
            - has_conflicts: bool
            - details: Optional conflict details
            
        Raises:
            PRServiceError: If conflict check fails
            
        Requirements: 9.4, 13.1
        """
        try:
            logger.info(f"Checking for merge conflicts in PR {pr_id}")
            
            # Get PR details
            pr = self.git_host_client.get_pr(pr_id)
            
            # Check for conflicts using Git host client
            has_conflicts = self.git_host_client.check_conflicts(pr.pr_id)
            
            result = {
                "pr_id": pr_id,
                "pr_number": pr.pr_number,
                "has_conflicts": has_conflicts,
                "checked_at": datetime.now().isoformat(),
            }
            
            if has_conflicts:
                logger.warning(f"PR #{pr.pr_number} has merge conflicts")
                result["details"] = {
                    "message": "This pull request has merge conflicts that must be resolved",
                    "source_branch": pr.source_branch,
                    "target_branch": pr.target_branch,
                }
            else:
                logger.info(f"PR #{pr.pr_number} has no merge conflicts")
                result["details"] = {
                    "message": "No merge conflicts detected",
                }
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to check conflicts for PR {pr_id}: {e}")
            raise PRServiceError(f"Conflict check failed: {e}") from e
    
    def _check_and_handle_conflicts(self, pr: PullRequest) -> bool:
        """
        Check for conflicts and handle them (post comment, record event).
        
        Args:
            pr: PullRequest object
            
        Returns:
            True if conflicts were detected, False otherwise
            
        Requirements: 13.1, 13.2, 13.3
        """
        try:
            logger.debug(f"Checking for conflicts in PR #{pr.pr_number}")
            
            # Check for conflicts
            conflict_result = self.check_merge_conflicts(pr.pr_id)
            
            if conflict_result["has_conflicts"]:
                logger.warning(f"Conflicts detected in PR #{pr.pr_number}")
                
                # Post conflict comment if enabled
                if self.config.conflict_detection.auto_comment:
                    conflict_details = conflict_result.get("details", {})
                    conflict_details["source_branch"] = pr.source_branch
                    conflict_details["target_branch"] = pr.target_branch
                    
                    self.post_conflict_comment(pr.pr_id, conflict_details)
                
                return True
            else:
                logger.debug(f"No conflicts detected in PR #{pr.pr_number}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to check and handle conflicts for PR #{pr.pr_number}: {e}")
            return False
    
    def post_conflict_comment(
        self,
        pr_id: str,
        conflict_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Post a comment about merge conflicts to a pull request.
        
        Args:
            pr_id: Pull request identifier
            conflict_details: Optional dictionary with conflict details
            
        Requirements: 13.2
        """
        try:
            logger.info(f"Posting conflict comment to PR {pr_id}")
            
            # Build conflict message
            message = "## ⚠️ Merge Conflicts Detected\n\n"
            message += "This pull request has merge conflicts that must be resolved before it can be merged.\n"
            
            if conflict_details:
                if "source_branch" in conflict_details and "target_branch" in conflict_details:
                    message += f"\n**Branches:**\n"
                    message += f"- Source: `{conflict_details['source_branch']}`\n"
                    message += f"- Target: `{conflict_details['target_branch']}`\n"
                
                if "conflicting_files" in conflict_details:
                    message += f"\n**Conflicting Files:**\n"
                    for file in conflict_details["conflicting_files"]:
                        message += f"- `{file}`\n"
            
            message += "\n### How to Resolve\n"
            message += "1. Pull the latest changes from the target branch\n"
            message += "2. Resolve the conflicts in your local branch\n"
            message += "3. Push the resolved changes\n"
            
            # Post the comment
            self.post_comment(pr_id, message, use_template=False)
            
            # Record conflict detection event
            if self.task_registry:
                try:
                    pr = self.git_host_client.get_pr(pr_id)
                    spec_name = pr.spec_id or "unknown"
                    task_id = pr.task_id or "unknown"
                    
                    event = TaskEvent(
                        event_type=EventType.TASK_UPDATED,
                        spec_name=spec_name,
                        task_id=task_id,
                        timestamp=datetime.now(),
                        details={
                            "event": "conflicts_detected",
                            "pr_number": pr.pr_number,
                            "pr_id": pr_id,
                            "conflict_details": conflict_details or {},
                        }
                    )
                    
                    self.task_registry.event_store.record_event(event)
                    logger.debug(f"Recorded conflict detection event for task {task_id}")
                except Exception as e:
                    logger.error(f"Failed to record conflict detection event: {e}")
            
            logger.info(f"Successfully posted conflict comment to PR {pr_id}")
        
        except Exception as e:
            logger.error(f"Failed to post conflict comment to PR {pr_id}: {e}")
            # Don't raise exception, comment posting failure shouldn't block other operations
    
    def convert_draft_to_ready(
        self,
        pr_id: str,
        assign_reviewers: bool = True,
        update_labels: bool = True
    ) -> None:
        """
        Convert a draft PR to ready for review.
        
        This method:
        1. Converts the PR from draft to ready state
        2. Optionally assigns reviewers (if not skipped for drafts)
        3. Optionally updates labels (removes draft label)
        
        Args:
            pr_id: Pull request identifier
            assign_reviewers: Whether to assign reviewers after conversion
            update_labels: Whether to update labels after conversion
            
        Raises:
            PRServiceError: If conversion fails
            
        Requirements: 12.2
        """
        if not self.config.draft.enabled:
            logger.warning("Draft feature is disabled, skipping conversion")
            return
        
        try:
            logger.info(f"Converting draft PR {pr_id} to ready for review")
            
            # Get current PR details
            pr = self.git_host_client.get_pr(pr_id)
            
            # Check if PR is actually a draft
            if not pr.draft:
                logger.warning(f"PR #{pr.pr_number} is not a draft, skipping conversion")
                return
            
            # Convert to ready using Git host client
            self.git_host_client.convert_to_ready(pr_id)
            
            # Update PR object
            pr.convert_from_draft()
            
            logger.info(f"Successfully converted PR #{pr.pr_number} to ready for review")
            
            # Assign reviewers if configured and requested
            if assign_reviewers and self.config.reviewers.enabled:
                # Get task information from PR metadata
                if pr.task_id and pr.spec_id:
                    try:
                        # Get task from Task Registry
                        if self.task_registry:
                            taskset = self.task_registry.get_taskset(pr.spec_id)
                            task = next((t for t in taskset.tasks if t.id == pr.task_id), None)
                            
                            if task:
                                logger.info(f"Assigning reviewers to PR #{pr.pr_number}")
                                self._assign_reviewers(pr, task)
                            else:
                                logger.warning(
                                    f"Task {pr.task_id} not found in spec {pr.spec_id}, "
                                    "skipping reviewer assignment"
                                )
                    except Exception as e:
                        logger.error(f"Failed to assign reviewers after draft conversion: {e}")
            
            # Update labels if configured and requested
            if update_labels and self.config.labels.enabled:
                try:
                    # Remove draft label
                    draft_label = self.config.draft.draft_label
                    if draft_label in pr.labels:
                        self.git_host_client.remove_label(pr_id, draft_label)
                        logger.info(f"Removed draft label '{draft_label}' from PR #{pr.pr_number}")
                except Exception as e:
                    logger.error(f"Failed to update labels after draft conversion: {e}")
            
            # Record conversion event in Task Registry
            if self.task_registry and pr.spec_id and pr.task_id:
                try:
                    event = TaskEvent(
                        event_type=EventType.TASK_UPDATED,
                        spec_name=pr.spec_id,
                        task_id=pr.task_id,
                        timestamp=datetime.now(),
                        details={
                            "event": "draft_converted_to_ready",
                            "pr_url": pr.url,
                            "pr_number": pr.pr_number,
                            "pr_id": pr.pr_id,
                        }
                    )
                    
                    self.task_registry.event_store.record_event(event)
                    logger.debug(f"Recorded draft conversion event for task {pr.task_id}")
                except Exception as e:
                    logger.error(f"Failed to record draft conversion event: {e}")
        
        except Exception as e:
            logger.error(f"Failed to convert draft PR {pr_id} to ready: {e}")
            raise PRServiceError(f"Draft conversion failed: {e}") from e
    
    def convert_draft_on_ci_success(
        self,
        pr_id: str
    ) -> bool:
        """
        Convert draft PR to ready when CI succeeds.
        
        This method should be called when CI status changes to SUCCESS
        for a draft PR. It checks if auto-conversion is enabled and
        converts the PR to ready for review.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            True if PR was converted, False otherwise
            
        Requirements: 12.2
        """
        if not self.config.draft.enabled or not self.config.draft.convert_on_ci_success:
            logger.debug("Draft auto-conversion on CI success is disabled")
            return False
        
        try:
            logger.info(f"Checking draft auto-conversion for PR {pr_id}")
            
            # Get PR details
            pr = self.git_host_client.get_pr(pr_id)
            
            # Check if PR is a draft
            if not pr.draft:
                logger.debug(f"PR #{pr.pr_number} is not a draft, skipping conversion")
                return False
            
            # Check CI status
            ci_status = self.git_host_client.get_ci_status(pr.pr_id)
            if ci_status != CIStatus.SUCCESS:
                logger.debug(
                    f"PR #{pr.pr_number} CI status is {ci_status.value}, "
                    "skipping draft conversion"
                )
                return False
            
            # Convert to ready
            logger.info(f"Auto-converting draft PR #{pr.pr_number} to ready (CI success)")
            
            self.convert_draft_to_ready(
                pr_id=pr_id,
                assign_reviewers=True,
                update_labels=True
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Draft auto-conversion failed for PR {pr_id}: {e}")
            return False
    
    def recheck_conflicts_after_resolution(
        self,
        pr_id: str,
        post_success_comment: bool = True
    ) -> bool:
        """
        Re-check for conflicts after resolution attempt.
        
        This method should be called after a developer pushes changes
        to resolve conflicts. It checks if conflicts are resolved and
        optionally posts a success comment.
        
        Args:
            pr_id: Pull request identifier
            post_success_comment: Whether to post a comment if conflicts are resolved
            
        Returns:
            True if conflicts are resolved, False if conflicts still exist
            
        Requirements: 13.4
        """
        try:
            logger.info(f"Re-checking conflicts for PR {pr_id}")
            
            # Get PR details
            pr = self.git_host_client.get_pr(pr_id)
            
            # Check for conflicts
            conflict_result = self.check_merge_conflicts(pr_id)
            
            if conflict_result["has_conflicts"]:
                logger.warning(f"Conflicts still exist in PR #{pr.pr_number}")
                return False
            else:
                logger.info(f"Conflicts resolved in PR #{pr.pr_number}")
                
                # Post success comment if requested
                if post_success_comment and self.config.conflict_detection.auto_comment:
                    message = "## ✅ Conflicts Resolved\n\n"
                    message += "The merge conflicts in this pull request have been resolved. "
                    message += "The PR can now proceed with the review process.\n"
                    
                    self.post_comment(pr_id, message, use_template=False)
                
                # Record conflict resolution event
                if self.task_registry:
                    try:
                        spec_name = pr.spec_id or "unknown"
                        task_id = pr.task_id or "unknown"
                        
                        event = TaskEvent(
                            event_type=EventType.TASK_UPDATED,
                            spec_name=spec_name,
                            task_id=task_id,
                            timestamp=datetime.now(),
                            details={
                                "event": "conflicts_resolved",
                                "pr_number": pr.pr_number,
                                "pr_id": pr_id,
                            }
                        )
                        
                        self.task_registry.event_store.record_event(event)
                        logger.debug(f"Recorded conflict resolution event for task {task_id}")
                    except Exception as e:
                        logger.error(f"Failed to record conflict resolution event: {e}")
                
                return True
        
        except Exception as e:
            logger.error(f"Failed to re-check conflicts for PR {pr_id}: {e}")
            return False
    
    def periodic_conflict_check(
        self,
        pr_ids: Optional[List[str]] = None,
        only_open_prs: bool = True
    ) -> Dict[str, bool]:
        """
        Perform periodic conflict checking on multiple PRs.
        
        This method can be called periodically (e.g., via a cron job or scheduler)
        to check for conflicts in open PRs. It's useful for detecting conflicts
        that arise when the target branch is updated.
        
        Args:
            pr_ids: Optional list of specific PR IDs to check. If None, checks all open PRs.
            only_open_prs: Whether to only check open PRs (default: True)
            
        Returns:
            Dictionary mapping PR IDs to conflict status (True if conflicts exist)
            
        Requirements: 13.5
        """
        if not self.config.conflict_detection.enabled or not self.config.conflict_detection.periodic_check:
            logger.debug("Periodic conflict checking is disabled")
            return {}
        
        try:
            logger.info("Starting periodic conflict check")
            
            results = {}
            
            # If no specific PR IDs provided, we would need to query the Git host
            # for all open PRs. For now, we'll work with the provided list.
            if pr_ids is None:
                logger.warning(
                    "No PR IDs provided for periodic conflict check. "
                    "In production, this would query the Git host for all open PRs."
                )
                return results
            
            # Check each PR for conflicts
            for pr_id in pr_ids:
                try:
                    # Get PR details
                    pr = self.git_host_client.get_pr(pr_id)
                    
                    # Skip if not open and only_open_prs is True
                    if only_open_prs and pr.state != PRState.OPEN:
                        logger.debug(f"Skipping PR #{pr.pr_number} (not open)")
                        continue
                    
                    # Check for conflicts
                    has_conflicts = self._check_and_handle_conflicts(pr)
                    results[pr_id] = has_conflicts
                    
                    if has_conflicts:
                        logger.warning(f"Periodic check: Conflicts found in PR #{pr.pr_number}")
                    else:
                        logger.debug(f"Periodic check: No conflicts in PR #{pr.pr_number}")
                
                except Exception as e:
                    logger.error(f"Failed to check PR {pr_id} during periodic check: {e}")
                    results[pr_id] = None  # Indicate check failed
            
            logger.info(
                f"Periodic conflict check complete: "
                f"{sum(1 for v in results.values() if v)} PRs with conflicts, "
                f"{sum(1 for v in results.values() if v is False)} PRs without conflicts"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Periodic conflict check failed: {e}")
            return {}
    
    def handle_draft_pr_creation(
        self,
        pr: PullRequest,
        task: Task
    ) -> None:
        """
        Handle special processing for draft PR creation.
        
        This method applies draft-specific handling:
        1. Skips reviewer assignment if configured
        2. Adds draft label
        3. Records draft creation event
        
        Args:
            pr: PullRequest object (draft PR)
            task: Task object
            
        Requirements: 12.3, 12.4
        """
        if not self.config.draft.enabled:
            logger.debug("Draft feature is disabled")
            return
        
        if not pr.draft:
            logger.debug(f"PR #{pr.pr_number} is not a draft")
            return
        
        try:
            logger.info(f"Handling draft PR creation for PR #{pr.pr_number}")
            
            # Add draft label if configured
            if self.config.labels.enabled:
                draft_label = self.config.draft.draft_label
                try:
                    self.git_host_client.add_labels(pr.pr_id, [draft_label])
                    logger.info(f"Added draft label '{draft_label}' to PR #{pr.pr_number}")
                except Exception as e:
                    logger.error(f"Failed to add draft label: {e}")
            
            # Record draft creation event in Task Registry
            if self.task_registry:
                try:
                    spec_name = pr.spec_id or task.spec_name if hasattr(task, 'spec_name') else "unknown"
                    
                    event = TaskEvent(
                        event_type=EventType.TASK_UPDATED,
                        spec_name=spec_name,
                        task_id=task.id,
                        timestamp=datetime.now(),
                        details={
                            "event": "draft_pr_created",
                            "pr_url": pr.url,
                            "pr_number": pr.pr_number,
                            "pr_id": pr.pr_id,
                            "draft": True,
                        }
                    )
                    
                    self.task_registry.event_store.record_event(event)
                    logger.debug(f"Recorded draft PR creation event for task {task.id}")
                except Exception as e:
                    logger.error(f"Failed to record draft PR creation event: {e}")
            
            logger.info(f"Successfully handled draft PR creation for PR #{pr.pr_number}")
        
        except Exception as e:
            logger.error(f"Failed to handle draft PR creation for PR #{pr.pr_number}: {e}")
            # Don't raise exception, draft handling failure shouldn't block PR creationonflicts in your local branch\n"
            message += "3. Commit the resolved changes\n"
            message += "4. Push to update this pull request\n"
            
            # Post the comment
            self.post_comment(pr_id, message, use_template=False)
            
            # Record conflict detection event
            if self.task_registry:
                pr = self.git_host_client.get_pr(pr_id)
                spec_name = pr.spec_id or "unknown"
                task_id = pr.task_id or "unknown"
                
                event = TaskEvent(
                    event_type=EventType.TASK_UPDATED,
                    spec_name=spec_name,
                    task_id=task_id,
                    timestamp=datetime.now(),
                    details={
                        "event": "conflicts_detected",
                        "pr_number": pr.pr_number,
                        "pr_id": pr_id,
                        "conflict_details": conflict_details or {},
                    }
                )
                
                self.task_registry.event_store.record_event(event)
            
            logger.info(f"Successfully posted conflict comment to PR {pr_id}")
        
        except Exception as e:
            logger.error(f"Failed to post conflict comment to PR {pr_id}: {e}")
            # Don't raise exception, comment posting failure shouldn't block other operations

    def record_ci_started(self, pr_id: str) -> None:
        """
        Record CI execution start for metrics tracking.
        
        Args:
            pr_id: Pull request identifier
            
        Requirements: 14.3
        """
        if self.metrics_collector:
            self.metrics_collector.record_ci_started(pr_id)
            logger.debug(f"Recorded CI start for PR {pr_id}")
    
    def record_ci_completed(self, pr_id: str, status: CIStatus) -> None:
        """
        Record CI execution completion for metrics tracking.
        
        Args:
            pr_id: Pull request identifier
            status: CI status
            
        Requirements: 14.3
        """
        if self.metrics_collector:
            self.metrics_collector.record_ci_completed(pr_id, status)
            logger.info(f"Recorded CI completion for PR {pr_id}: {status.value}")
    
    def update_pr_stats(self, pr: PullRequest) -> None:
        """
        Update PR statistics in metrics collector.
        
        Args:
            pr: PullRequest object with updated metadata
            
        Requirements: 14.1
        """
        if self.metrics_collector:
            self.metrics_collector.update_pr_stats(pr)
            logger.debug(f"Updated stats for PR #{pr.pr_number}")
    
    def get_pr_metrics(self, pr_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific PR.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            Dictionary containing PR metrics or None if not found
            
        Requirements: 14.1, 14.2, 14.3
        """
        if not self.metrics_collector:
            logger.warning("Metrics collector not initialized")
            return None
        
        metrics = self.metrics_collector.get_metrics(pr_id)
        if metrics:
            return metrics.to_dict()
        return None
    
    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """
        Get aggregate metrics across all PRs.
        
        Returns:
            Dictionary containing aggregate statistics
            
        Requirements: 14.1, 14.2, 14.3, 14.4
        """
        if not self.metrics_collector:
            logger.warning("Metrics collector not initialized")
            return {}
        
        return self.metrics_collector.get_aggregate_stats()
    
    def calculate_merge_rate(self, prs: List[PullRequest]) -> float:
        """
        Calculate merge rate from a list of PRs.
        
        Args:
            prs: List of PullRequest objects
            
        Returns:
            Merge rate as a percentage (0-100)
            
        Requirements: 14.4
        """
        if not self.metrics_collector:
            logger.warning("Metrics collector not initialized")
            return 0.0
        
        return self.metrics_collector.calculate_merge_rate(prs)
    
    def export_metrics(self, output_path: Path) -> None:
        """
        Export all metrics to a JSON file.
        
        Args:
            output_path: Path to export metrics to
            
        Raises:
            PRServiceError: If metrics export fails
            
        Requirements: 14.1, 14.2, 14.3, 14.4
        """
        if not self.metrics_collector:
            raise PRServiceError("Metrics collector not initialized")
        
        self.metrics_collector.export_metrics(output_path)
        logger.info(f"Exported metrics to {output_path}")
    
    def export_prometheus_metrics(self, output_path: Optional[Path] = None) -> str:
        """
        Export metrics in Prometheus format.
        
        Args:
            output_path: Optional path to export metrics to file
            
        Returns:
            Metrics in Prometheus exposition format
            
        Raises:
            PRServiceError: If Prometheus exporter not initialized
            
        Requirements: 14.5
        """
        if not self.prometheus_exporter:
            raise PRServiceError("Prometheus exporter not initialized")
        
        metrics_text = self.prometheus_exporter.export_metrics()
        
        if output_path:
            self.prometheus_exporter.export_to_file(output_path)
            logger.info(f"Exported Prometheus metrics to {output_path}")
        
        return metrics_text

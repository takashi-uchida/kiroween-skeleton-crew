"""
Configuration management for Review & PR Service.

Defines configuration classes and utilities for service setup.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any
import os
import yaml
import json


class GitHostType(Enum):
    """Supported Git hosting platforms."""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class MergeStrategy(Enum):
    """PR merge strategies."""
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class ReviewerStrategy(Enum):
    """Reviewer assignment strategies."""
    ROUND_ROBIN = "round-robin"
    LOAD_BALANCED = "load-balanced"
    CODEOWNERS = "codeowners"
    MANUAL = "manual"


@dataclass
class LabelConfig:
    """Configuration for automatic label management."""
    
    enabled: bool = True
    rules: Dict[str, List[str]] = field(default_factory=dict)
    ci_status_labels: bool = True
    priority_labels: bool = True
    
    def __post_init__(self):
        """Initialize default label rules if not provided."""
        if not self.rules:
            self.rules = {
                "backend": ["backend", "api"],
                "frontend": ["frontend", "ui"],
                "database": ["database", "db"],
                "devops": ["devops", "infrastructure"],
                "documentation": ["docs"],
                "testing": ["testing", "qa"],
            }


@dataclass
class ReviewerConfig:
    """Configuration for automatic reviewer assignment."""
    
    enabled: bool = True
    strategy: ReviewerStrategy = ReviewerStrategy.ROUND_ROBIN
    codeowners_path: Optional[str] = None
    default_reviewers: List[str] = field(default_factory=list)
    type_reviewers: Dict[str, List[str]] = field(default_factory=dict)
    max_reviewers: int = 2
    skip_draft_prs: bool = True
    
    def __post_init__(self):
        """Validate reviewer configuration."""
        if self.strategy == ReviewerStrategy.CODEOWNERS and not self.codeowners_path:
            self.codeowners_path = ".github/CODEOWNERS"
        
        # Initialize default type-based reviewers if not provided
        if not self.type_reviewers:
            self.type_reviewers = {
                "backend": [],
                "frontend": [],
                "database": [],
                "devops": [],
                "documentation": [],
                "testing": [],
            }


@dataclass
class MergeConfig:
    """Configuration for PR merge behavior."""
    
    strategy: MergeStrategy = MergeStrategy.SQUASH
    auto_merge_enabled: bool = False
    delete_branch_after_merge: bool = True
    require_ci_success: bool = True
    required_approvals: int = 1
    check_conflicts: bool = True


@dataclass
class TemplateConfig:
    """Configuration for PR template generation."""
    
    template_path: Optional[str] = None
    comment_template_path: Optional[str] = None
    include_test_results: bool = True
    include_artifact_links: bool = True
    include_execution_logs: bool = True
    custom_sections: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default template paths if not provided."""
        if not self.template_path:
            self.template_path = "templates/pr-template.md"
        if not self.comment_template_path:
            self.comment_template_path = "templates/comment-template.md"


@dataclass
class CIConfig:
    """Configuration for CI status monitoring."""
    
    enabled: bool = True
    polling_interval: int = 60  # seconds
    timeout: int = 3600  # seconds (1 hour)
    auto_comment_on_failure: bool = True
    update_pr_on_status_change: bool = True
    comment_on_success: bool = False  # Optional: comment on CI success


@dataclass
class WebhookConfig:
    """Configuration for webhook handling."""
    
    enabled: bool = False
    port: int = 8080
    host: str = "0.0.0.0"
    path: str = "/webhook"
    secret: Optional[str] = None
    verify_signature: bool = True
    async_processing: bool = True
    
    def __post_init__(self):
        """Load webhook secret from environment if not provided."""
        if not self.secret:
            self.secret = os.getenv("WEBHOOK_SECRET")


@dataclass
class DraftConfig:
    """Configuration for draft PR functionality."""
    
    enabled: bool = True
    create_as_draft: bool = True
    convert_on_ci_success: bool = True
    skip_reviewers: bool = True
    draft_label: str = "draft"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    retry_on_rate_limit: bool = True


@dataclass
class ConflictDetectionConfig:
    """Configuration for conflict detection functionality."""
    
    enabled: bool = True
    check_on_creation: bool = True
    auto_comment: bool = True
    periodic_check: bool = True
    check_interval: int = 3600  # seconds (1 hour)
    recheck_on_push: bool = True


@dataclass
class PRServiceConfig:
    """
    Main configuration class for Review & PR Service.
    
    This class aggregates all configuration settings and provides
    methods for loading from files and environment variables.
    """
    
    # Git host settings
    git_host_type: GitHostType = GitHostType.GITHUB
    git_host_url: Optional[str] = None
    api_token: Optional[str] = None
    repository: Optional[str] = None
    
    # Feature configurations
    labels: LabelConfig = field(default_factory=LabelConfig)
    reviewers: ReviewerConfig = field(default_factory=ReviewerConfig)
    merge: MergeConfig = field(default_factory=MergeConfig)
    template: TemplateConfig = field(default_factory=TemplateConfig)
    ci: CIConfig = field(default_factory=CIConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    draft: DraftConfig = field(default_factory=DraftConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    conflict_detection: ConflictDetectionConfig = field(default_factory=ConflictDetectionConfig)
    
    # Integration settings
    artifact_store_url: Optional[str] = None
    task_registry_path: Optional[str] = None
    repo_pool_url: Optional[str] = None
    
    # Logging and monitoring
    log_level: str = "INFO"
    metrics_enabled: bool = True
    metrics_port: int = 9090
    metrics_storage_path: Optional[str] = None
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        self._load_from_env()
    
    def _load_from_env(self):
        """Load sensitive configuration from environment variables."""
        if not self.api_token:
            token_var = f"{self.git_host_type.value.upper()}_TOKEN"
            self.api_token = os.getenv(token_var) or os.getenv("GIT_HOST_TOKEN")
        
        if not self.git_host_url:
            url_var = f"{self.git_host_type.value.upper()}_URL"
            self.git_host_url = os.getenv(url_var)
        
        if not self.repository:
            self.repository = os.getenv("REPOSITORY")
        
        if not self.artifact_store_url:
            self.artifact_store_url = os.getenv("ARTIFACT_STORE_URL")
        
        if not self.task_registry_path:
            self.task_registry_path = os.getenv(
                "TASK_REGISTRY_PATH",
                str(Path.home() / ".necrocode" / "task_registry")
            )
        
        if not self.metrics_storage_path and self.metrics_enabled:
            self.metrics_storage_path = os.getenv(
                "METRICS_STORAGE_PATH",
                str(Path.home() / ".necrocode" / "pr_metrics.json")
            )
    
    @classmethod
    def from_yaml(cls, path: str) -> "PRServiceConfig":
        """
        Load configuration from YAML file.
        
        Args:
            path: Path to YAML configuration file
            
        Returns:
            PRServiceConfig instance
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data.get("pr_service", {}))
    
    @classmethod
    def from_json(cls, path: str) -> "PRServiceConfig":
        """
        Load configuration from JSON file.
        
        Args:
            path: Path to JSON configuration file
            
        Returns:
            PRServiceConfig instance
        """
        with open(path, "r") as f:
            data = json.load(f)
        
        return cls.from_dict(data.get("pr_service", {}))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PRServiceConfig":
        """
        Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            PRServiceConfig instance
        """
        # Convert string enums
        if "git_host_type" in data and isinstance(data["git_host_type"], str):
            data["git_host_type"] = GitHostType(data["git_host_type"])
        
        # Convert nested configurations
        if "labels" in data and isinstance(data["labels"], dict):
            data["labels"] = LabelConfig(**data["labels"])
        
        if "reviewers" in data and isinstance(data["reviewers"], dict):
            reviewers_data = data["reviewers"].copy()
            if "strategy" in reviewers_data and isinstance(reviewers_data["strategy"], str):
                reviewers_data["strategy"] = ReviewerStrategy(reviewers_data["strategy"])
            data["reviewers"] = ReviewerConfig(**reviewers_data)
        
        if "merge" in data and isinstance(data["merge"], dict):
            merge_data = data["merge"].copy()
            if "strategy" in merge_data and isinstance(merge_data["strategy"], str):
                merge_data["strategy"] = MergeStrategy(merge_data["strategy"])
            data["merge"] = MergeConfig(**merge_data)
        
        if "template" in data and isinstance(data["template"], dict):
            data["template"] = TemplateConfig(**data["template"])
        
        if "ci" in data and isinstance(data["ci"], dict):
            data["ci"] = CIConfig(**data["ci"])
        
        if "webhook" in data and isinstance(data["webhook"], dict):
            data["webhook"] = WebhookConfig(**data["webhook"])
        
        if "draft" in data and isinstance(data["draft"], dict):
            data["draft"] = DraftConfig(**data["draft"])
        
        if "retry" in data and isinstance(data["retry"], dict):
            data["retry"] = RetryConfig(**data["retry"])
        
        if "conflict_detection" in data and isinstance(data["conflict_detection"], dict):
            data["conflict_detection"] = ConflictDetectionConfig(**data["conflict_detection"])
        
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "git_host_type": self.git_host_type.value,
            "git_host_url": self.git_host_url,
            "repository": self.repository,
            "labels": {
                "enabled": self.labels.enabled,
                "rules": self.labels.rules,
                "ci_status_labels": self.labels.ci_status_labels,
                "priority_labels": self.labels.priority_labels,
            },
            "reviewers": {
                "enabled": self.reviewers.enabled,
                "strategy": self.reviewers.strategy.value,
                "codeowners_path": self.reviewers.codeowners_path,
                "default_reviewers": self.reviewers.default_reviewers,
                "type_reviewers": self.reviewers.type_reviewers,
                "max_reviewers": self.reviewers.max_reviewers,
                "skip_draft_prs": self.reviewers.skip_draft_prs,
            },
            "merge": {
                "strategy": self.merge.strategy.value,
                "auto_merge_enabled": self.merge.auto_merge_enabled,
                "delete_branch_after_merge": self.merge.delete_branch_after_merge,
                "require_ci_success": self.merge.require_ci_success,
                "required_approvals": self.merge.required_approvals,
                "check_conflicts": self.merge.check_conflicts,
            },
            "template": {
                "template_path": self.template.template_path,
                "comment_template_path": self.template.comment_template_path,
                "include_test_results": self.template.include_test_results,
                "include_artifact_links": self.template.include_artifact_links,
                "include_execution_logs": self.template.include_execution_logs,
                "custom_sections": self.template.custom_sections,
            },
            "ci": {
                "enabled": self.ci.enabled,
                "polling_interval": self.ci.polling_interval,
                "timeout": self.ci.timeout,
                "auto_comment_on_failure": self.ci.auto_comment_on_failure,
                "update_pr_on_status_change": self.ci.update_pr_on_status_change,
            },
            "webhook": {
                "enabled": self.webhook.enabled,
                "port": self.webhook.port,
                "host": self.webhook.host,
                "path": self.webhook.path,
                "verify_signature": self.webhook.verify_signature,
                "async_processing": self.webhook.async_processing,
            },
            "draft": {
                "enabled": self.draft.enabled,
                "create_as_draft": self.draft.create_as_draft,
                "convert_on_ci_success": self.draft.convert_on_ci_success,
                "skip_reviewers": self.draft.skip_reviewers,
                "draft_label": self.draft.draft_label,
            },
            "retry": {
                "max_retries": self.retry.max_retries,
                "initial_delay": self.retry.initial_delay,
                "max_delay": self.retry.max_delay,
                "exponential_base": self.retry.exponential_base,
                "retry_on_rate_limit": self.retry.retry_on_rate_limit,
            },
            "conflict_detection": {
                "enabled": self.conflict_detection.enabled,
                "check_on_creation": self.conflict_detection.check_on_creation,
                "auto_comment": self.conflict_detection.auto_comment,
                "periodic_check": self.conflict_detection.periodic_check,
                "check_interval": self.conflict_detection.check_interval,
                "recheck_on_push": self.conflict_detection.recheck_on_push,
            },
            "artifact_store_url": self.artifact_store_url,
            "task_registry_path": self.task_registry_path,
            "repo_pool_url": self.repo_pool_url,
            "log_level": self.log_level,
            "metrics_enabled": self.metrics_enabled,
            "metrics_port": self.metrics_port,
            "metrics_storage_path": self.metrics_storage_path,
        }
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.api_token:
            errors.append("API token is required")
        
        if not self.repository:
            errors.append("Repository is required")
        
        if self.reviewers.enabled and self.reviewers.strategy == ReviewerStrategy.CODEOWNERS:
            if not self.reviewers.codeowners_path:
                errors.append("CODEOWNERS path is required when using CODEOWNERS strategy")
        
        if self.webhook.enabled:
            if self.webhook.verify_signature and not self.webhook.secret:
                errors.append("Webhook secret is required when signature verification is enabled")
        
        if self.merge.required_approvals < 0:
            errors.append("Required approvals must be non-negative")
        
        if self.ci.polling_interval <= 0:
            errors.append("CI polling interval must be positive")
        
        if self.retry.max_retries < 0:
            errors.append("Max retries must be non-negative")
        
        return errors

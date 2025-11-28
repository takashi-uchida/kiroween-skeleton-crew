"""
Review & PR Service - Automated Pull Request creation and management.

This service handles:
- Automatic PR creation from Agent Runner artifacts
- PR template generation
- CI status monitoring and integration
- PR event handling (merge, close, etc.)
- Review comment automation
- Label and reviewer management
"""

from necrocode.review_pr_service.models import (
    PullRequest,
    PRState,
    CIStatus,
)
from necrocode.review_pr_service.exceptions import (
    PRServiceError,
    AuthenticationError,
    RateLimitError,
    PRCreationError,
    PRUpdateError,
    CIStatusError,
    NetworkError,
)
from necrocode.review_pr_service.config import PRServiceConfig
from necrocode.review_pr_service.git_host_client import (
    GitHostClient,
    GitHubClient,
    GitLabClient,
    BitbucketClient,
)
from necrocode.review_pr_service.pr_template_engine import PRTemplateEngine
from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.ci_status_monitor import CIStatusMonitor
from necrocode.review_pr_service.metrics_collector import MetricsCollector, PrometheusExporter
from necrocode.review_pr_service.retry_handler import (
    RetryHandler,
    with_retry,
    retry_operation,
    RateLimitWaiter,
)

__all__ = [
    "PullRequest",
    "PRState",
    "CIStatus",
    "PRServiceError",
    "AuthenticationError",
    "RateLimitError",
    "PRCreationError",
    "PRUpdateError",
    "CIStatusError",
    "NetworkError",
    "PRServiceConfig",
    "GitHostClient",
    "GitHubClient",
    "GitLabClient",
    "BitbucketClient",
    "PRTemplateEngine",
    "PRService",
    "CIStatusMonitor",
    "MetricsCollector",
    "PrometheusExporter",
    "RetryHandler",
    "with_retry",
    "retry_operation",
    "RateLimitWaiter",
]

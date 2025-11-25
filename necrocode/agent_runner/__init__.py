"""
Agent Runner - Task execution worker component for NecroCode.

This module provides the core functionality for executing tasks in isolated
workspaces, including Git operations, task implementation, testing, and
artifact management.
"""

from necrocode.agent_runner.models import (
    TaskContext,
    Workspace,
    RunnerState,
    RunnerResult,
    ImplementationResult,
    TestResult,
    SingleTestResult,
    PushResult,
    Artifact,
    ArtifactType,
    Playbook,
    PlaybookStep,
    SlotAllocation,
    CodeChange,
    LLMResponse,
    LLMConfig,
)
from necrocode.agent_runner.exceptions import (
    RunnerError,
    TaskContextValidationError,
    WorkspacePreparationError,
    ImplementationError,
    TestExecutionError,
    PushError,
    ArtifactUploadError,
    TimeoutError,
    SecurityError,
    ResourceConflictError,
    ResourceLimitError,
    PlaybookExecutionError,
)
from necrocode.agent_runner.config import (
    RunnerConfig,
    RetryConfig,
    ExecutionMode,
)
from necrocode.agent_runner.workspace_manager import WorkspaceManager
from necrocode.agent_runner.task_executor import TaskExecutor
from necrocode.agent_runner.test_runner import AgentTestRunner, CommandExecutor
from necrocode.agent_runner.artifact_uploader import ArtifactUploader
from necrocode.agent_runner.llm_client import LLMClient
from necrocode.agent_runner.task_registry_client import TaskRegistryClient
from necrocode.agent_runner.repo_pool_client import RepoPoolClient
from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.playbook_engine import (
    PlaybookEngine,
    PlaybookResult,
    StepResult,
)
from necrocode.agent_runner.runner_orchestrator import RunnerOrchestrator
from necrocode.agent_runner.security import (
    CredentialManager,
    SecretMasker,
    PermissionValidator,
)
from necrocode.agent_runner.resource_monitor import (
    TimeoutManager,
    ResourceMonitor,
    ResourceUsage,
    ServiceCallMetrics,
    ServiceCallTracker,
    ExecutionMonitor,
)
from necrocode.agent_runner.logging_config import (
    setup_logging,
    get_runner_logger,
    StructuredFormatter,
    RunnerLoggerAdapter,
)
from necrocode.agent_runner.metrics import (
    ExecutionMetrics,
    MetricsCollector,
    MetricsReporter,
)
from necrocode.agent_runner.health_check import (
    HealthCheckServer,
    HealthStatus,
    create_health_check_server,
)
from necrocode.agent_runner.execution_env import (
    ExecutionEnvironment,
    LocalProcessRunner,
    DockerRunner,
    KubernetesRunner,
    create_runner,
)
from necrocode.agent_runner.parallel_coordinator import (
    ParallelCoordinator,
    ParallelExecutionContext,
    RunnerInstance,
)

# Alias for convenience
TestRunner = AgentTestRunner

__all__ = [
    # Models
    "TaskContext",
    "Workspace",
    "RunnerState",
    "RunnerResult",
    "ImplementationResult",
    "TestResult",
    "SingleTestResult",
    "PushResult",
    "Artifact",
    "ArtifactType",
    "Playbook",
    "PlaybookStep",
    "SlotAllocation",
    "CodeChange",
    "LLMResponse",
    "LLMConfig",
    # Exceptions
    "RunnerError",
    "TaskContextValidationError",
    "WorkspacePreparationError",
    "ImplementationError",
    "TestExecutionError",
    "PushError",
    "ArtifactUploadError",
    "TimeoutError",
    "SecurityError",
    "ResourceConflictError",
    "ResourceLimitError",
    "PlaybookExecutionError",
    # Config
    "RunnerConfig",
    "RetryConfig",
    "ExecutionMode",
    # Workspace Manager
    "WorkspaceManager",
    # Task Executor
    "TaskExecutor",
    # Test Runner
    "TestRunner",
    "CommandExecutor",
    # Artifact Uploader
    "ArtifactUploader",
    # External Service Clients
    "LLMClient",
    "TaskRegistryClient",
    "RepoPoolClient",
    "ArtifactStoreClient",
    # Playbook Engine
    "PlaybookEngine",
    "PlaybookResult",
    "StepResult",
    # Runner Orchestrator
    "RunnerOrchestrator",
    # Security
    "CredentialManager",
    "SecretMasker",
    "PermissionValidator",
    # Resource Monitoring
    "TimeoutManager",
    "ResourceMonitor",
    "ResourceUsage",
    "ServiceCallMetrics",
    "ServiceCallTracker",
    "ExecutionMonitor",
    # Logging and Metrics
    "setup_logging",
    "get_runner_logger",
    "StructuredFormatter",
    "RunnerLoggerAdapter",
    "ExecutionMetrics",
    "MetricsCollector",
    "MetricsReporter",
    # Health Check
    "HealthCheckServer",
    "HealthStatus",
    "create_health_check_server",
    # Execution Environments
    "ExecutionEnvironment",
    "LocalProcessRunner",
    "DockerRunner",
    "KubernetesRunner",
    "create_runner",
    # Parallel Execution
    "ParallelCoordinator",
    "ParallelExecutionContext",
    "RunnerInstance",
]

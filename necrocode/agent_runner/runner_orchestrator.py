"""
Runner Orchestrator for Agent Runner.

This module provides the main orchestration logic for Agent Runner,
coordinating all components to execute tasks from start to finish.
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from necrocode.agent_runner.artifact_uploader import ArtifactUploader
from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.health_check import HealthCheckServer, create_health_check_server
from necrocode.agent_runner.metrics import MetricsCollector
from necrocode.agent_runner.exceptions import (
    ResourceConflictError,
    ResourceLimitError,
    RunnerError,
    SecurityError,
    TaskContextValidationError,
    TimeoutError,
)
from necrocode.agent_runner.models import (
    Artifact,
    ImplementationResult,
    PushResult,
    RunnerResult,
    RunnerState,
    RunnerStateSnapshot,
    TaskContext,
    TestResult,
    Workspace,
)
from necrocode.agent_runner.parallel_coordinator import (
    ParallelCoordinator,
    ParallelExecutionContext,
)
from necrocode.agent_runner.playbook_engine import PlaybookEngine
from necrocode.agent_runner.resource_monitor import ExecutionMonitor
from necrocode.agent_runner.security import (
    CredentialManager,
    PermissionValidator,
    SecretMasker,
)
from necrocode.agent_runner.task_executor import TaskExecutor
from necrocode.agent_runner.test_runner import TestRunner
from necrocode.agent_runner.workspace_manager import WorkspaceManager

# Import Task Registry if available
try:
    from necrocode.task_registry import TaskRegistry
    from necrocode.task_registry.models import TaskState, TaskEvent
    TASK_REGISTRY_AVAILABLE = True
except ImportError:
    TASK_REGISTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


class RunnerOrchestrator:
    """
    Main orchestrator for Agent Runner.
    
    Coordinates all components to execute tasks, including:
    - Workspace preparation
    - Task implementation
    - Test execution
    - Commit and push
    - Artifact upload
    - Completion reporting
    
    Requirements: 1.1, 1.3
    """
    
    def __init__(self, config: Optional[RunnerConfig] = None):
        """
        Initialize RunnerOrchestrator.
        
        Args:
            config: Runner configuration. If None, uses default config.
            
        Requirements: 1.1, 1.3
        """
        self.config = config or RunnerConfig()
        self.runner_id = self._generate_runner_id()
        self.state = RunnerState.IDLE
        
        # Initialize security components
        self.credential_manager = CredentialManager()
        self.secret_masker = SecretMasker()
        self.permission_validator: Optional[PermissionValidator] = None
        
        # Load credentials
        self._load_credentials()
        
        # Initialize components
        self.workspace_manager = WorkspaceManager(
            retry_config=self.config.git_retry_config
        )
        self.task_executor = TaskExecutor()
        self.test_runner = TestRunner()
        self.artifact_uploader = ArtifactUploader(config=self.config)
        self.playbook_engine = PlaybookEngine()
        
        # Initialize Task Registry if available
        self.task_registry: Optional[TaskRegistry] = None
        if TASK_REGISTRY_AVAILABLE and self.config.task_registry_path:
            try:
                self.task_registry = TaskRegistry(
                    registry_dir=self.config.task_registry_path
                )
                logger.info("Initialized Task Registry")
            except Exception as e:
                logger.warning(f"Failed to initialize Task Registry: {e}")
        
        # Execution logs
        self.execution_logs: list[str] = []
        
        # State tracking
        self.current_task_id: Optional[str] = None
        self.current_spec_name: Optional[str] = None
        self.execution_start_time: Optional[float] = None
        
        # Execution monitoring
        self.execution_monitor: Optional[ExecutionMonitor] = None
        
        # Parallel execution coordination
        self.parallel_coordinator: Optional[ParallelCoordinator] = None
        if self.config.max_parallel_runners is not None:
            self.parallel_coordinator = ParallelCoordinator(
                max_parallel_runners=self.config.max_parallel_runners
            )
            logger.info(
                f"Parallel coordination enabled: "
                f"max_parallel={self.config.max_parallel_runners}"
            )
        
        # Health check server
        self.health_check_server: Optional[HealthCheckServer] = None
        if self.config.enable_health_check:
            self.health_check_server = create_health_check_server(
                port=self.config.health_check_port,
                host="0.0.0.0",
                runner_id=self.runner_id
            )
            logger.info(
                f"Health check server configured on port {self.config.health_check_port}"
            )
        
        logger.info(f"RunnerOrchestrator initialized with ID: {self.runner_id}")
        logger.info(f"Execution mode: {self.config.execution_mode.value}")
    
    def _generate_runner_id(self) -> str:
        """
        Generate a unique runner ID.
        
        Returns:
            Unique runner identifier
            
        Requirements: 1.1, 1.3
        """
        # Generate UUID-based runner ID
        runner_id = f"runner-{uuid.uuid4().hex[:12]}"
        return runner_id
    
    def _load_credentials(self) -> None:
        """
        Load authentication credentials from environment or secret mounts.
        
        Loads credentials for:
        - Git operations
        - Artifact Store API
        - Kiro API
        
        Requirements: 1.4, 10.1
        """
        logger.info("Loading credentials")
        
        try:
            # Load Git token
            git_token = self.credential_manager.get_git_token(
                env_var=self.config.git_token_env_var
            )
            if git_token:
                # Add to secret masker
                if self.config.mask_secrets:
                    self.secret_masker.add_secret(git_token)
                logger.info("Git token loaded successfully")
            else:
                logger.warning("Git token not found - Git operations may fail")
            
            # Load Artifact Store API key
            artifact_api_key = self.credential_manager.get_api_key(
                service="artifact_store",
                env_var=self.config.artifact_store_api_key_env_var
            )
            if artifact_api_key:
                if self.config.mask_secrets:
                    self.secret_masker.add_secret(artifact_api_key)
                logger.info("Artifact Store API key loaded successfully")
            
            # Load Kiro API key if configured
            if self.config.kiro_api_url:
                kiro_api_key = self.credential_manager.get_api_key(
                    service="kiro",
                    env_var=self.config.kiro_api_key_env_var
                )
                if kiro_api_key:
                    if self.config.mask_secrets:
                        self.secret_masker.add_secret(kiro_api_key)
                    logger.info("Kiro API key loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise SecurityError(f"Credential loading failed: {e}")

    def _validate_task_context(self, task_context: TaskContext) -> None:
        """
        Validate task context before execution.
        
        Ensures that all required information is present and valid
        in the task context.
        
        Args:
            task_context: Task context to validate
            
        Raises:
            TaskContextValidationError: If validation fails
            
        Requirements: 1.2
        """
        logger.info(f"Validating task context for task {task_context.task_id}")
        
        errors = []
        
        # Check required fields
        if not task_context.task_id:
            errors.append("task_id is required")
        
        if not task_context.spec_name:
            errors.append("spec_name is required")
        
        if not task_context.title:
            errors.append("title is required")
        
        if not task_context.description:
            errors.append("description is required")
        
        if not task_context.required_skill:
            errors.append("required_skill is required")
        
        # Check workspace information
        if not task_context.slot_path:
            errors.append("slot_path is required")
        elif not task_context.slot_path.exists():
            errors.append(f"slot_path does not exist: {task_context.slot_path}")
        
        if not task_context.slot_id:
            errors.append("slot_id is required")
        
        if not task_context.branch_name:
            errors.append("branch_name is required")
        
        # Check acceptance criteria
        if not task_context.acceptance_criteria:
            logger.warning("No acceptance criteria specified for task")
        
        # Check timeout
        if task_context.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")
        
        # Check playbook path if specified
        if task_context.playbook_path and not task_context.playbook_path.exists():
            logger.warning(
                f"Playbook path does not exist: {task_context.playbook_path}, "
                "will use default playbook"
            )
        
        # Raise error if validation failed
        if errors:
            error_msg = "Task context validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error(error_msg)
            raise TaskContextValidationError(error_msg)
        
        logger.info("Task context validation passed")

    def run(self, task_context: TaskContext) -> RunnerResult:
        """
        Execute a task from start to finish.
        
        This is the main entry point for task execution. It orchestrates
        all phases of task execution:
        1. Validate task context
        2. Prepare workspace
        3. Execute task implementation
        4. Run tests
        5. Commit and push changes
        6. Upload artifacts
        7. Report completion
        
        Args:
            task_context: Task context containing all execution information
            
        Returns:
            RunnerResult containing execution results and artifacts
            
        Requirements: 2.1, 3.1, 4.1, 5.1, 6.1, 11.1, 11.2, 11.3, 11.4, 11.5, 14.1, 14.2, 14.3, 14.4
        """
        start_time = time.time()
        wait_start_time = start_time
        
        self._log(f"Starting task execution: {task_context.task_id}")
        self._log(f"Task: {task_context.title}")
        self._log(f"Spec: {task_context.spec_name}")
        
        # Initialize execution monitor
        self._init_execution_monitor(task_context)
        
        # Initialize metrics collector
        metrics_collector = MetricsCollector(
            runner_id=self.runner_id,
            task_id=task_context.task_id,
            spec_name=task_context.spec_name,
        )
        
        # Parallel execution context (if enabled)
        parallel_context = None
        concurrent_runners = 1
        wait_time = 0.0
        resource_conflicts = 0
        
        try:
            # Register with parallel coordinator if enabled
            if self.parallel_coordinator:
                # Check wait time before registering
                wait_time = self.parallel_coordinator.get_wait_time()
                if wait_time > 0:
                    self._log(
                        f"Waiting for available slot: estimated wait {wait_time:.0f}s"
                    )
                    time.sleep(min(wait_time, 60))  # Wait up to 1 minute
                
                # Create parallel execution context
                parallel_context = ParallelExecutionContext(
                    coordinator=self.parallel_coordinator,
                    runner_id=self.runner_id,
                    task_id=task_context.task_id,
                    spec_name=task_context.spec_name,
                    workspace_path=task_context.slot_path,
                )
                
                # Enter context (registers runner)
                parallel_context.__enter__()
                
                # Get concurrent runner count
                concurrent_runners = self.parallel_coordinator.get_concurrent_count()
                
                # Calculate actual wait time
                wait_time = time.time() - wait_start_time
                
                # Record parallel execution metrics
                metrics_collector.record_concurrent_runners(concurrent_runners)
                metrics_collector.record_wait_time(wait_time)
                
                self._log(
                    f"Registered with parallel coordinator: "
                    f"concurrent_runners={concurrent_runners}, wait_time={wait_time:.2f}s"
                )
        
        except Exception as e:
            self._log(f"Failed to register with parallel coordinator: {e}")
            # Continue without parallel coordination
            parallel_context = None
        
        try:
            # Start health check server if enabled
            if self.health_check_server:
                try:
                    self.health_check_server.start()
                    self._log(
                        f"Health check server started on port {self.config.health_check_port}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to start health check server: {e}")
            
            # Validate task context
            self._validate_task_context(task_context)
            
            # Track current task
            self.current_task_id = task_context.task_id
            self.current_spec_name = task_context.spec_name
            self.execution_start_time = start_time
            
            # Transition to running state
            self._transition_state(RunnerState.RUNNING)
            
            # Update health check status
            if self.health_check_server:
                self.health_check_server.update_status(
                    healthy=True,
                    runner_state="running",
                    current_task_id=task_context.task_id,
                    current_spec_name=task_context.spec_name,
                )
            
            # Start monitoring
            if self.execution_monitor:
                self.execution_monitor.start()
                self._log(
                    f"Execution monitoring started: timeout={task_context.timeout_seconds}s"
                )
            
            # 1. Prepare workspace
            self._log("Phase 1: Preparing workspace")
            metrics_collector.start_phase("workspace_preparation")
            self._check_execution_limits()
            workspace = self._prepare_workspace(task_context, metrics_collector)
            metrics_collector.end_phase("workspace_preparation")
            
            # 2. Execute task implementation
            self._log("Phase 2: Executing task implementation")
            metrics_collector.start_phase("task_implementation")
            self._check_execution_limits()
            impl_result = self._execute_task(task_context, workspace)
            metrics_collector.end_phase("task_implementation")
            
            if not impl_result.success:
                raise RunnerError(f"Task implementation failed: {impl_result.error}")
            
            # Record implementation metrics
            metrics_collector.record_implementation(
                files_changed=len(impl_result.files_changed),
                lines_added=0,  # TODO: Parse diff for line counts
                lines_removed=0,
            )
            
            # 3. Run tests
            self._log("Phase 3: Running tests")
            metrics_collector.start_phase("test_execution")
            self._check_execution_limits()
            test_result = self._run_tests(task_context, workspace)
            metrics_collector.end_phase("test_execution")
            
            if not test_result.success:
                raise RunnerError("Tests failed")
            
            # Record test metrics
            passed = sum(1 for r in test_result.test_results if r.success)
            failed = sum(1 for r in test_result.test_results if not r.success)
            metrics_collector.record_tests(
                tests_run=len(test_result.test_results),
                tests_passed=passed,
                tests_failed=failed,
            )
            
            # 4. Commit and push changes
            self._log("Phase 4: Committing and pushing changes")
            metrics_collector.start_phase("commit_and_push")
            self._check_execution_limits()
            push_result = self._commit_and_push(task_context, workspace)
            metrics_collector.end_phase("commit_and_push")
            
            if not push_result.success:
                raise RunnerError(f"Push failed: {push_result.error}")
            
            # Record retries
            for _ in range(push_result.retry_count):
                metrics_collector.record_retry()
            
            # 5. Upload artifacts
            self._log("Phase 5: Uploading artifacts")
            metrics_collector.start_phase("artifact_upload")
            self._check_execution_limits()
            artifacts = self._upload_artifacts(
                task_context,
                impl_result,
                test_result
            )
            metrics_collector.end_phase("artifact_upload")
            
            # Record artifact metrics
            total_size = sum(a.size_bytes for a in artifacts)
            metrics_collector.record_artifacts(
                artifacts_uploaded=len(artifacts),
                total_size_bytes=total_size,
            )
            
            # 6. Report completion
            self._log("Phase 6: Reporting completion")
            self._report_completion(task_context, artifacts)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Finalize metrics
            final_metrics = metrics_collector.finalize()
            
            # Log resource usage summary
            self._log_resource_summary()
            
            # Report metrics
            from necrocode.agent_runner.metrics import MetricsReporter
            metrics_reporter = MetricsReporter()
            metrics_reporter.report(final_metrics)
            
            # Transition to completed state
            self._transition_state(RunnerState.COMPLETED)
            
            # Update health check status
            if self.health_check_server:
                self.health_check_server.update_status(
                    healthy=True,
                    runner_state="completed",
                    current_task_id=None,
                    current_spec_name=None,
                )
            
            self._log(f"Task execution completed successfully in {duration:.2f}s")
            
            return RunnerResult(
                success=True,
                runner_id=self.runner_id,
                task_id=task_context.task_id,
                duration_seconds=duration,
                artifacts=artifacts,
                error=None,
                impl_result=impl_result,
                test_result=test_result,
                push_result=push_result,
                workspace_path=str(task_context.slot_path),
                concurrent_runners=concurrent_runners,
            )
            
        except (TimeoutError, ResourceLimitError) as e:
            # Handle timeout and resource limit errors specially
            duration = time.time() - start_time
            self._log(f"Task execution aborted after {duration:.2f}s: {e}")
            
            # Record error in metrics
            metrics_collector.record_error()
            
            # Log resource usage at time of failure
            self._log_resource_summary()
            
            # Handle error
            self._handle_error(task_context, e)
            
            # Transition to failed state
            self._transition_state(RunnerState.FAILED)
            
            # Update health check status
            if self.health_check_server:
                self.health_check_server.update_status(
                    healthy=False,
                    runner_state="failed",
                    current_task_id=None,
                    current_spec_name=None,
                    error=str(e),
                )
            
            return RunnerResult(
                success=False,
                runner_id=self.runner_id,
                task_id=task_context.task_id,
                duration_seconds=duration,
                artifacts=[],
                error=str(e),
                workspace_path=str(task_context.slot_path),
                concurrent_runners=concurrent_runners,
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self._log(f"Task execution failed after {duration:.2f}s: {e}")
            
            # Record error in metrics
            metrics_collector.record_error()
            
            # Handle error
            self._handle_error(task_context, e)
            
            # Transition to failed state
            self._transition_state(RunnerState.FAILED)
            
            # Update health check status
            if self.health_check_server:
                self.health_check_server.update_status(
                    healthy=False,
                    runner_state="failed",
                    current_task_id=None,
                    current_spec_name=None,
                    error=str(e),
                )
            
            return RunnerResult(
                success=False,
                runner_id=self.runner_id,
                task_id=task_context.task_id,
                duration_seconds=duration,
                artifacts=[],
                error=str(e),
                workspace_path=str(task_context.slot_path),
                concurrent_runners=concurrent_runners,
            )
            
        finally:
            # Unregister from parallel coordinator
            if parallel_context:
                try:
                    parallel_context.__exit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Failed to unregister from parallel coordinator: {e}")
            
            # Stop monitoring
            if self.execution_monitor:
                self.execution_monitor.stop()
            
            # Stop health check server
            if self.health_check_server:
                try:
                    self.health_check_server.stop()
                    self._log("Health check server stopped")
                except Exception as e:
                    logger.warning(f"Failed to stop health check server: {e}")
            
            # Always cleanup
            self._cleanup(task_context)
    
    def _prepare_workspace(
        self,
        task_context: TaskContext,
        metrics_collector: Optional[MetricsCollector] = None,
    ) -> Workspace:
        """
        Prepare workspace for task execution.
        
        Performs Git operations to set up a clean workspace:
        - Checkout base branch
        - Fetch latest changes
        - Rebase on base branch
        - Create task branch
        
        Args:
            task_context: Task context
            
        Returns:
            Workspace object
            
        Raises:
            WorkspacePreparationError: If workspace preparation fails
            
        Requirements: 2.1
        """
        self._log(f"Preparing workspace at {task_context.slot_path}")
        self._log(f"Creating branch: {task_context.branch_name}")
        
        try:
            # Initialize permission validator for this workspace
            self.permission_validator = PermissionValidator(
                workspace_root=task_context.slot_path
            )
            self._log("Permission validator initialized")
            
            # Validate Git operations
            self.permission_validator.validate_git_operation(
                "branch",
                branch_name=task_context.branch_name
            )
            
            workspace = self.workspace_manager.prepare_workspace(
                slot_path=task_context.slot_path,
                branch_name=task_context.branch_name,
                base_branch="main"
            )
            
            # Check for branch conflicts
            conflicts = self._check_resource_conflicts(
                task_context,
                branches=[task_context.branch_name],
                metrics_collector=metrics_collector,
            )
            
            if conflicts:
                self._log(f"WARNING: Branch conflicts detected but continuing")
            
            # Update parallel coordinator with branch being used
            self._update_parallel_resources(
                task_context,
                branches=[task_context.branch_name]
            )
            
            self._log("Workspace prepared successfully")
            return workspace
            
        except Exception as e:
            self._log(f"Workspace preparation failed: {e}")
            raise
    
    def _execute_task(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> ImplementationResult:
        """
        Execute task implementation using TaskExecutor.
        
        Args:
            task_context: Task context
            workspace: Prepared workspace
            
        Returns:
            ImplementationResult
            
        Raises:
            ImplementationError: If implementation fails
            
        Requirements: 3.1
        """
        self._log(f"Executing task implementation: {task_context.task_id}")
        
        try:
            impl_result = self.task_executor.execute(task_context, workspace)
            
            if impl_result.success:
                self._log(
                    f"Implementation completed in {impl_result.duration_seconds:.2f}s"
                )
                self._log(f"Files changed: {len(impl_result.files_changed)}")
            else:
                self._log(f"Implementation failed: {impl_result.error}")
            
            return impl_result
            
        except Exception as e:
            self._log(f"Task execution failed: {e}")
            raise
    
    def _run_tests(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> TestResult:
        """
        Run tests for the task.
        
        Args:
            task_context: Task context
            workspace: Workspace with implementation
            
        Returns:
            TestResult
            
        Raises:
            TestExecutionError: If test execution fails critically
            
        Requirements: 4.1
        """
        self._log("Running tests")
        
        try:
            test_result = self.test_runner.run_tests(task_context, workspace)
            
            if test_result.success:
                self._log(
                    f"All tests passed ({len(test_result.test_results)} tests, "
                    f"{test_result.total_duration_seconds:.2f}s)"
                )
            else:
                failed_count = sum(
                    1 for r in test_result.test_results if not r.success
                )
                self._log(
                    f"Tests failed: {failed_count}/{len(test_result.test_results)} "
                    "tests failed"
                )
            
            return test_result
            
        except Exception as e:
            self._log(f"Test execution failed: {e}")
            raise
    
    def _commit_and_push(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> PushResult:
        """
        Commit changes and push to remote.
        
        Args:
            task_context: Task context
            workspace: Workspace with changes
            
        Returns:
            PushResult
            
        Raises:
            PushError: If push fails after retries
            
        Requirements: 5.1
        """
        self._log("Committing and pushing changes")
        
        try:
            # Validate push operation
            if self.permission_validator:
                self.permission_validator.validate_git_operation(
                    "push",
                    branch=task_context.branch_name,
                    force=False
                )
            
            # Generate commit message
            commit_message = self._generate_commit_message(task_context)
            self._log(f"Commit message: {commit_message}")
            
            # Commit changes
            commit_hash = self.workspace_manager.commit_changes(
                workspace=workspace,
                commit_message=commit_message
            )
            self._log(f"Changes committed: {commit_hash[:8]}")
            
            # Push branch
            push_result = self.workspace_manager.push_branch(
                workspace=workspace,
                branch_name=task_context.branch_name
            )
            
            if push_result.success:
                self._log(
                    f"Branch pushed successfully (retry count: {push_result.retry_count})"
                )
            else:
                self._log(f"Push failed: {push_result.error}")
            
            return push_result
            
        except Exception as e:
            self._log(f"Commit and push failed: {e}")
            raise
    
    def _upload_artifacts(
        self,
        task_context: TaskContext,
        impl_result: Optional[ImplementationResult],
        test_result: Optional[TestResult]
    ) -> list[Artifact]:
        """
        Upload execution artifacts to Artifact Store.
        
        Args:
            task_context: Task context
            impl_result: Implementation result (may be None)
            test_result: Test result (may be None)
            
        Returns:
            List of uploaded artifacts
            
        Requirements: 6.1
        """
        self._log("Uploading artifacts")
        
        try:
            # Collect execution logs
            logs = "\n".join(self.execution_logs)
            
            # Upload artifacts
            artifacts = self.artifact_uploader.upload_artifacts(
                task_context=task_context,
                impl_result=impl_result,
                test_result=test_result,
                logs=logs
            )
            
            self._log(f"Uploaded {len(artifacts)} artifacts")
            for artifact in artifacts:
                self._log(f"  - {artifact.type.value}: {artifact.uri}")
            
            return artifacts
            
        except Exception as e:
            self._log(f"Artifact upload failed: {e}")
            # Don't fail the task if artifact upload fails
            logger.warning(f"Artifact upload failed, continuing: {e}")
            return []
    
    def _generate_commit_message(self, task_context: TaskContext) -> str:
        """
        Generate commit message for task.
        
        Args:
            task_context: Task context
            
        Returns:
            Formatted commit message
        """
        # Format: feat(spec-name): task title [Task task-id]
        return (
            f"feat({task_context.spec_name}): {task_context.title} "
            f"[Task {task_context.task_id}]"
        )

    def _report_completion(
        self,
        task_context: TaskContext,
        artifacts: list[Artifact]
    ) -> None:
        """
        Report task completion to Task Registry.
        
        Records a TaskCompleted event in the Task Registry with
        execution details and artifact URIs.
        
        Args:
            task_context: Task context
            artifacts: List of uploaded artifacts
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        self._log("Reporting task completion")
        
        if not self.task_registry:
            self._log("Task Registry not available, skipping completion report")
            return
        
        try:
            # Update task state to Done
            self.task_registry.update_task_state(
                spec_name=task_context.spec_name,
                task_id=task_context.task_id,
                new_state=TaskState.DONE
            )
            
            # Record TaskCompleted event
            event_data = {
                "runner_id": self.runner_id,
                "branch_name": task_context.branch_name,
                "artifacts": [
                    {
                        "type": artifact.type.value,
                        "uri": artifact.uri,
                        "size_bytes": artifact.size_bytes,
                    }
                    for artifact in artifacts
                ],
            }
            
            self.task_registry.add_event(
                spec_name=task_context.spec_name,
                task_id=task_context.task_id,
                event_type=TaskEvent.TASK_COMPLETED,
                data=event_data
            )
            
            self._log("Task completion reported to Task Registry")
            
        except Exception as e:
            self._log(f"Failed to report completion to Task Registry: {e}")
            logger.warning(f"Failed to report completion: {e}")

    def _handle_error(self, task_context: TaskContext, error: Exception) -> None:
        """
        Handle task execution error.
        
        Records error information in logs and Task Registry,
        and performs any necessary error recovery actions.
        
        Args:
            task_context: Task context
            error: Exception that occurred
            
        Requirements: 8.1, 8.3, 8.4, 8.5
        """
        self._log(f"Handling error: {type(error).__name__}: {error}")
        
        # Log error details
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "runner_id": self.runner_id,
        }
        
        # Save error log to file if configured
        if self.config.log_file:
            try:
                self._save_error_log(task_context, error_details)
            except Exception as e:
                logger.error(f"Failed to save error log: {e}")
        
        # Report to Task Registry if available
        if self.task_registry:
            try:
                # Update task state to Failed
                self.task_registry.update_task_state(
                    spec_name=task_context.spec_name,
                    task_id=task_context.task_id,
                    new_state=TaskState.FAILED
                )
                
                # Record TaskFailed event
                self.task_registry.add_event(
                    spec_name=task_context.spec_name,
                    task_id=task_context.task_id,
                    event_type=TaskEvent.TASK_FAILED,
                    data=error_details
                )
                
                self._log("Error reported to Task Registry")
                
            except Exception as e:
                self._log(f"Failed to report error to Task Registry: {e}")
                logger.error(f"Failed to report error to Task Registry: {e}")
        
        # Attempt to upload error logs as artifacts
        try:
            logs = "\n".join(self.execution_logs)
            self.artifact_uploader.upload_artifacts(
                task_context=task_context,
                impl_result=None,
                test_result=None,
                logs=logs
            )
        except Exception as e:
            logger.warning(f"Failed to upload error artifacts: {e}")
    
    def _save_error_log(
        self,
        task_context: TaskContext,
        error_details: dict
    ) -> None:
        """
        Save error log to file.
        
        Args:
            task_context: Task context
            error_details: Error details dictionary
        """
        if not self.config.log_file:
            return
        
        log_file = self.config.log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "runner_id": self.runner_id,
            "task_id": task_context.task_id,
            "spec_name": task_context.spec_name,
            "error": error_details,
            "logs": self.execution_logs,
        }
        
        # Append to log file
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _cleanup(self, task_context: TaskContext) -> None:
        """
        Cleanup resources after task execution.
        
        Performs cleanup actions including:
        - Clearing sensitive data from memory
        - Clearing persisted state (if task completed successfully)
        - Releasing resources
        - Logging cleanup completion
        
        Args:
            task_context: Task context
            
        Requirements: 10.3
        """
        self._log("Performing cleanup")
        
        try:
            # Clear credentials from memory
            self.credential_manager.clear_credentials()
            self._log("Credentials cleared from memory")
            
            # Clear persisted state if task completed successfully
            if self.state == RunnerState.COMPLETED and self.config.persist_state:
                self.clear_state()
            
            # Reset task tracking
            self.current_task_id = None
            self.current_spec_name = None
            self.execution_start_time = None
            
            # Log cleanup completion
            self._log("Cleanup completed")
            
        except Exception as e:
            self._log(f"Cleanup failed: {e}")
            logger.warning(f"Cleanup failed: {e}")
    
    def _transition_state(self, new_state: RunnerState) -> None:
        """
        Transition runner to a new state with validation.
        
        Validates that the state transition is valid according to the
        state machine rules before performing the transition.
        
        Valid transitions:
        - IDLE -> RUNNING
        - RUNNING -> COMPLETED
        - RUNNING -> FAILED
        - Any state -> IDLE (for reset)
        
        Args:
            new_state: New state to transition to
            
        Raises:
            RunnerError: If state transition is invalid
            
        Requirements: 1.5
        """
        old_state = self.state
        
        # Validate state transition
        if not self._is_valid_transition(old_state, new_state):
            error_msg = (
                f"Invalid state transition: {old_state.value} -> {new_state.value}"
            )
            logger.error(error_msg)
            raise RunnerError(error_msg)
        
        # Perform transition
        self.state = new_state
        self._log(f"State transition: {old_state.value} -> {new_state.value}")
        
        # Persist state if configured
        if self.config.persist_state:
            try:
                self._persist_state()
            except Exception as e:
                logger.warning(f"Failed to persist state: {e}")
    
    def _is_valid_transition(
        self,
        from_state: RunnerState,
        to_state: RunnerState
    ) -> bool:
        """
        Check if a state transition is valid.
        
        Valid state transitions:
        - IDLE -> RUNNING: Start task execution
        - RUNNING -> COMPLETED: Task completed successfully
        - RUNNING -> FAILED: Task failed
        - Any state -> IDLE: Reset/cleanup (allows recovery)
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            True if transition is valid, False otherwise
            
        Requirements: 1.5
        """
        # Define valid transitions
        valid_transitions = {
            RunnerState.IDLE: {RunnerState.RUNNING},
            RunnerState.RUNNING: {RunnerState.COMPLETED, RunnerState.FAILED},
            RunnerState.COMPLETED: {RunnerState.IDLE},  # Allow reset
            RunnerState.FAILED: {RunnerState.IDLE},  # Allow reset
        }
        
        # Allow transition to same state (no-op)
        if from_state == to_state:
            return True
        
        # Check if transition is valid
        allowed_states = valid_transitions.get(from_state, set())
        return to_state in allowed_states
    
    def _persist_state(self) -> None:
        """
        Persist current runner state to file.
        
        Saves a snapshot of the current runner state including:
        - Runner ID
        - Current state
        - Current task information
        - Execution start time
        - Metadata
        
        The state file can be used for recovery or monitoring purposes.
        
        Requirements: 1.5
        """
        if not self.config.state_file_path:
            # Generate default state file path if not configured
            state_dir = Path.home() / ".necrocode" / "runner_states"
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / f"{self.runner_id}.json"
        else:
            state_file = self.config.state_file_path
            state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create state snapshot
        from datetime import datetime
        
        snapshot = RunnerStateSnapshot(
            runner_id=self.runner_id,
            state=self.state,
            task_id=self.current_task_id,
            spec_name=self.current_spec_name,
            start_time=datetime.fromtimestamp(self.execution_start_time) if self.execution_start_time else None,
            last_updated=datetime.now(),
            metadata={
                "execution_mode": self.config.execution_mode.value,
                "log_count": len(self.execution_logs),
            }
        )
        
        # Write to file
        import json
        
        with open(state_file, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        logger.debug(f"State persisted to {state_file}")
    
    def load_state(self, state_file: Optional[Path] = None) -> Optional[RunnerStateSnapshot]:
        """
        Load runner state from file.
        
        Loads a previously persisted state snapshot, which can be used
        for recovery or to resume execution after a restart.
        
        Args:
            state_file: Path to state file. If None, uses configured path
                       or default path based on runner_id.
        
        Returns:
            RunnerStateSnapshot if state file exists, None otherwise
            
        Requirements: 1.5
        """
        if state_file is None:
            if self.config.state_file_path:
                state_file = self.config.state_file_path
            else:
                state_dir = Path.home() / ".necrocode" / "runner_states"
                state_file = state_dir / f"{self.runner_id}.json"
        
        if not state_file.exists():
            logger.debug(f"State file not found: {state_file}")
            return None
        
        try:
            import json
            
            with open(state_file, "r") as f:
                data = json.load(f)
            
            snapshot = RunnerStateSnapshot.from_dict(data)
            logger.info(f"Loaded state from {state_file}: {snapshot.state.value}")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to load state from {state_file}: {e}")
            return None
    
    def clear_state(self, state_file: Optional[Path] = None) -> None:
        """
        Clear persisted state file.
        
        Removes the state file, typically called after successful
        task completion or when resetting the runner.
        
        Args:
            state_file: Path to state file. If None, uses configured path
                       or default path based on runner_id.
                       
        Requirements: 1.5
        """
        if state_file is None:
            if self.config.state_file_path:
                state_file = self.config.state_file_path
            else:
                state_dir = Path.home() / ".necrocode" / "runner_states"
                state_file = state_dir / f"{self.runner_id}.json"
        
        if state_file.exists():
            try:
                state_file.unlink()
                logger.debug(f"State file cleared: {state_file}")
            except Exception as e:
                logger.warning(f"Failed to clear state file {state_file}: {e}")
    
    def _init_execution_monitor(self, task_context: TaskContext) -> None:
        """
        Initialize execution monitor for timeout and resource limits.
        
        Args:
            task_context: Task context with timeout and resource settings
            
        Requirements: 11.1, 11.3, 11.4
        """
        try:
            self.execution_monitor = ExecutionMonitor(
                timeout_seconds=task_context.timeout_seconds,
                max_memory_mb=self.config.max_memory_mb,
                max_cpu_percent=self.config.max_cpu_percent,
                monitoring_interval=1.0,
            )
            logger.debug("Execution monitor initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize execution monitor: {e}")
            self.execution_monitor = None
    
    def _check_execution_limits(self) -> None:
        """
        Check timeout and resource limits.
        
        Raises:
            TimeoutError: If execution timeout exceeded
            ResourceLimitError: If resource limits exceeded
            
        Requirements: 11.2, 11.5
        """
        if self.execution_monitor:
            try:
                self.execution_monitor.check()
            except (TimeoutError, ResourceLimitError) as e:
                # Re-raise to be caught by run() method
                raise
    
    def _log_resource_summary(self) -> None:
        """
        Log resource usage summary.
        
        Requirements: 11.3, 11.4
        """
        if not self.execution_monitor:
            return
        
        try:
            status = self.execution_monitor.get_status()
            
            self._log(
                f"Execution time: {status['elapsed_seconds']:.2f}s / "
                f"{self.execution_monitor.timeout_manager.timeout_seconds}s"
            )
            
            if "resource_usage" in status:
                usage = status["resource_usage"]
                
                if usage.get("current"):
                    current = usage["current"]
                    self._log(
                        f"Current resource usage: "
                        f"Memory={current['memory_mb']:.1f}MB "
                        f"({current['memory_percent']:.1f}%), "
                        f"CPU={current['cpu_percent']:.1f}%"
                    )
                
                if usage.get("peak"):
                    peak = usage["peak"]
                    self._log(
                        f"Peak resource usage: "
                        f"Memory={peak['memory_mb']:.1f}MB "
                        f"({peak['memory_percent']:.1f}%), "
                        f"CPU={peak['cpu_percent']:.1f}%"
                    )
                
                if usage.get("average"):
                    avg = usage["average"]
                    self._log(
                        f"Average resource usage: "
                        f"Memory={avg['memory_mb']:.1f}MB, "
                        f"CPU={avg['cpu_percent']:.1f}%"
                    )
                
                if usage.get("limit_exceeded"):
                    self._log(f"WARNING: {usage['limit_exceeded_reason']}")
        
        except Exception as e:
            logger.warning(f"Failed to log resource summary: {e}")
    
    def _check_resource_conflicts(
        self,
        task_context: TaskContext,
        files: Optional[list[str]] = None,
        branches: Optional[list[str]] = None,
        metrics_collector: Optional[MetricsCollector] = None,
    ) -> list[str]:
        """
        Check for resource conflicts with other runners.
        
        Args:
            task_context: Task context
            files: List of files to check
            branches: List of branches to check
            metrics_collector: Optional metrics collector to record conflicts
            
        Returns:
            List of conflict descriptions
            
        Requirements: 14.3
        """
        if not self.parallel_coordinator:
            return []
        
        conflicts = self.parallel_coordinator.detect_conflicts(
            runner_id=self.runner_id,
            files=files,
            branches=branches,
        )
        
        if conflicts:
            self._log(f"Resource conflicts detected: {len(conflicts)}")
            for conflict in conflicts:
                self._log(f"  - {conflict}")
            
            # Record conflicts in metrics
            if metrics_collector:
                for _ in conflicts:
                    metrics_collector.record_resource_conflict()
        
        return conflicts
    
    def _update_parallel_resources(
        self,
        task_context: TaskContext,
        files: Optional[list[str]] = None,
        branches: Optional[list[str]] = None,
    ) -> None:
        """
        Update resources being used by this runner.
        
        Args:
            task_context: Task context
            files: List of files being used
            branches: List of branches being used
            
        Requirements: 14.3
        """
        if not self.parallel_coordinator:
            return
        
        self.parallel_coordinator.update_resources(
            runner_id=self.runner_id,
            files=files,
            branches=branches,
        )
    
    def _log(self, message: str) -> None:
        """
        Log a message to execution logs and logger.
        
        Automatically masks secrets if secret masking is enabled.
        
        Args:
            message: Message to log
        """
        from datetime import datetime
        
        # Mask secrets if enabled
        if self.config.mask_secrets:
            message = self.secret_masker.mask(message)
        
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        
        self.execution_logs.append(log_entry)
        logger.info(message)

"""
Dispatcher Core - Main orchestration component for task scheduling and assignment.

The DispatcherCore coordinates all dispatcher components to monitor tasks,
schedule them, allocate resources, and launch Agent Runners.
"""

import logging
import signal
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, TaskEvent, EventType
from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.models import Slot

from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.task_monitor import TaskMonitor
from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.dispatcher.scheduler import Scheduler
from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
from necrocode.dispatcher.runner_launcher import RunnerLauncher
from necrocode.dispatcher.runner_monitor import RunnerMonitor
from necrocode.dispatcher.metrics_collector import MetricsCollector
from necrocode.dispatcher.retry_manager import RetryManager
from necrocode.dispatcher.deadlock_detector import DeadlockDetector
from necrocode.dispatcher.event_recorder import EventRecorder
from necrocode.dispatcher.models import AgentPool, Runner, RunnerState, SchedulingPolicy
from necrocode.dispatcher.exceptions import (
    DispatcherError,
    TaskAssignmentError,
    SlotAllocationError,
    RunnerLaunchError,
    DeadlockDetectedError,
)


logger = logging.getLogger(__name__)


class DispatcherCore:
    """
    Main Dispatcher orchestration component.
    
    Coordinates task monitoring, scheduling, resource allocation, and runner launching.
    Implements the main dispatch loop and graceful shutdown.
    
    Requirements: 1.1
    """
    
    def __init__(self, config: Optional[DispatcherConfig] = None):
        """
        Initialize DispatcherCore with all components.
        
        Args:
            config: Dispatcher configuration (uses defaults if not provided)
            
        Requirements: 1.1
        """
        self.config = config or DispatcherConfig()
        self.running = False
        self._shutdown_event = threading.Event()
        self._main_thread: Optional[threading.Thread] = None
        
        # Global concurrency tracking
        self._global_running_count = 0
        self._global_running_lock = threading.Lock()
        
        # Initialize components
        logger.info("Initializing Dispatcher components...")
        
        self.task_monitor = TaskMonitor(self.config)
        self.task_queue = TaskQueue()
        self.scheduler = Scheduler(self.config.scheduling_policy)
        self.agent_pool_manager = AgentPoolManager(self.config)
        self.runner_launcher = RunnerLauncher(retry_attempts=self.config.retry_max_attempts)
        self.runner_monitor = RunnerMonitor(
            heartbeat_timeout=self.config.heartbeat_timeout,
            timeout_handler=self._handle_runner_timeout
        )
        self.metrics_collector = MetricsCollector()
        self.retry_manager = RetryManager(
            max_attempts=self.config.retry_max_attempts,
            backoff_base=self.config.retry_backoff_base,
            initial_delay=1.0,
            max_delay=300.0
        )
        self.deadlock_detector = DeadlockDetector()
        
        # Set component references for metrics collection
        self.metrics_collector.set_task_queue(self.task_queue)
        self.metrics_collector.set_agent_pool_manager(self.agent_pool_manager)
        self.metrics_collector.set_runner_monitor(self.runner_monitor)
        self.metrics_collector.set_dispatcher_core(self)
        
        # Initialize Task Registry client
        self.task_registry = TaskRegistry(registry_dir=self.config.task_registry_dir)
        
        # Initialize Event Recorder
        fallback_log_dir = Path(self.config.task_registry_dir).parent / "dispatcher_events"
        self.event_recorder = EventRecorder(
            task_registry=self.task_registry,
            fallback_log_dir=fallback_log_dir
        )
        
        # Initialize Repo Pool Manager
        # Use default config if not provided in dispatcher config
        repo_pool_config = getattr(self.config, 'repo_pool_config', None)
        self.repo_pool_manager = PoolManager(config=repo_pool_config)
        
        logger.info("DispatcherCore initialized successfully")
    
    def start(self) -> None:
        """
        Start the Dispatcher.
        
        Launches the main dispatch loop in a separate thread and sets up
        signal handlers for graceful shutdown.
        
        Requirements: 1.1, 1.2
        """
        if self.running:
            logger.warning("Dispatcher is already running")
            return
        
        logger.info("Starting Dispatcher...")
        
        self.running = True
        self._shutdown_event.clear()
        
        # Set up signal handlers for graceful shutdown (only in main thread)
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start main loop in a separate thread
        self._main_thread = threading.Thread(target=self._main_loop, daemon=False)
        self._main_thread.start()
        
        logger.info("Dispatcher started successfully")
    
    def stop(self, timeout: int = 300) -> None:
        """
        Stop the Dispatcher with graceful shutdown.
        
        Stops accepting new tasks, waits for running tasks to complete,
        and shuts down all components.
        
        Args:
            timeout: Maximum time to wait for runners to complete (seconds)
            
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
        """
        if not self.running:
            logger.warning("Dispatcher is not running")
            return
        
        logger.info(f"Stopping Dispatcher (timeout={timeout}s)...")
        
        # Signal shutdown
        self.running = False
        self._shutdown_event.set()
        
        # Wait for main loop to finish
        if self._main_thread and self._main_thread.is_alive():
            logger.info("Waiting for main loop to finish...")
            self._main_thread.join(timeout=10)
        
        # Wait for running tasks to complete
        self._wait_for_runners(timeout)
        
        logger.info("Dispatcher stopped successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop(timeout=self.config.graceful_shutdown_timeout)
    
    def _main_loop(self) -> None:
        """
        Main dispatch loop.
        
        Continuously:
        1. Polls for ready tasks
        2. Adds tasks to queue
        3. Schedules tasks
        4. Assigns tasks to runners
        5. Monitors runners
        6. Checks for deadlocks
        7. Collects metrics
        
        Requirements: 1.1, 1.2, 1.3, 1.5, 13.5
        """
        logger.info("Main dispatch loop started")
        
        deadlock_check_interval = 60  # Check for deadlocks every 60 seconds
        last_deadlock_check = time.time()
        
        while self.running:
            try:
                # 1. Poll for ready tasks
                ready_tasks = self.task_monitor.poll_ready_tasks()
                
                # 2. Add tasks to queue
                for task in ready_tasks:
                    if not self._is_task_in_queue(task):
                        self.task_queue.enqueue(task)
                        logger.info(f"Enqueued task {task.id} (priority={task.priority})")
                
                # 3. Schedule tasks (only if global limit not reached)
                if self.can_accept_task_globally():
                    scheduled_tasks = self.scheduler.schedule(
                        self.task_queue,
                        self.agent_pool_manager
                    )
                    
                    # 4. Assign tasks to runners
                    for task, pool in scheduled_tasks:
                        # Double-check global limit before each assignment
                        if not self.can_accept_task_globally():
                            # Global limit reached, re-queue remaining tasks
                            self.task_queue.enqueue(task)
                            logger.debug(
                                f"Global concurrency limit reached, re-queuing task {task.id}"
                            )
                            continue
                        
                        try:
                            self._assign_task(task, pool)
                        except Exception as e:
                            logger.error(f"Failed to assign task {task.id}: {e}")
                            # Re-enqueue task for retry
                            self.task_queue.enqueue(task)
                else:
                    logger.debug(
                        f"Global concurrency limit reached "
                        f"({self.get_global_running_count()}/{self.config.max_global_concurrency}), "
                        f"skipping scheduling"
                    )
                
                # 5. Monitor runners
                self.runner_monitor.check_heartbeats()
                
                # 6. Check for deadlocks periodically
                current_time = time.time()
                if current_time - last_deadlock_check >= deadlock_check_interval:
                    self._check_for_deadlocks()
                    last_deadlock_check = current_time
                
                # 7. Collect metrics
                self.metrics_collector.collect()
                
                # 8. Wait before next iteration
                time.sleep(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in main dispatch loop: {e}", exc_info=True)
                time.sleep(self.config.poll_interval)
        
        logger.info("Main dispatch loop stopped")
    
    def _is_task_in_queue(self, task: Task) -> bool:
        """
        Check if a task is already in the queue.
        
        Args:
            task: Task to check
            
        Returns:
            True if task is in queue, False otherwise
        """
        queued_tasks = self.task_queue.get_all_tasks()
        return any(t.id == task.id for t in queued_tasks)
    
    def _assign_task(self, task: Task, pool: AgentPool) -> None:
        """
        Assign a task to an Agent Runner.
        
        Steps:
        1. Allocate slot from Repo Pool Manager
        2. Launch Agent Runner
        3. Update Task Registry
        4. Add runner to monitoring
        5. Record metrics
        
        Args:
            task: Task to assign
            pool: Agent Pool to use
            
        Raises:
            TaskAssignmentError: If assignment fails
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4
        """
        logger.info(f"Assigning task {task.id} to pool {pool.name}")
        
        try:
            # 1. Allocate slot
            slot = self._allocate_slot(task)
            if not slot:
                logger.warning(f"No slot available for task {task.id}, re-queuing")
                self.task_queue.enqueue(task)
                return
            
            logger.info(f"Allocated slot {slot.slot_id} for task {task.id}")
            
            # 2. Launch Agent Runner
            try:
                runner = self.runner_launcher.launch(task, slot, pool)
                logger.info(
                    f"Launched runner {runner.runner_id} for task {task.id} "
                    f"(pool={pool.name}, slot={slot.slot_id})"
                )
            except RunnerLaunchError as e:
                logger.error(f"Failed to launch runner for task {task.id}: {e}")
                # Release slot and re-queue task
                self.repo_pool_manager.release_slot(slot.slot_id, cleanup=True)
                self.task_queue.enqueue(task)
                return
            
            # 3. Update Task Registry
            self._update_task_registry(task, runner, slot)
            
            # 4. Record TaskAssigned event
            spec_name = task.metadata.get("spec_name", "unknown")
            self.event_recorder.record_task_assigned(
                spec_name=spec_name,
                task_id=task.id,
                runner_id=runner.runner_id,
                slot_id=slot.slot_id,
                pool_name=pool.name,
                timestamp=runner.started_at
            )
            
            # 5. Record RunnerStarted event
            self.event_recorder.record_runner_started(
                spec_name=spec_name,
                task_id=task.id,
                runner_id=runner.runner_id,
                slot_id=slot.slot_id,
                pool_name=pool.name,
                pid=runner.pid,
                container_id=runner.container_id,
                job_name=runner.job_name,
                timestamp=runner.started_at
            )
            
            # 6. Add runner to monitoring
            self.runner_monitor.add_runner(runner)
            
            # 7. Update pool running count
            self.agent_pool_manager.increment_running_count(pool)
            
            # 8. Increment global running count
            self._increment_global_running_count()
            
            # 9. Record metrics
            self.metrics_collector.record_assignment(task, pool)
            
            logger.info(f"Successfully assigned task {task.id} to runner {runner.runner_id}")
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.id}: {e}", exc_info=True)
            raise TaskAssignmentError(f"Task assignment failed: {e}") from e
    
    def _allocate_slot(self, task: Task) -> Optional[Slot]:
        """
        Allocate a slot from Repo Pool Manager.
        
        Args:
            task: Task requiring a slot
            
        Returns:
            Allocated Slot or None if no slots available
            
        Requirements: 4.1, 4.2, 4.3
        """
        try:
            # Extract repo name from task metadata
            spec_name = task.metadata.get("spec_name", "unknown")
            repo_name = task.metadata.get("repo_name", spec_name)
            
            logger.info(f"Allocating slot for task {task.id} from repo '{repo_name}'")
            
            # Prepare metadata for slot
            slot_metadata = {
                "task_id": task.id,
                "spec_name": spec_name,
                "allocated_by": "dispatcher",
                "allocated_at": datetime.now().isoformat(),
            }
            
            # Allocate slot
            slot = self.repo_pool_manager.allocate_slot(repo_name, metadata=slot_metadata)
            
            if slot:
                logger.info(f"Allocated slot {slot.slot_id} for task {task.id}")
            else:
                logger.warning(f"No available slot for task {task.id} in repo '{repo_name}'")
            
            return slot
            
        except Exception as e:
            logger.error(f"Failed to allocate slot for task {task.id}: {e}")
            return None
    
    def _update_task_registry(self, task: Task, runner: Runner, slot: Slot) -> None:
        """
        Update Task Registry with task assignment information.
        
        Records:
        - Task state transition to RUNNING
        - Runner ID
        - Slot ID
        - TaskAssigned event
        
        Args:
            task: Assigned task
            runner: Launched runner
            slot: Allocated slot
            
        Requirements: 4.4, 10.1, 10.2, 10.3, 10.4
        """
        try:
            spec_name = task.metadata.get("spec_name", "unknown")
            
            # Update task state to RUNNING
            metadata = {
                "runner_id": runner.runner_id,
                "assigned_slot": slot.slot_id,
                "pool_name": runner.pool_name,
                "started_at": runner.started_at.isoformat(),
            }
            
            self.task_registry.update_task_state(
                spec_name=spec_name,
                task_id=task.id,
                new_state=TaskState.RUNNING,
                metadata=metadata
            )
            
            logger.info(
                f"Updated Task Registry: task {task.id} -> RUNNING "
                f"(runner={runner.runner_id}, slot={slot.slot_id})"
            )
            
        except Exception as e:
            logger.error(f"Failed to update Task Registry for task {task.id}: {e}")
            # Don't raise - runner is already launched, just log the error
    
    def _wait_for_runners(self, timeout: int) -> None:
        """
        Wait for running Agent Runners to complete.
        
        Monitors all running runners and waits for them to finish or timeout.
        
        Args:
            timeout: Maximum time to wait (seconds)
            
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
        """
        logger.info(f"Waiting for {self.runner_monitor.get_running_count()} runner(s) to complete...")
        
        start_time = time.time()
        
        while True:
            running_count = self.runner_monitor.get_running_count()
            
            if running_count == 0:
                logger.info("All runners completed")
                break
            
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(
                    f"Timeout reached ({timeout}s), {running_count} runner(s) still running"
                )
                # Force stop remaining runners
                self._force_stop_runners()
                break
            
            logger.info(
                f"Waiting for {running_count} runner(s) to complete "
                f"({elapsed:.1f}s / {timeout}s)"
            )
            time.sleep(5)
    
    def _force_stop_runners(self) -> None:
        """
        Force stop all running runners.
        
        Called when graceful shutdown timeout is reached.
        """
        logger.warning("Force stopping all running runners...")
        
        all_runners = self.runner_monitor.get_all_runners()
        
        for runner_id, runner_info in all_runners.items():
            if runner_info.state == RunnerState.RUNNING:
                logger.warning(f"Force stopping runner {runner_id}")
                
                # Update runner state
                self.runner_monitor.update_runner_state(runner_id, RunnerState.FAILED)
                
                # Release slot
                try:
                    slot_id = runner_info.runner.slot_id
                    self.repo_pool_manager.release_slot(slot_id, cleanup=True)
                    logger.info(f"Released slot {slot_id} for runner {runner_id}")
                except Exception as e:
                    logger.error(f"Failed to release slot for runner {runner_id}: {e}")
                
                # Decrement pool running count
                try:
                    pool = self.agent_pool_manager.get_pool_by_name(runner_info.runner.pool_name)
                    if pool:
                        self.agent_pool_manager.decrement_running_count(pool)
                except Exception as e:
                    logger.error(f"Failed to decrement pool count for runner {runner_id}: {e}")
                
                # Decrement global running count
                self._decrement_global_running_count()
    
    def handle_task_failure(
        self,
        task_id: str,
        spec_name: str,
        failure_reason: str = "unknown",
        runner_id: Optional[str] = None,
        slot_id: Optional[str] = None,
        pool_name: Optional[str] = None
    ) -> None:
        """
        Handle task failure and determine retry or permanent failure.
        
        Records the failure, checks retry eligibility, and either:
        - Re-queues the task for retry with exponential backoff
        - Marks the task as permanently FAILED
        
        Args:
            task_id: ID of failed task
            spec_name: Spec name
            failure_reason: Reason for failure
            runner_id: Optional runner ID
            slot_id: Optional slot ID to release
            pool_name: Optional pool name for decrementing count
            
        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
        """
        logger.warning(f"Handling failure for task {task_id}: {failure_reason}")
        
        # Record failure in retry manager
        self.retry_manager.record_failure(task_id, failure_reason)
        
        # Release slot if provided
        if slot_id:
            try:
                self.repo_pool_manager.release_slot(slot_id, cleanup=True)
                logger.info(f"Released slot {slot_id} for failed task {task_id}")
            except Exception as e:
                logger.error(f"Failed to release slot {slot_id}: {e}")
        
        # Decrement pool running count if provided
        if pool_name:
            try:
                pool = self.agent_pool_manager.get_pool_by_name(pool_name)
                if pool:
                    self.agent_pool_manager.decrement_running_count(pool)
            except Exception as e:
                logger.error(f"Failed to decrement pool count for {pool_name}: {e}")
        
        # Decrement global running count
        self._decrement_global_running_count()
        
        # Check if task has exceeded max retry attempts
        retry_count = self.retry_manager.get_retry_count(task_id)
        
        if retry_count < self.config.retry_max_attempts:
            # Task can be retried - re-queue it
            retry_info = self.retry_manager.get_retry_info(task_id)
            
            logger.info(
                f"Task {task_id} will be retried "
                f"(attempt {retry_count}/{self.config.retry_max_attempts})"
            )
            
            if retry_info and retry_info.next_retry_at:
                logger.info(f"Next retry scheduled for: {retry_info.next_retry_at.isoformat()}")
            
            # Get task from Task Registry and re-queue
            # The scheduler will check backoff timing before assigning
            try:
                task = self.task_monitor.task_registry_client.get_task(spec_name, task_id)
                if task:
                    self.task_queue.enqueue(task)
                    logger.info(f"Re-queued task {task_id} for retry")
                else:
                    logger.error(f"Failed to retrieve task {task_id} from registry")
            except Exception as e:
                logger.error(f"Failed to re-queue task {task_id}: {e}")
        else:
            # Max retries reached, mark as permanently failed
            logger.error(
                f"Task {task_id} permanently failed after {retry_count} retries"
            )
            
            # Record TaskFailed event
            self.event_recorder.record_task_failed(
                spec_name=spec_name,
                task_id=task_id,
                runner_id=runner_id,
                failure_reason=failure_reason,
                retry_count=retry_count
            )
            
            try:
                self.task_registry.update_task_state(
                    spec_name=spec_name,
                    task_id=task_id,
                    new_state=TaskState.FAILED,
                    metadata={
                        "reason": failure_reason,
                        "retries": retry_count,
                        "runner_id": runner_id,
                    }
                )
                
                # Clear retry info for failed task
                self.retry_manager.clear_retry_info(task_id)
                
                logger.info(f"Marked task {task_id} as FAILED in Task Registry")
            except Exception as e:
                logger.error(f"Failed to update task {task_id} to FAILED: {e}")
    
    def _handle_runner_timeout(self, runner_id: str, runner_info) -> None:
        """
        Handle runner timeout.
        
        Called by RunnerMonitor when a runner times out.
        Delegates to handle_task_failure for retry logic.
        
        Args:
            runner_id: ID of timed-out runner
            runner_info: RunnerInfo of timed-out runner
            
        Requirements: 8.3, 8.4, 9.1, 9.2, 9.3
        """
        logger.warning(f"Handling timeout for runner {runner_id}")
        
        task_id = runner_info.runner.task_id
        slot_id = runner_info.runner.slot_id
        pool_name = runner_info.runner.pool_name
        
        # Extract spec name from task metadata or runner info
        # This is a simplified approach - in production, spec_name should be stored
        spec_name = task_id.split("-")[0] if "-" in task_id else "unknown"
        
        # Handle failure with retry logic
        self.handle_task_failure(
            task_id=task_id,
            spec_name=spec_name,
            failure_reason="timeout",
            runner_id=runner_id,
            slot_id=slot_id,
            pool_name=pool_name
        )
    
    def handle_runner_completion(
        self,
        runner_id: str,
        task_id: str,
        spec_name: str,
        success: bool,
        slot_id: str,
        pool_name: str,
        failure_reason: Optional[str] = None
    ) -> None:
        """
        Handle runner completion notification.
        
        Called when an Agent Runner completes (successfully or with failure).
        Updates task state and handles retry logic for failures.
        
        Args:
            runner_id: ID of completed runner
            task_id: ID of completed task
            spec_name: Spec name
            success: Whether task completed successfully
            slot_id: Slot ID to release
            pool_name: Pool name for decrementing count
            failure_reason: Optional reason for failure
            
        Requirements: 6.3, 9.1, 9.3
        """
        logger.info(
            f"Handling completion for runner {runner_id}: "
            f"task={task_id}, success={success}"
        )
        
        # Get runner info for execution time calculation
        runner_info = self.runner_monitor.get_runner_status(runner_id)
        execution_time = None
        if runner_info:
            elapsed = (datetime.now() - runner_info.runner.started_at).total_seconds()
            execution_time = elapsed
        
        # Remove runner from monitoring
        self.runner_monitor.remove_runner(runner_id)
        
        if success:
            # Task completed successfully
            logger.info(f"Task {task_id} completed successfully")
            
            # Record RunnerFinished event
            self.event_recorder.record_runner_finished(
                spec_name=spec_name,
                task_id=task_id,
                runner_id=runner_id,
                slot_id=slot_id,
                success=True,
                execution_time_seconds=execution_time
            )
            
            # Record TaskCompleted event
            self.event_recorder.record_task_completed(
                spec_name=spec_name,
                task_id=task_id,
                runner_id=runner_id,
                execution_time_seconds=execution_time
            )
            
            # Release slot
            try:
                self.repo_pool_manager.release_slot(slot_id, cleanup=True)
                logger.info(f"Released slot {slot_id} for completed task {task_id}")
            except Exception as e:
                logger.error(f"Failed to release slot {slot_id}: {e}")
            
            # Decrement pool running count
            try:
                pool = self.agent_pool_manager.get_pool_by_name(pool_name)
                if pool:
                    self.agent_pool_manager.decrement_running_count(pool)
            except Exception as e:
                logger.error(f"Failed to decrement pool count for {pool_name}: {e}")
            
            # Decrement global running count
            self._decrement_global_running_count()
            
            # Update task state to DONE
            try:
                self.task_registry.update_task_state(
                    spec_name=spec_name,
                    task_id=task_id,
                    new_state=TaskState.DONE,
                    metadata={"runner_id": runner_id, "completed_at": datetime.now().isoformat()}
                )
                logger.info(f"Updated task {task_id} to DONE in Task Registry")
            except Exception as e:
                logger.error(f"Failed to update task {task_id} to DONE: {e}")
            
            # Clear retry info for successful task
            self.retry_manager.clear_retry_info(task_id)
        else:
            # Task failed
            logger.warning(f"Task {task_id} failed: {failure_reason}")
            
            # Record RunnerFinished event with failure
            self.event_recorder.record_runner_finished(
                spec_name=spec_name,
                task_id=task_id,
                runner_id=runner_id,
                slot_id=slot_id,
                success=False,
                execution_time_seconds=execution_time,
                failure_reason=failure_reason
            )
            
            # Handle failure with retry logic
            self.handle_task_failure(
                task_id=task_id,
                spec_name=spec_name,
                failure_reason=failure_reason or "unknown",
                runner_id=runner_id,
                slot_id=slot_id,
                pool_name=pool_name
            )
    
    def _check_for_deadlocks(self) -> None:
        """
        Check for deadlocks in task dependencies.
        
        Analyzes all tasks in the system to detect circular dependencies.
        Logs warnings and suggestions for manual intervention when deadlocks are found.
        
        Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
        """
        try:
            logger.info("Checking for deadlocks in task dependencies...")
            
            # Get all tasks from all specs
            all_tasks = []
            
            # Get all spec names from task registry
            registry_dir = Path(self.config.task_registry_dir)
            if registry_dir.exists():
                for spec_dir in registry_dir.iterdir():
                    if spec_dir.is_dir():
                        spec_name = spec_dir.name
                        try:
                            taskset = self.task_registry.get_taskset(spec_name)
                            if taskset:
                                all_tasks.extend(taskset.tasks)
                        except Exception as e:
                            logger.debug(f"Could not load taskset for {spec_name}: {e}")
            
            if not all_tasks:
                logger.debug("No tasks found for deadlock detection")
                return
            
            # Detect deadlocks
            cycles = self.deadlock_detector.detect_deadlock(all_tasks)
            
            if cycles:
                # Deadlock detected - log warnings and request manual intervention
                logger.warning(
                    f"DEADLOCK DETECTED: {len(cycles)} circular "
                    f"{'dependency' if len(cycles) == 1 else 'dependencies'} found!"
                )
                
                for i, cycle in enumerate(cycles, 1):
                    cycle_str = " -> ".join(cycle) + f" -> {cycle[0]}"
                    logger.warning(f"  Cycle {i}: {cycle_str}")
                
                # Get resolution suggestions
                suggestions = self.deadlock_detector.suggest_resolution(cycles)
                logger.warning("Manual intervention required. Suggested resolutions:")
                for suggestion in suggestions:
                    logger.warning(f"  - {suggestion}")
                
                # Get blocked tasks
                blocked_tasks = self.deadlock_detector.get_blocked_tasks(all_tasks)
                logger.warning(
                    f"{len(blocked_tasks)} task(s) are blocked by circular dependencies: "
                    f"{', '.join(t.id for t in blocked_tasks)}"
                )
                
            else:
                logger.info("No deadlocks detected")
                
        except Exception as e:
            logger.error(f"Error during deadlock detection: {e}", exc_info=True)
    
    def check_deadlock_now(self, raise_on_deadlock: bool = False) -> bool:
        """
        Manually trigger deadlock detection.
        
        Can be called externally to check for deadlocks on demand.
        
        Args:
            raise_on_deadlock: If True, raise DeadlockDetectedError on detection
            
        Returns:
            True if deadlock detected, False otherwise
            
        Raises:
            DeadlockDetectedError: If deadlock detected and raise_on_deadlock is True
            
        Requirements: 13.1, 13.2, 13.3, 13.4
        """
        logger.info("Manual deadlock check requested")
        
        # Get all tasks
        all_tasks = []
        registry_dir = Path(self.config.task_registry_dir)
        if registry_dir.exists():
            for spec_dir in registry_dir.iterdir():
                if spec_dir.is_dir():
                    spec_name = spec_dir.name
                    try:
                        taskset = self.task_registry.get_taskset(spec_name)
                        if taskset:
                            all_tasks.extend(taskset.tasks)
                    except Exception as e:
                        logger.debug(f"Could not load taskset for {spec_name}: {e}")
        
        # Check for deadlock
        return self.deadlock_detector.check_for_deadlock(all_tasks, raise_on_deadlock)
    
    def _increment_global_running_count(self) -> None:
        """
        Increment the global running task count.
        
        Thread-safe increment of global concurrency counter.
        
        Requirements: 6.1, 6.4
        """
        with self._global_running_lock:
            self._global_running_count += 1
            logger.debug(
                f"Global running count incremented: {self._global_running_count}/"
                f"{self.config.max_global_concurrency}"
            )
    
    def _decrement_global_running_count(self) -> None:
        """
        Decrement the global running task count.
        
        Thread-safe decrement of global concurrency counter.
        
        Requirements: 6.3
        """
        with self._global_running_lock:
            if self._global_running_count > 0:
                self._global_running_count -= 1
                logger.debug(
                    f"Global running count decremented: {self._global_running_count}/"
                    f"{self.config.max_global_concurrency}"
                )
            else:
                logger.warning("Attempted to decrement global running count but it's already 0")
    
    def get_global_running_count(self) -> int:
        """
        Get the current global running task count.
        
        Returns:
            Number of tasks currently running across all pools
            
        Requirements: 6.1, 6.4
        """
        with self._global_running_lock:
            return self._global_running_count
    
    def can_accept_task_globally(self) -> bool:
        """
        Check if the dispatcher can accept a new task globally.
        
        Checks against the global max concurrency limit.
        
        Returns:
            True if global limit not reached, False otherwise
            
        Requirements: 6.1, 6.4
        """
        with self._global_running_lock:
            can_accept = self._global_running_count < self.config.max_global_concurrency
            if not can_accept:
                logger.debug(
                    f"Global concurrency limit reached: {self._global_running_count}/"
                    f"{self.config.max_global_concurrency}"
                )
            return can_accept
    
    def update_task_priority(
        self,
        spec_name: str,
        task_id: str,
        new_priority: int
    ) -> bool:
        """
        Dynamically update the priority of a task.
        
        If the task is in the queue, it will be re-queued with the new priority.
        If the task is already running, the priority change will not affect it.
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            new_priority: New priority value (higher = more important)
            
        Returns:
            True if priority was updated successfully, False otherwise
            
        Requirements: 7.4
        """
        logger.info(f"Updating priority for task {task_id} to {new_priority}")
        
        try:
            # Get taskset from Task Registry
            taskset = self.task_registry.get_taskset(spec_name)
            if not taskset:
                logger.error(f"Taskset not found for spec {spec_name}")
                return False
            
            # Find the task
            task = None
            for t in taskset.tasks:
                if t.id == task_id:
                    task = t
                    break
            
            if not task:
                logger.error(f"Task {task_id} not found in spec {spec_name}")
                return False
            
            # Update task priority
            old_priority = task.priority
            task.priority = new_priority
            
            # Save updated task (update metadata to persist priority)
            self.task_registry.update_task_state(
                spec_name=spec_name,
                task_id=task_id,
                new_state=task.state,
                metadata={"priority": new_priority}
            )
            
            # If task is in queue, re-queue it with new priority
            queued_tasks = self.task_queue.get_all_tasks()
            task_in_queue = any(t.id == task_id for t in queued_tasks)
            
            if task_in_queue:
                # Remove old entry and re-add with new priority
                # This is done by clearing and re-adding all tasks
                all_tasks = []
                while not self.task_queue.is_empty():
                    t = self.task_queue.dequeue()
                    if t:
                        if t.id == task_id:
                            t.priority = new_priority
                        all_tasks.append(t)
                
                # Re-enqueue all tasks
                for t in all_tasks:
                    self.task_queue.enqueue(t)
                
                logger.info(
                    f"Updated task {task_id} priority from {old_priority} to {new_priority} "
                    f"and re-queued"
                )
            else:
                logger.info(
                    f"Updated task {task_id} priority from {old_priority} to {new_priority} "
                    f"(not in queue)"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update priority for task {task_id}: {e}")
            return False
    
    def set_scheduling_policy(self, policy: SchedulingPolicy) -> None:
        """
        Dynamically change the scheduling policy.
        
        This allows enabling or disabling priority-based scheduling at runtime.
        
        Args:
            policy: New scheduling policy to use
            
        Requirements: 7.5
        """
        logger.info(f"Changing scheduling policy from {self.config.scheduling_policy.value} to {policy.value}")
        
        self.config.scheduling_policy = policy
        self.scheduler.policy = policy
        
        logger.info(f"Scheduling policy updated to {policy.value}")
    
    def disable_priority_scheduling(self) -> None:
        """
        Disable priority-based scheduling by switching to FIFO.
        
        Convenience method to disable priority scheduling.
        
        Requirements: 7.5
        """
        logger.info("Disabling priority-based scheduling (switching to FIFO)")
        self.set_scheduling_policy(SchedulingPolicy.FIFO)
    
    def enable_priority_scheduling(self) -> None:
        """
        Enable priority-based scheduling.
        
        Convenience method to enable priority scheduling.
        
        Requirements: 7.5
        """
        logger.info("Enabling priority-based scheduling")
        self.set_scheduling_policy(SchedulingPolicy.PRIORITY)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current Dispatcher status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "running": self.running,
            "scheduling_policy": self.config.scheduling_policy.value,
            "queue_size": self.task_queue.size(),
            "running_tasks": self.runner_monitor.get_running_count(),
            "global_running_count": self.get_global_running_count(),
            "max_global_concurrency": self.config.max_global_concurrency,
            "pool_statuses": self.agent_pool_manager.get_all_pool_statuses(),
            "metrics": self.metrics_collector.get_metrics(),
            "retry_info": {
                task_id: info.to_dict()
                for task_id, info in self.retry_manager.get_all_retry_info().items()
            },
            "deadlock_info": {
                "last_check": self.deadlock_detector.get_last_check_time().isoformat()
                if self.deadlock_detector.get_last_check_time() else None,
                "detected_cycles": self.deadlock_detector.get_detected_cycles(),
            },
            "event_recorder": self.event_recorder.get_statistics(),
        }

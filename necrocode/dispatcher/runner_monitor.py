"""
Runner Monitor for the Dispatcher component.

Monitors Agent Runners, tracks heartbeats, detects timeouts, and manages runner state.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable

from necrocode.dispatcher.models import Runner, RunnerInfo, RunnerState

logger = logging.getLogger(__name__)


class RunnerMonitor:
    """
    Agent Runner monitoring and heartbeat management.
    
    Tracks running Agent Runners, monitors their heartbeats, detects timeouts,
    and triggers task reassignment when runners fail or timeout.
    """
    
    def __init__(
        self,
        heartbeat_timeout: int = 60,
        timeout_handler: Optional[Callable[[str, RunnerInfo], None]] = None
    ):
        """
        Initialize the RunnerMonitor.
        
        Args:
            heartbeat_timeout: Timeout in seconds for heartbeat checks (default: 60)
            timeout_handler: Optional callback for handling timeouts
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.timeout_handler = timeout_handler
        self.runners: Dict[str, RunnerInfo] = {}
        self.lock = threading.Lock()
        logger.info(
            f"RunnerMonitor initialized with heartbeat_timeout={heartbeat_timeout}s"
        )
    
    def add_runner(self, runner: Runner) -> None:
        """
        Add a runner to the monitoring list.
        
        Args:
            runner: Runner instance to monitor
        """
        with self.lock:
            runner_info = RunnerInfo(
                runner=runner,
                last_heartbeat=datetime.now(),
                state=RunnerState.RUNNING
            )
            self.runners[runner.runner_id] = runner_info
            logger.info(
                f"Added runner {runner.runner_id} for task {runner.task_id} "
                f"to monitoring (pool: {runner.pool_name})"
            )
    
    def remove_runner(self, runner_id: str) -> None:
        """
        Remove a runner from the monitoring list.
        
        Args:
            runner_id: ID of the runner to remove
        """
        with self.lock:
            if runner_id in self.runners:
                runner_info = self.runners[runner_id]
                del self.runners[runner_id]
                logger.info(
                    f"Removed runner {runner_id} from monitoring "
                    f"(task: {runner_info.runner.task_id}, "
                    f"state: {runner_info.state.value})"
                )
            else:
                logger.warning(f"Attempted to remove unknown runner {runner_id}")
    
    def update_heartbeat(self, runner_id: str) -> None:
        """
        Update the heartbeat timestamp for a runner.
        
        Args:
            runner_id: ID of the runner to update
        """
        with self.lock:
            if runner_id in self.runners:
                self.runners[runner_id].last_heartbeat = datetime.now()
                logger.debug(f"Updated heartbeat for runner {runner_id}")
            else:
                logger.warning(
                    f"Received heartbeat for unknown runner {runner_id}"
                )
    
    def check_heartbeats(self) -> None:
        """
        Check all runners for heartbeat timeouts.
        
        Detects runners that haven't sent a heartbeat within the timeout period
        and triggers timeout handling.
        """
        now = datetime.now()
        timeout_threshold = timedelta(seconds=self.heartbeat_timeout)
        
        with self.lock:
            timed_out_runners = []
            
            for runner_id, info in self.runners.items():
                elapsed = now - info.last_heartbeat
                
                if elapsed > timeout_threshold and info.state == RunnerState.RUNNING:
                    timed_out_runners.append((runner_id, info))
                    logger.warning(
                        f"Runner {runner_id} timeout detected "
                        f"(task: {info.runner.task_id}, "
                        f"elapsed: {elapsed.total_seconds():.1f}s)"
                    )
        
        # Handle timeouts outside the lock to avoid deadlock
        for runner_id, info in timed_out_runners:
            self._handle_timeout(runner_id, info)
    
    def _handle_timeout(self, runner_id: str, info: RunnerInfo) -> None:
        """
        Handle a runner timeout.
        
        Updates the runner state to FAILED and triggers the timeout handler
        for task reassignment.
        
        Args:
            runner_id: ID of the timed-out runner
            info: RunnerInfo of the timed-out runner
        """
        with self.lock:
            # Update state to FAILED
            if runner_id in self.runners:
                self.runners[runner_id].state = RunnerState.FAILED
                self.runners[runner_id].runner.state = RunnerState.FAILED
        
        logger.error(
            f"Runner {runner_id} timed out and marked as FAILED "
            f"(task: {info.runner.task_id}, pool: {info.runner.pool_name})"
        )
        
        # Trigger timeout handler if provided
        if self.timeout_handler:
            try:
                self.timeout_handler(runner_id, info)
                logger.info(
                    f"Timeout handler executed for runner {runner_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error in timeout handler for runner {runner_id}: {e}",
                    exc_info=True
                )
    
    def get_runner_status(self, runner_id: str) -> Optional[RunnerInfo]:
        """
        Get the current status of a runner.
        
        Args:
            runner_id: ID of the runner
            
        Returns:
            RunnerInfo if the runner exists, None otherwise
        """
        with self.lock:
            return self.runners.get(runner_id)
    
    def get_all_runners(self) -> Dict[str, RunnerInfo]:
        """
        Get all monitored runners.
        
        Returns:
            Dictionary mapping runner IDs to RunnerInfo
        """
        with self.lock:
            return dict(self.runners)
    
    def get_running_count(self) -> int:
        """
        Get the count of currently running runners.
        
        Returns:
            Number of runners in RUNNING state
        """
        with self.lock:
            return sum(
                1 for info in self.runners.values()
                if info.state == RunnerState.RUNNING
            )
    
    def update_runner_state(
        self,
        runner_id: str,
        state: RunnerState
    ) -> None:
        """
        Update the state of a runner.
        
        Args:
            runner_id: ID of the runner
            state: New state for the runner
        """
        with self.lock:
            if runner_id in self.runners:
                old_state = self.runners[runner_id].state
                self.runners[runner_id].state = state
                self.runners[runner_id].runner.state = state
                logger.info(
                    f"Runner {runner_id} state changed: "
                    f"{old_state.value} -> {state.value}"
                )
            else:
                logger.warning(
                    f"Attempted to update state for unknown runner {runner_id}"
                )

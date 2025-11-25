"""
Parallel execution coordination for Agent Runner.

This module provides functionality to coordinate multiple Agent Runner instances
executing tasks in parallel, including resource conflict detection and
concurrent runner tracking.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class RunnerInstance:
    """
    Information about a running Agent Runner instance.
    
    Tracks the state and resource usage of a single runner instance
    for parallel execution coordination.
    
    Requirements: 14.1, 14.2
    """
    runner_id: str
    task_id: str
    spec_name: str
    workspace_path: Path
    start_time: datetime
    last_heartbeat: datetime
    
    # Resource usage
    files_locked: Set[str] = field(default_factory=set)
    branches_used: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "runner_id": self.runner_id,
            "task_id": self.task_id,
            "spec_name": self.spec_name,
            "workspace_path": str(self.workspace_path),
            "start_time": self.start_time.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "files_locked": list(self.files_locked),
            "branches_used": list(self.branches_used),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RunnerInstance":
        """Create from dictionary."""
        data = data.copy()
        data["workspace_path"] = Path(data["workspace_path"])
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])
        data["files_locked"] = set(data.get("files_locked", []))
        data["branches_used"] = set(data.get("branches_used", []))
        return cls(**data)


class ParallelCoordinator:
    """
    Coordinates parallel execution of multiple Agent Runner instances.
    
    Provides functionality to:
    - Track active runner instances
    - Detect resource conflicts
    - Enforce maximum parallel execution limits
    - Record parallel execution metrics
    
    This coordinator is completely stateless - all state is stored in files
    and can be reconstructed from the filesystem.
    
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
    """
    
    def __init__(
        self,
        coordination_dir: Optional[Path] = None,
        max_parallel_runners: Optional[int] = None,
        heartbeat_timeout_seconds: float = 300.0,  # 5 minutes
    ):
        """
        Initialize parallel coordinator.
        
        Args:
            coordination_dir: Directory for coordination files
            max_parallel_runners: Maximum number of parallel runners (None = unlimited)
            heartbeat_timeout_seconds: Timeout for runner heartbeats
            
        Requirements: 14.4, 14.5
        """
        # Use default coordination directory if not specified
        if coordination_dir is None:
            coordination_dir = Path.home() / ".necrocode" / "runner_coordination"
        
        self.coordination_dir = coordination_dir
        self.coordination_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_parallel_runners = max_parallel_runners
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        
        # Thread-safe lock for file operations
        self._lock = Lock()
        
        logger.info(
            f"ParallelCoordinator initialized: "
            f"dir={coordination_dir}, max_parallel={max_parallel_runners}"
        )
    
    def register_runner(
        self,
        runner_id: str,
        task_id: str,
        spec_name: str,
        workspace_path: Path,
    ) -> bool:
        """
        Register a new runner instance.
        
        Checks if the runner can start based on:
        - Maximum parallel runner limit
        - Resource conflicts with existing runners
        
        Args:
            runner_id: Unique runner ID
            task_id: Task ID being executed
            spec_name: Spec name
            workspace_path: Workspace path for this runner
            
        Returns:
            True if registration successful, False if rejected
            
        Requirements: 14.1, 14.2, 14.5
        """
        with self._lock:
            # Clean up stale runners
            self._cleanup_stale_runners()
            
            # Check maximum parallel runners limit
            active_runners = self._get_active_runners()
            
            if self.max_parallel_runners is not None:
                if len(active_runners) >= self.max_parallel_runners:
                    logger.warning(
                        f"Maximum parallel runners limit reached: "
                        f"{len(active_runners)}/{self.max_parallel_runners}"
                    )
                    return False
            
            # Check for workspace conflicts
            for runner in active_runners.values():
                if runner.workspace_path == workspace_path:
                    logger.error(
                        f"Workspace conflict detected: {workspace_path} "
                        f"already in use by runner {runner.runner_id}"
                    )
                    return False
            
            # Register runner
            instance = RunnerInstance(
                runner_id=runner_id,
                task_id=task_id,
                spec_name=spec_name,
                workspace_path=workspace_path,
                start_time=datetime.now(),
                last_heartbeat=datetime.now(),
            )
            
            self._save_runner_instance(instance)
            
            logger.info(
                f"Runner registered: {runner_id} "
                f"(active: {len(active_runners) + 1})"
            )
            
            return True
    
    def unregister_runner(self, runner_id: str) -> None:
        """
        Unregister a runner instance.
        
        Removes the runner from active tracking, freeing up resources
        for other runners.
        
        Args:
            runner_id: Runner ID to unregister
            
        Requirements: 14.1
        """
        with self._lock:
            runner_file = self.coordination_dir / f"{runner_id}.json"
            
            if runner_file.exists():
                try:
                    runner_file.unlink()
                    logger.info(f"Runner unregistered: {runner_id}")
                except Exception as e:
                    logger.error(f"Failed to unregister runner {runner_id}: {e}")
    
    def update_heartbeat(self, runner_id: str) -> None:
        """
        Update runner heartbeat timestamp.
        
        Should be called periodically by active runners to indicate
        they are still alive.
        
        Args:
            runner_id: Runner ID
            
        Requirements: 14.1
        """
        with self._lock:
            runner_file = self.coordination_dir / f"{runner_id}.json"
            
            if not runner_file.exists():
                logger.warning(f"Runner not found for heartbeat update: {runner_id}")
                return
            
            try:
                # Load runner instance
                with open(runner_file, "r") as f:
                    data = json.load(f)
                
                instance = RunnerInstance.from_dict(data)
                
                # Update heartbeat
                instance.last_heartbeat = datetime.now()
                
                # Save updated instance
                self._save_runner_instance(instance)
                
            except Exception as e:
                logger.error(f"Failed to update heartbeat for {runner_id}: {e}")
    
    def detect_conflicts(
        self,
        runner_id: str,
        files: Optional[List[str]] = None,
        branches: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Detect resource conflicts with other runners.
        
        Checks if the specified files or branches are being used by
        other active runners.
        
        Args:
            runner_id: Runner ID checking for conflicts
            files: List of file paths to check
            branches: List of branch names to check
            
        Returns:
            List of conflict descriptions (empty if no conflicts)
            
        Requirements: 14.3
        """
        with self._lock:
            conflicts = []
            
            # Clean up stale runners
            self._cleanup_stale_runners()
            
            # Get active runners
            active_runners = self._get_active_runners()
            
            # Check each active runner (excluding self)
            for other_id, other_runner in active_runners.items():
                if other_id == runner_id:
                    continue
                
                # Check file conflicts
                if files:
                    file_conflicts = set(files) & other_runner.files_locked
                    if file_conflicts:
                        conflicts.append(
                            f"File conflict with runner {other_id}: "
                            f"{', '.join(file_conflicts)}"
                        )
                
                # Check branch conflicts
                if branches:
                    branch_conflicts = set(branches) & other_runner.branches_used
                    if branch_conflicts:
                        conflicts.append(
                            f"Branch conflict with runner {other_id}: "
                            f"{', '.join(branch_conflicts)}"
                        )
            
            if conflicts:
                logger.warning(
                    f"Resource conflicts detected for runner {runner_id}: "
                    f"{len(conflicts)} conflicts"
                )
            
            return conflicts
    
    def update_resources(
        self,
        runner_id: str,
        files: Optional[List[str]] = None,
        branches: Optional[List[str]] = None,
    ) -> None:
        """
        Update resources being used by a runner.
        
        Args:
            runner_id: Runner ID
            files: List of file paths being used
            branches: List of branch names being used
            
        Requirements: 14.3
        """
        with self._lock:
            runner_file = self.coordination_dir / f"{runner_id}.json"
            
            if not runner_file.exists():
                logger.warning(f"Runner not found for resource update: {runner_id}")
                return
            
            try:
                # Load runner instance
                with open(runner_file, "r") as f:
                    data = json.load(f)
                
                instance = RunnerInstance.from_dict(data)
                
                # Update resources
                if files is not None:
                    instance.files_locked = set(files)
                if branches is not None:
                    instance.branches_used = set(branches)
                
                # Update heartbeat
                instance.last_heartbeat = datetime.now()
                
                # Save updated instance
                self._save_runner_instance(instance)
                
            except Exception as e:
                logger.error(f"Failed to update resources for {runner_id}: {e}")
    
    def get_concurrent_count(self) -> int:
        """
        Get current number of concurrent runners.
        
        Returns:
            Number of active runners
            
        Requirements: 14.4
        """
        with self._lock:
            self._cleanup_stale_runners()
            active_runners = self._get_active_runners()
            return len(active_runners)
    
    def get_wait_time(self) -> float:
        """
        Calculate estimated wait time for a new runner.
        
        Based on current load and maximum parallel runners limit.
        
        Returns:
            Estimated wait time in seconds (0 if can start immediately)
            
        Requirements: 14.4
        """
        with self._lock:
            self._cleanup_stale_runners()
            active_runners = self._get_active_runners()
            
            # If no limit or under limit, no wait time
            if self.max_parallel_runners is None:
                return 0.0
            
            if len(active_runners) < self.max_parallel_runners:
                return 0.0
            
            # Estimate wait time based on oldest runner
            # (assuming FIFO completion)
            if not active_runners:
                return 0.0
            
            oldest_runner = min(
                active_runners.values(),
                key=lambda r: r.start_time
            )
            
            # Estimate based on how long oldest runner has been running
            elapsed = (datetime.now() - oldest_runner.start_time).total_seconds()
            
            # Assume average task takes 30 minutes, estimate remaining time
            estimated_remaining = max(0, 1800 - elapsed)
            
            return estimated_remaining
    
    def get_status(self) -> Dict:
        """
        Get current coordination status.
        
        Returns:
            Dictionary with coordination status information
            
        Requirements: 14.4
        """
        with self._lock:
            self._cleanup_stale_runners()
            active_runners = self._get_active_runners()
            
            return {
                "active_runners": len(active_runners),
                "max_parallel_runners": self.max_parallel_runners,
                "runners": [
                    {
                        "runner_id": r.runner_id,
                        "task_id": r.task_id,
                        "spec_name": r.spec_name,
                        "elapsed_seconds": (
                            datetime.now() - r.start_time
                        ).total_seconds(),
                    }
                    for r in active_runners.values()
                ],
            }
    
    def _get_active_runners(self) -> Dict[str, RunnerInstance]:
        """
        Get all active runner instances.
        
        Returns:
            Dictionary mapping runner_id to RunnerInstance
        """
        active_runners = {}
        
        # Read all runner files
        for runner_file in self.coordination_dir.glob("*.json"):
            try:
                with open(runner_file, "r") as f:
                    data = json.load(f)
                
                instance = RunnerInstance.from_dict(data)
                active_runners[instance.runner_id] = instance
                
            except Exception as e:
                logger.warning(f"Failed to load runner file {runner_file}: {e}")
        
        return active_runners
    
    def _cleanup_stale_runners(self) -> None:
        """
        Clean up stale runner instances.
        
        Removes runners that haven't sent a heartbeat within the timeout period.
        """
        now = datetime.now()
        
        for runner_file in self.coordination_dir.glob("*.json"):
            try:
                with open(runner_file, "r") as f:
                    data = json.load(f)
                
                instance = RunnerInstance.from_dict(data)
                
                # Check if heartbeat is stale
                elapsed = (now - instance.last_heartbeat).total_seconds()
                
                if elapsed > self.heartbeat_timeout_seconds:
                    logger.warning(
                        f"Removing stale runner: {instance.runner_id} "
                        f"(last heartbeat: {elapsed:.0f}s ago)"
                    )
                    runner_file.unlink()
                    
            except Exception as e:
                logger.warning(f"Failed to check runner file {runner_file}: {e}")
    
    def _save_runner_instance(self, instance: RunnerInstance) -> None:
        """
        Save runner instance to file.
        
        Args:
            instance: Runner instance to save
        """
        runner_file = self.coordination_dir / f"{instance.runner_id}.json"
        
        try:
            with open(runner_file, "w") as f:
                json.dump(instance.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save runner instance {instance.runner_id}: {e}")
            raise


class ParallelExecutionContext:
    """
    Context manager for parallel execution coordination.
    
    Automatically registers/unregisters runner and updates heartbeat.
    
    Requirements: 14.1, 14.2
    """
    
    def __init__(
        self,
        coordinator: ParallelCoordinator,
        runner_id: str,
        task_id: str,
        spec_name: str,
        workspace_path: Path,
        heartbeat_interval: float = 30.0,  # 30 seconds
    ):
        """
        Initialize parallel execution context.
        
        Args:
            coordinator: Parallel coordinator
            runner_id: Runner ID
            task_id: Task ID
            spec_name: Spec name
            workspace_path: Workspace path
            heartbeat_interval: Heartbeat update interval in seconds
        """
        self.coordinator = coordinator
        self.runner_id = runner_id
        self.task_id = task_id
        self.spec_name = spec_name
        self.workspace_path = workspace_path
        self.heartbeat_interval = heartbeat_interval
        
        self._last_heartbeat = 0.0
        self._registered = False
    
    def __enter__(self):
        """Enter context - register runner."""
        # Register runner
        success = self.coordinator.register_runner(
            runner_id=self.runner_id,
            task_id=self.task_id,
            spec_name=self.spec_name,
            workspace_path=self.workspace_path,
        )
        
        if not success:
            raise RuntimeError(
                f"Failed to register runner {self.runner_id}: "
                "maximum parallel runners limit reached or resource conflict"
            )
        
        self._registered = True
        self._last_heartbeat = time.time()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - unregister runner."""
        if self._registered:
            self.coordinator.unregister_runner(self.runner_id)
    
    def update_heartbeat_if_needed(self) -> None:
        """Update heartbeat if interval has elapsed."""
        now = time.time()
        
        if now - self._last_heartbeat >= self.heartbeat_interval:
            self.coordinator.update_heartbeat(self.runner_id)
            self._last_heartbeat = now

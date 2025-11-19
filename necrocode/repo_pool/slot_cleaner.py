"""Slot cleanup operations for Repo Pool Manager."""

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from necrocode.repo_pool.exceptions import CleanupError, GitOperationError
from necrocode.repo_pool.git_operations import GitOperations
from necrocode.repo_pool.models import CleanupResult, Slot, SlotState


logger = logging.getLogger(__name__)


@dataclass
class RepairResult:
    """Result of a slot repair operation."""
    slot_id: str
    success: bool
    actions_taken: List[str]
    errors: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CleanupRecord:
    """Record of a cleanup operation."""
    slot_id: str
    operation_type: str  # "before_allocation" or "after_release"
    success: bool
    duration_seconds: float
    operations: List[str]
    errors: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class SlotCleaner:
    """Slot cleanup operations."""
    
    def __init__(self, git_ops: Optional[GitOperations] = None):
        """
        Initialize SlotCleaner.
        
        Args:
            git_ops: GitOperations instance (creates new one if not provided)
        """
        self.git_ops = git_ops or GitOperations()
        self.cleanup_log: List[CleanupRecord] = []
        
        # Background cleanup support
        self._background_executor: Optional[ThreadPoolExecutor] = None
        self._background_futures: Dict[str, Future] = {}
        self._background_lock = threading.Lock()
    
    def cleanup_before_allocation(self, slot: Slot) -> CleanupResult:
        """
        Cleanup slot before allocation.
        
        Performs:
        1. git fetch --all (update to latest remote state)
        2. git clean -fdx (remove untracked files)
        3. git reset --hard (reset working directory)
        
        Args:
            slot: Slot to cleanup
            
        Returns:
            CleanupResult with operation details
            
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        start_time = time.time()
        operations = []
        errors = []
        
        try:
            # Mark slot as cleaning
            original_state = slot.state
            slot.state = SlotState.CLEANING
            
            # 1. Fetch all remote branches
            try:
                fetch_result = self.git_ops.fetch_all(slot.slot_path)
                operations.append("fetch")
                if not fetch_result.success:
                    errors.append(f"Fetch failed: {fetch_result.stderr}")
            except Exception as e:
                errors.append(f"Fetch error: {str(e)}")
            
            # 2. Clean untracked files
            try:
                clean_result = self.git_ops.clean(slot.slot_path, force=True)
                operations.append("clean")
                if not clean_result.success:
                    errors.append(f"Clean failed: {clean_result.stderr}")
            except Exception as e:
                errors.append(f"Clean error: {str(e)}")
            
            # 3. Reset working directory
            try:
                reset_result = self.git_ops.reset_hard(slot.slot_path)
                operations.append("reset")
                if not reset_result.success:
                    errors.append(f"Reset failed: {reset_result.stderr}")
            except Exception as e:
                errors.append(f"Reset error: {str(e)}")
            
            # Update slot git information
            try:
                slot.current_branch = self.git_ops.get_current_branch(slot.slot_path)
                slot.current_commit = self.git_ops.get_current_commit(slot.slot_path)
            except Exception as e:
                errors.append(f"Failed to update git info: {str(e)}")
            
            duration = time.time() - start_time
            success = len(errors) == 0
            
            # Restore state if cleanup failed
            if not success:
                slot.state = SlotState.ERROR
            else:
                slot.state = original_state
            
            result = CleanupResult(
                slot_id=slot.slot_id,
                success=success,
                duration_seconds=duration,
                operations=operations,
                errors=errors
            )
            
            # Log the cleanup
            self._log_cleanup(
                slot.slot_id,
                "before_allocation",
                success,
                duration,
                operations,
                errors
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            slot.state = SlotState.ERROR
            
            result = CleanupResult(
                slot_id=slot.slot_id,
                success=False,
                duration_seconds=duration,
                operations=operations,
                errors=errors + [f"Unexpected error: {str(e)}"]
            )
            
            self._log_cleanup(
                slot.slot_id,
                "before_allocation",
                False,
                duration,
                operations,
                errors + [str(e)]
            )
            
            return result
    
    def cleanup_after_release(self, slot: Slot) -> CleanupResult:
        """
        Cleanup slot after release.
        
        Performs the same operations as cleanup_before_allocation:
        1. git fetch --all
        2. git clean -fdx
        3. git reset --hard
        
        Args:
            slot: Slot to cleanup
            
        Returns:
            CleanupResult with operation details
            
        Requirements: 3.4
        """
        start_time = time.time()
        operations = []
        errors = []
        
        try:
            # Mark slot as cleaning
            slot.state = SlotState.CLEANING
            
            # 1. Fetch all remote branches
            try:
                fetch_result = self.git_ops.fetch_all(slot.slot_path)
                operations.append("fetch")
                if not fetch_result.success:
                    errors.append(f"Fetch failed: {fetch_result.stderr}")
            except Exception as e:
                errors.append(f"Fetch error: {str(e)}")
            
            # 2. Clean untracked files
            try:
                clean_result = self.git_ops.clean(slot.slot_path, force=True)
                operations.append("clean")
                if not clean_result.success:
                    errors.append(f"Clean failed: {clean_result.stderr}")
            except Exception as e:
                errors.append(f"Clean error: {str(e)}")
            
            # 3. Reset working directory
            try:
                reset_result = self.git_ops.reset_hard(slot.slot_path)
                operations.append("reset")
                if not reset_result.success:
                    errors.append(f"Reset failed: {reset_result.stderr}")
            except Exception as e:
                errors.append(f"Reset error: {str(e)}")
            
            # Update slot git information
            try:
                slot.current_branch = self.git_ops.get_current_branch(slot.slot_path)
                slot.current_commit = self.git_ops.get_current_commit(slot.slot_path)
            except Exception as e:
                errors.append(f"Failed to update git info: {str(e)}")
            
            duration = time.time() - start_time
            success = len(errors) == 0
            
            # Set final state
            if success:
                slot.state = SlotState.AVAILABLE
            else:
                slot.state = SlotState.ERROR
            
            result = CleanupResult(
                slot_id=slot.slot_id,
                success=success,
                duration_seconds=duration,
                operations=operations,
                errors=errors
            )
            
            # Log the cleanup
            self._log_cleanup(
                slot.slot_id,
                "after_release",
                success,
                duration,
                operations,
                errors
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            slot.state = SlotState.ERROR
            
            result = CleanupResult(
                slot_id=slot.slot_id,
                success=False,
                duration_seconds=duration,
                operations=operations,
                errors=errors + [f"Unexpected error: {str(e)}"]
            )
            
            self._log_cleanup(
                slot.slot_id,
                "after_release",
                False,
                duration,
                operations,
                errors + [str(e)]
            )
            
            return result
    
    def _log_cleanup(
        self,
        slot_id: str,
        operation_type: str,
        success: bool,
        duration: float,
        operations: List[str],
        errors: List[str]
    ) -> None:
        """
        Log a cleanup operation.
        
        Args:
            slot_id: Slot identifier
            operation_type: Type of cleanup operation
            success: Whether cleanup succeeded
            duration: Duration in seconds
            operations: List of operations performed
            errors: List of errors encountered
        """
        record = CleanupRecord(
            slot_id=slot_id,
            operation_type=operation_type,
            success=success,
            duration_seconds=duration,
            operations=operations,
            errors=errors
        )
        self.cleanup_log.append(record)
    
    def verify_slot_integrity(self, slot: Slot) -> bool:
        """
        Verify slot integrity.
        
        Checks:
        1. Slot directory exists
        2. .git directory exists
        3. Working tree is valid (can get current branch/commit)
        4. Repository is not corrupted
        
        Args:
            slot: Slot to verify
            
        Returns:
            True if slot is valid, False otherwise
            
        Requirements: 9.2
        """
        try:
            # Check if slot directory exists
            if not slot.slot_path.exists():
                return False
            
            # Check if .git directory exists
            git_dir = slot.slot_path / ".git"
            if not git_dir.exists() or not git_dir.is_dir():
                return False
            
            # Try to get current branch (validates git repository)
            try:
                branch = self.git_ops.get_current_branch(slot.slot_path)
                if not branch:
                    return False
            except (GitOperationError, Exception):
                return False
            
            # Try to get current commit
            try:
                commit = self.git_ops.get_current_commit(slot.slot_path)
                if not commit:
                    return False
            except (GitOperationError, Exception):
                return False
            
            # Check if working tree is clean (can run git status)
            try:
                is_clean = self.git_ops.is_clean_working_tree(slot.slot_path)
                # We don't care if it's clean or not, just that the command works
            except (GitOperationError, Exception):
                return False
            
            return True
            
        except Exception:
            return False
    
    def repair_slot(self, slot: Slot) -> RepairResult:
        """
        Repair a corrupted slot.
        
        Attempts to repair by:
        1. Verifying integrity first
        2. If .git exists but corrupted, try git fsck and repair
        3. If repair fails, delete and re-clone repository
        
        Args:
            slot: Slot to repair
            
        Returns:
            RepairResult with repair details
            
        Requirements: 9.2
        """
        actions_taken = []
        errors = []
        
        try:
            # First verify if slot needs repair
            if self.verify_slot_integrity(slot):
                return RepairResult(
                    slot_id=slot.slot_id,
                    success=True,
                    actions_taken=["verified_integrity"],
                    errors=[]
                )
            
            actions_taken.append("integrity_check_failed")
            
            # Check if .git directory exists
            git_dir = slot.slot_path / ".git"
            if git_dir.exists():
                # Try to repair existing repository
                actions_taken.append("attempting_git_fsck")
                
                try:
                    # Run git fsck to check for corruption
                    fsck_result = self.git_ops._run_git_command(
                        ["git", "fsck", "--full"],
                        cwd=slot.slot_path,
                        retry=False
                    )
                    
                    if fsck_result.success:
                        actions_taken.append("fsck_passed")
                        
                        # Try cleanup to restore working state
                        cleanup_result = self.cleanup_before_allocation(slot)
                        if cleanup_result.success:
                            actions_taken.append("cleanup_successful")
                            
                            # Verify again
                            if self.verify_slot_integrity(slot):
                                slot.state = SlotState.AVAILABLE
                                return RepairResult(
                                    slot_id=slot.slot_id,
                                    success=True,
                                    actions_taken=actions_taken,
                                    errors=errors
                                )
                        else:
                            errors.extend(cleanup_result.errors)
                    else:
                        errors.append(f"fsck failed: {fsck_result.stderr}")
                        
                except Exception as e:
                    errors.append(f"fsck error: {str(e)}")
            
            # If we reach here, need to re-clone
            actions_taken.append("attempting_reclone")
            
            # Delete existing directory
            try:
                import shutil
                if slot.slot_path.exists():
                    shutil.rmtree(slot.slot_path)
                    actions_taken.append("deleted_corrupted_directory")
            except Exception as e:
                errors.append(f"Failed to delete directory: {str(e)}")
                slot.state = SlotState.ERROR
                return RepairResult(
                    slot_id=slot.slot_id,
                    success=False,
                    actions_taken=actions_taken,
                    errors=errors
                )
            
            # Re-clone repository
            try:
                clone_result = self.git_ops.clone_repo(slot.repo_url, slot.slot_path)
                if clone_result.success:
                    actions_taken.append("recloned_repository")
                    
                    # Update slot information
                    slot.current_branch = self.git_ops.get_current_branch(slot.slot_path)
                    slot.current_commit = self.git_ops.get_current_commit(slot.slot_path)
                    slot.state = SlotState.AVAILABLE
                    slot.updated_at = datetime.now()
                    
                    # Verify the repair
                    if self.verify_slot_integrity(slot):
                        return RepairResult(
                            slot_id=slot.slot_id,
                            success=True,
                            actions_taken=actions_taken,
                            errors=errors
                        )
                    else:
                        errors.append("Verification failed after re-clone")
                else:
                    errors.append(f"Clone failed: {clone_result.stderr}")
                    
            except Exception as e:
                errors.append(f"Re-clone error: {str(e)}")
            
            # If we reach here, repair failed
            slot.state = SlotState.ERROR
            return RepairResult(
                slot_id=slot.slot_id,
                success=False,
                actions_taken=actions_taken,
                errors=errors
            )
            
        except Exception as e:
            slot.state = SlotState.ERROR
            return RepairResult(
                slot_id=slot.slot_id,
                success=False,
                actions_taken=actions_taken,
                errors=errors + [f"Unexpected error: {str(e)}"]
            )
    
    def warmup_slot(self, slot: Slot) -> CleanupResult:
        """
        Pre-warmup a slot for faster allocation.
        
        Performs:
        1. git fetch --all (ensure latest remote state)
        2. Verify integrity
        3. Update slot metadata
        
        This prepares the slot for quick allocation without full cleanup overhead.
        
        Args:
            slot: Slot to warmup
            
        Returns:
            CleanupResult with warmup details
            
        Requirements: 3.5, 10.3
        """
        start_time = time.time()
        operations = []
        errors = []
        
        try:
            # Only warmup available slots
            if slot.state != SlotState.AVAILABLE:
                return CleanupResult(
                    slot_id=slot.slot_id,
                    success=False,
                    duration_seconds=0.0,
                    operations=[],
                    errors=[f"Slot not available for warmup (state: {slot.state.value})"]
                )
            
            # Fetch latest remote state
            try:
                fetch_result = self.git_ops.fetch_all(slot.slot_path)
                operations.append("fetch")
                if not fetch_result.success:
                    errors.append(f"Fetch failed: {fetch_result.stderr}")
            except Exception as e:
                errors.append(f"Fetch error: {str(e)}")
            
            # Verify integrity
            try:
                is_valid = self.verify_slot_integrity(slot)
                operations.append("verify_integrity")
                if not is_valid:
                    errors.append("Integrity verification failed")
            except Exception as e:
                errors.append(f"Verification error: {str(e)}")
            
            # Update slot git information
            try:
                slot.current_branch = self.git_ops.get_current_branch(slot.slot_path)
                slot.current_commit = self.git_ops.get_current_commit(slot.slot_path)
                slot.updated_at = datetime.now()
                operations.append("update_metadata")
            except Exception as e:
                errors.append(f"Failed to update git info: {str(e)}")
            
            duration = time.time() - start_time
            success = len(errors) == 0
            
            result = CleanupResult(
                slot_id=slot.slot_id,
                success=success,
                duration_seconds=duration,
                operations=operations,
                errors=errors
            )
            
            # Log the warmup
            self._log_cleanup(
                slot.slot_id,
                "warmup",
                success,
                duration,
                operations,
                errors
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            result = CleanupResult(
                slot_id=slot.slot_id,
                success=False,
                duration_seconds=duration,
                operations=operations,
                errors=errors + [f"Unexpected error: {str(e)}"]
            )
            
            self._log_cleanup(
                slot.slot_id,
                "warmup",
                False,
                duration,
                operations,
                errors + [str(e)]
            )
            
            return result
    
    def get_cleanup_log(self, slot_id: Optional[str] = None) -> List[CleanupRecord]:
        """
        Get cleanup log entries.
        
        Args:
            slot_id: Optional slot ID to filter logs (returns all if None)
            
        Returns:
            List of CleanupRecord entries
            
        Requirements: 10.3
        """
        if slot_id is None:
            return self.cleanup_log.copy()
        
        return [
            record for record in self.cleanup_log
            if record.slot_id == slot_id
        ]
    
    # ===== Parallel Cleanup Operations (Task 10.1) =====
    
    def cleanup_slots_parallel(
        self,
        slots: List[Slot],
        operation: str = "before_allocation",
        max_workers: Optional[int] = None
    ) -> Dict[str, CleanupResult]:
        """
        Cleanup multiple slots in parallel.
        
        This method uses ThreadPoolExecutor to run cleanup operations
        concurrently, significantly reducing total cleanup time when
        working with multiple slots.
        
        Args:
            slots: List of slots to cleanup
            operation: Type of cleanup ("before_allocation", "after_release", or "warmup")
            max_workers: Maximum number of parallel workers (default: min(16, len(slots)))
            
        Returns:
            Dictionary mapping slot_id to CleanupResult
            
        Requirements: 10.1
        """
        if not slots:
            return {}
        
        # Default to reasonable number of workers
        if max_workers is None:
            max_workers = min(16, len(slots))
        
        # Select cleanup method based on operation type
        if operation == "before_allocation":
            cleanup_method = self.cleanup_before_allocation
        elif operation == "after_release":
            cleanup_method = self.cleanup_after_release
        elif operation == "warmup":
            cleanup_method = self.warmup_slot
        else:
            raise ValueError(f"Invalid operation type: {operation}")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all cleanup tasks
            future_to_slot = {
                executor.submit(cleanup_method, slot): slot
                for slot in slots
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_slot):
                slot = future_to_slot[future]
                try:
                    result = future.result()
                    results[slot.slot_id] = result
                except Exception as e:
                    # Create error result for failed cleanup
                    results[slot.slot_id] = CleanupResult(
                        slot_id=slot.slot_id,
                        success=False,
                        duration_seconds=0.0,
                        operations=[],
                        errors=[f"Parallel cleanup error: {str(e)}"]
                    )
        
        return results
    
    def warmup_slots_parallel(
        self,
        slots: List[Slot],
        max_workers: Optional[int] = None
    ) -> Dict[str, CleanupResult]:
        """
        Warmup multiple slots in parallel.
        
        Convenience method for parallel warmup operations.
        
        Args:
            slots: List of slots to warmup
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary mapping slot_id to CleanupResult
            
        Requirements: 10.1
        """
        return self.cleanup_slots_parallel(slots, operation="warmup", max_workers=max_workers)
    
    # ===== Background Cleanup Operations (Task 10.2) =====
    
    def _ensure_background_executor(self) -> None:
        """Ensure background executor is initialized."""
        with self._background_lock:
            if self._background_executor is None:
                self._background_executor = ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix="background_cleanup"
                )
    
    def cleanup_background(
        self,
        slot: Slot,
        operation: str = "after_release",
        callback: Optional[Callable[[CleanupResult], None]] = None
    ) -> str:
        """
        Start cleanup operation in background.
        
        This method submits a cleanup operation to a background thread pool
        and returns immediately. The cleanup runs asynchronously without
        blocking the caller.
        
        Args:
            slot: Slot to cleanup
            operation: Type of cleanup ("before_allocation", "after_release", or "warmup")
            callback: Optional callback function to call when cleanup completes
            
        Returns:
            Task ID for tracking the background operation
            
        Requirements: 10.4
        """
        self._ensure_background_executor()
        
        # Select cleanup method
        if operation == "before_allocation":
            cleanup_method = self.cleanup_before_allocation
        elif operation == "after_release":
            cleanup_method = self.cleanup_after_release
        elif operation == "warmup":
            cleanup_method = self.warmup_slot
        else:
            raise ValueError(f"Invalid operation type: {operation}")
        
        # Generate task ID
        task_id = f"{slot.slot_id}_{operation}_{time.time()}"
        
        # Define wrapper function that handles callback
        def cleanup_with_callback():
            try:
                result = cleanup_method(slot)
                if callback:
                    callback(result)
                return result
            except Exception as e:
                logger.error(
                    f"Background cleanup failed for {slot.slot_id}: {e}"
                )
                error_result = CleanupResult(
                    slot_id=slot.slot_id,
                    success=False,
                    duration_seconds=0.0,
                    operations=[],
                    errors=[f"Background cleanup error: {str(e)}"]
                )
                if callback:
                    callback(error_result)
                return error_result
        
        # Submit to background executor
        with self._background_lock:
            future = self._background_executor.submit(cleanup_with_callback)
            self._background_futures[task_id] = future
        
        logger.info(
            f"Started background cleanup for {slot.slot_id} "
            f"(task_id: {task_id}, operation: {operation})"
        )
        
        return task_id
    
    def is_background_cleanup_complete(self, task_id: str) -> bool:
        """
        Check if a background cleanup task is complete.
        
        Args:
            task_id: Task ID returned by cleanup_background()
            
        Returns:
            True if task is complete, False if still running
            
        Requirements: 10.4
        """
        with self._background_lock:
            future = self._background_futures.get(task_id)
            if future is None:
                return True  # Task not found, consider it complete
            return future.done()
    
    def get_background_cleanup_result(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[CleanupResult]:
        """
        Get result of a background cleanup task.
        
        This method blocks until the task completes or timeout is reached.
        
        Args:
            task_id: Task ID returned by cleanup_background()
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            CleanupResult if task completed, None if timeout or task not found
            
        Requirements: 10.4
        """
        with self._background_lock:
            future = self._background_futures.get(task_id)
            if future is None:
                logger.warning(f"Background task not found: {task_id}")
                return None
        
        try:
            result = future.result(timeout=timeout)
            
            # Clean up completed future
            with self._background_lock:
                self._background_futures.pop(task_id, None)
            
            return result
        except TimeoutError:
            logger.warning(
                f"Timeout waiting for background cleanup result: {task_id}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error getting background cleanup result for {task_id}: {e}"
            )
            
            # Clean up failed future
            with self._background_lock:
                self._background_futures.pop(task_id, None)
            
            return None
    
    def cancel_background_cleanup(self, task_id: str) -> bool:
        """
        Attempt to cancel a background cleanup task.
        
        Args:
            task_id: Task ID returned by cleanup_background()
            
        Returns:
            True if task was cancelled, False otherwise
            
        Requirements: 10.4
        """
        with self._background_lock:
            future = self._background_futures.get(task_id)
            if future is None:
                return False
            
            cancelled = future.cancel()
            
            if cancelled:
                self._background_futures.pop(task_id, None)
                logger.info(f"Cancelled background cleanup task: {task_id}")
            
            return cancelled
    
    def get_active_background_tasks(self) -> List[str]:
        """
        Get list of active background cleanup task IDs.
        
        Returns:
            List of task IDs for running background cleanups
            
        Requirements: 10.4
        """
        with self._background_lock:
            return [
                task_id for task_id, future in self._background_futures.items()
                if not future.done()
            ]
    
    def wait_for_all_background_cleanups(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all background cleanup tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            True if all tasks completed, False if timeout
            
        Requirements: 10.4
        """
        with self._background_lock:
            futures = list(self._background_futures.values())
        
        if not futures:
            return True
        
        try:
            # Wait for all futures to complete
            for future in futures:
                future.result(timeout=timeout)
            
            # Clean up completed futures
            with self._background_lock:
                self._background_futures.clear()
            
            logger.info("All background cleanup tasks completed")
            return True
            
        except TimeoutError:
            logger.warning("Timeout waiting for background cleanups to complete")
            return False
    
    def shutdown_background_executor(self, wait: bool = True) -> None:
        """
        Shutdown the background cleanup executor.
        
        Args:
            wait: If True, wait for all tasks to complete before shutdown
            
        Requirements: 10.4
        """
        with self._background_lock:
            if self._background_executor is not None:
                logger.info("Shutting down background cleanup executor")
                self._background_executor.shutdown(wait=wait)
                self._background_executor = None
                self._background_futures.clear()

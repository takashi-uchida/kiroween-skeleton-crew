"""
Event Recorder for Dispatcher.

Handles recording of dispatcher events to Task Registry with fallback to local logging.
Implements requirements 10.1, 10.2, 10.3, 10.4, 10.5.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import TaskEvent, EventType
from necrocode.task_registry.exceptions import TaskRegistryError


logger = logging.getLogger(__name__)


class EventRecorder:
    """
    Records dispatcher events to Task Registry.
    
    Handles event recording with automatic fallback to local logging
    when Task Registry is unavailable.
    
    Requirements: 10.1, 10.2, 10.5
    """
    
    def __init__(
        self,
        task_registry: TaskRegistry,
        fallback_log_dir: Optional[Path] = None
    ):
        """
        Initialize EventRecorder.
        
        Args:
            task_registry: Task Registry instance for event recording
            fallback_log_dir: Directory for fallback logging (defaults to ./dispatcher_events)
            
        Requirements: 10.1
        """
        self.task_registry = task_registry
        self.fallback_log_dir = fallback_log_dir or Path("./dispatcher_events")
        self.fallback_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Track event recording failures for monitoring
        self.failed_events_count = 0
        self.total_events_count = 0
    
    def record_task_assigned(
        self,
        spec_name: str,
        task_id: str,
        runner_id: str,
        slot_id: str,
        pool_name: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record TaskAssigned event.
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            runner_id: Runner ID assigned to task
            slot_id: Slot ID allocated for task
            pool_name: Agent Pool name
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if event recorded successfully, False otherwise
            
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        details = {
            "runner_id": runner_id,
            "slot_id": slot_id,
            "pool_name": pool_name,
        }
        
        return self._record_event(
            event_type=EventType.TASK_ASSIGNED,
            spec_name=spec_name,
            task_id=task_id,
            details=details,
            timestamp=timestamp
        )
    
    def record_runner_started(
        self,
        spec_name: str,
        task_id: str,
        runner_id: str,
        slot_id: str,
        pool_name: str,
        pid: Optional[int] = None,
        container_id: Optional[str] = None,
        job_name: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record RunnerStarted event.
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            runner_id: Runner ID
            slot_id: Slot ID
            pool_name: Agent Pool name
            pid: Process ID (for local process)
            container_id: Container ID (for Docker)
            job_name: Job name (for Kubernetes)
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if event recorded successfully, False otherwise
            
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        details = {
            "runner_id": runner_id,
            "slot_id": slot_id,
            "pool_name": pool_name,
        }
        
        # Add execution environment details
        if pid is not None:
            details["pid"] = pid
        if container_id:
            details["container_id"] = container_id
        if job_name:
            details["job_name"] = job_name
        
        return self._record_event(
            event_type=EventType.RUNNER_STARTED,
            spec_name=spec_name,
            task_id=task_id,
            details=details,
            timestamp=timestamp
        )
    
    def record_runner_finished(
        self,
        spec_name: str,
        task_id: str,
        runner_id: str,
        slot_id: str,
        success: bool,
        execution_time_seconds: Optional[float] = None,
        failure_reason: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record RunnerFinished event.
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            runner_id: Runner ID
            slot_id: Slot ID
            success: Whether runner completed successfully
            execution_time_seconds: Total execution time in seconds
            failure_reason: Reason for failure (if applicable)
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if event recorded successfully, False otherwise
            
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        details = {
            "runner_id": runner_id,
            "slot_id": slot_id,
            "success": success,
        }
        
        # Add execution time if available
        if execution_time_seconds is not None:
            details["execution_time_seconds"] = execution_time_seconds
        
        # Add failure reason if applicable
        if not success and failure_reason:
            details["failure_reason"] = failure_reason
        
        return self._record_event(
            event_type=EventType.RUNNER_FINISHED,
            spec_name=spec_name,
            task_id=task_id,
            details=details,
            timestamp=timestamp
        )
    
    def record_task_completed(
        self,
        spec_name: str,
        task_id: str,
        runner_id: str,
        execution_time_seconds: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record TaskCompleted event.
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            runner_id: Runner ID that completed the task
            execution_time_seconds: Total execution time in seconds
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if event recorded successfully, False otherwise
            
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        details = {
            "runner_id": runner_id,
        }
        
        if execution_time_seconds is not None:
            details["execution_time_seconds"] = execution_time_seconds
        
        return self._record_event(
            event_type=EventType.TASK_COMPLETED,
            spec_name=spec_name,
            task_id=task_id,
            details=details,
            timestamp=timestamp
        )
    
    def record_task_failed(
        self,
        spec_name: str,
        task_id: str,
        runner_id: Optional[str],
        failure_reason: str,
        retry_count: int = 0,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record TaskFailed event.
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            runner_id: Runner ID (if applicable)
            failure_reason: Reason for failure
            retry_count: Number of retry attempts
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if event recorded successfully, False otherwise
            
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        details = {
            "failure_reason": failure_reason,
            "retry_count": retry_count,
        }
        
        if runner_id:
            details["runner_id"] = runner_id
        
        return self._record_event(
            event_type=EventType.TASK_FAILED,
            spec_name=spec_name,
            task_id=task_id,
            details=details,
            timestamp=timestamp
        )
    
    def _record_event(
        self,
        event_type: EventType,
        spec_name: str,
        task_id: str,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record an event to Task Registry with fallback to local logging.
        
        Args:
            event_type: Type of event
            spec_name: Spec name
            task_id: Task ID
            details: Event details
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if event recorded successfully, False otherwise
            
        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
        """
        self.total_events_count += 1
        
        # Create event
        event = TaskEvent(
            event_type=event_type,
            spec_name=spec_name,
            task_id=task_id,
            timestamp=timestamp or datetime.now(),
            details=details
        )
        
        try:
            # Try to record to Task Registry
            self.task_registry.event_store.record_event(event)
            
            logger.debug(
                f"Recorded {event_type.value} event for task {task_id} "
                f"(spec={spec_name})"
            )
            
            return True
            
        except (TaskRegistryError, Exception) as e:
            # Task Registry recording failed - fallback to local logging
            self.failed_events_count += 1
            
            logger.error(
                f"Failed to record {event_type.value} event to Task Registry: {e}"
            )
            
            # Write to fallback log
            self._write_fallback_log(event)
            
            return False
    
    def _write_fallback_log(self, event: TaskEvent) -> None:
        """
        Write event to fallback log file.
        
        Creates a local log file when Task Registry is unavailable.
        
        Args:
            event: Event to log
            
        Requirements: 10.5
        """
        try:
            # Create spec-specific fallback log file
            fallback_file = self.fallback_log_dir / f"{event.spec_name}_events.jsonl"
            
            # Append event in JSON Lines format
            with open(fallback_file, 'a', encoding='utf-8') as f:
                f.write(event.to_jsonl() + '\n')
            
            logger.warning(
                f"Event written to fallback log: {fallback_file} "
                f"(type={event.event_type.value}, task={event.task_id})"
            )
            
        except Exception as e:
            # Even fallback logging failed - just log to application logger
            logger.error(
                f"Failed to write fallback log for {event.event_type.value} event: {e}"
            )
            logger.error(f"Event details: {event.to_dict()}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get event recording statistics.
        
        Returns:
            Dictionary with statistics
        """
        success_rate = 0.0
        if self.total_events_count > 0:
            success_rate = (
                (self.total_events_count - self.failed_events_count) 
                / self.total_events_count
            ) * 100
        
        return {
            "total_events": self.total_events_count,
            "failed_events": self.failed_events_count,
            "success_rate": success_rate,
        }

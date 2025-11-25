"""
Resource monitoring and timeout management for Agent Runner.

This module provides functionality for:
- Task execution timeout management
- Memory usage monitoring
- CPU usage monitoring
- Resource limit enforcement

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

import logging
import os
import signal
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from necrocode.agent_runner.exceptions import ResourceLimitError, TimeoutError

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """
    Snapshot of resource usage at a point in time.
    
    Attributes:
        timestamp: When the measurement was taken
        memory_mb: Memory usage in megabytes
        memory_percent: Memory usage as percentage of system memory
        cpu_percent: CPU usage percentage
        process_id: Process ID being monitored
    """
    timestamp: datetime
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    process_id: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "cpu_percent": self.cpu_percent,
            "process_id": self.process_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ResourceUsage":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            memory_mb=data["memory_mb"],
            memory_percent=data["memory_percent"],
            cpu_percent=data["cpu_percent"],
            process_id=data["process_id"],
        )


class TimeoutManager:
    """
    Manages task execution timeouts.
    
    Provides functionality to:
    - Set execution timeout
    - Monitor elapsed time
    - Interrupt execution when timeout is reached
    - Handle timeout gracefully
    
    Requirements: 11.1, 11.2
    """
    
    def __init__(self, timeout_seconds: int):
        """
        Initialize TimeoutManager.
        
        Args:
            timeout_seconds: Maximum execution time in seconds
            
        Raises:
            ValueError: If timeout_seconds is not positive
        """
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        
        self.timeout_seconds = timeout_seconds
        self.start_time: Optional[float] = None
        self.timer: Optional[threading.Timer] = None
        self.timed_out = False
        self.callback: Optional[Callable] = None
        
        logger.info(f"TimeoutManager initialized with {timeout_seconds}s timeout")
    
    def start(self, callback: Optional[Callable] = None) -> None:
        """
        Start the timeout timer.
        
        Args:
            callback: Optional callback to invoke when timeout occurs
            
        Requirements: 11.1
        """
        self.start_time = time.time()
        self.timed_out = False
        self.callback = callback
        
        # Create timer that will fire when timeout is reached
        self.timer = threading.Timer(self.timeout_seconds, self._on_timeout)
        self.timer.daemon = True
        self.timer.start()
        
        logger.info(f"Timeout timer started: {self.timeout_seconds}s")
    
    def stop(self) -> None:
        """
        Stop the timeout timer.
        
        Should be called when task completes successfully before timeout.
        """
        if self.timer:
            self.timer.cancel()
            self.timer = None
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info(f"Timeout timer stopped after {elapsed:.2f}s")
    
    def _on_timeout(self) -> None:
        """
        Internal callback when timeout is reached.
        
        Marks the execution as timed out and invokes the user callback
        if provided.
        
        Requirements: 11.2
        """
        self.timed_out = True
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        logger.error(
            f"Task execution timeout reached: {elapsed:.2f}s / {self.timeout_seconds}s"
        )
        
        # Invoke user callback if provided
        if self.callback:
            try:
                self.callback()
            except Exception as e:
                logger.error(f"Timeout callback failed: {e}")
    
    def check_timeout(self) -> None:
        """
        Check if timeout has been reached.
        
        Raises:
            TimeoutError: If timeout has been reached
            
        Requirements: 11.2
        """
        if self.timed_out:
            elapsed = time.time() - self.start_time if self.start_time else 0
            raise TimeoutError(
                f"Task execution timeout: {elapsed:.2f}s exceeded limit of "
                f"{self.timeout_seconds}s"
            )
    
    def get_elapsed_seconds(self) -> float:
        """
        Get elapsed time since timer started.
        
        Returns:
            Elapsed time in seconds, or 0 if timer not started
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def get_remaining_seconds(self) -> float:
        """
        Get remaining time before timeout.
        
        Returns:
            Remaining time in seconds, or 0 if timed out
        """
        if self.timed_out:
            return 0.0
        
        elapsed = self.get_elapsed_seconds()
        remaining = self.timeout_seconds - elapsed
        return max(0.0, remaining)


class ResourceMonitor:
    """
    Monitors system resource usage (memory, CPU).
    
    Provides functionality to:
    - Monitor memory usage
    - Monitor CPU usage
    - Enforce resource limits
    - Record resource usage history
    
    Requirements: 11.3, 11.4, 11.5
    """
    
    def __init__(
        self,
        max_memory_mb: Optional[int] = None,
        max_cpu_percent: Optional[int] = None,
        monitoring_interval: float = 1.0,
        process_id: Optional[int] = None
    ):
        """
        Initialize ResourceMonitor.
        
        Args:
            max_memory_mb: Maximum memory usage in MB (None = no limit)
            max_cpu_percent: Maximum CPU usage percentage (None = no limit)
            monitoring_interval: How often to check resources (seconds)
            process_id: Process ID to monitor (None = current process)
            
        Raises:
            ImportError: If psutil is not available
            ValueError: If limits are invalid
        """
        if not PSUTIL_AVAILABLE:
            raise ImportError(
                "psutil is required for resource monitoring. "
                "Install it with: pip install psutil"
            )
        
        if max_memory_mb is not None and max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        
        if max_cpu_percent is not None and (max_cpu_percent <= 0 or max_cpu_percent > 100):
            raise ValueError("max_cpu_percent must be between 1 and 100")
        
        if monitoring_interval <= 0:
            raise ValueError("monitoring_interval must be positive")
        
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.monitoring_interval = monitoring_interval
        
        # Get process to monitor
        self.process_id = process_id or os.getpid()
        try:
            self.process = psutil.Process(self.process_id)
        except psutil.NoSuchProcess:
            raise ValueError(f"Process {self.process_id} does not exist")
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.usage_history: list[ResourceUsage] = []
        self.limit_exceeded = False
        self.limit_exceeded_reason: Optional[str] = None
        
        logger.info(
            f"ResourceMonitor initialized for PID {self.process_id}: "
            f"max_memory={max_memory_mb}MB, max_cpu={max_cpu_percent}%"
        )
    
    def start(self) -> None:
        """
        Start resource monitoring in background thread.
        
        Requirements: 11.3, 11.4
        """
        if self.monitoring:
            logger.warning("Resource monitoring already started")
            return
        
        self.monitoring = True
        self.limit_exceeded = False
        self.limit_exceeded_reason = None
        self.usage_history.clear()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info("Resource monitoring started")
    
    def stop(self) -> None:
        """
        Stop resource monitoring.
        """
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        # Wait for monitor thread to finish
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
            self.monitor_thread = None
        
        logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop that runs in background thread.
        
        Periodically checks resource usage and enforces limits.
        
        Requirements: 11.3, 11.4, 11.5
        """
        logger.debug("Resource monitoring loop started")
        
        while self.monitoring:
            try:
                # Get current resource usage
                usage = self._get_current_usage()
                
                # Record in history
                self.usage_history.append(usage)
                
                # Check limits
                self._check_limits(usage)
                
                # Sleep until next check
                time.sleep(self.monitoring_interval)
                
            except psutil.NoSuchProcess:
                logger.warning(f"Process {self.process_id} no longer exists")
                self.monitoring = False
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                # Continue monitoring despite errors
        
        logger.debug("Resource monitoring loop stopped")
    
    def _get_current_usage(self) -> ResourceUsage:
        """
        Get current resource usage snapshot.
        
        Returns:
            ResourceUsage snapshot
            
        Requirements: 11.3, 11.4
        """
        # Get memory info
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
        memory_percent = self.process.memory_percent()
        
        # Get CPU usage (averaged over monitoring interval)
        cpu_percent = self.process.cpu_percent(interval=None)
        
        return ResourceUsage(
            timestamp=datetime.now(),
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            cpu_percent=cpu_percent,
            process_id=self.process_id,
        )
    
    def _check_limits(self, usage: ResourceUsage) -> None:
        """
        Check if resource usage exceeds configured limits.
        
        Args:
            usage: Current resource usage
            
        Requirements: 11.5
        """
        # Check memory limit
        if self.max_memory_mb is not None and usage.memory_mb > self.max_memory_mb:
            self.limit_exceeded = True
            self.limit_exceeded_reason = (
                f"Memory limit exceeded: {usage.memory_mb:.1f}MB > "
                f"{self.max_memory_mb}MB"
            )
            logger.warning(self.limit_exceeded_reason)
        
        # Check CPU limit
        if self.max_cpu_percent is not None and usage.cpu_percent > self.max_cpu_percent:
            self.limit_exceeded = True
            self.limit_exceeded_reason = (
                f"CPU limit exceeded: {usage.cpu_percent:.1f}% > "
                f"{self.max_cpu_percent}%"
            )
            logger.warning(self.limit_exceeded_reason)
    
    def check_limits(self) -> None:
        """
        Check if resource limits have been exceeded.
        
        Raises:
            ResourceLimitError: If resource limits have been exceeded
            
        Requirements: 11.5
        """
        if self.limit_exceeded:
            raise ResourceLimitError(self.limit_exceeded_reason or "Resource limit exceeded")
    
    def get_current_usage(self) -> Optional[ResourceUsage]:
        """
        Get the most recent resource usage measurement.
        
        Returns:
            Most recent ResourceUsage, or None if no measurements yet
        """
        if not self.usage_history:
            return None
        return self.usage_history[-1]
    
    def get_peak_usage(self) -> Optional[ResourceUsage]:
        """
        Get the peak resource usage (highest memory).
        
        Returns:
            ResourceUsage with highest memory usage, or None if no measurements
        """
        if not self.usage_history:
            return None
        return max(self.usage_history, key=lambda u: u.memory_mb)
    
    def get_average_usage(self) -> Optional[dict]:
        """
        Get average resource usage across all measurements.
        
        Returns:
            Dictionary with average memory_mb and cpu_percent, or None
        """
        if not self.usage_history:
            return None
        
        avg_memory = sum(u.memory_mb for u in self.usage_history) / len(self.usage_history)
        avg_cpu = sum(u.cpu_percent for u in self.usage_history) / len(self.usage_history)
        
        return {
            "memory_mb": avg_memory,
            "cpu_percent": avg_cpu,
            "sample_count": len(self.usage_history),
        }
    
    def get_usage_summary(self) -> dict:
        """
        Get comprehensive summary of resource usage.
        
        Returns:
            Dictionary with current, peak, and average usage statistics
        """
        current = self.get_current_usage()
        peak = self.get_peak_usage()
        average = self.get_average_usage()
        
        return {
            "current": current.to_dict() if current else None,
            "peak": peak.to_dict() if peak else None,
            "average": average,
            "limit_exceeded": self.limit_exceeded,
            "limit_exceeded_reason": self.limit_exceeded_reason,
            "sample_count": len(self.usage_history),
        }


class ExecutionMonitor:
    """
    Combined timeout and resource monitoring for task execution.
    
    Provides unified interface for:
    - Timeout management
    - Resource monitoring
    - Limit enforcement
    
    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """
    
    def __init__(
        self,
        timeout_seconds: int,
        max_memory_mb: Optional[int] = None,
        max_cpu_percent: Optional[int] = None,
        monitoring_interval: float = 1.0,
    ):
        """
        Initialize ExecutionMonitor.
        
        Args:
            timeout_seconds: Maximum execution time
            max_memory_mb: Maximum memory usage (None = no limit)
            max_cpu_percent: Maximum CPU usage (None = no limit)
            monitoring_interval: Resource monitoring interval
        """
        self.timeout_manager = TimeoutManager(timeout_seconds)
        
        # Only create resource monitor if psutil is available and limits are set
        self.resource_monitor: Optional[ResourceMonitor] = None
        if PSUTIL_AVAILABLE and (max_memory_mb is not None or max_cpu_percent is not None):
            self.resource_monitor = ResourceMonitor(
                max_memory_mb=max_memory_mb,
                max_cpu_percent=max_cpu_percent,
                monitoring_interval=monitoring_interval,
            )
        elif not PSUTIL_AVAILABLE and (max_memory_mb is not None or max_cpu_percent is not None):
            logger.warning(
                "Resource limits configured but psutil not available. "
                "Resource monitoring disabled."
            )
    
    def start(self) -> None:
        """
        Start timeout and resource monitoring.
        
        Requirements: 11.1, 11.3, 11.4
        """
        self.timeout_manager.start()
        
        if self.resource_monitor:
            self.resource_monitor.start()
    
    def stop(self) -> None:
        """
        Stop timeout and resource monitoring.
        """
        self.timeout_manager.stop()
        
        if self.resource_monitor:
            self.resource_monitor.stop()
    
    def check(self) -> None:
        """
        Check timeout and resource limits.
        
        Raises:
            TimeoutError: If timeout exceeded
            ResourceLimitError: If resource limits exceeded
            
        Requirements: 11.2, 11.5
        """
        # Check timeout first (higher priority)
        self.timeout_manager.check_timeout()
        
        # Check resource limits
        if self.resource_monitor:
            self.resource_monitor.check_limits()
    
    def get_status(self) -> dict:
        """
        Get current monitoring status.
        
        Returns:
            Dictionary with timeout and resource usage information
        """
        status = {
            "elapsed_seconds": self.timeout_manager.get_elapsed_seconds(),
            "remaining_seconds": self.timeout_manager.get_remaining_seconds(),
            "timed_out": self.timeout_manager.timed_out,
        }
        
        if self.resource_monitor:
            status["resource_usage"] = self.resource_monitor.get_usage_summary()
        
        return status

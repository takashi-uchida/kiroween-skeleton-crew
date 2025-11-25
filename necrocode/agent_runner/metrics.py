"""
Execution metrics collection and reporting for Agent Runner.

This module provides functionality to collect and report execution metrics
including execution time, memory usage, CPU usage, and other performance data.

Requirements: 12.3
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ExecutionMetrics:
    """
    Metrics collected during task execution.
    
    Contains timing, resource usage, and other performance metrics
    for a single task execution.
    
    Requirements: 12.3
    """
    runner_id: str
    task_id: str
    spec_name: str
    
    # Timing metrics
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Phase timings
    phase_timings: Dict[str, float] = field(default_factory=dict)
    
    # Resource usage metrics
    peak_memory_mb: float = 0.0
    peak_memory_percent: float = 0.0
    peak_cpu_percent: float = 0.0
    average_memory_mb: float = 0.0
    average_cpu_percent: float = 0.0
    
    # Execution metrics
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    
    # Artifact metrics
    artifacts_uploaded: int = 0
    total_artifact_size_bytes: int = 0
    
    # Error metrics
    errors_encountered: int = 0
    retries_attempted: int = 0
    
    # Parallel execution metrics
    concurrent_runners: int = 1  # Number of concurrent runners
    wait_time_seconds: float = 0.0  # Time spent waiting for resources
    resource_conflicts_detected: int = 0  # Number of resource conflicts
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "runner_id": self.runner_id,
            "task_id": self.task_id,
            "spec_name": self.spec_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "phase_timings": self.phase_timings,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_memory_percent": self.peak_memory_percent,
            "peak_cpu_percent": self.peak_cpu_percent,
            "average_memory_mb": self.average_memory_mb,
            "average_cpu_percent": self.average_cpu_percent,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "artifacts_uploaded": self.artifacts_uploaded,
            "total_artifact_size_bytes": self.total_artifact_size_bytes,
            "errors_encountered": self.errors_encountered,
            "retries_attempted": self.retries_attempted,
            "concurrent_runners": self.concurrent_runners,
            "wait_time_seconds": self.wait_time_seconds,
            "resource_conflicts_detected": self.resource_conflicts_detected,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionMetrics":
        """Create from dictionary."""
        data = data.copy()
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        return cls(**data)


class MetricsCollector:
    """
    Collects execution metrics during task execution.
    
    Tracks timing, resource usage, and other metrics throughout
    the task execution lifecycle.
    
    Requirements: 12.3
    """
    
    def __init__(
        self,
        runner_id: str,
        task_id: str,
        spec_name: str
    ):
        """
        Initialize metrics collector.
        
        Args:
            runner_id: Runner ID
            task_id: Task ID
            spec_name: Spec name
        """
        self.metrics = ExecutionMetrics(
            runner_id=runner_id,
            task_id=task_id,
            spec_name=spec_name,
            start_time=datetime.now()
        )
        
        # Phase timing tracking
        self._phase_start_times: Dict[str, float] = {}
        
        # Resource usage samples
        self._memory_samples: List[float] = []
        self._cpu_samples: List[float] = []
        
        # Process handle for resource monitoring
        self._process: Optional[Any] = None
        if PSUTIL_AVAILABLE:
            try:
                self._process = psutil.Process()
            except Exception:
                self._process = None
    
    def start_phase(self, phase_name: str) -> None:
        """
        Start timing a phase.
        
        Args:
            phase_name: Name of the phase (e.g., "workspace_preparation")
        """
        self._phase_start_times[phase_name] = time.time()
    
    def end_phase(self, phase_name: str) -> None:
        """
        End timing a phase.
        
        Args:
            phase_name: Name of the phase
        """
        if phase_name in self._phase_start_times:
            start_time = self._phase_start_times[phase_name]
            duration = time.time() - start_time
            self.metrics.phase_timings[phase_name] = duration
            del self._phase_start_times[phase_name]
    
    def sample_resources(self) -> None:
        """
        Sample current resource usage.
        
        Collects current memory and CPU usage and updates peak values.
        """
        if not self._process or not PSUTIL_AVAILABLE:
            return
        
        try:
            # Get memory info
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = self._process.memory_percent()
            
            # Get CPU percent
            cpu_percent = self._process.cpu_percent(interval=0.1)
            
            # Update samples
            self._memory_samples.append(memory_mb)
            self._cpu_samples.append(cpu_percent)
            
            # Update peak values
            if memory_mb > self.metrics.peak_memory_mb:
                self.metrics.peak_memory_mb = memory_mb
            if memory_percent > self.metrics.peak_memory_percent:
                self.metrics.peak_memory_percent = memory_percent
            if cpu_percent > self.metrics.peak_cpu_percent:
                self.metrics.peak_cpu_percent = cpu_percent
                
        except Exception:
            # Ignore errors in resource sampling
            pass
    
    def record_implementation(
        self,
        files_changed: int,
        lines_added: int = 0,
        lines_removed: int = 0
    ) -> None:
        """
        Record implementation metrics.
        
        Args:
            files_changed: Number of files changed
            lines_added: Number of lines added
            lines_removed: Number of lines removed
        """
        self.metrics.files_changed = files_changed
        self.metrics.lines_added = lines_added
        self.metrics.lines_removed = lines_removed
    
    def record_tests(
        self,
        tests_run: int,
        tests_passed: int,
        tests_failed: int
    ) -> None:
        """
        Record test execution metrics.
        
        Args:
            tests_run: Total number of tests run
            tests_passed: Number of tests passed
            tests_failed: Number of tests failed
        """
        self.metrics.tests_run = tests_run
        self.metrics.tests_passed = tests_passed
        self.metrics.tests_failed = tests_failed
    
    def record_artifacts(
        self,
        artifacts_uploaded: int,
        total_size_bytes: int
    ) -> None:
        """
        Record artifact upload metrics.
        
        Args:
            artifacts_uploaded: Number of artifacts uploaded
            total_size_bytes: Total size of artifacts in bytes
        """
        self.metrics.artifacts_uploaded = artifacts_uploaded
        self.metrics.total_artifact_size_bytes = total_size_bytes
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self.metrics.errors_encountered += 1
    
    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.metrics.retries_attempted += 1
    
    def record_concurrent_runners(self, count: int) -> None:
        """
        Record number of concurrent runners.
        
        Args:
            count: Number of concurrent runners
        """
        self.metrics.concurrent_runners = count
    
    def record_wait_time(self, seconds: float) -> None:
        """
        Record time spent waiting for resources.
        
        Args:
            seconds: Wait time in seconds
        """
        self.metrics.wait_time_seconds += seconds
    
    def record_resource_conflict(self) -> None:
        """Record a resource conflict detection."""
        self.metrics.resource_conflicts_detected += 1
    
    def finalize(self) -> ExecutionMetrics:
        """
        Finalize metrics collection.
        
        Calculates final metrics including duration and averages.
        
        Returns:
            Finalized execution metrics
        """
        # Set end time and duration
        self.metrics.end_time = datetime.now()
        self.metrics.duration_seconds = (
            self.metrics.end_time - self.metrics.start_time
        ).total_seconds()
        
        # Calculate average resource usage
        if self._memory_samples:
            self.metrics.average_memory_mb = sum(self._memory_samples) / len(self._memory_samples)
        if self._cpu_samples:
            self.metrics.average_cpu_percent = sum(self._cpu_samples) / len(self._cpu_samples)
        
        return self.metrics


class MetricsReporter:
    """
    Reports execution metrics to various outputs.
    
    Supports reporting metrics to:
    - JSON files
    - Console output
    - Metrics endpoints (future)
    
    Requirements: 12.3
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize metrics reporter.
        
        Args:
            output_dir: Directory for metrics output files
        """
        self.output_dir = output_dir
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def report(self, metrics: ExecutionMetrics) -> None:
        """
        Report metrics to all configured outputs.
        
        Args:
            metrics: Execution metrics to report
        """
        # Report to console
        self._report_console(metrics)
        
        # Report to file if output directory is configured
        if self.output_dir:
            self._report_file(metrics)
    
    def _report_console(self, metrics: ExecutionMetrics) -> None:
        """
        Report metrics to console.
        
        Args:
            metrics: Execution metrics
        """
        print("\n" + "=" * 60)
        print("EXECUTION METRICS")
        print("=" * 60)
        print(f"Runner ID: {metrics.runner_id}")
        print(f"Task ID: {metrics.task_id}")
        print(f"Spec: {metrics.spec_name}")
        print(f"Duration: {metrics.duration_seconds:.2f}s")
        print()
        
        # Phase timings
        if metrics.phase_timings:
            print("Phase Timings:")
            for phase, duration in metrics.phase_timings.items():
                print(f"  {phase}: {duration:.2f}s")
            print()
        
        # Resource usage
        print("Resource Usage:")
        print(f"  Peak Memory: {metrics.peak_memory_mb:.1f} MB ({metrics.peak_memory_percent:.1f}%)")
        print(f"  Peak CPU: {metrics.peak_cpu_percent:.1f}%")
        print(f"  Avg Memory: {metrics.average_memory_mb:.1f} MB")
        print(f"  Avg CPU: {metrics.average_cpu_percent:.1f}%")
        print()
        
        # Implementation metrics
        print("Implementation:")
        print(f"  Files Changed: {metrics.files_changed}")
        print(f"  Lines Added: {metrics.lines_added}")
        print(f"  Lines Removed: {metrics.lines_removed}")
        print()
        
        # Test metrics
        if metrics.tests_run > 0:
            print("Tests:")
            print(f"  Total: {metrics.tests_run}")
            print(f"  Passed: {metrics.tests_passed}")
            print(f"  Failed: {metrics.tests_failed}")
            print()
        
        # Artifact metrics
        if metrics.artifacts_uploaded > 0:
            print("Artifacts:")
            print(f"  Uploaded: {metrics.artifacts_uploaded}")
            print(f"  Total Size: {metrics.total_artifact_size_bytes / (1024 * 1024):.2f} MB")
            print()
        
        # Error metrics
        if metrics.errors_encountered > 0 or metrics.retries_attempted > 0:
            print("Errors & Retries:")
            print(f"  Errors: {metrics.errors_encountered}")
            print(f"  Retries: {metrics.retries_attempted}")
            print()
        
        # Parallel execution metrics
        if metrics.concurrent_runners > 1 or metrics.wait_time_seconds > 0 or metrics.resource_conflicts_detected > 0:
            print("Parallel Execution:")
            print(f"  Concurrent Runners: {metrics.concurrent_runners}")
            if metrics.wait_time_seconds > 0:
                print(f"  Wait Time: {metrics.wait_time_seconds:.2f}s")
            if metrics.resource_conflicts_detected > 0:
                print(f"  Resource Conflicts: {metrics.resource_conflicts_detected}")
            print()
        
        print("=" * 60 + "\n")
    
    def _report_file(self, metrics: ExecutionMetrics) -> None:
        """
        Report metrics to JSON file.
        
        Args:
            metrics: Execution metrics
        """
        if not self.output_dir:
            return
        
        # Generate filename with timestamp
        timestamp = metrics.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"metrics_{metrics.runner_id}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Write metrics to file
        with open(filepath, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
    
    def report_summary(self, metrics_list: List[ExecutionMetrics]) -> None:
        """
        Report summary of multiple executions.
        
        Args:
            metrics_list: List of execution metrics
        """
        if not metrics_list:
            return
        
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Executions: {len(metrics_list)}")
        print()
        
        # Calculate aggregates
        total_duration = sum(m.duration_seconds for m in metrics_list)
        avg_duration = total_duration / len(metrics_list)
        
        total_files = sum(m.files_changed for m in metrics_list)
        total_tests = sum(m.tests_run for m in metrics_list)
        total_passed = sum(m.tests_passed for m in metrics_list)
        total_failed = sum(m.tests_failed for m in metrics_list)
        
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Average Duration: {avg_duration:.2f}s")
        print(f"Total Files Changed: {total_files}")
        print(f"Total Tests Run: {total_tests}")
        print(f"Total Tests Passed: {total_passed}")
        print(f"Total Tests Failed: {total_failed}")
        print("=" * 60 + "\n")

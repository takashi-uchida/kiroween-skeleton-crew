"""
Tests for logging and monitoring functionality.

Tests structured logging, metrics collection, and health check endpoints.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import json
import logging
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from necrocode.agent_runner.health_check import (
    HealthCheckServer,
    HealthStatus,
    create_health_check_server,
)
from necrocode.agent_runner.logging_config import (
    RunnerLoggerAdapter,
    StructuredFormatter,
    get_runner_logger,
    setup_logging,
)
from necrocode.agent_runner.metrics import (
    ExecutionMetrics,
    MetricsCollector,
    MetricsReporter,
)
from necrocode.agent_runner.security import SecretMasker


class TestStructuredLogging:
    """
    Tests for structured logging functionality.
    
    Requirements: 12.1, 12.2, 12.4
    """
    
    def test_structured_formatter_basic(self):
        """Test basic JSON formatting."""
        formatter = StructuredFormatter()
        
        # Create log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format record
        formatted = formatter.format(record)
        
        # Parse JSON
        log_entry = json.loads(formatted)
        
        # Verify fields
        assert "timestamp" in log_entry
        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "test.logger"
        assert log_entry["message"] == "Test message"
    
    def test_structured_formatter_with_context(self):
        """Test JSON formatting with runner context."""
        formatter = StructuredFormatter()
        
        # Create log record with context
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.runner_id = "runner-123"
        record.task_id = "task-1.1"
        record.spec_name = "test-spec"
        
        # Format record
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        # Verify context fields
        assert log_entry["runner_id"] == "runner-123"
        assert log_entry["task_id"] == "task-1.1"
        assert log_entry["spec_name"] == "test-spec"
    
    def test_structured_formatter_with_secret_masking(self):
        """Test secret masking in structured logs."""
        secret_masker = SecretMasker()
        secret_masker.add_secret("secret-token-123")
        
        formatter = StructuredFormatter(secret_masker=secret_masker)
        
        # Create log record with secret
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Token: secret-token-123",
            args=(),
            exc_info=None
        )
        
        # Format record
        formatted = formatter.format(record)
        
        # Verify secret is masked (SecretMasker masks with pattern)
        assert "secret-token-123" not in formatted
        # The masker uses a pattern like "secr***-123" or similar
        assert "***" in formatted
    
    def test_runner_logger_adapter(self):
        """Test logger adapter with automatic context."""
        base_logger = logging.getLogger("test.logger")
        
        adapter = RunnerLoggerAdapter(
            logger=base_logger,
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Test context injection
        msg, kwargs = adapter.process("Test message", {})
        
        assert "extra" in kwargs
        assert kwargs["extra"]["runner_id"] == "runner-123"
        assert kwargs["extra"]["task_id"] == "task-1.1"
        assert kwargs["extra"]["spec_name"] == "test-spec"
    
    def test_runner_logger_adapter_update_context(self):
        """Test updating logger context."""
        base_logger = logging.getLogger("test.logger")
        
        adapter = RunnerLoggerAdapter(
            logger=base_logger,
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Update context
        adapter.update_context(task_id="task-1.2", spec_name="new-spec")
        
        # Verify updated context
        msg, kwargs = adapter.process("Test message", {})
        assert kwargs["extra"]["task_id"] == "task-1.2"
        assert kwargs["extra"]["spec_name"] == "new-spec"
    
    def test_setup_logging_structured(self):
        """Test logging setup with structured format."""
        with TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            # Setup logging
            setup_logging(
                log_level="INFO",
                structured=True,
                log_file=log_file
            )
            
            # Log a message
            logger = logging.getLogger("test.logger")
            logger.info("Test message")
            
            # Verify log file exists and contains JSON
            assert log_file.exists()
            log_content = log_file.read_text()
            
            # Should be valid JSON
            log_lines = [line for line in log_content.strip().split("\n") if line]
            for line in log_lines:
                log_entry = json.loads(line)
                assert "timestamp" in log_entry
                assert "level" in log_entry
    
    def test_get_runner_logger(self):
        """Test getting runner logger with context."""
        logger = get_runner_logger(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        assert isinstance(logger, RunnerLoggerAdapter)
        assert logger.runner_id == "runner-123"
        assert logger.task_id == "task-1.1"
        assert logger.spec_name == "test-spec"


class TestMetricsCollection:
    """
    Tests for metrics collection functionality.
    
    Requirements: 12.3
    """
    
    def test_execution_metrics_creation(self):
        """Test creating execution metrics."""
        metrics = ExecutionMetrics(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec",
            start_time=datetime.now()
        )
        
        assert metrics.runner_id == "runner-123"
        assert metrics.task_id == "task-1.1"
        assert metrics.spec_name == "test-spec"
        assert metrics.duration_seconds == 0.0
    
    def test_execution_metrics_serialization(self):
        """Test metrics serialization to dict."""
        metrics = ExecutionMetrics(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec",
            start_time=datetime.now(),
            duration_seconds=10.5,
            peak_memory_mb=256.0,
            files_changed=5
        )
        
        # Convert to dict
        data = metrics.to_dict()
        
        assert data["runner_id"] == "runner-123"
        assert data["duration_seconds"] == 10.5
        assert data["peak_memory_mb"] == 256.0
        assert data["files_changed"] == 5
        
        # Convert back from dict
        restored = ExecutionMetrics.from_dict(data)
        assert restored.runner_id == metrics.runner_id
        assert restored.duration_seconds == metrics.duration_seconds
    
    def test_metrics_collector_phase_timing(self):
        """Test phase timing collection."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Time a phase
        collector.start_phase("test_phase")
        time.sleep(0.1)
        collector.end_phase("test_phase")
        
        # Verify timing recorded
        assert "test_phase" in collector.metrics.phase_timings
        assert collector.metrics.phase_timings["test_phase"] >= 0.1
    
    def test_metrics_collector_resource_sampling(self):
        """Test resource usage sampling."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Sample resources
        collector.sample_resources()
        
        # Peak values should be set (if psutil is available)
        # Note: Values may be 0 if psutil is not available
        assert collector.metrics.peak_memory_mb >= 0
        assert collector.metrics.peak_cpu_percent >= 0
    
    def test_metrics_collector_implementation_recording(self):
        """Test recording implementation metrics."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Record implementation
        collector.record_implementation(
            files_changed=5,
            lines_added=100,
            lines_removed=20
        )
        
        assert collector.metrics.files_changed == 5
        assert collector.metrics.lines_added == 100
        assert collector.metrics.lines_removed == 20
    
    def test_metrics_collector_test_recording(self):
        """Test recording test metrics."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Record tests
        collector.record_tests(
            tests_run=10,
            tests_passed=9,
            tests_failed=1
        )
        
        assert collector.metrics.tests_run == 10
        assert collector.metrics.tests_passed == 9
        assert collector.metrics.tests_failed == 1
    
    def test_metrics_collector_artifact_recording(self):
        """Test recording artifact metrics."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Record artifacts
        collector.record_artifacts(
            artifacts_uploaded=3,
            total_size_bytes=1024 * 1024  # 1 MB
        )
        
        assert collector.metrics.artifacts_uploaded == 3
        assert collector.metrics.total_artifact_size_bytes == 1024 * 1024
    
    def test_metrics_collector_error_retry_recording(self):
        """Test recording errors and retries."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Record errors and retries
        collector.record_error()
        collector.record_error()
        collector.record_retry()
        
        assert collector.metrics.errors_encountered == 2
        assert collector.metrics.retries_attempted == 1
    
    def test_metrics_collector_finalize(self):
        """Test finalizing metrics."""
        collector = MetricsCollector(
            runner_id="runner-123",
            task_id="task-1.1",
            spec_name="test-spec"
        )
        
        # Simulate some work
        time.sleep(0.1)
        
        # Finalize
        metrics = collector.finalize()
        
        # Verify end time and duration set
        assert metrics.end_time is not None
        assert metrics.duration_seconds >= 0.1
    
    def test_metrics_reporter_file_output(self):
        """Test metrics reporting to file."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            reporter = MetricsReporter(output_dir=output_dir)
            
            # Create metrics
            metrics = ExecutionMetrics(
                runner_id="runner-123",
                task_id="task-1.1",
                spec_name="test-spec",
                start_time=datetime.now(),
                duration_seconds=10.0
            )
            
            # Report metrics
            reporter.report(metrics)
            
            # Verify file created
            json_files = list(output_dir.glob("metrics_*.json"))
            assert len(json_files) == 1
            
            # Verify content
            with open(json_files[0]) as f:
                data = json.load(f)
            
            assert data["runner_id"] == "runner-123"
            assert data["duration_seconds"] == 10.0


class TestHealthCheck:
    """
    Tests for health check functionality.
    
    Requirements: 12.5
    """
    
    def test_health_status_creation(self):
        """Test creating health status."""
        status = HealthStatus()
        
        assert status.healthy is True
        assert status.runner_state == "idle"
        assert status.runner_id is None
    
    def test_health_status_update(self):
        """Test updating health status."""
        status = HealthStatus()
        
        status.update(
            healthy=True,
            runner_state="running",
            runner_id="runner-123",
            current_task_id="task-1.1",
            current_spec_name="test-spec"
        )
        
        assert status.healthy is True
        assert status.runner_state == "running"
        assert status.runner_id == "runner-123"
        assert status.current_task_id == "task-1.1"
        assert status.current_spec_name == "test-spec"
    
    def test_health_status_to_dict(self):
        """Test health status serialization."""
        status = HealthStatus()
        status.update(
            healthy=True,
            runner_state="running",
            runner_id="runner-123"
        )
        
        data = status.to_dict()
        
        assert data["status"] == "healthy"
        assert data["runner_id"] == "runner-123"
        assert data["runner_state"] == "running"
        assert "uptime_seconds" in data
        assert "last_check" in data
    
    def test_create_health_check_server(self):
        """Test creating health check server."""
        server = create_health_check_server(
            port=8080,
            host="127.0.0.1",
            runner_id="runner-123"
        )
        
        assert isinstance(server, HealthCheckServer)
        assert server.port == 8080
        assert server.host == "127.0.0.1"
        assert server.health_status.runner_id == "runner-123"
    
    def test_health_check_server_lifecycle(self):
        """Test starting and stopping health check server."""
        import socket
        
        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            s.listen(1)
            port = s.getsockname()[1]
        
        server = create_health_check_server(
            port=port,
            host="127.0.0.1",
            runner_id="runner-123"
        )
        
        try:
            # Start server
            server.start()
            assert server.running is True
            
            # Give server time to start
            time.sleep(0.5)
        finally:
            # Stop server
            server.stop()
            assert server.running is False
    
    def test_health_check_server_update_status(self):
        """Test updating server status."""
        server = create_health_check_server(
            port=8083,
            host="127.0.0.1",
            runner_id="runner-123"
        )
        
        # Update status
        server.update_status(
            healthy=True,
            runner_state="running",
            current_task_id="task-1.1"
        )
        
        # Verify status updated
        assert server.health_status.runner_state == "running"
        assert server.health_status.current_task_id == "task-1.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

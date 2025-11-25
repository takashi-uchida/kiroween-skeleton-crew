"""
Tests for resource monitoring and timeout functionality.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 16.3
"""

import time
import pytest

from necrocode.agent_runner.resource_monitor import (
    ExecutionMonitor,
    ResourceMonitor,
    ResourceUsage,
    ServiceCallMetrics,
    ServiceCallTracker,
    TimeoutManager,
)
from necrocode.agent_runner.exceptions import ResourceLimitError, TimeoutError


class TestTimeoutManager:
    """Tests for TimeoutManager."""
    
    def test_init(self):
        """Test TimeoutManager initialization."""
        timeout_mgr = TimeoutManager(timeout_seconds=10)
        
        assert timeout_mgr.timeout_seconds == 10
        assert timeout_mgr.start_time is None
        assert timeout_mgr.timer is None
        assert timeout_mgr.timed_out is False
    
    def test_init_invalid_timeout(self):
        """Test initialization with invalid timeout."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            TimeoutManager(timeout_seconds=0)
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            TimeoutManager(timeout_seconds=-1)
    
    def test_start_stop(self):
        """Test starting and stopping timer."""
        timeout_mgr = TimeoutManager(timeout_seconds=10)
        
        # Start timer
        timeout_mgr.start()
        assert timeout_mgr.start_time is not None
        assert timeout_mgr.timer is not None
        assert timeout_mgr.timed_out is False
        
        # Stop timer
        timeout_mgr.stop()
        assert timeout_mgr.timer is None
    
    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        timeout_mgr = TimeoutManager(timeout_seconds=10)
        
        # Before start
        assert timeout_mgr.get_elapsed_seconds() == 0.0
        
        # After start
        timeout_mgr.start()
        time.sleep(0.5)
        
        elapsed = timeout_mgr.get_elapsed_seconds()
        assert 0.4 < elapsed < 0.7  # Allow some tolerance
        
        timeout_mgr.stop()
    
    def test_remaining_time(self):
        """Test remaining time calculation."""
        timeout_mgr = TimeoutManager(timeout_seconds=2)
        
        timeout_mgr.start()
        time.sleep(0.5)
        
        remaining = timeout_mgr.get_remaining_seconds()
        assert 1.3 < remaining < 1.7  # Allow some tolerance
        
        timeout_mgr.stop()
    
    def test_timeout_detection(self):
        """Test timeout detection."""
        timeout_mgr = TimeoutManager(timeout_seconds=1)
        
        timeout_mgr.start()
        
        # Should not timeout immediately
        try:
            timeout_mgr.check_timeout()
        except TimeoutError:
            pytest.fail("Should not timeout immediately")
        
        # Wait for timeout
        time.sleep(1.5)
        
        # Should timeout now
        with pytest.raises(TimeoutError, match="Task execution timeout"):
            timeout_mgr.check_timeout()
        
        assert timeout_mgr.timed_out is True
        timeout_mgr.stop()
    
    def test_timeout_callback(self):
        """Test timeout callback invocation."""
        callback_invoked = []
        
        def callback():
            callback_invoked.append(True)
        
        timeout_mgr = TimeoutManager(timeout_seconds=1)
        timeout_mgr.start(callback=callback)
        
        # Wait for timeout
        time.sleep(1.5)
        
        # Callback should have been invoked
        assert len(callback_invoked) == 1
        assert timeout_mgr.timed_out is True
        
        timeout_mgr.stop()


class TestResourceMonitor:
    """Tests for ResourceMonitor."""
    
    def test_init_requires_psutil(self):
        """Test that ResourceMonitor requires psutil."""
        try:
            import psutil
            # If psutil is available, test normal initialization
            monitor = ResourceMonitor(
                max_memory_mb=100,
                max_cpu_percent=80
            )
            assert monitor.max_memory_mb == 100
            assert monitor.max_cpu_percent == 80
        except ImportError:
            # If psutil not available, should raise ImportError
            with pytest.raises(ImportError, match="psutil is required"):
                ResourceMonitor(max_memory_mb=100)
    
    def test_init_invalid_limits(self):
        """Test initialization with invalid limits."""
        try:
            import psutil
            
            # Invalid memory limit
            with pytest.raises(ValueError, match="max_memory_mb must be positive"):
                ResourceMonitor(max_memory_mb=0)
            
            # Invalid CPU limit
            with pytest.raises(ValueError, match="max_cpu_percent must be between"):
                ResourceMonitor(max_cpu_percent=0)
            
            with pytest.raises(ValueError, match="max_cpu_percent must be between"):
                ResourceMonitor(max_cpu_percent=101)
            
            # Invalid monitoring interval
            with pytest.raises(ValueError, match="monitoring_interval must be positive"):
                ResourceMonitor(
                    max_memory_mb=100,
                    monitoring_interval=0
                )
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_start_stop(self):
        """Test starting and stopping monitoring."""
        try:
            import psutil
            
            monitor = ResourceMonitor(
                max_memory_mb=1000,
                monitoring_interval=0.1
            )
            
            # Start monitoring
            monitor.start()
            assert monitor.monitoring is True
            assert monitor.monitor_thread is not None
            
            # Let it collect some samples
            time.sleep(0.5)
            
            # Stop monitoring
            monitor.stop()
            assert monitor.monitoring is False
            
            # Should have collected samples
            assert len(monitor.usage_history) > 0
            
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_get_current_usage(self):
        """Test getting current resource usage."""
        try:
            import psutil
            
            monitor = ResourceMonitor(
                max_memory_mb=1000,
                monitoring_interval=0.1
            )
            
            monitor.start()
            time.sleep(0.3)  # Let it collect samples
            
            current = monitor.get_current_usage()
            assert current is not None
            assert isinstance(current, ResourceUsage)
            assert current.memory_mb > 0
            assert current.memory_percent > 0
            assert current.cpu_percent >= 0
            
            monitor.stop()
            
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_get_peak_usage(self):
        """Test getting peak resource usage."""
        try:
            import psutil
            
            monitor = ResourceMonitor(
                max_memory_mb=1000,
                monitoring_interval=0.1
            )
            
            monitor.start()
            time.sleep(0.3)
            
            peak = monitor.get_peak_usage()
            assert peak is not None
            assert isinstance(peak, ResourceUsage)
            
            monitor.stop()
            
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_get_average_usage(self):
        """Test getting average resource usage."""
        try:
            import psutil
            
            monitor = ResourceMonitor(
                max_memory_mb=1000,
                monitoring_interval=0.1
            )
            
            monitor.start()
            time.sleep(0.3)
            
            average = monitor.get_average_usage()
            assert average is not None
            assert "memory_mb" in average
            assert "cpu_percent" in average
            assert "sample_count" in average
            assert average["sample_count"] > 0
            
            monitor.stop()
            
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_usage_summary(self):
        """Test getting usage summary."""
        try:
            import psutil
            
            monitor = ResourceMonitor(
                max_memory_mb=1000,
                monitoring_interval=0.1
            )
            
            monitor.start()
            time.sleep(0.3)
            monitor.stop()
            
            summary = monitor.get_usage_summary()
            assert "current" in summary
            assert "peak" in summary
            assert "average" in summary
            assert "limit_exceeded" in summary
            assert "sample_count" in summary
            
        except ImportError:
            pytest.skip("psutil not available")


class TestExecutionMonitor:
    """Tests for ExecutionMonitor."""
    
    def test_init(self):
        """Test ExecutionMonitor initialization."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            max_memory_mb=500,
            max_cpu_percent=80
        )
        
        assert exec_mon.timeout_manager is not None
        assert exec_mon.timeout_manager.timeout_seconds == 10
        
        # Resource monitor may or may not be available
        if exec_mon.resource_monitor:
            assert exec_mon.resource_monitor.max_memory_mb == 500
            assert exec_mon.resource_monitor.max_cpu_percent == 80
    
    def test_start_stop(self):
        """Test starting and stopping execution monitor."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            max_memory_mb=500
        )
        
        exec_mon.start()
        assert exec_mon.timeout_manager.start_time is not None
        
        if exec_mon.resource_monitor:
            assert exec_mon.resource_monitor.monitoring is True
        
        time.sleep(0.2)
        
        exec_mon.stop()
        assert exec_mon.timeout_manager.timer is None
        
        if exec_mon.resource_monitor:
            assert exec_mon.resource_monitor.monitoring is False
    
    def test_check_timeout(self):
        """Test timeout checking."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=1,
            max_memory_mb=1000
        )
        
        exec_mon.start()
        
        # Should not timeout immediately
        try:
            exec_mon.check()
        except TimeoutError:
            pytest.fail("Should not timeout immediately")
        
        # Wait for timeout
        time.sleep(1.5)
        
        # Should timeout now
        with pytest.raises(TimeoutError):
            exec_mon.check()
        
        exec_mon.stop()
    
    def test_get_status(self):
        """Test getting execution status."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            max_memory_mb=500
        )
        
        exec_mon.start()
        time.sleep(0.2)
        
        status = exec_mon.get_status()
        assert "elapsed_seconds" in status
        assert "remaining_seconds" in status
        assert "timed_out" in status
        
        assert status["elapsed_seconds"] > 0
        assert status["remaining_seconds"] < 10
        assert status["timed_out"] is False
        
        exec_mon.stop()


class TestResourceUsage:
    """Tests for ResourceUsage model."""
    
    def test_to_dict(self):
        """Test converting ResourceUsage to dictionary."""
        from datetime import datetime
        
        usage = ResourceUsage(
            timestamp=datetime.now(),
            memory_mb=100.5,
            memory_percent=10.2,
            cpu_percent=25.3,
            process_id=12345
        )
        
        data = usage.to_dict()
        assert "timestamp" in data
        assert data["memory_mb"] == 100.5
        assert data["memory_percent"] == 10.2
        assert data["cpu_percent"] == 25.3
        assert data["process_id"] == 12345
    
    def test_from_dict(self):
        """Test creating ResourceUsage from dictionary."""
        from datetime import datetime
        
        now = datetime.now()
        data = {
            "timestamp": now.isoformat(),
            "memory_mb": 100.5,
            "memory_percent": 10.2,
            "cpu_percent": 25.3,
            "process_id": 12345
        }
        
        usage = ResourceUsage.from_dict(data)
        assert usage.memory_mb == 100.5
        assert usage.memory_percent == 10.2
        assert usage.cpu_percent == 25.3
        assert usage.process_id == 12345


class TestServiceCallMetrics:
    """Tests for ServiceCallMetrics model."""
    
    def test_to_dict(self):
        """Test converting ServiceCallMetrics to dictionary."""
        from datetime import datetime
        
        start = datetime.now()
        end = datetime.now()
        
        metrics = ServiceCallMetrics(
            service_name="openai",
            operation="generate_code",
            start_time=start,
            end_time=end,
            duration_seconds=2.5,
            success=True,
            metadata={"tokens_used": 1500}
        )
        
        data = metrics.to_dict()
        assert data["service_name"] == "openai"
        assert data["operation"] == "generate_code"
        assert data["duration_seconds"] == 2.5
        assert data["success"] is True
        assert data["metadata"]["tokens_used"] == 1500
    
    def test_from_dict(self):
        """Test creating ServiceCallMetrics from dictionary."""
        from datetime import datetime
        
        now = datetime.now()
        data = {
            "service_name": "task_registry",
            "operation": "update_task_status",
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "duration_seconds": 0.5,
            "success": True,
            "error": None,
            "metadata": {}
        }
        
        metrics = ServiceCallMetrics.from_dict(data)
        assert metrics.service_name == "task_registry"
        assert metrics.operation == "update_task_status"
        assert metrics.duration_seconds == 0.5
        assert metrics.success is True


class TestServiceCallTracker:
    """Tests for ServiceCallTracker."""
    
    def test_init(self):
        """Test ServiceCallTracker initialization."""
        tracker = ServiceCallTracker()
        assert len(tracker.calls) == 0
    
    def test_record_call(self):
        """Test recording a service call."""
        tracker = ServiceCallTracker()
        
        tracker.record_call(
            service_name="openai",
            operation="generate_code",
            duration_seconds=2.5,
            success=True,
            metadata={"tokens_used": 1500}
        )
        
        assert len(tracker.calls) == 1
        call = tracker.calls[0]
        assert call.service_name == "openai"
        assert call.operation == "generate_code"
        assert call.duration_seconds == 2.5
        assert call.success is True
        assert call.metadata["tokens_used"] == 1500
    
    def test_get_calls_by_service(self):
        """Test getting calls by service name."""
        tracker = ServiceCallTracker()
        
        tracker.record_call("openai", "generate_code", 2.5, True)
        tracker.record_call("task_registry", "update_status", 0.5, True)
        tracker.record_call("openai", "generate_code", 3.0, True)
        
        openai_calls = tracker.get_calls_by_service("openai")
        assert len(openai_calls) == 2
        assert all(call.service_name == "openai" for call in openai_calls)
    
    def test_get_llm_calls(self):
        """Test getting LLM calls."""
        tracker = ServiceCallTracker()
        
        tracker.record_call("openai", "generate_code", 2.5, True)
        tracker.record_call("task_registry", "update_status", 0.5, True)
        tracker.record_call("anthropic", "generate_text", 1.5, True)
        
        llm_calls = tracker.get_llm_calls()
        assert len(llm_calls) == 2
        assert all(call.service_name.lower() in {"openai", "anthropic"} for call in llm_calls)
    
    def test_get_external_service_calls(self):
        """Test getting external service calls."""
        tracker = ServiceCallTracker()
        
        tracker.record_call("openai", "generate_code", 2.5, True)
        tracker.record_call("task_registry", "update_status", 0.5, True)
        tracker.record_call("repo_pool", "allocate_slot", 0.3, True)
        
        external_calls = tracker.get_external_service_calls()
        assert len(external_calls) == 2
        assert all(
            call.service_name.lower() in {"task_registry", "repo_pool"}
            for call in external_calls
        )
    
    def test_get_service_statistics(self):
        """Test getting service statistics."""
        tracker = ServiceCallTracker()
        
        tracker.record_call("openai", "generate_code", 2.5, True)
        tracker.record_call("openai", "generate_code", 3.0, True)
        tracker.record_call("openai", "generate_code", 1.5, False, error="Rate limit")
        
        stats = tracker.get_service_statistics("openai")
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["total_duration_seconds"] == 7.0
        assert stats["average_duration_seconds"] == pytest.approx(7.0 / 3)
        assert stats["min_duration_seconds"] == 1.5
        assert stats["max_duration_seconds"] == 3.0
    
    def test_get_llm_statistics(self):
        """Test getting LLM statistics."""
        tracker = ServiceCallTracker()
        
        tracker.record_call(
            "openai", "generate_code", 2.5, True,
            metadata={"tokens_used": 1500}
        )
        tracker.record_call(
            "openai", "generate_code", 3.0, True,
            metadata={"tokens_used": 2000}
        )
        
        stats = tracker.get_llm_statistics()
        assert stats["total_calls"] == 2
        assert stats["total_duration_seconds"] == 5.5
        assert stats["average_duration_seconds"] == 2.75
        assert stats["total_tokens_used"] == 3500
    
    def test_get_external_service_statistics(self):
        """Test getting external service statistics."""
        tracker = ServiceCallTracker()
        
        tracker.record_call("task_registry", "update_status", 0.5, True)
        tracker.record_call("task_registry", "add_event", 0.3, True)
        tracker.record_call("repo_pool", "allocate_slot", 0.8, True)
        
        stats = tracker.get_external_service_statistics()
        assert stats["total_calls"] == 3
        assert stats["total_duration_seconds"] == 1.6
        assert "by_service" in stats
        assert "task_registry" in stats["by_service"]
        assert "repo_pool" in stats["by_service"]
        assert stats["by_service"]["task_registry"]["total_calls"] == 2
        assert stats["by_service"]["repo_pool"]["total_calls"] == 1
    
    def test_get_all_statistics(self):
        """Test getting all statistics."""
        tracker = ServiceCallTracker()
        
        tracker.record_call(
            "openai", "generate_code", 2.5, True,
            metadata={"tokens_used": 1500}
        )
        tracker.record_call("task_registry", "update_status", 0.5, True)
        
        stats = tracker.get_all_statistics()
        assert "llm" in stats
        assert "external_services" in stats
        assert "all_calls" in stats
        assert stats["llm"]["total_calls"] == 1
        assert stats["external_services"]["total_calls"] == 1
        assert stats["all_calls"]["total_calls"] == 2
    
    def test_clear(self):
        """Test clearing recorded calls."""
        tracker = ServiceCallTracker()
        
        tracker.record_call("openai", "generate_code", 2.5, True)
        tracker.record_call("task_registry", "update_status", 0.5, True)
        
        assert len(tracker.calls) == 2
        
        tracker.clear()
        assert len(tracker.calls) == 0


class TestExecutionMonitorWithServiceTracking:
    """Tests for ExecutionMonitor with service call tracking."""
    
    def test_init_with_service_tracking(self):
        """Test ExecutionMonitor initialization with service tracking."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            track_service_calls=True
        )
        
        assert exec_mon.service_call_tracker is not None
    
    def test_init_without_service_tracking(self):
        """Test ExecutionMonitor initialization without service tracking."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            track_service_calls=False
        )
        
        assert exec_mon.service_call_tracker is None
    
    def test_record_service_call(self):
        """Test recording service calls."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            track_service_calls=True
        )
        
        exec_mon.record_service_call(
            service_name="openai",
            operation="generate_code",
            duration_seconds=2.5,
            success=True,
            metadata={"tokens_used": 1500}
        )
        
        assert len(exec_mon.service_call_tracker.calls) == 1
    
    def test_get_status_with_service_calls(self):
        """Test getting status with service call statistics."""
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            track_service_calls=True
        )
        
        exec_mon.start()
        
        exec_mon.record_service_call(
            "openai", "generate_code", 2.5, True,
            metadata={"tokens_used": 1500}
        )
        exec_mon.record_service_call(
            "task_registry", "update_status", 0.5, True
        )
        
        time.sleep(0.1)
        
        status = exec_mon.get_status()
        assert "service_calls" in status
        assert "llm" in status["service_calls"]
        assert "external_services" in status["service_calls"]
        assert status["service_calls"]["llm"]["total_calls"] == 1
        assert status["service_calls"]["external_services"]["total_calls"] == 1
        
        exec_mon.stop()

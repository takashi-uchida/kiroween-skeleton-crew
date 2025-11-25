"""
Tests for resource monitoring and timeout functionality.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

import time
import pytest

from necrocode.agent_runner.resource_monitor import (
    ExecutionMonitor,
    ResourceMonitor,
    ResourceUsage,
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

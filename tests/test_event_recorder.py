"""
Tests for EventRecorder.

Tests event recording functionality with Task Registry integration
and fallback logging.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import EventType
from necrocode.dispatcher.event_recorder import EventRecorder


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def task_registry(temp_dir):
    """Create a TaskRegistry instance for testing."""
    registry_dir = temp_dir / "registry"
    return TaskRegistry(registry_dir=str(registry_dir))


@pytest.fixture
def event_recorder(task_registry, temp_dir):
    """Create an EventRecorder instance for testing."""
    fallback_dir = temp_dir / "fallback"
    return EventRecorder(
        task_registry=task_registry,
        fallback_log_dir=fallback_dir
    )


def test_record_task_assigned(event_recorder, task_registry):
    """Test recording TaskAssigned event."""
    # Record event
    success = event_recorder.record_task_assigned(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local"
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.TASK_ASSIGNED
    assert event.spec_name == "test-spec"
    assert event.task_id == "1.1"
    assert event.details["runner_id"] == "runner-123"
    assert event.details["slot_id"] == "slot-456"
    assert event.details["pool_name"] == "local"


def test_record_runner_started(event_recorder, task_registry):
    """Test recording RunnerStarted event."""
    # Record event with local process details
    success = event_recorder.record_runner_started(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local",
        pid=12345
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.RUNNER_STARTED
    assert event.details["runner_id"] == "runner-123"
    assert event.details["pid"] == 12345


def test_record_runner_started_docker(event_recorder, task_registry):
    """Test recording RunnerStarted event for Docker."""
    # Record event with Docker details
    success = event_recorder.record_runner_started(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="docker",
        container_id="abc123"
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.RUNNER_STARTED
    assert event.details["container_id"] == "abc123"


def test_record_runner_finished_success(event_recorder, task_registry):
    """Test recording RunnerFinished event for successful completion."""
    # Record event
    success = event_recorder.record_runner_finished(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        success=True,
        execution_time_seconds=45.5
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.RUNNER_FINISHED
    assert event.details["success"] is True
    assert event.details["execution_time_seconds"] == 45.5
    assert "failure_reason" not in event.details


def test_record_runner_finished_failure(event_recorder, task_registry):
    """Test recording RunnerFinished event for failure."""
    # Record event
    success = event_recorder.record_runner_finished(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        success=False,
        execution_time_seconds=10.0,
        failure_reason="timeout"
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.RUNNER_FINISHED
    assert event.details["success"] is False
    assert event.details["failure_reason"] == "timeout"


def test_record_task_completed(event_recorder, task_registry):
    """Test recording TaskCompleted event."""
    # Record event
    success = event_recorder.record_task_completed(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        execution_time_seconds=60.0
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.TASK_COMPLETED
    assert event.details["runner_id"] == "runner-123"
    assert event.details["execution_time_seconds"] == 60.0


def test_record_task_failed(event_recorder, task_registry):
    """Test recording TaskFailed event."""
    # Record event
    success = event_recorder.record_task_failed(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        failure_reason="execution error",
        retry_count=2
    )
    
    assert success is True
    
    # Verify event was recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    
    event = events[0]
    assert event.event_type == EventType.TASK_FAILED
    assert event.details["runner_id"] == "runner-123"
    assert event.details["failure_reason"] == "execution error"
    assert event.details["retry_count"] == 2


def test_multiple_events_for_task(event_recorder, task_registry):
    """Test recording multiple events for the same task."""
    # Record multiple events
    event_recorder.record_task_assigned(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local"
    )
    
    event_recorder.record_runner_started(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local"
    )
    
    event_recorder.record_task_completed(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123"
    )
    
    # Verify all events were recorded
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 3
    
    # Verify event types
    event_types = [e.event_type for e in events]
    assert EventType.TASK_ASSIGNED in event_types
    assert EventType.RUNNER_STARTED in event_types
    assert EventType.TASK_COMPLETED in event_types


def test_fallback_logging(temp_dir):
    """Test fallback logging when Task Registry fails."""
    from unittest.mock import Mock, patch
    from necrocode.task_registry.exceptions import TaskRegistryError
    
    # Create a task registry with a valid directory
    registry_dir = temp_dir / "registry"
    task_registry = TaskRegistry(registry_dir=str(registry_dir))
    
    # Create event recorder
    fallback_dir = temp_dir / "fallback"
    recorder = EventRecorder(
        task_registry=task_registry,
        fallback_log_dir=fallback_dir
    )
    
    # Mock the event_store.record_event to raise an exception
    with patch.object(task_registry.event_store, 'record_event', side_effect=TaskRegistryError("Simulated failure")):
        # Try to record event (should fail and fallback to local log)
        success = recorder.record_task_assigned(
            spec_name="test-spec",
            task_id="1.1",
            runner_id="runner-123",
            slot_id="slot-456",
            pool_name="local"
        )
        
        # Recording should return False (failed to write to Task Registry)
        assert success is False
        
        # Verify fallback log was created
        fallback_file = fallback_dir / "test-spec_events.jsonl"
        assert fallback_file.exists()
        
        # Verify fallback log contains the event
        with open(fallback_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 1
        # Check that the failed event is in the fallback log
        assert "TaskAssigned" in lines[0]
        assert "runner-123" in lines[0]


def test_statistics(event_recorder):
    """Test event recording statistics."""
    # Initially no events
    stats = event_recorder.get_statistics()
    assert stats["total_events"] == 0
    assert stats["failed_events"] == 0
    assert stats["success_rate"] == 0.0
    
    # Record some successful events
    event_recorder.record_task_assigned(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local"
    )
    
    event_recorder.record_runner_started(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local"
    )
    
    # Check statistics
    stats = event_recorder.get_statistics()
    assert stats["total_events"] == 2
    assert stats["failed_events"] == 0
    assert stats["success_rate"] == 100.0


def test_custom_timestamp(event_recorder, task_registry):
    """Test recording event with custom timestamp."""
    custom_time = datetime(2024, 1, 1, 12, 0, 0)
    
    # Record event with custom timestamp
    event_recorder.record_task_assigned(
        spec_name="test-spec",
        task_id="1.1",
        runner_id="runner-123",
        slot_id="slot-456",
        pool_name="local",
        timestamp=custom_time
    )
    
    # Verify timestamp
    events = task_registry.event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    assert events[0].timestamp == custom_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

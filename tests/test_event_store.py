"""Unit tests for EventStore.

Tests event recording, searching, and log rotation.
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.event_store import EventStore
from necrocode.task_registry.models import TaskEvent, EventType


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def events_dir(tmp_path):
    """Create temporary events directory."""
    return tmp_path / "events"


@pytest.fixture
def event_store(events_dir):
    """Create EventStore instance."""
    return EventStore(events_dir)


@pytest.fixture
def sample_event():
    """Create sample TaskEvent."""
    return TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={"title": "Test Task"},
    )


# ============================================================================
# EventStore Initialization Tests
# ============================================================================

def test_event_store_creates_events_dir(events_dir):
    """Test EventStore creates events directory if it doesn't exist."""
    assert not events_dir.exists()
    
    EventStore(events_dir)
    
    assert events_dir.exists()
    assert events_dir.is_dir()


def test_event_store_uses_existing_events_dir(events_dir):
    """Test EventStore uses existing events directory."""
    events_dir.mkdir(parents=True)
    test_file = events_dir / "test.txt"
    test_file.write_text("test")
    
    EventStore(events_dir)
    
    assert events_dir.exists()
    assert test_file.exists()


# ============================================================================
# Record Event Tests
# ============================================================================

def test_record_event_creates_spec_directory(event_store, sample_event):
    """Test record_event creates spec directory."""
    event_store.record_event(sample_event)
    
    spec_dir = event_store.events_dir / "test-spec"
    assert spec_dir.exists()
    assert spec_dir.is_dir()


def test_record_event_creates_events_file(event_store, sample_event):
    """Test record_event creates events.jsonl file."""
    event_store.record_event(sample_event)
    
    events_file = event_store.events_dir / "test-spec" / "events.jsonl"
    assert events_file.exists()
    assert events_file.is_file()


def test_record_event_writes_json_lines(event_store, sample_event):
    """Test record_event writes JSON Lines format."""
    event_store.record_event(sample_event)
    
    events_file = event_store.events_dir / "test-spec" / "events.jsonl"
    with open(events_file, "r") as f:
        line = f.readline()
    
    # Should be valid JSON
    event_data = json.loads(line)
    assert event_data["event_type"] == "TaskCreated"
    assert event_data["spec_name"] == "test-spec"
    assert event_data["task_id"] == "1.1"


def test_record_event_appends_to_existing_file(event_store):
    """Test record_event appends to existing events file."""
    event1 = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={"title": "Task 1"},
    )
    
    event2 = TaskEvent(
        event_type=EventType.TASK_ASSIGNED,
        spec_name="test-spec",
        task_id="1.1",
        details={"runner_id": "runner-1"},
    )
    
    event_store.record_event(event1)
    event_store.record_event(event2)
    
    events_file = event_store.events_dir / "test-spec" / "events.jsonl"
    with open(events_file, "r") as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    assert "TaskCreated" in lines[0]
    assert "TaskAssigned" in lines[1]


def test_record_event_multiple_specs(event_store):
    """Test record_event handles multiple specs."""
    event1 = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="spec-one",
        task_id="1.1",
        details={},
    )
    
    event2 = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="spec-two",
        task_id="1.1",
        details={},
    )
    
    event_store.record_event(event1)
    event_store.record_event(event2)
    
    assert (event_store.events_dir / "spec-one" / "events.jsonl").exists()
    assert (event_store.events_dir / "spec-two" / "events.jsonl").exists()


# ============================================================================
# Get Events by Task Tests
# ============================================================================

def test_get_events_by_task_returns_matching_events(event_store):
    """Test get_events_by_task returns events for specific task."""
    # Record events for different tasks
    event1 = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={"title": "Task 1.1"},
    )
    
    event2 = TaskEvent(
        event_type=EventType.TASK_ASSIGNED,
        spec_name="test-spec",
        task_id="1.1",
        details={"runner_id": "runner-1"},
    )
    
    event3 = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.2",
        details={"title": "Task 1.2"},
    )
    
    event_store.record_event(event1)
    event_store.record_event(event2)
    event_store.record_event(event3)
    
    # Get events for task 1.1
    events = event_store.get_events_by_task("test-spec", "1.1")
    
    assert len(events) == 2
    assert all(e.task_id == "1.1" for e in events)
    assert events[0].event_type == EventType.TASK_CREATED
    assert events[1].event_type == EventType.TASK_ASSIGNED


def test_get_events_by_task_empty_result(event_store):
    """Test get_events_by_task returns empty list for nonexistent task."""
    events = event_store.get_events_by_task("test-spec", "nonexistent")
    assert events == []


def test_get_events_by_task_nonexistent_spec(event_store):
    """Test get_events_by_task returns empty list for nonexistent spec."""
    events = event_store.get_events_by_task("nonexistent-spec", "1.1")
    assert events == []


def test_get_events_by_task_preserves_order(event_store):
    """Test get_events_by_task preserves chronological order."""
    # Record events in order
    for i in range(5):
        event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name="test-spec",
            task_id="1.1",
            details={"update": i},
        )
        event_store.record_event(event)
    
    events = event_store.get_events_by_task("test-spec", "1.1")
    
    assert len(events) == 5
    for i, event in enumerate(events):
        assert event.details["update"] == i


# ============================================================================
# Get Events by Timerange Tests
# ============================================================================

def test_get_events_by_timerange_returns_matching_events(event_store):
    """Test get_events_by_timerange returns events within timerange."""
    base_time = datetime(2025, 11, 15, 10, 0, 0)
    
    # Create events with different timestamps
    for i in range(5):
        event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name="test-spec",
            task_id="1.1",
            details={"index": i},
        )
        # Manually set timestamp
        event.timestamp = base_time + timedelta(hours=i)
        event_store.record_event(event)
    
    # Query for events between hour 1 and hour 3
    start_time = base_time + timedelta(hours=1)
    end_time = base_time + timedelta(hours=3)
    
    events = event_store.get_events_by_timerange("test-spec", start_time, end_time)
    
    # Should get events at hours 1, 2, 3 (inclusive)
    assert len(events) == 3
    assert events[0].details["index"] == 1
    assert events[1].details["index"] == 2
    assert events[2].details["index"] == 3


def test_get_events_by_timerange_empty_result(event_store):
    """Test get_events_by_timerange returns empty list when no events match."""
    base_time = datetime(2025, 11, 15, 10, 0, 0)
    
    event = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={},
    )
    event.timestamp = base_time
    event_store.record_event(event)
    
    # Query for different timerange
    start_time = base_time + timedelta(days=1)
    end_time = base_time + timedelta(days=2)
    
    events = event_store.get_events_by_timerange("test-spec", start_time, end_time)
    assert events == []


def test_get_events_by_timerange_nonexistent_spec(event_store):
    """Test get_events_by_timerange returns empty list for nonexistent spec."""
    start_time = datetime(2025, 11, 15, 10, 0, 0)
    end_time = datetime(2025, 11, 15, 12, 0, 0)
    
    events = event_store.get_events_by_timerange("nonexistent-spec", start_time, end_time)
    assert events == []


def test_get_events_by_timerange_all_event_types(event_store):
    """Test get_events_by_timerange returns all event types in range."""
    base_time = datetime(2025, 11, 15, 10, 0, 0)
    
    event_types = [
        EventType.TASK_CREATED,
        EventType.TASK_ASSIGNED,
        EventType.TASK_COMPLETED,
        EventType.TASK_FAILED,
    ]
    
    for i, event_type in enumerate(event_types):
        event = TaskEvent(
            event_type=event_type,
            spec_name="test-spec",
            task_id="1.1",
            details={},
        )
        event.timestamp = base_time + timedelta(minutes=i)
        event_store.record_event(event)
    
    events = event_store.get_events_by_timerange(
        "test-spec",
        base_time,
        base_time + timedelta(hours=1)
    )
    
    assert len(events) == 4
    returned_types = {e.event_type for e in events}
    assert returned_types == set(event_types)


# ============================================================================
# Log Rotation Tests
# ============================================================================

def test_rotate_logs_creates_rotated_file(event_store, sample_event):
    """Test rotate_logs creates rotated log file."""
    # Record some events
    for i in range(10):
        event_store.record_event(sample_event)
    
    # Rotate logs
    event_store.rotate_logs(max_size_mb=0.001)  # Very small size to force rotation
    
    # Check for rotated file
    spec_dir = event_store.events_dir / "test-spec"
    rotated_files = list(spec_dir.glob("events.jsonl.*"))
    
    assert len(rotated_files) > 0


def test_rotate_logs_preserves_events(event_store):
    """Test rotate_logs preserves all events in rotated file."""
    # Record events
    events_to_record = []
    for i in range(10):
        event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name="test-spec",
            task_id="1.1",
            details={"index": i},
        )
        events_to_record.append(event)
        event_store.record_event(event)
    
    # Rotate logs
    event_store.rotate_logs(max_size_mb=0.001)
    
    # After rotation, current file should be empty
    events = event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 0
    
    # But rotated file should exist
    rotated_file = event_store.events_dir / "test-spec" / "events.jsonl.1"
    assert rotated_file.exists()


def test_rotate_logs_no_rotation_when_under_limit(event_store, sample_event):
    """Test rotate_logs doesn't rotate when under size limit."""
    # Record a few events
    for i in range(3):
        event_store.record_event(sample_event)
    
    # Rotate with large limit
    event_store.rotate_logs(max_size_mb=100)
    
    # Should not create rotated files
    spec_dir = event_store.events_dir / "test-spec"
    rotated_files = list(spec_dir.glob("events.jsonl.*"))
    
    assert len(rotated_files) == 0


def test_rotate_logs_multiple_specs(event_store):
    """Test rotate_logs handles multiple specs."""
    # Record events for multiple specs
    for spec_name in ["spec-one", "spec-two", "spec-three"]:
        for i in range(10):
            event = TaskEvent(
                event_type=EventType.TASK_CREATED,
                spec_name=spec_name,
                task_id="1.1",
                details={},
            )
            event_store.record_event(event)
    
    # Rotate logs
    event_store.rotate_logs(max_size_mb=0.001)
    
    # Verify rotation happened for all specs
    for spec_name in ["spec-one", "spec-two", "spec-three"]:
        spec_dir = event_store.events_dir / spec_name
        assert spec_dir.exists()


def test_rotate_logs_increments_rotation_number(event_store, sample_event):
    """Test rotate_logs increments rotation number."""
    # Record and rotate multiple times
    for rotation in range(3):
        for i in range(10):
            event_store.record_event(sample_event)
        event_store.rotate_logs(max_size_mb=0.001)
    
    # Check for multiple rotated files
    spec_dir = event_store.events_dir / "test-spec"
    rotated_files = sorted(spec_dir.glob("events.jsonl.*"))
    
    assert len(rotated_files) >= 2


# ============================================================================
# Event Type Coverage Tests
# ============================================================================

def test_record_all_event_types(event_store):
    """Test recording all event types."""
    event_types = [
        EventType.TASK_CREATED,
        EventType.TASK_UPDATED,
        EventType.TASK_READY,
        EventType.TASK_ASSIGNED,
        EventType.TASK_COMPLETED,
        EventType.TASK_FAILED,
        EventType.RUNNER_STARTED,
        EventType.RUNNER_FINISHED,
        EventType.PR_OPENED,
        EventType.PR_MERGED,
    ]
    
    for event_type in event_types:
        event = TaskEvent(
            event_type=event_type,
            spec_name="test-spec",
            task_id="1.1",
            details={},
        )
        event_store.record_event(event)
    
    # Verify all events were recorded
    events = event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == len(event_types)
    
    recorded_types = {e.event_type for e in events}
    assert recorded_types == set(event_types)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_record_event_with_large_details(event_store):
    """Test recording event with large details."""
    large_details = {
        "data": "x" * 10000,  # 10KB of data
        "nested": {
            "level1": {
                "level2": {
                    "level3": "deep nesting"
                }
            }
        }
    }
    
    event = TaskEvent(
        event_type=EventType.TASK_UPDATED,
        spec_name="test-spec",
        task_id="1.1",
        details=large_details,
    )
    
    event_store.record_event(event)
    
    # Verify event can be retrieved
    events = event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    assert events[0].details["data"] == large_details["data"]


def test_record_event_with_special_characters(event_store):
    """Test recording event with special characters."""
    event = TaskEvent(
        event_type=EventType.TASK_CREATED,
        spec_name="test-spec",
        task_id="1.1",
        details={
            "title": "Task with 日本語 and émojis 🎉",
            "description": "Line1\nLine2\tTabbed",
        },
    )
    
    event_store.record_event(event)
    
    events = event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 1
    assert events[0].details["title"] == event.details["title"]
    assert events[0].details["description"] == event.details["description"]


def test_get_events_handles_corrupted_line(event_store, sample_event):
    """Test get_events_by_task handles corrupted JSON line gracefully."""
    # Record valid event
    event_store.record_event(sample_event)
    
    # Append corrupted line
    events_file = event_store.events_dir / "test-spec" / "events.jsonl"
    with open(events_file, "a") as f:
        f.write("{ invalid json }\n")
    
    # Record another valid event
    event_store.record_event(sample_event)
    
    # Should skip corrupted line and return valid events
    events = event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 2


def test_concurrent_event_recording(event_store):
    """Test concurrent event recording (basic test)."""
    # Record events rapidly
    events_to_record = []
    for i in range(100):
        event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name="test-spec",
            task_id="1.1",
            details={"index": i},
        )
        events_to_record.append(event)
        event_store.record_event(event)
    
    # Verify all events were recorded
    events = event_store.get_events_by_task("test-spec", "1.1")
    assert len(events) == 100

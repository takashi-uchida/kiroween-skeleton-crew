"""Performance tests for event log operations.

Tests EventStore write performance and log rotation.
Requirements: All
"""

import time
from pathlib import Path
import sys
import pytest
from datetime import datetime, timedelta

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


def generate_event(spec_name: str, task_id: str, event_type: EventType) -> TaskEvent:
    """Generate a test event."""
    return TaskEvent(
        event_type=event_type,
        spec_name=spec_name,
        task_id=task_id,
        timestamp=datetime.now(),
        details={"test": "data", "value": 123}
    )


# ============================================================================
# Single Event Write Performance Tests
# ============================================================================

def test_single_event_write_performance(event_store):
    """Test performance of writing single events."""
    event = generate_event("test-spec", "1.1", EventType.TASK_CREATED)
    
    start = time.time()
    event_store.record_event(event)
    elapsed = time.time() - start
    
    assert elapsed < 0.1  # Should complete within 100ms
    print(f"\nWrote single event in {elapsed*1000:.2f} ms")


def test_sequential_event_writes(event_store):
    """Test performance of sequential event writes."""
    num_events = 100
    
    start = time.time()
    
    for i in range(num_events):
        event = generate_event("test-spec", f"{i}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # Should complete within 5 seconds
    print(f"\nWrote {num_events} events sequentially in {elapsed:.2f} seconds")
    print(f"Average: {elapsed/num_events*1000:.2f} ms per event")


# ============================================================================
# Bulk Event Write Performance Tests
# ============================================================================

def test_bulk_event_writes_1000_events(event_store):
    """Test writing 1000 events."""
    num_events = 1000
    
    start = time.time()
    
    for i in range(num_events):
        event = generate_event("test-spec", f"{i % 100}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nWrote {num_events} events in {elapsed:.2f} seconds")
    print(f"Throughput: {num_events/elapsed:.0f} events/second")


def test_bulk_event_writes_10000_events(event_store):
    """Test writing 10000 events."""
    num_events = 10000
    
    start = time.time()
    
    for i in range(num_events):
        event = generate_event("test-spec", f"{i % 100}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 120.0  # Should complete within 2 minutes
    print(f"\nWrote {num_events} events in {elapsed:.2f} seconds")
    print(f"Throughput: {num_events/elapsed:.0f} events/second")


# ============================================================================
# Event Read Performance Tests
# ============================================================================

def test_read_events_by_task_performance(event_store):
    """Test performance of reading events by task."""
    # Write events
    for i in range(1000):
        event = generate_event("test-spec", "1.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    # Read events
    start = time.time()
    events = event_store.get_events_by_task("test-spec", "1.1")
    elapsed = time.time() - start
    
    assert len(events) == 1000
    assert elapsed < 2.0  # Should complete within 2 seconds
    print(f"\nRead 1000 events by task in {elapsed:.3f} seconds")


def test_read_events_by_timerange_performance(event_store):
    """Test performance of reading events by time range."""
    # Write events with different timestamps
    base_time = datetime.now()
    for i in range(1000):
        event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name="test-spec",
            task_id=f"{i % 100}.1",
            timestamp=base_time + timedelta(seconds=i),
            details={"index": i}
        )
        event_store.record_event(event)
    
    # Read events in time range
    start_time = base_time
    end_time = base_time + timedelta(seconds=500)
    
    start = time.time()
    events = event_store.get_events_by_timerange("test-spec", start_time, end_time)
    elapsed = time.time() - start
    
    assert len(events) > 0
    assert elapsed < 3.0  # Should complete within 3 seconds
    print(f"\nRead events by timerange in {elapsed:.3f} seconds")


def test_read_all_events_performance(event_store):
    """Test performance of reading all events."""
    # Write events for a single task
    for i in range(1000):
        event = generate_event("test-spec", "1.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    # Read all events for that task
    start = time.time()
    events = event_store.get_events_by_task("test-spec", "1.1")
    elapsed = time.time() - start
    
    assert len(events) >= 1000
    assert elapsed < 5.0  # Should complete within 5 seconds
    print(f"\nRead all events in {elapsed:.3f} seconds")


# ============================================================================
# Log Rotation Performance Tests
# ============================================================================

def test_log_rotation_performance(event_store):
    """Test performance of log rotation."""
    # Write many events to trigger rotation
    for i in range(5000):
        event = generate_event("test-spec", f"{i % 100}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    # Perform rotation
    start = time.time()
    event_store.rotate_logs(max_size_mb=1)  # Small size to force rotation
    elapsed = time.time() - start
    
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nRotated logs in {elapsed:.2f} seconds")


def test_log_rotation_with_large_file(event_store):
    """Test log rotation with large event log file."""
    # Write many events
    for i in range(10000):
        event = generate_event("test-spec", f"{i % 100}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    # Check file size
    event_file = event_store.events_dir / "test-spec" / "events.jsonl"
    file_size_mb = event_file.stat().st_size / 1024 / 1024
    print(f"\nEvent log file size: {file_size_mb:.2f} MB")
    
    # Rotate
    start = time.time()
    event_store.rotate_logs(max_size_mb=5)
    elapsed = time.time() - start
    
    assert elapsed < 15.0  # Should complete within 15 seconds
    print(f"Rotated {file_size_mb:.2f} MB log in {elapsed:.2f} seconds")


# ============================================================================
# Multiple Spec Performance Tests
# ============================================================================

def test_multiple_specs_event_writes(event_store):
    """Test writing events for multiple specs."""
    num_specs = 10
    events_per_spec = 100
    
    start = time.time()
    
    for spec_num in range(num_specs):
        spec_name = f"spec-{spec_num}"
        for i in range(events_per_spec):
            event = generate_event(spec_name, f"{i}.1", EventType.TASK_UPDATED)
            event_store.record_event(event)
    
    elapsed = time.time() - start
    
    total_events = num_specs * events_per_spec
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nWrote {total_events} events across {num_specs} specs in {elapsed:.2f} seconds")


def test_concurrent_spec_event_reads(event_store):
    """Test reading events from multiple specs concurrently."""
    # Write events for multiple specs
    num_specs = 5
    for spec_num in range(num_specs):
        spec_name = f"spec-{spec_num}"
        for i in range(200):
            event = generate_event(spec_name, f"{i}.1", EventType.TASK_UPDATED)
            event_store.record_event(event)
    
    # Read from all specs
    start = time.time()
    
    for spec_num in range(num_specs):
        spec_name = f"spec-{spec_num}"
        events = event_store.get_events_by_task(spec_name, "1.1")
    
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # Should complete within 5 seconds
    print(f"\nRead events from {num_specs} specs in {elapsed:.3f} seconds")


# ============================================================================
# Event Type Distribution Tests
# ============================================================================

def test_mixed_event_types_performance(event_store):
    """Test performance with mixed event types."""
    event_types = [
        EventType.TASK_CREATED,
        EventType.TASK_UPDATED,
        EventType.TASK_READY,
        EventType.TASK_ASSIGNED,
        EventType.TASK_COMPLETED,
        EventType.TASK_FAILED,
    ]
    
    num_events = 1000
    
    start = time.time()
    
    for i in range(num_events):
        event_type = event_types[i % len(event_types)]
        event = generate_event("test-spec", f"{i % 100}.1", event_type)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nWrote {num_events} mixed-type events in {elapsed:.2f} seconds")


# ============================================================================
# Large Event Payload Tests
# ============================================================================

def test_large_event_payload_performance(event_store):
    """Test performance with large event payloads."""
    # Create event with large details
    large_details = {
        "description": "x" * 10000,  # 10KB string
        "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
        "artifacts": [f"file://artifact-{i}.txt" for i in range(50)]
    }
    
    num_events = 100
    
    start = time.time()
    
    for i in range(num_events):
        event = TaskEvent(
            event_type=EventType.TASK_UPDATED,
            spec_name="test-spec",
            task_id=f"{i}.1",
            timestamp=datetime.now(),
            details=large_details
        )
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 10.0  # Should complete within 10 seconds
    print(f"\nWrote {num_events} large events in {elapsed:.2f} seconds")


# ============================================================================
# File System Performance Tests
# ============================================================================

def test_event_file_growth_rate(event_store):
    """Test event file growth rate."""
    initial_size = 0
    event_file = event_store.events_dir / "test-spec" / "events.jsonl"
    
    if event_file.exists():
        initial_size = event_file.stat().st_size
    
    # Write 1000 events
    for i in range(1000):
        event = generate_event("test-spec", f"{i}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    final_size = event_file.stat().st_size
    growth = (final_size - initial_size) / 1024  # KB
    
    print(f"\nFile grew by {growth:.2f} KB for 1000 events")
    print(f"Average: {growth/1000:.2f} KB per event")
    
    # Should be reasonable size (< 1MB for 1000 events)
    assert growth < 1024


def test_event_file_append_performance(event_store):
    """Test append performance to existing event file."""
    # Create initial file with events
    for i in range(1000):
        event = generate_event("test-spec", f"{i}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    # Measure append performance
    start = time.time()
    
    for i in range(1000, 2000):
        event = generate_event("test-spec", f"{i}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nAppended 1000 events to existing file in {elapsed:.2f} seconds")


# ============================================================================
# Stress Tests
# ============================================================================

@pytest.mark.slow
def test_extreme_event_volume_50000_events(event_store):
    """Stress test with 50000 events (marked as slow)."""
    num_events = 50000
    
    start = time.time()
    
    for i in range(num_events):
        event = generate_event("test-spec", f"{i % 1000}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    
    assert elapsed < 300.0  # Should complete within 5 minutes
    print(f"\nWrote {num_events} events in {elapsed:.2f} seconds")
    print(f"Throughput: {num_events/elapsed:.0f} events/second")


@pytest.mark.slow
def test_extreme_read_performance_50000_events(event_store):
    """Stress test reading 50000 events."""
    # Write events
    for i in range(50000):
        event = generate_event("test-spec", "1.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    # Read all events
    start = time.time()
    events = event_store.get_events_by_task("test-spec", "1.1")
    elapsed = time.time() - start
    
    assert len(events) == 50000
    assert elapsed < 30.0  # Should complete within 30 seconds
    print(f"\nRead {len(events)} events in {elapsed:.2f} seconds")


# ============================================================================
# Throughput Tests
# ============================================================================

def test_sustained_write_throughput(event_store):
    """Test sustained write throughput over time."""
    duration_seconds = 10
    event_count = 0
    
    start = time.time()
    
    while time.time() - start < duration_seconds:
        event = generate_event("test-spec", f"{event_count % 100}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
        event_count += 1
    
    elapsed = time.time() - start
    throughput = event_count / elapsed
    
    print(f"\nSustained throughput: {throughput:.0f} events/second over {elapsed:.1f} seconds")
    print(f"Total events written: {event_count}")
    
    # Should maintain reasonable throughput
    assert throughput > 50  # At least 50 events/second


def test_burst_write_performance(event_store):
    """Test burst write performance."""
    burst_size = 1000
    
    start = time.time()
    
    # Write burst of events as fast as possible
    for i in range(burst_size):
        event = generate_event("test-spec", f"{i}.1", EventType.TASK_UPDATED)
        event_store.record_event(event)
    
    elapsed = time.time() - start
    throughput = burst_size / elapsed
    
    print(f"\nBurst throughput: {throughput:.0f} events/second")
    print(f"Wrote {burst_size} events in {elapsed:.3f} seconds")
    
    # Should handle bursts efficiently
    assert elapsed < 10.0


# ============================================================================
# Memory Efficiency Tests
# ============================================================================

def test_memory_usage_during_writes(event_store):
    """Test memory usage during event writes."""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Write many events
        for i in range(10000):
            event = generate_event("test-spec", f"{i % 100}.1", EventType.TASK_UPDATED)
            event_store.record_event(event)
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory increase for 10000 events: {memory_increase:.2f} MB")
        
        # Should not use excessive memory (< 100 MB for 10000 events)
        assert memory_increase < 100
    except ImportError:
        pytest.skip("psutil not available")


def test_memory_usage_during_reads(event_store):
    """Test memory usage during event reads."""
    try:
        import psutil
        import os
        
        # Write events
        for i in range(10000):
            event = generate_event("test-spec", "1.1", EventType.TASK_UPDATED)
            event_store.record_event(event)
        
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Read events
        events = event_store.get_events_by_task("test-spec", "1.1")
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory increase for reading 10000 events: {memory_increase:.2f} MB")
        
        # Should not use excessive memory
        assert memory_increase < 200
    except ImportError:
        pytest.skip("psutil not available")

"""
Example: Event Recorder Usage

Demonstrates how to use the EventRecorder to record dispatcher events
to the Task Registry with automatic fallback to local logging.
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import EventType
from necrocode.dispatcher.event_recorder import EventRecorder


def main():
    """Demonstrate EventRecorder usage."""
    
    # Create temporary directory for this example
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Initialize Task Registry
        registry_dir = temp_dir / "registry"
        task_registry = TaskRegistry(registry_dir=str(registry_dir))
        print(f"\nInitialized Task Registry at: {registry_dir}")
        
        # Initialize Event Recorder
        fallback_dir = temp_dir / "fallback_logs"
        event_recorder = EventRecorder(
            task_registry=task_registry,
            fallback_log_dir=fallback_dir
        )
        print(f"Initialized Event Recorder with fallback at: {fallback_dir}")
        
        # Example 1: Record task assignment
        print("\n" + "="*60)
        print("Example 1: Recording Task Assignment")
        print("="*60)
        
        success = event_recorder.record_task_assigned(
            spec_name="chat-app",
            task_id="1.1",
            runner_id="runner-abc123",
            slot_id="slot-001",
            pool_name="local"
        )
        print(f"Task assigned event recorded: {success}")
        
        # Example 2: Record runner started
        print("\n" + "="*60)
        print("Example 2: Recording Runner Started")
        print("="*60)
        
        success = event_recorder.record_runner_started(
            spec_name="chat-app",
            task_id="1.1",
            runner_id="runner-abc123",
            slot_id="slot-001",
            pool_name="local",
            pid=12345  # Local process
        )
        print(f"Runner started event recorded: {success}")
        
        # Example 3: Record successful completion
        print("\n" + "="*60)
        print("Example 3: Recording Successful Completion")
        print("="*60)
        
        # Record runner finished
        success = event_recorder.record_runner_finished(
            spec_name="chat-app",
            task_id="1.1",
            runner_id="runner-abc123",
            slot_id="slot-001",
            success=True,
            execution_time_seconds=45.5
        )
        print(f"Runner finished event recorded: {success}")
        
        # Record task completed
        success = event_recorder.record_task_completed(
            spec_name="chat-app",
            task_id="1.1",
            runner_id="runner-abc123",
            execution_time_seconds=45.5
        )
        print(f"Task completed event recorded: {success}")
        
        # Example 4: Record task failure
        print("\n" + "="*60)
        print("Example 4: Recording Task Failure")
        print("="*60)
        
        # Simulate a failed task
        success = event_recorder.record_task_assigned(
            spec_name="chat-app",
            task_id="1.2",
            runner_id="runner-def456",
            slot_id="slot-002",
            pool_name="docker"
        )
        
        success = event_recorder.record_runner_started(
            spec_name="chat-app",
            task_id="1.2",
            runner_id="runner-def456",
            slot_id="slot-002",
            pool_name="docker",
            container_id="container-xyz"
        )
        
        # Record failure
        success = event_recorder.record_runner_finished(
            spec_name="chat-app",
            task_id="1.2",
            runner_id="runner-def456",
            slot_id="slot-002",
            success=False,
            execution_time_seconds=10.0,
            failure_reason="timeout"
        )
        print(f"Runner finished (failed) event recorded: {success}")
        
        success = event_recorder.record_task_failed(
            spec_name="chat-app",
            task_id="1.2",
            runner_id="runner-def456",
            failure_reason="timeout",
            retry_count=2
        )
        print(f"Task failed event recorded: {success}")
        
        # Example 5: View recorded events
        print("\n" + "="*60)
        print("Example 5: Viewing Recorded Events")
        print("="*60)
        
        # Get events for task 1.1
        events_1_1 = task_registry.event_store.get_events_by_task("chat-app", "1.1")
        print(f"\nEvents for task 1.1: {len(events_1_1)}")
        for event in events_1_1:
            print(f"  - {event.event_type.value} at {event.timestamp.isoformat()}")
            print(f"    Details: {event.details}")
        
        # Get events for task 1.2
        events_1_2 = task_registry.event_store.get_events_by_task("chat-app", "1.2")
        print(f"\nEvents for task 1.2: {len(events_1_2)}")
        for event in events_1_2:
            print(f"  - {event.event_type.value} at {event.timestamp.isoformat()}")
            print(f"    Details: {event.details}")
        
        # Example 6: Event recording statistics
        print("\n" + "="*60)
        print("Example 6: Event Recording Statistics")
        print("="*60)
        
        stats = event_recorder.get_statistics()
        print(f"\nTotal events recorded: {stats['total_events']}")
        print(f"Failed events: {stats['failed_events']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        
        # Example 7: Fallback logging demonstration
        print("\n" + "="*60)
        print("Example 7: Fallback Logging (Simulated Failure)")
        print("="*60)
        
        # Create a recorder with broken Task Registry
        broken_registry = TaskRegistry(registry_dir="/invalid/path")
        fallback_recorder = EventRecorder(
            task_registry=broken_registry,
            fallback_log_dir=fallback_dir
        )
        
        # Try to record event (will fail and use fallback)
        success = fallback_recorder.record_task_assigned(
            spec_name="test-spec",
            task_id="2.1",
            runner_id="runner-ghi789",
            slot_id="slot-003",
            pool_name="k8s"
        )
        print(f"Event recorded to Task Registry: {success}")
        print(f"Event written to fallback log: {not success}")
        
        # Check fallback log
        fallback_file = fallback_dir / "test-spec_events.jsonl"
        if fallback_file.exists():
            print(f"\nFallback log created at: {fallback_file}")
            with open(fallback_file, 'r') as f:
                lines = f.readlines()
            print(f"Fallback log contains {len(lines)} event(s)")
        
        # Example 8: Recording with custom timestamps
        print("\n" + "="*60)
        print("Example 8: Recording with Custom Timestamps")
        print("="*60)
        
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        success = event_recorder.record_task_assigned(
            spec_name="chat-app",
            task_id="1.3",
            runner_id="runner-jkl012",
            slot_id="slot-004",
            pool_name="local",
            timestamp=custom_time
        )
        print(f"Event recorded with custom timestamp: {success}")
        
        events = task_registry.event_store.get_events_by_task("chat-app", "1.3")
        if events:
            print(f"Event timestamp: {events[0].timestamp.isoformat()}")
        
        print("\n" + "="*60)
        print("Example completed successfully!")
        print("="*60)
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    main()

"""
Example demonstrating timeout and resource monitoring in Agent Runner.

This example shows how to:
1. Configure timeout limits
2. Configure resource limits (memory, CPU)
3. Monitor resource usage during execution
4. Track LLM and external service call times
5. Handle timeout and resource limit errors

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 16.3
"""

import logging
import time
from pathlib import Path

from necrocode.agent_runner import (
    ExecutionMonitor,
    ResourceMonitor,
    ResourceUsage,
    RunnerConfig,
    RunnerOrchestrator,
    ServiceCallTracker,
    TaskContext,
    TimeoutManager,
)
from necrocode.agent_runner.exceptions import ResourceLimitError, TimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def example_timeout_manager():
    """
    Example 1: Using TimeoutManager directly.
    
    Demonstrates basic timeout functionality.
    """
    print("\n" + "=" * 60)
    print("Example 1: TimeoutManager")
    print("=" * 60)
    
    # Create timeout manager with 5 second timeout
    timeout_mgr = TimeoutManager(timeout_seconds=5)
    
    # Start the timer
    timeout_mgr.start()
    print(f"Timer started with {timeout_mgr.timeout_seconds}s timeout")
    
    # Simulate work
    for i in range(10):
        time.sleep(1)
        
        elapsed = timeout_mgr.get_elapsed_seconds()
        remaining = timeout_mgr.get_remaining_seconds()
        
        print(f"  Step {i+1}: Elapsed={elapsed:.1f}s, Remaining={remaining:.1f}s")
        
        try:
            # Check if timeout reached
            timeout_mgr.check_timeout()
        except TimeoutError as e:
            print(f"  ❌ Timeout reached: {e}")
            break
    
    # Stop the timer
    timeout_mgr.stop()
    print("Timer stopped")


def example_resource_monitor():
    """
    Example 2: Using ResourceMonitor directly.
    
    Demonstrates resource usage monitoring and limit enforcement.
    """
    print("\n" + "=" * 60)
    print("Example 2: ResourceMonitor")
    print("=" * 60)
    
    try:
        # Create resource monitor with limits
        resource_mon = ResourceMonitor(
            max_memory_mb=500,  # 500 MB limit
            max_cpu_percent=80,  # 80% CPU limit
            monitoring_interval=0.5  # Check every 0.5 seconds
        )
        
        print(f"Resource monitor created:")
        print(f"  Max memory: {resource_mon.max_memory_mb}MB")
        print(f"  Max CPU: {resource_mon.max_cpu_percent}%")
        
        # Start monitoring
        resource_mon.start()
        print("Monitoring started...")
        
        # Simulate work
        for i in range(10):
            time.sleep(1)
            
            # Get current usage
            current = resource_mon.get_current_usage()
            if current:
                print(
                    f"  Step {i+1}: "
                    f"Memory={current.memory_mb:.1f}MB "
                    f"({current.memory_percent:.1f}%), "
                    f"CPU={current.cpu_percent:.1f}%"
                )
            
            try:
                # Check if limits exceeded
                resource_mon.check_limits()
            except ResourceLimitError as e:
                print(f"  ❌ Resource limit exceeded: {e}")
                break
        
        # Stop monitoring
        resource_mon.stop()
        
        # Print summary
        print("\nResource Usage Summary:")
        summary = resource_mon.get_usage_summary()
        
        if summary["current"]:
            current = summary["current"]
            print(
                f"  Current: Memory={current['memory_mb']:.1f}MB, "
                f"CPU={current['cpu_percent']:.1f}%"
            )
        
        if summary["peak"]:
            peak = summary["peak"]
            print(
                f"  Peak: Memory={peak['memory_mb']:.1f}MB, "
                f"CPU={peak['cpu_percent']:.1f}%"
            )
        
        if summary["average"]:
            avg = summary["average"]
            print(
                f"  Average: Memory={avg['memory_mb']:.1f}MB, "
                f"CPU={avg['cpu_percent']:.1f}%"
            )
        
        print(f"  Samples: {summary['sample_count']}")
        
    except ImportError as e:
        print(f"⚠️  Resource monitoring not available: {e}")
        print("   Install psutil: pip install psutil")


def example_execution_monitor():
    """
    Example 3: Using ExecutionMonitor (combined timeout + resources).
    
    Demonstrates unified monitoring interface.
    """
    print("\n" + "=" * 60)
    print("Example 3: ExecutionMonitor (Combined)")
    print("=" * 60)
    
    try:
        # Create execution monitor with both timeout and resource limits
        exec_mon = ExecutionMonitor(
            timeout_seconds=10,
            max_memory_mb=500,
            max_cpu_percent=80,
            monitoring_interval=0.5
        )
        
        print("Execution monitor created with:")
        print(f"  Timeout: {exec_mon.timeout_manager.timeout_seconds}s")
        if exec_mon.resource_monitor:
            print(f"  Max memory: {exec_mon.resource_monitor.max_memory_mb}MB")
            print(f"  Max CPU: {exec_mon.resource_monitor.max_cpu_percent}%")
        
        # Start monitoring
        exec_mon.start()
        print("Monitoring started...")
        
        # Simulate work
        for i in range(15):
            time.sleep(1)
            
            # Get status
            status = exec_mon.get_status()
            
            print(
                f"  Step {i+1}: "
                f"Elapsed={status['elapsed_seconds']:.1f}s, "
                f"Remaining={status['remaining_seconds']:.1f}s"
            )
            
            if "resource_usage" in status and status["resource_usage"]["current"]:
                current = status["resource_usage"]["current"]
                print(
                    f"           "
                    f"Memory={current['memory_mb']:.1f}MB, "
                    f"CPU={current['cpu_percent']:.1f}%"
                )
            
            try:
                # Check all limits
                exec_mon.check()
            except (TimeoutError, ResourceLimitError) as e:
                print(f"  ❌ Limit exceeded: {e}")
                break
        
        # Stop monitoring
        exec_mon.stop()
        print("Monitoring stopped")
        
    except ImportError as e:
        print(f"⚠️  Resource monitoring not available: {e}")
        print("   Install psutil: pip install psutil")


def example_runner_with_limits():
    """
    Example 4: RunnerOrchestrator with timeout and resource limits.
    
    Demonstrates how limits are enforced during actual task execution.
    """
    print("\n" + "=" * 60)
    print("Example 4: RunnerOrchestrator with Limits")
    print("=" * 60)
    
    # Create config with limits
    config = RunnerConfig(
        default_timeout_seconds=30,  # 30 second timeout
        max_memory_mb=1000,  # 1 GB memory limit
        max_cpu_percent=90,  # 90% CPU limit
        log_level="INFO",
    )
    
    print("Runner configuration:")
    print(f"  Timeout: {config.default_timeout_seconds}s")
    print(f"  Max memory: {config.max_memory_mb}MB")
    print(f"  Max CPU: {config.max_cpu_percent}%")
    
    # Create orchestrator
    orchestrator = RunnerOrchestrator(config=config)
    print(f"Runner created: {orchestrator.runner_id}")
    
    # Note: Actual task execution would require a real workspace
    # This example just shows the configuration
    print("\nNote: Limits will be enforced during task execution")
    print("      - Timeout will interrupt long-running tasks")
    print("      - Resource limits will abort tasks exceeding memory/CPU")


def example_timeout_callback():
    """
    Example 5: TimeoutManager with callback.
    
    Demonstrates custom timeout handling.
    """
    print("\n" + "=" * 60)
    print("Example 5: Timeout with Callback")
    print("=" * 60)
    
    def on_timeout():
        """Custom callback when timeout occurs."""
        print("  ⚠️  Custom timeout handler invoked!")
        print("  ⚠️  Performing cleanup...")
    
    # Create timeout manager with callback
    timeout_mgr = TimeoutManager(timeout_seconds=3)
    
    # Start with callback
    timeout_mgr.start(callback=on_timeout)
    print(f"Timer started with {timeout_mgr.timeout_seconds}s timeout and callback")
    
    # Simulate work that exceeds timeout
    for i in range(10):
        time.sleep(1)
        
        if timeout_mgr.timed_out:
            print(f"  Step {i+1}: Timeout detected, stopping work")
            break
        
        print(f"  Step {i+1}: Working...")
    
    timeout_mgr.stop()


def example_service_call_tracking():
    """
    Example 6: ServiceCallTracker for LLM and external service monitoring.
    
    Demonstrates tracking service call times and generating statistics.
    """
    print("\n" + "=" * 60)
    print("Example 6: Service Call Tracking")
    print("=" * 60)
    
    # Create service call tracker
    tracker = ServiceCallTracker()
    print("Service call tracker created")
    
    # Simulate LLM calls
    print("\nSimulating LLM calls...")
    tracker.record_call(
        service_name="openai",
        operation="generate_code",
        duration_seconds=2.5,
        success=True,
        metadata={"tokens_used": 1500, "model": "gpt-4"}
    )
    print("  ✓ Recorded OpenAI call: 2.5s, 1500 tokens")
    
    time.sleep(0.1)
    
    tracker.record_call(
        service_name="openai",
        operation="generate_code",
        duration_seconds=3.2,
        success=True,
        metadata={"tokens_used": 2000, "model": "gpt-4"}
    )
    print("  ✓ Recorded OpenAI call: 3.2s, 2000 tokens")
    
    # Simulate external service calls
    print("\nSimulating external service calls...")
    tracker.record_call(
        service_name="task_registry",
        operation="update_task_status",
        duration_seconds=0.5,
        success=True
    )
    print("  ✓ Recorded Task Registry call: 0.5s")
    
    tracker.record_call(
        service_name="repo_pool",
        operation="allocate_slot",
        duration_seconds=0.8,
        success=True
    )
    print("  ✓ Recorded Repo Pool call: 0.8s")
    
    tracker.record_call(
        service_name="artifact_store",
        operation="upload",
        duration_seconds=1.2,
        success=True,
        metadata={"size_bytes": 1024000}
    )
    print("  ✓ Recorded Artifact Store call: 1.2s")
    
    # Simulate a failed call
    tracker.record_call(
        service_name="task_registry",
        operation="add_event",
        duration_seconds=0.3,
        success=False,
        error="Connection timeout"
    )
    print("  ✗ Recorded failed Task Registry call: 0.3s")
    
    # Get statistics
    print("\n" + "-" * 60)
    print("LLM Statistics:")
    print("-" * 60)
    llm_stats = tracker.get_llm_statistics()
    print(f"  Total calls: {llm_stats['total_calls']}")
    print(f"  Total duration: {llm_stats['total_duration_seconds']:.2f}s")
    print(f"  Average duration: {llm_stats['average_duration_seconds']:.2f}s")
    print(f"  Total tokens used: {llm_stats['total_tokens_used']}")
    
    print("\n" + "-" * 60)
    print("External Service Statistics:")
    print("-" * 60)
    ext_stats = tracker.get_external_service_statistics()
    print(f"  Total calls: {ext_stats['total_calls']}")
    print(f"  Total duration: {ext_stats['total_duration_seconds']:.2f}s")
    print(f"  Average duration: {ext_stats['average_duration_seconds']:.2f}s")
    
    print("\n  By service:")
    for service_name, stats in ext_stats['by_service'].items():
        print(f"    {service_name}:")
        print(f"      Calls: {stats['total_calls']}")
        print(f"      Duration: {stats['total_duration_seconds']:.2f}s")
        print(f"      Average: {stats['average_duration_seconds']:.2f}s")
    
    print("\n" + "-" * 60)
    print("All Service Statistics:")
    print("-" * 60)
    all_stats = tracker.get_service_statistics()
    print(f"  Total calls: {all_stats['total_calls']}")
    print(f"  Successful: {all_stats['successful_calls']}")
    print(f"  Failed: {all_stats['failed_calls']}")
    print(f"  Total duration: {all_stats['total_duration_seconds']:.2f}s")


def example_execution_monitor_with_service_tracking():
    """
    Example 7: ExecutionMonitor with service call tracking.
    
    Demonstrates unified monitoring with service call tracking.
    """
    print("\n" + "=" * 60)
    print("Example 7: ExecutionMonitor with Service Tracking")
    print("=" * 60)
    
    # Create execution monitor with service tracking
    exec_mon = ExecutionMonitor(
        timeout_seconds=30,
        max_memory_mb=500,
        track_service_calls=True
    )
    
    print("Execution monitor created with service call tracking")
    
    # Start monitoring
    exec_mon.start()
    print("Monitoring started...")
    
    # Simulate work with service calls
    print("\nSimulating task execution with service calls...")
    
    # LLM call
    time.sleep(0.5)
    exec_mon.record_service_call(
        service_name="openai",
        operation="generate_code",
        duration_seconds=2.5,
        success=True,
        metadata={"tokens_used": 1500}
    )
    print("  ✓ LLM call completed: 2.5s")
    
    # External service calls
    time.sleep(0.2)
    exec_mon.record_service_call(
        service_name="task_registry",
        operation="update_status",
        duration_seconds=0.3,
        success=True
    )
    print("  ✓ Task Registry call completed: 0.3s")
    
    time.sleep(0.2)
    exec_mon.record_service_call(
        service_name="artifact_store",
        operation="upload",
        duration_seconds=1.0,
        success=True
    )
    print("  ✓ Artifact Store call completed: 1.0s")
    
    # Get comprehensive status
    status = exec_mon.get_status()
    
    print("\n" + "-" * 60)
    print("Execution Status:")
    print("-" * 60)
    print(f"  Elapsed: {status['elapsed_seconds']:.2f}s")
    print(f"  Remaining: {status['remaining_seconds']:.2f}s")
    
    if "service_calls" in status:
        print("\n  Service Calls:")
        sc = status["service_calls"]
        
        if "llm" in sc:
            print(f"    LLM calls: {sc['llm']['total_calls']}")
            print(f"    LLM duration: {sc['llm']['total_duration_seconds']:.2f}s")
            print(f"    LLM tokens: {sc['llm']['total_tokens_used']}")
        
        if "external_services" in sc:
            print(f"    External calls: {sc['external_services']['total_calls']}")
            print(f"    External duration: {sc['external_services']['total_duration_seconds']:.2f}s")
    
    # Stop monitoring
    exec_mon.stop()
    print("\nMonitoring stopped")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Agent Runner - Timeout and Resource Monitoring Examples")
    print("=" * 60)
    
    try:
        # Example 1: Basic timeout
        example_timeout_manager()
        
        # Example 2: Resource monitoring
        example_resource_monitor()
        
        # Example 3: Combined monitoring
        example_execution_monitor()
        
        # Example 4: Runner with limits
        example_runner_with_limits()
        
        # Example 5: Timeout callback
        example_timeout_callback()
        
        # Example 6: Service call tracking
        example_service_call_tracking()
        
        # Example 7: Execution monitor with service tracking
        example_execution_monitor_with_service_tracking()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()

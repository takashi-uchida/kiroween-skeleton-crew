"""
Example demonstrating timeout and resource monitoring in Agent Runner.

This example shows how to:
1. Configure timeout limits
2. Configure resource limits (memory, CPU)
3. Monitor resource usage during execution
4. Handle timeout and resource limit errors

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
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
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()

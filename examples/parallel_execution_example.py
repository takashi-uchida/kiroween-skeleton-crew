"""
Example demonstrating parallel execution support in Agent Runner.

This example shows how to:
1. Configure parallel execution with max runners limit
2. Use ParallelCoordinator to track concurrent runners
3. Detect resource conflicts between runners
4. Record parallel execution metrics

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

import time
from pathlib import Path
from threading import Thread

from necrocode.agent_runner import (
    ParallelCoordinator,
    ParallelExecutionContext,
    RunnerConfig,
    RunnerOrchestrator,
    TaskContext,
)


def simulate_runner(
    coordinator: ParallelCoordinator,
    runner_id: str,
    task_id: str,
    workspace_path: Path,
    duration: float = 5.0,
):
    """
    Simulate a runner instance executing a task.
    
    Args:
        coordinator: Parallel coordinator
        runner_id: Runner ID
        task_id: Task ID
        workspace_path: Workspace path
        duration: Simulated execution duration
    """
    print(f"[{runner_id}] Starting task {task_id}")
    
    try:
        # Register with coordinator
        with ParallelExecutionContext(
            coordinator=coordinator,
            runner_id=runner_id,
            task_id=task_id,
            spec_name="example-spec",
            workspace_path=workspace_path,
        ) as context:
            print(f"[{runner_id}] Registered successfully")
            
            # Get concurrent count
            concurrent = coordinator.get_concurrent_count()
            print(f"[{runner_id}] Concurrent runners: {concurrent}")
            
            # Simulate work
            for i in range(int(duration)):
                time.sleep(1)
                context.update_heartbeat_if_needed()
                print(f"[{runner_id}] Working... ({i+1}/{int(duration)}s)")
            
            print(f"[{runner_id}] Task completed")
            
    except RuntimeError as e:
        print(f"[{runner_id}] Failed to register: {e}")


def example_basic_parallel_coordination():
    """
    Example 1: Basic parallel coordination with max runners limit.
    
    Demonstrates:
    - Setting max parallel runners limit
    - Automatic registration/unregistration
    - Concurrent runner tracking
    """
    print("=" * 60)
    print("Example 1: Basic Parallel Coordination")
    print("=" * 60)
    
    # Create coordinator with max 3 parallel runners
    coordinator = ParallelCoordinator(max_parallel_runners=3)
    
    # Create workspace paths
    workspaces = [
        Path(f"/tmp/workspace-{i}") for i in range(5)
    ]
    
    # Start 5 runners (only 3 will run concurrently)
    threads = []
    for i in range(5):
        thread = Thread(
            target=simulate_runner,
            args=(
                coordinator,
                f"runner-{i}",
                f"task-{i}",
                workspaces[i],
                3.0,  # 3 seconds
            )
        )
        thread.start()
        threads.append(thread)
        time.sleep(0.5)  # Stagger starts
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    # Check final status
    status = coordinator.get_status()
    print(f"\nFinal status: {status['active_runners']} active runners")
    print()


def example_resource_conflict_detection():
    """
    Example 2: Resource conflict detection.
    
    Demonstrates:
    - Detecting file conflicts
    - Detecting branch conflicts
    - Recording conflict metrics
    """
    print("=" * 60)
    print("Example 2: Resource Conflict Detection")
    print("=" * 60)
    
    coordinator = ParallelCoordinator()
    
    # Register first runner
    workspace1 = Path("/tmp/workspace-1")
    success = coordinator.register_runner(
        runner_id="runner-1",
        task_id="task-1",
        spec_name="example-spec",
        workspace_path=workspace1,
    )
    print(f"Runner 1 registered: {success}")
    
    # Update resources for runner 1
    coordinator.update_resources(
        runner_id="runner-1",
        files=["src/main.py", "src/utils.py"],
        branches=["feature/task-1"],
    )
    print("Runner 1 resources: src/main.py, src/utils.py, feature/task-1")
    
    # Register second runner
    workspace2 = Path("/tmp/workspace-2")
    success = coordinator.register_runner(
        runner_id="runner-2",
        task_id="task-2",
        spec_name="example-spec",
        workspace_path=workspace2,
    )
    print(f"Runner 2 registered: {success}")
    
    # Check for conflicts with runner 1's resources
    conflicts = coordinator.detect_conflicts(
        runner_id="runner-2",
        files=["src/main.py", "src/config.py"],  # main.py conflicts
        branches=["feature/task-2"],  # No conflict
    )
    
    print(f"\nConflicts detected: {len(conflicts)}")
    for conflict in conflicts:
        print(f"  - {conflict}")
    
    # Cleanup
    coordinator.unregister_runner("runner-1")
    coordinator.unregister_runner("runner-2")
    print()


def example_wait_time_estimation():
    """
    Example 3: Wait time estimation.
    
    Demonstrates:
    - Estimating wait time when at capacity
    - Recording wait time metrics
    """
    print("=" * 60)
    print("Example 3: Wait Time Estimation")
    print("=" * 60)
    
    # Create coordinator with max 2 runners
    coordinator = ParallelCoordinator(max_parallel_runners=2)
    
    # Register 2 runners (at capacity)
    for i in range(2):
        workspace = Path(f"/tmp/workspace-{i}")
        coordinator.register_runner(
            runner_id=f"runner-{i}",
            task_id=f"task-{i}",
            spec_name="example-spec",
            workspace_path=workspace,
        )
    
    status = coordinator.get_status()
    print(f"Active runners: {status['active_runners']}/{status['max_parallel_runners']}")
    
    # Check wait time for new runner
    wait_time = coordinator.get_wait_time()
    print(f"Estimated wait time: {wait_time:.0f}s")
    
    # Cleanup
    for i in range(2):
        coordinator.unregister_runner(f"runner-{i}")
    print()


def example_runner_orchestrator_with_parallel():
    """
    Example 4: RunnerOrchestrator with parallel execution.
    
    Demonstrates:
    - Configuring RunnerOrchestrator with max parallel runners
    - Automatic parallel coordination during task execution
    - Metrics collection for parallel execution
    """
    print("=" * 60)
    print("Example 4: RunnerOrchestrator with Parallel Execution")
    print("=" * 60)
    
    # Create config with max parallel runners
    config = RunnerConfig(
        max_parallel_runners=3,
        default_timeout_seconds=60,
    )
    
    # Create orchestrator
    orchestrator = RunnerOrchestrator(config=config)
    
    print(f"Runner ID: {orchestrator.runner_id}")
    print(f"Max parallel runners: {config.max_parallel_runners}")
    
    if orchestrator.parallel_coordinator:
        status = orchestrator.parallel_coordinator.get_status()
        print(f"Current active runners: {status['active_runners']}")
    
    print("\nNote: Actual task execution would require a valid TaskContext")
    print("      and workspace setup. This example shows configuration only.")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("PARALLEL EXECUTION EXAMPLES")
    print("=" * 60 + "\n")
    
    # Run examples
    example_basic_parallel_coordination()
    example_resource_conflict_detection()
    example_wait_time_estimation()
    example_runner_orchestrator_with_parallel()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

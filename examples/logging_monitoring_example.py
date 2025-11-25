"""
Example demonstrating logging and monitoring features of Agent Runner.

This example shows how to:
1. Configure structured logging
2. Collect execution metrics
3. Start a health check server
4. Monitor task execution

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from necrocode.agent_runner import (
    ExecutionMetrics,
    HealthCheckServer,
    MetricsCollector,
    MetricsReporter,
    RunnerConfig,
    RunnerOrchestrator,
    TaskContext,
    create_health_check_server,
    get_runner_logger,
    setup_logging,
)


def example_structured_logging():
    """
    Example 1: Structured logging with JSON format.
    
    Demonstrates:
    - Setting up structured logging
    - Using runner logger adapter
    - Automatic context injection
    """
    print("\n" + "=" * 60)
    print("Example 1: Structured Logging")
    print("=" * 60 + "\n")
    
    # Setup structured logging
    setup_logging(
        log_level="INFO",
        structured=True,
        log_file=None  # Console only for demo
    )
    
    # Get runner logger with context
    logger = get_runner_logger(
        runner_id="runner-demo-001",
        task_id="task-1.1",
        spec_name="example-spec"
    )
    
    # Log messages - context is automatically added
    logger.info("Starting task execution")
    logger.info("Workspace prepared", extra={"workspace_path": "/tmp/workspace"})
    logger.warning("Test failed", extra={"test_name": "test_auth", "exit_code": 1})
    logger.error("Implementation failed", extra={"error": "Syntax error"})
    
    # Update context for new task
    logger.update_context(task_id="task-1.2", spec_name="example-spec")
    logger.info("Starting next task")
    
    print("\nStructured logs are output in JSON format with automatic context.")


def example_metrics_collection():
    """
    Example 2: Execution metrics collection.
    
    Demonstrates:
    - Creating metrics collector
    - Recording phase timings
    - Sampling resource usage
    - Recording implementation/test metrics
    - Finalizing and reporting metrics
    """
    print("\n" + "=" * 60)
    print("Example 2: Metrics Collection")
    print("=" * 60 + "\n")
    
    # Create metrics collector
    collector = MetricsCollector(
        runner_id="runner-demo-001",
        task_id="task-1.1",
        spec_name="example-spec"
    )
    
    # Simulate task execution with phase timing
    print("Simulating task execution...")
    
    # Phase 1: Workspace preparation
    collector.start_phase("workspace_preparation")
    time.sleep(0.5)
    collector.sample_resources()
    collector.end_phase("workspace_preparation")
    
    # Phase 2: Implementation
    collector.start_phase("implementation")
    time.sleep(1.0)
    collector.sample_resources()
    collector.record_implementation(
        files_changed=5,
        lines_added=150,
        lines_removed=30
    )
    collector.end_phase("implementation")
    
    # Phase 3: Testing
    collector.start_phase("testing")
    time.sleep(0.8)
    collector.sample_resources()
    collector.record_tests(
        tests_run=10,
        tests_passed=9,
        tests_failed=1
    )
    collector.end_phase("testing")
    
    # Phase 4: Artifact upload
    collector.start_phase("artifact_upload")
    time.sleep(0.3)
    collector.sample_resources()
    collector.record_artifacts(
        artifacts_uploaded=3,
        total_size_bytes=1024 * 512  # 512 KB
    )
    collector.end_phase("artifact_upload")
    
    # Finalize metrics
    metrics = collector.finalize()
    
    # Report metrics
    reporter = MetricsReporter()
    reporter.report(metrics)
    
    print("\nMetrics collected and reported successfully.")
    
    return metrics


def example_health_check():
    """
    Example 3: Health check server.
    
    Demonstrates:
    - Creating health check server
    - Starting server in background
    - Updating health status
    - Querying health endpoints
    """
    print("\n" + "=" * 60)
    print("Example 3: Health Check Server")
    print("=" * 60 + "\n")
    
    # Create health check server
    health_server = create_health_check_server(
        port=8080,
        host="127.0.0.1",
        runner_id="runner-demo-001"
    )
    
    try:
        # Start server
        health_server.start()
        print(f"Health check server started on http://127.0.0.1:8080")
        print("Endpoints:")
        print("  - GET /health   - Health check")
        print("  - GET /ready    - Readiness check")
        print()
        
        # Update status - idle
        health_server.update_status(
            healthy=True,
            runner_state="idle"
        )
        print("Status: idle")
        time.sleep(1)
        
        # Update status - running
        health_server.update_status(
            healthy=True,
            runner_state="running",
            current_task_id="task-1.1",
            current_spec_name="example-spec"
        )
        print("Status: running task-1.1")
        time.sleep(1)
        
        # Update status - completed
        health_server.update_status(
            healthy=True,
            runner_state="completed"
        )
        print("Status: completed")
        time.sleep(1)
        
        print("\nYou can query the health endpoints:")
        print("  curl http://127.0.0.1:8080/health")
        print("  curl http://127.0.0.1:8080/ready")
        print("\nPress Ctrl+C to stop the server...")
        
        # Keep server running for demo
        time.sleep(5)
        
    finally:
        # Stop server
        health_server.stop()
        print("\nHealth check server stopped.")


def example_integrated_monitoring():
    """
    Example 4: Integrated monitoring with RunnerOrchestrator.
    
    Demonstrates:
    - Configuring runner with logging and monitoring
    - Automatic metrics collection during execution
    - Health check integration
    """
    print("\n" + "=" * 60)
    print("Example 4: Integrated Monitoring")
    print("=" * 60 + "\n")
    
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a mock workspace
        workspace_path = tmpdir_path / "workspace"
        workspace_path.mkdir()
        
        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=workspace_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=workspace_path,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=workspace_path,
            capture_output=True
        )
        
        # Create initial commit
        (workspace_path / "README.md").write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=workspace_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace_path,
            capture_output=True
        )
        
        # Configure runner with logging and monitoring
        config = RunnerConfig(
            log_level="INFO",
            structured_logging=True,
            log_file=tmpdir_path / "runner.log",
            enable_health_check=True,
            health_check_port=8081,
            metrics_enabled=True,
        )
        
        # Setup logging
        setup_logging(
            log_level=config.log_level,
            structured=config.structured_logging,
            log_file=config.log_file
        )
        
        # Create orchestrator
        orchestrator = RunnerOrchestrator(config=config)
        
        print(f"Runner ID: {orchestrator.runner_id}")
        print(f"Log file: {config.log_file}")
        print()
        
        # Create task context
        task_context = TaskContext(
            task_id="1.1",
            spec_name="example-spec",
            title="Example task",
            description="This is an example task for demonstration",
            acceptance_criteria=["Task completes successfully"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_path,
            slot_id="slot-1",
            branch_name="feature/task-1.1-example",
            timeout_seconds=60,
        )
        
        print("Task execution would run here with full monitoring:")
        print("  - Structured logging to file and console")
        print("  - Automatic metrics collection")
        print("  - Health check server running")
        print("  - Resource usage monitoring")
        print()
        
        # Note: We don't actually run the task since it requires Kiro integration
        print("(Skipping actual execution in this demo)")
        
        # Show log file contents
        if config.log_file and config.log_file.exists():
            print(f"\nLog file contents ({config.log_file}):")
            print("-" * 60)
            print(config.log_file.read_text())


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("AGENT RUNNER LOGGING AND MONITORING EXAMPLES")
    print("=" * 60)
    
    try:
        # Example 1: Structured logging
        example_structured_logging()
        
        # Example 2: Metrics collection
        metrics = example_metrics_collection()
        
        # Example 3: Health check server
        # Commented out to avoid blocking
        # example_health_check()
        
        # Example 4: Integrated monitoring
        example_integrated_monitoring()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

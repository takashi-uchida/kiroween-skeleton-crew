"""
Example demonstrating RunnerOrchestrator usage.

This example shows how to use the RunnerOrchestrator to execute a task
from start to finish, including workspace preparation, implementation,
testing, and artifact upload.
"""

import logging
from pathlib import Path
from necrocode.agent_runner import (
    RunnerOrchestrator,
    RunnerConfig,
    TaskContext,
    ExecutionMode,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the RunnerOrchestrator example."""
    
    logger.info("=== RunnerOrchestrator Example ===")
    
    # Create runner configuration
    config = RunnerConfig(
        execution_mode=ExecutionMode.LOCAL_PROCESS,
        default_timeout_seconds=1800,
        log_level="INFO",
        structured_logging=True,
        artifact_store_url="file://~/.necrocode/artifacts",
        mask_secrets=True,
    )
    
    # Initialize orchestrator
    orchestrator = RunnerOrchestrator(config=config)
    
    logger.info(f"Initialized orchestrator with ID: {orchestrator.runner_id}")
    logger.info(f"Current state: {orchestrator.state.value}")
    
    # Create task context
    # Note: In a real scenario, this would come from the Dispatcher
    task_context = TaskContext(
        task_id="1.1",
        spec_name="example-feature",
        title="Implement user authentication",
        description="Add JWT-based authentication to the API",
        acceptance_criteria=[
            "POST /api/auth/register creates new user",
            "POST /api/auth/login returns JWT token",
            "Middleware validates JWT on protected routes",
            "Passwords are hashed with bcrypt",
        ],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp/example-workspace"),  # Would be provided by Repo Pool Manager
        slot_id="slot-1",
        branch_name="feature/task-example-feature-1.1-user-auth",
        test_commands=["npm test"],
        fail_fast=True,
        timeout_seconds=1800,
        complexity="medium",
        require_review=False,
    )
    
    logger.info(f"Task context created: {task_context.task_id}")
    logger.info(f"Task: {task_context.title}")
    
    # Note: In a real scenario, you would execute the task here:
    # result = orchestrator.run(task_context)
    #
    # However, this requires:
    # 1. A valid workspace at slot_path
    # 2. Kiro integration for implementation
    # 3. Task Registry for completion reporting
    #
    # For demonstration purposes, we'll just show the setup
    
    logger.info("\n=== Orchestrator Setup Complete ===")
    logger.info("To execute a task, call: orchestrator.run(task_context)")
    logger.info("\nThe orchestrator will:")
    logger.info("  1. Validate task context")
    logger.info("  2. Prepare workspace (git operations)")
    logger.info("  3. Execute task implementation (via Kiro)")
    logger.info("  4. Run tests")
    logger.info("  5. Commit and push changes")
    logger.info("  6. Upload artifacts")
    logger.info("  7. Report completion to Task Registry")
    
    # Show configuration
    logger.info("\n=== Configuration ===")
    logger.info(f"Execution mode: {config.execution_mode.value}")
    logger.info(f"Timeout: {config.default_timeout_seconds}s")
    logger.info(f"Artifact store: {config.artifact_store_url}")
    logger.info(f"Git retry count: {config.git_retry_config.max_retries}")
    logger.info(f"Mask secrets: {config.mask_secrets}")


if __name__ == "__main__":
    main()

"""
Example: RunnerOrchestrator with External Service Integration

This example demonstrates how to configure and use RunnerOrchestrator
with external services (Task Registry, Repo Pool Manager, Artifact Store, LLM).
"""

import os
from pathlib import Path

from necrocode.agent_runner.config import RunnerConfig
from necrocode.agent_runner.models import TaskContext
from necrocode.agent_runner.runner_orchestrator import RunnerOrchestrator


def example_with_external_services():
    """Example: Configure RunnerOrchestrator with external services."""
    
    print("=" * 80)
    print("RunnerOrchestrator with External Services Integration")
    print("=" * 80)
    
    # Configure with external service URLs
    config = RunnerConfig(
        # External service URLs
        task_registry_url="http://localhost:8000",
        repo_pool_url="http://localhost:8001",
        artifact_store_url="http://localhost:8002",
        
        # LLM configuration
        llm_model="gpt-4",
        llm_timeout_seconds=120,
        llm_max_tokens=4000,
        
        # Execution settings
        default_timeout_seconds=1800,
        max_memory_mb=2048,
        max_cpu_percent=80,
        
        # Logging
        log_level="INFO",
        structured_logging=True,
        
        # Security
        mask_secrets=True,
    )
    
    print("\n✓ Configuration created:")
    print(f"  - Task Registry URL: {config.task_registry_url}")
    print(f"  - Repo Pool URL: {config.repo_pool_url}")
    print(f"  - Artifact Store URL: {config.artifact_store_url}")
    print(f"  - LLM Model: {config.llm_model}")
    print(f"  - Timeout: {config.default_timeout_seconds}s")
    print(f"  - Max Memory: {config.max_memory_mb}MB")
    
    # Initialize orchestrator
    # Note: This will attempt to connect to external services
    # In a real scenario, ensure services are running
    try:
        orchestrator = RunnerOrchestrator(config=config)
        print(f"\n✓ RunnerOrchestrator initialized:")
        print(f"  - Runner ID: {orchestrator.runner_id}")
        print(f"  - State: {orchestrator.state.value}")
        print(f"  - Task Registry Client: {'✓' if orchestrator.task_registry_client else '✗'}")
        print(f"  - Repo Pool Client: {'✓' if orchestrator.repo_pool_client else '✗'}")
        print(f"  - Artifact Store Client: {'✓' if orchestrator.artifact_store_client else '✗'}")
        print(f"  - LLM Config: {'✓' if orchestrator.llm_config else '✗'}")
        
    except Exception as e:
        print(f"\n✗ Failed to initialize orchestrator: {e}")
        print("  Note: External services may not be running")


def example_with_legacy_mode():
    """Example: Configure RunnerOrchestrator in legacy mode (no external services)."""
    
    print("\n" + "=" * 80)
    print("RunnerOrchestrator in Legacy Mode (No External Services)")
    print("=" * 80)
    
    # Configure without external services (legacy mode)
    config = RunnerConfig(
        # No external service URLs - will use legacy Task Registry
        task_registry_path=Path.home() / ".necrocode" / "task_registry",
        
        # LLM configuration (still needed for code generation)
        llm_model="gpt-4",
        
        # Execution settings
        default_timeout_seconds=1800,
        log_level="INFO",
    )
    
    print("\n✓ Configuration created (legacy mode):")
    print(f"  - Task Registry Path: {config.task_registry_path}")
    print(f"  - LLM Model: {config.llm_model}")
    print(f"  - External Services: Disabled")
    
    try:
        orchestrator = RunnerOrchestrator(config=config)
        print(f"\n✓ RunnerOrchestrator initialized:")
        print(f"  - Runner ID: {orchestrator.runner_id}")
        print(f"  - State: {orchestrator.state.value}")
        print(f"  - Task Registry Client: {'✓' if orchestrator.task_registry_client else '✗ (using legacy)'}")
        print(f"  - Repo Pool Client: {'✓' if orchestrator.repo_pool_client else '✗ (not configured)'}")
        print(f"  - Artifact Store Client: {'✓' if orchestrator.artifact_store_client else '✗ (using file-based)'}")
        
    except Exception as e:
        print(f"\n✗ Failed to initialize orchestrator: {e}")


def example_task_context():
    """Example: Create a TaskContext for execution."""
    
    print("\n" + "=" * 80)
    print("TaskContext Example")
    print("=" * 80)
    
    # Create a sample task context
    task_context = TaskContext(
        task_id="1.1",
        spec_name="example-feature",
        title="Implement user authentication",
        description="Add JWT-based authentication to the API",
        acceptance_criteria=[
            "POST /api/auth/register creates new user",
            "POST /api/auth/login returns JWT token",
            "Middleware validates JWT on protected routes",
        ],
        dependencies=[],
        required_skill="backend",
        
        # Workspace information
        slot_path=Path("/tmp/workspace/slot1"),
        slot_id="slot-1",
        branch_name="feature/task-1.1-user-auth",
        
        # Test settings
        test_commands=["npm test"],
        fail_fast=True,
        
        # Timeout
        timeout_seconds=1800,
        
        # LLM settings
        related_files=["models/User.js", "package.json"],
        max_tokens=4000,
        
        # Metadata
        metadata={
            "repo_url": "https://github.com/example/repo.git",
            "complexity": "medium",
        }
    )
    
    print("\n✓ TaskContext created:")
    print(f"  - Task ID: {task_context.task_id}")
    print(f"  - Spec: {task_context.spec_name}")
    print(f"  - Title: {task_context.title}")
    print(f"  - Branch: {task_context.branch_name}")
    print(f"  - Acceptance Criteria: {len(task_context.acceptance_criteria)} items")
    print(f"  - Related Files: {task_context.related_files}")
    print(f"  - Repo URL: {task_context.metadata.get('repo_url')}")
    
    return task_context


def example_environment_variables():
    """Example: Show required environment variables."""
    
    print("\n" + "=" * 80)
    print("Required Environment Variables")
    print("=" * 80)
    
    env_vars = {
        "GIT_TOKEN": "GitHub personal access token for Git operations",
        "LLM_API_KEY": "OpenAI API key for code generation",
        "ARTIFACT_STORE_API_KEY": "API key for Artifact Store (optional)",
    }
    
    print("\nEnvironment variables for RunnerOrchestrator:")
    for var, description in env_vars.items():
        value = os.environ.get(var)
        status = "✓ Set" if value else "✗ Not set"
        print(f"  - {var}: {status}")
        print(f"    {description}")


if __name__ == "__main__":
    # Run examples
    example_with_external_services()
    example_with_legacy_mode()
    example_task_context()
    example_environment_variables()
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Set up external services (Task Registry, Repo Pool, Artifact Store)")
    print("2. Configure environment variables (GIT_TOKEN, LLM_API_KEY)")
    print("3. Create a TaskContext with your task details")
    print("4. Call orchestrator.run(task_context) to execute the task")

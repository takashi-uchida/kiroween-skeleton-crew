#!/usr/bin/env python3
"""
Example usage of external service clients.

This example demonstrates how to use the LLMClient, TaskRegistryClient,
RepoPoolClient, and ArtifactStoreClient.
"""

import os
from pathlib import Path

from necrocode.agent_runner.llm_client import LLMClient
from necrocode.agent_runner.task_registry_client import TaskRegistryClient
from necrocode.agent_runner.repo_pool_client import RepoPoolClient
from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.models import LLMConfig


def example_llm_client():
    """Example: Using LLMClient for code generation"""
    print("=" * 60)
    print("LLMClient Example")
    print("=" * 60)
    
    # Configure LLM client
    config = LLMConfig(
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"),
        model="gpt-4",
        timeout_seconds=120,
        max_tokens=4000
    )
    
    client = LLMClient(config)
    
    # Generate code
    prompt = """
    # Task: Create a simple Python function
    
    ## Description
    Create a function that calculates the factorial of a number.
    
    ## Acceptance Criteria
    1. Function should handle positive integers
    2. Function should return 1 for input 0
    3. Function should raise ValueError for negative numbers
    
    ## Instructions
    Generate the code changes in JSON format:
    {
      "code_changes": [
        {
          "file_path": "math_utils.py",
          "operation": "create",
          "content": "# file content here"
        }
      ],
      "explanation": "Brief explanation"
    }
    """
    
    try:
        # Note: This will fail without a valid API key
        # response = client.generate_code(
        #     prompt=prompt,
        #     workspace_path=Path("/tmp/workspace"),
        #     max_tokens=2000
        # )
        # print(f"Generated {len(response.code_changes)} code changes")
        # print(f"Model: {response.model}")
        # print(f"Tokens used: {response.tokens_used}")
        print("✓ LLMClient configured successfully")
        print("  (Actual API call commented out - requires valid API key)")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_task_registry_client():
    """Example: Using TaskRegistryClient"""
    print("\n" + "=" * 60)
    print("TaskRegistryClient Example")
    print("=" * 60)
    
    # Create client
    client = TaskRegistryClient("http://localhost:8080")
    
    # Check health
    is_healthy = client.health_check()
    print(f"Task Registry health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
    
    # Example operations (commented out - require running service)
    # client.update_task_status("task-123", "in_progress")
    # client.add_event("task-123", "TaskStarted", {"runner_id": "runner-001"})
    # client.add_artifact("task-123", "diff", "s3://bucket/diff.txt", 1024)
    
    print("✓ TaskRegistryClient configured successfully")


def example_repo_pool_client():
    """Example: Using RepoPoolClient"""
    print("\n" + "=" * 60)
    print("RepoPoolClient Example")
    print("=" * 60)
    
    # Create client
    client = RepoPoolClient("http://localhost:8081")
    
    # Check health
    is_healthy = client.health_check()
    print(f"Repo Pool Manager health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
    
    # Example operations (commented out - require running service)
    # slot = client.allocate_slot(
    #     repo_url="https://github.com/user/repo.git",
    #     required_by="task-123"
    # )
    # print(f"Allocated slot: {slot.slot_id} at {slot.slot_path}")
    # 
    # # Do work in the slot...
    # 
    # client.release_slot(slot.slot_id)
    # print(f"Released slot: {slot.slot_id}")
    
    print("✓ RepoPoolClient configured successfully")


def example_artifact_store_client():
    """Example: Using ArtifactStoreClient"""
    print("\n" + "=" * 60)
    print("ArtifactStoreClient Example")
    print("=" * 60)
    
    # Create client
    client = ArtifactStoreClient("http://localhost:8082")
    
    # Check health
    is_healthy = client.health_check()
    print(f"Artifact Store health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
    
    # Example operations (commented out - require running service)
    # # Upload text artifact
    # diff_content = "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,4 @@\n+new line\n"
    # uri = client.upload_text(
    #     artifact_type="diff",
    #     content=diff_content,
    #     metadata={"task_id": "task-123"}
    # )
    # print(f"Uploaded diff to: {uri}")
    # 
    # # Upload binary artifact
    # log_content = b"Log content here..."
    # uri = client.upload(
    #     artifact_type="log",
    #     content=log_content,
    #     metadata={"task_id": "task-123"}
    # )
    # print(f"Uploaded log to: {uri}")
    # 
    # # Download artifact
    # content = client.download_text(uri)
    # print(f"Downloaded content: {content[:50]}...")
    
    print("✓ ArtifactStoreClient configured successfully")


def example_integrated_workflow():
    """Example: Integrated workflow using all clients"""
    print("\n" + "=" * 60)
    print("Integrated Workflow Example")
    print("=" * 60)
    
    # Initialize all clients
    llm_config = LLMConfig(
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"),
        model="gpt-4"
    )
    llm_client = LLMClient(llm_config)
    task_registry = TaskRegistryClient("http://localhost:8080")
    repo_pool = RepoPoolClient("http://localhost:8081")
    artifact_store = ArtifactStoreClient("http://localhost:8082")
    
    print("✓ All clients initialized")
    
    # Simulated workflow (commented out - requires running services)
    # 1. Update task status to in_progress
    # task_registry.update_task_status("task-123", "in_progress")
    # 
    # 2. Allocate workspace slot
    # slot = repo_pool.allocate_slot(
    #     repo_url="https://github.com/user/repo.git",
    #     required_by="task-123"
    # )
    # 
    # 3. Generate code using LLM
    # response = llm_client.generate_code(
    #     prompt="Create a login function...",
    #     workspace_path=slot.slot_path
    # )
    # 
    # 4. Upload artifacts
    # diff_uri = artifact_store.upload_text("diff", "diff content...")
    # log_uri = artifact_store.upload_text("log", "log content...")
    # 
    # 5. Register artifacts with task registry
    # task_registry.add_artifact("task-123", "diff", diff_uri, 1024)
    # task_registry.add_artifact("task-123", "log", log_uri, 2048)
    # 
    # 6. Update task status to done
    # task_registry.update_task_status("task-123", "done")
    # 
    # 7. Release workspace slot
    # repo_pool.release_slot(slot.slot_id)
    
    print("✓ Workflow structure validated")
    print("  (Actual operations commented out - require running services)")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("External Service Clients Examples")
    print("=" * 60)
    print()
    
    example_llm_client()
    example_task_registry_client()
    example_repo_pool_client()
    example_artifact_store_client()
    example_integrated_workflow()
    
    print("\n" + "=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)
    print()
    print("Note: Most operations are commented out as they require:")
    print("  - Valid OpenAI API key (for LLMClient)")
    print("  - Running Task Registry service")
    print("  - Running Repo Pool Manager service")
    print("  - Running Artifact Store service")
    print()


if __name__ == "__main__":
    main()

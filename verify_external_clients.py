#!/usr/bin/env python3
"""
Verification script for external service clients.

This script verifies that all external service clients can be imported
and instantiated correctly.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from necrocode.agent_runner.llm_client import LLMClient
from necrocode.agent_runner.task_registry_client import TaskRegistryClient
from necrocode.agent_runner.repo_pool_client import RepoPoolClient
from necrocode.agent_runner.artifact_store_client import ArtifactStoreClient
from necrocode.agent_runner.models import LLMConfig


def verify_llm_client():
    """Verify LLMClient can be instantiated"""
    print("✓ Verifying LLMClient...")
    config = LLMConfig(
        api_key="test-key",
        model="gpt-4",
        timeout_seconds=120,
        max_tokens=4000
    )
    client = LLMClient(config)
    assert client.config.model == "gpt-4"
    assert client.config.timeout_seconds == 120
    print("  ✓ LLMClient instantiated successfully")


def verify_task_registry_client():
    """Verify TaskRegistryClient can be instantiated"""
    print("✓ Verifying TaskRegistryClient...")
    client = TaskRegistryClient("http://localhost:8080")
    assert client.base_url == "http://localhost:8080"
    assert client.timeout == 30
    print("  ✓ TaskRegistryClient instantiated successfully")


def verify_repo_pool_client():
    """Verify RepoPoolClient can be instantiated"""
    print("✓ Verifying RepoPoolClient...")
    client = RepoPoolClient("http://localhost:8081")
    assert client.base_url == "http://localhost:8081"
    assert client.timeout == 30
    print("  ✓ RepoPoolClient instantiated successfully")


def verify_artifact_store_client():
    """Verify ArtifactStoreClient can be instantiated"""
    print("✓ Verifying ArtifactStoreClient...")
    client = ArtifactStoreClient("http://localhost:8082")
    assert client.base_url == "http://localhost:8082"
    assert client.timeout == 60
    print("  ✓ ArtifactStoreClient instantiated successfully")


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("External Service Clients Verification")
    print("=" * 60)
    print()
    
    try:
        verify_llm_client()
        verify_task_registry_client()
        verify_repo_pool_client()
        verify_artifact_store_client()
        
        print()
        print("=" * 60)
        print("✓ All external service clients verified successfully!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Verification failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

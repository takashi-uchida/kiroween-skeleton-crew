"""
Example: Reviewer Assignment Strategies

This example demonstrates the different reviewer assignment strategies
supported by the Review & PR Service:
- Task type-based assignment
- CODEOWNERS file parsing
- Round-robin distribution
- Load-balanced assignment

Requirements: 8.1, 8.2, 8.3, 8.4
"""

import os
from pathlib import Path
from datetime import datetime

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import (
    PRServiceConfig,
    ReviewerConfig,
    ReviewerStrategy,
    GitHostType,
)
from necrocode.task_registry.models import Task


def example_type_based_assignment():
    """
    Example: Assign reviewers based on task type.
    
    Requirements: 8.1
    """
    print("\n=== Example 1: Type-Based Reviewer Assignment ===\n")
    
    # Configure type-based reviewers
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token=os.getenv("GITHUB_TOKEN", "fake-token-for-demo"),
        repository="owner/repo",
        reviewers=ReviewerConfig(
            enabled=True,
            strategy=ReviewerStrategy.MANUAL,
            type_reviewers={
                "backend": ["alice", "bob"],
                "frontend": ["charlie", "diana"],
                "database": ["eve", "frank"],
            },
            max_reviewers=2,
        )
    )
    
    # Create PR service
    service = PRService(config)
    
    # Create a backend task
    backend_task = Task(
        id="1.1",
        title="Implement REST API",
        description="Create REST API endpoints",
        status="in_progress",
        created_at=datetime.now(),
        metadata={
            "type": "backend",
        }
    )
    
    print(f"Task: {backend_task.title}")
    print(f"Task type: {backend_task.metadata.get('type')}")
    print(f"Expected reviewers: alice, bob")
    print("\nNote: In a real scenario, this would assign reviewers to the PR")


def example_codeowners_assignment():
    """
    Example: Assign reviewers based on CODEOWNERS file.
    
    Requirements: 8.2
    """
    print("\n=== Example 2: CODEOWNERS-Based Assignment ===\n")
    
    # Create a sample CODEOWNERS file
    codeowners_path = Path("/tmp/CODEOWNERS")
    codeowners_content = """
# Backend code
/backend/ @alice @bob
*.py @alice

# Frontend code
/frontend/ @charlie @diana
*.js @charlie
*.tsx @diana

# Database migrations
/migrations/ @eve @frank
*.sql @eve
"""
    
    codeowners_path.write_text(codeowners_content)
    print(f"Created CODEOWNERS file at: {codeowners_path}")
    print(f"Content:\n{codeowners_content}")
    
    # Configure CODEOWNERS strategy
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token=os.getenv("GITHUB_TOKEN", "fake-token-for-demo"),
        repository="owner/repo",
        reviewers=ReviewerConfig(
            enabled=True,
            strategy=ReviewerStrategy.CODEOWNERS,
            codeowners_path=str(codeowners_path),
            max_reviewers=2,
        )
    )
    
    # Create PR service
    service = PRService(config)
    
    # Create a task with file changes
    task = Task(
        id="2.1",
        title="Update backend API",
        description="Modify backend API endpoints",
        status="in_progress",
        created_at=datetime.now(),
        metadata={
            "files": [
                "backend/api/users.py",
                "backend/api/auth.py",
            ]
        }
    )
    
    print(f"\nTask: {task.title}")
    print(f"Modified files: {task.metadata.get('files')}")
    print(f"Expected reviewers: alice, bob (from /backend/ pattern)")
    
    # Parse CODEOWNERS
    codeowners_map = service._parse_codeowners(str(codeowners_path))
    reviewers = service._get_reviewers_from_codeowners(task, codeowners_map)
    print(f"Matched reviewers: {reviewers}")
    
    # Cleanup
    codeowners_path.unlink()


def example_round_robin_assignment():
    """
    Example: Assign reviewers using round-robin strategy.
    
    Requirements: 8.3
    """
    print("\n=== Example 3: Round-Robin Assignment ===\n")
    
    # Configure round-robin strategy
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token=os.getenv("GITHUB_TOKEN", "fake-token-for-demo"),
        repository="owner/repo",
        reviewers=ReviewerConfig(
            enabled=True,
            strategy=ReviewerStrategy.ROUND_ROBIN,
            default_reviewers=["alice", "bob", "charlie", "diana"],
            max_reviewers=2,
        )
    )
    
    # Create PR service
    service = PRService(config)
    
    # Simulate multiple PR assignments
    available_reviewers = ["alice", "bob", "charlie", "diana"]
    
    print(f"Available reviewers: {available_reviewers}")
    print(f"Max reviewers per PR: 2")
    print("\nRound-robin assignments:")
    
    for i in range(5):
        selected = service._select_reviewers_round_robin(
            available_reviewers,
            2,
            "backend"
        )
        print(f"  PR {i+1}: {selected}")
    
    print("\nNote: Reviewers are distributed evenly across PRs")


def example_load_balanced_assignment():
    """
    Example: Assign reviewers using load-balanced strategy.
    
    Requirements: 8.4
    """
    print("\n=== Example 4: Load-Balanced Assignment ===\n")
    
    # Configure load-balanced strategy
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token=os.getenv("GITHUB_TOKEN", "fake-token-for-demo"),
        repository="owner/repo",
        reviewers=ReviewerConfig(
            enabled=True,
            strategy=ReviewerStrategy.LOAD_BALANCED,
            default_reviewers=["alice", "bob", "charlie", "diana"],
            max_reviewers=2,
        )
    )
    
    # Create PR service
    service = PRService(config)
    
    # Simulate initial loads
    service._reviewer_load = {
        "alice": 3,
        "bob": 1,
        "charlie": 2,
        "diana": 0,
    }
    
    available_reviewers = ["alice", "bob", "charlie", "diana"]
    
    print(f"Available reviewers: {available_reviewers}")
    print(f"Current loads: {service._reviewer_load}")
    print(f"Max reviewers per PR: 2")
    print("\nLoad-balanced assignments:")
    
    for i in range(3):
        selected = service._select_reviewers_load_balanced(
            available_reviewers,
            2
        )
        print(f"  PR {i+1}: {selected} (loads: {[service._get_reviewer_load(r) for r in selected]})")
        
        # Simulate assignment
        for reviewer in selected:
            service._increment_reviewer_load(reviewer)
        
        print(f"    Updated loads: {service._reviewer_load}")
    
    print("\nNote: Reviewers with lower workload are prioritized")


def example_combined_strategies():
    """
    Example: Combine multiple reviewer sources with selection strategy.
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    print("\n=== Example 5: Combined Strategies ===\n")
    
    # Configure with multiple sources
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        api_token=os.getenv("GITHUB_TOKEN", "fake-token-for-demo"),
        repository="owner/repo",
        reviewers=ReviewerConfig(
            enabled=True,
            strategy=ReviewerStrategy.LOAD_BALANCED,
            type_reviewers={
                "backend": ["alice", "bob"],
                "frontend": ["charlie", "diana"],
            },
            default_reviewers=["eve", "frank"],
            max_reviewers=2,
        )
    )
    
    # Create PR service
    service = PRService(config)
    
    # Set initial loads
    service._reviewer_load = {
        "alice": 2,
        "bob": 1,
        "charlie": 0,
        "diana": 3,
        "eve": 1,
        "frank": 2,
    }
    
    print("Configuration:")
    print(f"  Type reviewers (backend): {config.reviewers.type_reviewers['backend']}")
    print(f"  Default reviewers: {config.reviewers.default_reviewers}")
    print(f"  Strategy: {config.reviewers.strategy.value}")
    print(f"  Max reviewers: {config.reviewers.max_reviewers}")
    print(f"\nCurrent loads: {service._reviewer_load}")
    
    # Simulate reviewer pool
    all_reviewers = ["alice", "bob", "eve", "frank"]  # backend + default
    
    print(f"\nAvailable reviewers: {all_reviewers}")
    
    selected = service._select_reviewers_load_balanced(all_reviewers, 2)
    print(f"Selected reviewers: {selected}")
    print(f"Selected loads: {[service._get_reviewer_load(r) for r in selected]}")
    
    print("\nNote: Load-balanced strategy selects reviewers with lowest workload")


def main():
    """Run all reviewer assignment examples."""
    print("=" * 70)
    print("Reviewer Assignment Examples")
    print("=" * 70)
    
    example_type_based_assignment()
    example_codeowners_assignment()
    example_round_robin_assignment()
    example_load_balanced_assignment()
    example_combined_strategies()
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

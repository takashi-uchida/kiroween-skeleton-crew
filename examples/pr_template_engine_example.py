"""
Example usage of PRTemplateEngine.

Demonstrates how to generate PR descriptions using templates.
"""

from datetime import datetime
from pathlib import Path

from necrocode.review_pr_service.config import PRServiceConfig, TemplateConfig
from necrocode.review_pr_service.pr_template_engine import PRTemplateEngine
from necrocode.task_registry.models import Task, TaskState, Artifact, ArtifactType


def main():
    """Demonstrate PR template engine usage."""
    
    print("=" * 80)
    print("PR Template Engine Example")
    print("=" * 80)
    
    # Create configuration
    config = PRServiceConfig(
        repository="necrocode/example-repo",
        template=TemplateConfig(
            template_path="templates/pr-template.md",
            include_test_results=True,
            include_artifact_links=True,
            include_execution_logs=True
        )
    )
    
    # Initialize template engine
    engine = PRTemplateEngine(config)
    print("\n✓ Initialized PRTemplateEngine")
    
    # Create a sample task
    task = Task(
        id="2.1",
        title="Implement JWT Authentication",
        description="Add login and register endpoints with JWT token generation and validation.",
        state=TaskState.DONE,
        dependencies=["1.1"],
        required_skill="backend"
    )
    
    # Add sample artifacts
    task.artifacts = [
        Artifact(
            type=ArtifactType.DIFF,
            uri="https://artifact-store.example.com/diffs/task-2.1.diff",
            size_bytes=4096,
            metadata={"name": "Code Changes"}
        ),
        Artifact(
            type=ArtifactType.TEST_RESULT,
            uri="https://artifact-store.example.com/tests/task-2.1.json",
            size_bytes=2048,
            metadata={
                "total_tests": 15,
                "passed": 14,
                "failed": 1,
                "skipped": 0,
                "duration": 3.45
            }
        ),
        Artifact(
            type=ArtifactType.LOG,
            uri="https://artifact-store.example.com/logs/task-2.1.log",
            size_bytes=8192,
            metadata={
                "name": "Execution Log",
                "execution_time": 45.2,
                "has_errors": False
            }
        )
    ]
    
    # Define acceptance criteria
    acceptance_criteria = [
        "POST /api/auth/register creates new user",
        "POST /api/auth/login returns JWT token",
        "Middleware validates JWT on protected routes",
        "Passwords are hashed with bcrypt",
        "Tests cover happy path and error cases"
    ]
    
    print("\n" + "=" * 80)
    print("Example 1: Generate PR Description with Default Template")
    print("=" * 80)
    
    # Generate PR description
    description = engine.generate(
        task=task,
        acceptance_criteria=acceptance_criteria
    )
    
    print("\nGenerated PR Description:")
    print("-" * 80)
    print(description)
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("Example 2: Generate PR Description with Custom Sections")
    print("=" * 80)
    
    # Add custom sections
    engine.set_custom_section(
        "Breaking Changes",
        "None - This is a new feature with no breaking changes."
    )
    engine.set_custom_section(
        "Migration Notes",
        "Update environment variables to include JWT_SECRET."
    )
    
    description_with_custom = engine.generate(
        task=task,
        acceptance_criteria=acceptance_criteria
    )
    
    print("\nGenerated PR Description with Custom Sections:")
    print("-" * 80)
    print(description_with_custom)
    print("-" * 80)
    
    # Clear custom sections
    engine.clear_custom_sections()
    
    print("\n" + "=" * 80)
    print("Example 3: Generate PR Comment")
    print("=" * 80)
    
    # Generate a comment
    comment = engine.generate_comment(
        message="⚠️ Test failure detected in authentication tests.",
        details={
            "Failed Test": "test_login_with_invalid_password",
            "Error": "AssertionError: Expected 401, got 500",
            "File": "tests/test_auth.py:45"
        }
    )
    
    print("\nGenerated PR Comment:")
    print("-" * 80)
    print(comment)
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("Example 4: Validate Template")
    print("=" * 80)
    
    # Validate template
    errors = engine.validate_template()
    
    if errors:
        print("\n❌ Template validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ Template is valid")
    
    print("\n" + "=" * 80)
    print("Example 5: Generate with Minimal Data")
    print("=" * 80)
    
    # Create a minimal task
    minimal_task = Task(
        id="1.1",
        title="Setup Database Schema",
        description="Create User and Message models with MongoDB.",
        state=TaskState.DONE
    )
    
    # Generate with minimal data
    minimal_description = engine.generate(
        task=minimal_task,
        acceptance_criteria=["User model has required fields", "Message model has required fields"]
    )
    
    print("\nGenerated PR Description (Minimal):")
    print("-" * 80)
    print(minimal_description)
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("Example 6: Custom Template Path")
    print("=" * 80)
    
    # Create a custom inline template
    custom_template_path = Path("templates/custom-pr-template.md")
    custom_template_path.parent.mkdir(parents=True, exist_ok=True)
    
    custom_template_content = """# 🚀 {{title}}

**Task ID:** {{task_id}}

## What's Changed
{{description}}

{% if test_results %}
## Test Status
{{test_results}}
{% endif %}

---
*Auto-generated PR*
"""
    
    with open(custom_template_path, "w") as f:
        f.write(custom_template_content)
    
    # Load custom template
    engine.load_custom_template(str(custom_template_path))
    
    custom_description = engine.generate(
        task=task,
        acceptance_criteria=acceptance_criteria
    )
    
    print("\nGenerated PR Description with Custom Template:")
    print("-" * 80)
    print(custom_description)
    print("-" * 80)
    
    # Cleanup
    custom_template_path.unlink()
    
    print("\n" + "=" * 80)
    print("✓ All examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

"""
Example demonstrating TestRunner usage.

This example shows how to use the TestRunner component to execute tests
for a task, including custom test commands and default test detection.
"""

import tempfile
from pathlib import Path

from necrocode.agent_runner import (
    TaskContext,
    TestRunner,
    Workspace,
)


def example_basic_test_execution():
    """Example: Basic test execution with explicit commands."""
    print("=" * 60)
    print("Example 1: Basic Test Execution")
    print("=" * 60)
    
    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        # Create workspace
        workspace = Workspace(
            path=workspace_path,
            branch_name="feature/task-1-example",
            base_branch="main"
        )
        
        # Create task context with explicit test commands
        task_context = TaskContext(
            task_id="1",
            spec_name="example-spec",
            title="Example Task",
            description="Example task for testing",
            acceptance_criteria=["Tests pass", "Code is clean"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_path,
            slot_id="slot-1",
            branch_name="feature/task-1-example",
            test_commands=["echo 'Running test 1'", "echo 'Running test 2'"],
            fail_fast=True,
            timeout_seconds=30
        )
        
        # Run tests
        runner = TestRunner()
        result = runner.run_tests(task_context, workspace)
        
        # Display results
        print(f"\nTest execution completed:")
        print(f"  Success: {result.success}")
        print(f"  Total duration: {result.total_duration_seconds:.2f}s")
        print(f"  Number of tests: {len(result.test_results)}")
        
        for i, test_result in enumerate(result.test_results, 1):
            print(f"\n  Test {i}:")
            print(f"    Command: {test_result.command}")
            print(f"    Success: {test_result.success}")
            print(f"    Duration: {test_result.duration_seconds:.2f}s")
            print(f"    Output: {test_result.stdout.strip()}")


def example_fail_fast_mode():
    """Example: Fail-fast mode stops on first failure."""
    print("\n" + "=" * 60)
    print("Example 2: Fail-Fast Mode")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        workspace = Workspace(
            path=workspace_path,
            branch_name="feature/task-2-failfast",
            base_branch="main"
        )
        
        # Create task with failing test
        task_context = TaskContext(
            task_id="2",
            spec_name="example-spec",
            title="Fail-Fast Example",
            description="Example with failing test",
            acceptance_criteria=["Tests pass"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_path,
            slot_id="slot-1",
            branch_name="feature/task-2-failfast",
            test_commands=[
                "echo 'Test 1 passes'",
                "exit 1",  # This will fail
                "echo 'Test 3 should not run'"
            ],
            fail_fast=True,  # Stop on first failure
            timeout_seconds=30
        )
        
        runner = TestRunner()
        result = runner.run_tests(task_context, workspace)
        
        print(f"\nTest execution with fail-fast:")
        print(f"  Success: {result.success}")
        print(f"  Tests executed: {len(result.test_results)} (stopped after failure)")
        
        for i, test_result in enumerate(result.test_results, 1):
            status = "✓" if test_result.success else "✗"
            print(f"  {status} Test {i}: {test_result.command}")


def example_default_test_detection():
    """Example: Automatic test command detection."""
    print("\n" + "=" * 60)
    print("Example 3: Default Test Detection")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        # Create a Python project structure
        (workspace_path / "requirements.txt").write_text("pytest\n")
        (workspace_path / "pytest.ini").write_text("[pytest]\n")
        tests_dir = workspace_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").write_text(
            "def test_example():\n    assert True\n"
        )
        
        workspace = Workspace(
            path=workspace_path,
            branch_name="feature/task-3-autodetect",
            base_branch="main"
        )
        
        # Create task without explicit test commands
        task_context = TaskContext(
            task_id="3",
            spec_name="example-spec",
            title="Auto-Detect Example",
            description="Example with automatic test detection",
            acceptance_criteria=["Tests pass"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_path,
            slot_id="slot-1",
            branch_name="feature/task-3-autodetect",
            test_commands=None,  # Will auto-detect
            fail_fast=True,
            timeout_seconds=30
        )
        
        runner = TestRunner()
        
        # Get detected commands
        detected_commands = runner._get_default_test_commands(workspace_path)
        print(f"\nDetected project type: Python (pytest)")
        print(f"Default test commands: {detected_commands}")


def example_nodejs_project_detection():
    """Example: Node.js project test detection."""
    print("\n" + "=" * 60)
    print("Example 4: Node.js Project Detection")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        # Create a Node.js project structure
        import json
        package_json = {
            "name": "example-project",
            "version": "1.0.0",
            "scripts": {
                "test": "jest"
            }
        }
        (workspace_path / "package.json").write_text(json.dumps(package_json, indent=2))
        
        runner = TestRunner()
        detected_commands = runner._get_default_test_commands(workspace_path)
        
        print(f"\nDetected project type: Node.js")
        print(f"Default test commands: {detected_commands}")


def example_multiple_languages():
    """Example: Test detection for multiple languages."""
    print("\n" + "=" * 60)
    print("Example 5: Multiple Language Detection")
    print("=" * 60)
    
    runner = TestRunner()
    
    languages = {
        "Python (pytest)": {"pytest.ini": "[pytest]\n", "requirements.txt": "pytest\n"},
        "Node.js": {"package.json": '{"scripts": {"test": "npm test"}}'},
        "Go": {"go.mod": "module example\n"},
        "Rust": {"Cargo.toml": "[package]\nname = 'example'\n"},
        "Ruby": {"Gemfile": "source 'https://rubygems.org'\n"},
    }
    
    for lang, files in languages.items():
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            
            # Create project files
            for filename, content in files.items():
                (workspace_path / filename).write_text(content)
            
            # Detect commands
            commands = runner._get_default_test_commands(workspace_path)
            print(f"\n{lang}:")
            print(f"  Commands: {commands if commands else 'None detected'}")


if __name__ == "__main__":
    print("\nTestRunner Examples")
    print("=" * 60)
    
    example_basic_test_execution()
    example_fail_fast_mode()
    example_default_test_detection()
    example_nodejs_project_detection()
    example_multiple_languages()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)

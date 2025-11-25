"""
Tests for TestRunner component.

Tests the test execution functionality including command execution,
result aggregation, and default test command detection.
"""

import json
import tempfile
from pathlib import Path

import pytest

from necrocode.agent_runner import (
    CommandExecutor,
    TaskContext,
    TestRunner,
    Workspace,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        workspace = Workspace(
            path=workspace_path,
            branch_name="test-branch",
            base_branch="main"
        )
        yield workspace


@pytest.fixture
def task_context(temp_workspace):
    """Create a test task context."""
    return TaskContext(
        task_id="test-1",
        spec_name="test-spec",
        title="Test Task",
        description="Test task description",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
        dependencies=[],
        required_skill="backend",
        slot_path=temp_workspace.path,
        slot_id="slot-1",
        branch_name="test-branch",
        test_commands=None,
        fail_fast=True,
        timeout_seconds=30
    )


class TestCommandExecutor:
    """Tests for CommandExecutor."""
    
    def test_execute_successful_command(self, temp_workspace):
        """Test executing a successful command."""
        executor = CommandExecutor()
        result = executor.execute(
            command="echo 'Hello World'",
            cwd=temp_workspace.path,
            timeout_seconds=5
        )
        
        assert result.success is True
        assert result.exit_code == 0
        assert "Hello World" in result.stdout
        assert result.stderr == ""
        assert result.duration_seconds > 0
    
    def test_execute_failing_command(self, temp_workspace):
        """Test executing a command that fails."""
        executor = CommandExecutor()
        result = executor.execute(
            command="exit 1",
            cwd=temp_workspace.path,
            timeout_seconds=5
        )
        
        assert result.success is False
        assert result.exit_code == 1
        assert result.duration_seconds > 0
    
    def test_execute_command_with_stderr(self, temp_workspace):
        """Test executing a command that writes to stderr."""
        executor = CommandExecutor()
        result = executor.execute(
            command="echo 'Error message' >&2",
            cwd=temp_workspace.path,
            timeout_seconds=5
        )
        
        assert result.success is True
        assert "Error message" in result.stderr
    
    def test_execute_command_timeout(self, temp_workspace):
        """Test command execution timeout."""
        executor = CommandExecutor()
        result = executor.execute(
            command="sleep 10",
            cwd=temp_workspace.path,
            timeout_seconds=1
        )
        
        assert result.success is False
        assert result.exit_code == -1


class TestTestRunner:
    """Tests for TestRunner."""
    
    def test_run_tests_with_explicit_commands(self, task_context, temp_workspace):
        """Test running tests with explicitly configured commands."""
        task_context.test_commands = ["echo 'Test 1'", "echo 'Test 2'"]
        
        runner = TestRunner()
        result = runner.run_tests(task_context, temp_workspace)
        
        assert result.success is True
        assert len(result.test_results) == 2
        assert all(r.success for r in result.test_results)
        assert result.total_duration_seconds > 0
    
    def test_run_tests_with_failure(self, task_context, temp_workspace):
        """Test running tests where one fails."""
        task_context.test_commands = ["echo 'Test 1'", "exit 1", "echo 'Test 3'"]
        task_context.fail_fast = False
        
        runner = TestRunner()
        result = runner.run_tests(task_context, temp_workspace)
        
        assert result.success is False
        assert len(result.test_results) == 3
        assert result.test_results[0].success is True
        assert result.test_results[1].success is False
        assert result.test_results[2].success is True
    
    def test_run_tests_fail_fast(self, task_context, temp_workspace):
        """Test fail-fast mode stops on first failure."""
        task_context.test_commands = ["echo 'Test 1'", "exit 1", "echo 'Test 3'"]
        task_context.fail_fast = True
        
        runner = TestRunner()
        result = runner.run_tests(task_context, temp_workspace)
        
        assert result.success is False
        assert len(result.test_results) == 2  # Should stop after second test
        assert result.test_results[0].success is True
        assert result.test_results[1].success is False
    
    def test_run_tests_no_commands(self, task_context, temp_workspace):
        """Test running tests with no commands returns success."""
        task_context.test_commands = None
        
        runner = TestRunner()
        result = runner.run_tests(task_context, temp_workspace)
        
        assert result.success is True
        assert len(result.test_results) == 0
        assert result.total_duration_seconds == 0.0
    
    def test_detect_nodejs_project(self, temp_workspace):
        """Test detection of Node.js project."""
        # Create package.json with test script
        package_json = temp_workspace.path / "package.json"
        package_json.write_text(json.dumps({
            "name": "test-project",
            "scripts": {
                "test": "jest"
            }
        }))
        
        runner = TestRunner()
        commands = runner._get_default_test_commands(temp_workspace.path)
        
        assert "npm test" in commands
    
    def test_detect_python_project_pytest(self, temp_workspace):
        """Test detection of Python project with pytest."""
        # Create requirements.txt to indicate Python project
        requirements = temp_workspace.path / "requirements.txt"
        requirements.write_text("pytest\n")
        
        # Create pytest.ini
        pytest_ini = temp_workspace.path / "pytest.ini"
        pytest_ini.write_text("[pytest]\n")
        
        runner = TestRunner()
        commands = runner._get_default_test_commands(temp_workspace.path)
        
        assert "pytest" in commands
    
    def test_detect_python_project_unittest(self, temp_workspace):
        """Test detection of Python project with unittest."""
        # Create requirements.txt to indicate Python project
        requirements = temp_workspace.path / "requirements.txt"
        requirements.write_text("# test dependencies\n")
        
        # Create test directory
        test_dir = temp_workspace.path / "test"
        test_dir.mkdir()
        
        runner = TestRunner()
        commands = runner._get_default_test_commands(temp_workspace.path)
        
        assert any("unittest" in cmd for cmd in commands)
    
    def test_detect_go_project(self, temp_workspace):
        """Test detection of Go project."""
        # Create go.mod
        go_mod = temp_workspace.path / "go.mod"
        go_mod.write_text("module test\n")
        
        runner = TestRunner()
        commands = runner._get_default_test_commands(temp_workspace.path)
        
        assert "go test ./..." in commands
    
    def test_detect_rust_project(self, temp_workspace):
        """Test detection of Rust project."""
        # Create Cargo.toml
        cargo_toml = temp_workspace.path / "Cargo.toml"
        cargo_toml.write_text("[package]\nname = 'test'\n")
        
        runner = TestRunner()
        commands = runner._get_default_test_commands(temp_workspace.path)
        
        assert "cargo test" in commands
    
    def test_no_project_detected(self, temp_workspace):
        """Test when no project type is detected."""
        runner = TestRunner()
        commands = runner._get_default_test_commands(temp_workspace.path)
        
        assert commands == []
    
    def test_run_single_test(self, temp_workspace):
        """Test running a single test command."""
        runner = TestRunner()
        result = runner._run_single_test(
            command="echo 'Single test'",
            workspace=temp_workspace,
            timeout_seconds=5
        )
        
        assert result.success is True
        assert "Single test" in result.stdout
        assert result.exit_code == 0


class TestTestResultSerialization:
    """Tests for TestResult serialization."""
    
    def test_single_test_result_serialization(self):
        """Test SingleTestResult to_dict and from_dict."""
        from necrocode.agent_runner import SingleTestResult
        
        result = SingleTestResult(
            command="pytest",
            success=True,
            stdout="Test output",
            stderr="",
            exit_code=0,
            duration_seconds=1.5
        )
        
        data = result.to_dict()
        restored = SingleTestResult.from_dict(data)
        
        assert restored.command == result.command
        assert restored.success == result.success
        assert restored.stdout == result.stdout
        assert restored.stderr == result.stderr
        assert restored.exit_code == result.exit_code
        assert restored.duration_seconds == result.duration_seconds
    
    def test_test_result_serialization(self):
        """Test TestResult to_dict and from_dict."""
        from necrocode.agent_runner import SingleTestResult, TestResult
        
        single_results = [
            SingleTestResult(
                command="test1",
                success=True,
                stdout="out1",
                stderr="",
                exit_code=0,
                duration_seconds=1.0
            ),
            SingleTestResult(
                command="test2",
                success=True,
                stdout="out2",
                stderr="",
                exit_code=0,
                duration_seconds=2.0
            )
        ]
        
        result = TestResult(
            success=True,
            test_results=single_results,
            total_duration_seconds=3.0
        )
        
        data = result.to_dict()
        restored = TestResult.from_dict(data)
        
        assert restored.success == result.success
        assert len(restored.test_results) == len(result.test_results)
        assert restored.total_duration_seconds == result.total_duration_seconds
        assert restored.test_results[0].command == "test1"
        assert restored.test_results[1].command == "test2"

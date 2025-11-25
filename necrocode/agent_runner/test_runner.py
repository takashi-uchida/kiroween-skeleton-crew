"""
Test execution for Agent Runner.

This module provides test execution capabilities, including running test commands,
capturing output, and aggregating results.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from .exceptions import TestExecutionError
from .models import SingleTestResult, TaskContext, TestResult, Workspace

logger = logging.getLogger(__name__)


class CommandExecutor:
    """
    Abstraction for executing shell commands.
    
    Provides a consistent interface for running commands with timeout,
    output capture, and error handling.
    """
    
    def execute(
        self,
        command: str,
        cwd: Path,
        timeout_seconds: int = 300,
        env: Optional[dict] = None
    ) -> SingleTestResult:
        """
        Execute a shell command and capture results.
        
        Args:
            command: Shell command to execute
            cwd: Working directory for command execution
            timeout_seconds: Maximum execution time in seconds
            env: Optional environment variables
            
        Returns:
            SingleTestResult containing execution details
            
        Raises:
            TestExecutionError: If command execution fails critically
        """
        logger.info(f"Executing command: {command}")
        logger.debug(f"Working directory: {cwd}")
        
        start_time = time.time()
        
        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env
            )
            
            duration = time.time() - start_time
            
            # Determine success based on exit code
            success = result.returncode == 0
            
            logger.info(
                f"Command completed in {duration:.2f}s with exit code {result.returncode}"
            )
            
            return SingleTestResult(
                command=command,
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_seconds=duration
            )
            
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            logger.error(f"Command timed out after {timeout_seconds}s")
            
            return SingleTestResult(
                command=command,
                success=False,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "",
                exit_code=-1,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Command execution failed: {e}")
            
            return SingleTestResult(
                command=command,
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration_seconds=duration
            )


class AgentTestRunner:
    """
    Test execution manager for Agent Runner.
    
    Coordinates test execution, including running multiple test commands,
    capturing results, and determining overall test success.
    """
    
    def __init__(self):
        """Initialize TestRunner with CommandExecutor."""
        self.command_executor = CommandExecutor()
        logger.info("TestRunner initialized")
    
    def run_tests(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> TestResult:
        """
        Execute all tests for a task.
        
        Runs test commands specified in the task context, or uses default
        test commands if none are specified. Supports fail-fast mode to
        stop on first failure.
        
        Args:
            task_context: Task context containing test configuration
            workspace: Workspace where tests should be executed
            
        Returns:
            TestResult containing aggregated test results
            
        Raises:
            TestExecutionError: If test execution fails critically
        """
        logger.info(f"Running tests for task {task_context.task_id}")
        
        # Get test commands from context or use defaults
        test_commands = task_context.test_commands
        if not test_commands:
            test_commands = self._get_default_test_commands(workspace.path)
            logger.info(f"Using default test commands: {test_commands}")
        else:
            logger.info(f"Using configured test commands: {test_commands}")
        
        if not test_commands:
            logger.warning("No test commands found, skipping tests")
            return TestResult(
                success=True,
                test_results=[],
                total_duration_seconds=0.0
            )
        
        # Execute each test command
        results: List[SingleTestResult] = []
        total_duration = 0.0
        
        for cmd in test_commands:
            logger.info(f"Executing test command: {cmd}")
            
            result = self._run_single_test(
                command=cmd,
                workspace=workspace,
                timeout_seconds=task_context.timeout_seconds
            )
            
            results.append(result)
            total_duration += result.duration_seconds
            
            # Log test result
            if result.success:
                logger.info(f"Test passed: {cmd}")
            else:
                logger.error(f"Test failed: {cmd}")
                logger.error(f"Exit code: {result.exit_code}")
                logger.error(f"Stderr: {result.stderr}")
            
            # Stop on first failure if fail_fast is enabled
            if not result.success and task_context.fail_fast:
                logger.warning("Fail-fast enabled, stopping test execution")
                break
        
        # Determine overall success
        overall_success = all(r.success for r in results)
        
        logger.info(
            f"Test execution completed: {len(results)} tests, "
            f"{'all passed' if overall_success else 'some failed'}"
        )
        
        return TestResult(
            success=overall_success,
            test_results=results,
            total_duration_seconds=total_duration
        )
    
    def _run_single_test(
        self,
        command: str,
        workspace: Workspace,
        timeout_seconds: int = 300
    ) -> SingleTestResult:
        """
        Execute a single test command.
        
        Args:
            command: Test command to execute
            workspace: Workspace where test should be executed
            timeout_seconds: Maximum execution time
            
        Returns:
            SingleTestResult containing test execution details
        """
        return self.command_executor.execute(
            command=command,
            cwd=workspace.path,
            timeout_seconds=timeout_seconds
        )
    
    def _get_default_test_commands(self, workspace_path: Path) -> List[str]:
        """
        Determine default test commands based on project structure.
        
        Detects the project type by examining files in the workspace
        and returns appropriate test commands for the detected language/framework.
        
        Args:
            workspace_path: Path to workspace directory
            
        Returns:
            List of default test commands for the detected project type
        """
        logger.info(f"Detecting project type in {workspace_path}")
        
        # Check for various project indicators
        indicators = {
            "package.json": self._get_nodejs_test_commands,
            "requirements.txt": self._get_python_test_commands,
            "setup.py": self._get_python_test_commands,
            "pyproject.toml": self._get_python_test_commands,
            "Gemfile": self._get_ruby_test_commands,
            "go.mod": self._get_go_test_commands,
            "Cargo.toml": self._get_rust_test_commands,
            "pom.xml": self._get_java_maven_test_commands,
            "build.gradle": self._get_java_gradle_test_commands,
        }
        
        for indicator_file, command_getter in indicators.items():
            if (workspace_path / indicator_file).exists():
                logger.info(f"Detected project type from {indicator_file}")
                return command_getter(workspace_path)
        
        logger.warning("Could not detect project type, no default test commands")
        return []
    
    def _get_nodejs_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Node.js projects."""
        commands = []
        
        # Check package.json for test script
        package_json = workspace_path / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    if "scripts" in data and "test" in data["scripts"]:
                        commands.append("npm test")
                        logger.info("Found npm test script")
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")
        
        # Fallback to common test runners
        if not commands:
            if (workspace_path / "jest.config.js").exists():
                commands.append("npx jest")
            elif (workspace_path / "vitest.config.ts").exists():
                commands.append("npx vitest run")
            elif (workspace_path / "mocha").exists():
                commands.append("npx mocha")
        
        return commands
    
    def _get_python_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Python projects."""
        commands = []
        
        # Check for pytest
        if (workspace_path / "pytest.ini").exists():
            commands.append("pytest")
        elif (workspace_path / "tests").exists():
            commands.append("pytest")
        # Check for unittest
        elif (workspace_path / "test").exists():
            commands.append("python -m unittest discover")
        
        return commands
    
    def _get_ruby_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Ruby projects."""
        if (workspace_path / "spec").exists():
            return ["bundle exec rspec"]
        return ["bundle exec rake test"]
    
    def _get_go_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Go projects."""
        return ["go test ./..."]
    
    def _get_rust_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Rust projects."""
        return ["cargo test"]
    
    def _get_java_maven_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Java Maven projects."""
        return ["mvn test"]
    
    def _get_java_gradle_test_commands(self, workspace_path: Path) -> List[str]:
        """Get default test commands for Java Gradle projects."""
        return ["./gradlew test"]


# Alias for backward compatibility and clearer naming
TestRunner = AgentTestRunner

"""
Playbook execution engine for Agent Runner.

This module provides Playbook execution capabilities, including loading
YAML-based playbooks, executing steps with conditions, and managing
execution flow.
"""

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .exceptions import PlaybookExecutionError
from .models import Playbook, PlaybookStep

logger = logging.getLogger(__name__)


class PlaybookEngine:
    """
    Playbook execution engine.
    
    Manages loading and executing Playbooks, which define custom
    task execution workflows with conditional steps, timeouts,
    and retry logic.
    """
    
    # Default Playbook for standard task execution
    DEFAULT_PLAYBOOK = {
        "name": "Default Task Playbook",
        "steps": [
            {
                "name": "Install dependencies",
                "command": "echo 'No dependency installation configured'",
                "condition": "install_deps == true",
                "fail_fast": False,
                "timeout_seconds": 300,
                "retry_count": 2
            },
            {
                "name": "Run linter",
                "command": "echo 'No linter configured'",
                "condition": "lint_enabled == true",
                "fail_fast": False,
                "timeout_seconds": 300,
                "retry_count": 0
            },
            {
                "name": "Run tests",
                "command": "echo 'No tests configured'",
                "condition": "test_enabled == true",
                "fail_fast": True,
                "timeout_seconds": 600,
                "retry_count": 0
            },
            {
                "name": "Build project",
                "command": "echo 'No build configured'",
                "condition": "build_enabled == true",
                "fail_fast": True,
                "timeout_seconds": 600,
                "retry_count": 1
            }
        ]
    }
    
    def __init__(self):
        """Initialize PlaybookEngine."""
        logger.info("PlaybookEngine initialized")
    
    def get_default_playbook(self) -> Playbook:
        """
        Get the default Playbook.
        
        Returns a standard Playbook suitable for most task types,
        with common steps like dependency installation, linting,
        testing, and building.
        
        Returns:
            Default Playbook object
        """
        logger.info("Creating default Playbook")
        
        steps = []
        for step_data in self.DEFAULT_PLAYBOOK["steps"]:
            step = PlaybookStep(
                name=step_data["name"],
                command=step_data["command"],
                condition=step_data.get("condition"),
                fail_fast=step_data.get("fail_fast", True),
                timeout_seconds=step_data.get("timeout_seconds", 300),
                retry_count=step_data.get("retry_count", 0)
            )
            steps.append(step)
        
        return Playbook(
            name=self.DEFAULT_PLAYBOOK["name"],
            steps=steps,
            metadata={"source": "default"}
        )
    
    def load_playbook(self, playbook_path: Path) -> Playbook:
        """
        Load a Playbook from a YAML file.
        
        Parses a YAML file containing Playbook definition and converts
        it into a Playbook object with validated steps.
        
        Args:
            playbook_path: Path to YAML Playbook file
            
        Returns:
            Playbook object containing parsed steps
            
        Raises:
            PlaybookExecutionError: If Playbook file cannot be loaded or parsed
        """
        logger.info(f"Loading Playbook from {playbook_path}")
        
        if not playbook_path.exists():
            raise PlaybookExecutionError(f"Playbook file not found: {playbook_path}")
        
        try:
            with open(playbook_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise PlaybookExecutionError(f"Empty Playbook file: {playbook_path}")
            
            # Validate required fields
            if "name" not in data:
                raise PlaybookExecutionError("Playbook must have a 'name' field")
            
            if "steps" not in data or not isinstance(data["steps"], list):
                raise PlaybookExecutionError("Playbook must have a 'steps' list")
            
            # Parse steps
            steps = []
            for i, step_data in enumerate(data["steps"]):
                try:
                    step = self._parse_step(step_data, i)
                    steps.append(step)
                except Exception as e:
                    raise PlaybookExecutionError(
                        f"Failed to parse step {i}: {e}"
                    )
            
            # Extract metadata
            metadata = data.get("metadata", {})
            metadata["source"] = "file"
            metadata["file_path"] = str(playbook_path)
            
            playbook = Playbook(
                name=data["name"],
                steps=steps,
                metadata=metadata
            )
            
            logger.info(
                f"Loaded Playbook '{playbook.name}' with {len(steps)} steps"
            )
            
            return playbook
            
        except yaml.YAMLError as e:
            raise PlaybookExecutionError(f"Failed to parse YAML: {e}")
        except Exception as e:
            raise PlaybookExecutionError(f"Failed to load Playbook: {e}")
    
    def load_playbook_or_default(
        self,
        playbook_path: Optional[Path] = None
    ) -> Playbook:
        """
        Load a Playbook from file or return default.
        
        Attempts to load a custom Playbook from the specified path.
        If the path is None or the file doesn't exist, returns the
        default Playbook instead.
        
        Args:
            playbook_path: Optional path to custom Playbook file
            
        Returns:
            Loaded Playbook or default Playbook
        """
        if playbook_path is None:
            logger.info("No Playbook path specified, using default")
            return self.get_default_playbook()
        
        if not playbook_path.exists():
            logger.warning(
                f"Playbook file not found: {playbook_path}, using default"
            )
            return self.get_default_playbook()
        
        try:
            return self.load_playbook(playbook_path)
        except PlaybookExecutionError as e:
            logger.error(f"Failed to load Playbook: {e}, using default")
            return self.get_default_playbook()
    
    def _parse_step(self, step_data: Dict[str, Any], index: int) -> PlaybookStep:
        """
        Parse a single Playbook step from dictionary.
        
        Args:
            step_data: Dictionary containing step configuration
            index: Step index for error reporting
            
        Returns:
            PlaybookStep object
            
        Raises:
            ValueError: If step data is invalid
        """
        # Validate required fields
        if "name" not in step_data:
            raise ValueError(f"Step {index} missing 'name' field")
        
        if "command" not in step_data:
            raise ValueError(f"Step {index} missing 'command' field")
        
        # Extract fields with defaults
        return PlaybookStep(
            name=step_data["name"],
            command=step_data["command"],
            condition=step_data.get("condition"),
            fail_fast=step_data.get("fail_fast", True),
            timeout_seconds=step_data.get("timeout_seconds", 300),
            retry_count=step_data.get("retry_count", 0)
        )
    
    def execute_playbook(
        self,
        playbook: Playbook,
        context: Dict[str, Any],
        cwd: Path
    ) -> "PlaybookResult":
        """
        Execute a Playbook with the given context.
        
        Executes each step in the Playbook sequentially, evaluating
        conditions and handling failures according to step configuration.
        
        Args:
            playbook: Playbook to execute
            context: Execution context for variable substitution and conditions
            cwd: Working directory for command execution
            
        Returns:
            PlaybookResult containing execution results for all steps
            
        Raises:
            PlaybookExecutionError: If Playbook execution fails critically
        """
        logger.info(f"Executing Playbook '{playbook.name}'")
        logger.debug(f"Context: {context}")
        logger.debug(f"Working directory: {cwd}")
        
        results: List["StepResult"] = []
        
        for i, step in enumerate(playbook.steps):
            logger.info(f"Step {i + 1}/{len(playbook.steps)}: {step.name}")
            
            # Check if step should be executed
            if not self._should_execute_step(step, context):
                logger.info(f"Skipping step '{step.name}' (condition not met)")
                results.append(StepResult(
                    step_name=step.name,
                    command=step.command,
                    success=True,
                    skipped=True,
                    stdout="",
                    stderr="",
                    exit_code=0,
                    duration_seconds=0.0
                ))
                continue
            
            # Execute step
            result = self._execute_step(step, context, cwd)
            results.append(result)
            
            # Log result
            if result.success:
                logger.info(f"Step '{step.name}' completed successfully")
            else:
                logger.error(f"Step '{step.name}' failed")
                logger.error(f"Exit code: {result.exit_code}")
                logger.error(f"Stderr: {result.stderr}")
            
            # Handle failure
            if not result.success and step.fail_fast:
                logger.warning(
                    f"Step '{step.name}' failed with fail_fast=True, "
                    "stopping Playbook execution"
                )
                break
        
        # Determine overall success
        overall_success = all(r.success for r in results)
        
        logger.info(
            f"Playbook execution completed: {len(results)} steps executed, "
            f"{'all succeeded' if overall_success else 'some failed'}"
        )
        
        return PlaybookResult(
            playbook_name=playbook.name,
            success=overall_success,
            step_results=results,
            total_duration_seconds=sum(r.duration_seconds for r in results)
        )
    
    def _execute_step(
        self,
        step: PlaybookStep,
        context: Dict[str, Any],
        cwd: Path
    ) -> "StepResult":
        """
        Execute a single Playbook step.
        
        Executes the step command with retry logic if configured,
        and captures output and execution metrics.
        
        Args:
            step: PlaybookStep to execute
            context: Execution context for variable substitution
            cwd: Working directory for command execution
            
        Returns:
            StepResult containing execution details
        """
        logger.debug(f"Executing step: {step.name}")
        
        # Substitute variables in command
        command = self._substitute_variables(step.command, context)
        logger.debug(f"Command after substitution: {command}")
        
        # Execute with retries
        last_result = None
        for attempt in range(step.retry_count + 1):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{step.retry_count}")
            
            result = self._execute_command(
                command=command,
                cwd=cwd,
                timeout_seconds=step.timeout_seconds
            )
            
            last_result = result
            
            # If successful, return immediately
            if result.success:
                return StepResult(
                    step_name=step.name,
                    command=command,
                    success=True,
                    skipped=False,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.exit_code,
                    duration_seconds=result.duration_seconds,
                    retry_count=attempt
                )
            
            # If not successful and retries remain, continue
            if attempt < step.retry_count:
                logger.warning(
                    f"Step failed, will retry ({attempt + 1}/{step.retry_count})"
                )
        
        # All retries exhausted, return failure
        return StepResult(
            step_name=step.name,
            command=command,
            success=False,
            skipped=False,
            stdout=last_result.stdout if last_result else "",
            stderr=last_result.stderr if last_result else "",
            exit_code=last_result.exit_code if last_result else -1,
            duration_seconds=last_result.duration_seconds if last_result else 0.0,
            retry_count=step.retry_count
        )
    
    def _execute_command(
        self,
        command: str,
        cwd: Path,
        timeout_seconds: int
    ) -> "CommandResult":
        """
        Execute a shell command.
        
        Args:
            command: Shell command to execute
            cwd: Working directory
            timeout_seconds: Maximum execution time
            
        Returns:
            CommandResult with execution details
        """
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            duration = time.time() - start_time
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration_seconds=duration
            )
            
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            logger.error(f"Command timed out after {timeout_seconds}s")
            
            return CommandResult(
                success=False,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "",
                exit_code=-1,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Command execution failed: {e}")
            
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration_seconds=duration
            )
    
    def _substitute_variables(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Substitute variables in text using context.
        
        Replaces ${variable_name} patterns with values from context.
        
        Args:
            text: Text containing variable references
            context: Dictionary of variable values
            
        Returns:
            Text with variables substituted
        """
        # Find all ${variable} patterns
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in context:
                return str(context[var_name])
            else:
                logger.warning(f"Variable '{var_name}' not found in context")
                return match.group(0)  # Keep original if not found
        
        return re.sub(pattern, replace_var, text)
    
    def _should_execute_step(
        self,
        step: PlaybookStep,
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate whether a step should be executed based on its condition.
        
        Evaluates the step's condition expression against the context.
        Supports simple comparison operators (==, !=, <, >, <=, >=)
        and boolean values.
        
        Args:
            step: PlaybookStep with optional condition
            context: Execution context for condition evaluation
            
        Returns:
            True if step should be executed, False otherwise
        """
        # If no condition, always execute
        if not step.condition:
            return True
        
        condition = step.condition.strip()
        logger.debug(f"Evaluating condition: {condition}")
        
        try:
            # Parse and evaluate condition
            result = self._evaluate_condition(condition, context)
            logger.debug(f"Condition result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            # On error, default to executing the step
            return True
    
    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition expression.
        
        Supports:
        - Boolean literals: true, false
        - Comparison operators: ==, !=, <, >, <=, >=
        - Variable references from context
        - String and numeric comparisons
        
        Args:
            condition: Condition expression to evaluate
            context: Context dictionary for variable lookup
            
        Returns:
            Boolean result of condition evaluation
            
        Raises:
            ValueError: If condition syntax is invalid
        """
        # Handle boolean literals
        if condition.lower() == "true":
            return True
        if condition.lower() == "false":
            return False
        
        # Try to parse comparison operators
        operators = [
            ("==", lambda a, b: a == b),
            ("!=", lambda a, b: a != b),
            ("<=", lambda a, b: a <= b),
            (">=", lambda a, b: a >= b),
            ("<", lambda a, b: a < b),
            (">", lambda a, b: a > b),
        ]
        
        for op_str, op_func in operators:
            if op_str in condition:
                parts = condition.split(op_str, 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), context)
                    right = self._resolve_value(parts[1].strip(), context)
                    
                    # Try numeric comparison first
                    try:
                        left_num = float(left) if isinstance(left, str) else left
                        right_num = float(right) if isinstance(right, str) else right
                        return op_func(left_num, right_num)
                    except (ValueError, TypeError):
                        # Fall back to string comparison
                        return op_func(str(left), str(right))
        
        # If no operator found, treat as variable lookup
        value = self._resolve_value(condition, context)
        
        # Convert to boolean
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        if isinstance(value, (int, float)):
            return value != 0
        
        return bool(value)
    
    def _resolve_value(
        self,
        expr: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        Resolve a value expression.
        
        Handles:
        - String literals (quoted)
        - Numeric literals
        - Boolean literals
        - Variable references from context
        
        Args:
            expr: Expression to resolve
            context: Context dictionary for variable lookup
            
        Returns:
            Resolved value
        """
        expr = expr.strip()
        
        # Handle quoted strings
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        
        # Handle boolean literals
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
        
        # Try numeric literal
        try:
            if '.' in expr:
                return float(expr)
            else:
                return int(expr)
        except ValueError:
            pass
        
        # Look up in context
        if expr in context:
            return context[expr]
        
        # Return as string if not found
        logger.warning(f"Variable '{expr}' not found in context, treating as string")
        return expr


# Result classes for Playbook execution

class CommandResult:
    """Result of a single command execution."""
    
    def __init__(
        self,
        success: bool,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float
    ):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration_seconds = duration_seconds


class StepResult:
    """Result of a Playbook step execution."""
    
    def __init__(
        self,
        step_name: str,
        command: str,
        success: bool,
        skipped: bool,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_seconds: float,
        retry_count: int = 0
    ):
        self.step_name = step_name
        self.command = command
        self.success = success
        self.skipped = skipped
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration_seconds = duration_seconds
        self.retry_count = retry_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_name": self.step_name,
            "command": self.command,
            "success": self.success,
            "skipped": self.skipped,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
        }


class PlaybookResult:
    """Result of complete Playbook execution."""
    
    def __init__(
        self,
        playbook_name: str,
        success: bool,
        step_results: List[StepResult],
        total_duration_seconds: float
    ):
        self.playbook_name = playbook_name
        self.success = success
        self.step_results = step_results
        self.total_duration_seconds = total_duration_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "playbook_name": self.playbook_name,
            "success": self.success,
            "step_results": [r.to_dict() for r in self.step_results],
            "total_duration_seconds": self.total_duration_seconds,
        }


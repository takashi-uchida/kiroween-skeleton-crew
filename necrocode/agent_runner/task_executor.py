"""
Task Executor for Agent Runner.

This module provides the TaskExecutor class that handles task implementation
by coordinating with Kiro (the AI agent) to generate code based on task context.
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from necrocode.agent_runner.models import (
    TaskContext,
    Workspace,
    ImplementationResult,
)
from necrocode.agent_runner.exceptions import ImplementationError

logger = logging.getLogger(__name__)


class KiroClient:
    """
    Client for communicating with Kiro AI agent.
    
    This class provides methods to invoke Kiro for task implementation,
    handling the communication protocol and response parsing.
    """
    
    def __init__(self, workspace_path: Optional[Path] = None):
        """
        Initialize Kiro client.
        
        Args:
            workspace_path: Path to the workspace where Kiro will operate
        """
        self.workspace_path = workspace_path
        self.logger = logging.getLogger(f"{__name__}.KiroClient")
    
    def implement(
        self,
        prompt: str,
        workspace_path: Path,
        timeout_seconds: int = 1800
    ) -> Dict[str, Any]:
        """
        Request Kiro to implement a task.
        
        Args:
            prompt: Implementation prompt describing what to implement
            workspace_path: Path to workspace where implementation occurs
            timeout_seconds: Maximum time to wait for implementation
        
        Returns:
            Dictionary containing:
                - files_changed: List of files modified
                - duration: Time taken in seconds
                - notes: Implementation notes from Kiro
        
        Raises:
            ImplementationError: If Kiro execution fails
        """
        self.logger.info(f"Requesting Kiro implementation in {workspace_path}")
        self.logger.debug(f"Prompt: {prompt[:200]}...")
        
        start_time = time.time()
        
        try:
            # In a real implementation, this would invoke Kiro via:
            # 1. Kiro CLI command
            # 2. Kiro API endpoint
            # 3. Direct integration with Kiro's Python API
            #
            # For now, we simulate the response structure
            # that Kiro would return after implementing the task
            
            # Example: kiro execute --prompt "{prompt}" --workspace "{workspace_path}"
            # This is a placeholder for the actual Kiro integration
            
            response = self._invoke_kiro(prompt, workspace_path, timeout_seconds)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"Kiro implementation completed in {duration:.2f}s, "
                f"modified {len(response.get('files_changed', []))} files"
            )
            
            return {
                "files_changed": response.get("files_changed", []),
                "duration": duration,
                "notes": response.get("notes", ""),
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Kiro implementation failed after {duration:.2f}s: {e}")
            raise ImplementationError(f"Kiro execution failed: {e}") from e
    
    def _invoke_kiro(
        self,
        prompt: str,
        workspace_path: Path,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """
        Internal method to invoke Kiro.
        
        This is where the actual Kiro invocation would happen.
        Currently returns a simulated response structure.
        
        Args:
            prompt: Implementation prompt
            workspace_path: Workspace path
            timeout_seconds: Timeout in seconds
        
        Returns:
            Response dictionary from Kiro
        
        Raises:
            ImplementationError: If invocation fails
        """
        # TODO: Implement actual Kiro invocation
        # Options:
        # 1. CLI: subprocess.run(["kiro", "execute", "--prompt", prompt, ...])
        # 2. API: requests.post("http://kiro-api/execute", json={...})
        # 3. Direct: from kiro import Agent; agent.execute(prompt)
        
        # For now, return a placeholder response
        # In production, this would be replaced with actual Kiro integration
        self.logger.warning(
            "Using placeholder Kiro response - actual integration not yet implemented"
        )
        
        return {
            "files_changed": [],
            "notes": "Placeholder response - Kiro integration pending",
        }


class TaskExecutor:
    """
    Executes task implementation using Kiro AI agent.
    
    This class coordinates the task implementation process, including:
    - Building implementation prompts from task context
    - Invoking Kiro to generate code
    - Verifying implementation results
    - Handling errors and retries
    """
    
    def __init__(self, kiro_client: Optional[KiroClient] = None):
        """
        Initialize TaskExecutor.
        
        Args:
            kiro_client: Optional KiroClient instance. If not provided,
                        a new instance will be created.
        """
        self.kiro_client = kiro_client or KiroClient()
        self.logger = logging.getLogger(f"{__name__}.TaskExecutor")
    
    def execute(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> ImplementationResult:
        """
        Execute task implementation.
        
        This is the main entry point for task execution. It:
        1. Builds an implementation prompt from task context
        2. Invokes Kiro to implement the task
        3. Verifies the implementation
        4. Returns the result
        
        Args:
            task_context: Context information for the task
            workspace: Workspace where implementation occurs
        
        Returns:
            ImplementationResult containing implementation details
        
        Raises:
            ImplementationError: If implementation fails
        """
        self.logger.info(
            f"Executing task {task_context.task_id}: {task_context.title}"
        )
        
        start_time = time.time()
        
        try:
            # Build implementation prompt
            prompt = self._build_implementation_prompt(task_context)
            
            # Invoke Kiro to implement
            impl_response = self.kiro_client.implement(
                prompt=prompt,
                workspace_path=workspace.path,
                timeout_seconds=task_context.timeout_seconds
            )
            
            # Verify implementation
            if not self._verify_implementation(impl_response, task_context):
                raise ImplementationError("Implementation verification failed")
            
            # Get diff of changes
            diff = self._get_workspace_diff(workspace)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"Task {task_context.task_id} implemented successfully "
                f"in {duration:.2f}s"
            )
            
            return ImplementationResult(
                success=True,
                diff=diff,
                files_changed=impl_response["files_changed"],
                duration_seconds=duration,
                error=None,
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Task {task_context.task_id} implementation failed "
                f"after {duration:.2f}s: {e}"
            )
            
            return ImplementationResult(
                success=False,
                diff="",
                files_changed=[],
                duration_seconds=duration,
                error=str(e),
            )
    
    def _build_implementation_prompt(self, task_context: TaskContext) -> str:
        """
        Build implementation prompt from task context.
        
        Creates a detailed prompt for Kiro that includes:
        - Task description and title
        - Acceptance criteria
        - Dependencies and context
        - Required skills and complexity
        
        Args:
            task_context: Task context to build prompt from
        
        Returns:
            Formatted prompt string for Kiro
        """
        self.logger.debug(f"Building prompt for task {task_context.task_id}")
        
        # Build acceptance criteria section
        criteria_text = "\n".join(
            f"- {criterion}" for criterion in task_context.acceptance_criteria
        )
        
        # Build dependencies section
        if task_context.dependencies:
            deps_text = "\n".join(
                f"- Task {dep}" for dep in task_context.dependencies
            )
            dependencies_section = f"\n## Dependencies\n{deps_text}\n"
        else:
            dependencies_section = ""
        
        # Build metadata section
        metadata_items = []
        metadata_items.append(f"- Required Skill: {task_context.required_skill}")
        metadata_items.append(f"- Complexity: {task_context.complexity}")
        metadata_items.append(f"- Spec: {task_context.spec_name}")
        
        if task_context.metadata:
            for key, value in task_context.metadata.items():
                metadata_items.append(f"- {key}: {value}")
        
        metadata_text = "\n".join(metadata_items)
        
        # Construct the full prompt
        prompt = f"""# Task: {task_context.title}

## Task ID
{task_context.task_id}

## Description
{task_context.description}
{dependencies_section}
## Acceptance Criteria
{criteria_text}

## Technical Context
{metadata_text}

## Instructions
Implement this task according to the description and acceptance criteria.
Ensure all acceptance criteria are met and the implementation follows best practices.
"""
        
        self.logger.debug(f"Generated prompt ({len(prompt)} chars)")
        
        return prompt
    
    def _verify_implementation(
        self,
        impl_response: Dict[str, Any],
        task_context: TaskContext
    ) -> bool:
        """
        Verify implementation result.
        
        Performs basic validation of the implementation response to ensure
        it meets minimum requirements. This includes checking that:
        - Files were actually changed
        - Response structure is valid
        - No obvious errors occurred
        
        Args:
            impl_response: Response from Kiro implementation
            task_context: Original task context
        
        Returns:
            True if implementation appears valid, False otherwise
        """
        self.logger.debug(f"Verifying implementation for task {task_context.task_id}")
        
        try:
            # Check that response has required fields
            if "files_changed" not in impl_response:
                self.logger.error("Implementation response missing 'files_changed'")
                return False
            
            # Check that at least some files were changed
            # (unless this is a documentation-only or analysis task)
            files_changed = impl_response["files_changed"]
            if not files_changed and task_context.required_skill != "documentation":
                self.logger.warning(
                    "No files were changed during implementation - "
                    "this may indicate an issue"
                )
                # Don't fail for this - some tasks might not change files
            
            # Check for error indicators in response
            if "error" in impl_response and impl_response["error"]:
                self.logger.error(f"Implementation reported error: {impl_response['error']}")
                return False
            
            self.logger.debug("Implementation verification passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Implementation verification failed: {e}")
            return False
    
    def _get_workspace_diff(self, workspace: Workspace) -> str:
        """
        Get diff of changes in workspace.
        
        Executes git diff to capture all changes made during implementation.
        
        Args:
            workspace: Workspace to get diff from
        
        Returns:
            Git diff output as string
        """
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=workspace.path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get workspace diff: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Unexpected error getting diff: {e}")
            return ""

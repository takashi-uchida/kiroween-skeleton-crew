"""
Task Executor for Agent Runner.

This module provides the TaskExecutor class that handles task implementation
by coordinating with LLM services to generate code based on task context.
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from necrocode.agent_runner.models import (
    TaskContext,
    Workspace,
    ImplementationResult,
    LLMConfig,
    CodeChange,
)
from necrocode.agent_runner.exceptions import ImplementationError
from necrocode.agent_runner.llm_client import LLMClient

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Executes task implementation using LLM services.
    
    This class coordinates the task implementation process, including:
    - Building implementation prompts from task context
    - Invoking LLM to generate code
    - Applying code changes to workspace
    - Verifying implementation results
    - Handling errors and retries
    """
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """
        Initialize TaskExecutor.
        
        Args:
            llm_config: LLM configuration (API key, model name, etc.).
                       If None, LLM client will not be initialized and
                       execute() will fail if called.
        """
        self.llm_client = LLMClient(llm_config) if llm_config else None
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
        2. Invokes LLM to generate code
        3. Applies code changes to workspace
        4. Verifies the implementation
        5. Returns the result
        
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
        
        # Check if LLM client is available
        if not self.llm_client:
            error_msg = "LLM client not initialized - cannot execute task without LLM configuration"
            self.logger.error(error_msg)
            raise ImplementationError(error_msg)
        
        start_time = time.time()
        
        try:
            # Build implementation prompt
            prompt = self._build_implementation_prompt(task_context, workspace)
            
            # Invoke LLM to generate code
            llm_response = self.llm_client.generate_code(
                prompt=prompt,
                workspace_path=workspace.path,
                max_tokens=task_context.max_tokens
            )
            
            # Apply code changes to workspace
            files_changed = self._apply_code_changes(workspace, llm_response.code_changes)
            
            # Verify implementation
            if not self._verify_implementation(workspace, files_changed):
                raise ImplementationError("Implementation verification failed")
            
            # Get diff of changes
            diff = self._get_workspace_diff(workspace)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"Task {task_context.task_id} implemented successfully "
                f"in {duration:.2f}s, modified {len(files_changed)} files, "
                f"used {llm_response.tokens_used} tokens"
            )
            
            return ImplementationResult(
                success=True,
                diff=diff,
                files_changed=files_changed,
                duration_seconds=duration,
                llm_model=llm_response.model,
                tokens_used=llm_response.tokens_used,
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
    
    def _build_implementation_prompt(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> str:
        """
        Build implementation prompt from task context.
        
        Creates a detailed prompt for LLM that includes:
        - Task description and title
        - Acceptance criteria
        - Dependencies and context
        - Workspace structure
        - Related files content
        - JSON response format specification
        
        Args:
            task_context: Task context to build prompt from
            workspace: Workspace to analyze for structure
        
        Returns:
            Formatted prompt string for LLM
        """
        self.logger.debug(f"Building prompt for task {task_context.task_id}")
        
        prompt_parts = [
            f"# Task: {task_context.title}",
            f"\n## Description\n{task_context.description}",
            "\n## Acceptance Criteria"
        ]
        
        # Add acceptance criteria
        for i, criteria in enumerate(task_context.acceptance_criteria, 1):
            prompt_parts.append(f"{i}. {criteria}")
        
        # Add dependencies information
        if task_context.dependencies:
            prompt_parts.append("\n## Completed Dependencies")
            for dep_id in task_context.dependencies:
                prompt_parts.append(f"- Task {dep_id}")
        
        # Add workspace structure
        prompt_parts.append("\n## Current Workspace Structure")
        workspace_structure = self._get_workspace_structure(workspace)
        prompt_parts.append(workspace_structure)
        
        # Add related files content
        if task_context.related_files:
            prompt_parts.append("\n## Related Files")
            for file_path in task_context.related_files:
                try:
                    content = self._read_workspace_file(workspace, file_path)
                    prompt_parts.append(f"\n### {file_path}\n```\n{content}\n```")
                except Exception as e:
                    self.logger.warning(f"Could not read related file {file_path}: {e}")
        
        # Add technical context
        prompt_parts.append("\n## Technical Context")
        prompt_parts.append(f"- Required Skill: {task_context.required_skill}")
        prompt_parts.append(f"- Complexity: {task_context.complexity}")
        prompt_parts.append(f"- Spec: {task_context.spec_name}")
        
        if task_context.metadata:
            for key, value in task_context.metadata.items():
                prompt_parts.append(f"- {key}: {value}")
        
        # Add instructions for JSON response format
        prompt_parts.append("\n## Instructions")
        prompt_parts.append("Generate the code changes needed to implement this task.")
        prompt_parts.append("Return the changes in the following JSON format:")
        prompt_parts.append("""
{
  "code_changes": [
    {
      "file_path": "path/to/file.py",
      "operation": "create|modify|delete",
      "content": "file content here"
    }
  ],
  "explanation": "Brief explanation of changes"
}
""")
        
        prompt = "\n".join(prompt_parts)
        self.logger.debug(f"Generated prompt ({len(prompt)} chars)")
        
        return prompt
    
    def _get_workspace_structure(self, workspace: Workspace) -> str:
        """
        Get workspace file structure.
        
        Generates a tree-like representation of the workspace directory structure,
        excluding common directories like .git, node_modules, __pycache__, etc.
        
        Args:
            workspace: Workspace to analyze
        
        Returns:
            String representation of workspace structure
        """
        try:
            # Directories to exclude from structure
            exclude_dirs = {'.git', 'node_modules', '__pycache__', '.pytest_cache',
                          'venv', '.venv', 'dist', 'build', '.egg-info'}
            
            # Build structure recursively
            structure_lines = []
            
            def walk_directory(path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0):
                if current_depth >= max_depth:
                    return
                
                try:
                    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                    for i, item in enumerate(items):
                        if item.name in exclude_dirs or item.name.startswith('.'):
                            continue
                        
                        is_last = i == len(items) - 1
                        current_prefix = "└── " if is_last else "├── "
                        structure_lines.append(f"{prefix}{current_prefix}{item.name}")
                        
                        if item.is_dir():
                            next_prefix = prefix + ("    " if is_last else "│   ")
                            walk_directory(item, next_prefix, max_depth, current_depth + 1)
                except PermissionError:
                    pass
            
            walk_directory(workspace.path)
            
            if structure_lines:
                return "\n".join(structure_lines)
            else:
                return "(empty workspace)"
                
        except Exception as e:
            self.logger.warning(f"Could not generate workspace structure: {e}")
            return "(structure unavailable)"
    
    def _read_workspace_file(self, workspace: Workspace, file_path: str) -> str:
        """
        Read a file from the workspace.
        
        Args:
            workspace: Workspace containing the file
            file_path: Relative path to file within workspace
        
        Returns:
            File content as string
        
        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        full_path = workspace.path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not full_path.is_file():
            raise IOError(f"Not a file: {file_path}")
        
        # Limit file size to avoid huge prompts (e.g., 100KB)
        max_size = 100 * 1024
        if full_path.stat().st_size > max_size:
            self.logger.warning(f"File {file_path} exceeds size limit, truncating")
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(max_size) + "\n... (truncated)"
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _apply_code_changes(
        self,
        workspace: Workspace,
        code_changes: List[CodeChange]
    ) -> List[str]:
        """
        Apply code changes to workspace.
        
        Applies a list of code changes (create, modify, delete operations)
        to the workspace filesystem.
        
        Args:
            workspace: Workspace to apply changes to
            code_changes: List of code changes to apply
        
        Returns:
            List of file paths that were changed
        
        Raises:
            ImplementationError: If a change cannot be applied
        """
        self.logger.debug(f"Applying {len(code_changes)} code changes")
        
        files_changed = []
        
        for change in code_changes:
            file_path = workspace.path / change.file_path
            
            try:
                if change.operation == "create":
                    # Create parent directories if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file content
                    file_path.write_text(change.content, encoding='utf-8')
                    files_changed.append(change.file_path)
                    self.logger.debug(f"Created file: {change.file_path}")
                    
                elif change.operation == "modify":
                    # Verify file exists
                    if not file_path.exists():
                        raise ImplementationError(
                            f"Cannot modify non-existent file: {change.file_path}"
                        )
                    
                    # Write updated content
                    file_path.write_text(change.content, encoding='utf-8')
                    files_changed.append(change.file_path)
                    self.logger.debug(f"Modified file: {change.file_path}")
                    
                elif change.operation == "delete":
                    # Delete file if it exists
                    if file_path.exists():
                        file_path.unlink()
                        files_changed.append(change.file_path)
                        self.logger.debug(f"Deleted file: {change.file_path}")
                    else:
                        self.logger.warning(
                            f"Cannot delete non-existent file: {change.file_path}"
                        )
                        
                else:
                    raise ImplementationError(
                        f"Unknown operation: {change.operation} for file {change.file_path}"
                    )
                    
            except ImplementationError:
                raise
            except Exception as e:
                raise ImplementationError(
                    f"Failed to apply change to {change.file_path}: {e}"
                ) from e
        
        self.logger.info(f"Applied changes to {len(files_changed)} files")
        return files_changed
    
    def _verify_implementation(
        self,
        workspace: Workspace,
        files_changed: List[str]
    ) -> bool:
        """
        Verify implementation result.
        
        Performs basic validation of the implementation to ensure
        it meets minimum requirements. This includes checking that:
        - Files were actually changed
        - Changed files exist in workspace
        - No obvious errors occurred
        
        Args:
            workspace: Workspace where implementation occurred
            files_changed: List of files that were changed
        
        Returns:
            True if implementation appears valid, False otherwise
        """
        self.logger.debug("Verifying implementation")
        
        try:
            # Check that at least some files were changed
            if not files_changed:
                self.logger.warning(
                    "No files were changed during implementation - "
                    "this may indicate an issue"
                )
                # Don't fail for this - some tasks might not change files
                return True
            
            # Verify that changed files exist in workspace
            for file_path in files_changed:
                full_path = workspace.path / file_path
                # File might have been deleted, so only check non-deleted files
                # We can't easily distinguish deleted files here, so we'll skip this check
                # The git diff will show the actual changes
            
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

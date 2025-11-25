"""
Workspace Manager for Agent Runner.

This module provides Git operations for the Agent Runner, including
workspace preparation, commit management, push operations with retry,
and rollback functionality.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional

from .config import RetryConfig
from .exceptions import WorkspacePreparationError, PushError
from .models import Workspace, PushResult


class WorkspaceManager:
    """
    Manages Git operations for Agent Runner workspaces.
    
    Provides methods for preparing workspaces (checkout, fetch, rebase, branch creation),
    committing changes, pushing with retry logic, getting diffs, and rolling back changes.
    """
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        Initialize WorkspaceManager.
        
        Args:
            retry_config: Configuration for retry behavior. If None, uses default config.
        """
        self.retry_config = retry_config or RetryConfig()
    
    def prepare_workspace(
        self,
        slot_path: Path,
        branch_name: str,
        base_branch: str = "main"
    ) -> Workspace:
        """
        Prepare workspace for task execution.
        
        Performs the following Git operations:
        1. git checkout <base_branch>
        2. git fetch origin
        3. git rebase origin/<base_branch>
        4. git checkout -b <branch_name>
        
        Args:
            slot_path: Path to the workspace slot
            branch_name: Name of the new branch to create
            base_branch: Base branch to rebase from (default: "main")
            
        Returns:
            Workspace object with path and branch information
            
        Raises:
            WorkspacePreparationError: If any Git operation fails
            
        Requirements: 2.2, 2.3, 2.4, 2.5
        """
        try:
            # 1. Checkout base branch
            self._run_git_command(
                ["checkout", base_branch],
                cwd=slot_path,
                error_msg=f"Failed to checkout {base_branch}"
            )
            
            # 2. Fetch latest changes
            self._run_git_command(
                ["fetch", "origin"],
                cwd=slot_path,
                error_msg="Failed to fetch from origin"
            )
            
            # 3. Rebase on latest base branch
            self._run_git_command(
                ["rebase", f"origin/{base_branch}"],
                cwd=slot_path,
                error_msg=f"Failed to rebase on origin/{base_branch}"
            )
            
            # 4. Create and checkout new branch
            self._run_git_command(
                ["checkout", "-b", branch_name],
                cwd=slot_path,
                error_msg=f"Failed to create branch {branch_name}"
            )
            
            return Workspace(
                path=slot_path,
                branch_name=branch_name,
                base_branch=base_branch
            )
            
        except subprocess.CalledProcessError as e:
            raise WorkspacePreparationError(
                f"Workspace preparation failed: {str(e)}"
            ) from e
    
    def commit_changes(
        self,
        workspace: Workspace,
        commit_message: str
    ) -> str:
        """
        Commit changes in the workspace.
        
        Performs:
        1. git add .
        2. git commit -m "<commit_message>"
        
        Args:
            workspace: Workspace object
            commit_message: Commit message to use
            
        Returns:
            Commit hash of the created commit
            
        Raises:
            WorkspacePreparationError: If commit operation fails
            
        Requirements: 2.2, 2.3, 2.4, 2.5
        """
        try:
            # Stage all changes
            self._run_git_command(
                ["add", "."],
                cwd=workspace.path,
                error_msg="Failed to stage changes"
            )
            
            # Commit changes
            self._run_git_command(
                ["commit", "-m", commit_message],
                cwd=workspace.path,
                error_msg="Failed to commit changes"
            )
            
            # Get commit hash
            result = self._run_git_command(
                ["rev-parse", "HEAD"],
                cwd=workspace.path,
                error_msg="Failed to get commit hash",
                capture_output=True
            )
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            raise WorkspacePreparationError(
                f"Failed to commit changes: {str(e)}"
            ) from e
    
    def get_diff(self, workspace: Workspace) -> str:
        """
        Get diff of changes in the workspace.
        
        Returns the diff between the current state and the base branch.
        
        Args:
            workspace: Workspace object
            
        Returns:
            Diff output as string
            
        Raises:
            WorkspacePreparationError: If diff operation fails
            
        Requirements: 2.2, 2.3, 2.4, 2.5
        """
        try:
            result = self._run_git_command(
                ["diff", f"origin/{workspace.base_branch}...HEAD"],
                cwd=workspace.path,
                error_msg="Failed to get diff",
                capture_output=True
            )
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            raise WorkspacePreparationError(
                f"Failed to get diff: {str(e)}"
            ) from e

    
    def push_branch(
        self,
        workspace: Workspace,
        branch_name: str
    ) -> PushResult:
        """
        Push branch to remote with retry logic.
        
        Attempts to push the branch to origin with exponential backoff retry.
        Uses the retry configuration provided during initialization.
        
        Args:
            workspace: Workspace object
            branch_name: Name of the branch to push
            
        Returns:
            PushResult with success status, commit hash, and retry count
            
        Raises:
            PushError: If push fails after all retry attempts
            
        Requirements: 5.4, 5.5, 8.2
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.retry_config.max_retries:
            try:
                # Attempt to push
                self._run_git_command(
                    ["push", "-u", "origin", branch_name],
                    cwd=workspace.path,
                    error_msg=f"Failed to push branch {branch_name}"
                )
                
                # Get commit hash
                result = self._run_git_command(
                    ["rev-parse", "HEAD"],
                    cwd=workspace.path,
                    error_msg="Failed to get commit hash",
                    capture_output=True
                )
                commit_hash = result.stdout.strip()
                
                return PushResult(
                    success=True,
                    branch_name=branch_name,
                    commit_hash=commit_hash,
                    retry_count=retry_count,
                    error=None
                )
                
            except subprocess.CalledProcessError as e:
                last_error = str(e)
                retry_count += 1
                
                if retry_count <= self.retry_config.max_retries:
                    # Calculate delay with exponential backoff
                    delay = self.retry_config.get_delay(retry_count - 1)
                    time.sleep(delay)
                else:
                    # Max retries exceeded
                    break
        
        # All retries failed
        raise PushError(
            f"Failed to push branch {branch_name} after {retry_count} attempts. "
            f"Last error: {last_error}"
        )
    
    def rollback(self, workspace: Workspace) -> None:
        """
        Rollback changes in the workspace.
        
        Performs a hard reset to the base branch, discarding all local changes.
        
        Args:
            workspace: Workspace object
            
        Raises:
            WorkspacePreparationError: If rollback operation fails
            
        Requirements: 8.1
        """
        try:
            # Hard reset to base branch
            self._run_git_command(
                ["reset", "--hard", f"origin/{workspace.base_branch}"],
                cwd=workspace.path,
                error_msg="Failed to rollback changes"
            )
            
            # Clean untracked files
            self._run_git_command(
                ["clean", "-fd"],
                cwd=workspace.path,
                error_msg="Failed to clean untracked files"
            )
            
        except subprocess.CalledProcessError as e:
            raise WorkspacePreparationError(
                f"Failed to rollback workspace: {str(e)}"
            ) from e
    
    def _run_git_command(
        self,
        args: list[str],
        cwd: Path,
        error_msg: str,
        capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run a Git command with error handling.
        
        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory for the command
            error_msg: Error message to use if command fails
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CompletedProcess object if capture_output=True
            
        Raises:
            subprocess.CalledProcessError: If command fails
        """
        cmd = ["git"] + args
        
        if capture_output:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return result
        else:
            subprocess.run(
                cmd,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return subprocess.CompletedProcess(cmd, 0)

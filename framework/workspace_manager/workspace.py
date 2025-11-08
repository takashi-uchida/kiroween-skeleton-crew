"""Individual workspace management for spec task execution.

This module provides the Workspace class that represents a single isolated
workspace for executing spec tasks with git operations.
"""

from pathlib import Path
from typing import List, Optional

from .branch_strategy import BranchStrategy
from .git_operations import GitOperations, GitOperationError


class WorkspaceError(Exception):
    """Raised when a workspace operation fails."""
    pass


class Workspace:
    """Represents a single workspace instance with git operations.
    
    A workspace is an isolated directory containing a cloned repository
    where spec tasks are executed. Each workspace manages its own git
    branches and commits following the Spirit Protocol.
    """
    
    def __init__(self, path: Path, spec_name: str, git_ops: GitOperations):
        """Initialize workspace with path and git operations.
        
        Args:
            path: Path to the workspace directory
            spec_name: Name of the spec this workspace is for
            git_ops: GitOperations instance for this workspace
        """
        self.path = Path(path)
        self.spec_name = spec_name
        self.git_ops = git_ops
    
    def create_task_branch(self, task_id: str, task_description: str) -> str:
        """Create and checkout feature branch for task.
        
        Uses BranchStrategy to generate a properly formatted branch name
        following the pattern: feature/task-{spec-id}-{task-number}-{description}
        
        Args:
            task_id: Task identifier (e.g., "2", "2.1")
            task_description: Brief description of the task
            
        Returns:
            Name of the created branch
            
        Raises:
            WorkspaceError: If branch creation fails or working directory is dirty
            
        Example:
            >>> workspace.create_task_branch("2.1", "implement workspace class")
            'feature/task-kiro-workspace-2.1-implement-workspace-class'
        """
        # Check if working directory is clean before creating branch
        try:
            if not self.git_ops.is_clean():
                raise WorkspaceError(
                    "Working directory has uncommitted changes. "
                    "Please commit or stash changes before creating a new branch."
                )
        except GitOperationError as e:
            raise WorkspaceError(f"Failed to check working directory status: {str(e)}") from e
        
        # Generate branch name using BranchStrategy
        branch_name = BranchStrategy.generate_branch_name(
            spec_id=self.spec_name,
            task_number=task_id,
            description=task_description
        )
        
        # Create and checkout the branch
        try:
            self.git_ops.create_branch(branch_name, checkout=True)
            return branch_name
        except GitOperationError as e:
            raise WorkspaceError(f"Failed to create task branch: {str(e)}") from e
    
    def commit_task(
        self,
        task_id: str,
        scope: str,
        description: str,
        files: Optional[List[Path]] = None
    ) -> None:
        """Commit changes following Spirit Protocol format.
        
        Creates a commit with a message following the Spirit Protocol:
        spirit(scope): spell description
        
        The task ID is included in the commit body for traceability.
        
        Args:
            task_id: Task identifier for traceability (e.g., "2.1")
            scope: Scope of the change (e.g., "workspace", "git", "state")
            description: Description of what the commit does
            files: Optional list of specific files to commit. If None, commits all changes.
            
        Raises:
            WorkspaceError: If commit operation fails
            
        Example:
            >>> workspace.commit_task(
            ...     task_id="2.1",
            ...     scope="workspace",
            ...     description="implement workspace class",
            ...     files=[Path("framework/workspace_manager/workspace.py")]
            ... )
        """
        # Generate Spirit Protocol commit message
        commit_message = BranchStrategy.generate_commit_message(
            scope=scope,
            description=description,
            task_id=task_id
        )
        
        # Commit the changes
        try:
            self.git_ops.commit(message=commit_message, files=files)
        except GitOperationError as e:
            raise WorkspaceError(f"Failed to commit task changes: {str(e)}") from e
    
    def push_branch(self, branch_name: str) -> None:
        """Push feature branch to remote.
        
        Pushes the specified branch to the remote repository with
        upstream tracking enabled.
        
        Args:
            branch_name: Name of the branch to push
            
        Raises:
            WorkspaceError: If push operation fails
            
        Example:
            >>> workspace.push_branch("feature/task-kiro-workspace-2.1-implement-workspace-class")
        """
        try:
            self.git_ops.push(branch=branch_name, set_upstream=True)
        except GitOperationError as e:
            raise WorkspaceError(f"Failed to push branch: {str(e)}") from e
    
    def get_current_branch(self) -> str:
        """Get name of current branch.
        
        Returns:
            Name of the currently checked out branch
            
        Raises:
            WorkspaceError: If unable to determine current branch
            
        Example:
            >>> workspace.get_current_branch()
            'feature/task-kiro-workspace-2.1-implement-workspace-class'
        """
        try:
            return self.git_ops.get_current_branch()
        except GitOperationError as e:
            raise WorkspaceError(f"Failed to get current branch: {str(e)}") from e
    
    def is_clean(self) -> bool:
        """Check if working directory has uncommitted changes.
        
        Returns:
            True if working directory is clean (no uncommitted changes),
            False otherwise
            
        Raises:
            WorkspaceError: If unable to check working directory status
            
        Example:
            >>> workspace.is_clean()
            True
        """
        try:
            return self.git_ops.is_clean()
        except GitOperationError as e:
            raise WorkspaceError(f"Failed to check working directory status: {str(e)}") from e

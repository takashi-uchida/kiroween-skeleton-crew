"""Workspace orchestrator for managing multiple isolated spec workspaces.

This module provides the WorkspaceManager class that orchestrates the lifecycle
of multiple workspace instances, handling repository cloning, state tracking,
and cleanup operations.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .git_operations import GitOperations, GitOperationError
from .gitignore_manager import (
    add_workspace_to_gitignore,
    initialize_workspace_gitignore,
    GitignoreManagerError
)
from .models import WorkspaceConfig, WorkspaceInfo
from .state_tracker import StateTracker
from .workspace import Workspace


class WorkspaceManagerError(Exception):
    """Raised when a workspace manager operation fails."""
    pass


class WorkspaceManager:
    """Main orchestrator for workspace lifecycle management.
    
    WorkspaceManager handles the creation, retrieval, listing, and cleanup
    of isolated workspace directories for spec task execution. Each workspace
    contains a cloned repository and maintains its own git state.
    """
    
    def __init__(self, config: WorkspaceConfig):
        """Initialize WorkspaceManager with configuration.
        
        Args:
            config: WorkspaceConfig instance with paths and settings
        """
        self.config = config
        self.state_tracker = StateTracker(config.state_file)
        
        # Ensure base path exists
        Path(config.base_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize .gitignore with workspace patterns and state file
        try:
            initialize_workspace_gitignore(
                Path(config.gitignore_path),
                Path(config.state_file)
            )
        except GitignoreManagerError as e:
            # Log warning but don't fail initialization
            print(f"Warning: Failed to initialize .gitignore: {str(e)}")
    
    def _get_workspace_path(self, spec_name: str) -> Path:
        """Generate workspace directory path for a spec.
        
        Args:
            spec_name: Name of the spec
            
        Returns:
            Path to the workspace directory
        """
        return Path(self.config.base_path) / f"workspace-{spec_name}"
    
    def _update_gitignore(self, workspace_path: Path) -> None:
        """Add workspace directory to .gitignore to prevent nested repository issues.
        
        Args:
            workspace_path: Path to the workspace directory to add
        """
        gitignore_path = Path(self.config.gitignore_path)
        
        try:
            add_workspace_to_gitignore(gitignore_path, workspace_path)
        except GitignoreManagerError as e:
            raise WorkspaceManagerError(
                f"Failed to update .gitignore: {str(e)}"
            ) from e

    def create_workspace(self, spec_name: str, repo_url: str) -> Workspace:
        """Clone repository into spec-named subdirectory.
        
        Creates a new isolated workspace by cloning the specified repository.
        The workspace directory is added to .gitignore to prevent nested
        repository issues. Checks for existing workspace before creation.
        
        Args:
            spec_name: Name of the spec (used for directory naming)
            repo_url: URL of the repository to clone
            
        Returns:
            Workspace instance for the created workspace
            
        Raises:
            WorkspaceManagerError: If workspace already exists or creation fails
            
        Example:
            >>> manager = WorkspaceManager(config)
            >>> workspace = manager.create_workspace(
            ...     "kiro-workspace-task-execution",
            ...     "https://github.com/user/repo.git"
            ... )
        """
        # Check if workspace already exists
        existing_workspace = self.state_tracker.load_workspace(spec_name)
        if existing_workspace is not None:
            raise WorkspaceManagerError(
                f"Workspace for spec '{spec_name}' already exists at "
                f"{existing_workspace.workspace_path}. Use get_workspace() to "
                f"retrieve it or cleanup_workspace() to remove it first."
            )
        
        # Generate workspace path
        workspace_path = self._get_workspace_path(spec_name)
        
        # Check if directory already exists on filesystem
        if workspace_path.exists():
            raise WorkspaceManagerError(
                f"Directory {workspace_path} already exists. "
                f"Please remove it manually or use a different spec name."
            )
        
        # Clone the repository
        try:
            # Use a temporary GitOperations instance for cloning
            # (cwd doesn't matter for clone operation)
            temp_git_ops = GitOperations(Path.cwd())
            temp_git_ops.clone(repo_url, workspace_path)
        except GitOperationError as e:
            # Clean up partial clone if it exists
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise WorkspaceManagerError(
                f"Failed to clone repository: {str(e)}"
            ) from e
        
        # Update .gitignore
        try:
            self._update_gitignore(workspace_path)
        except Exception as e:
            # Log warning but don't fail - workspace is still usable
            print(f"Warning: Failed to update .gitignore: {str(e)}")
        
        # Create GitOperations instance for the workspace
        git_ops = GitOperations(workspace_path)
        
        # Get the current branch (usually 'main' or 'master')
        try:
            current_branch = git_ops.get_current_branch()
        except GitOperationError:
            current_branch = "main"  # Default fallback
        
        # Create workspace info
        workspace_info = WorkspaceInfo(
            spec_name=spec_name,
            workspace_path=workspace_path,
            repo_url=repo_url,
            current_branch=current_branch,
            created_at=datetime.utcnow().isoformat() + "Z",
            tasks_completed=[],
            status="active"
        )
        
        # Save to state
        self.state_tracker.save_workspace(workspace_info)
        
        # Create and return Workspace instance
        return Workspace(
            path=workspace_path,
            spec_name=spec_name,
            git_ops=git_ops
        )
    
    def get_workspace(self, spec_name: str) -> Optional[Workspace]:
        """Retrieve existing workspace by spec name.
        
        Loads workspace information from state and creates a Workspace
        instance if the workspace exists.
        
        Args:
            spec_name: Name of the spec to retrieve workspace for
            
        Returns:
            Workspace instance if found, None otherwise
            
        Example:
            >>> manager = WorkspaceManager(config)
            >>> workspace = manager.get_workspace("kiro-workspace-task-execution")
            >>> if workspace:
            ...     print(f"Found workspace at {workspace.path}")
        """
        # Load workspace info from state
        workspace_info = self.state_tracker.load_workspace(spec_name)
        
        if workspace_info is None:
            return None
        
        # Verify workspace directory still exists
        if not workspace_info.workspace_path.exists():
            # Workspace was deleted externally, clean up state
            self.state_tracker.remove_workspace(spec_name)
            return None
        
        # Create GitOperations instance
        git_ops = GitOperations(workspace_info.workspace_path)
        
        # Create and return Workspace instance
        return Workspace(
            path=workspace_info.workspace_path,
            spec_name=spec_name,
            git_ops=git_ops
        )
    
    def list_workspaces(self) -> List[WorkspaceInfo]:
        """List all active workspaces and their status.
        
        Returns a list of WorkspaceInfo objects containing details about
        each tracked workspace including path, status, and completion info.
        
        Returns:
            List of WorkspaceInfo instances for all tracked workspaces
            
        Example:
            >>> manager = WorkspaceManager(config)
            >>> workspaces = manager.list_workspaces()
            >>> for ws in workspaces:
            ...     print(f"{ws.spec_name}: {ws.status} - {len(ws.tasks_completed)} tasks completed")
        """
        return self.state_tracker.list_all()
    
    def cleanup_workspace(self, spec_name: str, force: bool = False) -> None:
        """Remove workspace directory and update state.
        
        Deletes the workspace directory from the filesystem and removes
        the workspace from state tracking. If force=False, will check for
        uncommitted changes before deletion.
        
        Args:
            spec_name: Name of the spec to cleanup workspace for
            force: If True, delete even if there are uncommitted changes
            
        Raises:
            WorkspaceManagerError: If workspace not found or cleanup fails
            
        Example:
            >>> manager = WorkspaceManager(config)
            >>> manager.cleanup_workspace("kiro-workspace-task-execution")
            >>> # Or force cleanup regardless of uncommitted changes
            >>> manager.cleanup_workspace("kiro-workspace-task-execution", force=True)
        """
        # Load workspace info
        workspace_info = self.state_tracker.load_workspace(spec_name)
        
        if workspace_info is None:
            raise WorkspaceManagerError(
                f"Workspace for spec '{spec_name}' not found in state"
            )
        
        workspace_path = workspace_info.workspace_path
        
        # Check if directory exists
        if not workspace_path.exists():
            # Directory already deleted, just clean up state
            self.state_tracker.remove_workspace(spec_name)
            return
        
        # If not forcing, check for uncommitted changes
        if not force:
            try:
                git_ops = GitOperations(workspace_path)
                if not git_ops.is_clean():
                    raise WorkspaceManagerError(
                        f"Workspace has uncommitted changes. "
                        f"Use force=True to delete anyway or commit changes first."
                    )
            except GitOperationError as e:
                # If we can't check status, warn but allow deletion with force
                if not force:
                    raise WorkspaceManagerError(
                        f"Unable to check workspace status: {str(e)}. "
                        f"Use force=True to delete anyway."
                    ) from e
        
        # Remove the workspace directory
        try:
            shutil.rmtree(workspace_path)
        except Exception as e:
            raise WorkspaceManagerError(
                f"Failed to remove workspace directory: {str(e)}"
            ) from e
        
        # Remove from state tracking
        self.state_tracker.remove_workspace(spec_name)

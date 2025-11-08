"""Workspace management for NecroCode spirits."""

This package provides components for managing isolated workspace directories,
git operations, branch strategies, and state tracking for spec-driven development.
"""

from .branch_strategy import BranchStrategy
from .config_manager import ConfigManager, ConfigValidationError
from .git_operations import GitOperations, GitOperationError
from .gitignore_manager import (
    append_to_gitignore,
    add_workspace_to_gitignore,
    add_workspace_state_to_gitignore,
    initialize_workspace_gitignore,
    GitignoreManagerError
)
from .models import WorkspaceConfig, WorkspaceInfo
from .state_tracker import StateTracker
from .workspace import Workspace, WorkspaceError
from .workspace_manager import WorkspaceManager, WorkspaceManagerError

__all__ = [
    # Core classes
    'WorkspaceManager',
    'Workspace',
    'BranchStrategy',
    'GitOperations',
    'StateTracker',
    'ConfigManager',
    
    # Data models
    'WorkspaceConfig',
    'WorkspaceInfo',
    
    # Gitignore utilities
    'append_to_gitignore',
    'add_workspace_to_gitignore',
    'add_workspace_state_to_gitignore',
    'initialize_workspace_gitignore',
    
    # Exceptions
    'WorkspaceManagerError',
    'WorkspaceError',
    'GitOperationError',
    'GitignoreManagerError',
    'ConfigValidationError',
]

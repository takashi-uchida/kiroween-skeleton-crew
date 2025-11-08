"""Workspace management system for isolated spec task execution.

This package provides components for managing isolated workspace directories,
git operations, branch strategies, and state tracking for spec-driven development.

Two main workspace management approaches:
- WorkspaceOrchestrator: Manages multiple isolated workspace directories for spec execution
- SpiritWorkspaceManager: Handles branch naming and commit formatting for spirit agents
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
from .workspace_manager import (
    WorkspaceOrchestrator,
    SpiritWorkspaceManager,
    WorkspaceManagerError
)

__all__ = [
    # Core orchestration classes
    'WorkspaceOrchestrator',
    'SpiritWorkspaceManager',
    'Workspace',
    
    # Utilities
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

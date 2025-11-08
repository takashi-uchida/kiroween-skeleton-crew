"""Utilities for managing .gitignore entries for workspace directories.

This module provides helper functions to append workspace directories and
state files to .gitignore, with duplicate entry prevention.
"""

from pathlib import Path
from typing import List, Optional


class GitignoreManagerError(Exception):
    """Raised when a .gitignore operation fails."""
    pass


def _read_gitignore_entries(gitignore_path: Path) -> List[str]:
    """Read existing entries from .gitignore file.
    
    Args:
        gitignore_path: Path to the .gitignore file
        
    Returns:
        List of lines from the .gitignore file
    """
    if not gitignore_path.exists():
        return []
    
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        return f.read().splitlines()


def _normalize_entry(entry: str) -> str:
    """Normalize a .gitignore entry for comparison.
    
    Removes trailing slashes and whitespace for consistent comparison.
    
    Args:
        entry: The .gitignore entry to normalize
        
    Returns:
        Normalized entry string
    """
    return entry.rstrip('/').strip()


def _entry_exists(entry: str, existing_lines: List[str]) -> bool:
    """Check if an entry already exists in .gitignore.
    
    Performs normalized comparison to handle variations like trailing slashes.
    
    Args:
        entry: The entry to check for
        existing_lines: List of existing .gitignore lines
        
    Returns:
        True if entry exists, False otherwise
    """
    normalized_entry = _normalize_entry(entry)
    
    for line in existing_lines:
        # Skip comments and empty lines
        if line.strip().startswith('#') or not line.strip():
            continue
        
        if _normalize_entry(line) == normalized_entry:
            return True
    
    return False


def append_to_gitignore(
    gitignore_path: Path,
    entries: List[str],
    comment: Optional[str] = None
) -> List[str]:
    """Append entries to .gitignore with duplicate prevention.
    
    Adds the specified entries to the .gitignore file, ensuring no duplicates
    are created. Optionally adds a comment before the entries.
    
    Args:
        gitignore_path: Path to the .gitignore file
        entries: List of entries to add (e.g., ["workspace-*/", ".kiro/state.json"])
        comment: Optional comment to add before the entries
        
    Returns:
        List of entries that were actually added (excludes duplicates)
        
    Raises:
        GitignoreManagerError: If unable to write to .gitignore
        
    Example:
        >>> added = append_to_gitignore(
        ...     Path(".gitignore"),
        ...     ["workspace-*/", ".kiro/workspace-state.json"],
        ...     comment="Kiro workspace directories"
        ... )
        >>> print(f"Added {len(added)} entries")
    """
    # Create .gitignore if it doesn't exist
    if not gitignore_path.exists():
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.touch()
    
    # Read existing entries
    try:
        existing_lines = _read_gitignore_entries(gitignore_path)
    except Exception as e:
        raise GitignoreManagerError(
            f"Failed to read .gitignore: {str(e)}"
        ) from e
    
    # Filter out entries that already exist
    entries_to_add = [
        entry for entry in entries
        if not _entry_exists(entry, existing_lines)
    ]
    
    # Nothing to add
    if not entries_to_add:
        return []
    
    # Write new entries
    try:
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            # Add newline if file doesn't end with one
            if existing_lines and existing_lines[-1] != '':
                f.write('\n')
            
            # Add comment if provided
            if comment:
                f.write(f"\n# {comment}\n")
            
            # Add entries
            for entry in entries_to_add:
                f.write(f"{entry}\n")
    except Exception as e:
        raise GitignoreManagerError(
            f"Failed to write to .gitignore: {str(e)}"
        ) from e
    
    return entries_to_add


def add_workspace_to_gitignore(
    gitignore_path: Path,
    workspace_path: Path
) -> bool:
    """Add a specific workspace directory to .gitignore.
    
    Adds the workspace directory to .gitignore, using a relative path
    if possible. Prevents duplicate entries.
    
    Args:
        gitignore_path: Path to the .gitignore file
        workspace_path: Path to the workspace directory to add
        
    Returns:
        True if entry was added, False if it already existed
        
    Raises:
        GitignoreManagerError: If unable to write to .gitignore
        
    Example:
        >>> added = add_workspace_to_gitignore(
        ...     Path(".gitignore"),
        ...     Path("workspace-kiro-task-execution")
        ... )
    """
    # Determine the relative path from .gitignore location to workspace
    try:
        relative_path = workspace_path.relative_to(gitignore_path.parent)
        entry = f"{relative_path}/"
    except ValueError:
        # If not relative, use the workspace path as-is
        entry = f"{workspace_path}/"
    
    added_entries = append_to_gitignore(gitignore_path, [entry])
    return len(added_entries) > 0


def add_workspace_state_to_gitignore(
    gitignore_path: Path,
    state_file_path: Path
) -> bool:
    """Add workspace state file to .gitignore.
    
    Adds the state file to .gitignore to prevent it from being committed.
    Uses relative path if possible.
    
    Args:
        gitignore_path: Path to the .gitignore file
        state_file_path: Path to the state file to add
        
    Returns:
        True if entry was added, False if it already existed
        
    Raises:
        GitignoreManagerError: If unable to write to .gitignore
        
    Example:
        >>> added = add_workspace_state_to_gitignore(
        ...     Path(".gitignore"),
        ...     Path(".kiro/workspace-state.json")
        ... )
    """
    # Determine the relative path from .gitignore location to state file
    try:
        relative_path = state_file_path.relative_to(gitignore_path.parent)
        entry = str(relative_path)
    except ValueError:
        # If not relative, use the state file path as-is
        entry = str(state_file_path)
    
    added_entries = append_to_gitignore(gitignore_path, [entry])
    return len(added_entries) > 0


def initialize_workspace_gitignore(
    gitignore_path: Path,
    state_file_path: Path
) -> None:
    """Initialize .gitignore with workspace-related entries.
    
    Adds common workspace patterns and the state file to .gitignore.
    This should be called once during workspace manager initialization.
    
    Args:
        gitignore_path: Path to the .gitignore file
        state_file_path: Path to the state file
        
    Raises:
        GitignoreManagerError: If unable to write to .gitignore
        
    Example:
        >>> initialize_workspace_gitignore(
        ...     Path(".gitignore"),
        ...     Path(".kiro/workspace-state.json")
        ... )
    """
    # Determine relative path for state file
    try:
        relative_state_path = state_file_path.relative_to(gitignore_path.parent)
        state_entry = str(relative_state_path)
    except ValueError:
        state_entry = str(state_file_path)
    
    # Add workspace pattern and state file
    entries = [
        "workspace-*/",  # Pattern for all workspace directories
        state_entry      # State file
    ]
    
    append_to_gitignore(
        gitignore_path,
        entries,
        comment="Kiro workspace directories and state"
    )

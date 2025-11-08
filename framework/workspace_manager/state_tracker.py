"""State tracking and persistence for workspace management."""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .models import WorkspaceInfo


class StateTracker:
    """Manages workspace state persistence using JSON storage."""
    
    def __init__(self, state_file: Path):
        """Initialize StateTracker with path to state JSON file.
        
        Args:
            state_file: Path to the JSON file for state persistence
        """
        self.state_file = Path(state_file)
        self._ensure_state_file()
    
    def _ensure_state_file(self) -> None:
        """Ensure state file and parent directory exist."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._write_state({"workspaces": {}})
    
    def _read_state(self) -> dict:
        """Read state from JSON file with error handling.
        
        Returns:
            Dictionary containing workspace state
            
        Raises:
            ValueError: If state file is corrupted
        """
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Create backup of corrupted file
            backup_path = self.state_file.with_suffix('.json.backup')
            shutil.copy2(self.state_file, backup_path)
            raise ValueError(
                f"State file corrupted. Backup created at {backup_path}. "
                f"Error: {str(e)}"
            )
        except Exception as e:
            raise ValueError(f"Failed to read state file: {str(e)}")
    
    def _write_state(self, state: dict) -> None:
        """Write state to JSON file with backup.
        
        Args:
            state: Dictionary containing workspace state
        """
        # Create backup before writing
        if self.state_file.exists():
            backup_path = self.state_file.with_suffix('.json.bak')
            shutil.copy2(self.state_file, backup_path)
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            # Restore from backup if write fails
            backup_path = self.state_file.with_suffix('.json.bak')
            if backup_path.exists():
                shutil.copy2(backup_path, self.state_file)
            raise ValueError(f"Failed to write state file: {str(e)}")

    def save_workspace(self, workspace_info: WorkspaceInfo) -> None:
        """Persist workspace information to state file.
        
        Args:
            workspace_info: WorkspaceInfo instance to save
        """
        state = self._read_state()
        state["workspaces"][workspace_info.spec_name] = workspace_info.to_dict()
        self._write_state(state)
    
    def load_workspace(self, spec_name: str) -> Optional[WorkspaceInfo]:
        """Load workspace info from state file.
        
        Args:
            spec_name: Name of the spec to load workspace for
            
        Returns:
            WorkspaceInfo instance if found, None otherwise
        """
        state = self._read_state()
        workspace_data = state["workspaces"].get(spec_name)
        
        if workspace_data is None:
            return None
        
        return WorkspaceInfo.from_dict(workspace_data)
    
    def list_all(self) -> List[WorkspaceInfo]:
        """Return all tracked workspaces.
        
        Returns:
            List of WorkspaceInfo instances for all tracked workspaces
        """
        state = self._read_state()
        workspaces = []
        
        for workspace_data in state["workspaces"].values():
            workspaces.append(WorkspaceInfo.from_dict(workspace_data))
        
        return workspaces
    
    def remove_workspace(self, spec_name: str) -> None:
        """Remove workspace from state tracking.
        
        Args:
            spec_name: Name of the spec to remove workspace for
        """
        state = self._read_state()
        
        if spec_name in state["workspaces"]:
            del state["workspaces"][spec_name]
            self._write_state(state)
    
    def update_task_status(self, spec_name: str, task_id: str, status: str) -> None:
        """Update completion status for a task.
        
        Args:
            spec_name: Name of the spec
            task_id: Identifier for the task (e.g., "1.1", "2.3")
            status: Status to set ('completed', 'in_progress', 'failed')
            
        Raises:
            ValueError: If workspace not found
        """
        state = self._read_state()
        
        if spec_name not in state["workspaces"]:
            raise ValueError(f"Workspace '{spec_name}' not found in state")
        
        workspace_data = state["workspaces"][spec_name]
        
        # Add task to completed list if status is 'completed' and not already there
        if status == 'completed' and task_id not in workspace_data["tasks_completed"]:
            workspace_data["tasks_completed"].append(task_id)
        
        # Update workspace status if needed
        if status == 'failed':
            workspace_data["status"] = "error"
        
        self._write_state(state)

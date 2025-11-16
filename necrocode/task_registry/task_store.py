"""
TaskStore - Persistence layer for tasksets

Handles saving, loading, and managing tasksets in JSON format.
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .models import Taskset
from .exceptions import TasksetNotFoundError, TaskRegistryError


class TaskStore:
    """TaskStore manages persistence of tasksets to the filesystem"""
    
    def __init__(self, storage_dir: Path):
        """
        Initialize TaskStore
        
        Args:
            storage_dir: Directory where tasksets will be stored
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_taskset_dir(self, spec_name: str) -> Path:
        """Get the directory path for a specific taskset"""
        return self.storage_dir / spec_name
    
    def _get_taskset_file(self, spec_name: str) -> Path:
        """Get the file path for a taskset JSON file"""
        return self._get_taskset_dir(spec_name) / "taskset.json"
    
    def save_taskset(self, taskset: Taskset) -> None:
        """
        Save a taskset to JSON file
        
        Args:
            taskset: The taskset to save
            
        Raises:
            TaskRegistryError: If save operation fails
        """
        try:
            taskset_dir = self._get_taskset_dir(taskset.spec_name)
            taskset_dir.mkdir(parents=True, exist_ok=True)
            
            taskset_file = self._get_taskset_file(taskset.spec_name)
            
            # Update the updated_at timestamp
            taskset.updated_at = datetime.now()
            
            # Convert to dict and save as JSON
            data = taskset.to_dict()
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = taskset_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(taskset_file)
            
        except Exception as e:
            raise TaskRegistryError(f"Failed to save taskset '{taskset.spec_name}': {e}") from e
    
    def load_taskset(self, spec_name: str) -> Taskset:
        """
        Load a taskset from JSON file
        
        Args:
            spec_name: Name of the spec/taskset to load
            
        Returns:
            The loaded Taskset object
            
        Raises:
            TasksetNotFoundError: If taskset doesn't exist
            TaskRegistryError: If load operation fails
        """
        taskset_file = self._get_taskset_file(spec_name)
        
        if not taskset_file.exists():
            raise TasksetNotFoundError(f"Taskset '{spec_name}' not found")
        
        try:
            with open(taskset_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return Taskset.from_dict(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in taskset '{spec_name}': {e}") from e
        except Exception as e:
            raise TaskRegistryError(f"Failed to load taskset '{spec_name}': {e}") from e
    
    def list_tasksets(self) -> List[str]:
        """
        Get list of all taskset names
        
        Returns:
            List of spec names that have tasksets
        """
        tasksets = []
        
        if not self.storage_dir.exists():
            return tasksets
        
        for item in self.storage_dir.iterdir():
            if item.is_dir():
                taskset_file = item / "taskset.json"
                if taskset_file.exists():
                    tasksets.append(item.name)
        
        return sorted(tasksets)
    
    def taskset_exists(self, spec_name: str) -> bool:
        """
        Check if a taskset exists
        
        Args:
            spec_name: Name of the spec/taskset
            
        Returns:
            True if taskset exists, False otherwise
        """
        return self._get_taskset_file(spec_name).exists()
    
    def delete_taskset(self, spec_name: str) -> None:
        """
        Delete a taskset and its directory
        
        Args:
            spec_name: Name of the spec/taskset to delete
            
        Raises:
            TasksetNotFoundError: If taskset doesn't exist
            TaskRegistryError: If delete operation fails
        """
        taskset_dir = self._get_taskset_dir(spec_name)
        
        if not taskset_dir.exists():
            raise TasksetNotFoundError(f"Taskset '{spec_name}' not found")
        
        try:
            shutil.rmtree(taskset_dir)
        except Exception as e:
            raise TaskRegistryError(f"Failed to delete taskset '{spec_name}': {e}") from e
    
    def backup_taskset(self, spec_name: str, backup_dir: Path) -> Path:
        """
        Create a backup of a taskset
        
        Args:
            spec_name: Name of the spec/taskset to backup
            backup_dir: Directory where backup will be stored
            
        Returns:
            Path to the backup file
            
        Raises:
            TasksetNotFoundError: If taskset doesn't exist
            TaskRegistryError: If backup operation fails
        """
        taskset_file = self._get_taskset_file(spec_name)
        
        if not taskset_file.exists():
            raise TasksetNotFoundError(f"Taskset '{spec_name}' not found")
        
        try:
            # Create backup directory
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{spec_name}_backup_{timestamp}.json"
            backup_path = backup_dir / backup_filename
            
            # Load taskset to verify integrity
            taskset = self.load_taskset(spec_name)
            
            # Save to backup location
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(taskset.to_dict(), f, indent=2, ensure_ascii=False)
            
            return backup_path
            
        except TasksetNotFoundError:
            raise
        except Exception as e:
            raise TaskRegistryError(f"Failed to backup taskset '{spec_name}': {e}") from e
    
    def restore_taskset(self, backup_path: Path) -> str:
        """
        Restore a taskset from a backup file
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            The spec_name of the restored taskset
            
        Raises:
            TaskRegistryError: If restore operation fails
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        try:
            # Load and verify backup file
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verify integrity
            if not self._verify_backup_integrity(data):
                raise ValueError(f"Backup file integrity check failed: {backup_path}")
            
            # Create taskset from backup data
            taskset = Taskset.from_dict(data)
            
            # Save the restored taskset
            self.save_taskset(taskset)
            
            return taskset.spec_name
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in backup file: {e}") from e
        except Exception as e:
            raise TaskRegistryError(f"Failed to restore from backup: {e}") from e
    
    def _verify_backup_integrity(self, data: dict) -> bool:
        """
        Verify the integrity of a backup file
        
        Args:
            data: The parsed JSON data from backup
            
        Returns:
            True if backup is valid, False otherwise
        """
        # Check required fields
        required_fields = ['spec_name', 'version', 'created_at', 'updated_at', 'tasks']
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Verify tasks is a list
        if not isinstance(data['tasks'], list):
            return False
        
        # Verify version is an integer
        if not isinstance(data['version'], int):
            return False
        
        # Basic validation passed
        return True

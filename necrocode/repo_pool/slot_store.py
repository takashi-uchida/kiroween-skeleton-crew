"""Slot persistence layer for Repo Pool Manager."""

import json
import shutil
from pathlib import Path
from typing import List, Optional

from necrocode.repo_pool.exceptions import PoolNotFoundError, SlotNotFoundError
from necrocode.repo_pool.models import Pool, Slot


class SlotStore:
    """Handles persistence of pool and slot metadata."""
    
    def __init__(self, workspaces_dir: Path):
        """
        Initialize SlotStore.
        
        Args:
            workspaces_dir: Base directory for all workspaces
        """
        self.workspaces_dir = Path(workspaces_dir)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_pool_dir(self, repo_name: str) -> Path:
        """Get pool directory path."""
        return self.workspaces_dir / repo_name
    
    def _get_pool_file(self, repo_name: str) -> Path:
        """Get pool metadata file path."""
        return self._get_pool_dir(repo_name) / "pool.json"
    
    def _get_slot_dir(self, repo_name: str, slot_id: str) -> Path:
        """Get slot directory path."""
        # Extract slot name from slot_id (e.g., "workspace-chat-app-slot1" -> "slot1")
        slot_name = slot_id.split("-")[-1]
        return self._get_pool_dir(repo_name) / slot_name
    
    def _get_slot_file(self, repo_name: str, slot_id: str) -> Path:
        """Get slot metadata file path."""
        return self._get_slot_dir(repo_name, slot_id) / "slot.json"
    
    def save_pool(self, pool: Pool) -> None:
        """
        Save pool metadata to JSON file.
        
        Args:
            pool: Pool object to save
            
        File path: {workspaces_dir}/{repo_name}/pool.json
        """
        pool_dir = self._get_pool_dir(pool.repo_name)
        pool_dir.mkdir(parents=True, exist_ok=True)
        
        pool_file = self._get_pool_file(pool.repo_name)
        pool_data = pool.to_dict()
        
        with open(pool_file, 'w', encoding='utf-8') as f:
            json.dump(pool_data, f, indent=2, ensure_ascii=False)
    
    def load_pool(self, repo_name: str) -> Pool:
        """
        Load pool metadata from JSON file.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            Pool object
            
        Raises:
            PoolNotFoundError: If pool file doesn't exist
        """
        pool_file = self._get_pool_file(repo_name)
        
        if not pool_file.exists():
            raise PoolNotFoundError(f"Pool not found: {repo_name}")
        
        with open(pool_file, 'r', encoding='utf-8') as f:
            pool_data = json.load(f)
        
        # Load all slots for this pool
        slots = self.list_slots(repo_name)
        
        return Pool.from_dict(pool_data, slots)
    
    def save_slot(self, slot: Slot) -> None:
        """
        Save slot metadata to JSON file.
        
        Args:
            slot: Slot object to save
            
        File path: {workspaces_dir}/{repo_name}/{slot_name}/slot.json
        """
        slot_dir = self._get_slot_dir(slot.repo_name, slot.slot_id)
        slot_dir.mkdir(parents=True, exist_ok=True)
        
        slot_file = self._get_slot_file(slot.repo_name, slot.slot_id)
        slot_data = slot.to_dict()
        
        with open(slot_file, 'w', encoding='utf-8') as f:
            json.dump(slot_data, f, indent=2, ensure_ascii=False)
    
    def load_slot(self, slot_id: str) -> Slot:
        """
        Load slot metadata from JSON file.
        
        Args:
            slot_id: Slot identifier (e.g., "workspace-chat-app-slot1")
            
        Returns:
            Slot object
            
        Raises:
            SlotNotFoundError: If slot file doesn't exist
        """
        # Extract repo_name from slot_id
        # Format: "workspace-{repo_name}-{slot_name}"
        parts = slot_id.split("-")
        if len(parts) < 3:
            raise SlotNotFoundError(f"Invalid slot_id format: {slot_id}")
        
        # Reconstruct repo_name (everything between "workspace-" and last "-slotN")
        repo_name = "-".join(parts[1:-1])
        
        slot_file = self._get_slot_file(repo_name, slot_id)
        
        if not slot_file.exists():
            raise SlotNotFoundError(f"Slot not found: {slot_id}")
        
        with open(slot_file, 'r', encoding='utf-8') as f:
            slot_data = json.load(f)
        
        return Slot.from_dict(slot_data)
    
    def list_slots(self, repo_name: str) -> List[Slot]:
        """
        Get all slots in a pool.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            List of Slot objects
        """
        pool_dir = self._get_pool_dir(repo_name)
        
        if not pool_dir.exists():
            return []
        
        slots = []
        
        # Iterate through subdirectories looking for slot.json files
        for slot_dir in pool_dir.iterdir():
            if not slot_dir.is_dir():
                continue
            
            slot_file = slot_dir / "slot.json"
            if slot_file.exists():
                try:
                    with open(slot_file, 'r', encoding='utf-8') as f:
                        slot_data = json.load(f)
                    slots.append(Slot.from_dict(slot_data))
                except (json.JSONDecodeError, KeyError) as e:
                    # Skip corrupted slot files
                    print(f"Warning: Failed to load slot from {slot_file}: {e}")
                    continue
        
        return slots
    
    def delete_slot(self, slot_id: str) -> None:
        """
        Delete a slot and its directory completely.
        
        Args:
            slot_id: Slot identifier
            
        Raises:
            SlotNotFoundError: If slot doesn't exist
        """
        # Extract repo_name from slot_id
        parts = slot_id.split("-")
        if len(parts) < 3:
            raise SlotNotFoundError(f"Invalid slot_id format: {slot_id}")
        
        repo_name = "-".join(parts[1:-1])
        slot_dir = self._get_slot_dir(repo_name, slot_id)
        
        if not slot_dir.exists():
            raise SlotNotFoundError(f"Slot directory not found: {slot_id}")
        
        # Remove the entire slot directory
        shutil.rmtree(slot_dir)
    
    def pool_exists(self, repo_name: str) -> bool:
        """
        Check if a pool exists.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            True if pool exists, False otherwise
        """
        return self._get_pool_file(repo_name).exists()
    
    def slot_exists(self, slot_id: str) -> bool:
        """
        Check if a slot exists.
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            True if slot exists, False otherwise
        """
        try:
            parts = slot_id.split("-")
            if len(parts) < 3:
                return False
            
            repo_name = "-".join(parts[1:-1])
            slot_file = self._get_slot_file(repo_name, slot_id)
            return slot_file.exists()
        except Exception:
            return False

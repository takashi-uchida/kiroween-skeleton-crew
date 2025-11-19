"""
Pool Manager - Main API for Repo Pool Manager

This module provides the main PoolManager class that coordinates all
pool and slot operations including creation, allocation, cleanup, and monitoring.
"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.exceptions import (
    NoAvailableSlotError,
    PoolNotFoundError,
    SlotAllocationError,
    SlotNotFoundError,
)
from necrocode.repo_pool.git_operations import GitOperations
from necrocode.repo_pool.lock_manager import LockManager
from necrocode.repo_pool.models import (
    AllocationMetrics,
    Pool,
    PoolSummary,
    Slot,
    SlotState,
    SlotStatus,
)
from necrocode.repo_pool.slot_allocator import SlotAllocator
from necrocode.repo_pool.slot_cleaner import SlotCleaner
from necrocode.repo_pool.slot_store import SlotStore


logger = logging.getLogger(__name__)


class PoolManager:
    """
    Main API for Repo Pool Manager.
    
    PoolManager coordinates all pool and slot operations:
    - Pool creation and management
    - Slot allocation and release
    - Cleanup operations
    - Status monitoring
    - Dynamic slot addition/removal
    
    Requirements: 1.1
    """
    
    def __init__(self, config: Optional[PoolConfig] = None, auto_init_pools: bool = False):
        """
        Initialize PoolManager with all components.
        
        Args:
            config: Pool configuration (uses defaults if not provided)
            auto_init_pools: If True, automatically initialize pools from config
            
        Requirements: 1.1, 8.2
        """
        self.config = config or PoolConfig()
        
        # Ensure workspaces directory exists
        self.workspaces_dir = self.config.workspaces_dir
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.slot_store = SlotStore(self.workspaces_dir)
        self.slot_allocator = SlotAllocator(self.slot_store)
        self.git_ops = GitOperations()
        self.slot_cleaner = SlotCleaner(self.git_ops)
        
        # Initialize lock manager
        locks_dir = self.workspaces_dir / "locks"
        self.lock_manager = LockManager(locks_dir)
        
        # Metrics tracking
        self._allocation_times: Dict[str, List[float]] = {}  # repo_name -> [duration]
        self._cleanup_times: Dict[str, List[float]] = {}  # repo_name -> [duration]
        self._metrics_lock = threading.Lock()
        
        logger.info(
            f"PoolManager initialized with workspaces_dir: {self.workspaces_dir}"
        )
        
        # Auto-initialize pools from configuration if requested
        if auto_init_pools:
            self.initialize_pools_from_config()
    
    @classmethod
    def from_config_file(cls, config_file: Optional[Path] = None, auto_init_pools: bool = True) -> "PoolManager":
        """
        Create PoolManager from configuration file.
        
        Args:
            config_file: Path to configuration file (optional)
            auto_init_pools: If True, automatically initialize pools from config
            
        Returns:
            PoolManager instance with loaded configuration
            
        Requirements: 8.2
        """
        config = PoolConfig.load_from_file(config_file)
        config.validate()
        return cls(config=config, auto_init_pools=auto_init_pools)
    
    def initialize_pools_from_config(self) -> Dict[str, Pool]:
        """
        Initialize all pools defined in configuration.
        
        Creates pools that don't exist yet, skips existing pools.
        
        Returns:
            Dictionary of created pools (repo_name -> Pool)
            
        Requirements: 8.2
        """
        created_pools = {}
        
        for repo_name, pool_def in self.config.pools.items():
            try:
                # Check if pool already exists
                existing_pool = self.slot_store.load_pool(repo_name)
                if existing_pool:
                    logger.info(f"Pool '{repo_name}' already exists, skipping")
                    continue
            except PoolNotFoundError:
                pass
            
            # Create new pool
            try:
                logger.info(
                    f"Creating pool '{repo_name}' with {pool_def.num_slots} slots"
                )
                pool = self.create_pool(
                    repo_name=repo_name,
                    repo_url=pool_def.repo_url,
                    num_slots=pool_def.num_slots
                )
                created_pools[repo_name] = pool
                logger.info(f"Successfully created pool '{repo_name}'")
            except Exception as e:
                logger.error(f"Failed to create pool '{repo_name}': {e}")
        
        return created_pools
    
    def reload_config(self, config_file: Optional[Path] = None) -> None:
        """
        Reload configuration from file and apply changes.
        
        This method:
        1. Reloads configuration from file
        2. Validates new configuration
        3. Initializes new pools
        4. Updates existing pool settings where applicable
        
        Args:
            config_file: Path to configuration file (optional)
            
        Requirements: 8.3
        """
        # Reload configuration
        new_config = PoolConfig.load_from_file(config_file or self.config.config_file)
        new_config.validate()
        
        # Update configuration
        old_config = self.config
        self.config = new_config
        
        logger.info("Configuration reloaded successfully")
        
        # Initialize new pools
        self.initialize_pools_from_config()
        
        logger.info("Dynamic configuration update completed")

    # ===== Pool Management API (Task 7.2) =====
    
    def create_pool(
        self,
        repo_name: str,
        repo_url: str,
        num_slots: int
    ) -> Pool:
        """
        Create a new pool with specified number of slots.
        
        This method:
        1. Creates pool directory structure
        2. Clones repository for each slot
        3. Initializes slot metadata
        4. Saves pool and slot information
        
        Args:
            repo_name: Repository name (used as pool identifier)
            repo_url: Repository URL to clone
            num_slots: Number of slots to create
            
        Returns:
            Created Pool object
            
        Raises:
            PoolManagerError: If pool creation fails
            
        Requirements: 1.1, 1.2
        """
        logger.info(
            f"Creating pool '{repo_name}' with {num_slots} slots from {repo_url}"
        )
        
        # Check if pool already exists
        if self.slot_store.pool_exists(repo_name):
            raise ValueError(f"Pool '{repo_name}' already exists")
        
        # Create pool directory
        pool_dir = self.workspaces_dir / repo_name
        pool_dir.mkdir(parents=True, exist_ok=True)
        
        # Create slots
        slots = []
        for i in range(1, num_slots + 1):
            slot_name = f"slot{i}"
            slot_id = f"workspace-{repo_name}-{slot_name}"
            slot_path = pool_dir / slot_name
            
            logger.info(f"Creating slot {i}/{num_slots}: {slot_id}")
            
            try:
                # Clone repository
                clone_result = self.git_ops.clone_repo(repo_url, slot_path)
                if not clone_result.success:
                    raise SlotAllocationError(
                        f"Failed to clone repository for slot {slot_id}: "
                        f"{clone_result.stderr}"
                    )
                
                # Get initial git information
                current_branch = self.git_ops.get_current_branch(slot_path)
                current_commit = self.git_ops.get_current_commit(slot_path)
                
                # Create slot object
                slot = Slot(
                    slot_id=slot_id,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    slot_path=slot_path,
                    state=SlotState.AVAILABLE,
                    current_branch=current_branch,
                    current_commit=current_commit,
                )
                
                # Save slot metadata
                self.slot_store.save_slot(slot)
                slots.append(slot)
                
                logger.info(f"Successfully created slot {slot_id}")
                
            except Exception as e:
                logger.error(f"Failed to create slot {slot_id}: {e}")
                # Continue with other slots, but log the error
                raise SlotAllocationError(
                    f"Failed to create slot {slot_id}: {str(e)}"
                ) from e
        
        # Create pool object
        now = datetime.now()
        pool = Pool(
            repo_name=repo_name,
            repo_url=repo_url,
            num_slots=num_slots,
            slots=slots,
            created_at=now,
            updated_at=now,
        )
        
        # Save pool metadata
        self.slot_store.save_pool(pool)
        
        logger.info(
            f"Successfully created pool '{repo_name}' with {len(slots)} slots"
        )
        
        return pool
    
    def get_pool(self, repo_name: str) -> Pool:
        """
        Get pool by repository name.
        
        Args:
            repo_name: Repository name
            
        Returns:
            Pool object
            
        Raises:
            PoolNotFoundError: If pool doesn't exist
            
        Requirements: 1.2
        """
        logger.debug(f"Getting pool '{repo_name}'")
        return self.slot_store.load_pool(repo_name)
    
    def list_pools(self) -> List[str]:
        """
        List all pool names.
        
        Returns:
            List of repository names (pool identifiers)
            
        Requirements: 1.5
        """
        logger.debug("Listing all pools")
        
        pools = []
        
        if not self.workspaces_dir.exists():
            return pools
        
        # Iterate through workspace directories
        for pool_dir in self.workspaces_dir.iterdir():
            if not pool_dir.is_dir():
                continue
            
            # Skip locks directory
            if pool_dir.name == "locks":
                continue
            
            # Check if pool.json exists
            pool_file = pool_dir / "pool.json"
            if pool_file.exists():
                pools.append(pool_dir.name)
        
        logger.debug(f"Found {len(pools)} pool(s)")
        return pools

    # ===== Slot Allocation and Release API (Task 7.3) =====
    
    def allocate_slot(
        self,
        repo_name: str,
        metadata: Optional[Dict] = None
    ) -> Optional[Slot]:
        """
        Allocate an available slot from the pool.
        
        This method:
        1. Finds an available slot using LRU strategy
        2. Acquires lock on the slot
        3. Performs cleanup before allocation
        4. Marks slot as allocated
        5. Returns slot information
        
        Args:
            repo_name: Repository name
            metadata: Optional metadata to attach to the slot
            
        Returns:
            Allocated Slot object, or None if no slots available
            
        Raises:
            PoolNotFoundError: If pool doesn't exist
            NoAvailableSlotError: If no slots are available
            SlotAllocationError: If allocation fails
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.4, 10.5
        """
        logger.info(f"Allocating slot from pool '{repo_name}'")
        start_time = time.time()
        
        # Check if pool exists
        if not self.slot_store.pool_exists(repo_name):
            raise PoolNotFoundError(f"Pool not found: {repo_name}")
        
        # Find available slot
        slot = self.slot_allocator.find_available_slot(repo_name)
        
        if slot is None:
            logger.warning(f"No available slots in pool '{repo_name}'")
            raise NoAvailableSlotError(
                f"No available slots in pool '{repo_name}'"
            )
        
        logger.info(f"Found available slot: {slot.slot_id}")
        
        # Acquire lock and allocate
        try:
            with self.lock_manager.acquire_slot_lock(
                slot.slot_id,
                timeout=self.config.lock_timeout
            ):
                # Reload slot to ensure we have latest state
                slot = self.slot_store.load_slot(slot.slot_id)
                
                # Double-check slot is still available
                if not slot.is_available():
                    logger.warning(
                        f"Slot {slot.slot_id} no longer available "
                        f"(state: {slot.state.value})"
                    )
                    # Try to find another slot recursively
                    return self.allocate_slot(repo_name, metadata)
                
                # Perform cleanup before allocation
                logger.info(f"Cleaning up slot {slot.slot_id} before allocation")
                cleanup_result = self.slot_cleaner.cleanup_before_allocation(slot)
                
                if not cleanup_result.success:
                    logger.error(
                        f"Cleanup failed for slot {slot.slot_id}: "
                        f"{cleanup_result.errors}"
                    )
                    slot.state = SlotState.ERROR
                    self.slot_store.save_slot(slot)
                    raise SlotAllocationError(
                        f"Cleanup failed for slot {slot.slot_id}: "
                        f"{', '.join(cleanup_result.errors)}"
                    )
                
                # Mark slot as allocated
                self.slot_allocator.mark_allocated(slot.slot_id, metadata)
                
                # Reload slot to get updated state
                slot = self.slot_store.load_slot(slot.slot_id)
                
                # Record allocation time metric
                allocation_duration = time.time() - start_time
                self._record_allocation_time(repo_name, allocation_duration)
                
                logger.info(
                    f"Successfully allocated slot {slot.slot_id} "
                    f"(allocation #{slot.allocation_count}, "
                    f"duration: {allocation_duration:.2f}s)"
                )
                
                return slot
                
        except Exception as e:
            logger.error(f"Failed to allocate slot from pool '{repo_name}': {e}")
            raise SlotAllocationError(
                f"Failed to allocate slot: {str(e)}"
            ) from e
    
    def release_slot(self, slot_id: str, cleanup: bool = True) -> None:
        """
        Release a slot back to the pool.
        
        This method:
        1. Acquires lock on the slot
        2. Performs cleanup after release (optional)
        3. Marks slot as available
        4. Releases lock
        
        Args:
            slot_id: Slot identifier
            cleanup: Whether to perform cleanup (default: True)
            
        Raises:
            SlotNotFoundError: If slot doesn't exist
            SlotAllocationError: If release fails
            
        Requirements: 2.4, 3.4
        """
        logger.info(f"Releasing slot {slot_id} (cleanup={cleanup})")
        
        try:
            with self.lock_manager.acquire_slot_lock(
                slot_id,
                timeout=self.config.lock_timeout
            ):
                # Load slot
                slot = self.slot_store.load_slot(slot_id)
                
                # Perform cleanup after release if requested
                if cleanup:
                    logger.info(f"Cleaning up slot {slot_id} after release")
                    cleanup_result = self.slot_cleaner.cleanup_after_release(slot)
                    
                    if not cleanup_result.success:
                        logger.warning(
                            f"Cleanup failed for slot {slot_id}: "
                            f"{cleanup_result.errors}"
                        )
                        # Continue with release even if cleanup fails
                
                # Mark slot as available
                self.slot_allocator.mark_available(slot_id)
                
                logger.info(f"Successfully released slot {slot_id}")
                
        except SlotNotFoundError:
            logger.error(f"Slot not found: {slot_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to release slot {slot_id}: {e}")
            raise SlotAllocationError(
                f"Failed to release slot {slot_id}: {str(e)}"
            ) from e

    # ===== Slot Status Management API (Task 7.4) =====
    
    def get_slot_status(self, slot_id: str) -> SlotStatus:
        """
        Get detailed status of a slot.
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            SlotStatus object with detailed information
            
        Raises:
            SlotNotFoundError: If slot doesn't exist
            
        Requirements: 5.1, 5.2
        """
        logger.debug(f"Getting status for slot {slot_id}")
        
        # Load slot
        slot = self.slot_store.load_slot(slot_id)
        
        # Check if slot is locked
        is_locked = self.lock_manager.is_locked(slot_id)
        
        # Calculate disk usage
        disk_usage_mb = 0.0
        if slot.slot_path.exists():
            try:
                # Calculate total size of slot directory
                total_size = sum(
                    f.stat().st_size
                    for f in slot.slot_path.rglob('*')
                    if f.is_file()
                )
                disk_usage_mb = total_size / (1024 * 1024)  # Convert to MB
            except Exception as e:
                logger.warning(f"Failed to calculate disk usage for {slot_id}: {e}")
        
        return SlotStatus(
            slot_id=slot.slot_id,
            state=slot.state,
            is_locked=is_locked,
            current_branch=slot.current_branch,
            current_commit=slot.current_commit,
            allocation_count=slot.allocation_count,
            last_allocated_at=slot.last_allocated_at,
            disk_usage_mb=disk_usage_mb,
        )
    
    def get_pool_summary(self) -> Dict[str, PoolSummary]:
        """
        Get summary of all pools.
        
        Returns:
            Dictionary mapping repo_name to PoolSummary
            
        Requirements: 5.4, 5.5
        """
        logger.debug("Getting summary of all pools")
        
        summaries = {}
        
        for repo_name in self.list_pools():
            try:
                pool = self.get_pool(repo_name)
                
                # Count slots by state
                available_count = len([
                    s for s in pool.slots if s.state == SlotState.AVAILABLE
                ])
                allocated_count = len([
                    s for s in pool.slots if s.state == SlotState.ALLOCATED
                ])
                cleaning_count = len([
                    s for s in pool.slots if s.state == SlotState.CLEANING
                ])
                error_count = len([
                    s for s in pool.slots if s.state == SlotState.ERROR
                ])
                
                # Calculate total allocations
                total_allocations = sum(s.allocation_count for s in pool.slots)
                
                # Calculate average allocation time
                # Use slot usage statistics as proxy
                total_usage_seconds = sum(s.total_usage_seconds for s in pool.slots)
                avg_allocation_time = (
                    total_usage_seconds / total_allocations
                    if total_allocations > 0
                    else 0.0
                )
                
                summary = PoolSummary(
                    repo_name=repo_name,
                    total_slots=pool.num_slots,
                    available_slots=available_count,
                    allocated_slots=allocated_count,
                    cleaning_slots=cleaning_count,
                    error_slots=error_count,
                    total_allocations=total_allocations,
                    average_allocation_time_seconds=avg_allocation_time,
                )
                
                summaries[repo_name] = summary
                
            except Exception as e:
                logger.error(f"Failed to get summary for pool '{repo_name}': {e}")
                continue
        
        logger.debug(f"Generated summaries for {len(summaries)} pool(s)")
        return summaries

    # ===== Dynamic Slot Addition and Removal (Task 7.5) =====
    
    def add_slot(self, repo_name: str) -> Slot:
        """
        Add a new slot to an existing pool.
        
        This method:
        1. Loads the existing pool
        2. Determines the next slot number
        3. Clones the repository
        4. Initializes slot metadata
        5. Updates pool metadata
        
        Args:
            repo_name: Repository name
            
        Returns:
            Created Slot object
            
        Raises:
            PoolNotFoundError: If pool doesn't exist
            SlotAllocationError: If slot creation fails
            
        Requirements: 7.1, 7.2
        """
        logger.info(f"Adding new slot to pool '{repo_name}'")
        
        # Load existing pool
        pool = self.get_pool(repo_name)
        
        # Determine next slot number
        existing_slot_numbers = []
        for slot in pool.slots:
            # Extract slot number from slot_id (e.g., "workspace-chat-app-slot3" -> 3)
            slot_name = slot.slot_id.split("-")[-1]  # "slot3"
            if slot_name.startswith("slot"):
                try:
                    slot_num = int(slot_name[4:])  # Extract number after "slot"
                    existing_slot_numbers.append(slot_num)
                except ValueError:
                    continue
        
        next_slot_num = max(existing_slot_numbers) + 1 if existing_slot_numbers else 1
        
        # Create new slot
        slot_name = f"slot{next_slot_num}"
        slot_id = f"workspace-{repo_name}-{slot_name}"
        slot_path = self.workspaces_dir / repo_name / slot_name
        
        logger.info(f"Creating new slot: {slot_id}")
        
        try:
            # Clone repository
            clone_result = self.git_ops.clone_repo(pool.repo_url, slot_path)
            if not clone_result.success:
                raise SlotAllocationError(
                    f"Failed to clone repository for slot {slot_id}: "
                    f"{clone_result.stderr}"
                )
            
            # Get initial git information
            current_branch = self.git_ops.get_current_branch(slot_path)
            current_commit = self.git_ops.get_current_commit(slot_path)
            
            # Create slot object
            slot = Slot(
                slot_id=slot_id,
                repo_name=repo_name,
                repo_url=pool.repo_url,
                slot_path=slot_path,
                state=SlotState.AVAILABLE,
                current_branch=current_branch,
                current_commit=current_commit,
            )
            
            # Save slot metadata
            self.slot_store.save_slot(slot)
            
            # Update pool metadata
            pool.num_slots += 1
            pool.slots.append(slot)
            pool.updated_at = datetime.now()
            self.slot_store.save_pool(pool)
            
            logger.info(
                f"Successfully added slot {slot_id} to pool '{repo_name}' "
                f"(total slots: {pool.num_slots})"
            )
            
            return slot
            
        except Exception as e:
            logger.error(f"Failed to add slot to pool '{repo_name}': {e}")
            raise SlotAllocationError(
                f"Failed to add slot: {str(e)}"
            ) from e
    
    def remove_slot(self, slot_id: str, force: bool = False) -> None:
        """
        Remove a slot from the pool.
        
        This method:
        1. Checks if slot is in use (unless force=True)
        2. Acquires lock on the slot
        3. Deletes slot directory
        4. Updates pool metadata
        
        Args:
            slot_id: Slot identifier
            force: Force removal even if slot is allocated (default: False)
            
        Raises:
            SlotNotFoundError: If slot doesn't exist
            SlotAllocationError: If slot is in use and force=False
            
        Requirements: 7.3, 7.4, 7.5
        """
        logger.info(f"Removing slot {slot_id} (force={force})")
        
        try:
            # Load slot
            slot = self.slot_store.load_slot(slot_id)
            
            # Check if slot is in use
            if not force and slot.state == SlotState.ALLOCATED:
                raise SlotAllocationError(
                    f"Cannot remove slot {slot_id}: slot is currently allocated. "
                    f"Use force=True to remove anyway."
                )
            
            # Acquire lock before removal
            with self.lock_manager.acquire_slot_lock(
                slot_id,
                timeout=self.config.lock_timeout
            ):
                # Delete slot directory and metadata
                self.slot_store.delete_slot(slot_id)
                
                # Update pool metadata
                pool = self.get_pool(slot.repo_name)
                pool.slots = [s for s in pool.slots if s.slot_id != slot_id]
                pool.num_slots = len(pool.slots)
                pool.updated_at = datetime.now()
                self.slot_store.save_pool(pool)
                
                logger.info(
                    f"Successfully removed slot {slot_id} from pool '{slot.repo_name}' "
                    f"(remaining slots: {pool.num_slots})"
                )
                
        except SlotNotFoundError:
            logger.error(f"Slot not found: {slot_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to remove slot {slot_id}: {e}")
            raise SlotAllocationError(
                f"Failed to remove slot {slot_id}: {str(e)}"
            ) from e

    # ===== Error Handling and Recovery (Task 9) =====
    
    def detect_long_allocated_slots(
        self,
        max_allocation_hours: int = 24
    ) -> List[Slot]:
        """
        Detect slots that have been allocated for too long.
        
        Long-allocated slots may indicate:
        - Crashed agent processes
        - Forgotten allocations
        - Deadlocks
        
        Args:
            max_allocation_hours: Maximum allocation time in hours
            
        Returns:
            List of slots allocated longer than threshold
            
        Requirements: 9.3
        """
        from datetime import timedelta
        
        logger.info(
            f"Detecting slots allocated longer than {max_allocation_hours} hours"
        )
        
        long_allocated = []
        cutoff_time = datetime.now() - timedelta(hours=max_allocation_hours)
        
        for repo_name in self.list_pools():
            try:
                pool = self.get_pool(repo_name)
                
                for slot in pool.slots:
                    if (slot.state == SlotState.ALLOCATED and
                        slot.last_allocated_at and
                        slot.last_allocated_at < cutoff_time):
                        
                        allocation_duration = datetime.now() - slot.last_allocated_at
                        logger.warning(
                            f"Slot {slot.slot_id} has been allocated for "
                            f"{allocation_duration} (threshold: {max_allocation_hours}h)"
                        )
                        long_allocated.append(slot)
                        
            except Exception as e:
                logger.error(
                    f"Error checking pool '{repo_name}' for long allocations: {e}"
                )
        
        logger.info(
            f"Found {len(long_allocated)} slot(s) allocated longer than "
            f"{max_allocation_hours} hours"
        )
        return long_allocated
    
    def detect_corrupted_slots(self) -> List[Slot]:
        """
        Detect corrupted slots.
        
        Checks all slots for:
        - Missing directories
        - Corrupted git repositories
        - Invalid metadata
        
        Returns:
            List of corrupted slots
            
        Requirements: 9.3
        """
        logger.info("Detecting corrupted slots")
        
        corrupted = []
        
        for repo_name in self.list_pools():
            try:
                pool = self.get_pool(repo_name)
                
                for slot in pool.slots:
                    # Skip slots already marked as ERROR
                    if slot.state == SlotState.ERROR:
                        corrupted.append(slot)
                        continue
                    
                    # Verify slot integrity
                    is_valid = self.slot_cleaner.verify_slot_integrity(slot)
                    
                    if not is_valid:
                        logger.warning(
                            f"Slot {slot.slot_id} failed integrity check"
                        )
                        corrupted.append(slot)
                        
            except Exception as e:
                logger.error(
                    f"Error checking pool '{repo_name}' for corruption: {e}"
                )
        
        logger.info(f"Found {len(corrupted)} corrupted slot(s)")
        return corrupted
    
    def detect_orphaned_locks(self) -> List[str]:
        """
        Detect orphaned lock files.
        
        Orphaned locks are lock files that:
        - Don't correspond to any existing slot
        - Are stale (older than configured threshold)
        
        Returns:
            List of slot IDs with orphaned locks
            
        Requirements: 9.4
        """
        logger.info("Detecting orphaned lock files")
        
        # Get all valid slot IDs
        valid_slot_ids = set()
        for repo_name in self.list_pools():
            try:
                pool = self.get_pool(repo_name)
                for slot in pool.slots:
                    valid_slot_ids.add(slot.slot_id)
            except Exception as e:
                logger.error(f"Error loading pool '{repo_name}': {e}")
        
        # Detect stale locks
        stale_locks = self.lock_manager.detect_stale_locks(
            max_age_hours=self.config.stale_lock_hours
        )
        
        # Find orphaned locks (stale locks for non-existent slots)
        orphaned = []
        for slot_id in stale_locks:
            if slot_id not in valid_slot_ids:
                logger.warning(
                    f"Found orphaned lock for non-existent slot: {slot_id}"
                )
                orphaned.append(slot_id)
        
        logger.info(
            f"Found {len(orphaned)} orphaned lock(s) out of "
            f"{len(stale_locks)} stale lock(s)"
        )
        return orphaned
    
    def detect_anomalies(
        self,
        max_allocation_hours: int = 24
    ) -> Dict[str, List]:
        """
        Detect all anomalies in the pool system.
        
        Combines detection of:
        - Long-allocated slots
        - Corrupted slots
        - Orphaned locks
        
        Args:
            max_allocation_hours: Maximum allocation time in hours
            
        Returns:
            Dictionary with anomaly types and affected items
            
        Requirements: 9.3, 9.4
        """
        logger.info("Running comprehensive anomaly detection")
        
        anomalies = {
            "long_allocated_slots": self.detect_long_allocated_slots(
                max_allocation_hours
            ),
            "corrupted_slots": self.detect_corrupted_slots(),
            "orphaned_locks": self.detect_orphaned_locks(),
        }
        
        total_anomalies = (
            len(anomalies["long_allocated_slots"]) +
            len(anomalies["corrupted_slots"]) +
            len(anomalies["orphaned_locks"])
        )
        
        logger.info(f"Anomaly detection complete: {total_anomalies} issue(s) found")
        return anomalies
    
    def recover_slot(self, slot_id: str, force: bool = False) -> bool:
        """
        Recover a slot from error state.
        
        Recovery process:
        1. Verify slot integrity
        2. If corrupted, attempt repair
        3. If repair fails and force=True, re-initialize slot
        4. Update slot state
        
        Args:
            slot_id: Slot identifier
            force: Force re-initialization if repair fails
            
        Returns:
            True if recovery succeeded, False otherwise
            
        Requirements: 9.2
        """
        logger.info(f"Attempting to recover slot {slot_id} (force={force})")
        
        try:
            # Load slot
            slot = self.slot_store.load_slot(slot_id)
            
            # Acquire lock for recovery
            with self.lock_manager.acquire_slot_lock(
                slot_id,
                timeout=self.config.lock_timeout
            ):
                # Reload slot to ensure latest state
                slot = self.slot_store.load_slot(slot_id)
                
                # Attempt repair
                logger.info(f"Repairing slot {slot_id}")
                repair_result = self.slot_cleaner.repair_slot(slot)
                
                if repair_result.success:
                    logger.info(
                        f"Successfully recovered slot {slot_id}: "
                        f"{', '.join(repair_result.actions_taken)}"
                    )
                    
                    # Save updated slot state
                    self.slot_store.save_slot(slot)
                    return True
                else:
                    logger.error(
                        f"Failed to recover slot {slot_id}: "
                        f"{', '.join(repair_result.errors)}"
                    )
                    
                    if force:
                        logger.warning(
                            f"Force recovery enabled, marking slot {slot_id} "
                            f"as available despite repair failure"
                        )
                        slot.state = SlotState.AVAILABLE
                        slot.updated_at = datetime.now()
                        self.slot_store.save_slot(slot)
                        return True
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Error during slot recovery for {slot_id}: {e}")
            return False
    
    def isolate_slot(self, slot_id: str) -> None:
        """
        Isolate a slot in error state.
        
        Marks the slot as ERROR state to prevent allocation.
        Manual intervention will be required to recover the slot.
        
        Args:
            slot_id: Slot identifier
            
        Requirements: 9.5
        """
        logger.warning(f"Isolating slot {slot_id} due to errors")
        
        try:
            # Load slot
            slot = self.slot_store.load_slot(slot_id)
            
            # Mark as error
            slot.state = SlotState.ERROR
            slot.updated_at = datetime.now()
            
            # Add metadata about isolation
            slot.metadata["isolated_at"] = datetime.now().isoformat()
            slot.metadata["isolation_reason"] = "Manual isolation or recovery failure"
            
            # Save updated state
            self.slot_store.save_slot(slot)
            
            logger.warning(
                f"Slot {slot_id} isolated and marked as ERROR. "
                f"Manual recovery required."
            )
            
        except Exception as e:
            logger.error(f"Failed to isolate slot {slot_id}: {e}")
            raise
    
    def auto_recover(
        self,
        max_allocation_hours: int = 24,
        recover_corrupted: bool = True,
        cleanup_orphaned_locks: bool = True,
        force_release_long_allocated: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically recover from detected anomalies.
        
        Recovery actions:
        1. Release long-allocated slots (if force_release_long_allocated=True)
        2. Repair corrupted slots (if recover_corrupted=True)
        3. Clean up orphaned locks (if cleanup_orphaned_locks=True)
        
        Args:
            max_allocation_hours: Maximum allocation time threshold
            recover_corrupted: Whether to attempt recovery of corrupted slots
            cleanup_orphaned_locks: Whether to clean up orphaned locks
            force_release_long_allocated: Whether to force-release long-allocated slots
            
        Returns:
            Dictionary with recovery results
            
        Requirements: 9.2, 9.5
        """
        logger.info("Starting automatic recovery process")
        
        results = {
            "long_allocated_released": 0,
            "corrupted_recovered": 0,
            "corrupted_isolated": 0,
            "orphaned_locks_cleaned": 0,
            "errors": []
        }
        
        # Detect anomalies
        anomalies = self.detect_anomalies(max_allocation_hours)
        
        # Handle long-allocated slots
        if force_release_long_allocated:
            logger.info(
                f"Force-releasing {len(anomalies['long_allocated_slots'])} "
                f"long-allocated slot(s)"
            )
            
            for slot in anomalies["long_allocated_slots"]:
                try:
                    logger.warning(
                        f"Force-releasing long-allocated slot {slot.slot_id}"
                    )
                    self.release_slot(slot.slot_id, cleanup=True)
                    results["long_allocated_released"] += 1
                except Exception as e:
                    error_msg = f"Failed to release slot {slot.slot_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        else:
            logger.info(
                f"Found {len(anomalies['long_allocated_slots'])} "
                f"long-allocated slot(s), but force_release is disabled"
            )
        
        # Handle corrupted slots
        if recover_corrupted:
            logger.info(
                f"Attempting to recover {len(anomalies['corrupted_slots'])} "
                f"corrupted slot(s)"
            )
            
            for slot in anomalies["corrupted_slots"]:
                try:
                    success = self.recover_slot(slot.slot_id, force=False)
                    
                    if success:
                        results["corrupted_recovered"] += 1
                    else:
                        # Isolate slot if recovery failed
                        logger.warning(
                            f"Recovery failed for slot {slot.slot_id}, isolating"
                        )
                        self.isolate_slot(slot.slot_id)
                        results["corrupted_isolated"] += 1
                        
                except Exception as e:
                    error_msg = f"Error recovering slot {slot.slot_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        else:
            logger.info(
                f"Found {len(anomalies['corrupted_slots'])} corrupted slot(s), "
                f"but recovery is disabled"
            )
        
        # Handle orphaned locks
        if cleanup_orphaned_locks:
            logger.info(
                f"Cleaning up {len(anomalies['orphaned_locks'])} orphaned lock(s)"
            )
            
            for slot_id in anomalies["orphaned_locks"]:
                try:
                    self.lock_manager.force_unlock(slot_id)
                    results["orphaned_locks_cleaned"] += 1
                except Exception as e:
                    error_msg = f"Failed to clean orphaned lock {slot_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        else:
            logger.info(
                f"Found {len(anomalies['orphaned_locks'])} orphaned lock(s), "
                f"but cleanup is disabled"
            )
        
        logger.info(
            f"Auto-recovery complete: "
            f"{results['long_allocated_released']} released, "
            f"{results['corrupted_recovered']} recovered, "
            f"{results['corrupted_isolated']} isolated, "
            f"{results['orphaned_locks_cleaned']} locks cleaned, "
            f"{len(results['errors'])} error(s)"
        )
        
        return results
    
    # ===== Performance Optimization (Task 10) =====
    
    def warmup_pool_parallel(
        self,
        repo_name: str,
        max_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Warmup all available slots in a pool in parallel.
        
        This method fetches latest remote state for all available slots
        concurrently, preparing them for fast allocation.
        
        Args:
            repo_name: Repository name
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with warmup results and statistics
            
        Requirements: 10.1
        """
        logger.info(f"Starting parallel warmup for pool '{repo_name}'")
        start_time = time.time()
        
        # Load pool
        pool = self.get_pool(repo_name)
        
        # Get available slots
        available_slots = [s for s in pool.slots if s.state == SlotState.AVAILABLE]
        
        if not available_slots:
            logger.warning(f"No available slots to warmup in pool '{repo_name}'")
            return {
                "repo_name": repo_name,
                "slots_warmed": 0,
                "successful": 0,
                "failed": 0,
                "duration_seconds": 0.0,
                "results": {}
            }
        
        logger.info(
            f"Warming up {len(available_slots)} available slot(s) in parallel"
        )
        
        # Perform parallel warmup
        results = self.slot_cleaner.warmup_slots_parallel(
            available_slots,
            max_workers=max_workers
        )
        
        # Count successes and failures
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful
        
        duration = time.time() - start_time
        
        logger.info(
            f"Parallel warmup complete for pool '{repo_name}': "
            f"{successful} successful, {failed} failed, "
            f"{duration:.2f}s total"
        )
        
        return {
            "repo_name": repo_name,
            "slots_warmed": len(results),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "results": results
        }
    
    def cleanup_pool_parallel(
        self,
        repo_name: str,
        operation: str = "warmup",
        max_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Cleanup all available slots in a pool in parallel.
        
        Args:
            repo_name: Repository name
            operation: Type of cleanup ("warmup", "before_allocation", or "after_release")
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with cleanup results and statistics
            
        Requirements: 10.1
        """
        logger.info(
            f"Starting parallel cleanup ({operation}) for pool '{repo_name}'"
        )
        start_time = time.time()
        
        # Load pool
        pool = self.get_pool(repo_name)
        
        # Get available slots
        available_slots = [s for s in pool.slots if s.state == SlotState.AVAILABLE]
        
        if not available_slots:
            logger.warning(f"No available slots to cleanup in pool '{repo_name}'")
            return {
                "repo_name": repo_name,
                "slots_cleaned": 0,
                "successful": 0,
                "failed": 0,
                "duration_seconds": 0.0,
                "results": {}
            }
        
        logger.info(
            f"Cleaning up {len(available_slots)} available slot(s) in parallel"
        )
        
        # Perform parallel cleanup
        results = self.slot_cleaner.cleanup_slots_parallel(
            available_slots,
            operation=operation,
            max_workers=max_workers
        )
        
        # Count successes and failures
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful
        
        duration = time.time() - start_time
        
        logger.info(
            f"Parallel cleanup complete for pool '{repo_name}': "
            f"{successful} successful, {failed} failed, "
            f"{duration:.2f}s total"
        )
        
        return {
            "repo_name": repo_name,
            "slots_cleaned": len(results),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "results": results
        }
    
    def release_slot_background(
        self,
        slot_id: str,
        cleanup: bool = True
    ) -> Optional[str]:
        """
        Release a slot with background cleanup.
        
        This method releases the slot immediately and performs cleanup
        in the background without blocking. Useful for faster slot
        release when cleanup time is not critical.
        
        Args:
            slot_id: Slot identifier
            cleanup: Whether to perform cleanup (default: True)
            
        Returns:
            Background task ID if cleanup is enabled, None otherwise
            
        Requirements: 10.4
        """
        logger.info(f"Releasing slot {slot_id} with background cleanup")
        
        try:
            # Load slot
            slot = self.slot_store.load_slot(slot_id)
            
            # Mark slot as available immediately (without cleanup)
            self.slot_allocator.mark_available(slot_id)
            
            logger.info(f"Slot {slot_id} marked as available")
            
            # Start background cleanup if requested
            if cleanup:
                # Reload slot to get updated state
                slot = self.slot_store.load_slot(slot_id)
                
                task_id = self.slot_cleaner.cleanup_background(
                    slot,
                    operation="after_release"
                )
                
                logger.info(
                    f"Started background cleanup for slot {slot_id} "
                    f"(task_id: {task_id})"
                )
                
                return task_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to release slot {slot_id}: {e}")
            raise SlotAllocationError(
                f"Failed to release slot {slot_id}: {str(e)}"
            ) from e
    
    # ===== Metrics Collection (Task 10.3) =====
    
    def _record_allocation_time(self, repo_name: str, duration: float) -> None:
        """
        Record allocation time for metrics.
        
        Args:
            repo_name: Repository name
            duration: Allocation duration in seconds
            
        Requirements: 10.5
        """
        with self._metrics_lock:
            if repo_name not in self._allocation_times:
                self._allocation_times[repo_name] = []
            self._allocation_times[repo_name].append(duration)
            
            # Limit history to last 1000 allocations
            if len(self._allocation_times[repo_name]) > 1000:
                self._allocation_times[repo_name] = self._allocation_times[repo_name][-1000:]
    
    def _record_cleanup_time(self, repo_name: str, duration: float) -> None:
        """
        Record cleanup time for metrics.
        
        Args:
            repo_name: Repository name
            duration: Cleanup duration in seconds
            
        Requirements: 10.5
        """
        with self._metrics_lock:
            if repo_name not in self._cleanup_times:
                self._cleanup_times[repo_name] = []
            self._cleanup_times[repo_name].append(duration)
            
            # Limit history to last 1000 cleanups
            if len(self._cleanup_times[repo_name]) > 1000:
                self._cleanup_times[repo_name] = self._cleanup_times[repo_name][-1000:]
    
    def get_allocation_metrics(self, repo_name: str) -> AllocationMetrics:
        """
        Get allocation metrics for a repository.
        
        Args:
            repo_name: Repository name
            
        Returns:
            AllocationMetrics with statistics
            
        Requirements: 10.5
        """
        # Get metrics from slot allocator (includes cache hit rate)
        allocator_metrics = self.slot_allocator.get_allocation_metrics(repo_name)
        
        # Add our timing metrics
        with self._metrics_lock:
            allocation_times = self._allocation_times.get(repo_name, [])
            avg_time = sum(allocation_times) / len(allocation_times) if allocation_times else 0.0
        
        # Update average time with our measurements
        if avg_time > 0:
            allocator_metrics.average_allocation_time_seconds = avg_time
        
        return allocator_metrics
    
    def get_performance_metrics(self, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Args:
            repo_name: Optional repository name (returns all if None)
            
        Returns:
            Dictionary with performance metrics
            
        Requirements: 10.5
        """
        if repo_name:
            repos = [repo_name]
        else:
            repos = self.list_pools()
        
        metrics = {}
        
        for repo in repos:
            try:
                # Get allocation metrics
                allocation_metrics = self.get_allocation_metrics(repo)
                
                # Get cleanup times
                with self._metrics_lock:
                    cleanup_times = self._cleanup_times.get(repo, [])
                    avg_cleanup_time = (
                        sum(cleanup_times) / len(cleanup_times)
                        if cleanup_times else 0.0
                    )
                
                # Get pool summary
                pool_summary = self.get_pool_summary().get(repo)
                
                # Get cleanup log statistics
                cleanup_log = self.slot_cleaner.get_cleanup_log()
                repo_cleanups = [
                    r for r in cleanup_log
                    if r.slot_id.startswith(f"workspace-{repo}-")
                ]
                
                successful_cleanups = sum(1 for r in repo_cleanups if r.success)
                failed_cleanups = len(repo_cleanups) - successful_cleanups
                
                metrics[repo] = {
                    "allocation": {
                        "total_allocations": allocation_metrics.total_allocations,
                        "average_time_seconds": allocation_metrics.average_allocation_time_seconds,
                        "cache_hit_rate": allocation_metrics.cache_hit_rate,
                        "failed_allocations": allocation_metrics.failed_allocations,
                    },
                    "cleanup": {
                        "total_cleanups": len(repo_cleanups),
                        "successful_cleanups": successful_cleanups,
                        "failed_cleanups": failed_cleanups,
                        "average_time_seconds": avg_cleanup_time,
                    },
                    "pool": {
                        "total_slots": pool_summary.total_slots if pool_summary else 0,
                        "available_slots": pool_summary.available_slots if pool_summary else 0,
                        "allocated_slots": pool_summary.allocated_slots if pool_summary else 0,
                        "error_slots": pool_summary.error_slots if pool_summary else 0,
                    }
                }
                
            except Exception as e:
                logger.error(f"Error getting metrics for pool '{repo}': {e}")
                metrics[repo] = {"error": str(e)}
        
        return metrics
    
    def export_metrics(self, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export all metrics to a file or return as dictionary.
        
        Args:
            output_file: Optional file path to write metrics (JSON format)
            
        Returns:
            Dictionary with all metrics
            
        Requirements: 10.5
        """
        import json
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "pools": self.get_performance_metrics(),
            "system": {
                "total_pools": len(self.list_pools()),
                "workspaces_dir": str(self.workspaces_dir),
            }
        }
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            logger.info(f"Metrics exported to {output_file}")
        
        return metrics
    
    def clear_metrics(self, repo_name: Optional[str] = None) -> None:
        """
        Clear collected metrics.
        
        Args:
            repo_name: Optional repository name (clears all if None)
            
        Requirements: 10.5
        """
        with self._metrics_lock:
            if repo_name:
                self._allocation_times.pop(repo_name, None)
                self._cleanup_times.pop(repo_name, None)
                logger.info(f"Cleared metrics for pool '{repo_name}'")
            else:
                self._allocation_times.clear()
                self._cleanup_times.clear()
                logger.info("Cleared all metrics")
        
        # Also clear allocator metrics
        self.slot_allocator.clear_metrics(repo_name)

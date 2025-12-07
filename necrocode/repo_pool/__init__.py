"""Repo Pool Manager - Workspace slot management for NecroCode."""

from necrocode.repo_pool.models import (
    Pool,
    Slot,
    SlotState,
    SlotStatus,
    PoolSummary,
    CleanupResult,
    GitResult,
    AllocationMetrics,
)
from necrocode.repo_pool.exceptions import (
    PoolManagerError,
    PoolNotFoundError,
    SlotNotFoundError,
    NoAvailableSlotError,
    SlotAllocationError,
    GitOperationError,
    CleanupError,
    LockTimeoutError,
)
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.git_operations import GitOperations
from necrocode.repo_pool.slot_store import SlotStore
from necrocode.repo_pool.lock_manager import LockManager
from necrocode.repo_pool.slot_cleaner import SlotCleaner, CleanupRecord, RepairResult
from necrocode.repo_pool.slot_allocator import SlotAllocator
# Use WorktreePoolManager as the default PoolManager
from necrocode.repo_pool.worktree_pool_manager import WorktreePoolManager as PoolManager
# Keep old implementation available for backward compatibility
from necrocode.repo_pool.pool_manager import PoolManager as CloneBasedPoolManager

__all__ = [
    # Models
    "Pool",
    "Slot",
    "SlotState",
    "SlotStatus",
    "PoolSummary",
    "CleanupResult",
    "GitResult",
    "AllocationMetrics",
    # Exceptions
    "PoolManagerError",
    "PoolNotFoundError",
    "SlotNotFoundError",
    "NoAvailableSlotError",
    "SlotAllocationError",
    "GitOperationError",
    "CleanupError",
    "LockTimeoutError",
    # Config
    "PoolConfig",
    # Git Operations
    "GitOperations",
    # Slot Store
    "SlotStore",
    # Lock Manager
    "LockManager",
    # Slot Cleaner
    "SlotCleaner",
    "CleanupRecord",
    "RepairResult",
    # Slot Allocator
    "SlotAllocator",
    # Pool Manager (Main API - now using WorktreePoolManager)
    "PoolManager",
    "CloneBasedPoolManager",  # Old implementation for backward compatibility
]

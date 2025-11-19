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
from necrocode.repo_pool.pool_manager import PoolManager

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
    # Pool Manager (Main API)
    "PoolManager",
]

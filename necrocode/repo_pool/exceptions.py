"""Exception classes for Repo Pool Manager."""


class PoolManagerError(Exception):
    """Base exception for Pool Manager."""
    pass


class PoolNotFoundError(PoolManagerError):
    """Pool not found."""
    pass


class SlotNotFoundError(PoolManagerError):
    """Slot not found."""
    pass


class NoAvailableSlotError(PoolManagerError):
    """No available slot."""
    pass


class SlotAllocationError(PoolManagerError):
    """Slot allocation failed."""
    pass


class GitOperationError(PoolManagerError):
    """Git operation failed."""
    pass


class CleanupError(PoolManagerError):
    """Cleanup operation failed."""
    pass


class LockTimeoutError(PoolManagerError):
    """Lock acquisition timeout."""
    pass

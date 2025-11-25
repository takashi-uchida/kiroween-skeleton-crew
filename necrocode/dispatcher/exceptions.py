"""
Exception classes for the Dispatcher component.

Defines custom exceptions for various dispatcher error conditions.
"""


class DispatcherError(Exception):
    """Base exception for Dispatcher errors."""
    pass


class TaskAssignmentError(DispatcherError):
    """Raised when task assignment to an Agent Runner fails."""
    pass


class SlotAllocationError(DispatcherError):
    """Raised when slot allocation from Repo Pool Manager fails."""
    pass


class RunnerLaunchError(DispatcherError):
    """Raised when Agent Runner launch fails."""
    pass


class PoolNotFoundError(DispatcherError):
    """Raised when a requested Agent Pool is not found."""
    pass


class DeadlockDetectedError(DispatcherError):
    """Raised when a deadlock is detected in task dependencies."""
    pass

"""
Exception classes for Task Registry
"""


class TaskRegistryError(Exception):
    """Base exception for Task Registry"""
    pass


class TaskNotFoundError(TaskRegistryError):
    """Task not found"""
    
    def __init__(self, task_id: str, spec_name: str = None):
        self.task_id = task_id
        self.spec_name = spec_name
        message = f"Task '{task_id}' not found"
        if spec_name:
            message += f" in spec '{spec_name}'"
        super().__init__(message)


class TasksetNotFoundError(TaskRegistryError):
    """Taskset not found"""
    
    def __init__(self, spec_name: str):
        self.spec_name = spec_name
        super().__init__(f"Taskset '{spec_name}' not found")


class InvalidStateTransitionError(TaskRegistryError):
    """Invalid state transition"""
    
    def __init__(self, task_id: str, from_state: str, to_state: str):
        self.task_id = task_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid state transition for task '{task_id}': "
            f"{from_state} -> {to_state}"
        )


class CircularDependencyError(TaskRegistryError):
    """Circular dependency detected"""
    
    def __init__(self, cycle):
        # Handle both list and string inputs
        if isinstance(cycle, str):
            self.cycle = [cycle]
            cycle_str = cycle
        else:
            self.cycle = cycle if isinstance(cycle, list) else list(cycle)
            cycle_str = " -> ".join(str(c) for c in self.cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class LockTimeoutError(TaskRegistryError):
    """Lock acquisition timeout"""
    
    def __init__(self, spec_name: str, timeout: float):
        self.spec_name = spec_name
        self.timeout = timeout
        super().__init__(
            f"Failed to acquire lock for '{spec_name}' "
            f"within {timeout} seconds"
        )


class SyncError(TaskRegistryError):
    """Kiro sync error"""
    
    def __init__(self, message: str, spec_name: str = None):
        self.spec_name = spec_name
        full_message = f"Sync error: {message}"
        if spec_name:
            full_message += f" (spec: {spec_name})"
        super().__init__(full_message)

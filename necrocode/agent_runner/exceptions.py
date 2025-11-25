"""
Exception classes for Agent Runner.

This module defines the exception hierarchy for error handling
in the Agent Runner component.
"""


class RunnerError(Exception):
    """
    Base exception for Agent Runner.
    
    All Agent Runner-specific exceptions inherit from this class.
    """
    pass


class TaskContextValidationError(RunnerError):
    """
    Task context validation failed.
    
    Raised when the provided TaskContext is missing required information
    or contains invalid data.
    """
    pass


class WorkspacePreparationError(RunnerError):
    """
    Workspace preparation failed.
    
    Raised when Git operations during workspace setup fail,
    such as checkout, fetch, rebase, or branch creation.
    """
    pass


class ImplementationError(RunnerError):
    """
    Task implementation failed.
    
    Raised when the task implementation process encounters an error,
    such as Kiro execution failure or implementation verification failure.
    """
    pass


class TestExecutionError(RunnerError):
    """
    Test execution failed.
    
    Raised when test commands fail to execute or produce unexpected results.
    """
    pass


class PushError(RunnerError):
    """
    Git push operation failed.
    
    Raised when pushing changes to the remote repository fails,
    even after retry attempts.
    """
    pass


class ArtifactUploadError(RunnerError):
    """
    Artifact upload failed.
    
    Raised when uploading artifacts to the Artifact Store fails.
    Note: This is typically a warning condition and may not stop execution.
    """
    pass


class TimeoutError(RunnerError):
    """
    Execution timeout exceeded.
    
    Raised when task execution exceeds the configured timeout limit.
    """
    pass


class PlaybookExecutionError(RunnerError):
    """
    Playbook execution failed.
    
    Raised when a Playbook step fails to execute or produces an error.
    """
    pass


class ResourceLimitError(RunnerError):
    """
    Resource limit exceeded.
    
    Raised when the runner exceeds configured resource limits
    (memory, CPU, etc.).
    """
    pass


class SecurityError(RunnerError):
    """
    Security-related error.
    
    Raised when authentication fails, permissions are insufficient,
    or other security constraints are violated.
    """
    pass


class ResourceConflictError(RunnerError):
    """
    Resource conflict with another runner.
    
    Raised when a critical resource conflict is detected with another
    parallel runner instance (e.g., same workspace, same branch).
    """
    pass

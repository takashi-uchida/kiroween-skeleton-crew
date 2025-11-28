"""
Exception classes for Review & PR Service.

Defines custom exceptions for various error scenarios in PR operations.
"""


class PRServiceError(Exception):
    """
    Base exception for all Review & PR Service errors.
    
    All custom exceptions in this module inherit from this base class.
    """
    
    def __init__(self, message: str, details: dict = None):
        """
        Initialize PRServiceError.
        
        Args:
            message: Error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class AuthenticationError(PRServiceError):
    """
    Raised when authentication with Git host fails.
    
    This typically indicates invalid credentials, expired tokens,
    or insufficient permissions.
    """
    
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, details)


class RateLimitError(PRServiceError):
    """
    Raised when Git host API rate limit is exceeded.
    
    Contains information about when the rate limit will reset.
    """
    
    def __init__(
        self,
        message: str = "API rate limit exceeded",
        reset_time: int = None,
        details: dict = None
    ):
        """
        Initialize RateLimitError.
        
        Args:
            message: Error message
            reset_time: Unix timestamp when rate limit resets
            details: Additional error details
        """
        super().__init__(message, details)
        self.reset_time = reset_time
    
    def __str__(self) -> str:
        """String representation including reset time."""
        base_msg = super().__str__()
        if self.reset_time:
            return f"{base_msg} | Reset at: {self.reset_time}"
        return base_msg


class PRCreationError(PRServiceError):
    """
    Raised when PR creation fails.
    
    This can occur due to various reasons such as invalid branch names,
    conflicts, or Git host API errors.
    """
    
    def __init__(self, message: str = "Failed to create pull request", details: dict = None):
        super().__init__(message, details)


class PRUpdateError(PRServiceError):
    """
    Raised when PR update operation fails.
    
    This includes failures in updating PR description, labels, reviewers, etc.
    """
    
    def __init__(self, message: str = "Failed to update pull request", details: dict = None):
        super().__init__(message, details)


class CIStatusError(PRServiceError):
    """
    Raised when CI status retrieval or monitoring fails.
    
    This can occur when CI system is unavailable or returns invalid data.
    """
    
    def __init__(self, message: str = "Failed to retrieve CI status", details: dict = None):
        super().__init__(message, details)


class WebhookError(PRServiceError):
    """
    Raised when webhook processing fails.
    
    This includes signature verification failures and invalid webhook payloads.
    """
    
    def __init__(self, message: str = "Webhook processing failed", details: dict = None):
        super().__init__(message, details)


class WebhookSignatureError(WebhookError):
    """
    Raised when webhook signature verification fails.
    
    This indicates a potential security issue or misconfiguration.
    """
    
    def __init__(self, message: str = "Invalid webhook signature", details: dict = None):
        super().__init__(message, details)


class MergeError(PRServiceError):
    """
    Raised when PR merge operation fails.
    
    This can occur due to merge conflicts, failed checks, or insufficient permissions.
    """
    
    def __init__(self, message: str = "Failed to merge pull request", details: dict = None):
        super().__init__(message, details)


class ConflictError(PRServiceError):
    """
    Raised when merge conflicts are detected.
    
    Contains information about conflicting files.
    """
    
    def __init__(
        self,
        message: str = "Merge conflicts detected",
        conflicting_files: list = None,
        details: dict = None
    ):
        """
        Initialize ConflictError.
        
        Args:
            message: Error message
            conflicting_files: List of files with conflicts
            details: Additional error details
        """
        super().__init__(message, details)
        self.conflicting_files = conflicting_files or []
    
    def __str__(self) -> str:
        """String representation including conflicting files."""
        base_msg = super().__str__()
        if self.conflicting_files:
            files_str = ", ".join(self.conflicting_files)
            return f"{base_msg} | Conflicting files: {files_str}"
        return base_msg


class TemplateError(PRServiceError):
    """
    Raised when PR template processing fails.
    
    This can occur due to invalid template syntax or missing template variables.
    """
    
    def __init__(self, message: str = "Template processing failed", details: dict = None):
        super().__init__(message, details)


class ArtifactDownloadError(PRServiceError):
    """
    Raised when artifact download from Artifact Store fails.
    
    This can occur due to network issues or missing artifacts.
    """
    
    def __init__(self, message: str = "Failed to download artifact", details: dict = None):
        super().__init__(message, details)


class NetworkError(PRServiceError):
    """
    Raised when network communication with Git host fails.
    
    This is typically a transient error that can be retried.
    """
    
    def __init__(self, message: str = "Network communication failed", details: dict = None):
        super().__init__(message, details)


class ConfigurationError(PRServiceError):
    """
    Raised when service configuration is invalid or incomplete.
    
    This indicates a setup or configuration issue that must be resolved.
    """
    
    def __init__(self, message: str = "Invalid configuration", details: dict = None):
        super().__init__(message, details)


class GitHostError(PRServiceError):
    """
    Raised when Git host API returns an unexpected error.
    
    This is a generic error for Git host-specific issues.
    """
    
    def __init__(
        self,
        message: str = "Git host API error",
        status_code: int = None,
        details: dict = None
    ):
        """
        Initialize GitHostError.
        
        Args:
            message: Error message
            status_code: HTTP status code from API
            details: Additional error details
        """
        super().__init__(message, details)
        self.status_code = status_code
    
    def __str__(self) -> str:
        """String representation including status code."""
        base_msg = super().__str__()
        if self.status_code:
            return f"{base_msg} | Status code: {self.status_code}"
        return base_msg

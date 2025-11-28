"""
Retry Handler - Error handling and retry logic for Review & PR Service.

This module provides retry mechanisms with exponential backoff for handling
transient errors like network failures and rate limits.
"""

import logging
import time
from typing import Callable, TypeVar, Any, Optional
from functools import wraps
from datetime import datetime

try:
    from .exceptions import (
        PRServiceError,
        AuthenticationError,
        RateLimitError,
        NetworkError,
    )
except ImportError:
    # Fallback for direct module execution
    from necrocode.review_pr_service.exceptions import (
        PRServiceError,
        AuthenticationError,
        RateLimitError,
        NetworkError,
    )


logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryHandler:
    """
    Handles retry logic with exponential backoff for API operations.
    
    Provides automatic retry for transient errors while failing fast
    for permanent errors like authentication failures.
    
    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_rate_limit: bool = True
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds before first retry (default: 1.0)
            max_delay: Maximum delay in seconds between retries (default: 60.0)
            exponential_base: Base for exponential backoff calculation (default: 2.0)
            retry_on_rate_limit: Whether to retry on rate limit errors (default: True)
            
        Requirements: 15.2, 15.4
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_rate_limit = retry_on_rate_limit
        
        logger.debug(
            f"RetryHandler initialized: max_retries={max_retries}, "
            f"initial_delay={initial_delay}s, max_delay={max_delay}s"
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
            
        Requirements: 15.4
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: Exception that was raised
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if should retry, False otherwise
            
        Requirements: 15.1, 15.2, 15.3
        """
        # Never retry if max attempts reached
        if attempt >= self.max_retries:
            logger.debug(f"Max retries ({self.max_retries}) reached, not retrying")
            return False
        
        # Never retry authentication errors (permanent failure)
        if isinstance(exception, AuthenticationError):
            logger.error(f"Authentication error detected, not retrying: {exception}")
            return False
        
        # Retry rate limit errors if configured
        if isinstance(exception, RateLimitError):
            if self.retry_on_rate_limit:
                logger.warning(
                    f"Rate limit error detected, will retry (attempt {attempt + 1}/{self.max_retries}): {exception}"
                )
                return True
            else:
                logger.error(f"Rate limit error detected, not retrying: {exception}")
                return False
        
        # Retry network errors (transient failures)
        if isinstance(exception, NetworkError):
            logger.warning(
                f"Network error detected, will retry (attempt {attempt + 1}/{self.max_retries}): {exception}"
            )
            return True
        
        # Don't retry other PRServiceError subclasses by default
        if isinstance(exception, PRServiceError):
            logger.error(f"PR service error detected, not retrying: {exception}")
            return False
        
        # Retry generic exceptions (might be transient)
        logger.warning(
            f"Generic exception detected, will retry (attempt {attempt + 1}/{self.max_retries}): {exception}"
        )
        return True
    
    def _handle_rate_limit(self, exception: RateLimitError) -> float:
        """
        Handle rate limit error and calculate wait time.
        
        Args:
            exception: RateLimitError with reset time information
            
        Returns:
            Wait time in seconds
            
        Requirements: 15.1
        """
        if exception.reset_time:
            # Calculate wait time until rate limit resets
            current_time = int(time.time())
            wait_time = max(0, exception.reset_time - current_time)
            
            # Add small buffer (5 seconds)
            wait_time += 5
            
            # Cap at max_delay
            wait_time = min(wait_time, self.max_delay)
            
            logger.info(
                f"Rate limit will reset at {exception.reset_time} "
                f"(waiting {wait_time}s)"
            )
            
            return wait_time
        else:
            # No reset time provided, use exponential backoff
            logger.warning("Rate limit error without reset time, using exponential backoff")
            return self.initial_delay
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Execute a function with automatic retry on transient errors.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from the function
            
        Raises:
            AuthenticationError: If authentication fails (no retry)
            RateLimitError: If rate limit exceeded and retries exhausted
            NetworkError: If network error persists after retries
            PRServiceError: For other errors
            
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
        """
        attempt = 0
        last_exception = None
        
        while attempt <= self.max_retries:
            try:
                # Log attempt
                if attempt > 0:
                    logger.info(
                        f"Retry attempt {attempt}/{self.max_retries} for {func.__name__}"
                    )
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success - log if this was a retry
                if attempt > 0:
                    logger.info(
                        f"Operation succeeded after {attempt} retries: {func.__name__}"
                    )
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Log error
                logger.error(
                    f"Error in {func.__name__} (attempt {attempt + 1}/{self.max_retries + 1}): {e}",
                    exc_info=True
                )
                
                # Check if we should retry
                if not self._should_retry(e, attempt):
                    # Don't retry - re-raise the exception
                    raise
                
                # Calculate delay
                if isinstance(e, RateLimitError):
                    delay = self._handle_rate_limit(e)
                else:
                    delay = self._calculate_delay(attempt)
                
                # Log retry delay
                logger.info(
                    f"Retrying {func.__name__} in {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                
                # Wait before retry
                time.sleep(delay)
                
                # Increment attempt counter
                attempt += 1
        
        # All retries exhausted - raise the last exception
        logger.error(
            f"All retries exhausted for {func.__name__}, raising last exception"
        )
        raise last_exception


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_on_rate_limit: bool = True
):
    """
    Decorator to add retry logic to a function.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        retry_on_rate_limit: Whether to retry on rate limit errors
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @with_retry(max_retries=3, initial_delay=1.0)
        def create_pr(title, description):
            # API call that might fail
            return api.create_pull_request(title, description)
    
    Requirements: 15.1, 15.2, 15.4
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            handler = RetryHandler(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retry_on_rate_limit=retry_on_rate_limit
            )
            return handler.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


class RateLimitWaiter:
    """
    Handles rate limit detection and waiting.
    
    Provides utilities for detecting rate limits and calculating
    appropriate wait times before retrying.
    
    Requirements: 15.1
    """
    
    @staticmethod
    def wait_for_rate_limit_reset(reset_time: int, buffer_seconds: int = 5) -> None:
        """
        Wait until rate limit resets.
        
        Args:
            reset_time: Unix timestamp when rate limit resets
            buffer_seconds: Additional buffer time in seconds (default: 5)
            
        Requirements: 15.1
        """
        current_time = int(time.time())
        wait_time = max(0, reset_time - current_time) + buffer_seconds
        
        if wait_time > 0:
            logger.info(
                f"Rate limit active, waiting {wait_time}s until reset "
                f"(reset at {datetime.fromtimestamp(reset_time)})"
            )
            time.sleep(wait_time)
            logger.info("Rate limit wait complete, resuming operations")
        else:
            logger.debug("Rate limit already reset, no wait needed")
    
    @staticmethod
    def extract_rate_limit_info(exception: Exception) -> Optional[int]:
        """
        Extract rate limit reset time from exception.
        
        Args:
            exception: Exception that might contain rate limit info
            
        Returns:
            Unix timestamp of rate limit reset, or None if not available
            
        Requirements: 15.1
        """
        if isinstance(exception, RateLimitError):
            return exception.reset_time
        
        # Try to extract from exception message or attributes
        if hasattr(exception, 'reset_time'):
            return exception.reset_time
        
        # Check for common rate limit headers in exception details
        if hasattr(exception, 'details') and isinstance(exception.details, dict):
            reset_time = exception.details.get('reset_time') or exception.details.get('x-ratelimit-reset')
            if reset_time:
                try:
                    return int(reset_time)
                except (ValueError, TypeError):
                    pass
        
        return None


# Global retry handler instance for convenience
default_retry_handler = RetryHandler()


def retry_operation(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Convenience function to retry an operation with default settings.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result from the function
        
    Example:
        result = retry_operation(api.create_pr, title="My PR", description="...")
    
    Requirements: 15.2, 15.4
    """
    return default_retry_handler.execute_with_retry(func, *args, **kwargs)

"""
Example demonstrating error handling and retry functionality in Review & PR Service.

This example shows:
- Rate limit handling with automatic waiting
- Network error retry with exponential backoff
- Authentication error detection (no retry)
- Comprehensive error logging

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.review_pr_service.retry_handler import (
    RetryHandler,
    with_retry,
    retry_operation,
    RateLimitWaiter
)
from necrocode.review_pr_service.exceptions import (
    AuthenticationError,
    RateLimitError,
    NetworkError,
    PRServiceError
)


# Configure logging to see retry behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_rate_limit_handling():
    """
    Example: Handling rate limit errors with automatic waiting.
    
    Requirements: 15.1
    """
    print("\n" + "="*60)
    print("Example 1: Rate Limit Handling")
    print("="*60)
    
    # Simulate a function that hits rate limit
    attempt_count = [0]
    
    @with_retry(max_retries=3, retry_on_rate_limit=True)
    def api_call_with_rate_limit():
        attempt_count[0] += 1
        logger.info(f"API call attempt {attempt_count[0]}")
        
        if attempt_count[0] < 2:
            # Simulate rate limit on first attempt
            import time
            reset_time = int(time.time()) + 5  # Reset in 5 seconds
            raise RateLimitError(
                "API rate limit exceeded",
                reset_time=reset_time
            )
        
        return "Success after rate limit"
    
    try:
        result = api_call_with_rate_limit()
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def example_network_error_retry():
    """
    Example: Retrying network errors with exponential backoff.
    
    Requirements: 15.2, 15.4
    """
    print("\n" + "="*60)
    print("Example 2: Network Error Retry with Exponential Backoff")
    print("="*60)
    
    # Simulate a function with transient network errors
    attempt_count = [0]
    
    @with_retry(max_retries=3, initial_delay=0.5, exponential_base=2.0)
    def api_call_with_network_issues():
        attempt_count[0] += 1
        logger.info(f"API call attempt {attempt_count[0]}")
        
        if attempt_count[0] < 3:
            # Simulate network error on first two attempts
            raise NetworkError(
                f"Connection timeout (attempt {attempt_count[0]})"
            )
        
        return "Success after network recovery"
    
    try:
        result = api_call_with_network_issues()
        print(f"✓ Result: {result}")
        print(f"✓ Total attempts: {attempt_count[0]}")
    except Exception as e:
        print(f"✗ Failed after {attempt_count[0]} attempts: {e}")


def example_authentication_error_no_retry():
    """
    Example: Authentication errors are not retried.
    
    Requirements: 15.3
    """
    print("\n" + "="*60)
    print("Example 3: Authentication Error (No Retry)")
    print("="*60)
    
    attempt_count = [0]
    
    @with_retry(max_retries=3)
    def api_call_with_auth_error():
        attempt_count[0] += 1
        logger.info(f"API call attempt {attempt_count[0]}")
        
        # Authentication errors should not be retried
        raise AuthenticationError(
            "Invalid API token",
            details={"status_code": 401}
        )
    
    try:
        result = api_call_with_auth_error()
        print(f"✓ Result: {result}")
    except AuthenticationError as e:
        print(f"✓ Correctly failed without retry: {e}")
        print(f"✓ Total attempts: {attempt_count[0]} (should be 1)")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def example_manual_retry_handler():
    """
    Example: Using RetryHandler directly for custom retry logic.
    
    Requirements: 15.2, 15.4
    """
    print("\n" + "="*60)
    print("Example 4: Manual Retry Handler")
    print("="*60)
    
    # Create custom retry handler
    handler = RetryHandler(
        max_retries=5,
        initial_delay=0.5,
        max_delay=10.0,
        exponential_base=2.0
    )
    
    attempt_count = [0]
    
    def unreliable_operation():
        attempt_count[0] += 1
        logger.info(f"Operation attempt {attempt_count[0]}")
        
        if attempt_count[0] < 4:
            raise NetworkError(f"Temporary failure {attempt_count[0]}")
        
        return f"Success after {attempt_count[0]} attempts"
    
    try:
        result = handler.execute_with_retry(unreliable_operation)
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"✗ Failed: {e}")


def example_rate_limit_waiter():
    """
    Example: Using RateLimitWaiter for explicit rate limit handling.
    
    Requirements: 15.1
    """
    print("\n" + "="*60)
    print("Example 5: Rate Limit Waiter")
    print("="*60)
    
    import time
    
    # Simulate rate limit with reset time
    reset_time = int(time.time()) + 3  # Reset in 3 seconds
    
    print(f"Rate limit active, reset at: {reset_time}")
    print("Waiting for rate limit to reset...")
    
    start_time = time.time()
    RateLimitWaiter.wait_for_rate_limit_reset(reset_time, buffer_seconds=1)
    elapsed = time.time() - start_time
    
    print(f"✓ Waited {elapsed:.1f} seconds")
    print("✓ Rate limit reset, can proceed with API calls")


def example_error_logging():
    """
    Example: Comprehensive error logging during retries.
    
    Requirements: 15.5
    """
    print("\n" + "="*60)
    print("Example 6: Error Logging")
    print("="*60)
    
    # Enable debug logging to see all retry details
    logging.getLogger('necrocode.review_pr_service.retry_handler').setLevel(logging.DEBUG)
    
    attempt_count = [0]
    
    @with_retry(max_retries=3, initial_delay=0.5)
    def operation_with_detailed_logging():
        attempt_count[0] += 1
        
        if attempt_count[0] == 1:
            raise NetworkError("First attempt failed - connection timeout")
        elif attempt_count[0] == 2:
            raise NetworkError("Second attempt failed - DNS resolution error")
        else:
            return "Success on third attempt"
    
    try:
        result = operation_with_detailed_logging()
        print(f"✓ Result: {result}")
        print("✓ Check logs above for detailed retry information")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Reset logging level
    logging.getLogger('necrocode.review_pr_service.retry_handler').setLevel(logging.INFO)


def example_mixed_errors():
    """
    Example: Handling different error types in sequence.
    
    Requirements: 15.1, 15.2, 15.3, 15.5
    """
    print("\n" + "="*60)
    print("Example 7: Mixed Error Types")
    print("="*60)
    
    attempt_count = [0]
    
    @with_retry(max_retries=5, initial_delay=0.5)
    def operation_with_mixed_errors():
        attempt_count[0] += 1
        logger.info(f"Attempt {attempt_count[0]}")
        
        if attempt_count[0] == 1:
            # First: network error (will retry)
            raise NetworkError("Network timeout")
        elif attempt_count[0] == 2:
            # Second: rate limit (will retry with wait)
            import time
            reset_time = int(time.time()) + 2
            raise RateLimitError("Rate limit", reset_time=reset_time)
        elif attempt_count[0] == 3:
            # Third: another network error (will retry)
            raise NetworkError("Connection refused")
        else:
            # Fourth: success
            return "Success after handling multiple error types"
    
    try:
        result = operation_with_mixed_errors()
        print(f"✓ Result: {result}")
        print(f"✓ Handled {attempt_count[0]} attempts with different error types")
    except Exception as e:
        print(f"✗ Failed: {e}")


def example_convenience_function():
    """
    Example: Using the convenience retry_operation function.
    
    Requirements: 15.2, 15.4
    """
    print("\n" + "="*60)
    print("Example 8: Convenience Function")
    print("="*60)
    
    attempt_count = [0]
    
    def simple_operation(value: str):
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise NetworkError("Temporary failure")
        return f"Processed: {value}"
    
    try:
        result = retry_operation(simple_operation, "test-data")
        print(f"✓ Result: {result}")
        print(f"✓ Used default retry settings")
    except Exception as e:
        print(f"✗ Failed: {e}")


def main():
    """Run all error handling examples."""
    print("\n" + "="*60)
    print("Review & PR Service - Error Handling & Retry Examples")
    print("="*60)
    
    try:
        # Run all examples
        example_rate_limit_handling()
        example_network_error_retry()
        example_authentication_error_no_retry()
        example_manual_retry_handler()
        example_rate_limit_waiter()
        example_error_logging()
        example_mixed_errors()
        example_convenience_function()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

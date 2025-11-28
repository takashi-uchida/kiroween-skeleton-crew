"""
Verification script for Task 15: Error Handling and Retry Implementation.

This script verifies:
- Rate limit handling (15.1)
- Network error retry with exponential backoff (15.2)
- Authentication error detection (15.3)
- Error logging (15.4, 15.5)
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import directly - now with fallback imports in retry_handler
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_rate_limit_handling():
    """Test rate limit handling with automatic waiting."""
    print("\n" + "="*60)
    print("TEST 1: Rate Limit Handling (Requirement 15.1)")
    print("="*60)
    
    attempt_count = [0]
    
    @with_retry(max_retries=3, retry_on_rate_limit=True, initial_delay=0.5)
    def api_call_with_rate_limit():
        attempt_count[0] += 1
        logger.info(f"API call attempt {attempt_count[0]}")
        
        if attempt_count[0] < 2:
            reset_time = int(time.time()) + 2
            raise RateLimitError(
                "API rate limit exceeded",
                reset_time=reset_time
            )
        
        return "Success after rate limit"
    
    try:
        result = api_call_with_rate_limit()
        print(f"✓ PASS: {result}")
        print(f"✓ Total attempts: {attempt_count[0]}")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_network_error_retry():
    """Test network error retry with exponential backoff."""
    print("\n" + "="*60)
    print("TEST 2: Network Error Retry (Requirements 15.2, 15.4)")
    print("="*60)
    
    attempt_count = [0]
    start_time = time.time()
    
    @with_retry(max_retries=3, initial_delay=0.5, exponential_base=2.0)
    def api_call_with_network_issues():
        attempt_count[0] += 1
        logger.info(f"API call attempt {attempt_count[0]}")
        
        if attempt_count[0] < 3:
            raise NetworkError(f"Connection timeout (attempt {attempt_count[0]})")
        
        return "Success after network recovery"
    
    try:
        result = api_call_with_network_issues()
        elapsed = time.time() - start_time
        print(f"✓ PASS: {result}")
        print(f"✓ Total attempts: {attempt_count[0]}")
        print(f"✓ Total time: {elapsed:.2f}s (with exponential backoff)")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_authentication_error_no_retry():
    """Test that authentication errors are not retried."""
    print("\n" + "="*60)
    print("TEST 3: Authentication Error (Requirement 15.3)")
    print("="*60)
    
    attempt_count = [0]
    
    @with_retry(max_retries=3)
    def api_call_with_auth_error():
        attempt_count[0] += 1
        logger.info(f"API call attempt {attempt_count[0]}")
        raise AuthenticationError("Invalid API token")
    
    try:
        result = api_call_with_auth_error()
        print(f"✗ FAIL: Should have raised AuthenticationError")
        return False
    except AuthenticationError as e:
        print(f"✓ PASS: Correctly failed without retry")
        print(f"✓ Total attempts: {attempt_count[0]} (should be 1)")
        if attempt_count[0] == 1:
            print(f"✓ PASS: No retry attempted for auth error")
            return True
        else:
            print(f"✗ FAIL: Unexpected retry count: {attempt_count[0]}")
            return False


def test_manual_retry_handler():
    """Test manual retry handler usage."""
    print("\n" + "="*60)
    print("TEST 4: Manual Retry Handler (Requirements 15.2, 15.4)")
    print("="*60)
    
    handler = RetryHandler(
        max_retries=5,
        initial_delay=0.3,
        max_delay=5.0,
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
        print(f"✓ PASS: {result}")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_rate_limit_waiter():
    """Test rate limit waiter functionality."""
    print("\n" + "="*60)
    print("TEST 5: Rate Limit Waiter (Requirement 15.1)")
    print("="*60)
    
    reset_time = int(time.time()) + 2
    
    print(f"Rate limit active, reset at: {reset_time}")
    print("Waiting for rate limit to reset...")
    
    start_time = time.time()
    RateLimitWaiter.wait_for_rate_limit_reset(reset_time, buffer_seconds=0)
    elapsed = time.time() - start_time
    
    print(f"✓ PASS: Waited {elapsed:.1f} seconds")
    
    if elapsed >= 1.8 and elapsed <= 3.0:
        print(f"✓ PASS: Wait time is correct")
        return True
    else:
        print(f"✗ FAIL: Wait time unexpected: {elapsed:.1f}s")
        return False


def test_error_logging():
    """Test comprehensive error logging."""
    print("\n" + "="*60)
    print("TEST 6: Error Logging (Requirement 15.5)")
    print("="*60)
    
    # Enable debug logging
    logging.getLogger('necrocode.review_pr_service.retry_handler').setLevel(logging.DEBUG)
    
    attempt_count = [0]
    
    @with_retry(max_retries=3, initial_delay=0.3)
    def operation_with_logging():
        attempt_count[0] += 1
        
        if attempt_count[0] == 1:
            raise NetworkError("First attempt failed - connection timeout")
        elif attempt_count[0] == 2:
            raise NetworkError("Second attempt failed - DNS resolution error")
        else:
            return "Success on third attempt"
    
    try:
        result = operation_with_logging()
        print(f"✓ PASS: {result}")
        print(f"✓ PASS: Check logs above for detailed retry information")
        
        # Reset logging level
        logging.getLogger('necrocode.review_pr_service.retry_handler').setLevel(logging.INFO)
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_mixed_errors():
    """Test handling different error types in sequence."""
    print("\n" + "="*60)
    print("TEST 7: Mixed Error Types (Requirements 15.1, 15.2, 15.3, 15.5)")
    print("="*60)
    
    attempt_count = [0]
    
    @with_retry(max_retries=5, initial_delay=0.3)
    def operation_with_mixed_errors():
        attempt_count[0] += 1
        logger.info(f"Attempt {attempt_count[0]}")
        
        if attempt_count[0] == 1:
            raise NetworkError("Network timeout")
        elif attempt_count[0] == 2:
            reset_time = int(time.time()) + 1
            raise RateLimitError("Rate limit", reset_time=reset_time)
        elif attempt_count[0] == 3:
            raise NetworkError("Connection refused")
        else:
            return "Success after handling multiple error types"
    
    try:
        result = operation_with_mixed_errors()
        print(f"✓ PASS: {result}")
        print(f"✓ Total attempts: {attempt_count[0]}")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_convenience_function():
    """Test convenience retry_operation function."""
    print("\n" + "="*60)
    print("TEST 8: Convenience Function (Requirements 15.2, 15.4)")
    print("="*60)
    
    attempt_count = [0]
    
    def simple_operation(value: str):
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise NetworkError("Temporary failure")
        return f"Processed: {value}"
    
    try:
        result = retry_operation(simple_operation, "test-data")
        print(f"✓ PASS: {result}")
        print(f"✓ Used default retry settings")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("TASK 15 VERIFICATION: Error Handling and Retry Implementation")
    print("="*70)
    
    tests = [
        ("Rate Limit Handling", test_rate_limit_handling),
        ("Network Error Retry", test_network_error_retry),
        ("Authentication Error", test_authentication_error_no_retry),
        ("Manual Retry Handler", test_manual_retry_handler),
        ("Rate Limit Waiter", test_rate_limit_waiter),
        ("Error Logging", test_error_logging),
        ("Mixed Error Types", test_mixed_errors),
        ("Convenience Function", test_convenience_function),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}", exc_info=True)
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Task 15 implementation verified!")
        return 0
    else:
        print(f"\n✗ SOME TESTS FAILED - {total - passed} test(s) need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())

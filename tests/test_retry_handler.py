"""
Tests for retry handler functionality.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
"""

import pytest
import time
from unittest.mock import Mock, patch

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


class TestRetryHandler:
    """Test RetryHandler class."""
    
    def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retries."""
        handler = RetryHandler(max_retries=3)
        
        call_count = [0]
        
        def successful_operation():
            call_count[0] += 1
            return "success"
        
        result = handler.execute_with_retry(successful_operation)
        
        assert result == "success"
        assert call_count[0] == 1  # Called only once
    
    def test_network_error_retry(self):
        """Test that network errors are retried."""
        handler = RetryHandler(max_retries=3, initial_delay=0.1)
        
        call_count = [0]
        
        def failing_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise NetworkError("Connection timeout")
            return "success"
        
        result = handler.execute_with_retry(failing_operation)
        
        assert result == "success"
        assert call_count[0] == 3  # Failed twice, succeeded on third
    
    def test_authentication_error_no_retry(self):
        """Test that authentication errors are not retried."""
        handler = RetryHandler(max_retries=3)
        
        call_count = [0]
        
        def auth_failing_operation():
            call_count[0] += 1
            raise AuthenticationError("Invalid token")
        
        with pytest.raises(AuthenticationError):
            handler.execute_with_retry(auth_failing_operation)
        
        assert call_count[0] == 1  # Called only once, no retry
    
    def test_rate_limit_retry(self):
        """Test that rate limit errors are retried."""
        handler = RetryHandler(max_retries=3, initial_delay=0.1, retry_on_rate_limit=True)
        
        call_count = [0]
        
        def rate_limited_operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RateLimitError("Rate limit exceeded")
            return "success"
        
        result = handler.execute_with_retry(rate_limited_operation)
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_rate_limit_no_retry_when_disabled(self):
        """Test that rate limit errors are not retried when disabled."""
        handler = RetryHandler(max_retries=3, retry_on_rate_limit=False)
        
        call_count = [0]
        
        def rate_limited_operation():
            call_count[0] += 1
            raise RateLimitError("Rate limit exceeded")
        
        with pytest.raises(RateLimitError):
            handler.execute_with_retry(rate_limited_operation)
        
        assert call_count[0] == 1  # No retry
    
    def test_max_retries_exhausted(self):
        """Test that operation fails after max retries."""
        handler = RetryHandler(max_retries=2, initial_delay=0.1)
        
        call_count = [0]
        
        def always_failing_operation():
            call_count[0] += 1
            raise NetworkError("Always fails")
        
        with pytest.raises(NetworkError):
            handler.execute_with_retry(always_failing_operation)
        
        assert call_count[0] == 3  # Initial + 2 retries
    
    def test_exponential_backoff(self):
        """Test that delays increase exponentially."""
        handler = RetryHandler(
            max_retries=3,
            initial_delay=0.1,
            exponential_base=2.0
        )
        
        # Test delay calculation
        assert handler._calculate_delay(0) == 0.1  # 0.1 * 2^0
        assert handler._calculate_delay(1) == 0.2  # 0.1 * 2^1
        assert handler._calculate_delay(2) == 0.4  # 0.1 * 2^2
        assert handler._calculate_delay(3) == 0.8  # 0.1 * 2^3
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        handler = RetryHandler(
            max_retries=10,
            initial_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0
        )
        
        # Large attempt number should be capped
        assert handler._calculate_delay(10) == 5.0  # Capped at max_delay
    
    def test_rate_limit_with_reset_time(self):
        """Test rate limit handling with reset time."""
        handler = RetryHandler(max_retries=3, initial_delay=0.1)
        
        reset_time = int(time.time()) + 2  # 2 seconds from now
        exception = RateLimitError("Rate limit", reset_time=reset_time)
        
        wait_time = handler._handle_rate_limit(exception)
        
        # Should wait until reset time + buffer
        assert wait_time >= 2
        assert wait_time <= 10  # Should be reasonable


class TestWithRetryDecorator:
    """Test with_retry decorator."""
    
    def test_decorator_basic(self):
        """Test basic decorator usage."""
        call_count = [0]
        
        @with_retry(max_retries=3, initial_delay=0.1)
        def decorated_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise NetworkError("Temporary failure")
            return "success"
        
        result = decorated_function()
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_decorator_with_arguments(self):
        """Test decorator with function arguments."""
        call_count = [0]
        
        @with_retry(max_retries=2, initial_delay=0.1)
        def decorated_function(value: str, multiplier: int = 1):
            call_count[0] += 1
            if call_count[0] < 2:
                raise NetworkError("Temporary failure")
            return value * multiplier
        
        result = decorated_function("test", multiplier=2)
        
        assert result == "testtest"
        assert call_count[0] == 2
    
    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @with_retry(max_retries=3)
        def my_function():
            """My function docstring."""
            return "result"
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My function docstring."


class TestRetryOperation:
    """Test retry_operation convenience function."""
    
    def test_retry_operation_success(self):
        """Test retry_operation with successful operation."""
        call_count = [0]
        
        def operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise NetworkError("Temporary failure")
            return "success"
        
        result = retry_operation(operation)
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_operation_with_args(self):
        """Test retry_operation with function arguments."""
        call_count = [0]
        
        def operation(value: str):
            call_count[0] += 1
            if call_count[0] < 2:
                raise NetworkError("Temporary failure")
            return f"processed: {value}"
        
        result = retry_operation(operation, "test-data")
        
        assert result == "processed: test-data"
        assert call_count[0] == 2


class TestRateLimitWaiter:
    """Test RateLimitWaiter class."""
    
    def test_wait_for_rate_limit_reset(self):
        """Test waiting for rate limit reset."""
        # Set reset time 1 second in the future
        reset_time = int(time.time()) + 1
        
        start_time = time.time()
        RateLimitWaiter.wait_for_rate_limit_reset(reset_time, buffer_seconds=0)
        elapsed = time.time() - start_time
        
        # Should have waited approximately 1 second
        assert elapsed >= 0.9  # Allow some tolerance
        assert elapsed <= 2.0  # Should not wait too long
    
    def test_wait_for_past_reset_time(self):
        """Test that past reset times don't cause waiting."""
        # Set reset time in the past
        reset_time = int(time.time()) - 10
        
        start_time = time.time()
        RateLimitWaiter.wait_for_rate_limit_reset(reset_time, buffer_seconds=0)
        elapsed = time.time() - start_time
        
        # Should not wait
        assert elapsed < 0.1
    
    def test_extract_rate_limit_info_from_exception(self):
        """Test extracting rate limit info from exception."""
        reset_time = int(time.time()) + 60
        exception = RateLimitError("Rate limit", reset_time=reset_time)
        
        extracted = RateLimitWaiter.extract_rate_limit_info(exception)
        
        assert extracted == reset_time
    
    def test_extract_rate_limit_info_from_details(self):
        """Test extracting rate limit info from exception details."""
        reset_time = int(time.time()) + 60
        exception = PRServiceError(
            "Error",
            details={"reset_time": reset_time}
        )
        exception.reset_time = reset_time
        
        extracted = RateLimitWaiter.extract_rate_limit_info(exception)
        
        assert extracted == reset_time
    
    def test_extract_rate_limit_info_none(self):
        """Test that None is returned when no rate limit info available."""
        exception = NetworkError("Network error")
        
        extracted = RateLimitWaiter.extract_rate_limit_info(exception)
        
        assert extracted is None


class TestErrorLogging:
    """Test error logging functionality."""
    
    def test_errors_are_logged(self, caplog):
        """Test that all errors are logged."""
        handler = RetryHandler(max_retries=2, initial_delay=0.1)
        
        call_count = [0]
        
        def failing_operation():
            call_count[0] += 1
            raise NetworkError(f"Error {call_count[0]}")
        
        with caplog.at_level("ERROR"):
            with pytest.raises(NetworkError):
                handler.execute_with_retry(failing_operation)
        
        # Should have logged errors for each attempt
        assert len([r for r in caplog.records if r.levelname == "ERROR"]) >= 3
    
    def test_retry_attempts_logged(self, caplog):
        """Test that retry attempts are logged."""
        handler = RetryHandler(max_retries=2, initial_delay=0.1)
        
        call_count = [0]
        
        def failing_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise NetworkError("Temporary failure")
            return "success"
        
        with caplog.at_level("INFO"):
            handler.execute_with_retry(failing_operation)
        
        # Should have logged retry attempts
        retry_logs = [r for r in caplog.records if "Retry attempt" in r.message]
        assert len(retry_logs) >= 2


class TestIntegration:
    """Integration tests for retry handler."""
    
    def test_realistic_api_scenario(self):
        """Test realistic API call scenario with multiple error types."""
        handler = RetryHandler(max_retries=5, initial_delay=0.1)
        
        call_count = [0]
        
        def api_call():
            call_count[0] += 1
            
            if call_count[0] == 1:
                # First call: network timeout
                raise NetworkError("Connection timeout")
            elif call_count[0] == 2:
                # Second call: rate limit
                reset_time = int(time.time()) + 1
                raise RateLimitError("Rate limit", reset_time=reset_time)
            elif call_count[0] == 3:
                # Third call: another network error
                raise NetworkError("DNS resolution failed")
            else:
                # Fourth call: success
                return {"status": "success", "data": "result"}
        
        result = handler.execute_with_retry(api_call)
        
        assert result["status"] == "success"
        assert call_count[0] == 4  # Succeeded on 4th attempt

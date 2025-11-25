"""Integration tests for LLM service.

Tests actual integration with LLM services (OpenAI, etc.).
These tests require valid API keys and may incur costs.

Requirements: 16.1, 16.2, 16.3, 16.5, 16.6
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.llm_client import LLMClient
from necrocode.agent_runner.models import LLMConfig, LLMResponse, CodeChange
from necrocode.agent_runner.exceptions import ImplementationError


# ============================================================================
# Configuration
# ============================================================================

# Skip tests if API key is not available or tests are disabled
SKIP_LLM_TESTS = os.getenv("SKIP_LLM_TESTS", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Test with different models
TEST_MODELS = [
    "gpt-4",
    "gpt-3.5-turbo",
]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def llm_config():
    """Create LLM configuration."""
    return LLMConfig(
        api_key=OPENAI_API_KEY,
        model="gpt-4",
        timeout_seconds=120,
        max_tokens=4000
    )


@pytest.fixture
def llm_client(llm_config):
    """Create LLMClient instance."""
    return LLMClient(llm_config)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create some existing files
    (workspace / "README.md").write_text("# Test Project\n")
    (workspace / "src").mkdir()
    (workspace / "src" / "__init__.py").write_text("")
    
    return workspace


# ============================================================================
# Basic LLM Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMBasicIntegration:
    """Basic integration tests for LLM service."""
    
    def test_simple_code_generation(self, llm_client, temp_workspace):
        """Test simple code generation."""
        prompt = """
# Task: Create a hello world function

## Description
Create a simple Python function that returns "Hello, World!"

## Acceptance Criteria
1. Function should be named hello_world
2. Function should return the string "Hello, World!"
3. Function should be in a file named hello.py

## Instructions
Generate the code changes needed to implement this task.
Return the changes in the following JSON format:
{
  "code_changes": [
    {
      "file_path": "path/to/file.py",
      "operation": "create",
      "content": "file content here"
    }
  ],
  "explanation": "Brief explanation of changes"
}
"""
        
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        
        # Verify response structure
        assert isinstance(response, LLMResponse)
        assert len(response.code_changes) > 0
        assert response.explanation is not None
        assert response.model is not None
        assert response.tokens_used > 0
        
        # Verify code changes
        for change in response.code_changes:
            assert isinstance(change, CodeChange)
            assert change.file_path is not None
            assert change.operation in ["create", "modify", "delete"]
            if change.operation != "delete":
                assert change.content is not None
        
        print(f"\nGenerated {len(response.code_changes)} code changes")
        print(f"Model: {response.model}")
        print(f"Tokens used: {response.tokens_used}")
    
    def test_code_modification(self, llm_client, temp_workspace):
        """Test modifying existing code."""
        # Create an existing file
        existing_file = temp_workspace / "calculator.py"
        existing_file.write_text("""
def add(a, b):
    return a + b
""")
        
        prompt = f"""
# Task: Add subtract function

## Description
Add a subtract function to the existing calculator.py file

## Current File Content
```python
{existing_file.read_text()}
```

## Acceptance Criteria
1. Add a subtract function that takes two parameters
2. Function should return the difference
3. Keep the existing add function

## Instructions
Generate the code changes needed to implement this task.
Return the changes in JSON format with file_path, operation, and content.
"""
        
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        
        assert isinstance(response, LLMResponse)
        assert len(response.code_changes) > 0
        
        # Should modify the existing file
        assert any(
            change.file_path == "calculator.py" and change.operation == "modify"
            for change in response.code_changes
        )
    
    def test_multiple_file_generation(self, llm_client, temp_workspace):
        """Test generating multiple files."""
        prompt = """
# Task: Create a simple module

## Description
Create a simple Python module with:
1. A models.py file with a User class
2. A utils.py file with a helper function
3. An __init__.py file to make it a package

## Instructions
Generate the code changes for all three files.
Return the changes in JSON format.
"""
        
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        
        assert isinstance(response, LLMResponse)
        assert len(response.code_changes) >= 2  # At least 2 files
        
        # Verify different files
        file_paths = [change.file_path for change in response.code_changes]
        assert len(file_paths) == len(set(file_paths))  # All unique


# ============================================================================
# Model Comparison Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMModelComparison:
    """Compare different LLM models."""
    
    @pytest.mark.parametrize("model", TEST_MODELS)
    def test_model_performance(self, model, temp_workspace):
        """Test performance of different models."""
        config = LLMConfig(
            api_key=OPENAI_API_KEY,
            model=model,
            timeout_seconds=120
        )
        client = LLMClient(config)
        
        prompt = """
# Task: Create a simple function

Create a Python function that calculates factorial.
Return the code in JSON format.
"""
        
        start_time = time.time()
        response = client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        duration = time.time() - start_time
        
        print(f"\nModel: {model}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Tokens: {response.tokens_used}")
        print(f"  Code changes: {len(response.code_changes)}")
        
        assert isinstance(response, LLMResponse)
        assert response.model == model


# ============================================================================
# Rate Limiting Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMRateLimiting:
    """Test rate limiting behavior."""
    
    def test_rapid_requests(self, llm_client, temp_workspace):
        """Test rapid successive requests."""
        num_requests = 5
        responses = []
        
        for i in range(num_requests):
            prompt = f"""
# Task: Create function {i}

Create a simple Python function named func_{i}.
Return the code in JSON format.
"""
            
            try:
                response = llm_client.generate_code(
                    prompt=prompt,
                    workspace_path=temp_workspace
                )
                responses.append(response)
            except Exception as e:
                print(f"Request {i} failed: {e}")
                # Rate limiting may cause some requests to fail
                # This is expected behavior
        
        print(f"\nSuccessful requests: {len(responses)}/{num_requests}")
        
        # At least some requests should succeed
        assert len(responses) > 0
    
    def test_rate_limit_retry(self, llm_client, temp_workspace):
        """Test retry behavior on rate limit errors."""
        # This test may trigger rate limits intentionally
        # The client should handle retries automatically
        
        prompt = """
# Task: Create a test function

Create a simple test function.
Return the code in JSON format.
"""
        
        # Make multiple requests quickly
        for i in range(3):
            try:
                response = llm_client.generate_code(
                    prompt=prompt,
                    workspace_path=temp_workspace
                )
                assert isinstance(response, LLMResponse)
            except Exception as e:
                # Rate limit errors are acceptable
                print(f"Request {i} encountered error: {e}")


# ============================================================================
# Timeout Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMTimeout:
    """Test timeout behavior."""
    
    def test_short_timeout(self, temp_workspace):
        """Test with very short timeout."""
        config = LLMConfig(
            api_key=OPENAI_API_KEY,
            model="gpt-4",
            timeout_seconds=1  # Very short timeout
        )
        client = LLMClient(config)
        
        prompt = """
# Task: Create a complex module

Create a complex Python module with multiple classes and functions.
Include detailed documentation and type hints.
Return the code in JSON format.
"""
        
        # This may timeout due to short timeout
        try:
            response = client.generate_code(
                prompt=prompt,
                workspace_path=temp_workspace
            )
            # If it succeeds, that's fine too
            assert isinstance(response, LLMResponse)
        except Exception as e:
            # Timeout is expected
            print(f"Timeout occurred as expected: {e}")
    
    def test_reasonable_timeout(self, llm_client, temp_workspace):
        """Test with reasonable timeout."""
        prompt = """
# Task: Create a simple function

Create a simple Python function.
Return the code in JSON format.
"""
        
        start_time = time.time()
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        duration = time.time() - start_time
        
        # Should complete within timeout
        assert duration < llm_client.config.timeout_seconds
        assert isinstance(response, LLMResponse)


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMErrorHandling:
    """Test error handling."""
    
    def test_invalid_api_key(self, temp_workspace):
        """Test with invalid API key."""
        config = LLMConfig(
            api_key="invalid-key",
            model="gpt-4"
        )
        client = LLMClient(config)
        
        prompt = "Create a simple function"
        
        with pytest.raises(Exception):
            client.generate_code(
                prompt=prompt,
                workspace_path=temp_workspace
            )
    
    def test_invalid_model(self, temp_workspace):
        """Test with invalid model name."""
        config = LLMConfig(
            api_key=OPENAI_API_KEY,
            model="invalid-model-name"
        )
        client = LLMClient(config)
        
        prompt = "Create a simple function"
        
        with pytest.raises(Exception):
            client.generate_code(
                prompt=prompt,
                workspace_path=temp_workspace
            )
    
    def test_malformed_response_handling(self, llm_client, temp_workspace):
        """Test handling of malformed responses."""
        # Use a prompt that might produce non-JSON output
        prompt = """
Just write some code without JSON formatting.
Don't use JSON at all.
"""
        
        try:
            response = llm_client.generate_code(
                prompt=prompt,
                workspace_path=temp_workspace
            )
            # If it succeeds, the LLM followed instructions anyway
            assert isinstance(response, LLMResponse)
        except ImplementationError as e:
            # Expected error for malformed response
            assert "parse" in str(e).lower()


# ============================================================================
# Token Usage Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMTokenUsage:
    """Test token usage tracking."""
    
    def test_token_counting(self, llm_client, temp_workspace):
        """Test that token usage is tracked."""
        prompt = """
# Task: Create a function

Create a simple Python function.
Return the code in JSON format.
"""
        
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        
        # Verify token usage is tracked
        assert response.tokens_used > 0
        print(f"\nTokens used: {response.tokens_used}")
    
    def test_token_usage_scaling(self, llm_client, temp_workspace):
        """Test that token usage scales with prompt size."""
        # Short prompt
        short_prompt = "Create a simple function in JSON format."
        short_response = llm_client.generate_code(
            prompt=short_prompt,
            workspace_path=temp_workspace
        )
        
        # Long prompt
        long_prompt = """
# Task: Create a comprehensive module

## Description
Create a comprehensive Python module with:
1. Multiple classes with inheritance
2. Type hints for all functions
3. Detailed docstrings
4. Unit tests
5. Configuration management
6. Error handling
7. Logging
8. Documentation

## Acceptance Criteria
- All code should follow PEP 8
- Include type hints
- Include docstrings
- Include error handling

Return the code in JSON format.
"""
        long_response = llm_client.generate_code(
            prompt=long_prompt,
            workspace_path=temp_workspace
        )
        
        print(f"\nShort prompt tokens: {short_response.tokens_used}")
        print(f"Long prompt tokens: {long_response.tokens_used}")
        
        # Long prompt should use more tokens
        assert long_response.tokens_used > short_response.tokens_used
    
    def test_max_tokens_limit(self, temp_workspace):
        """Test max tokens limit."""
        config = LLMConfig(
            api_key=OPENAI_API_KEY,
            model="gpt-4",
            max_tokens=100  # Very low limit
        )
        client = LLMClient(config)
        
        prompt = """
# Task: Create a large module

Create a very large Python module with many classes and functions.
Return the code in JSON format.
"""
        
        response = client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace,
            max_tokens=100
        )
        
        # Response should be limited
        assert response.tokens_used <= 150  # Some overhead allowed


# ============================================================================
# Service Availability Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMServiceAvailability:
    """Test LLM service availability."""
    
    def test_service_connectivity(self, llm_client, temp_workspace):
        """Test basic connectivity to LLM service."""
        prompt = "Create a simple function in JSON format."
        
        try:
            response = llm_client.generate_code(
                prompt=prompt,
                workspace_path=temp_workspace
            )
            assert isinstance(response, LLMResponse)
            print("\nLLM service is available")
        except Exception as e:
            pytest.fail(f"LLM service is not available: {e}")
    
    def test_service_response_time(self, llm_client, temp_workspace):
        """Test LLM service response time."""
        prompt = "Create a simple function in JSON format."
        
        start_time = time.time()
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        response_time = time.time() - start_time
        
        print(f"\nLLM response time: {response_time:.2f}s")
        
        # Should respond within reasonable time (< 30 seconds)
        assert response_time < 30.0


# ============================================================================
# Quality Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.quality
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMCodeQuality:
    """Test quality of generated code."""
    
    def test_generated_code_syntax(self, llm_client, temp_workspace):
        """Test that generated code has valid syntax."""
        prompt = """
# Task: Create a Python class

Create a simple Python class named Calculator with add and subtract methods.
Return the code in JSON format.
"""
        
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        
        # Try to compile the generated code
        for change in response.code_changes:
            if change.file_path.endswith('.py') and change.operation != "delete":
                try:
                    compile(change.content, change.file_path, 'exec')
                    print(f"\n{change.file_path}: Valid Python syntax")
                except SyntaxError as e:
                    pytest.fail(f"Generated code has syntax error: {e}")
    
    def test_generated_code_completeness(self, llm_client, temp_workspace):
        """Test that generated code is complete."""
        prompt = """
# Task: Create a complete module

Create a complete Python module with:
1. A class definition
2. Method implementations
3. Docstrings

Return the code in JSON format.
"""
        
        response = llm_client.generate_code(
            prompt=prompt,
            workspace_path=temp_workspace
        )
        
        # Verify code changes are not empty
        for change in response.code_changes:
            if change.operation != "delete":
                assert len(change.content) > 0
                assert change.content.strip() != ""


# ============================================================================
# Performance Benchmarks
# ============================================================================

@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.benchmark
@pytest.mark.skipif(SKIP_LLM_TESTS or not OPENAI_API_KEY, reason="LLM tests disabled or no API key")
class TestLLMPerformance:
    """Performance benchmarks for LLM integration."""
    
    def test_average_response_time(self, llm_client, temp_workspace):
        """Measure average response time."""
        num_requests = 3
        response_times = []
        
        for i in range(num_requests):
            prompt = f"""
# Task: Create function {i}

Create a simple Python function.
Return the code in JSON format.
"""
            
            start_time = time.time()
            response = llm_client.generate_code(
                prompt=prompt,
                workspace_path=temp_workspace
            )
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"\nLLM Performance ({num_requests} requests):")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  Min: {min_time:.2f}s")
        print(f"  Max: {max_time:.2f}s")
        
        # Average should be reasonable
        assert avg_time < 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "llm"])

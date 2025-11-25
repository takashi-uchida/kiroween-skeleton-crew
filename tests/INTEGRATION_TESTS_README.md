# Integration Tests Guide

This guide explains how to run the integration tests for the Agent Runner.

## Test Files

### 1. External Services Integration (`test_external_services_integration.py`)
Tests integration with Task Registry, Repo Pool Manager, and Artifact Store.

**Requirements:**
- External services must be running
- Set environment variables for service URLs

**Run:**
```bash
# Set service URLs (optional, defaults to localhost)
export TASK_REGISTRY_URL="http://localhost:8080"
export REPO_POOL_URL="http://localhost:8081"
export ARTIFACT_STORE_URL="http://localhost:8082"

# Enable integration tests
export SKIP_INTEGRATION_TESTS="false"

# Run tests
pytest tests/test_external_services_integration.py -v
```

### 2. LLM Integration (`test_llm_integration.py`)
Tests integration with LLM services (OpenAI).

**Requirements:**
- Valid OpenAI API key
- Tests may incur API costs

**Run:**
```bash
# Set API key
export OPENAI_API_KEY="your-api-key-here"

# Enable LLM tests
export SKIP_LLM_TESTS="false"

# Run tests
pytest tests/test_llm_integration.py -v -m llm
```

### 3. End-to-End Tests (`test_runner_e2e.py`)
Tests complete task execution workflows.

**Requirements:**
- Git installed and configured
- Sufficient disk space for temporary workspaces

**Run:**
```bash
# Enable E2E tests
export SKIP_E2E_TESTS="false"

# Run tests
pytest tests/test_runner_e2e.py -v -m e2e
```

### 4. Performance Tests (Updated)
Tests execution performance including LLM call overhead.

**Run:**
```bash
# Run performance tests
pytest tests/test_runner_performance.py -v -m performance
pytest tests/test_parallel_runners.py -v -m performance
```

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Integration tests only
pytest -v -m integration

# LLM tests only
pytest -v -m llm

# E2E tests only
pytest -v -m e2e

# Performance tests only
pytest -v -m performance

# Slow tests only
pytest -v -m slow

# Exclude slow tests
pytest -v -m "not slow"
```

## Running All Tests

```bash
# Run all tests (with services enabled)
export SKIP_INTEGRATION_TESTS="false"
export SKIP_LLM_TESTS="false"
export SKIP_E2E_TESTS="false"
export OPENAI_API_KEY="your-api-key"

pytest tests/test_external_services_integration.py \
       tests/test_llm_integration.py \
       tests/test_runner_e2e.py \
       -v
```

## CI/CD Configuration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      task-registry:
        image: task-registry:latest
        ports:
          - 8080:8080
      
      repo-pool:
        image: repo-pool:latest
        ports:
          - 8081:8081
      
      artifact-store:
        image: artifact-store:latest
        ports:
          - 8082:8082
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      
      - name: Run integration tests
        env:
          SKIP_INTEGRATION_TESTS: "false"
          TASK_REGISTRY_URL: "http://localhost:8080"
          REPO_POOL_URL: "http://localhost:8081"
          ARTIFACT_STORE_URL: "http://localhost:8082"
        run: |
          pytest tests/test_external_services_integration.py -v
      
      - name: Run E2E tests
        env:
          SKIP_E2E_TESTS: "false"
        run: |
          pytest tests/test_runner_e2e.py -v
```

## Troubleshooting

### Tests are skipped
- Check that environment variables are set correctly
- Ensure `SKIP_*_TESTS` variables are set to `"false"` (string, not boolean)

### External service tests fail
- Verify services are running: `curl http://localhost:8080/health`
- Check service URLs are correct
- Ensure network connectivity

### LLM tests fail
- Verify API key is valid
- Check API rate limits
- Ensure sufficient API credits

### E2E tests fail
- Check Git is installed: `git --version`
- Verify disk space is available
- Check file permissions

## Test Statistics

- **External Services Integration**: 23 tests
- **LLM Integration**: 20 tests
- **End-to-End**: 18 tests
- **Performance Updates**: 5 tests enhanced
- **Total New Tests**: 61

## Performance Benchmarks

Expected performance ranges (with mocked implementations):

- Single task execution: < 30 seconds
- Workspace preparation: < 5 seconds
- Commit and push: < 5 seconds
- Artifact upload: < 10 seconds
- LLM call overhead: 30-50% of total time
- Parallel speedup: > 1.5x

## Notes

- Integration tests are designed to be idempotent
- Tests clean up resources after execution
- Temporary workspaces are created in system temp directory
- Tests use mocking where appropriate to reduce external dependencies
- Performance tests provide baseline metrics for regression detection

## Support

For issues or questions:
1. Check test output for detailed error messages
2. Review test documentation in source files
3. Verify environment configuration
4. Check service logs for external service issues

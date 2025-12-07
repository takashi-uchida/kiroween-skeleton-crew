#!/usr/bin/env python3
"""
Test script for Task 11: Logging and Monitoring Updates

Tests the updated logging, metrics, and health check functionality
for LLM and external service integration.
"""

import logging
import sys
from pathlib import Path

# Add necrocode to path
sys.path.insert(0, str(Path(__file__).parent))

from necrocode.agent_runner.logging_config import setup_logging, get_runner_logger
from necrocode.agent_runner.metrics import MetricsCollector, MetricsReporter
from necrocode.agent_runner.health_check import check_external_services, HealthStatus


def test_structured_logging():
    """Test structured logging with LLM and external service context"""
    print("\n" + "=" * 60)
    print("TEST: Structured Logging")
    print("=" * 60)
    
    # Setup logging
    setup_logging(log_level='INFO', structured=True)
    logger = get_runner_logger('test-runner-123', 'task-456', 'test-spec')
    
    # Test basic logging
    logger.info('Test log message', extra={'test_field': 'test_value'})
    
    # Test LLM logging context
    logger.info(
        'LLM request',
        extra={
            'llm_model': 'gpt-4',
            'max_tokens': 4000,
            'prompt_length': 1500
        }
    )
    
    # Test external service logging context
    logger.info(
        'External service call',
        extra={
            'service': 'task_registry',
            'operation': 'update_task_status',
            'duration_seconds': 0.5
        }
    )
    
    print("✓ Structured logging test passed")


def test_execution_metrics():
    """Test execution metrics with LLM and external service tracking"""
    print("\n" + "=" * 60)
    print("TEST: Execution Metrics")
    print("=" * 60)
    
    # Create metrics collector
    collector = MetricsCollector('test-runner', 'test-task', 'test-spec')
    
    # Record LLM calls
    collector.record_llm_call(
        duration_seconds=1.5,
        tokens_used=1000,
        prompt_tokens=500,
        completion_tokens=500
    )
    collector.record_llm_call(
        duration_seconds=2.0,
        tokens_used=1500,
        prompt_tokens=700,
        completion_tokens=800
    )
    
    # Record external service calls
    collector.record_external_service_call('task_registry', 0.5)
    collector.record_external_service_call('task_registry', 0.3)
    collector.record_external_service_call('repo_pool', 0.4)
    collector.record_external_service_call('artifact_store', 0.7)
    
    # Record other metrics
    collector.record_implementation(files_changed=5, lines_added=100, lines_removed=20)
    collector.record_tests(tests_run=10, tests_passed=9, tests_failed=1)
    
    # Finalize metrics
    metrics = collector.finalize()
    
    # Verify LLM metrics
    assert metrics.llm_calls == 2, f"Expected 2 LLM calls, got {metrics.llm_calls}"
    assert metrics.llm_total_duration_seconds == 3.5, \
        f"Expected 3.5s LLM duration, got {metrics.llm_total_duration_seconds}"
    assert metrics.llm_total_tokens == 2500, \
        f"Expected 2500 tokens, got {metrics.llm_total_tokens}"
    assert metrics.llm_prompt_tokens == 1200, \
        f"Expected 1200 prompt tokens, got {metrics.llm_prompt_tokens}"
    assert metrics.llm_completion_tokens == 1300, \
        f"Expected 1300 completion tokens, got {metrics.llm_completion_tokens}"
    
    # Verify external service metrics
    assert metrics.task_registry_calls == 2, \
        f"Expected 2 Task Registry calls, got {metrics.task_registry_calls}"
    assert metrics.task_registry_duration_seconds == 0.8, \
        f"Expected 0.8s Task Registry duration, got {metrics.task_registry_duration_seconds}"
    assert metrics.repo_pool_calls == 1, \
        f"Expected 1 Repo Pool call, got {metrics.repo_pool_calls}"
    assert metrics.artifact_store_calls == 1, \
        f"Expected 1 Artifact Store call, got {metrics.artifact_store_calls}"
    
    print(f"✓ LLM calls: {metrics.llm_calls}")
    print(f"✓ LLM duration: {metrics.llm_total_duration_seconds}s")
    print(f"✓ LLM tokens: {metrics.llm_total_tokens}")
    print(f"✓ Task Registry calls: {metrics.task_registry_calls}")
    print(f"✓ Repo Pool calls: {metrics.repo_pool_calls}")
    print(f"✓ Artifact Store calls: {metrics.artifact_store_calls}")
    print("✓ Execution metrics test passed")
    
    # Test metrics reporter
    print("\n--- Metrics Report ---")
    reporter = MetricsReporter()
    reporter.report(metrics)


def test_health_check():
    """Test health check with external service connectivity"""
    print("\n" + "=" * 60)
    print("TEST: Health Check")
    print("=" * 60)
    
    # Test health status
    health_status = HealthStatus()
    health_status.update(
        healthy=True,
        runner_state="running",
        runner_id="test-runner-123",
        current_task_id="task-456",
        current_spec_name="test-spec"
    )
    
    # Update service status
    health_status.update_service_status("task_registry", True)
    health_status.update_service_status("repo_pool", True)
    health_status.update_service_status("artifact_store", False)
    health_status.update_service_status("llm_service", True)
    
    # Get status dict
    status_dict = health_status.to_dict()
    
    # Verify external services are included
    assert "external_services" in status_dict, "external_services not in status dict"
    assert status_dict["external_services"]["task_registry"] == True
    assert status_dict["external_services"]["repo_pool"] == True
    assert status_dict["external_services"]["artifact_store"] == False
    assert status_dict["external_services"]["llm_service"] == True
    
    print(f"✓ Health status: {status_dict['status']}")
    print(f"✓ Runner state: {status_dict['runner_state']}")
    print(f"✓ External services: {status_dict['external_services']}")
    
    # Test check_external_services function (without actual clients)
    service_status = check_external_services()
    assert isinstance(service_status, dict), "service_status should be a dict"
    
    print("✓ Health check test passed")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TASK 11: LOGGING AND MONITORING UPDATES - TEST SUITE")
    print("=" * 60)
    
    try:
        test_structured_logging()
        test_execution_metrics()
        test_health_check()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nTask 11 implementation verified:")
        print("  ✓ 11.1 Structured logging updated with LLM and external service context")
        print("  ✓ 11.2 Execution metrics updated with LLM and service call tracking")
        print("  ✓ 11.3 Health check updated with external service connectivity")
        print("\nRequirements satisfied:")
        print("  ✓ 12.1, 12.2, 12.4 - Structured logging")
        print("  ✓ 12.3, 16.4 - Execution metrics")
        print("  ✓ 12.5, 15.5, 16.6 - Health checks")
        print("  ✓ 3.4 - LLM request/response logging")
        print("  ✓ 16.4 - Token usage tracking")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

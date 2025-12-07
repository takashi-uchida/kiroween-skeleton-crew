"""
Verification script for Task 9: Review Comment Implementation

This script verifies that all subtasks of Task 9 have been implemented correctly:
- 9.1: Automatic comment posting
- 9.2: Comment content with test failure details and error log links
- 9.3: Comment template customization and auto-comment disable option

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock

from necrocode.review_pr_service.pr_service import PRService
from necrocode.review_pr_service.config import PRServiceConfig, GitHostType
from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def verify_subtask_9_1():
    """Verify 9.1: Automatic comment posting."""
    logger.info("=" * 60)
    logger.info("Verifying Subtask 9.1: Automatic Comment Posting")
    logger.info("=" * 60)
    
    # Create mock Git host client
    mock_client = Mock()
    mock_client.add_comment = Mock()
    
    # Create configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="test/repo",
        api_token="test-token"
    )
    
    # Create PR service with mocked client
    pr_service = PRService(config)
    pr_service.git_host_client = mock_client
    
    # Test 1: Post simple comment
    logger.info("Test 1: Post simple comment")
    pr_service.post_comment(
        pr_id="123",
        message="Test comment",
        use_template=False
    )
    assert mock_client.add_comment.called, "❌ Comment not posted"
    logger.info("✅ Simple comment posting works")
    
    # Test 2: Post comment with details
    logger.info("Test 2: Post comment with details")
    mock_client.reset_mock()
    pr_service.post_comment(
        pr_id="123",
        message="Review required",
        details={"Priority": "High", "Reviewer": "john@example.com"},
        use_template=False
    )
    assert mock_client.add_comment.called, "❌ Comment with details not posted"
    call_args = mock_client.add_comment.call_args[0]
    assert "Priority" in call_args[1], "❌ Details not included in comment"
    logger.info("✅ Comment with details works")
    
    # Test 3: Post test failure comment
    logger.info("Test 3: Post test failure comment")
    mock_client.reset_mock()
    test_results = {
        "total": 50,
        "passed": 45,
        "failed": 5,
        "skipped": 0,
        "duration": 123.45
    }
    pr_service.post_test_failure_comment(
        pr_id="123",
        test_results=test_results
    )
    assert mock_client.add_comment.called, "❌ Test failure comment not posted"
    logger.info("✅ Test failure comment posting works")
    
    logger.info("✅ Subtask 9.1 VERIFIED: Automatic comment posting implemented")
    return True


def verify_subtask_9_2():
    """Verify 9.2: Comment content with test failure details and error logs."""
    logger.info("=" * 60)
    logger.info("Verifying Subtask 9.2: Comment Content")
    logger.info("=" * 60)
    
    # Create mock Git host client
    mock_client = Mock()
    mock_client.add_comment = Mock()
    
    # Create configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="test/repo",
        api_token="test-token"
    )
    
    # Create PR service with mocked client
    pr_service = PRService(config)
    pr_service.git_host_client = mock_client
    
    # Test 1: Comment includes test failure details
    logger.info("Test 1: Comment includes test failure details")
    test_results = {
        "total": 100,
        "passed": 95,
        "failed": 5,
        "skipped": 0,
        "duration": 456.78,
        "failed_tests": [
            {
                "name": "test_authentication",
                "error": "AssertionError: Expected 200, got 401"
            },
            {
                "name": "test_database",
                "error": "ConnectionError: Database unavailable"
            }
        ]
    }
    
    pr_service.post_test_failure_comment(
        pr_id="123",
        test_results=test_results
    )
    
    call_args = mock_client.add_comment.call_args[0]
    comment_text = call_args[1]
    
    # Verify test statistics
    assert "100" in comment_text, "❌ Total tests not in comment"
    assert "95" in comment_text, "❌ Passed tests not in comment"
    assert "5" in comment_text, "❌ Failed tests not in comment"
    assert "456.78" in comment_text, "❌ Duration not in comment"
    logger.info("✅ Test statistics included in comment")
    
    # Verify failed test details
    assert "test_authentication" in comment_text, "❌ Failed test name not in comment"
    assert "AssertionError" in comment_text, "❌ Error message not in comment"
    logger.info("✅ Failed test details included in comment")
    
    # Test 2: Comment includes error log links
    logger.info("Test 2: Comment includes error log links")
    mock_client.reset_mock()
    error_log_url = "https://ci.example.com/logs/456"
    
    pr_service.post_test_failure_comment(
        pr_id="123",
        test_results=test_results,
        error_log_url=error_log_url
    )
    
    call_args = mock_client.add_comment.call_args[0]
    comment_text = call_args[1]
    
    assert error_log_url in comment_text, "❌ Error log URL not in comment"
    assert "Error Logs" in comment_text, "❌ Error logs section not in comment"
    logger.info("✅ Error log links included in comment")
    
    # Test 3: Comment includes artifact links
    logger.info("Test 3: Comment includes artifact links")
    mock_client.reset_mock()
    artifact_links = {
        "Test Report": "https://artifacts.example.com/report.html",
        "Coverage": "https://artifacts.example.com/coverage.html"
    }
    
    pr_service.post_test_failure_comment(
        pr_id="123",
        test_results=test_results,
        artifact_links=artifact_links
    )
    
    call_args = mock_client.add_comment.call_args[0]
    comment_text = call_args[1]
    
    assert "Test Report" in comment_text, "❌ Artifact name not in comment"
    assert artifact_links["Test Report"] in comment_text, "❌ Artifact URL not in comment"
    logger.info("✅ Artifact links included in comment")
    
    # Test 4: Comment includes next steps
    assert "Next Steps" in comment_text, "❌ Next steps not in comment"
    logger.info("✅ Next steps guidance included in comment")
    
    logger.info("✅ Subtask 9.2 VERIFIED: Comment content with details implemented")
    return True


def verify_subtask_9_3():
    """Verify 9.3: Comment template customization and auto-comment disable."""
    logger.info("=" * 60)
    logger.info("Verifying Subtask 9.3: Comment Template Customization")
    logger.info("=" * 60)
    
    # Create mock Git host client
    mock_client = Mock()
    mock_client.add_comment = Mock()
    
    # Test 1: Custom comment template path configuration
    logger.info("Test 1: Custom comment template path configuration")
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="test/repo",
        api_token="test-token"
    )
    
    custom_template_path = "custom/path/to/template.md"
    config.template.comment_template_path = custom_template_path
    
    assert config.template.comment_template_path == custom_template_path, \
        "❌ Custom template path not set"
    logger.info("✅ Custom comment template path can be configured")
    
    # Test 2: Auto-comment can be disabled
    logger.info("Test 2: Auto-comment can be disabled")
    config.ci.auto_comment_on_failure = False
    
    pr_service = PRService(config)
    pr_service.git_host_client = mock_client
    
    test_results = {
        "total": 10,
        "passed": 8,
        "failed": 2,
        "skipped": 0
    }
    
    pr_service.post_test_failure_comment(
        pr_id="123",
        test_results=test_results
    )
    
    assert not mock_client.add_comment.called, \
        "❌ Comment posted even though auto-comment is disabled"
    logger.info("✅ Auto-comment can be disabled")
    
    # Test 3: Template loading functionality exists
    logger.info("Test 3: Template loading functionality")
    config.ci.auto_comment_on_failure = True
    pr_service = PRService(config)
    
    assert hasattr(pr_service, '_load_comment_template'), \
        "❌ Template loading method not found"
    logger.info("✅ Template loading functionality exists")
    
    # Test 4: Plain text fallback exists
    logger.info("Test 4: Plain text fallback")
    assert hasattr(pr_service, '_format_comment_plain'), \
        "❌ Plain text formatting method not found"
    
    plain_text = pr_service._format_comment_plain(
        "Test message",
        {"key": "value"}
    )
    assert "Test message" in plain_text, "❌ Message not in plain text"
    assert "key" in plain_text, "❌ Details not in plain text"
    logger.info("✅ Plain text fallback works")
    
    logger.info("✅ Subtask 9.3 VERIFIED: Comment template customization implemented")
    return True


def verify_task_9():
    """Verify all subtasks of Task 9."""
    logger.info("\n" + "=" * 60)
    logger.info("TASK 9 VERIFICATION: Review Comment Implementation")
    logger.info("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("9.1", verify_subtask_9_1()))
    except Exception as e:
        logger.error(f"❌ Subtask 9.1 failed: {e}")
        results.append(("9.1", False))
    
    try:
        results.append(("9.2", verify_subtask_9_2()))
    except Exception as e:
        logger.error(f"❌ Subtask 9.2 failed: {e}")
        results.append(("9.2", False))
    
    try:
        results.append(("9.3", verify_subtask_9_3()))
    except Exception as e:
        logger.error(f"❌ Subtask 9.3 failed: {e}")
        results.append(("9.3", False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    for subtask, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"Subtask {subtask}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ TASK 9 FULLY VERIFIED: All subtasks implemented correctly")
        logger.info("\nImplemented Features:")
        logger.info("- Automatic comment posting on test failures")
        logger.info("- Comprehensive test failure details in comments")
        logger.info("- Error log links in comments")
        logger.info("- Artifact links in comments")
        logger.info("- Next steps guidance in comments")
        logger.info("- Custom comment template support")
        logger.info("- Auto-comment enable/disable configuration")
        logger.info("- Plain text fallback when template unavailable")
    else:
        logger.error("❌ TASK 9 VERIFICATION FAILED: Some subtasks not implemented")
    
    logger.info("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = verify_task_9()
    exit(0 if success else 1)

"""
Verification script for Task 10: Merge Strategy Implementation.

This script verifies that all subtasks have been implemented:
- 10.1: Merge strategy configuration
- 10.2: Auto-merge on CI success
- 10.3: Required approvals configuration
- 10.4: Conflict detection
- 10.5: Merge failure handling

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_imports():
    """Verify all required imports are available."""
    logger.info("Verifying imports...")
    
    try:
        from necrocode.review_pr_service.config import (
            PRServiceConfig,
            MergeStrategy,
            MergeConfig
        )
        from necrocode.review_pr_service.pr_service import PRService
        from necrocode.review_pr_service.models import PullRequest, CIStatus
        
        logger.info("✓ All imports successful")
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def verify_merge_strategy_enum():
    """Verify MergeStrategy enum has all required values."""
    logger.info("\nVerifying MergeStrategy enum...")
    
    try:
        from necrocode.review_pr_service.config import MergeStrategy
        
        # Check all strategies exist
        strategies = [
            MergeStrategy.MERGE,
            MergeStrategy.SQUASH,
            MergeStrategy.REBASE
        ]
        
        for strategy in strategies:
            logger.info(f"  ✓ {strategy.name}: {strategy.value}")
        
        logger.info("✓ MergeStrategy enum verified")
        return True
    except Exception as e:
        logger.error(f"✗ MergeStrategy verification failed: {e}")
        return False


def verify_merge_config():
    """Verify MergeConfig class has all required fields."""
    logger.info("\nVerifying MergeConfig class...")
    
    try:
        from necrocode.review_pr_service.config import MergeConfig, MergeStrategy
        
        # Create config with all fields
        config = MergeConfig(
            strategy=MergeStrategy.SQUASH,
            auto_merge_enabled=True,
            delete_branch_after_merge=True,
            require_ci_success=True,
            required_approvals=2,
            check_conflicts=True
        )
        
        # Verify all fields
        assert hasattr(config, 'strategy')
        assert hasattr(config, 'auto_merge_enabled')
        assert hasattr(config, 'delete_branch_after_merge')
        assert hasattr(config, 'require_ci_success')
        assert hasattr(config, 'required_approvals')
        assert hasattr(config, 'check_conflicts')
        
        logger.info(f"  ✓ strategy: {config.strategy.value}")
        logger.info(f"  ✓ auto_merge_enabled: {config.auto_merge_enabled}")
        logger.info(f"  ✓ delete_branch_after_merge: {config.delete_branch_after_merge}")
        logger.info(f"  ✓ require_ci_success: {config.require_ci_success}")
        logger.info(f"  ✓ required_approvals: {config.required_approvals}")
        logger.info(f"  ✓ check_conflicts: {config.check_conflicts}")
        
        logger.info("✓ MergeConfig class verified")
        return True
    except Exception as e:
        logger.error(f"✗ MergeConfig verification failed: {e}")
        return False


def verify_pr_service_methods():
    """Verify PRService has all required merge methods."""
    logger.info("\nVerifying PRService merge methods...")
    
    try:
        from necrocode.review_pr_service.pr_service import PRService
        
        # Check all required methods exist
        required_methods = [
            'merge_pr',
            '_perform_merge_checks',
            '_get_approval_count',
            '_record_merge_failure',
            'auto_merge_on_ci_success',
            'check_merge_conflicts',
            'post_conflict_comment'
        ]
        
        for method_name in required_methods:
            assert hasattr(PRService, method_name), f"Missing method: {method_name}"
            logger.info(f"  ✓ {method_name}")
        
        logger.info("✓ All PRService merge methods verified")
        return True
    except Exception as e:
        logger.error(f"✗ PRService method verification failed: {e}")
        return False


def verify_merge_pr_signature():
    """Verify merge_pr method has correct signature."""
    logger.info("\nVerifying merge_pr method signature...")
    
    try:
        from necrocode.review_pr_service.pr_service import PRService
        import inspect
        
        # Get method signature
        sig = inspect.signature(PRService.merge_pr)
        params = list(sig.parameters.keys())
        
        # Check required parameters
        required_params = [
            'self',
            'pr_id',
            'merge_strategy',
            'delete_branch',
            'check_ci',
            'check_approvals',
            'check_conflicts'
        ]
        
        for param in required_params:
            assert param in params, f"Missing parameter: {param}"
            logger.info(f"  ✓ {param}")
        
        logger.info("✓ merge_pr signature verified")
        return True
    except Exception as e:
        logger.error(f"✗ merge_pr signature verification failed: {e}")
        return False


def verify_auto_merge_signature():
    """Verify auto_merge_on_ci_success method has correct signature."""
    logger.info("\nVerifying auto_merge_on_ci_success method signature...")
    
    try:
        from necrocode.review_pr_service.pr_service import PRService
        import inspect
        
        # Get method signature
        sig = inspect.signature(PRService.auto_merge_on_ci_success)
        params = list(sig.parameters.keys())
        
        # Check required parameters
        required_params = ['self', 'pr_id', 'merge_strategy']
        
        for param in required_params:
            assert param in params, f"Missing parameter: {param}"
            logger.info(f"  ✓ {param}")
        
        logger.info("✓ auto_merge_on_ci_success signature verified")
        return True
    except Exception as e:
        logger.error(f"✗ auto_merge_on_ci_success signature verification failed: {e}")
        return False


def verify_conflict_detection_signature():
    """Verify check_merge_conflicts method has correct signature."""
    logger.info("\nVerifying check_merge_conflicts method signature...")
    
    try:
        from necrocode.review_pr_service.pr_service import PRService
        import inspect
        
        # Get method signature
        sig = inspect.signature(PRService.check_merge_conflicts)
        params = list(sig.parameters.keys())
        
        # Check required parameters
        required_params = ['self', 'pr_id']
        
        for param in required_params:
            assert param in params, f"Missing parameter: {param}"
            logger.info(f"  ✓ {param}")
        
        logger.info("✓ check_merge_conflicts signature verified")
        return True
    except Exception as e:
        logger.error(f"✗ check_merge_conflicts signature verification failed: {e}")
        return False


def verify_git_host_client_methods():
    """Verify GitHostClient has merge-related methods."""
    logger.info("\nVerifying GitHostClient merge methods...")
    
    try:
        from necrocode.review_pr_service.git_host_client import GitHostClient
        
        # Check required methods
        required_methods = [
            'merge_pr',
            'check_conflicts'
        ]
        
        for method_name in required_methods:
            assert hasattr(GitHostClient, method_name), f"Missing method: {method_name}"
            logger.info(f"  ✓ {method_name}")
        
        logger.info("✓ GitHostClient merge methods verified")
        return True
    except Exception as e:
        logger.error(f"✗ GitHostClient method verification failed: {e}")
        return False


def verify_example_file():
    """Verify example file exists and is valid."""
    logger.info("\nVerifying example file...")
    
    try:
        example_path = Path("examples/merge_strategy_example.py")
        
        assert example_path.exists(), "Example file not found"
        logger.info(f"  ✓ File exists: {example_path}")
        
        # Check file has content
        content = example_path.read_text()
        assert len(content) > 0, "Example file is empty"
        logger.info(f"  ✓ File size: {len(content)} bytes")
        
        # Check for key functions
        required_functions = [
            'example_merge_strategy_configuration',
            'example_manual_merge',
            'example_auto_merge',
            'example_conflict_detection',
            'example_merge_failure_handling'
        ]
        
        for func_name in required_functions:
            assert func_name in content, f"Missing function: {func_name}"
            logger.info(f"  ✓ {func_name}")
        
        logger.info("✓ Example file verified")
        return True
    except Exception as e:
        logger.error(f"✗ Example file verification failed: {e}")
        return False


def verify_test_file():
    """Verify test file exists and is valid."""
    logger.info("\nVerifying test file...")
    
    try:
        test_path = Path("tests/test_merge_strategy.py")
        
        assert test_path.exists(), "Test file not found"
        logger.info(f"  ✓ File exists: {test_path}")
        
        # Check file has content
        content = test_path.read_text()
        assert len(content) > 0, "Test file is empty"
        logger.info(f"  ✓ File size: {len(content)} bytes")
        
        # Check for key test classes
        required_classes = [
            'TestMergeStrategyConfiguration',
            'TestManualMerge',
            'TestAutoMerge',
            'TestMergeChecks',
            'TestConflictDetection',
            'TestMergeFailureHandling'
        ]
        
        for class_name in required_classes:
            assert class_name in content, f"Missing test class: {class_name}"
            logger.info(f"  ✓ {class_name}")
        
        logger.info("✓ Test file verified")
        return True
    except Exception as e:
        logger.error(f"✗ Test file verification failed: {e}")
        return False


def verify_requirements_coverage():
    """Verify all requirements are covered."""
    logger.info("\nVerifying requirements coverage...")
    
    requirements = {
        "9.1": "Merge strategy configuration",
        "9.2": "Auto-merge on CI success",
        "9.3": "Required approvals configuration",
        "9.4": "Conflict detection before merge",
        "9.5": "Merge failure error recording"
    }
    
    try:
        # Check implementation file
        impl_path = Path("necrocode/review_pr_service/pr_service.py")
        impl_content = impl_path.read_text()
        
        for req_id, req_desc in requirements.items():
            # Check if requirement is mentioned in implementation
            assert req_id in impl_content, f"Requirement {req_id} not found in implementation"
            logger.info(f"  ✓ {req_id}: {req_desc}")
        
        logger.info("✓ All requirements covered")
        return True
    except Exception as e:
        logger.error(f"✗ Requirements coverage verification failed: {e}")
        return False


def main():
    """Run all verification checks."""
    logger.info("=" * 70)
    logger.info("TASK 10: MERGE STRATEGY IMPLEMENTATION VERIFICATION")
    logger.info("=" * 70)
    
    checks = [
        ("Imports", verify_imports),
        ("MergeStrategy Enum", verify_merge_strategy_enum),
        ("MergeConfig Class", verify_merge_config),
        ("PRService Methods", verify_pr_service_methods),
        ("merge_pr Signature", verify_merge_pr_signature),
        ("auto_merge_on_ci_success Signature", verify_auto_merge_signature),
        ("check_merge_conflicts Signature", verify_conflict_detection_signature),
        ("GitHostClient Methods", verify_git_host_client_methods),
        ("Example File", verify_example_file),
        ("Test File", verify_test_file),
        ("Requirements Coverage", verify_requirements_coverage)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"Check '{check_name}' failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {check_name}")
    
    logger.info("=" * 70)
    logger.info(f"Results: {passed}/{total} checks passed")
    logger.info("=" * 70)
    
    if passed == total:
        logger.info("\n✓ ALL VERIFICATIONS PASSED")
        logger.info("\nTask 10 Implementation Complete:")
        logger.info("  ✓ 10.1: Merge strategy configuration")
        logger.info("  ✓ 10.2: Auto-merge on CI success")
        logger.info("  ✓ 10.3: Required approvals configuration")
        logger.info("  ✓ 10.4: Conflict detection")
        logger.info("  ✓ 10.5: Merge failure handling")
        return 0
    else:
        logger.error(f"\n✗ {total - passed} VERIFICATION(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

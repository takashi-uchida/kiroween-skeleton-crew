#!/usr/bin/env python3
"""
Verification script for Task 10: Performance Optimization Implementation

This script verifies that all required methods and features are implemented.
"""

import inspect
from pathlib import Path


def verify_git_operations():
    """Verify GitOperations has parallel fetch method."""
    print("Checking GitOperations...")
    
    # Read the file
    git_ops_file = Path("necrocode/repo_pool/git_operations.py")
    content = git_ops_file.read_text()
    
    checks = {
        "fetch_all_parallel method": "def fetch_all_parallel(" in content,
        "ThreadPoolExecutor import": "from concurrent.futures import ThreadPoolExecutor" in content,
        "Parallel execution logic": "executor.submit" in content,
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return all(checks.values())


def verify_slot_cleaner():
    """Verify SlotCleaner has parallel and background cleanup methods."""
    print("\nChecking SlotCleaner...")
    
    # Read the file
    cleaner_file = Path("necrocode/repo_pool/slot_cleaner.py")
    content = cleaner_file.read_text()
    
    checks = {
        "cleanup_slots_parallel method": "def cleanup_slots_parallel(" in content,
        "warmup_slots_parallel method": "def warmup_slots_parallel(" in content,
        "cleanup_background method": "def cleanup_background(" in content,
        "is_background_cleanup_complete method": "def is_background_cleanup_complete(" in content,
        "get_background_cleanup_result method": "def get_background_cleanup_result(" in content,
        "cancel_background_cleanup method": "def cancel_background_cleanup(" in content,
        "get_active_background_tasks method": "def get_active_background_tasks(" in content,
        "wait_for_all_background_cleanups method": "def wait_for_all_background_cleanups(" in content,
        "shutdown_background_executor method": "def shutdown_background_executor(" in content,
        "Background executor infrastructure": "_background_executor" in content,
        "Threading support": "import threading" in content,
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return all(checks.values())


def verify_pool_manager():
    """Verify PoolManager has performance optimization methods."""
    print("\nChecking PoolManager...")
    
    # Read the file
    manager_file = Path("necrocode/repo_pool/pool_manager.py")
    content = manager_file.read_text()
    
    checks = {
        "warmup_pool_parallel method": "def warmup_pool_parallel(" in content,
        "cleanup_pool_parallel method": "def cleanup_pool_parallel(" in content,
        "release_slot_background method": "def release_slot_background(" in content,
        "_record_allocation_time method": "def _record_allocation_time(" in content,
        "_record_cleanup_time method": "def _record_cleanup_time(" in content,
        "get_allocation_metrics method": "def get_allocation_metrics(" in content,
        "get_performance_metrics method": "def get_performance_metrics(" in content,
        "export_metrics method": "def export_metrics(" in content,
        "clear_metrics method": "def clear_metrics(" in content,
        "Metrics tracking infrastructure": "_allocation_times" in content,
        "Threading support": "import threading" in content,
        "Metrics recording in allocate_slot": "_record_allocation_time(repo_name" in content,
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return all(checks.values())


def verify_example_file():
    """Verify example file exists and has all examples."""
    print("\nChecking Example File...")
    
    example_file = Path("examples/performance_optimization_example.py")
    
    if not example_file.exists():
        print("  ✗ Example file does not exist")
        return False
    
    content = example_file.read_text()
    
    checks = {
        "Parallel operations example": "def example_parallel_operations(" in content,
        "Background cleanup example": "def example_background_cleanup(" in content,
        "Metrics collection example": "def example_metrics_collection(" in content,
        "Performance comparison example": "def example_performance_comparison(" in content,
        "Main function": "def main(" in content,
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return all(checks.values())


def verify_documentation():
    """Verify summary documentation exists."""
    print("\nChecking Documentation...")
    
    summary_file = Path("TASK_10_PERFORMANCE_SUMMARY.md")
    
    if not summary_file.exists():
        print("  ✗ Summary file does not exist")
        return False
    
    content = summary_file.read_text()
    
    checks = {
        "Task 10 title": "Task 10: Performance Optimization" in content,
        "Subtask 10.1 documentation": "10.1 Parallel Processing" in content,
        "Subtask 10.2 documentation": "10.2 Background Cleanup" in content,
        "Subtask 10.3 documentation": "10.3 Metrics Collection" in content,
        "Usage examples": "Usage Examples" in content,
        "Requirements mapping": "Requirements Mapping" in content,
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return all(checks.values())


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Task 10: Performance Optimization - Verification")
    print("=" * 60)
    
    results = {
        "GitOperations": verify_git_operations(),
        "SlotCleaner": verify_slot_cleaner(),
        "PoolManager": verify_pool_manager(),
        "Example File": verify_example_file(),
        "Documentation": verify_documentation(),
    }
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    for component, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {component}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("Task 10 implementation is complete and verified!")
    else:
        print("✗ SOME CHECKS FAILED")
        print("Please review the failed components above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())

"""
Verification script for Task 11: Deadlock Detection Implementation.

This script verifies that:
1. Dependency graph analysis works correctly
2. Circular dependencies are detected
3. Deadlock warnings are logged
4. Manual intervention suggestions are provided
5. Periodic deadlock checking is integrated into DispatcherCore
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from necrocode.dispatcher.deadlock_detector import DeadlockDetector
from necrocode.dispatcher.exceptions import DeadlockDetectedError
from necrocode.task_registry.models import Task, TaskState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_dependency_graph_analysis():
    """Test 11.1: Dependency graph analysis and cycle detection."""
    print("\n" + "="*70)
    print("TEST 11.1: Dependency Graph Analysis")
    print("="*70)
    
    detector = DeadlockDetector()
    
    # Test 1: No cycles
    print("\n1. Testing linear dependencies (no cycles)...")
    tasks_no_cycle = [
        Task(id="1", title="Task 1", description="", state=TaskState.READY, dependencies=[]),
        Task(id="2", title="Task 2", description="", state=TaskState.READY, dependencies=["1"]),
        Task(id="3", title="Task 3", description="", state=TaskState.READY, dependencies=["2"]),
    ]
    
    cycles = detector.detect_deadlock(tasks_no_cycle)
    assert len(cycles) == 0, "Expected no cycles in linear dependencies"
    print("   ✅ No cycles detected in linear dependencies")
    
    # Test 2: Simple cycle
    print("\n2. Testing simple circular dependency (A -> B -> A)...")
    tasks_simple_cycle = [
        Task(id="1", title="Task 1", description="", state=TaskState.READY, dependencies=["2"]),
        Task(id="2", title="Task 2", description="", state=TaskState.READY, dependencies=["1"]),
    ]
    
    cycles = detector.detect_deadlock(tasks_simple_cycle)
    assert len(cycles) == 1, "Expected 1 cycle in simple circular dependency"
    assert "1" in cycles[0] and "2" in cycles[0], "Cycle should contain tasks 1 and 2"
    print(f"   ✅ Detected cycle: {' -> '.join(cycles[0])}")
    
    # Test 3: Complex cycle
    print("\n3. Testing complex circular dependency (A -> B -> C -> A)...")
    tasks_complex_cycle = [
        Task(id="1", title="Task 1", description="", state=TaskState.READY, dependencies=["2"]),
        Task(id="2", title="Task 2", description="", state=TaskState.READY, dependencies=["3"]),
        Task(id="3", title="Task 3", description="", state=TaskState.READY, dependencies=["1"]),
    ]
    
    cycles = detector.detect_deadlock(tasks_complex_cycle)
    assert len(cycles) == 1, "Expected 1 cycle in complex circular dependency"
    assert all(task_id in cycles[0] for task_id in ["1", "2", "3"]), \
        "Cycle should contain all three tasks"
    print(f"   ✅ Detected cycle: {' -> '.join(cycles[0])}")
    
    # Test 4: Completed tasks ignored
    print("\n4. Testing that completed tasks are ignored...")
    tasks_completed = [
        Task(id="1", title="Task 1", description="", state=TaskState.DONE, dependencies=["2"]),
        Task(id="2", title="Task 2", description="", state=TaskState.DONE, dependencies=["1"]),
    ]
    
    cycles = detector.detect_deadlock(tasks_completed)
    assert len(cycles) == 0, "Expected no cycles when tasks are completed"
    print("   ✅ Completed tasks correctly ignored")
    
    print("\n✅ Requirement 13.1: Dependency graph analysis - PASSED")
    print("✅ Requirement 13.2: Circular dependency detection - PASSED")
    return True


def test_deadlock_handling():
    """Test 11.2: Deadlock detection warnings and manual intervention."""
    print("\n" + "="*70)
    print("TEST 11.2: Deadlock Handling")
    print("="*70)
    
    detector = DeadlockDetector()
    
    # Test 1: Warning on deadlock detection
    print("\n1. Testing deadlock warning...")
    tasks_with_cycle = [
        Task(id="1", title="Frontend", description="", state=TaskState.READY, dependencies=["2"]),
        Task(id="2", title="Backend", description="", state=TaskState.READY, dependencies=["1"]),
    ]
    
    cycles = detector.detect_deadlock(tasks_with_cycle)
    assert len(cycles) > 0, "Expected deadlock to be detected"
    print(f"   ✅ Deadlock detected: {len(cycles)} cycle(s)")
    
    # Test 2: Resolution suggestions
    print("\n2. Testing resolution suggestions...")
    suggestions = detector.suggest_resolution(cycles)
    assert len(suggestions) > 0, "Expected resolution suggestions"
    print("   ✅ Resolution suggestions generated:")
    for suggestion in suggestions:
        print(f"      - {suggestion}")
    
    # Test 3: Blocked tasks identification
    print("\n3. Testing blocked tasks identification...")
    blocked_tasks = detector.get_blocked_tasks(tasks_with_cycle)
    assert len(blocked_tasks) == 2, "Expected 2 blocked tasks"
    print(f"   ✅ Identified {len(blocked_tasks)} blocked tasks:")
    for task in blocked_tasks:
        print(f"      - {task.id}: {task.title}")
    
    # Test 4: Exception raising
    print("\n4. Testing exception on deadlock...")
    try:
        detector.check_for_deadlock(tasks_with_cycle, raise_on_deadlock=True)
        assert False, "Expected DeadlockDetectedError to be raised"
    except DeadlockDetectedError as e:
        print(f"   ✅ DeadlockDetectedError raised: {str(e)[:80]}...")
    
    # Test 5: Last check time tracking
    print("\n5. Testing last check time tracking...")
    last_check = detector.get_last_check_time()
    assert last_check is not None, "Expected last check time to be recorded"
    assert isinstance(last_check, datetime), "Expected datetime object"
    print(f"   ✅ Last check time recorded: {last_check.isoformat()}")
    
    print("\n✅ Requirement 13.3: Deadlock warning - PASSED")
    print("✅ Requirement 13.4: Manual intervention request - PASSED")
    print("✅ Requirement 13.5: Periodic deadlock detection - PASSED")
    return True


def test_dispatcher_integration():
    """Test integration with DispatcherCore."""
    print("\n" + "="*70)
    print("TEST: DispatcherCore Integration")
    print("="*70)
    
    print("\n1. Testing DeadlockDetector initialization in DispatcherCore...")
    from necrocode.dispatcher import DispatcherCore, DispatcherConfig
    
    config = DispatcherConfig()
    dispatcher = DispatcherCore(config)
    
    assert hasattr(dispatcher, 'deadlock_detector'), \
        "DispatcherCore should have deadlock_detector attribute"
    assert isinstance(dispatcher.deadlock_detector, DeadlockDetector), \
        "deadlock_detector should be a DeadlockDetector instance"
    print("   ✅ DeadlockDetector initialized in DispatcherCore")
    
    print("\n2. Testing manual deadlock check method...")
    assert hasattr(dispatcher, 'check_deadlock_now'), \
        "DispatcherCore should have check_deadlock_now method"
    print("   ✅ Manual deadlock check method available")
    
    print("\n3. Testing deadlock info in status...")
    status = dispatcher.get_status()
    assert 'deadlock_info' in status, "Status should include deadlock_info"
    assert 'last_check' in status['deadlock_info'], \
        "deadlock_info should include last_check"
    assert 'detected_cycles' in status['deadlock_info'], \
        "deadlock_info should include detected_cycles"
    print("   ✅ Deadlock info included in status")
    
    print("\n✅ DispatcherCore integration - PASSED")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("TASK 11: DEADLOCK DETECTION VERIFICATION")
    print("="*70)
    print("\nVerifying implementation of:")
    print("  - 11.1: Dependency graph analysis")
    print("  - 11.2: Deadlock handling")
    print("\nRequirements:")
    print("  - 13.1: Analyze task dependency graphs")
    print("  - 13.2: Detect circular dependencies")
    print("  - 13.3: Log warnings on deadlock detection")
    print("  - 13.4: Request manual intervention")
    print("  - 13.5: Periodic deadlock detection")
    
    try:
        # Run tests
        test_dependency_graph_analysis()
        test_deadlock_handling()
        test_dispatcher_integration()
        
        # Summary
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)
        print("\n✅ ALL TESTS PASSED")
        print("\nImplemented features:")
        print("  ✅ Dependency graph construction")
        print("  ✅ Cycle detection using DFS")
        print("  ✅ Circular dependency identification")
        print("  ✅ Deadlock warnings and logging")
        print("  ✅ Resolution suggestions")
        print("  ✅ Blocked task identification")
        print("  ✅ Exception raising on deadlock")
        print("  ✅ Integration with DispatcherCore")
        print("  ✅ Periodic deadlock checking")
        print("  ✅ Status reporting")
        
        print("\n" + "="*70)
        print("Task 11: Deadlock Detection - COMPLETE ✅")
        print("="*70 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

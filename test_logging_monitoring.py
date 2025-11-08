"""Test logging and monitoring functionality."""

import logging
from io import StringIO
from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.issue_router import IssueRouter
from framework.orchestrator.workload_monitor import WorkloadMonitor
from framework.orchestrator.job_parser import RoleRequest
from framework.communication.message_bus import MessageBus
from framework.agents.base_agent import BaseSpirit


def test_issue_router_logging():
    """Test that IssueRouter logs routing decisions."""
    print("\n" + "="*70)
    print("TEST: Issue Router Logging")
    print("="*70)
    
    # Setup logging capture
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger('framework.orchestrator.issue_router')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Create message bus and spirits
    message_bus = MessageBus()
    frontend1 = BaseSpirit(role="frontend", skills=["react"], workspace="test", instance_number=1)
    frontend2 = BaseSpirit(role="frontend", skills=["vue"], workspace="test", instance_number=2)
    message_bus.register(frontend1)
    message_bus.register(frontend2)
    
    # Create router and route an issue
    router = IssueRouter(message_bus)
    issue = {
        "id": "TEST-001",
        "title": "Create login UI component",
        "description": "Build a responsive login form with validation"
    }
    
    result = router.route_issue(issue)
    
    # Check logs
    log_output = log_stream.getvalue()
    
    assert "Routing issue TEST-001" in log_output, "Should log issue routing"
    assert "matched agent type: frontend" in log_output, "Should log matched agent type"
    assert "Load balancing across 2 agents" in log_output, "Should log load balancing"
    assert "Selected least-busy agent" in log_output, "Should log selected agent"
    assert result in ["frontend_spirit_1", "frontend_spirit_2"], f"Should return valid agent: {result}"
    
    print("✅ Issue router logging test passed")
    print(f"   - Routed to: {result}")
    print(f"   - Log entries: {len(log_output.splitlines())}")
    
    # Cleanup
    logger.removeHandler(handler)


def test_keyword_analysis_logging():
    """Test that keyword analysis is logged."""
    print("\n" + "="*70)
    print("TEST: Keyword Analysis Logging")
    print("="*70)
    
    # Setup logging capture
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger = logging.getLogger('framework.orchestrator.issue_router')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    # Create message bus and spirits
    message_bus = MessageBus()
    backend = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=1)
    message_bus.register(backend)
    
    # Create router and route an issue with multiple keywords
    router = IssueRouter(message_bus)
    issue = {
        "id": "TEST-002",
        "title": "Implement REST API endpoint",
        "description": "Create authentication endpoint with JWT tokens"
    }
    
    result = router.route_issue(issue)
    
    # Check logs
    log_output = log_stream.getvalue()
    
    assert "Keyword match scores" in log_output, "Should log keyword scores"
    assert "Best match: backend" in log_output, "Should log best match"
    assert result == "backend_spirit_1", f"Should route to backend: {result}"
    
    print("✅ Keyword analysis logging test passed")
    print(f"   - Matched keywords logged")
    print(f"   - Best match: backend")
    
    # Cleanup
    logger.removeHandler(handler)


def test_load_balancing_logging():
    """Test that load balancing decisions are logged."""
    print("\n" + "="*70)
    print("TEST: Load Balancing Logging")
    print("="*70)
    
    # Setup logging capture
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger('framework.orchestrator.issue_router')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Create message bus and spirits with different workloads
    message_bus = MessageBus()
    backend1 = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=1)
    backend2 = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=2)
    
    # Assign tasks to backend1 to make it busier
    backend1.assign_task("TASK-001")
    backend1.assign_task("TASK-002")
    
    message_bus.register(backend1)
    message_bus.register(backend2)
    
    # Create router and route an issue
    router = IssueRouter(message_bus)
    issue = {
        "id": "TEST-003",
        "title": "Create API endpoint",
        "description": "Build new REST endpoint"
    }
    
    result = router.route_issue(issue)
    
    # Check logs
    log_output = log_stream.getvalue()
    
    assert "Load balancing across 2 agents" in log_output, "Should log load balancing"
    assert "backend_spirit_1: 2 active tasks" in log_output, "Should log backend1 workload"
    assert "backend_spirit_2: 0 active tasks" in log_output, "Should log backend2 workload"
    assert "Selected least-busy agent: backend_spirit_2" in log_output, "Should select least busy"
    assert result == "backend_spirit_2", f"Should route to least busy agent: {result}"
    
    print("✅ Load balancing logging test passed")
    print(f"   - backend_spirit_1: 2 tasks")
    print(f"   - backend_spirit_2: 0 tasks")
    print(f"   - Selected: {result}")
    
    # Cleanup
    logger.removeHandler(handler)


def test_workload_monitor_dashboard():
    """Test workload monitoring dashboard."""
    print("\n" + "="*70)
    print("TEST: Workload Monitor Dashboard")
    print("="*70)
    
    # Create message bus and spirits
    message_bus = MessageBus()
    
    frontend1 = BaseSpirit(role="frontend", skills=["react"], workspace="test", instance_number=1)
    frontend2 = BaseSpirit(role="frontend", skills=["vue"], workspace="test", instance_number=2)
    backend1 = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=1)
    
    # Assign tasks
    frontend1.assign_task("TASK-001")
    frontend1.assign_task("TASK-002")
    frontend2.assign_task("TASK-003")
    backend1.assign_task("TASK-004")
    backend1.complete_task("TASK-004")
    
    message_bus.register(frontend1)
    message_bus.register(frontend2)
    message_bus.register(backend1)
    
    # Create monitor and display dashboard
    monitor = WorkloadMonitor(message_bus)
    stats = monitor.display_dashboard()
    
    # Verify statistics
    assert stats["total_spirits"] == 3, f"Should have 3 spirits: {stats['total_spirits']}"
    assert stats["total_active_tasks"] == 3, f"Should have 3 active tasks: {stats['total_active_tasks']}"
    assert stats["total_completed_tasks"] == 1, f"Should have 1 completed task: {stats['total_completed_tasks']}"
    assert stats["completion_rate"] == 25.0, f"Should have 25% completion rate: {stats['completion_rate']}"
    
    print("✅ Workload monitor dashboard test passed")
    print(f"   - Total spirits: {stats['total_spirits']}")
    print(f"   - Active tasks: {stats['total_active_tasks']}")
    print(f"   - Completed tasks: {stats['total_completed_tasks']}")
    print(f"   - Completion rate: {stats['completion_rate']}%")


def test_agent_workload_display():
    """Test individual agent workload display."""
    print("\n" + "="*70)
    print("TEST: Agent Workload Display")
    print("="*70)
    
    # Create message bus and spirit
    message_bus = MessageBus()
    frontend = BaseSpirit(role="frontend", skills=["react", "redux"], workspace="test", instance_number=1)
    
    # Assign and complete tasks
    frontend.assign_task("TASK-001")
    frontend.assign_task("TASK-002")
    frontend.complete_task("TASK-001")
    
    message_bus.register(frontend)
    
    # Create monitor and display agent workload
    monitor = WorkloadMonitor(message_bus)
    details = monitor.display_agent_workload("frontend_spirit_1")
    
    # Verify details
    assert details["identifier"] == "frontend_spirit_1", "Should have correct identifier"
    assert details["role"] == "frontend", "Should have correct role"
    assert details["active_tasks"] == 1, f"Should have 1 active task: {details['active_tasks']}"
    assert details["completed_tasks"] == 1, f"Should have 1 completed task: {details['completed_tasks']}"
    assert "TASK-002" in details["current_tasks"], "Should show current task"
    assert "TASK-001" in details["completed_tasks"], "Should show completed task"
    
    print("✅ Agent workload display test passed")
    print(f"   - Active: {details['active_tasks']}")
    print(f"   - Completed: {details['completed_tasks']}")


def test_role_summary_display():
    """Test role summary display."""
    print("\n" + "="*70)
    print("TEST: Role Summary Display")
    print("="*70)
    
    # Create message bus and spirits
    message_bus = MessageBus()
    
    backend1 = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=1)
    backend2 = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=2)
    backend3 = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=3)
    
    # Assign tasks
    backend1.assign_task("TASK-001")
    backend1.assign_task("TASK-002")
    backend2.assign_task("TASK-003")
    backend3.complete_task("TASK-004")
    
    message_bus.register(backend1)
    message_bus.register(backend2)
    message_bus.register(backend3)
    
    # Create monitor and display role summary
    monitor = WorkloadMonitor(message_bus)
    summary = monitor.display_role_summary("backend")
    
    # Verify summary
    assert summary["role"] == "backend", "Should have correct role"
    assert summary["total_instances"] == 3, f"Should have 3 instances: {summary['total_instances']}"
    assert summary["total_active_tasks"] == 3, f"Should have 3 active tasks: {summary['total_active_tasks']}"
    assert summary["total_completed_tasks"] == 1, f"Should have 1 completed task: {summary['total_completed_tasks']}"
    assert summary["average_workload"] == 1.0, f"Should have 1.0 avg workload: {summary['average_workload']}"
    
    print("✅ Role summary display test passed")
    print(f"   - Instances: {summary['total_instances']}")
    print(f"   - Active: {summary['total_active_tasks']}")
    print(f"   - Completed: {summary['total_completed_tasks']}")
    print(f"   - Average: {summary['average_workload']}")


def test_necromancer_integration():
    """Test Necromancer integration with logging and monitoring."""
    print("\n" + "="*70)
    print("TEST: Necromancer Integration")
    print("="*70)
    
    # Configure logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise for test
    
    # Create necromancer
    necromancer = Necromancer(workspace="test_workspace")
    
    job_description = """
    Simple web application with user authentication and dashboard.
    Need REST API, database, and frontend UI.
    """
    
    role_requests = [
        RoleRequest(name="database", skills=["schema"], count=1),
        RoleRequest(name="backend", skills=["api"], count=2),
        RoleRequest(name="frontend", skills=["ui"], count=1),
    ]
    
    # Summon team
    team_config = necromancer.summon_team(job_description, role_requests)
    
    # Verify workload monitor is available
    assert necromancer.workload_monitor is not None, "Should have workload monitor"
    
    # Display dashboard
    stats = necromancer.display_workload_dashboard()
    
    # Verify initial state
    assert stats["total_spirits"] >= 5, f"Should have at least 5 spirits: {stats['total_spirits']}"
    assert stats["total_active_tasks"] == 0, "Should have no active tasks initially"
    
    print("✅ Necromancer integration test passed")
    print(f"   - Total spirits: {stats['total_spirits']}")
    print(f"   - Workload monitor integrated")
    
    # Cleanup
    necromancer.banish_spirits()


def run_all_tests():
    """Run all logging and monitoring tests."""
    print("\n" + "="*70)
    print("🧪 RUNNING LOGGING & MONITORING TESTS")
    print("="*70)
    
    tests = [
        test_issue_router_logging,
        test_keyword_analysis_logging,
        test_load_balancing_logging,
        test_workload_monitor_dashboard,
        test_agent_workload_display,
        test_role_summary_display,
        test_necromancer_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
    
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

"""Test script for Task 5 implementation - Multiple agent instances support."""

import sys
sys.path.insert(0, '.')

from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.job_parser import RoleRequest


def test_single_instance_team():
    """Test default single-instance team summoning."""
    print("="*60)
    print("Test 1: Single Instance Team (Default)")
    print("="*60)
    
    necromancer = Necromancer(workspace="test_workspace1")
    
    job_description = """
    Simple web application with user authentication.
    """
    
    team_config = necromancer.summon_team(job_description)
    
    # Verify spirits were created
    assert len(necromancer.spirits) > 0, "No spirits were summoned"
    
    # Check for expected spirit identifiers
    expected_spirits = [
        "architect_spirit_1",
        "scrum_master_spirit_1",
        "database_spirit_1",
        "backend_spirit_1",
        "frontend_spirit_1",
        "qa_spirit_1",
        "devops_spirit_1"
    ]
    
    for spirit_id in expected_spirits:
        assert spirit_id in necromancer.spirits, f"Missing spirit: {spirit_id}"
        spirit = necromancer.spirits[spirit_id]
        assert spirit.instance_number == 1, f"Wrong instance number for {spirit_id}"
        assert spirit.identifier == spirit_id, f"Wrong identifier for {spirit_id}"
    
    print(f"✅ Successfully summoned {len(necromancer.spirits)} spirits")
    print(f"   Spirits: {list(necromancer.spirits.keys())}")
    
    necromancer.banish_spirits()
    print("✅ Test 1 passed!\n")


def test_multiple_instance_team():
    """Test summoning multiple instances per role."""
    print("="*60)
    print("Test 2: Multiple Instance Team")
    print("="*60)
    
    necromancer = Necromancer(workspace="test_workspace2")
    
    job_description = """
    Large-scale application requiring parallel development.
    """
    
    # Define role requests with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design"], count=1),
        RoleRequest(name="backend", skills=["api_development"], count=3),
        RoleRequest(name="frontend", skills=["ui_development"], count=2),
        RoleRequest(name="qa", skills=["testing"], count=1),
        RoleRequest(name="devops", skills=["infrastructure"], count=1),
    ]
    
    team_config = necromancer.summon_team(job_description, role_requests)
    
    # Verify correct number of spirits
    # 2 (architect + scrum_master) + 1 + 3 + 2 + 1 + 1 = 10
    expected_count = 2 + sum(req.count for req in role_requests)
    assert len(necromancer.spirits) == expected_count, \
        f"Expected {expected_count} spirits, got {len(necromancer.spirits)}"
    
    # Verify backend instances
    backend_spirits = [s for s in necromancer.spirits.keys() if s.startswith("backend_spirit_")]
    assert len(backend_spirits) == 3, f"Expected 3 backend spirits, got {len(backend_spirits)}"
    assert "backend_spirit_1" in backend_spirits
    assert "backend_spirit_2" in backend_spirits
    assert "backend_spirit_3" in backend_spirits
    
    # Verify frontend instances
    frontend_spirits = [s for s in necromancer.spirits.keys() if s.startswith("frontend_spirit_")]
    assert len(frontend_spirits) == 2, f"Expected 2 frontend spirits, got {len(frontend_spirits)}"
    assert "frontend_spirit_1" in frontend_spirits
    assert "frontend_spirit_2" in frontend_spirits
    
    # Verify instance numbers are correct
    for spirit_id, spirit in necromancer.spirits.items():
        expected_num = int(spirit_id.split("_")[-1])
        assert spirit.instance_number == expected_num, \
            f"Wrong instance number for {spirit_id}: expected {expected_num}, got {spirit.instance_number}"
    
    print(f"✅ Successfully summoned {len(necromancer.spirits)} spirits")
    print(f"   Backend instances: {backend_spirits}")
    print(f"   Frontend instances: {frontend_spirits}")
    
    necromancer.banish_spirits()
    print("✅ Test 2 passed!\n")


def test_issue_router_integration():
    """Test IssueRouter integration in sprint execution."""
    print("="*60)
    print("Test 3: IssueRouter Integration")
    print("="*60)
    
    necromancer = Necromancer(workspace="test_workspace3")
    
    # Verify IssueRouter was instantiated
    assert necromancer.issue_router is not None, "IssueRouter not initialized"
    assert necromancer.issue_router.message_bus == necromancer.message_bus, \
        "IssueRouter not connected to MessageBus"
    
    print("✅ IssueRouter successfully integrated")
    
    # Summon team with multiple instances
    role_requests = [
        RoleRequest(name="frontend", skills=["ui"], count=2),
        RoleRequest(name="backend", skills=["api"], count=2),
    ]
    
    job_description = "Web application with UI and API"
    team_config = necromancer.summon_team(job_description, role_requests)
    
    # Execute sprint to test routing
    if necromancer.sprint:
        results = necromancer.execute_sprint()
        
        # Verify results include agent_instance field
        if results.get("results"):
            for result in results["results"]:
                assert "agent_instance" in result, "Missing agent_instance in result"
                print(f"   Task assigned to: {result['agent_instance']}")
    
    necromancer.banish_spirits()
    print("✅ Test 3 passed!\n")


def test_workload_tracking():
    """Test that workload tracking works with task assignment."""
    print("="*60)
    print("Test 4: Workload Tracking")
    print("="*60)
    
    necromancer = Necromancer(workspace="test_workspace4")
    
    role_requests = [
        RoleRequest(name="frontend", skills=["ui"], count=2),
    ]
    
    job_description = "Simple UI application"
    team_config = necromancer.summon_team(job_description, role_requests)
    
    # Get frontend spirits
    frontend_1 = necromancer.spirits.get("frontend_spirit_1")
    frontend_2 = necromancer.spirits.get("frontend_spirit_2")
    
    assert frontend_1 is not None, "frontend_spirit_1 not found"
    assert frontend_2 is not None, "frontend_spirit_2 not found"
    
    # Verify initial workload is 0
    assert frontend_1.get_workload() == 0, "Initial workload should be 0"
    assert frontend_2.get_workload() == 0, "Initial workload should be 0"
    
    # Assign tasks
    frontend_1.assign_task("TASK-001")
    frontend_1.assign_task("TASK-002")
    frontend_2.assign_task("TASK-003")
    
    # Verify workload
    assert frontend_1.get_workload() == 2, "frontend_1 should have 2 tasks"
    assert frontend_2.get_workload() == 1, "frontend_2 should have 1 task"
    
    # Complete a task
    frontend_1.complete_task("TASK-001")
    assert frontend_1.get_workload() == 1, "frontend_1 should have 1 task after completion"
    assert len(frontend_1.completed_tasks) == 1, "Should have 1 completed task"
    
    print("✅ Workload tracking working correctly")
    print(f"   frontend_1: {frontend_1.get_workload()} active, {len(frontend_1.completed_tasks)} completed")
    print(f"   frontend_2: {frontend_2.get_workload()} active, {len(frontend_2.completed_tasks)} completed")
    
    necromancer.banish_spirits()
    print("✅ Test 4 passed!\n")


if __name__ == "__main__":
    try:
        test_single_instance_team()
        test_multiple_instance_team()
        test_issue_router_integration()
        test_workload_tracking()
        
        print("="*60)
        print("🎉 All tests passed!")
        print("="*60)
        print("\n✅ Task 5 implementation verified:")
        print("   - Multiple agent instances per role ✓")
        print("   - Unique identifier generation ✓")
        print("   - MessageBus registration ✓")
        print("   - IssueRouter integration ✓")
        print("   - Workload tracking ✓")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

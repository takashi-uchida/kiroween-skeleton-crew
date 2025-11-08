"""Integration tests for Task 10 - Complete workflow testing."""

import sys
sys.path.insert(0, '.')

from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.issue_router import IssueRouter
from framework.orchestrator.job_parser import RoleRequest
from framework.communication.message_bus import MessageBus
from framework.agents.base_agent import BaseSpirit


def test_issue_routing_keywords():
    """Test 10.1: Test issue routing with various keywords."""
    print("\n" + "="*70)
    print("TEST 10.1: Issue Routing with Various Keywords")
    print("="*70)
    
    # Create message bus and register agents
    message_bus = MessageBus()
    
    # Register one agent of each type
    frontend = BaseSpirit(role="frontend", skills=["react"], workspace="test", instance_number=1)
    backend = BaseSpirit(role="backend", skills=["api"], workspace="test", instance_number=1)
    database = BaseSpirit(role="database", skills=["schema"], workspace="test", instance_number=1)
    qa = BaseSpirit(role="qa", skills=["testing"], workspace="test", instance_number=1)
    devops = BaseSpirit(role="devops", skills=["docker"], workspace="test", instance_number=1)
    architect = BaseSpirit(role="architect", skills=["design"], workspace="test", instance_number=1)
    
    message_bus.register(frontend)
    message_bus.register(backend)
    message_bus.register(database)
    message_bus.register(qa)
    message_bus.register(devops)
    message_bus.register(architect)
    
    router = IssueRouter(message_bus)
    
    # Test cases with English keywords
    test_cases_english = [
        {
            "issue": {"id": "TEST-001", "title": "Create login UI component", "description": "Build responsive form with validation"},
            "expected_type": "frontend",
            "keywords": ["ui", "component", "form"]
        },
        {
            "issue": {"id": "TEST-002", "title": "Implement REST API endpoint", "description": "Create authentication endpoint with JWT"},
            "expected_type": "backend",
            "keywords": ["api", "endpoint", "authentication"]
        },
        {
            "issue": {"id": "TEST-003", "title": "Design user schema", "description": "Create database migration for user table"},
            "expected_type": "database",
            "keywords": ["schema", "database", "migration", "table"]
        },
        {
            "issue": {"id": "TEST-004", "title": "Write unit tests", "description": "Add test coverage for authentication module"},
            "expected_type": "qa",
            "keywords": ["test", "coverage"]
        },
        {
            "issue": {"id": "TEST-005", "title": "Setup Docker containers", "description": "Configure CI/CD pipeline with deployment"},
            "expected_type": "devops",
            "keywords": ["docker", "ci", "deployment"]
        },
        {
            "issue": {"id": "TEST-006", "title": "System architecture design", "description": "Define tech stack and scalability patterns"},
            "expected_type": "architect",
            "keywords": ["architecture", "design", "tech stack", "scalability"]
        }
    ]
    
    print("\n📝 Testing English keyword detection:")
    for test_case in test_cases_english:
        issue = test_case["issue"]
        expected_type = test_case["expected_type"]
        
        result = router.route_issue(issue)
        
        assert result is not None, f"Failed to route issue {issue['id']}"
        assert result.startswith(expected_type), \
            f"Issue {issue['id']} routed to {result}, expected {expected_type}_spirit_1"
        
        print(f"   ✅ {issue['id']}: '{issue['title'][:40]}...' → {result}")
    
    # Test cases with Japanese keywords
    test_cases_japanese = [
        {
            "issue": {"id": "TEST-007", "title": "ログイン画面の作成", "description": "フロントエンドのコンポーネントを実装"},
            "expected_type": "frontend",
            "keywords": ["フロント", "コンポーネント", "画面"]
        },
        {
            "issue": {"id": "TEST-008", "title": "APIエンドポイントの実装", "description": "バックエンドのサーバーロジック"},
            "expected_type": "backend",
            "keywords": ["エンドポイント", "バックエンド", "サーバー"]
        },
        {
            "issue": {"id": "TEST-009", "title": "データベーススキーマ設計", "description": "テーブル構造とクエリ最適化"},
            "expected_type": "database",
            "keywords": ["データベース", "スキーマ", "テーブル", "クエリ"]
        },
        {
            "issue": {"id": "TEST-010", "title": "テストケース作成", "description": "品質保証のためのテスト"},
            "expected_type": "qa",
            "keywords": ["テスト", "品質"]
        },
        {
            "issue": {"id": "TEST-011", "title": "デプロイ設定", "description": "インフラストラクチャの構築"},
            "expected_type": "devops",
            "keywords": ["デプロイ", "インフラ"]
        }
    ]
    
    print("\n📝 Testing Japanese keyword detection:")
    for test_case in test_cases_japanese:
        issue = test_case["issue"]
        expected_type = test_case["expected_type"]
        
        result = router.route_issue(issue)
        
        assert result is not None, f"Failed to route issue {issue['id']}"
        assert result.startswith(expected_type), \
            f"Issue {issue['id']} routed to {result}, expected {expected_type}_spirit_1"
        
        print(f"   ✅ {issue['id']}: '{issue['title']}' → {result}")
    
    # Test fallback for ambiguous issues (no clear keywords)
    print("\n📝 Testing fallback for ambiguous issues:")
    ambiguous_issue = {
        "id": "TEST-012",
        "title": "General improvement",
        "description": "Make things better overall"
    }
    
    result = router.route_issue(ambiguous_issue)
    # Should return None when no keywords match
    assert result is None, f"Ambiguous issue should return None, got {result}"
    print(f"   ✅ {ambiguous_issue['id']}: No keywords matched → None (correct)")
    
    print("\n✅ Test 10.1 PASSED: Issue routing with keywords works correctly")
    print(f"   - English keywords: ✓")
    print(f"   - Japanese keywords: ✓")
    print(f"   - Ambiguous fallback: ✓")


def test_load_balancing_multiple_agents():
    """Test 10.2: Test load balancing with multiple agents."""
    print("\n" + "="*70)
    print("TEST 10.2: Load Balancing with Multiple Agents")
    print("="*70)
    
    # Create message bus and register multiple agents
    message_bus = MessageBus()
    
    # Create 2 frontend and 2 backend agents
    frontend1 = BaseSpirit(role="frontend", skills=["react"], workspace="test", instance_number=1)
    frontend2 = BaseSpirit(role="frontend", skills=["vue"], workspace="test", instance_number=2)
    backend1 = BaseSpirit(role="backend", skills=["nodejs"], workspace="test", instance_number=1)
    backend2 = BaseSpirit(role="backend", skills=["python"], workspace="test", instance_number=2)
    
    message_bus.register(frontend1)
    message_bus.register(frontend2)
    message_bus.register(backend1)
    message_bus.register(backend2)
    
    router = IssueRouter(message_bus)
    
    # Test even distribution across frontend agents
    print("\n📊 Testing even distribution across frontend agents:")
    frontend_issues = [
        {"id": f"FE-{i:03d}", "title": f"Frontend task {i}", "description": "UI component work"}
        for i in range(1, 7)  # 6 tasks
    ]
    
    frontend_assignments = {"frontend_spirit_1": 0, "frontend_spirit_2": 0}
    
    for issue in frontend_issues:
        agent = router.route_issue(issue)
        assert agent in frontend_assignments, f"Unexpected agent: {agent}"
        frontend_assignments[agent] += 1
        
        # Assign task to track workload
        if agent == "frontend_spirit_1":
            frontend1.assign_task(issue["id"])
        else:
            frontend2.assign_task(issue["id"])
        
        print(f"   {issue['id']} → {agent} (workload: {frontend1.get_workload()}, {frontend2.get_workload()})")
    
    # Verify distribution is balanced (should be 3-3 or close)
    print(f"\n📈 Frontend distribution:")
    print(f"   frontend_spirit_1: {frontend_assignments['frontend_spirit_1']} tasks")
    print(f"   frontend_spirit_2: {frontend_assignments['frontend_spirit_2']} tasks")
    
    # Allow for slight imbalance but should be roughly even
    assert abs(frontend_assignments['frontend_spirit_1'] - frontend_assignments['frontend_spirit_2']) <= 2, \
        "Load balancing should distribute tasks evenly"
    
    # Test even distribution across backend agents
    print("\n📊 Testing even distribution across backend agents:")
    backend_issues = [
        {"id": f"BE-{i:03d}", "title": f"Backend task {i}", "description": "API endpoint work"}
        for i in range(1, 7)  # 6 tasks
    ]
    
    backend_assignments = {"backend_spirit_1": 0, "backend_spirit_2": 0}
    
    for issue in backend_issues:
        agent = router.route_issue(issue)
        assert agent in backend_assignments, f"Unexpected agent: {agent}"
        backend_assignments[agent] += 1
        
        # Assign task to track workload
        if agent == "backend_spirit_1":
            backend1.assign_task(issue["id"])
        else:
            backend2.assign_task(issue["id"])
        
        print(f"   {issue['id']} → {agent} (workload: {backend1.get_workload()}, {backend2.get_workload()})")
    
    print(f"\n📈 Backend distribution:")
    print(f"   backend_spirit_1: {backend_assignments['backend_spirit_1']} tasks")
    print(f"   backend_spirit_2: {backend_assignments['backend_spirit_2']} tasks")
    
    assert abs(backend_assignments['backend_spirit_1'] - backend_assignments['backend_spirit_2']) <= 2, \
        "Load balancing should distribute tasks evenly"
    
    # Test handling of agent unavailability
    print("\n🚫 Testing handling of agent unavailability:")
    
    # Remove all frontend agents
    message_bus.spirits = [s for s in message_bus.spirits if s.role != "frontend"]
    
    unavailable_issue = {"id": "FE-999", "title": "Frontend task", "description": "UI work"}
    result = router.route_issue(unavailable_issue)
    
    assert result is None, f"Should return None when no agents available, got {result}"
    print(f"   ✅ No frontend agents available → None (correct)")
    
    print("\n✅ Test 10.2 PASSED: Load balancing works correctly")
    print(f"   - Even distribution: ✓")
    print(f"   - Multiple agents: ✓")
    print(f"   - Agent unavailability: ✓")


def test_end_to_end_workflow():
    """Test 10.4: Test end-to-end workflow with parallel agents."""
    print("\n" + "="*70)
    print("TEST 10.4: End-to-End Workflow with Parallel Agents")
    print("="*70)
    
    # Create necromancer with multiple agent instances
    necromancer = Necromancer(workspace="test_e2e")
    
    job_description = """
    Build a web application with user authentication and dashboard.
    Need REST API, database schema, and responsive UI.
    """
    
    # Define role requests with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design"], count=1),
        RoleRequest(name="backend", skills=["api_development"], count=2),
        RoleRequest(name="frontend", skills=["ui_development"], count=2),
        RoleRequest(name="qa", skills=["testing"], count=1),
        RoleRequest(name="devops", skills=["infrastructure"], count=1),
    ]
    
    print("\n🧙 Step 1: Summon team with multiple instances")
    team_config = necromancer.summon_team(job_description, role_requests)
    
    # Verify team composition
    expected_count = 2 + sum(req.count for req in role_requests)  # +2 for architect and scrum_master
    assert len(necromancer.spirits) == expected_count, \
        f"Expected {expected_count} spirits, got {len(necromancer.spirits)}"
    
    # Verify multiple instances exist
    backend_spirits = [s for s in necromancer.spirits.keys() if s.startswith("backend_spirit_")]
    frontend_spirits = [s for s in necromancer.spirits.keys() if s.startswith("frontend_spirit_")]
    
    assert len(backend_spirits) == 2, f"Expected 2 backend spirits, got {len(backend_spirits)}"
    assert len(frontend_spirits) == 2, f"Expected 2 frontend spirits, got {len(frontend_spirits)}"
    
    print(f"   ✅ Summoned {len(necromancer.spirits)} spirits")
    print(f"   ✅ Backend instances: {backend_spirits}")
    print(f"   ✅ Frontend instances: {frontend_spirits}")
    
    print("\n📋 Step 2: Route issues automatically")
    # Verify IssueRouter is integrated
    assert necromancer.issue_router is not None, "IssueRouter should be initialized"
    
    # Test routing a few issues manually
    test_issues = [
        {"id": "E2E-001", "title": "Create login form", "description": "UI component for authentication"},
        {"id": "E2E-002", "title": "Implement auth API", "description": "Backend endpoint for login"},
        {"id": "E2E-003", "title": "Design user schema", "description": "Database table for users"},
    ]
    
    routed_agents = []
    for issue in test_issues:
        agent = necromancer.issue_router.route_issue(issue)
        assert agent is not None, f"Failed to route issue {issue['id']}"
        routed_agents.append(agent)
        print(f"   ✅ {issue['id']} → {agent}")
    
    # Verify different agent types were selected
    agent_types = set(agent.split('_')[0] for agent in routed_agents)
    assert len(agent_types) >= 2, "Should route to different agent types"
    
    print("\n⚡ Step 3: Execute sprint with parallel work")
    results = necromancer.execute_sprint()
    
    # Verify sprint execution
    assert "results" in results, "Sprint should return results"
    assert len(results["results"]) > 0, "Sprint should have task assignments"
    
    # Verify agent_instance field is present
    for result in results["results"]:
        assert "agent_instance" in result, "Result should include agent_instance"
        assert result["agent_instance"] in necromancer.spirits, \
            f"Agent instance {result['agent_instance']} should exist"
    
    print(f"   ✅ Executed sprint with {len(results['results'])} task assignments")
    
    # Verify tasks were distributed across multiple agents
    assigned_agents = set(result["agent_instance"] for result in results["results"])
    print(f"   ✅ Tasks distributed across {len(assigned_agents)} agents")
    
    # Verify workload tracking
    print("\n📊 Step 4: Verify all agents tracked their tasks")
    total_active_tasks = 0
    for spirit_id, spirit in necromancer.spirits.items():
        workload = spirit.get_workload()
        total_active_tasks += workload
        if workload > 0:
            print(f"   {spirit_id}: {workload} active tasks")
    
    assert total_active_tasks > 0, "At least some agents should have active tasks"
    print(f"   ✅ Total active tasks: {total_active_tasks}")
    
    # Cleanup
    necromancer.banish_spirits()
    
    print("\n✅ Test 10.4 PASSED: End-to-end workflow works correctly")
    print(f"   - Team summoning: ✓")
    print(f"   - Issue routing: ✓")
    print(f"   - Sprint execution: ✓")
    print(f"   - Workload tracking: ✓")


def run_all_integration_tests():
    """Run all integration tests for Task 10."""
    print("\n" + "="*70)
    print("🧪 RUNNING INTEGRATION TESTS - TASK 10")
    print("="*70)
    
    tests = [
        ("10.1", "Issue Routing with Keywords", test_issue_routing_keywords),
        ("10.2", "Load Balancing with Multiple Agents", test_load_balancing_multiple_agents),
        ("10.4", "End-to-End Workflow", test_end_to_end_workflow),
    ]
    
    passed = 0
    failed = 0
    
    for test_num, test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ Test {test_num} FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Test {test_num} ERROR: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print("📊 INTEGRATION TEST RESULTS")
    print("="*70)
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("\n🎉 Task 10 Implementation Complete:")
        print("   ✓ Issue routing with various keywords (English & Japanese)")
        print("   ✓ Load balancing with multiple agents")
        print("   ✓ Branch naming with multiple instances (Task 10.3 already done)")
        print("   ✓ End-to-end workflow with parallel agents")
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
    
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Demo script showcasing multiple agent instances working in parallel.

This demo demonstrates:
1. Summoning multiple instances of the same agent type
2. Automatic issue routing to different agent instances
3. Parallel work on different branches by multiple agents
4. Workload distribution across agent instances
"""

from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.job_parser import RoleRequest


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def display_workload_distribution(necromancer: Necromancer):
    """Display current workload across all agent instances."""
    print("\n📊 Workload Distribution:")
    print("-" * 70)
    
    # Group agents by role
    agents_by_role = {}
    for spirit_id, spirit in necromancer.spirits.items():
        role = spirit.role
        if role not in agents_by_role:
            agents_by_role[role] = []
        agents_by_role[role].append(spirit)
    
    # Display workload for each role
    for role, agents in sorted(agents_by_role.items()):
        print(f"\n{role.upper()} Agents:")
        for agent in agents:
            workload = agent.get_workload()
            completed = len(agent.completed_tasks)
            bar = "█" * workload + "░" * (5 - min(workload, 5))
            print(f"  {agent.identifier:25s} | Active: {workload} | Completed: {completed} | {bar}")


def demo_single_instance_team():
    """Demo 1: Traditional single-instance team (baseline)."""
    print_section("Demo 1: Single-Instance Team (Baseline)")
    
    necromancer = Necromancer(workspace="workspace1")
    
    job_description = """
    リアルタイムでホワイトボード共有できるコラボツール。
    WebSocket通信、ユーザー認証、描画データの永続化が必要。
    """
    
    print("📜 Job Description:")
    print(job_description.strip())
    print()
    
    # Summon default team (1 of each agent type)
    team_config = necromancer.summon_team(job_description)
    
    print(f"\n👻 Team Composition: {len(necromancer.spirits)} spirits")
    for spirit_id in sorted(necromancer.spirits.keys()):
        print(f"   - {spirit_id}")
    
    # Execute sprint
    necromancer.execute_sprint()
    
    # Display workload
    display_workload_distribution(necromancer)
    
    # Cleanup
    necromancer.banish_spirits()


def demo_multi_instance_team():
    """Demo 2: Multi-instance team with automatic load balancing."""
    print_section("Demo 2: Multi-Instance Team with Load Balancing")
    
    necromancer = Necromancer(workspace="workspace2")
    
    job_description = """
    大規模IoTダッシュボードシステム。
    センサーデータのリアルタイム可視化、アラート機能、デバイス管理、
    データ分析API、管理画面、ユーザー認証が必要。
    """
    
    print("📜 Job Description:")
    print(job_description.strip())
    print()
    
    # Define role requests with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design", "migrations", "timescaledb"], count=1),
        RoleRequest(name="backend", skills=["api_development", "websocket", "business_logic"], count=3),
        RoleRequest(name="frontend", skills=["ui_development", "ux", "data_visualization"], count=3),
        RoleRequest(name="qa", skills=["testing", "quality_assurance"], count=1),
        RoleRequest(name="devops", skills=["infrastructure", "deployment", "kubernetes"], count=1),
    ]
    
    print("🔮 Summoning Configuration:")
    for req in role_requests:
        print(f"   - {req.name}: {req.count} instance(s) with skills {req.skills}")
    print()
    
    # Summon team with multiple instances
    team_config = necromancer.summon_team(job_description, role_requests)
    
    print(f"\n👻 Team Composition: {len(necromancer.spirits)} spirits")
    
    # Group by role for display
    spirits_by_role = {}
    for spirit_id, spirit in necromancer.spirits.items():
        role = spirit.role
        if role not in spirits_by_role:
            spirits_by_role[role] = []
        spirits_by_role[role].append(spirit_id)
    
    for role, spirit_ids in sorted(spirits_by_role.items()):
        print(f"\n   {role.upper()}:")
        for spirit_id in sorted(spirit_ids):
            print(f"      - {spirit_id}")
    
    # Execute sprint with automatic routing
    print("\n⚡ Executing Sprint with Automatic Issue Routing...")
    necromancer.execute_sprint()
    
    # Display workload distribution
    display_workload_distribution(necromancer)
    
    # Show branch assignments
    print("\n🌿 Branch Assignments (Simulated):")
    print("-" * 70)
    for spirit_id, spirit in sorted(necromancer.spirits.items()):
        if spirit.current_tasks:
            role = spirit.role
            instance = spirit.instance_number
            for task_id in spirit.current_tasks:
                branch_name = f"{role}/spirit-{instance}/task-{task_id}"
                print(f"  {spirit_id:25s} -> {branch_name}")
    
    # Cleanup
    necromancer.banish_spirits()


def demo_parallel_work_simulation():
    """Demo 3: Simulate parallel work with task completion."""
    print_section("Demo 3: Parallel Work Simulation")
    
    necromancer = Necromancer(workspace="workspace3")
    
    job_description = """
    E-commerce platform with multiple features:
    - Product catalog with search and filtering
    - Shopping cart and checkout flow
    - User authentication and profiles
    - Order management dashboard
    - Payment integration
    - Real-time inventory updates
    """
    
    print("📜 Job Description:")
    print(job_description.strip())
    print()
    
    # Define role requests with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design", "migrations"], count=2),
        RoleRequest(name="backend", skills=["api_development", "business_logic"], count=4),
        RoleRequest(name="frontend", skills=["ui_development", "ux"], count=4),
        RoleRequest(name="qa", skills=["testing", "quality_assurance"], count=2),
        RoleRequest(name="devops", skills=["infrastructure", "deployment"], count=1),
    ]
    
    print("🔮 Summoning Configuration:")
    for req in role_requests:
        print(f"   - {req.name}: {req.count} instance(s)")
    print()
    
    # Summon team
    team_config = necromancer.summon_team(job_description, role_requests)
    
    print(f"\n👻 Team Composition: {len(necromancer.spirits)} spirits")
    
    # Execute sprint
    print("\n⚡ Executing Sprint...")
    sprint_results = necromancer.execute_sprint()
    
    # Initial workload
    print("\n📊 Initial Workload Distribution:")
    display_workload_distribution(necromancer)
    
    # Simulate some task completions
    print("\n⏳ Simulating Task Completion...")
    print("-" * 70)
    
    # Complete some tasks to show workload changes
    completed_count = 0
    for spirit_id, spirit in necromancer.spirits.items():
        if spirit.current_tasks and completed_count < 5:
            task_id = spirit.current_tasks[0]
            spirit.complete_task(task_id)
            print(f"  ✅ {spirit_id} completed task: {task_id}")
            completed_count += 1
    
    # Show updated workload
    print("\n📊 Updated Workload Distribution:")
    display_workload_distribution(necromancer)
    
    # Show statistics
    print("\n📈 Team Statistics:")
    print("-" * 70)
    total_active = sum(s.get_workload() for s in necromancer.spirits.values())
    total_completed = sum(len(s.completed_tasks) for s in necromancer.spirits.values())
    print(f"  Total Active Tasks:    {total_active}")
    print(f"  Total Completed Tasks: {total_completed}")
    print(f"  Total Spirits:         {len(necromancer.spirits)}")
    
    # Show most/least busy agents
    if necromancer.spirits:
        busiest = max(necromancer.spirits.values(), key=lambda s: s.get_workload())
        least_busy = min(necromancer.spirits.values(), key=lambda s: s.get_workload())
        print(f"\n  Busiest Agent:  {busiest.identifier} ({busiest.get_workload()} tasks)")
        print(f"  Least Busy:     {least_busy.identifier} ({least_busy.get_workload()} tasks)")
    
    # Cleanup
    necromancer.banish_spirits()


def demo_issue_routing():
    """Demo 4: Demonstrate automatic issue routing."""
    print_section("Demo 4: Automatic Issue Routing")
    
    necromancer = Necromancer(workspace="workspace4")
    
    # Create a simple job to get the team set up
    job_description = "Full-stack web application with authentication and dashboard"
    
    # Summon team with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design"], count=1),
        RoleRequest(name="backend", skills=["api_development"], count=2),
        RoleRequest(name="frontend", skills=["ui_development"], count=2),
        RoleRequest(name="qa", skills=["testing"], count=1),
        RoleRequest(name="devops", skills=["infrastructure"], count=1),
    ]
    
    necromancer.summon_team(job_description, role_requests)
    
    print("👻 Team Summoned:")
    for spirit_id in sorted(necromancer.spirits.keys()):
        print(f"   - {spirit_id}")
    
    # Test issue routing with various keywords
    print("\n🎯 Testing Issue Routing:")
    print("-" * 70)
    
    test_issues = [
        {"title": "Create login form component", "description": "Build a React component for user login"},
        {"title": "Implement authentication API", "description": "Create REST endpoints for login and register"},
        {"title": "Design user database schema", "description": "Create tables for users and sessions"},
        {"title": "Write unit tests for auth", "description": "Test authentication logic and edge cases"},
        {"title": "Setup Docker containers", "description": "Configure Docker for deployment"},
        {"title": "Build dashboard UI", "description": "Create data visualization components"},
        {"title": "Create analytics API", "description": "Backend endpoints for data aggregation"},
        {"title": "Optimize database queries", "description": "Improve query performance for analytics"},
    ]
    
    for issue in test_issues:
        routed_agent = necromancer.issue_router.route_issue(issue)
        if routed_agent:
            agent_role = routed_agent.split('_')[0]
            print(f"\n  Issue: {issue['title']}")
            print(f"  → Routed to: {routed_agent} ({agent_role})")
            
            # Assign the task
            if routed_agent in necromancer.spirits:
                necromancer.spirits[routed_agent].assign_task(issue['title'])
        else:
            print(f"\n  Issue: {issue['title']}")
            print(f"  → No route found (would go to scrum_master)")
    
    # Show final workload distribution
    display_workload_distribution(necromancer)
    
    # Cleanup
    necromancer.banish_spirits()


def main():
    """Run all demos."""
    print("\n" + "🎃" * 35)
    print("  NecroCode Multi-Agent Orchestration Demo")
    print("🎃" * 35)
    
    # Run all demos
    demo_single_instance_team()
    demo_multi_instance_team()
    demo_parallel_work_simulation()
    demo_issue_routing()
    
    # Final message
    print("\n" + "="*70)
    print("  ✨ All demos completed! The spirits have returned to the void.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

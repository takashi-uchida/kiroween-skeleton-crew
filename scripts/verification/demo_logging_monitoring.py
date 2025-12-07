"""Demo script for logging and workload monitoring features."""

import logging
from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.job_parser import RoleRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def demo_logging_and_monitoring():
    """Demonstrate logging and workload monitoring features."""
    
    print("="*70)
    print("🎃 NECROCODE LOGGING & MONITORING DEMO 🎃")
    print("="*70)
    
    # Create necromancer with multiple agent instances
    necromancer = Necromancer(workspace="demo_workspace")
    
    job_description = """
    リアルタイムでホワイトボード共有できるコラボツール。
    WebSocket通信、ユーザー認証、描画データの永続化が必要。
    ダッシュボードでユーザー統計を可視化する。
    """
    
    # Define role requests with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design", "migrations"], count=1),
        RoleRequest(name="backend", skills=["api_development", "websocket"], count=2),
        RoleRequest(name="frontend", skills=["ui_development", "ux"], count=2),
        RoleRequest(name="qa", skills=["testing", "quality_assurance"], count=1),
        RoleRequest(name="devops", skills=["infrastructure", "deployment"], count=1),
    ]
    
    print("\n🧙 Summoning team with multiple agent instances...")
    team_config = necromancer.summon_team(job_description, role_requests)
    
    print(f"\n👻 Summoned {len(necromancer.spirits)} spirit instances:")
    for spirit_id in sorted(necromancer.spirits.keys()):
        spirit = necromancer.spirits[spirit_id]
        print(f"   - {spirit_id} (skills: {', '.join(spirit.skills[:2])})")
    
    # Display initial workload
    print("\n" + "="*70)
    print("📊 INITIAL WORKLOAD STATE")
    print("="*70)
    necromancer.display_workload_dashboard()
    
    # Execute sprint (this will trigger issue routing with logging)
    print("\n" + "="*70)
    print("⚡ EXECUTING SPRINT WITH AUTOMATIC ROUTING")
    print("="*70)
    sprint_results = necromancer.execute_sprint()
    
    # Simulate some task completions
    print("\n" + "="*70)
    print("✅ SIMULATING TASK COMPLETIONS")
    print("="*70)
    
    # Complete some tasks for demonstration
    completed_count = 0
    for spirit_id, spirit in necromancer.spirits.items():
        if spirit.current_tasks and completed_count < 5:
            task_id = spirit.current_tasks[0]
            spirit.complete_task(task_id)
            necromancer.workload_monitor.log_task_completion(spirit_id, task_id)
            print(f"✓ {spirit_id} completed task: {task_id}")
            completed_count += 1
    
    # Display updated workload
    print("\n" + "="*70)
    print("📊 UPDATED WORKLOAD STATE (AFTER COMPLETIONS)")
    print("="*70)
    necromancer.display_workload_dashboard()
    
    # Display role-specific summaries
    print("\n" + "="*70)
    print("🔍 ROLE-SPECIFIC SUMMARIES")
    print("="*70)
    
    for role in ["frontend", "backend"]:
        necromancer.display_role_summary(role)
    
    # Display individual agent workload
    print("\n" + "="*70)
    print("🔍 INDIVIDUAL AGENT DETAILS")
    print("="*70)
    
    # Show details for first frontend and backend agents
    necromancer.display_agent_workload("frontend_spirit_1")
    necromancer.display_agent_workload("backend_spirit_1")
    
    # Banish spirits (will show final dashboard)
    necromancer.banish_spirits()
    
    print("\n" + "="*70)
    print("✨ DEMO COMPLETED")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("  ✓ Detailed logging for issue routing decisions")
    print("  ✓ Keyword match analysis and scoring")
    print("  ✓ Load balancing decision logging")
    print("  ✓ Workload monitoring dashboard")
    print("  ✓ Real-time task tracking per agent")
    print("  ✓ Role-specific workload summaries")
    print("  ✓ Individual agent workload details")
    print("  ✓ Task completion rate tracking")
    print("  ✓ Visual progress bars and workload indicators")
    print("="*70 + "\n")


if __name__ == "__main__":
    demo_logging_and_monitoring()

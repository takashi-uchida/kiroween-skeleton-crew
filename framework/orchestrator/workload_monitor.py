"""Workload Monitor - tracks and displays agent workload and progress."""

import logging
from typing import Dict, List
from datetime import datetime
from framework.communication.message_bus import MessageBus

logger = logging.getLogger(__name__)


class WorkloadMonitor:
    """Monitors and displays workload distribution across agent instances."""
    
    def __init__(self, message_bus: MessageBus):
        """Initialize WorkloadMonitor with message bus reference.
        
        Args:
            message_bus: MessageBus instance for accessing registered spirits
        """
        self.message_bus = message_bus
        self.start_time = datetime.utcnow()
    
    def display_dashboard(self) -> Dict:
        """Display comprehensive workload monitoring dashboard.
        
        Returns:
            Dictionary containing workload statistics
        """
        print("\n" + "="*70)
        print("👻 NECROCODE WORKLOAD MONITORING DASHBOARD 👻")
        print("="*70)
        
        spirits = self.message_bus.spirits
        
        if not spirits:
            print("⚠️ No spirits currently summoned")
            print("="*70 + "\n")
            return {"total_spirits": 0, "total_tasks": 0, "completed_tasks": 0}
        
        # Group spirits by role
        spirits_by_role = {}
        for spirit in spirits:
            role = spirit.role
            if role not in spirits_by_role:
                spirits_by_role[role] = []
            spirits_by_role[role].append(spirit)
        
        # Display statistics by role
        total_active_tasks = 0
        total_completed_tasks = 0
        
        for role, role_spirits in sorted(spirits_by_role.items()):
            print(f"\n🔮 {role.upper()} SPIRITS ({len(role_spirits)} instance{'s' if len(role_spirits) > 1 else ''})")
            print("-" * 70)
            
            for spirit in sorted(role_spirits, key=lambda s: s.instance_number):
                active_tasks = spirit.get_workload()
                completed_tasks = len(spirit.completed_tasks)
                total_tasks = active_tasks + completed_tasks
                
                total_active_tasks += active_tasks
                total_completed_tasks += completed_tasks
                
                # Status indicator
                if active_tasks == 0 and completed_tasks == 0:
                    status = "💤 IDLE"
                elif active_tasks > 0:
                    status = "⚡ BUSY"
                else:
                    status = "✅ DONE"
                
                # Workload bar
                workload_bar = self._create_workload_bar(active_tasks, completed_tasks)
                
                print(f"  {status} {spirit.identifier}")
                print(f"     Active: {active_tasks} | Completed: {completed_tasks} | Total: {total_tasks}")
                print(f"     {workload_bar}")
                
                # Show current task IDs if any
                if spirit.current_tasks:
                    task_list = ", ".join(spirit.current_tasks[:3])
                    if len(spirit.current_tasks) > 3:
                        task_list += f" (+{len(spirit.current_tasks) - 3} more)"
                    print(f"     📋 Current: {task_list}")
        
        # Overall statistics
        print("\n" + "="*70)
        print("📊 OVERALL STATISTICS")
        print("-" * 70)
        print(f"  Total Spirits: {len(spirits)}")
        print(f"  Active Tasks: {total_active_tasks}")
        print(f"  Completed Tasks: {total_completed_tasks}")
        print(f"  Total Tasks: {total_active_tasks + total_completed_tasks}")
        
        # Calculate completion rate
        total_all_tasks = total_active_tasks + total_completed_tasks
        if total_all_tasks > 0:
            completion_rate = (total_completed_tasks / total_all_tasks) * 100
            print(f"  Completion Rate: {completion_rate:.1f}%")
            print(f"  Progress: {self._create_progress_bar(completion_rate)}")
        
        # Runtime
        runtime = datetime.utcnow() - self.start_time
        print(f"  Runtime: {runtime.total_seconds():.1f}s")
        
        print("="*70 + "\n")
        
        return {
            "total_spirits": len(spirits),
            "total_active_tasks": total_active_tasks,
            "total_completed_tasks": total_completed_tasks,
            "completion_rate": completion_rate if total_all_tasks > 0 else 0,
            "spirits_by_role": {
                role: len(role_spirits) 
                for role, role_spirits in spirits_by_role.items()
            }
        }
    
    def display_agent_workload(self, agent_identifier: str) -> Dict:
        """Display detailed workload for a specific agent.
        
        Args:
            agent_identifier: Identifier of the agent (e.g., 'frontend_spirit_1')
            
        Returns:
            Dictionary containing agent workload details
        """
        spirit = next((s for s in self.message_bus.spirits if s.identifier == agent_identifier), None)
        
        if not spirit:
            logger.warning(f"Agent {agent_identifier} not found")
            return {"error": "Agent not found"}
        
        print(f"\n{'='*70}")
        print(f"👻 AGENT WORKLOAD: {agent_identifier}")
        print(f"{'='*70}")
        print(f"  Role: {spirit.role}")
        print(f"  Instance: #{spirit.instance_number}")
        print(f"  Workspace: {spirit.workspace}")
        print(f"  Skills: {', '.join(spirit.skills)}")
        print(f"\n📊 TASK STATISTICS")
        print(f"  Active Tasks: {len(spirit.current_tasks)}")
        print(f"  Completed Tasks: {len(spirit.completed_tasks)}")
        print(f"  Total Tasks: {len(spirit.current_tasks) + len(spirit.completed_tasks)}")
        
        if spirit.current_tasks:
            print(f"\n📋 CURRENT TASKS:")
            for task_id in spirit.current_tasks:
                print(f"    ⚡ {task_id}")
        
        if spirit.completed_tasks:
            print(f"\n✅ COMPLETED TASKS:")
            for task_id in spirit.completed_tasks[-5:]:  # Show last 5
                print(f"    ✓ {task_id}")
            if len(spirit.completed_tasks) > 5:
                print(f"    ... and {len(spirit.completed_tasks) - 5} more")
        
        print(f"{'='*70}\n")
        
        return {
            "identifier": agent_identifier,
            "role": spirit.role,
            "active_tasks": len(spirit.current_tasks),
            "completed_tasks": len(spirit.completed_tasks),
            "current_tasks": spirit.current_tasks,
            "completed_tasks": spirit.completed_tasks
        }
    
    def display_role_summary(self, role: str) -> Dict:
        """Display workload summary for all agents of a specific role.
        
        Args:
            role: Role type (e.g., 'frontend', 'backend')
            
        Returns:
            Dictionary containing role workload summary
        """
        role_spirits = [s for s in self.message_bus.spirits if s.role == role]
        
        if not role_spirits:
            logger.warning(f"No agents found for role: {role}")
            return {"error": "No agents found for role"}
        
        print(f"\n{'='*70}")
        print(f"🔮 ROLE SUMMARY: {role.upper()}")
        print(f"{'='*70}")
        print(f"  Total Instances: {len(role_spirits)}")
        
        total_active = sum(s.get_workload() for s in role_spirits)
        total_completed = sum(len(s.completed_tasks) for s in role_spirits)
        
        print(f"  Total Active Tasks: {total_active}")
        print(f"  Total Completed Tasks: {total_completed}")
        print(f"  Average Workload: {total_active / len(role_spirits):.1f} tasks/agent")
        
        print(f"\n📊 INSTANCE BREAKDOWN:")
        for spirit in sorted(role_spirits, key=lambda s: s.instance_number):
            active = spirit.get_workload()
            completed = len(spirit.completed_tasks)
            status = "⚡ BUSY" if active > 0 else ("✅ DONE" if completed > 0 else "💤 IDLE")
            print(f"    {status} {spirit.identifier}: {active} active, {completed} completed")
        
        print(f"{'='*70}\n")
        
        return {
            "role": role,
            "total_instances": len(role_spirits),
            "total_active_tasks": total_active,
            "total_completed_tasks": total_completed,
            "average_workload": total_active / len(role_spirits)
        }
    
    def log_task_assignment(self, agent_identifier: str, task_id: str, issue_title: str = ""):
        """Log task assignment event.
        
        Args:
            agent_identifier: Identifier of the agent receiving the task
            task_id: ID of the task being assigned
            issue_title: Optional title of the issue/task
        """
        logger.info(f"📝 Task assigned: {task_id} → {agent_identifier}")
        if issue_title:
            logger.info(f"   Title: {issue_title}")
    
    def log_task_completion(self, agent_identifier: str, task_id: str):
        """Log task completion event.
        
        Args:
            agent_identifier: Identifier of the agent completing the task
            task_id: ID of the task being completed
        """
        logger.info(f"✅ Task completed: {task_id} by {agent_identifier}")
    
    def _create_workload_bar(self, active: int, completed: int, width: int = 30) -> str:
        """Create a visual workload bar.
        
        Args:
            active: Number of active tasks
            completed: Number of completed tasks
            width: Width of the bar in characters
            
        Returns:
            String representation of the workload bar
        """
        total = active + completed
        if total == 0:
            return "[" + " " * width + "]"
        
        completed_width = int((completed / total) * width)
        active_width = int((active / total) * width)
        remaining_width = width - completed_width - active_width
        
        bar = "["
        bar += "█" * completed_width  # Completed tasks
        bar += "▓" * active_width      # Active tasks
        bar += " " * remaining_width   # Empty space
        bar += "]"
        
        return bar
    
    def _create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """Create a progress bar.
        
        Args:
            percentage: Completion percentage (0-100)
            width: Width of the bar in characters
            
        Returns:
            String representation of the progress bar
        """
        filled = int((percentage / 100) * width)
        empty = width - filled
        
        bar = "["
        bar += "█" * filled
        bar += "░" * empty
        bar += f"] {percentage:.1f}%"
        
        return bar

"""
Kiro Orchestrator - Manages task execution workflow
"""
import subprocess
from pathlib import Path
from typing import List, Dict, Set
from .task_planner import Task, TaskPlanner
from .task_context import TaskContextGenerator


class KiroOrchestrator:
    """Orchestrates Kiro task execution with dependency management"""
    
    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.planner = TaskPlanner(workspace_root)
        self.context_gen = TaskContextGenerator(workspace_root)
        self.completed_tasks: Set[str] = set()
    
    def execute_project(self, project_name: str):
        """Execute all tasks for a project"""
        print(f"\n🚀 Starting project execution: {project_name}\n")
        
        # Load tasks
        tasks = self.planner.load_tasks(project_name)
        print(f"📋 Loaded {len(tasks)} tasks\n")
        
        # Execute tasks in dependency order
        while len(self.completed_tasks) < len(tasks):
            ready_tasks = self._get_ready_tasks(tasks)
            
            if not ready_tasks:
                print("⚠️  No tasks ready to execute. Check for circular dependencies.")
                break
            
            for task in ready_tasks:
                self._execute_task(task, tasks)
        
        print(f"\n✅ Project execution complete: {len(self.completed_tasks)}/{len(tasks)} tasks completed\n")
    
    def _get_ready_tasks(self, tasks: List[Task]) -> List[Task]:
        """Get tasks that are ready to execute (dependencies met)"""
        ready = []
        for task in tasks:
            if task.id in self.completed_tasks:
                continue
            
            # Check if all dependencies are completed
            deps_met = all(dep in self.completed_tasks for dep in task.dependencies)
            if deps_met:
                ready.append(task)
        
        return ready
    
    def _execute_task(self, task: Task, all_tasks: List[Task]):
        """Execute a single task"""
        print(f"\n{'='*60}")
        print(f"📌 Task {task.id}: {task.title}")
        print(f"{'='*60}\n")
        
        # Get completed dependency tasks
        completed_deps = [t for t in all_tasks if t.id in self.completed_tasks]
        
        # Create branch
        branch_name = self._create_branch(task)
        
        # Generate task context
        self.context_gen.write_context(task, completed_deps)
        
        # Show instructions for manual execution
        print(f"\n📝 Task context created at .kiro/current-task.md")
        print(f"\n🔧 To execute this task:")
        print(f"   1. Review .kiro/current-task.md")
        print(f"   2. Implement the solution")
        print(f"   3. Commit with: git commit -m 'feat(task-{task.id}): {task.title}'")
        print(f"   4. Push branch: git push origin {branch_name}")
        print(f"   5. Create PR on GitHub")
        print(f"\n⏸️  Press Enter when task is complete...")
        
        input()  # Wait for user confirmation
        
        # Mark as completed
        self.completed_tasks.add(task.id)
        self.context_gen.clear_context()
        
        print(f"✅ Task {task.id} marked as complete\n")
    
    def _create_branch(self, task: Task) -> str:
        """Create a git branch for the task"""
        # Sanitize title for branch name
        slug = task.title.lower().replace(' ', '-').replace('/', '-')
        branch_name = f"feature/task-{task.id}-{slug}"
        
        try:
            # Create and checkout branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.workspace_root,
                check=True,
                capture_output=True
            )
            print(f"✓ Created branch: {branch_name}")
        except subprocess.CalledProcessError:
            # Branch might already exist, try to checkout
            try:
                subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=self.workspace_root,
                    check=True,
                    capture_output=True
                )
                print(f"✓ Checked out existing branch: {branch_name}")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Could not create/checkout branch: {e}")
        
        return branch_name
    
    def list_tasks(self, project_name: str):
        """List all tasks for a project"""
        tasks = self.planner.load_tasks(project_name)
        
        print(f"\n📋 Tasks for {project_name}:\n")
        for task in tasks:
            status = "✅" if task.id in self.completed_tasks else "⏳"
            deps = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""
            print(f"{status} Task {task.id}: {task.title}{deps}")
            print(f"   Type: {task.type}")
            print(f"   Files: {', '.join(task.files_to_create)}")
            print()

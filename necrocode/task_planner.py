"""
Task Planner - Converts job descriptions into structured task lists
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class Task:
    id: str
    title: str
    description: str
    dependencies: List[str]
    type: str  # backend, frontend, database, qa, devops
    files_to_create: List[str]
    acceptance_criteria: List[str]
    technical_context: Dict[str, Any]


class TaskPlanner:
    """Breaks down job descriptions into executable tasks"""
    
    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.tasks_dir = workspace_root / ".kiro" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
    
    def plan(self, job_description: str, project_name: str) -> List[Task]:
        """
        Converts job description into structured tasks.
        
        This is a template - in practice, you'd use Kiro to analyze
        the job description and generate this breakdown.
        """
        # For now, return a template structure
        # In production, this would call Kiro API or use LLM
        tasks = self._generate_task_breakdown(job_description, project_name)
        
        # Save to disk
        self.save_tasks(project_name, tasks)
        
        return tasks
    
    def _generate_task_breakdown(self, job_description: str, project_name: str) -> List[Task]:
        """
        Generates task breakdown from job description.
        This is where you'd integrate with Kiro's AI capabilities.
        """
        # Template implementation - replace with actual AI analysis
        return [
            Task(
                id="1",
                title="Project setup and structure",
                description="Initialize project structure with necessary directories and configuration files",
                dependencies=[],
                type="setup",
                files_to_create=["README.md", "package.json", ".gitignore"],
                acceptance_criteria=[
                    "Project structure is created",
                    "Dependencies are defined",
                    "README has basic documentation"
                ],
                technical_context={
                    "stack": "To be determined from job description",
                    "framework": "To be determined"
                }
            )
        ]
    
    def save_tasks(self, project_name: str, tasks: List[Task]):
        """Saves tasks to .kiro/tasks/{project}/tasks.json"""
        project_dir = self.tasks_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        tasks_file = project_dir / "tasks.json"
        
        data = {
            "project": project_name,
            "tasks": [asdict(task) for task in tasks]
        }
        
        with open(tasks_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Saved {len(tasks)} tasks to {tasks_file}")
    
    def load_tasks(self, project_name: str) -> List[Task]:
        """Loads tasks from .kiro/tasks/{project}/tasks.json"""
        tasks_file = self.tasks_dir / project_name / "tasks.json"
        
        if not tasks_file.exists():
            raise FileNotFoundError(f"No tasks found for project: {project_name}")
        
        with open(tasks_file, 'r') as f:
            data = json.load(f)
        
        return [Task(**task_data) for task_data in data["tasks"]]

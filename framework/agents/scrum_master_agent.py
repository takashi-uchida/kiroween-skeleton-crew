"""Scrum Master spirit - orchestrates the development ritual."""

from typing import List, Dict
from .base_agent import BaseSpirit


class ScrumMasterSpirit(BaseSpirit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backlog = []
        self.current_sprint = []
        self.dependencies = {}

    def decompose_job(self, job_description: str, architecture: dict) -> List[Dict]:
        """Break down job description into user stories."""
        stories = []
        
        # Authentication story
        if "認証" in job_description or "auth" in job_description.lower():
            stories.append({
                "id": "US-001",
                "title": "User Authentication",
                "description": "As a user, I want to login/register",
                "tasks": [
                    {"agent": "database", "task": "Create User schema"},
                    {"agent": "backend", "task": "Implement auth endpoints"},
                    {"agent": "frontend", "task": "Create login UI"},
                    {"agent": "qa", "task": "Write auth tests"},
                ],
                "priority": "high",
            })
        
        # Real-time features
        if "realtime" in job_description.lower() or "リアルタイム" in job_description:
            stories.append({
                "id": "US-002",
                "title": "Real-time Communication",
                "description": "As a user, I want real-time updates",
                "tasks": [
                    {"agent": "backend", "task": "Setup WebSocket server"},
                    {"agent": "frontend", "task": "Implement WebSocket client"},
                    {"agent": "qa", "task": "Test real-time sync"},
                ],
                "priority": "high",
            })
        
        # Data visualization
        if "dashboard" in job_description.lower() or "ダッシュボード" in job_description:
            stories.append({
                "id": "US-003",
                "title": "Data Visualization",
                "description": "As a user, I want to see data charts",
                "tasks": [
                    {"agent": "frontend", "task": "Implement chart components"},
                    {"agent": "backend", "task": "Create data aggregation API"},
                    {"agent": "database", "task": "Optimize queries for analytics"},
                ],
                "priority": "medium",
            })
        
        # DevOps story (always needed)
        stories.append({
            "id": "US-099",
            "title": "Infrastructure Setup",
            "description": "As a team, we need deployment infrastructure",
            "tasks": [
                {"agent": "devops", "task": "Create Docker configuration"},
                {"agent": "devops", "task": "Setup CI/CD pipeline"},
            ],
            "priority": "high",
        })
        
        self.backlog = stories
        return stories

    def create_sprint(self, sprint_number: int = 1) -> Dict:
        """Create a sprint from backlog."""
        high_priority = [s for s in self.backlog if s["priority"] == "high"]
        self.current_sprint = high_priority[:3]  # Max 3 stories per sprint
        
        return {
            "sprint_number": sprint_number,
            "stories": self.current_sprint,
            "chant": self.chant(f"Conjuring Sprint {sprint_number} from the backlog..."),
        }

    def assign_tasks(self, story: Dict) -> List[Dict]:
        """Assign tasks to spirits with dependencies."""
        assignments = []
        
        for task in story["tasks"]:
            assignment = {
                "story_id": story["id"],
                "agent": task["agent"],
                "task": task["task"],
                "status": "assigned",
                "blocking": self._get_blockers(task["agent"], story["tasks"]),
            }
            assignments.append(assignment)
        
        return assignments

    def _get_blockers(self, agent: str, all_tasks: List[Dict]) -> List[str]:
        """Determine which agents this task depends on."""
        # Database must complete before backend
        if agent == "backend":
            db_tasks = [t for t in all_tasks if t["agent"] == "database"]
            if db_tasks:
                return ["database"]
        
        # Frontend must wait for backend
        if agent == "frontend":
            backend_tasks = [t for t in all_tasks if t["agent"] == "backend"]
            if backend_tasks:
                return ["backend"]
        
        # QA waits for everyone
        if agent == "qa":
            return [t["agent"] for t in all_tasks if t["agent"] != "qa"]
        
        return []

    def resolve_conflict(self, conflict: Dict) -> str:
        """Resolve conflicts between spirits."""
        return self.chant(f"Mediating spectral dispute: {conflict.get('issue', 'unknown')}")

    def track_progress(self) -> Dict:
        """Track sprint progress."""
        return {
            "total_stories": len(self.current_sprint),
            "completed": 0,  # Would be updated by coordinator
            "in_progress": len(self.current_sprint),
            "chant": self.chant("Consulting the ethereal burndown chart..."),
        }

"""Scrum Master spirit - orchestrates the development ritual."""

from typing import List, Dict, Optional
from datetime import datetime
from .base_agent import BaseSpirit
from framework.communication.protocol import Issue


class ScrumMasterSpirit(BaseSpirit):
    def __init__(self, *args, message_bus=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.backlog = []
        self.current_sprint = []
        self.dependencies = {}
        self.message_bus = message_bus
        self.issue_router = None
        self.issue_counter = 0
        
        # Initialize IssueRouter if message_bus is provided
        if self.message_bus:
            from framework.orchestrator.issue_router import IssueRouter
            self.issue_router = IssueRouter(self.message_bus)

    def decompose_job(self, job_description: str, architecture: dict) -> List[Dict]:
        """Break down job description into user stories with Issue objects."""
        stories = []
        
        # Authentication story
        if "認証" in job_description or "auth" in job_description.lower():
            auth_issues = [
                self._create_issue("Create User schema", "Database schema for user authentication", ["database", "schema"], "high"),
                self._create_issue("Implement auth endpoints", "REST API endpoints for login/register", ["backend", "api", "auth"], "high"),
                self._create_issue("Create login UI", "User interface for authentication", ["frontend", "ui", "auth"], "high"),
                self._create_issue("Write auth tests", "Test suite for authentication flow", ["qa", "test"], "high"),
            ]
            stories.append({
                "id": "US-001",
                "title": "User Authentication",
                "description": "As a user, I want to login/register",
                "tasks": [
                    {"agent": "database", "task": "Create User schema", "issue": auth_issues[0]},
                    {"agent": "backend", "task": "Implement auth endpoints", "issue": auth_issues[1]},
                    {"agent": "frontend", "task": "Create login UI", "issue": auth_issues[2]},
                    {"agent": "qa", "task": "Write auth tests", "issue": auth_issues[3]},
                ],
                "issues": auth_issues,
                "priority": "high",
            })
        
        # Real-time features
        if "realtime" in job_description.lower() or "リアルタイム" in job_description:
            realtime_issues = [
                self._create_issue("Setup WebSocket server", "Configure WebSocket for real-time communication", ["backend", "websocket"], "high"),
                self._create_issue("Implement WebSocket client", "Frontend WebSocket integration", ["frontend", "websocket"], "high"),
                self._create_issue("Test real-time sync", "Verify real-time data synchronization", ["qa", "test"], "high"),
            ]
            stories.append({
                "id": "US-002",
                "title": "Real-time Communication",
                "description": "As a user, I want real-time updates",
                "tasks": [
                    {"agent": "backend", "task": "Setup WebSocket server", "issue": realtime_issues[0]},
                    {"agent": "frontend", "task": "Implement WebSocket client", "issue": realtime_issues[1]},
                    {"agent": "qa", "task": "Test real-time sync", "issue": realtime_issues[2]},
                ],
                "issues": realtime_issues,
                "priority": "high",
            })
        
        # Data visualization
        if "dashboard" in job_description.lower() or "ダッシュボード" in job_description:
            viz_issues = [
                self._create_issue("Implement chart components", "Create data visualization components", ["frontend", "ui", "chart"], "medium"),
                self._create_issue("Create data aggregation API", "Backend API for analytics data", ["backend", "api"], "medium"),
                self._create_issue("Optimize queries for analytics", "Database query optimization", ["database", "query"], "medium"),
            ]
            stories.append({
                "id": "US-003",
                "title": "Data Visualization",
                "description": "As a user, I want to see data charts",
                "tasks": [
                    {"agent": "frontend", "task": "Implement chart components", "issue": viz_issues[0]},
                    {"agent": "backend", "task": "Create data aggregation API", "issue": viz_issues[1]},
                    {"agent": "database", "task": "Optimize queries for analytics", "issue": viz_issues[2]},
                ],
                "issues": viz_issues,
                "priority": "medium",
            })
        
        # DevOps story (always needed)
        devops_issues = [
            self._create_issue("Create Docker configuration", "Setup Docker containers for deployment", ["devops", "docker"], "high"),
            self._create_issue("Setup CI/CD pipeline", "Configure continuous integration and deployment", ["devops", "ci", "cd"], "high"),
        ]
        stories.append({
            "id": "US-099",
            "title": "Infrastructure Setup",
            "description": "As a team, we need deployment infrastructure",
            "tasks": [
                {"agent": "devops", "task": "Create Docker configuration", "issue": devops_issues[0]},
                {"agent": "devops", "task": "Setup CI/CD pipeline", "issue": devops_issues[1]},
            ],
            "issues": devops_issues,
            "priority": "high",
        })
        
        self.backlog = stories
        return stories
    
    def _create_issue(self, title: str, description: str, labels: List[str], priority: str) -> Issue:
        """Create a new Issue object with auto-incrementing ID."""
        self.issue_counter += 1
        return Issue(
            id=f"ISSUE-{self.issue_counter:03d}",
            title=title,
            description=description,
            labels=labels,
            priority=priority,
            assigned_to="",
            status="open",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

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
        """Assign tasks to spirits with dependencies and automatic routing."""
        assignments = []
        
        for task in story["tasks"]:
            issue = task.get("issue")
            
            # Try automatic routing if IssueRouter is available and issue exists
            agent_instance = None
            if self.issue_router and issue:
                # Route using Issue object
                issue_dict = {
                    "title": issue.title,
                    "description": issue.description
                }
                agent_instance = self.route_issue(issue_dict)
                
                # Update issue with assignment
                if agent_instance:
                    issue.assigned_to = agent_instance
                    issue.status = "assigned"
                    issue.updated_at = datetime.utcnow()
            
            # Fallback to agent type if no specific instance found
            if not agent_instance:
                agent_instance = self._get_available_agent(task["agent"])
            
            assignment = {
                "story_id": story["id"],
                "agent": task["agent"],
                "agent_instance": agent_instance,
                "task": task["task"],
                "issue_id": issue.id if issue else "",
                "status": "assigned",
                "blocking": self._get_blockers(task["agent"], story["tasks"]),
            }
            assignments.append(assignment)
        
        return assignments
    
    def route_issue(self, issue: Dict) -> Optional[str]:
        """Route issue to appropriate agent using IssueRouter.
        
        Args:
            issue: Dictionary with 'title' and 'description'
            
        Returns:
            Agent identifier or None if routing fails
        """
        if not self.issue_router:
            return None
        
        return self.issue_router.route_issue(issue)
    
    def _get_available_agent(self, agent_type: str) -> Optional[str]:
        """Get available agent of specified type with load balancing.
        
        Args:
            agent_type: Type of agent (e.g., 'frontend', 'backend')
            
        Returns:
            Agent identifier or agent_type if no specific instance found
        """
        if not self.message_bus:
            return agent_type
        
        # Find all agents of the requested type
        agents = [s for s in self.message_bus.spirits if s.role == agent_type]
        
        if not agents:
            return agent_type
        
        # Select least-busy agent
        least_busy = min(agents, key=lambda a: a.get_workload())
        return least_busy.identifier

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

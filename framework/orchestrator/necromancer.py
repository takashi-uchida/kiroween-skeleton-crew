"""The Necromancer - master orchestrator that summons and coordinates all spirits."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from framework.agents import (
    ArchitectSpirit,
    ScrumMasterSpirit,
    FrontendSpirit,
    BackendSpirit,
    DatabaseSpirit,
    QASpirit,
    DevOpsSpirit,
    DocumentationSpirit,
)
from framework.communication.protocol import AgentMessage
from framework.communication.message_bus import MessageBus
from framework.orchestrator.issue_router import IssueRouter
from framework.orchestrator.workload_monitor import WorkloadMonitor
from framework.orchestrator.job_parser import RoleRequest
from strandsagents import SpecTaskRunner

# Configure logger
logger = logging.getLogger(__name__)


class Necromancer:
    """The master summoner who orchestrates the entire development ritual."""
    
    def __init__(
        self,
        workspace: str = "workspace1",
        spec_task_runner: Optional[SpecTaskRunner] = None,
    ):
        self.workspace = workspace
        self.message_bus = MessageBus()
        self.issue_router = IssueRouter(self.message_bus)
        self.workload_monitor = WorkloadMonitor(self.message_bus)
        self.spirits = {}
        self.architecture = None
        self.sprint = None
        self.spec_task_runner = spec_task_runner or SpecTaskRunner()
        
    def summon_team(self, job_description: str, role_requests: List[RoleRequest] = None) -> Dict:
        """Main entry point: summon a complete development team.
        
        Args:
            job_description: Natural language description of the project
            role_requests: Optional list of RoleRequest objects specifying roles and counts
                          If None, uses default single-instance team
        
        Returns:
            Dictionary with team configuration, architecture, sprint, and stories
        """
        print("🧙 Necromancer is analyzing the Job Description...")
        print(f"📜 Job: {job_description[:100]}...")
        
        # Phase 1: Summon Architect
        print("\n👻 Summoning Architect Ghost from the crypt...")
        architect = ArchitectSpirit(
            role="architect",
            skills=["system_design", "api_design"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["architect_spirit_1"] = architect
        self.message_bus.register(architect)
        
        # Architect designs the system
        self.architecture = architect.design_system(job_description)
        print(f"📐 {self.architecture['chant']}")
        print(f"   Tech Stack: {self.architecture['tech_stack']}")
        
        # Phase 2: Summon Scrum Master
        print("\n📋 Summoning Phantom Scrum Master...")
        scrum_master = ScrumMasterSpirit(
            role="scrum_master",
            skills=["task_management", "coordination"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["scrum_master_spirit_1"] = scrum_master
        self.message_bus.register(scrum_master)
        
        # Scrum Master decomposes job into stories
        stories = scrum_master.decompose_job(job_description, self.architecture)
        print(f"📋 {scrum_master.chant(f'Created {len(stories)} user stories')}")
        
        # Create sprint
        self.sprint = scrum_master.create_sprint(sprint_number=1)
        print(f"🕷️ {self.sprint['chant']}")
        
        # Phase 3: Summon development spirits
        print("\n💀 Raising the development spirits...")
        
        # If role_requests provided, use them; otherwise use defaults
        if role_requests:
            self._summon_from_requests(role_requests)
        else:
            self._summon_default_team()
        
        print("\n🕷️ All spirits have been summoned!")
        
        return {
            "team": list(self.spirits.keys()),
            "architecture": self.architecture,
            "sprint": self.sprint,
            "stories": stories,
        }

    def execute_spec_tasks(
        self,
        spec_name: str,
        specs_root: Optional[Path] = None,
        tasks_filename: str = "tasks.md",
    ) -> List[dict]:
        """Run .kiro spec tasks through Strands Agents by default.

        Args:
            spec_name: Name of the spec folder inside .kiro/specs
            specs_root: Base directory that contains .kiro/specs (defaults to repo root)
            tasks_filename: Markdown file describing the tasks (defaults to tasks.md)

        Returns:
            List of Strands agent outputs per task.
        """

        base = Path(specs_root or Path.cwd())
        tasks_path = base / ".kiro" / "specs" / spec_name / tasks_filename
        logger.info("Executing spec tasks via Strands Agents: %s", tasks_path)
        return self.spec_task_runner.run(tasks_path)
    
    def _summon_from_requests(self, role_requests: List[RoleRequest]) -> None:
        """Summon spirits based on role requests with instance counts.
        
        Args:
            role_requests: List of RoleRequest objects with role name, skills, and count
        """
        spirit_classes = {
            "database": DatabaseSpirit,
            "backend": BackendSpirit,
            "frontend": FrontendSpirit,
            "qa": QASpirit,
            "devops": DevOpsSpirit,
            "documentation": DocumentationSpirit,
        }
        
        for request in role_requests:
            spirit_class = spirit_classes.get(request.name)
            if not spirit_class:
                print(f"⚠️ Unknown role: {request.name}, skipping...")
                continue
            
            # Create multiple instances based on count
            for instance_num in range(1, request.count + 1):
                spirit = spirit_class(
                    role=request.name,
                    skills=request.skills,
                    workspace=self.workspace,
                    instance_number=instance_num
                )
                
                # Register with unique identifier
                self.spirits[spirit.identifier] = spirit
                self.message_bus.register(spirit)
                
                # Print summoning message based on role
                if request.name == "database":
                    print(f"   {spirit.weave_schema()}")
                elif request.name == "backend":
                    print(f"   {spirit.forge_api()}")
                elif request.name == "frontend":
                    print(f"   {spirit.summon_ui()}")
                elif request.name == "qa":
                    test_strategy = spirit.create_test_strategy(self.architecture)
                    print(f"   {test_strategy['chant']}")
                elif request.name == "devops":
                    print(f"   {spirit.chant('Preparing the deployment catacombs...')}")
                elif request.name == "documentation":
                    print(f"   {spirit.summon_documentation()}")
    
    def _summon_default_team(self) -> None:
        """Summon default single-instance team (legacy behavior)."""
        # Database Spirit
        database = DatabaseSpirit(
            role="database",
            skills=["schema_design", "migrations"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["database_spirit_1"] = database
        self.message_bus.register(database)
        print(f"   {database.weave_schema()}")
        
        # Backend Spirit
        backend = BackendSpirit(
            role="backend",
            skills=["api_development", "business_logic"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["backend_spirit_1"] = backend
        self.message_bus.register(backend)
        print(f"   {backend.forge_api()}")
        
        # Frontend Spirit
        frontend = FrontendSpirit(
            role="frontend",
            skills=["ui_development", "ux"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["frontend_spirit_1"] = frontend
        self.message_bus.register(frontend)
        print(f"   {frontend.summon_ui()}")
        
        # QA Spirit
        qa = QASpirit(
            role="qa",
            skills=["testing", "quality_assurance"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["qa_spirit_1"] = qa
        self.message_bus.register(qa)
        test_strategy = qa.create_test_strategy(self.architecture)
        print(f"   {test_strategy['chant']}")
        
        # DevOps Spirit
        devops = DevOpsSpirit(
            role="devops",
            skills=["infrastructure", "deployment"],
            workspace=self.workspace,
            instance_number=1
        )
        self.spirits["devops_spirit_1"] = devops
        self.message_bus.register(devops)
        print(f"   {devops.chant('Preparing the deployment catacombs...')}")
    
    def execute_sprint(self) -> Dict:
        """Execute the current sprint with spirit coordination and automatic issue routing."""
        if not self.sprint:
            return {"error": "No sprint created"}
        
        print("\n⚡ Beginning Sprint Execution...")
        logger.info(f"Starting sprint execution for workspace: {self.workspace}")
        
        scrum_master = self.spirits.get("scrum_master_spirit_1")
        if not scrum_master:
            # Fallback to legacy key
            scrum_master = self.spirits.get("scrum_master")
        
        # Display initial workload state
        print("\n📊 Initial Workload State:")
        self.workload_monitor.display_dashboard()
        
        results = []
        for story in self.sprint["stories"]:
            print(f"\n📖 Story: {story['title']}")
            logger.info(f"Processing story: {story['id']} - {story['title']}")
            
            # Assign tasks
            assignments = scrum_master.assign_tasks(story)
            
            for assignment in assignments:
                agent_type = assignment["agent"]
                task = assignment["task"]
                blockers = assignment["blocking"]
                issue_id = assignment.get("issue_id", story.get("id", ""))
                
                # Use IssueRouter to determine specific agent instance
                issue = {
                    "id": issue_id,
                    "title": story["title"],
                    "description": task,
                    "priority": story.get("priority", "medium")
                }
                
                agent_instance = self.issue_router.route_issue(issue)
                
                # Fallback to legacy naming if routing fails
                if not agent_instance:
                    agent_instance = f"{agent_type}_spirit_1"
                    logger.warning(f"Routing failed, using fallback: {agent_instance}")
                
                if blockers:
                    print(f"   ⏳ {agent_instance}: Waiting for {', '.join(blockers)}...")
                    logger.info(f"Task {issue_id} blocked by: {', '.join(blockers)}")
                else:
                    print(f"   ✨ {agent_instance}: {task}")
                    
                    # Send task assignment message to specific agent instance
                    message = AgentMessage(
                        sender="scrum_master_spirit_1",
                        receiver=agent_instance,
                        workspace=self.workspace,
                        message_type="task_assignment",
                        payload={
                            "story": story["title"],
                            "task": task,
                            "priority": story.get("priority", "medium"),
                            "agent_instance": agent_instance,
                            "issue_id": issue_id,
                        }
                    )
                    self.message_bus.dispatch(message)
                    
                    # Track task assignment on the agent
                    if agent_instance in self.spirits:
                        self.spirits[agent_instance].assign_task(issue_id)
                        self.workload_monitor.log_task_assignment(
                            agent_instance, 
                            issue_id, 
                            story["title"]
                        )
                    
                results.append({
                    "story": story["id"],
                    "agent": agent_type,
                    "agent_instance": agent_instance,
                    "task": task,
                    "status": "in_progress",
                })
        
        # Display final workload state
        print("\n📊 Final Workload State:")
        self.workload_monitor.display_dashboard()
        
        print("\n🔮 Sprint execution initiated!")
        logger.info(f"Sprint execution completed with {len(results)} task assignments")
        
        return {"results": results}
    
    def display_workload_dashboard(self) -> Dict:
        """Display the workload monitoring dashboard.
        
        Returns:
            Dictionary containing workload statistics
        """
        return self.workload_monitor.display_dashboard()
    
    def display_agent_workload(self, agent_identifier: str) -> Dict:
        """Display workload for a specific agent.
        
        Args:
            agent_identifier: Identifier of the agent
            
        Returns:
            Dictionary containing agent workload details
        """
        return self.workload_monitor.display_agent_workload(agent_identifier)
    
    def display_role_summary(self, role: str) -> Dict:
        """Display workload summary for a specific role.
        
        Args:
            role: Role type (e.g., 'frontend', 'backend')
            
        Returns:
            Dictionary containing role workload summary
        """
        return self.workload_monitor.display_role_summary(role)
    
    def banish_spirits(self):
        """Clean up and dismiss all spirits."""
        print("\n⚰️ Banishing spirits back to the void...")
        
        # Display final statistics before banishing
        logger.info("Displaying final workload statistics before banishment")
        self.workload_monitor.display_dashboard()
        
        self.spirits.clear()
        self.message_bus.spirits.clear()
        print("💀 All spirits have returned to eternal rest.")


def main():
    """Demo the Necromancer summoning process."""
    # Example 1: Real-time collaboration tool with default team
    print("="*60)
    print("Example 1: Default Single-Instance Team")
    print("="*60)
    necromancer = Necromancer(workspace="workspace1")
    
    job_description = """
    リアルタイムでホワイトボード共有できるコラボツール。
    WebSocket通信、ユーザー認証、描画データの永続化が必要。
    """
    
    team_config = necromancer.summon_team(job_description)
    necromancer.execute_sprint()
    necromancer.banish_spirits()
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: IoT Dashboard with multiple agent instances
    print("="*60)
    print("Example 2: Multiple Agent Instances")
    print("="*60)
    necromancer2 = Necromancer(workspace="workspace2")
    
    job_description2 = """
    センサーデータをリアルタイム可視化するダッシュボード。
    時系列データ分析、アラート機能、デバイス管理が必要。
    """
    
    # Define role requests with multiple instances
    role_requests = [
        RoleRequest(name="database", skills=["schema_design", "migrations"], count=1),
        RoleRequest(name="backend", skills=["api_development", "business_logic"], count=2),
        RoleRequest(name="frontend", skills=["ui_development", "ux"], count=2),
        RoleRequest(name="qa", skills=["testing", "quality_assurance"], count=1),
        RoleRequest(name="devops", skills=["infrastructure", "deployment"], count=1),
    ]
    
    team_config2 = necromancer2.summon_team(job_description2, role_requests)
    print(f"\n👻 Summoned {len(necromancer2.spirits)} spirit instances:")
    for spirit_id in necromancer2.spirits.keys():
        print(f"   - {spirit_id}")
    
    necromancer2.execute_sprint()
    necromancer2.banish_spirits()


if __name__ == "__main__":
    main()

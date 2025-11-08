"""The Necromancer - master orchestrator that summons and coordinates all spirits."""

from typing import Dict, List
from framework.agents import (
    ArchitectSpirit,
    ScrumMasterSpirit,
    FrontendSpirit,
    BackendSpirit,
    DatabaseSpirit,
    QASpirit,
    DevOpsSpirit,
)
from framework.communication.protocol import AgentMessage
from framework.communication.message_bus import MessageBus


class Necromancer:
    """The master summoner who orchestrates the entire development ritual."""
    
    def __init__(self, workspace: str = "workspace1"):
        self.workspace = workspace
        self.message_bus = MessageBus()
        self.spirits = {}
        self.architecture = None
        self.sprint = None
        
    def summon_team(self, job_description: str) -> Dict:
        """Main entry point: summon a complete development team."""
        print("🧙 Necromancer is analyzing the Job Description...")
        print(f"📜 Job: {job_description[:100]}...")
        
        # Phase 1: Summon Architect
        print("\n👻 Summoning Architect Ghost from the crypt...")
        architect = ArchitectSpirit(
            role="architect",
            skills=["system_design", "api_design"],
            workspace=self.workspace
        )
        self.spirits["architect"] = architect
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
            workspace=self.workspace
        )
        self.spirits["scrum_master"] = scrum_master
        self.message_bus.register(scrum_master)
        
        # Scrum Master decomposes job into stories
        stories = scrum_master.decompose_job(job_description, self.architecture)
        print(f"📋 {scrum_master.chant(f'Created {len(stories)} user stories')}")
        
        # Create sprint
        self.sprint = scrum_master.create_sprint(sprint_number=1)
        print(f"🕷️ {self.sprint['chant']}")
        
        # Phase 3: Summon development spirits
        print("\n💀 Raising the development spirits...")
        
        # Database Spirit
        database = DatabaseSpirit(
            role="database",
            skills=["schema_design", "migrations"],
            workspace=self.workspace
        )
        self.spirits["database"] = database
        self.message_bus.register(database)
        print(f"   {database.weave_schema()}")
        
        # Backend Spirit
        backend = BackendSpirit(
            role="backend",
            skills=["api_development", "business_logic"],
            workspace=self.workspace
        )
        self.spirits["backend"] = backend
        self.message_bus.register(backend)
        print(f"   {backend.forge_api()}")
        
        # Frontend Spirit
        frontend = FrontendSpirit(
            role="frontend",
            skills=["ui_development", "ux"],
            workspace=self.workspace
        )
        self.spirits["frontend"] = frontend
        self.message_bus.register(frontend)
        print(f"   {frontend.summon_ui()}")
        
        # QA Spirit
        qa = QASpirit(
            role="qa",
            skills=["testing", "quality_assurance"],
            workspace=self.workspace
        )
        self.spirits["qa"] = qa
        self.message_bus.register(qa)
        test_strategy = qa.create_test_strategy(self.architecture)
        print(f"   {test_strategy['chant']}")
        
        # DevOps Spirit
        devops = DevOpsSpirit(
            role="devops",
            skills=["infrastructure", "deployment"],
            workspace=self.workspace
        )
        self.spirits["devops"] = devops
        self.message_bus.register(devops)
        print(f"   {devops.chant('Preparing the deployment catacombs...')}")
        
        print("\n🕷️ All spirits have been summoned!")
        
        return {
            "team": list(self.spirits.keys()),
            "architecture": self.architecture,
            "sprint": self.sprint,
            "stories": stories,
        }
    
    def execute_sprint(self) -> Dict:
        """Execute the current sprint with spirit coordination."""
        if not self.sprint:
            return {"error": "No sprint created"}
        
        print("\n⚡ Beginning Sprint Execution...")
        scrum_master = self.spirits["scrum_master"]
        
        results = []
        for story in self.sprint["stories"]:
            print(f"\n📖 Story: {story['title']}")
            
            # Assign tasks
            assignments = scrum_master.assign_tasks(story)
            
            for assignment in assignments:
                agent_name = assignment["agent"]
                task = assignment["task"]
                blockers = assignment["blocking"]
                
                if blockers:
                    print(f"   ⏳ {agent_name}: Waiting for {', '.join(blockers)}...")
                else:
                    print(f"   ✨ {agent_name}: {task}")
                    
                    # Send task assignment message
                    message = AgentMessage(
                        sender="scrum_master",
                        receiver=f"{agent_name}_spirit",
                        workspace=self.workspace,
                        message_type="task_assignment",
                        payload={
                            "story": story["title"],
                            "task": task,
                            "priority": story["priority"],
                        }
                    )
                    self.message_bus.dispatch(message)
                    
                results.append({
                    "story": story["id"],
                    "agent": agent_name,
                    "task": task,
                    "status": "in_progress",
                })
        
        print("\n🔮 Sprint execution initiated!")
        return {"results": results}
    
    def banish_spirits(self):
        """Clean up and dismiss all spirits."""
        print("\n⚰️ Banishing spirits back to the void...")
        self.spirits.clear()
        self.message_bus.spirits.clear()
        print("💀 All spirits have returned to eternal rest.")


def main():
    """Demo the Necromancer summoning process."""
    # Example 1: Real-time collaboration tool
    necromancer = Necromancer(workspace="workspace1")
    
    job_description = """
    リアルタイムでホワイトボード共有できるコラボツール。
    WebSocket通信、ユーザー認証、描画データの永続化が必要。
    """
    
    team_config = necromancer.summon_team(job_description)
    necromancer.execute_sprint()
    necromancer.banish_spirits()
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: IoT Dashboard
    necromancer2 = Necromancer(workspace="workspace2")
    
    job_description2 = """
    センサーデータをリアルタイム可視化するダッシュボード。
    時系列データ分析、アラート機能、デバイス管理が必要。
    """
    
    team_config2 = necromancer2.summon_team(job_description2)
    necromancer2.execute_sprint()
    necromancer2.banish_spirits()


if __name__ == "__main__":
    main()

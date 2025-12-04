"""
Demonstration: Multiple AI agents working in parallel using git worktrees.

Each agent gets its own worktree and can work independently without conflicts.
"""

from pathlib import Path
from necrocode.repo_pool.worktree_pool_manager import WorktreePoolManager
import subprocess
import threading
import time
from typing import List


class AIAgent:
    """Simulates an AI agent working on a task."""
    
    def __init__(self, agent_id: str, worktree_path: Path, branch: str):
        self.agent_id = agent_id
        self.worktree_path = worktree_path
        self.branch = branch
    
    def execute_task(self, task_description: str):
        """
        Execute a task in the agent's dedicated worktree.
        This runs completely independently from other agents.
        """
        print(f"[{self.agent_id}] Starting task: {task_description}")
        print(f"[{self.agent_id}] Working in: {self.worktree_path}")
        print(f"[{self.agent_id}] Branch: {self.branch}")
        
        # Simulate AI agent work
        time.sleep(1)  # Simulate thinking
        
        # 1. Create/modify files in worktree
        test_file = self.worktree_path / f"{self.agent_id}_output.txt"
        test_file.write_text(f"Output from {self.agent_id}\nTask: {task_description}\n")
        
        # 2. Git add
        subprocess.run(
            ["git", "add", "."],
            cwd=self.worktree_path,
            check=True
        )
        
        # 3. Git commit
        subprocess.run(
            ["git", "commit", "-m", f"feat({self.agent_id}): {task_description}"],
            cwd=self.worktree_path,
            check=True
        )
        
        print(f"[{self.agent_id}] ✓ Committed changes")
        
        # 4. Push to remote (in real scenario)
        # subprocess.run(
        #     ["git", "push", "origin", self.branch],
        #     cwd=self.worktree_path,
        #     check=True
        # )
        
        print(f"[{self.agent_id}] ✓ Task completed\n")


def run_agent_in_thread(agent: AIAgent, task: str):
    """Run agent task in a separate thread."""
    agent.execute_task(task)


def main():
    print("=== Parallel AI Agents with Git Worktree ===\n")
    
    # Initialize worktree pool
    pool = WorktreePoolManager(
        base_repo_url="https://github.com/user/project.git",
        pool_dir=Path("./tmp_parallel_demo"),
        pool_size=10
    )
    
    # Define tasks for parallel execution
    tasks = [
        ("agent-1", "Implement JWT authentication API"),
        ("agent-2", "Create user login UI component"),
        ("agent-3", "Design database schema for users"),
        ("agent-4", "Write integration tests"),
        ("agent-5", "Update API documentation"),
    ]
    
    print(f"Spawning {len(tasks)} agents to work in parallel...\n")
    
    # Allocate worktrees and create agents
    agents: List[AIAgent] = []
    threads: List[threading.Thread] = []
    
    for agent_id, task_desc in tasks:
        # Allocate dedicated worktree for this agent
        slot = pool.allocate_slot(agent_id)
        
        # Create agent instance
        agent = AIAgent(
            agent_id=agent_id,
            worktree_path=slot.path,
            branch=slot.branch
        )
        agents.append(agent)
        
        # Start agent in separate thread (simulating parallel execution)
        thread = threading.Thread(
            target=run_agent_in_thread,
            args=(agent, task_desc)
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all agents to complete
    for thread in threads:
        thread.join()
    
    print("\n=== All Agents Completed ===")
    print("Each agent worked independently in its own worktree")
    print("No conflicts occurred because each had a separate branch\n")
    
    # Show pool statistics
    stats = pool.get_pool_stats()
    print("=== Pool Statistics ===")
    print(f"Total worktrees created: {stats['total_slots']}")
    print(f"Disk space used: {stats['main_repo_size_mb'] + stats['worktrees_total_size_mb']:.1f} MB")
    print(f"(vs {stats['main_repo_size_mb'] * len(tasks):.1f} MB with separate clones)\n")
    
    # Cleanup
    print("=== Cleanup ===")
    for agent in agents:
        # In real scenario, you'd merge PRs first
        print(f"Cleaning up {agent.agent_id}'s worktree...")
    
    print("\nDemo complete!")


if __name__ == "__main__":
    main()

"""
Real-world scenario: 5 AI agents building a chat application in parallel.

This demonstrates how git worktree enables true parallel development.
"""

from pathlib import Path
from necrocode.repo_pool.worktree_pool_manager import WorktreePoolManager
import concurrent.futures
import subprocess


def agent_task(pool: WorktreePoolManager, task_id: str, task_spec: dict) -> dict:
    """
    Execute a task in an isolated worktree.
    This function can be called by multiple agents simultaneously.
    """
    # Allocate worktree (thread-safe)
    slot = pool.allocate_slot(task_id)
    
    try:
        print(f"[{task_id}] Allocated worktree: {slot.path}")
        print(f"[{task_id}] Working on: {task_spec['description']}")
        
        # Agent works in its own directory
        for file_path, content in task_spec['files'].items():
            full_path = slot.path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        # Commit changes
        subprocess.run(["git", "add", "."], cwd=slot.path, check=True)
        subprocess.run([
            "git", "commit", "-m",
            f"feat({task_spec['component']}): {task_spec['description']}"
        ], cwd=slot.path, check=True)
        
        # Push to remote (creates PR)
        # subprocess.run(["git", "push", "origin", slot.branch], cwd=slot.path)
        
        print(f"[{task_id}] ✓ Completed and committed")
        
        return {
            "task_id": task_id,
            "status": "success",
            "branch": slot.branch,
            "files_created": len(task_spec['files'])
        }
        
    finally:
        # Cleanup (or keep for PR review)
        # pool.release_slot(slot)
        pass


def main():
    print("=== Real-World Parallel Development Scenario ===")
    print("Building a chat application with 5 AI agents\n")
    
    pool = WorktreePoolManager(
        base_repo_url="https://github.com/company/chat-app.git",
        pool_dir=Path("./chat_app_dev"),
        pool_size=10
    )
    
    # Define parallel tasks
    tasks = {
        "auth-backend": {
            "description": "Implement JWT authentication",
            "component": "backend",
            "files": {
                "backend/auth/jwt.py": "# JWT implementation\n",
                "backend/auth/middleware.py": "# Auth middleware\n",
                "tests/test_auth.py": "# Auth tests\n"
            }
        },
        "user-ui": {
            "description": "Create user login interface",
            "component": "frontend",
            "files": {
                "frontend/components/Login.tsx": "// Login component\n",
                "frontend/components/Register.tsx": "// Register component\n",
                "frontend/styles/auth.css": "/* Auth styles */\n"
            }
        },
        "websocket": {
            "description": "Setup WebSocket server",
            "component": "backend",
            "files": {
                "backend/websocket/server.py": "# WebSocket server\n",
                "backend/websocket/handlers.py": "# Message handlers\n"
            }
        },
        "chat-ui": {
            "description": "Build chat interface",
            "component": "frontend",
            "files": {
                "frontend/components/ChatRoom.tsx": "// Chat room\n",
                "frontend/components/MessageList.tsx": "// Message list\n"
            }
        },
        "database": {
            "description": "Design database schema",
            "component": "database",
            "files": {
                "database/models/user.py": "# User model\n",
                "database/models/message.py": "# Message model\n",
                "database/migrations/001_initial.sql": "-- Initial schema\n"
            }
        }
    }
    
    print(f"Executing {len(tasks)} tasks in parallel...\n")
    
    # Execute all tasks in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(agent_task, pool, task_id, spec): task_id
            for task_id, spec in tasks.items()
        }
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            task_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"\n✓ {task_id} finished successfully")
            except Exception as e:
                print(f"\n✗ {task_id} failed: {e}")
    
    print("\n=== Execution Summary ===")
    print(f"Total tasks: {len(tasks)}")
    print(f"Successful: {len([r for r in results if r['status'] == 'success'])}")
    print(f"Total files created: {sum(r['files_created'] for r in results)}")
    
    print("\n=== Created Branches (Ready for PR) ===")
    for result in results:
        print(f"  - {result['branch']}")
    
    stats = pool.get_pool_stats()
    print(f"\n=== Resource Usage ===")
    print(f"Disk space: {stats['main_repo_size_mb'] + stats['worktrees_total_size_mb']:.1f} MB")
    print(f"Savings vs clones: {(stats['main_repo_size_mb'] * len(tasks)) - (stats['main_repo_size_mb'] + stats['worktrees_total_size_mb']):.1f} MB")
    
    print("\n✓ All agents completed their work in parallel!")
    print("Each branch is ready for code review and PR merge.")


if __name__ == "__main__":
    main()

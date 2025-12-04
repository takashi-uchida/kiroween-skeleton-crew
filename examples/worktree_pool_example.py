"""
Example: Using WorktreePoolManager for parallel agent execution.

Demonstrates how git worktree simplifies parallel task execution.
"""

from pathlib import Path
from necrocode.repo_pool.worktree_pool_manager import WorktreePoolManager
import time


def main():
    # Initialize pool
    pool = WorktreePoolManager(
        base_repo_url="https://github.com/user/project.git",
        pool_dir=Path("./tmp_worktree_pool"),
        pool_size=5
    )
    
    print("=== Worktree Pool Manager Demo ===\n")
    
    # Simulate parallel task execution
    tasks = ["auth-api", "user-ui", "database-schema", "tests", "docs"]
    slots = []
    
    print("Allocating slots for parallel execution...")
    start = time.time()
    
    for task_id in tasks:
        slot = pool.allocate_slot(task_id)
        slots.append(slot)
        print(f"✓ Allocated {slot.slot_id} for task '{task_id}'")
        print(f"  Path: {slot.path}")
        print(f"  Branch: {slot.branch}\n")
    
    elapsed = time.time() - start
    print(f"Allocated {len(slots)} slots in {elapsed:.2f}s")
    print(f"(Traditional clone would take ~{len(slots) * 15}s)\n")
    
    # Show pool statistics
    stats = pool.get_pool_stats()
    print("=== Pool Statistics ===")
    print(f"Total slots: {stats['total_slots']}")
    print(f"Allocated: {stats['allocated_slots']}")
    print(f"Available capacity: {stats['available_capacity']}")
    print(f"Main repo size: {stats['main_repo_size_mb']:.1f} MB")
    print(f"Worktrees size: {stats['worktrees_total_size_mb']:.1f} MB")
    print(f"Total size: {stats['main_repo_size_mb'] + stats['worktrees_total_size_mb']:.1f} MB")
    print(f"(Traditional clone pool: ~{stats['main_repo_size_mb'] * len(slots):.1f} MB)\n")
    
    # Simulate task execution
    print("=== Simulating Task Execution ===")
    for slot in slots:
        print(f"Agent working in {slot.slot_id} on branch {slot.branch}...")
        # Agent would:
        # 1. cd to slot.path
        # 2. Make code changes
        # 3. git commit
        # 4. git push origin slot.branch
        # 5. Create PR via GitHub API
    
    print("\n=== Cleanup ===")
    for slot in slots:
        pool.release_slot(slot)
        print(f"✓ Released {slot.slot_id}")
    
    print("\nDone! All slots cleaned up.")


if __name__ == "__main__":
    main()

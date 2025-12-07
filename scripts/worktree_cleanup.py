#!/usr/bin/env python3
"""Git worktree summary & cleanup helper."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and clean git worktrees under the repository."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository root (default: current directory)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON summary instead of a human-readable table"
    )
    parser.add_argument(
        "--prune-stale",
        action="store_true",
        help="Target task worktrees whose branches no longer exist"
    )
    parser.add_argument(
        "--include-active-task",
        action="store_true",
        help="When pruning, also target task worktrees even if their branch still exists"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply removals (default: dry-run showing planned actions)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pass --force to git worktree remove"
    )
    return parser.parse_args()


def load_manager(repo_root: Path):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from necrocode.worktree_manager import WorktreeManager  # pylint: disable=import-error
    return WorktreeManager(repo_root)


def print_table(summary: List[Dict[str, Any]]) -> None:
    header = f"{'PATH':60} {'BRANCH':30} {'CATEGORY':10} {'STALE':5}"
    print(header)
    print("-" * len(header))
    for entry in summary:
        branch = entry.get("branch", "").replace("refs/heads/", "")
        stale = "yes" if (entry.get("branch_missing") or not entry.get("path_exists")) else "no"
        print(
            f"{entry.get('path')[:60]:60} "
            f"{branch[:30]:30} "
            f"{entry.get('category', 'unknown'):10} "
            f"{stale:5}"
        )


def main():
    args = parse_args()
    repo_root = Path(args.repo).expanduser().resolve()
    manager = load_manager(repo_root)

    summary = manager.summarize_worktrees()

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("Worktree summary for", repo_root)
        print_table(summary)

    if not args.prune_stale:
        return

    targets = [
        entry for entry in summary
        if entry.get("is_task_worktree")
        and (
            entry.get("branch_missing")
            or not entry.get("path_exists")
            or args.include_active_task
        )
    ]

    if not targets:
        print("\nNo task worktrees matched the prune criteria.")
        return

    print(f"\nTask worktrees selected for removal: {len(targets)}")
    for entry in targets:
        print(f" - {entry['path']} ({entry.get('branch', 'no-branch')})")

    if not args.apply:
        print("\nDry-run complete. Re-run with --apply to remove them.")
        return

    for entry in targets:
        task_name = Path(entry["path"]).name
        task_id = task_name.removeprefix("task-")
        try:
            manager.remove_worktree(task_id, force=args.force)
            print(f"Removed worktree {entry['path']}")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Failed to remove {entry['path']}: {exc}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Complete Workflow Example

Demonstrates the complete NecroCode workflow from job submission to PR creation.
"""

import time
from pathlib import Path

from necrocode.orchestration.service_manager import ServiceManager
from necrocode.orchestration.job_submitter import JobSubmitter


def main():
    """Run complete workflow example."""
    
    print("\n" + "🎃" * 30)
    print("NecroCode Complete Workflow Example")
    print("🎃" * 30 + "\n")
    
    # Setup
    workspace_root = Path('.')
    config_dir = Path('.necrocode')
    
    # Step 1: Setup services
    print("Step 1: Setting up NecroCode services...")
    print("-" * 60)
    
    manager = ServiceManager(
        workspace_root=workspace_root,
        config_dir=config_dir
    )
    
    manager.setup_all_services()
    
    print("✅ Services configured")
    print(f"   Config directory: {config_dir}")
    print()
    
    # Step 2: Submit a job
    print("Step 2: Submitting a job...")
    print("-" * 60)
    
    submitter = JobSubmitter(
        workspace_root=workspace_root,
        config_dir=config_dir
    )
    
    job_description = """
    Create a REST API for a task management system with the following features:
    
    1. User authentication (JWT-based)
    2. CRUD operations for tasks
    3. Task assignment to users
    4. Task status tracking (TODO, IN_PROGRESS, DONE)
    5. SQLite database
    6. Unit tests for all endpoints
    7. API documentation
    """
    
    job_id = submitter.submit_job(
        description=job_description,
        project_name="task-manager-api",
        repo_url="https://github.com/your-org/task-manager-api.git",
        base_branch="main"
    )
    
    print(f"✅ Job submitted: {job_id}")
    print()
    
    # Step 3: Check job status
    print("Step 3: Checking job status...")
    print("-" * 60)
    
    status = submitter.get_job_status(job_id)
    
    print(f"Project: {status['project_name']}")
    print(f"Status: {status['status']}")
    print(f"Spec: {status.get('spec_name', 'N/A')}")
    print(f"\nTasks created: {len(status.get('tasks', []))}")
    
    for task in status.get('tasks', []):
        print(f"  - Task {task['id']}: {task['title']}")
    
    print()
    
    # Step 4: Instructions for starting services
    print("Step 4: Start services to process the job")
    print("-" * 60)
    print()
    print("To start all services and process the job, run:")
    print()
    print("  # In terminal 1 (Dispatcher)")
    print("  python -m necrocode.dispatcher.main --config .necrocode/dispatcher.json")
    print()
    print("  # In terminal 2 (Review PR Service)")
    print("  python -m necrocode.review_pr_service.main --config .necrocode/review_pr_service.json")
    print()
    print("Or use the CLI:")
    print()
    print("  python necrocode_cli.py start --detached")
    print()
    
    # Step 5: Monitor progress
    print("Step 5: Monitor progress")
    print("-" * 60)
    print()
    print("Check job status:")
    print(f"  python necrocode_cli.py job status {job_id}")
    print()
    print("View logs:")
    print("  python necrocode_cli.py logs --follow")
    print()
    print("Check service status:")
    print("  python necrocode_cli.py status")
    print()
    
    # Summary
    print("\n" + "=" * 60)
    print("Workflow Summary")
    print("=" * 60)
    print()
    print("1. ✅ Services configured")
    print(f"2. ✅ Job submitted: {job_id}")
    print(f"3. ✅ {len(status.get('tasks', []))} tasks created")
    print("4. ⏳ Waiting for services to process tasks")
    print("5. ⏳ PRs will be created automatically")
    print()
    print("Next steps:")
    print("  - Start services: python necrocode_cli.py start")
    print(f"  - Monitor job: python necrocode_cli.py job status {job_id}")
    print("  - Review PRs on GitHub when completed")
    print()
    print("🎃" * 30 + "\n")


if __name__ == '__main__':
    main()

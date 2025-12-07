#!/usr/bin/env python3
"""
NecroCode CLI - Unified command-line interface for NecroCode system

Provides commands to manage and orchestrate all NecroCode services:
- Task Registry
- Repo Pool Manager
- Dispatcher
- Agent Runner
- Review PR Service
- Artifact Store
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

try:
    from necrocode.orchestration.service_manager import ServiceManager
    from necrocode.orchestration.job_submitter import JobSubmitter
except ImportError as import_error:
    ServiceManager = None
    JobSubmitter = None
    _IMPORT_ERROR = import_error
else:
    _IMPORT_ERROR = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def require_orchestration_dependencies():
    """Raise a helpful error if the orchestration modules failed to import."""
    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            "NecroCode orchestration modules are unavailable. "
            "Verify that the project dependencies are installed."
        ) from _IMPORT_ERROR


def resolve_path(path_str: str) -> Path:
    """Expand and resolve CLI paths consistently."""
    return Path(path_str).expanduser().resolve()


def resolve_workspace_and_config(args):
    """Return resolved workspace and config directories."""
    workspace = resolve_path(args.workspace)
    config_dir = resolve_path(args.config_dir)
    return workspace, config_dir


def setup_services_command(args):
    """Initialize all NecroCode services with default configuration."""
    require_orchestration_dependencies()
    
    print("🎃 Setting up NecroCode services...")
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    manager = ServiceManager(workspace_root=workspace, config_dir=config_dir)
    
    manager.setup_all_services()
    
    print("✅ All services configured successfully!")
    print(f"\nConfiguration files created in: {config_dir}")
    print("\nNext steps:")
    print("  1. Review and customize config files")
    print("  2. Run: necrocode start")


def start_command(args):
    """Start all NecroCode services."""
    require_orchestration_dependencies()
    
    print("🚀 Starting NecroCode services...")
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    manager = ServiceManager(workspace_root=workspace, config_dir=config_dir)
    
    services = args.services.split(',') if args.services else None
    
    manager.start_services(
        services=services,
        detached=args.detached
    )
    
    if args.detached:
        print("✅ Services started in background")
        print("\nCheck status: necrocode status")
        print("View logs: necrocode logs")
    else:
        print("\n⏸️  Press Ctrl+C to stop services...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping services...")
            manager.stop_services()


def stop_command(args):
    """Stop all NecroCode services."""
    require_orchestration_dependencies()
    
    print("🛑 Stopping NecroCode services...")
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    manager = ServiceManager(workspace_root=workspace, config_dir=config_dir)
    
    services = args.services.split(',') if args.services else None
    
    manager.stop_services(services=services, timeout=args.timeout)
    
    print("✅ Services stopped")


def status_command(args):
    """Show status of all NecroCode services."""
    require_orchestration_dependencies()
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    manager = ServiceManager(workspace_root=workspace, config_dir=config_dir)
    
    status = manager.get_status()
    
    if args.output_format == 'json':
        print(json.dumps(status, indent=2))
        return
    
    print("\n" + "=" * 60)
    print("NecroCode Services Status")
    print("=" * 60)
    
    for service_name, service_status in status.items():
        status_icon = "🟢" if service_status['running'] else "🔴"
        print(f"\n{status_icon} {service_name.upper()}")
        print(f"   Status: {'Running' if service_status['running'] else 'Stopped'}")
        
        if service_status.get('pid'):
            print(f"   PID: {service_status['pid']}")
        
        if service_status.get('port'):
            print(f"   Port: {service_status['port']}")
        
        if service_status.get('metrics'):
            for key, value in service_status['metrics'].items():
                print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)


def logs_command(args):
    """Show logs from NecroCode services."""
    require_orchestration_dependencies()
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    manager = ServiceManager(workspace_root=workspace, config_dir=config_dir)
    
    manager.show_logs(
        service=args.service,
        follow=args.follow,
        lines=args.lines
    )


def submit_command(args):
    """Submit a job description to NecroCode."""
    require_orchestration_dependencies()
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    submitter = JobSubmitter(workspace_root=workspace, config_dir=config_dir)
    
    if not args.description and not args.file:
        message = "Provide a job description argument or use --file."
        if hasattr(args, 'parser'):
            args.parser.error(message)
        raise ValueError(message)
    
    # Read job description from file or use argument
    if args.file:
        description_path = resolve_path(args.file)
        with description_path.open('r', encoding='utf-8') as file_handle:
            description = file_handle.read()
        print(f"📝 Submitting job from file: {description_path}")
    else:
        description = args.description
        print(f"📝 Submitting job: {description}")
    
    job_id = submitter.submit_job(
        description=description,
        project_name=args.project,
        repo_url=args.repo,
        base_branch=args.base_branch
    )
    
    print(f"✅ Job submitted: {job_id}")
    print(f"\nTrack progress: necrocode job status {job_id}")


def job_status_command(args):
    """Show status of a submitted job."""
    require_orchestration_dependencies()
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    submitter = JobSubmitter(workspace_root=workspace, config_dir=config_dir)
    
    status = submitter.get_job_status(args.job_id)
    
    if args.output_format == 'json':
        print(json.dumps(status, indent=2))
        return
    
    print("\n" + "=" * 60)
    print(f"Job Status: {args.job_id}")
    print("=" * 60)
    print(f"\nProject: {status['project_name']}")
    print(f"Status: {status['status']}")
    print(f"Created: {status['created_at']}")
    
    if status.get('tasks'):
        print(f"\nTasks: {status['tasks_completed']}/{status['tasks_total']}")
        
        for task in status['tasks'][:10]:  # Show first 10 tasks
            status_icon = {
                'DONE': '✅',
                'RUNNING': '🔄',
                'FAILED': '❌',
                'PENDING': '⏳'
            }.get(task['state'], '⏳')
            
            print(f"  {status_icon} {task['id']}: {task['title']}")
    
    if status.get('prs'):
        print(f"\nPull Requests: {len(status['prs'])}")
        for pr in status['prs']:
            print(f"  #{pr['number']}: {pr['title']} ({pr['state']})")
    
    print("\n" + "=" * 60)


def list_jobs_command(args):
    """List all submitted jobs."""
    require_orchestration_dependencies()
    
    workspace, config_dir = resolve_workspace_and_config(args)
    
    submitter = JobSubmitter(workspace_root=workspace, config_dir=config_dir)
    
    jobs = submitter.list_jobs(limit=args.limit)
    
    if args.output_format == 'json':
        print(json.dumps(jobs, indent=2))
        return
    
    print("\n" + "=" * 60)
    print("Submitted Jobs")
    print("=" * 60)
    
    for job in jobs:
        status_icon = {
            'completed': '✅',
            'running': '🔄',
            'failed': '❌',
            'pending': '⏳'
        }.get(job['status'], '⏳')
        
        print(f"\n{status_icon} {job['job_id']}")
        print(f"   Project: {job['project_name']}")
        print(f"   Status: {job['status']}")
        print(f"   Created: {job['created_at']}")
        print(f"   Tasks: {job.get('tasks_completed', 0)}/{job.get('tasks_total', 0)}")
    
    print("\n" + "=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='NecroCode - AI-powered multi-agent development framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup services
  necrocode setup
  
  # Start all services
  necrocode start
  
  # Submit a job
  necrocode submit "Create a REST API with authentication"
  
  # Check job status
  necrocode job status <job-id>
  
  # View logs
  necrocode logs --follow
  
  # Stop services
  necrocode stop
        """
    )
    
    parser.add_argument(
        '--workspace',
        default='.',
        help='Workspace root directory (default: current directory)'
    )
    
    parser.add_argument(
        '--config-dir',
        default='.necrocode',
        help='Configuration directory (default: .necrocode)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup NecroCode services')
    setup_parser.set_defaults(func=setup_services_command)
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start services')
    start_parser.add_argument(
        '--services',
        help='Comma-separated list of services to start (default: all)'
    )
    start_parser.add_argument(
        '--detached',
        action='store_true',
        help='Run services in background'
    )
    start_parser.set_defaults(func=start_command)
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop services')
    stop_parser.add_argument(
        '--services',
        help='Comma-separated list of services to stop (default: all)'
    )
    stop_parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout for graceful shutdown (default: 30s)'
    )
    stop_parser.set_defaults(func=stop_command)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show service status')
    status_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        dest='output_format',
        help='Output format for service status (default: table)'
    )
    status_parser.set_defaults(func=status_command)
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show service logs')
    logs_parser.add_argument('--service', help='Specific service to show logs for')
    logs_parser.add_argument('--follow', '-f', action='store_true', help='Follow log output')
    logs_parser.add_argument('--lines', '-n', type=int, default=100, help='Number of lines to show')
    logs_parser.set_defaults(func=logs_command)
    
    # Submit command
    submit_parser = subparsers.add_parser('submit', help='Submit a job')
    submit_parser.add_argument('description', nargs='?', help='Job description')
    submit_parser.add_argument('--file', '-f', help='Read job description from file')
    submit_parser.add_argument('--project', '-p', required=True, help='Project name')
    submit_parser.add_argument('--repo', '-r', help='Repository URL')
    submit_parser.add_argument('--base-branch', default='main', help='Base branch (default: main)')
    submit_parser.set_defaults(func=submit_command, parser=submit_parser)
    
    # Job commands
    job_parser = subparsers.add_parser('job', help='Job management')
    job_subparsers = job_parser.add_subparsers(dest='job_command')
    job_subparsers.required = True
    
    # Job status
    job_status_parser = job_subparsers.add_parser('status', help='Show job status')
    job_status_parser.add_argument('job_id', help='Job ID')
    job_status_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        dest='output_format',
        help='Output format for job status (default: table)'
    )
    job_status_parser.set_defaults(func=job_status_command)
    
    # Job list
    job_list_parser = job_subparsers.add_parser('list', help='List jobs')
    job_list_parser.add_argument('--limit', type=int, default=20, help='Number of jobs to show')
    job_list_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        dest='output_format',
        help='Output format for job listing (default: table)'
    )
    job_list_parser.set_defaults(func=list_jobs_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

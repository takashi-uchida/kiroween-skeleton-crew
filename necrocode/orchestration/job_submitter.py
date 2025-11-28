"""
Job Submitter - Submits jobs to NecroCode system

Handles:
- Job description parsing
- Task breakdown via LLM
- Task submission to Task Registry
- Job tracking
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState

logger = logging.getLogger(__name__)


class JobSubmitter:
    """
    Submits jobs to NecroCode system.
    
    Workflow:
    1. Parse job description
    2. Generate task breakdown (via LLM)
    3. Create spec in Task Registry
    4. Submit tasks
    5. Track job progress
    """
    
    def __init__(
        self,
        workspace_root: Path = Path('.'),
        config_dir: Path = Path('.necrocode')
    ):
        """
        Initialize Job Submitter.
        
        Args:
            workspace_root: Root directory of workspace
            config_dir: Configuration directory
        """
        self.workspace_root = workspace_root
        self.config_dir = workspace_root / config_dir
        
        # Load Task Registry config
        task_registry_config = self._load_task_registry_config()
        registry_dir = task_registry_config.get('registry_dir')
        
        self.task_registry = TaskRegistry(registry_dir=registry_dir)
        
        # Jobs directory
        self.jobs_dir = self.config_dir / 'jobs'
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"JobSubmitter initialized: jobs_dir={self.jobs_dir}")
    
    def _load_task_registry_config(self) -> Dict[str, Any]:
        """Load Task Registry configuration."""
        config_file = self.config_dir / 'task_registry.json'
        
        if not config_file.exists():
            # Use default
            return {
                'registry_dir': str(self.config_dir / 'data' / 'task_registry')
            }
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def submit_job(
        self,
        description: str,
        project_name: str,
        repo_url: Optional[str] = None,
        base_branch: str = 'main'
    ) -> str:
        """
        Submit a job to NecroCode.
        
        Args:
            description: Job description (natural language)
            project_name: Project name
            repo_url: Repository URL (optional)
            base_branch: Base branch for PRs
            
        Returns:
            Job ID
        """
        logger.info(f"Submitting job: {project_name}")
        
        # Generate job ID
        job_id = self._generate_job_id()
        
        # Create job record
        job_record = {
            'job_id': job_id,
            'project_name': project_name,
            'description': description,
            'repo_url': repo_url,
            'base_branch': base_branch,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'tasks': []
        }
        
        # Save job record
        self._save_job_record(job_id, job_record)
        
        # Generate task breakdown
        logger.info("Generating task breakdown...")
        tasks = self._generate_task_breakdown(description, project_name)
        
        # Create spec in Task Registry
        spec_name = f"{project_name}-{job_id[:8]}"
        self._create_spec(spec_name, project_name, description, tasks, repo_url, base_branch)
        
        # Update job record
        job_record['spec_name'] = spec_name
        job_record['tasks'] = [task.id for task in tasks]
        job_record['status'] = 'running'
        self._save_job_record(job_id, job_record)
        
        logger.info(f"Job submitted: {job_id} (spec: {spec_name}, tasks: {len(tasks)})")
        
        return job_id
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        return f"job-{uuid.uuid4().hex[:12]}"
    
    def _generate_task_breakdown(
        self,
        description: str,
        project_name: str
    ) -> List[Task]:
        """
        Generate task breakdown from job description.
        
        This is a simplified implementation. In production, this would:
        1. Use LLM to analyze job description
        2. Generate detailed task breakdown
        3. Identify dependencies
        4. Assign skills
        
        Args:
            description: Job description
            project_name: Project name
            
        Returns:
            List of tasks
        """
        logger.info("Generating task breakdown (using template)")
        
        # Template implementation - replace with LLM-based analysis
        tasks = [
            Task(
                id="1",
                title="Project setup and structure",
                description="Initialize project structure with necessary directories and configuration files",
                state=TaskState.READY,
                dependencies=[],
                required_skill="setup",
                priority=10,
                metadata={
                    'project_name': project_name,
                    'generated_from': 'job_description'
                }
            ),
            Task(
                id="2",
                title="Core implementation",
                description=f"Implement core functionality: {description}",
                state=TaskState.BLOCKED,
                dependencies=["1"],
                required_skill="backend",
                priority=5,
                metadata={
                    'project_name': project_name,
                    'generated_from': 'job_description'
                }
            ),
            Task(
                id="3",
                title="Testing and documentation",
                description="Add tests and documentation for implemented features",
                state=TaskState.BLOCKED,
                dependencies=["2"],
                required_skill="qa",
                priority=3,
                metadata={
                    'project_name': project_name,
                    'generated_from': 'job_description'
                }
            )
        ]
        
        logger.info(f"Generated {len(tasks)} tasks")
        
        return tasks
    
    def _create_spec(
        self,
        spec_name: str,
        project_name: str,
        description: str,
        tasks: List[Task],
        repo_url: Optional[str],
        base_branch: str
    ) -> None:
        """Create spec in Task Registry."""
        logger.info(f"Creating spec: {spec_name}")
        
        # Create taskset
        from necrocode.task_registry.kiro_sync import TaskDefinition
        
        # Convert tasks to TaskDefinitions (simplified format for kiro_sync)
        task_definitions = []
        for task in tasks:
            # Embed additional info in description
            desc = task.description
            if task.required_skill:
                desc += f"\n\nRequired Skill: {task.required_skill}"
            if task.priority:
                desc += f"\nPriority: {task.priority}"
            
            task_def = TaskDefinition(
                id=task.id,
                title=task.title,
                description=desc,
                is_optional=False,
                is_completed=False,
                dependencies=task.dependencies
            )
            task_definitions.append(task_def)
        
        # Create metadata
        metadata = {
            'repo_url': repo_url,
            'base_branch': base_branch,
            'created_by': 'job_submitter',
            'project_name': project_name,
            'description': description
        }
        
        # Save to Task Registry
        taskset = self.task_registry.create_taskset(
            spec_name=spec_name,
            tasks=task_definitions,
            metadata=metadata
        )
        
        logger.info(f"Spec created: {spec_name} with {len(tasks)} tasks")
    
    def _save_job_record(self, job_id: str, job_record: Dict[str, Any]) -> None:
        """Save job record to disk."""
        job_file = self.jobs_dir / f'{job_id}.json'
        
        with open(job_file, 'w') as f:
            json.dump(job_record, f, indent=2)
        
        logger.debug(f"Job record saved: {job_file}")
    
    def _load_job_record(self, job_id: str) -> Dict[str, Any]:
        """Load job record from disk."""
        job_file = self.jobs_dir / f'{job_id}.json'
        
        if not job_file.exists():
            raise FileNotFoundError(f"Job not found: {job_id}")
        
        with open(job_file, 'r') as f:
            return json.load(f)
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a submitted job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status including task progress
        """
        logger.info(f"Getting job status: {job_id}")
        
        # Load job record
        job_record = self._load_job_record(job_id)
        
        spec_name = job_record.get('spec_name')
        if not spec_name:
            return job_record
        
        # Get task states from Task Registry
        try:
            taskset = self.task_registry.get_taskset(spec_name)
            
            tasks_info = []
            tasks_completed = 0
            tasks_failed = 0
            
            # taskset.tasks is a list, not a dict
            for task in taskset.tasks:
                tasks_info.append({
                    'id': task.id,
                    'title': task.title,
                    'state': task.state.value
                })
                
                if task.state == TaskState.DONE:
                    tasks_completed += 1
                elif task.state == TaskState.FAILED:
                    tasks_failed += 1
            
            # Update status
            if tasks_completed == len(taskset.tasks):
                job_record['status'] = 'completed'
            elif tasks_failed > 0:
                job_record['status'] = 'failed'
            else:
                job_record['status'] = 'running'
            
            job_record['tasks'] = tasks_info
            job_record['tasks_total'] = len(taskset.tasks)
            job_record['tasks_completed'] = tasks_completed
            job_record['tasks_failed'] = tasks_failed
            
        except Exception as e:
            logger.warning(f"Failed to get task states: {e}")
        
        return job_record
    
    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List submitted jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job records
        """
        logger.info(f"Listing jobs (limit: {limit})")
        
        jobs = []
        
        # List job files
        job_files = sorted(
            self.jobs_dir.glob('job-*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for job_file in job_files[:limit]:
            try:
                with open(job_file, 'r') as f:
                    job_record = json.load(f)
                
                # Get current status
                job_id = job_record['job_id']
                current_status = self.get_job_status(job_id)
                
                jobs.append(current_status)
                
            except Exception as e:
                logger.warning(f"Failed to load job {job_file}: {e}")
        
        return jobs

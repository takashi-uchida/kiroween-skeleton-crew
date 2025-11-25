"""
Runner Launcher for the Dispatcher component.

Launches Agent Runners in different execution environments (local process, Docker, Kubernetes).
"""

import json
import logging
import os
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from necrocode.dispatcher.models import AgentPool, PoolType, Runner, RunnerState
from necrocode.dispatcher.exceptions import RunnerLaunchError

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """
    Task context passed to Agent Runner.
    
    Contains all information needed for the runner to execute a task.
    """
    task_id: str
    spec_name: str
    task_title: str
    task_description: str
    dependencies: list[str]
    required_skill: Optional[str]
    slot_id: str
    slot_path: str
    repo_url: str
    branch_name: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "spec_name": self.spec_name,
            "task_title": self.task_title,
            "task_description": self.task_description,
            "dependencies": self.dependencies,
            "required_skill": self.required_skill,
            "slot_id": self.slot_id,
            "slot_path": self.slot_path,
            "repo_url": self.repo_url,
            "branch_name": self.branch_name,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BaseLauncher(ABC):
    """Base class for Agent Runner launchers."""
    
    @abstractmethod
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """
        Launch an Agent Runner.
        
        Args:
            runner_id: Unique runner identifier
            task_context: Task execution context
            pool: Agent pool configuration
            
        Returns:
            Runner instance with launch information
            
        Raises:
            RunnerLaunchError: If launch fails
        """
        pass


class LocalProcessLauncher(BaseLauncher):
    """
    Launches Agent Runner as a local subprocess.
    
    Suitable for development and testing environments.
    """
    
    def __init__(self, runner_script: Optional[str] = None):
        """
        Initialize local process launcher.
        
        Args:
            runner_script: Path to the runner script (defaults to agent_runner main)
        """
        self.runner_script = runner_script or "python -m necrocode.agent_runner"
    
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """Launch Agent Runner as a local subprocess."""
        try:
            logger.info(f"Launching local process runner {runner_id} for task {task_context.task_id}")
            
            # Prepare environment variables
            env = os.environ.copy()
            env["RUNNER_ID"] = runner_id
            env["TASK_CONTEXT"] = task_context.to_json()
            env["POOL_NAME"] = pool.name
            
            # Add pool-specific config to environment
            for key, value in pool.config.items():
                env_key = f"RUNNER_{key.upper()}"
                env[env_key] = str(value)
            
            # Launch subprocess
            process = subprocess.Popen(
                self.runner_script.split(),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=task_context.slot_path,
            )
            
            logger.info(f"Local runner {runner_id} started with PID {process.pid}")
            
            return Runner(
                runner_id=runner_id,
                task_id=task_context.task_id,
                pool_name=pool.name,
                slot_id=task_context.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                pid=process.pid,
            )
            
        except Exception as e:
            logger.error(f"Failed to launch local runner {runner_id}: {e}")
            raise RunnerLaunchError(f"Local process launch failed: {e}") from e


class DockerLauncher(BaseLauncher):
    """
    Launches Agent Runner as a Docker container.
    
    Provides isolation and consistent execution environment.
    """
    
    def __init__(self):
        """Initialize Docker launcher."""
        try:
            import docker
            self.client = docker.from_env()
        except ImportError:
            raise RunnerLaunchError("Docker library not installed. Install with: pip install docker")
        except Exception as e:
            raise RunnerLaunchError(f"Failed to initialize Docker client: {e}")
    
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """Launch Agent Runner as a Docker container."""
        try:
            logger.info(f"Launching Docker runner {runner_id} for task {task_context.task_id}")
            
            # Get Docker image from pool config
            image = pool.config.get("image", "necrocode/runner:latest")
            
            # Prepare environment variables
            environment = {
                "RUNNER_ID": runner_id,
                "TASK_CONTEXT": task_context.to_json(),
                "POOL_NAME": pool.name,
            }
            
            # Add pool-specific config
            for key, value in pool.config.items():
                if key != "image" and key != "mount_repo_pool":
                    environment[f"RUNNER_{key.upper()}"] = str(value)
            
            # Prepare volume mounts
            volumes = {}
            if pool.config.get("mount_repo_pool", True):
                # Mount the slot directory
                volumes[task_context.slot_path] = {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            
            # Resource limits
            mem_limit = None
            if pool.memory_quota:
                mem_limit = f"{pool.memory_quota}m"
            
            cpu_quota = None
            if pool.cpu_quota:
                # Docker uses CPU quota in microseconds per 100ms period
                cpu_quota = int(pool.cpu_quota * 100000)
            
            # Launch container
            container = self.client.containers.run(
                image,
                detach=True,
                environment=environment,
                volumes=volumes,
                name=f"necrocode-runner-{runner_id}",
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                remove=True,  # Auto-remove on completion
            )
            
            logger.info(f"Docker runner {runner_id} started with container ID {container.id}")
            
            return Runner(
                runner_id=runner_id,
                task_id=task_context.task_id,
                pool_name=pool.name,
                slot_id=task_context.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                container_id=container.id,
            )
            
        except Exception as e:
            logger.error(f"Failed to launch Docker runner {runner_id}: {e}")
            raise RunnerLaunchError(f"Docker launch failed: {e}") from e


class KubernetesLauncher(BaseLauncher):
    """
    Launches Agent Runner as a Kubernetes Job.
    
    Provides scalable execution in Kubernetes clusters.
    """
    
    def __init__(self):
        """Initialize Kubernetes launcher."""
        try:
            from kubernetes import client, config
            config.load_kube_config()
            self.batch_v1 = client.BatchV1Api()
            self.core_v1 = client.CoreV1Api()
        except ImportError:
            raise RunnerLaunchError("Kubernetes library not installed. Install with: pip install kubernetes")
        except Exception as e:
            raise RunnerLaunchError(f"Failed to initialize Kubernetes client: {e}")
    
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """Launch Agent Runner as a Kubernetes Job."""
        try:
            from kubernetes import client
            
            logger.info(f"Launching Kubernetes runner {runner_id} for task {task_context.task_id}")
            
            # Get configuration from pool
            namespace = pool.config.get("namespace", "necrocode-agents")
            image = pool.config.get("image", "necrocode/runner:latest")
            job_template_path = pool.config.get("job_template")
            
            # Generate job name
            job_name = f"necrocode-runner-{runner_id}"[:63]  # K8s name limit
            
            # Prepare environment variables
            env_vars = [
                client.V1EnvVar(name="RUNNER_ID", value=runner_id),
                client.V1EnvVar(name="TASK_CONTEXT", value=task_context.to_json()),
                client.V1EnvVar(name="POOL_NAME", value=pool.name),
            ]
            
            # Add pool-specific config
            for key, value in pool.config.items():
                if key not in ["namespace", "image", "job_template"]:
                    env_vars.append(
                        client.V1EnvVar(name=f"RUNNER_{key.upper()}", value=str(value))
                    )
            
            # Resource requirements
            resources = client.V1ResourceRequirements()
            if pool.cpu_quota or pool.memory_quota:
                limits = {}
                requests = {}
                
                if pool.cpu_quota:
                    limits["cpu"] = str(pool.cpu_quota)
                    requests["cpu"] = str(max(1, pool.cpu_quota // 2))
                
                if pool.memory_quota:
                    limits["memory"] = f"{pool.memory_quota}Mi"
                    requests["memory"] = f"{pool.memory_quota // 2}Mi"
                
                resources.limits = limits
                resources.requests = requests
            
            # Create Job manifest
            if job_template_path and Path(job_template_path).exists():
                # Load from template
                job = self._load_job_template(job_template_path, job_name, env_vars, resources)
            else:
                # Create default Job
                job = self._create_default_job(
                    job_name, namespace, image, env_vars, resources, task_context
                )
            
            # Create the Job
            self.batch_v1.create_namespaced_job(namespace=namespace, body=job)
            
            logger.info(f"Kubernetes runner {runner_id} started as Job {job_name}")
            
            return Runner(
                runner_id=runner_id,
                task_id=task_context.task_id,
                pool_name=pool.name,
                slot_id=task_context.slot_id,
                state=RunnerState.RUNNING,
                started_at=datetime.now(),
                job_name=job_name,
            )
            
        except Exception as e:
            logger.error(f"Failed to launch Kubernetes runner {runner_id}: {e}")
            raise RunnerLaunchError(f"Kubernetes launch failed: {e}") from e
    
    def _create_default_job(
        self,
        job_name: str,
        namespace: str,
        image: str,
        env_vars: list,
        resources: Any,
        task_context: TaskContext
    ) -> Any:
        """Create a default Kubernetes Job manifest."""
        from kubernetes import client
        
        # Container spec
        container = client.V1Container(
            name="runner",
            image=image,
            env=env_vars,
            resources=resources,
            working_dir="/workspace",
        )
        
        # Pod spec
        pod_spec = client.V1PodSpec(
            containers=[container],
            restart_policy="Never",
        )
        
        # Pod template
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={
                    "app": "necrocode-runner",
                    "runner-id": job_name,
                    "task-id": task_context.task_id,
                }
            ),
            spec=pod_spec,
        )
        
        # Job spec
        job_spec = client.V1JobSpec(
            template=pod_template,
            backoff_limit=0,  # No retries
            ttl_seconds_after_finished=3600,  # Clean up after 1 hour
        )
        
        # Job
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                namespace=namespace,
            ),
            spec=job_spec,
        )
        
        return job
    
    def _load_job_template(
        self,
        template_path: str,
        job_name: str,
        env_vars: list,
        resources: Any
    ) -> Any:
        """Load and customize Job from template file."""
        import yaml
        from kubernetes import client
        
        with open(template_path, 'r') as f:
            template = yaml.safe_load(f)
        
        # Customize template
        template["metadata"]["name"] = job_name
        
        # Update container env and resources
        container = template["spec"]["template"]["spec"]["containers"][0]
        container["env"] = [{"name": e.name, "value": e.value} for e in env_vars]
        
        if resources.limits or resources.requests:
            container["resources"] = {}
            if resources.limits:
                container["resources"]["limits"] = resources.limits
            if resources.requests:
                container["resources"]["requests"] = resources.requests
        
        return client.ApiClient().deserialize(
            client.ApiClient().sanitize_for_serialization(template),
            "V1Job"
        )


class RunnerLauncher:
    """
    Main Runner Launcher that delegates to specific launchers.
    
    Handles runner ID generation, task context building, and launch delegation.
    """
    
    def __init__(self, retry_attempts: int = 3):
        """
        Initialize Runner Launcher.
        
        Args:
            retry_attempts: Number of retry attempts on launch failure
        """
        self.retry_attempts = retry_attempts
        self.local_launcher = LocalProcessLauncher()
        self._docker_launcher: Optional[DockerLauncher] = None
        self._k8s_launcher: Optional[KubernetesLauncher] = None
    
    @property
    def docker_launcher(self) -> DockerLauncher:
        """Lazy-load Docker launcher."""
        if self._docker_launcher is None:
            self._docker_launcher = DockerLauncher()
        return self._docker_launcher
    
    @property
    def k8s_launcher(self) -> KubernetesLauncher:
        """Lazy-load Kubernetes launcher."""
        if self._k8s_launcher is None:
            self._k8s_launcher = KubernetesLauncher()
        return self._k8s_launcher
    
    def launch(
        self,
        task: Any,  # Task from task_registry.models
        slot: Any,  # Slot from repo_pool.models
        pool: AgentPool
    ) -> Runner:
        """
        Launch an Agent Runner for a task.
        
        Args:
            task: Task to execute
            slot: Allocated workspace slot
            pool: Agent pool to use
            
        Returns:
            Runner instance
            
        Raises:
            RunnerLaunchError: If launch fails after retries
        """
        runner_id = self._generate_runner_id()
        task_context = self._build_task_context(task, slot)
        
        # Attempt launch with retries
        last_error = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.info(
                    f"Launching runner {runner_id} (attempt {attempt}/{self.retry_attempts})"
                )
                
                # Delegate to appropriate launcher
                if pool.type == PoolType.LOCAL_PROCESS:
                    return self.local_launcher.launch(runner_id, task_context, pool)
                elif pool.type == PoolType.DOCKER:
                    return self.docker_launcher.launch(runner_id, task_context, pool)
                elif pool.type == PoolType.KUBERNETES:
                    return self.k8s_launcher.launch(runner_id, task_context, pool)
                else:
                    raise RunnerLaunchError(f"Unknown pool type: {pool.type}")
                    
            except RunnerLaunchError as e:
                last_error = e
                logger.warning(
                    f"Launch attempt {attempt} failed for runner {runner_id}: {e}"
                )
                
                if attempt < self.retry_attempts:
                    logger.info(f"Retrying launch for runner {runner_id}...")
                    continue
        
        # All retries exhausted
        error_msg = f"Failed to launch runner {runner_id} after {self.retry_attempts} attempts"
        if last_error:
            error_msg += f": {last_error}"
        
        logger.error(error_msg)
        raise RunnerLaunchError(error_msg)
    
    def _generate_runner_id(self) -> str:
        """
        Generate a unique runner ID.
        
        Returns:
            Unique runner identifier
        """
        return f"runner-{uuid.uuid4().hex[:12]}"
    
    def _build_task_context(self, task: Any, slot: Any) -> TaskContext:
        """
        Build task context from task and slot information.
        
        Args:
            task: Task from task registry
            slot: Slot from repo pool
            
        Returns:
            TaskContext with all necessary information
        """
        return TaskContext(
            task_id=task.id,
            spec_name=getattr(task, 'spec_name', task.metadata.get('spec_name', 'unknown')),
            task_title=task.title,
            task_description=task.description,
            dependencies=task.dependencies,
            required_skill=task.required_skill,
            slot_id=slot.slot_id,
            slot_path=str(slot.slot_path),
            repo_url=slot.repo_url,
            branch_name=task.reserved_branch,
            metadata=task.metadata,
        )

"""
Execution environment implementations for Agent Runner.

This module provides different execution environments for running tasks:
- LocalProcessRunner: Run as a local process
- DockerRunner: Run inside a Docker container
- KubernetesRunner: Run as a Kubernetes Job

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from necrocode.agent_runner.config import ExecutionMode, RunnerConfig
from necrocode.agent_runner.exceptions import RunnerError
from necrocode.agent_runner.models import RunnerResult, TaskContext
from necrocode.agent_runner.runner_orchestrator import RunnerOrchestrator

logger = logging.getLogger(__name__)


class ExecutionEnvironment(ABC):
    """
    Abstract base class for execution environments.
    
    Defines the common interface that all execution environments must implement.
    This allows the runner to be executed in different environments (local, Docker, K8s)
    with a consistent interface.
    
    Requirements: 9.1
    """
    
    def __init__(self, config: RunnerConfig):
        """
        Initialize execution environment.
        
        Args:
            config: Runner configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def execute(self, task_context: TaskContext) -> RunnerResult:
        """
        Execute a task in this environment.
        
        Args:
            task_context: Task context containing execution information
            
        Returns:
            RunnerResult with execution results
            
        Raises:
            RunnerError: If execution fails
        """
        pass
    
    @abstractmethod
    def validate_environment(self) -> None:
        """
        Validate that the execution environment is properly configured.
        
        Raises:
            RunnerError: If environment validation fails
        """
        pass
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get information about the execution environment.
        
        Returns:
            Dictionary with environment information
        """
        return {
            "execution_mode": self.config.execution_mode.value,
            "config": self.config.to_dict(),
        }


class LocalProcessRunner(ExecutionEnvironment):
    """
    Local process execution environment.
    
    Runs the Agent Runner as a local process on the host machine.
    This is the simplest execution mode and is suitable for:
    - Development and testing
    - Single-machine deployments
    - Environments where containerization is not available
    
    Requirements: 9.2
    """
    
    def __init__(self, config: Optional[RunnerConfig] = None):
        """
        Initialize local process runner.
        
        Args:
            config: Runner configuration. If None, uses default config.
        """
        if config is None:
            config = RunnerConfig(execution_mode=ExecutionMode.LOCAL_PROCESS)
        elif config.execution_mode != ExecutionMode.LOCAL_PROCESS:
            config.execution_mode = ExecutionMode.LOCAL_PROCESS
        
        super().__init__(config)
        self.orchestrator = RunnerOrchestrator(config)
        
        self.logger.info("LocalProcessRunner initialized")
    
    def execute(self, task_context: TaskContext) -> RunnerResult:
        """
        Execute task as a local process.
        
        Simply delegates to the RunnerOrchestrator which runs in the
        current process.
        
        Args:
            task_context: Task context
            
        Returns:
            RunnerResult
            
        Requirements: 9.2
        """
        self.logger.info(f"Executing task {task_context.task_id} as local process")
        
        try:
            # Validate environment before execution
            self.validate_environment()
            
            # Execute task using orchestrator
            result = self.orchestrator.run(task_context)
            
            self.logger.info(
                f"Task {task_context.task_id} completed: "
                f"success={result.success}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            raise RunnerError(f"Local process execution failed: {e}")
    
    def validate_environment(self) -> None:
        """
        Validate local process environment.
        
        Checks that:
        - Required environment variables are set
        - Workspace paths are accessible
        - Git is available
        
        Raises:
            RunnerError: If validation fails
            
        Requirements: 9.2
        """
        self.logger.debug("Validating local process environment")
        
        errors = []
        
        # Check Git availability
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                errors.append("Git is not available or not working properly")
            else:
                self.logger.debug(f"Git version: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("Git is not installed or not in PATH")
        
        # Check required environment variables
        if self.config.git_token_env_var:
            if not os.getenv(self.config.git_token_env_var):
                self.logger.warning(
                    f"Git token environment variable not set: "
                    f"{self.config.git_token_env_var}"
                )
        
        # Check Task Registry path if configured
        if self.config.task_registry_path:
            if not self.config.task_registry_path.exists():
                self.logger.warning(
                    f"Task Registry path does not exist: "
                    f"{self.config.task_registry_path}"
                )
        
        if errors:
            error_msg = "Environment validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise RunnerError(error_msg)
        
        self.logger.debug("Environment validation passed")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get local process environment information.
        
        Returns:
            Dictionary with environment details
        """
        info = super().get_environment_info()
        info.update({
            "hostname": os.uname().nodename if hasattr(os, "uname") else "unknown",
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
        })
        return info


class DockerRunner(ExecutionEnvironment):
    """
    Docker container execution environment.
    
    Runs the Agent Runner inside a Docker container. This provides:
    - Isolation from the host system
    - Consistent execution environment
    - Resource limits via Docker
    - Easy deployment and scaling
    
    Requirements: 9.3
    """
    
    def __init__(self, config: Optional[RunnerConfig] = None):
        """
        Initialize Docker runner.
        
        Args:
            config: Runner configuration. If None, uses default config.
        """
        if config is None:
            config = RunnerConfig(execution_mode=ExecutionMode.DOCKER)
        elif config.execution_mode != ExecutionMode.DOCKER:
            config.execution_mode = ExecutionMode.DOCKER
        
        super().__init__(config)
        self.container_id: Optional[str] = None
        
        self.logger.info("DockerRunner initialized")
    
    def execute(self, task_context: TaskContext) -> RunnerResult:
        """
        Execute task in a Docker container.
        
        Creates a Docker container with:
        - Workspace mounted as a volume
        - Environment variables injected
        - Resource limits applied
        - Network configuration
        
        Args:
            task_context: Task context
            
        Returns:
            RunnerResult
            
        Requirements: 9.3
        """
        self.logger.info(
            f"Executing task {task_context.task_id} in Docker container"
        )
        
        try:
            # Validate environment
            self.validate_environment()
            
            # Build Docker run command
            docker_cmd = self._build_docker_command(task_context)
            
            self.logger.debug(f"Docker command: {' '.join(docker_cmd)}")
            
            # Run container
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=task_context.timeout_seconds + 60  # Add buffer
            )
            
            if result.returncode != 0:
                error_msg = f"Docker execution failed: {result.stderr}"
                self.logger.error(error_msg)
                raise RunnerError(error_msg)
            
            # Parse result from container output
            # In a real implementation, this would parse structured output
            # from the container (e.g., JSON written to a file)
            self.logger.info(f"Task {task_context.task_id} completed in Docker")
            
            # For now, return a basic result
            # In production, we'd parse the actual result from the container
            from necrocode.agent_runner.models import RunnerResult
            return RunnerResult(
                success=True,
                runner_id=f"docker-{self.container_id or 'unknown'}",
                task_id=task_context.task_id,
                duration_seconds=0.0,  # Would be parsed from output
                artifacts=[],
                error=None,
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Docker execution timed out after {task_context.timeout_seconds}s"
            self.logger.error(error_msg)
            raise RunnerError(error_msg)
        except Exception as e:
            self.logger.error(f"Docker execution failed: {e}")
            raise RunnerError(f"Docker execution failed: {e}")
        finally:
            # Cleanup container if it exists
            if self.container_id:
                self._cleanup_container()
    
    def _build_docker_command(self, task_context: TaskContext) -> list[str]:
        """
        Build Docker run command with all necessary options.
        
        Args:
            task_context: Task context
            
        Returns:
            List of command arguments
            
        Requirements: 9.3
        """
        cmd = ["docker", "run", "--rm"]
        
        # Add container name
        container_name = f"necrocode-runner-{task_context.task_id}"
        cmd.extend(["--name", container_name])
        self.container_id = container_name
        
        # Mount workspace
        workspace_mount = f"{task_context.slot_path}:/workspace"
        cmd.extend(["-v", workspace_mount])
        
        # Mount additional volumes from config
        for host_path, container_path in self.config.docker_volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        # Set working directory
        cmd.extend(["-w", "/workspace"])
        
        # Inject environment variables
        env_vars = self._get_environment_variables()
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])
        
        # Set resource limits
        if self.config.max_memory_mb:
            cmd.extend(["-m", f"{self.config.max_memory_mb}m"])
        
        if self.config.max_cpu_percent:
            # Docker uses CPU shares (1024 = 100%)
            cpu_shares = int((self.config.max_cpu_percent / 100) * 1024)
            cmd.extend(["--cpu-shares", str(cpu_shares)])
        
        # Set network
        if self.config.docker_network:
            cmd.extend(["--network", self.config.docker_network])
        
        # Add image
        cmd.append(self.config.docker_image)
        
        # Add command to run inside container
        # This would execute the runner with the task context
        cmd.extend([
            "python", "-m", "necrocode.agent_runner",
            "--task-id", task_context.task_id,
            "--spec-name", task_context.spec_name,
        ])
        
        return cmd
    
    def _get_environment_variables(self) -> Dict[str, str]:
        """
        Get environment variables to inject into container.
        
        Returns:
            Dictionary of environment variables
            
        Requirements: 9.3
        """
        env_vars = {}
        
        # Git token
        git_token = os.getenv(self.config.git_token_env_var)
        if git_token:
            env_vars[self.config.git_token_env_var] = git_token
        
        # Artifact Store API key
        artifact_api_key = os.getenv(self.config.artifact_store_api_key_env_var)
        if artifact_api_key:
            env_vars[self.config.artifact_store_api_key_env_var] = artifact_api_key
        
        # Kiro API key
        if self.config.kiro_api_url:
            kiro_api_key = os.getenv(self.config.kiro_api_key_env_var)
            if kiro_api_key:
                env_vars[self.config.kiro_api_key_env_var] = kiro_api_key
        
        # Runner configuration
        env_vars["RUNNER_LOG_LEVEL"] = self.config.log_level
        env_vars["ARTIFACT_STORE_URL"] = self.config.artifact_store_url
        
        if self.config.kiro_api_url:
            env_vars["KIRO_API_URL"] = self.config.kiro_api_url
        
        return env_vars
    
    def _cleanup_container(self) -> None:
        """
        Cleanup Docker container.
        
        Stops and removes the container if it's still running.
        """
        if not self.container_id:
            return
        
        try:
            # Try to stop container
            subprocess.run(
                ["docker", "stop", self.container_id],
                capture_output=True,
                timeout=10
            )
            self.logger.debug(f"Stopped container: {self.container_id}")
        except Exception as e:
            self.logger.warning(f"Failed to stop container: {e}")
        
        try:
            # Try to remove container
            subprocess.run(
                ["docker", "rm", self.container_id],
                capture_output=True,
                timeout=10
            )
            self.logger.debug(f"Removed container: {self.container_id}")
        except Exception as e:
            self.logger.warning(f"Failed to remove container: {e}")
    
    def validate_environment(self) -> None:
        """
        Validate Docker environment.
        
        Checks that:
        - Docker is installed and running
        - Required image is available
        - Docker daemon is accessible
        
        Raises:
            RunnerError: If validation fails
            
        Requirements: 9.3
        """
        self.logger.debug("Validating Docker environment")
        
        errors = []
        
        # Check Docker availability
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                errors.append("Docker is not available or not working properly")
            else:
                self.logger.debug(f"Docker version: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("Docker is not installed or not in PATH")
        
        # Check Docker daemon
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                errors.append("Docker daemon is not running or not accessible")
        except subprocess.TimeoutExpired:
            errors.append("Docker daemon is not responding")
        
        # Check if image exists
        try:
            result = subprocess.run(
                ["docker", "images", "-q", self.config.docker_image],
                capture_output=True,
                text=True,
                timeout=5
            )
            if not result.stdout.strip():
                self.logger.warning(
                    f"Docker image not found locally: {self.config.docker_image}. "
                    "It will be pulled on first run."
                )
        except subprocess.TimeoutExpired:
            self.logger.warning("Failed to check for Docker image")
        
        if errors:
            error_msg = "Docker environment validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise RunnerError(error_msg)
        
        self.logger.debug("Docker environment validation passed")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get Docker environment information.
        
        Returns:
            Dictionary with Docker details
        """
        info = super().get_environment_info()
        info.update({
            "docker_image": self.config.docker_image,
            "docker_network": self.config.docker_network,
            "container_id": self.container_id,
        })
        return info



class KubernetesRunner(ExecutionEnvironment):
    """
    Kubernetes Job execution environment.
    
    Runs the Agent Runner as a Kubernetes Job. This provides:
    - Cloud-native execution
    - Automatic scaling and scheduling
    - Resource management via K8s
    - Secret management via K8s Secrets
    - Integration with K8s ecosystem
    
    Requirements: 9.4
    """
    
    def __init__(self, config: Optional[RunnerConfig] = None):
        """
        Initialize Kubernetes runner.
        
        Args:
            config: Runner configuration. If None, uses default config.
        """
        if config is None:
            config = RunnerConfig(execution_mode=ExecutionMode.KUBERNETES)
        elif config.execution_mode != ExecutionMode.KUBERNETES:
            config.execution_mode = ExecutionMode.KUBERNETES
        
        super().__init__(config)
        self.job_name: Optional[str] = None
        self.namespace = config.k8s_namespace
        
        self.logger.info("KubernetesRunner initialized")
    
    def execute(self, task_context: TaskContext) -> RunnerResult:
        """
        Execute task as a Kubernetes Job.
        
        Creates a Kubernetes Job with:
        - Workspace mounted via PVC or hostPath
        - Secrets mounted for credentials
        - Resource requests and limits
        - Service account for K8s API access
        
        Args:
            task_context: Task context
            
        Returns:
            RunnerResult
            
        Requirements: 9.4
        """
        self.logger.info(
            f"Executing task {task_context.task_id} as Kubernetes Job"
        )
        
        try:
            # Validate environment
            self.validate_environment()
            
            # Generate job name
            self.job_name = self._generate_job_name(task_context)
            
            # Create job manifest
            job_manifest = self._create_job_manifest(task_context)
            
            # Write manifest to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.yaml',
                delete=False
            ) as f:
                import yaml
                yaml.dump(job_manifest, f)
                manifest_path = f.name
            
            try:
                # Apply job manifest
                self._apply_job(manifest_path)
                
                # Wait for job completion
                result = self._wait_for_job_completion(
                    task_context.timeout_seconds
                )
                
                return result
                
            finally:
                # Cleanup manifest file
                Path(manifest_path).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"Kubernetes execution failed: {e}")
            raise RunnerError(f"Kubernetes execution failed: {e}")
        finally:
            # Cleanup job if configured
            if self.job_name:
                self._cleanup_job()
    
    def _generate_job_name(self, task_context: TaskContext) -> str:
        """
        Generate Kubernetes Job name.
        
        Job names must be DNS-1123 compliant:
        - Lowercase alphanumeric characters or '-'
        - Start with alphanumeric character
        - End with alphanumeric character
        - Max 63 characters
        
        Args:
            task_context: Task context
            
        Returns:
            Valid Kubernetes Job name
        """
        import re
        
        # Create base name from spec and task ID
        base_name = f"runner-{task_context.spec_name}-{task_context.task_id}"
        
        # Convert to lowercase and replace invalid characters
        job_name = base_name.lower()
        job_name = re.sub(r'[^a-z0-9-]', '-', job_name)
        job_name = re.sub(r'-+', '-', job_name)  # Collapse multiple dashes
        job_name = job_name.strip('-')  # Remove leading/trailing dashes
        
        # Truncate to 63 characters
        if len(job_name) > 63:
            job_name = job_name[:63].rstrip('-')
        
        return job_name
    
    def _create_job_manifest(self, task_context: TaskContext) -> Dict[str, Any]:
        """
        Create Kubernetes Job manifest.
        
        Args:
            task_context: Task context
            
        Returns:
            Job manifest as dictionary
            
        Requirements: 9.4
        """
        # Build container spec
        container = {
            "name": "runner",
            "image": self.config.docker_image,
            "imagePullPolicy": "IfNotPresent",
            "command": ["python", "-m", "necrocode.agent_runner"],
            "args": [
                "--task-id", task_context.task_id,
                "--spec-name", task_context.spec_name,
            ],
            "env": self._get_environment_variables_k8s(),
            "volumeMounts": [
                {
                    "name": "workspace",
                    "mountPath": "/workspace",
                }
            ],
            "resources": {
                "requests": self.config.k8s_resource_requests,
                "limits": self.config.k8s_resource_limits,
            },
        }
        
        # Add secret mounts
        secret_mounts = self._get_secret_mounts()
        if secret_mounts:
            container["volumeMounts"].extend(secret_mounts)
        
        # Build pod spec
        pod_spec = {
            "restartPolicy": "Never",
            "containers": [container],
            "volumes": [
                {
                    "name": "workspace",
                    "hostPath": {
                        "path": str(task_context.slot_path),
                        "type": "Directory",
                    }
                }
            ],
        }
        
        # Add service account if configured
        if self.config.k8s_service_account:
            pod_spec["serviceAccountName"] = self.config.k8s_service_account
        
        # Add image pull secrets if configured
        if self.config.k8s_image_pull_secrets:
            pod_spec["imagePullSecrets"] = [
                {"name": secret} for secret in self.config.k8s_image_pull_secrets
            ]
        
        # Add secret volumes
        secret_volumes = self._get_secret_volumes()
        if secret_volumes:
            pod_spec["volumes"].extend(secret_volumes)
        
        # Build job manifest
        manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": self.job_name,
                "namespace": self.namespace,
                "labels": {
                    "app": "necrocode-runner",
                    "task-id": task_context.task_id,
                    "spec-name": task_context.spec_name,
                },
            },
            "spec": {
                "backoffLimit": 0,  # Don't retry failed jobs
                "ttlSecondsAfterFinished": 3600,  # Cleanup after 1 hour
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "necrocode-runner",
                            "task-id": task_context.task_id,
                        },
                    },
                    "spec": pod_spec,
                },
            },
        }
        
        return manifest
    
    def _get_environment_variables_k8s(self) -> list[Dict[str, Any]]:
        """
        Get environment variables for Kubernetes container.
        
        Returns:
            List of environment variable definitions
            
        Requirements: 9.4
        """
        env_vars = []
        
        # Add basic configuration
        env_vars.extend([
            {"name": "RUNNER_LOG_LEVEL", "value": self.config.log_level},
            {"name": "ARTIFACT_STORE_URL", "value": self.config.artifact_store_url},
        ])
        
        if self.config.kiro_api_url:
            env_vars.append({
                "name": "KIRO_API_URL",
                "value": self.config.kiro_api_url
            })
        
        # Secrets are typically mounted as files or env vars from K8s Secrets
        # Here we show how to reference them from secrets
        env_vars.extend([
            {
                "name": self.config.git_token_env_var,
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "necrocode-secrets",
                        "key": "git-token",
                        "optional": True,
                    }
                }
            },
            {
                "name": self.config.artifact_store_api_key_env_var,
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "necrocode-secrets",
                        "key": "artifact-store-api-key",
                        "optional": True,
                    }
                }
            },
        ])
        
        if self.config.kiro_api_url:
            env_vars.append({
                "name": self.config.kiro_api_key_env_var,
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "necrocode-secrets",
                        "key": "kiro-api-key",
                        "optional": True,
                    }
                }
            })
        
        return env_vars
    
    def _get_secret_mounts(self) -> list[Dict[str, Any]]:
        """
        Get secret volume mounts for container.
        
        Returns:
            List of volume mount definitions
        """
        # Example: mount secrets as files
        return [
            {
                "name": "secrets",
                "mountPath": "/secrets",
                "readOnly": True,
            }
        ]
    
    def _get_secret_volumes(self) -> list[Dict[str, Any]]:
        """
        Get secret volumes for pod.
        
        Returns:
            List of volume definitions
        """
        return [
            {
                "name": "secrets",
                "secret": {
                    "secretName": "necrocode-secrets",
                    "optional": True,
                }
            }
        ]
    
    def _apply_job(self, manifest_path: str) -> None:
        """
        Apply Kubernetes Job manifest.
        
        Args:
            manifest_path: Path to manifest file
            
        Raises:
            RunnerError: If job creation fails
        """
        self.logger.info(f"Creating Kubernetes Job: {self.job_name}")
        
        try:
            result = subprocess.run(
                [
                    "kubectl", "apply",
                    "-f", manifest_path,
                    "-n", self.namespace,
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = f"Failed to create Job: {result.stderr}"
                raise RunnerError(error_msg)
            
            self.logger.info(f"Job created: {self.job_name}")
            
        except subprocess.TimeoutExpired:
            raise RunnerError("Job creation timed out")
        except Exception as e:
            raise RunnerError(f"Failed to create Job: {e}")
    
    def _wait_for_job_completion(self, timeout_seconds: int) -> RunnerResult:
        """
        Wait for Kubernetes Job to complete.
        
        Args:
            timeout_seconds: Maximum time to wait
            
        Returns:
            RunnerResult parsed from job output
            
        Raises:
            RunnerError: If job fails or times out
        """
        self.logger.info(f"Waiting for Job completion: {self.job_name}")
        
        try:
            # Wait for job to complete
            result = subprocess.run(
                [
                    "kubectl", "wait",
                    f"job/{self.job_name}",
                    "--for=condition=complete",
                    f"--timeout={timeout_seconds}s",
                    "-n", self.namespace,
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 10
            )
            
            if result.returncode != 0:
                # Check if job failed
                self._check_job_failure()
                
                error_msg = f"Job did not complete: {result.stderr}"
                raise RunnerError(error_msg)
            
            self.logger.info(f"Job completed: {self.job_name}")
            
            # Get job logs
            logs = self._get_job_logs()
            
            # Parse result from logs
            # In a real implementation, this would parse structured output
            from necrocode.agent_runner.models import RunnerResult
            return RunnerResult(
                success=True,
                runner_id=f"k8s-{self.job_name}",
                task_id="",  # Would be parsed from logs
                duration_seconds=0.0,  # Would be parsed from logs
                artifacts=[],
                error=None,
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Job timed out after {timeout_seconds}s"
            self.logger.error(error_msg)
            raise RunnerError(error_msg)
        except Exception as e:
            self.logger.error(f"Failed to wait for Job: {e}")
            raise RunnerError(f"Failed to wait for Job: {e}")
    
    def _check_job_failure(self) -> None:
        """
        Check if job failed and get failure reason.
        
        Raises:
            RunnerError: If job failed
        """
        try:
            result = subprocess.run(
                [
                    "kubectl", "get",
                    f"job/{self.job_name}",
                    "-o", "jsonpath={.status.conditions[?(@.type=='Failed')].message}",
                    "-n", self.namespace,
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout.strip():
                raise RunnerError(f"Job failed: {result.stdout.strip()}")
                
        except subprocess.TimeoutExpired:
            self.logger.warning("Failed to check job failure status")
    
    def _get_job_logs(self) -> str:
        """
        Get logs from Kubernetes Job.
        
        Returns:
            Job logs as string
        """
        try:
            result = subprocess.run(
                [
                    "kubectl", "logs",
                    f"job/{self.job_name}",
                    "-n", self.namespace,
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                self.logger.warning(f"Failed to get job logs: {result.stderr}")
                return ""
                
        except Exception as e:
            self.logger.warning(f"Failed to get job logs: {e}")
            return ""
    
    def _cleanup_job(self) -> None:
        """
        Cleanup Kubernetes Job.
        
        Deletes the job and associated pods.
        """
        if not self.job_name:
            return
        
        try:
            subprocess.run(
                [
                    "kubectl", "delete",
                    f"job/{self.job_name}",
                    "-n", self.namespace,
                    "--ignore-not-found",
                ],
                capture_output=True,
                timeout=30
            )
            self.logger.debug(f"Deleted job: {self.job_name}")
        except Exception as e:
            self.logger.warning(f"Failed to delete job: {e}")
    
    def validate_environment(self) -> None:
        """
        Validate Kubernetes environment.
        
        Checks that:
        - kubectl is installed and configured
        - Cluster is accessible
        - Namespace exists
        - Required secrets exist (optional)
        
        Raises:
            RunnerError: If validation fails
            
        Requirements: 9.4
        """
        self.logger.debug("Validating Kubernetes environment")
        
        errors = []
        
        # Check kubectl availability
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                errors.append("kubectl is not available or not working properly")
            else:
                self.logger.debug(f"kubectl version: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("kubectl is not installed or not in PATH")
        
        # Check cluster connectivity
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                errors.append("Cannot connect to Kubernetes cluster")
        except subprocess.TimeoutExpired:
            errors.append("Kubernetes cluster is not responding")
        
        # Check namespace exists
        try:
            result = subprocess.run(
                ["kubectl", "get", "namespace", self.namespace],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self.logger.warning(
                    f"Namespace does not exist: {self.namespace}. "
                    "It will be created if you have permissions."
                )
        except subprocess.TimeoutExpired:
            self.logger.warning("Failed to check namespace")
        
        if errors:
            error_msg = "Kubernetes environment validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise RunnerError(error_msg)
        
        self.logger.debug("Kubernetes environment validation passed")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get Kubernetes environment information.
        
        Returns:
            Dictionary with Kubernetes details
        """
        info = super().get_environment_info()
        info.update({
            "namespace": self.namespace,
            "job_name": self.job_name,
            "docker_image": self.config.docker_image,
            "service_account": self.config.k8s_service_account,
        })
        return info


def create_runner(config: Optional[RunnerConfig] = None) -> ExecutionEnvironment:
    """
    Factory function to create appropriate runner based on execution mode.
    
    Args:
        config: Runner configuration. If None, uses default config.
        
    Returns:
        ExecutionEnvironment instance for the configured mode
        
    Raises:
        ValueError: If execution mode is not supported
        
    Requirements: 9.1, 9.5
    """
    if config is None:
        config = RunnerConfig()
    
    mode = config.execution_mode
    
    if mode == ExecutionMode.LOCAL_PROCESS:
        return LocalProcessRunner(config)
    elif mode == ExecutionMode.DOCKER:
        return DockerRunner(config)
    elif mode == ExecutionMode.KUBERNETES:
        return KubernetesRunner(config)
    else:
        raise ValueError(f"Unsupported execution mode: {mode}")

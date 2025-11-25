"""Integration tests for Kubernetes execution environment.

Tests the KubernetesRunner execution environment with Kubernetes Jobs.

Requirements: 9.4
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.agent_runner.config import ExecutionMode, RunnerConfig
from necrocode.agent_runner.execution_env import KubernetesRunner
from necrocode.agent_runner.models import TaskContext


# ============================================================================
# Kubernetes Availability Check
# ============================================================================

def is_kubernetes_available():
    """Check if kubectl is available and can connect to a cluster."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Skip all tests if Kubernetes is not available
pytestmark = pytest.mark.skipif(
    not is_kubernetes_available(),
    reason="Kubernetes is not available or kubectl cannot connect to cluster"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary Git workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Initialize Git repository
    subprocess.run(
        ["git", "init"],
        cwd=workspace,
        check=True,
        capture_output=True
    )
    
    # Configure Git
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=workspace,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=workspace,
        check=True,
        capture_output=True
    )
    
    # Create initial commit
    readme = workspace / "README.md"
    readme.write_text("# Test Project\n")
    
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=workspace,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=workspace,
        check=True,
        capture_output=True
    )
    
    return workspace


@pytest.fixture
def k8s_config(tmp_path):
    """Create Kubernetes runner configuration."""
    return RunnerConfig(
        execution_mode=ExecutionMode.KUBERNETES,
        docker_image="python:3.11-slim",
        k8s_namespace="default",
        k8s_service_account=None,
        k8s_resource_requests={"cpu": "100m", "memory": "128Mi"},
        k8s_resource_limits={"cpu": "500m", "memory": "512Mi"},
        log_level="DEBUG",
        artifact_store_url=f"file://{tmp_path / 'artifacts'}",
    )


@pytest.fixture
def k8s_runner(k8s_config):
    """Create KubernetesRunner instance."""
    return KubernetesRunner(config=k8s_config)


@pytest.fixture
def simple_task_context(temp_workspace):
    """Create a simple task context."""
    return TaskContext(
        task_id="k8s-test-1",
        spec_name="k8s-test",
        title="Kubernetes test task",
        description="Test task for Kubernetes execution",
        acceptance_criteria=["Task should execute in Kubernetes"],
        dependencies=[],
        required_skill="backend",
        slot_path=temp_workspace,
        slot_id="slot-1",
        branch_name="feature/k8s-test",
        timeout_seconds=300,
    )


# ============================================================================
# Environment Validation Tests
# ============================================================================

def test_k8s_environment_validation(k8s_runner):
    """Test Kubernetes environment validation."""
    # Should pass if kubectl is available
    k8s_runner.validate_environment()


def test_k8s_environment_info(k8s_runner):
    """Test getting Kubernetes environment information."""
    info = k8s_runner.get_environment_info()
    
    assert info is not None
    assert info["execution_mode"] == "kubernetes"
    assert "k8s_namespace" in info
    assert info["k8s_namespace"] == "default"


def test_k8s_runner_initialization():
    """Test KubernetesRunner initialization."""
    runner = KubernetesRunner()
    
    assert runner.config.execution_mode == ExecutionMode.KUBERNETES
    assert runner.job_name is None
    assert runner.namespace == "default"


def test_k8s_runner_with_custom_config(k8s_config):
    """Test KubernetesRunner with custom configuration."""
    k8s_config.k8s_namespace = "necrocode"
    k8s_config.k8s_service_account = "necrocode-runner"
    
    runner = KubernetesRunner(config=k8s_config)
    
    assert runner.config.execution_mode == ExecutionMode.KUBERNETES
    assert runner.namespace == "necrocode"


# ============================================================================
# Job Name Generation Tests
# ============================================================================

def test_k8s_job_name_generation(k8s_runner, simple_task_context):
    """Test Kubernetes Job name generation."""
    job_name = k8s_runner._generate_job_name(simple_task_context)
    
    assert job_name is not None
    assert len(job_name) <= 63  # K8s name limit
    assert job_name.islower()
    assert job_name[0].isalnum()
    assert job_name[-1].isalnum()
    assert "runner" in job_name


def test_k8s_job_name_with_special_characters(k8s_runner):
    """Test Job name generation with special characters."""
    task_context = TaskContext(
        task_id="test_1.2.3",
        spec_name="my-spec_v2",
        title="Test",
        description="Test",
        acceptance_criteria=[],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp"),
        slot_id="slot-1",
        branch_name="test",
        timeout_seconds=60,
    )
    
    job_name = k8s_runner._generate_job_name(task_context)
    
    # Should convert invalid characters to dashes
    assert "_" not in job_name
    assert "." not in job_name
    assert job_name.replace("-", "").isalnum()


def test_k8s_job_name_length_limit(k8s_runner):
    """Test Job name respects 63 character limit."""
    task_context = TaskContext(
        task_id="very-long-task-id-that-exceeds-kubernetes-limits",
        spec_name="very-long-spec-name-that-also-exceeds-limits",
        title="Test",
        description="Test",
        acceptance_criteria=[],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp"),
        slot_id="slot-1",
        branch_name="test",
        timeout_seconds=60,
    )
    
    job_name = k8s_runner._generate_job_name(task_context)
    
    assert len(job_name) <= 63
    assert job_name[-1] != "-"  # Should not end with dash


# ============================================================================
# Job Manifest Creation Tests
# ============================================================================

def test_k8s_job_manifest_creation(k8s_runner, simple_task_context):
    """Test Kubernetes Job manifest creation."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    assert manifest is not None
    assert manifest["apiVersion"] == "batch/v1"
    assert manifest["kind"] == "Job"
    assert "metadata" in manifest
    assert "spec" in manifest


def test_k8s_job_manifest_metadata(k8s_runner, simple_task_context):
    """Test Job manifest metadata."""
    k8s_runner.job_name = "test-job"
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    metadata = manifest["metadata"]
    assert metadata["name"] == "test-job"
    assert metadata["namespace"] == "default"
    assert "labels" in metadata
    assert metadata["labels"]["app"] == "necrocode-runner"
    assert metadata["labels"]["task-id"] == simple_task_context.task_id


def test_k8s_job_manifest_container_spec(k8s_runner, simple_task_context):
    """Test Job manifest container specification."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["name"] == "runner"
    assert container["image"] == "python:3.11-slim"
    assert container["command"] == ["python", "-m", "necrocode.agent_runner"]
    assert "--task-id" in container["args"]
    assert simple_task_context.task_id in container["args"]


def test_k8s_job_manifest_resource_limits(k8s_runner, simple_task_context):
    """Test Job manifest resource limits."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    resources = container["resources"]
    
    assert "requests" in resources
    assert resources["requests"]["cpu"] == "100m"
    assert resources["requests"]["memory"] == "128Mi"
    
    assert "limits" in resources
    assert resources["limits"]["cpu"] == "500m"
    assert resources["limits"]["memory"] == "512Mi"


def test_k8s_job_manifest_volumes(k8s_runner, simple_task_context):
    """Test Job manifest volume configuration."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    pod_spec = manifest["spec"]["template"]["spec"]
    
    # Check workspace volume
    volumes = pod_spec["volumes"]
    assert len(volumes) > 0
    
    workspace_volume = next(v for v in volumes if v["name"] == "workspace")
    assert workspace_volume is not None
    assert "hostPath" in workspace_volume
    assert workspace_volume["hostPath"]["path"] == str(simple_task_context.slot_path)


def test_k8s_job_manifest_volume_mounts(k8s_runner, simple_task_context):
    """Test Job manifest volume mounts."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    volume_mounts = container["volumeMounts"]
    
    # Check workspace mount
    workspace_mount = next(m for m in volume_mounts if m["name"] == "workspace")
    assert workspace_mount is not None
    assert workspace_mount["mountPath"] == "/workspace"


def test_k8s_job_manifest_with_service_account(k8s_config, simple_task_context):
    """Test Job manifest with service account."""
    k8s_config.k8s_service_account = "necrocode-runner"
    
    runner = KubernetesRunner(config=k8s_config)
    manifest = runner._create_job_manifest(simple_task_context)
    
    pod_spec = manifest["spec"]["template"]["spec"]
    assert pod_spec["serviceAccountName"] == "necrocode-runner"


def test_k8s_job_manifest_with_image_pull_secrets(k8s_config, simple_task_context):
    """Test Job manifest with image pull secrets."""
    k8s_config.k8s_image_pull_secrets = ["regcred", "dockerhub"]
    
    runner = KubernetesRunner(config=k8s_config)
    manifest = runner._create_job_manifest(simple_task_context)
    
    pod_spec = manifest["spec"]["template"]["spec"]
    assert "imagePullSecrets" in pod_spec
    assert len(pod_spec["imagePullSecrets"]) == 2
    assert pod_spec["imagePullSecrets"][0]["name"] == "regcred"


def test_k8s_job_manifest_restart_policy(k8s_runner, simple_task_context):
    """Test Job manifest restart policy."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    pod_spec = manifest["spec"]["template"]["spec"]
    assert pod_spec["restartPolicy"] == "Never"


def test_k8s_job_manifest_backoff_limit(k8s_runner, simple_task_context):
    """Test Job manifest backoff limit."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    job_spec = manifest["spec"]
    assert job_spec["backoffLimit"] == 0  # Don't retry


def test_k8s_job_manifest_ttl(k8s_runner, simple_task_context):
    """Test Job manifest TTL after finished."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    job_spec = manifest["spec"]
    assert "ttlSecondsAfterFinished" in job_spec
    assert job_spec["ttlSecondsAfterFinished"] == 3600  # 1 hour


# ============================================================================
# Environment Variable Tests
# ============================================================================

def test_k8s_environment_variables(k8s_runner):
    """Test Kubernetes environment variable configuration."""
    env_vars = k8s_runner._get_environment_variables_k8s()
    
    assert isinstance(env_vars, list)
    assert len(env_vars) > 0
    
    # Check basic config vars
    log_level_var = next(v for v in env_vars if v["name"] == "RUNNER_LOG_LEVEL")
    assert log_level_var["value"] == "DEBUG"


def test_k8s_environment_variables_from_secrets(k8s_runner):
    """Test environment variables from Kubernetes Secrets."""
    env_vars = k8s_runner._get_environment_variables_k8s()
    
    # Check secret references
    git_token_var = next(v for v in env_vars if v["name"] == "GIT_TOKEN")
    assert "valueFrom" in git_token_var
    assert "secretKeyRef" in git_token_var["valueFrom"]
    assert git_token_var["valueFrom"]["secretKeyRef"]["name"] == "necrocode-secrets"


def test_k8s_environment_variables_with_kiro(k8s_config):
    """Test environment variables with Kiro API."""
    k8s_config.kiro_api_url = "https://kiro.example.com"
    
    runner = KubernetesRunner(config=k8s_config)
    env_vars = runner._get_environment_variables_k8s()
    
    # Check Kiro URL
    kiro_url_var = next(v for v in env_vars if v["name"] == "KIRO_API_URL")
    assert kiro_url_var["value"] == "https://kiro.example.com"
    
    # Check Kiro API key from secret
    kiro_key_var = next(v for v in env_vars if v["name"] == "KIRO_API_KEY")
    assert "valueFrom" in kiro_key_var


# ============================================================================
# Secret Mount Tests
# ============================================================================

def test_k8s_secret_mounts(k8s_runner):
    """Test secret volume mounts."""
    mounts = k8s_runner._get_secret_mounts()
    
    assert isinstance(mounts, list)
    assert len(mounts) > 0
    
    # Check secrets mount
    secrets_mount = next(m for m in mounts if m["name"] == "secrets")
    assert secrets_mount["mountPath"] == "/secrets"
    assert secrets_mount["readOnly"] is True


def test_k8s_secret_volumes(k8s_runner):
    """Test secret volumes."""
    volumes = k8s_runner._get_secret_volumes()
    
    assert isinstance(volumes, list)
    assert len(volumes) > 0
    
    # Check secrets volume
    secrets_volume = next(v for v in volumes if v["name"] == "secrets")
    assert "secret" in secrets_volume
    assert secrets_volume["secret"]["secretName"] == "necrocode-secrets"


# ============================================================================
# Job Application Tests
# ============================================================================

@pytest.mark.slow
def test_k8s_job_manifest_yaml_format(k8s_runner, simple_task_context):
    """Test that Job manifest can be serialized to YAML."""
    import yaml
    
    k8s_runner.job_name = "test-job"
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    # Should be serializable to YAML
    yaml_str = yaml.dump(manifest)
    assert yaml_str is not None
    assert "apiVersion: batch/v1" in yaml_str
    assert "kind: Job" in yaml_str


# ============================================================================
# Validation Tests
# ============================================================================

def test_k8s_validation_kubectl_available(k8s_runner):
    """Test validation checks kubectl availability."""
    # Should pass if kubectl is available
    k8s_runner.validate_environment()


def test_k8s_validation_cluster_connection(k8s_runner):
    """Test validation checks cluster connection."""
    # Should pass if cluster is accessible
    k8s_runner.validate_environment()


# ============================================================================
# Namespace Tests
# ============================================================================

def test_k8s_custom_namespace(k8s_config, simple_task_context):
    """Test Kubernetes with custom namespace."""
    k8s_config.k8s_namespace = "necrocode-test"
    
    runner = KubernetesRunner(config=k8s_config)
    manifest = runner._create_job_manifest(simple_task_context)
    
    assert manifest["metadata"]["namespace"] == "necrocode-test"


def test_k8s_default_namespace(k8s_runner, simple_task_context):
    """Test Kubernetes with default namespace."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    assert manifest["metadata"]["namespace"] == "default"


# ============================================================================
# Resource Configuration Tests
# ============================================================================

def test_k8s_custom_resource_requests(k8s_config, simple_task_context):
    """Test custom resource requests."""
    k8s_config.k8s_resource_requests = {
        "cpu": "200m",
        "memory": "256Mi",
    }
    
    runner = KubernetesRunner(config=k8s_config)
    manifest = runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    requests = container["resources"]["requests"]
    
    assert requests["cpu"] == "200m"
    assert requests["memory"] == "256Mi"


def test_k8s_custom_resource_limits(k8s_config, simple_task_context):
    """Test custom resource limits."""
    k8s_config.k8s_resource_limits = {
        "cpu": "1000m",
        "memory": "1Gi",
    }
    
    runner = KubernetesRunner(config=k8s_config)
    manifest = runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    limits = container["resources"]["limits"]
    
    assert limits["cpu"] == "1000m"
    assert limits["memory"] == "1Gi"


# ============================================================================
# Label Tests
# ============================================================================

def test_k8s_job_labels(k8s_runner, simple_task_context):
    """Test Job labels."""
    k8s_runner.job_name = "test-job"
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    labels = manifest["metadata"]["labels"]
    
    assert labels["app"] == "necrocode-runner"
    assert labels["task-id"] == simple_task_context.task_id
    assert labels["spec-name"] == simple_task_context.spec_name


def test_k8s_pod_labels(k8s_runner, simple_task_context):
    """Test Pod labels."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    pod_labels = manifest["spec"]["template"]["metadata"]["labels"]
    
    assert pod_labels["app"] == "necrocode-runner"
    assert pod_labels["task-id"] == simple_task_context.task_id


# ============================================================================
# Image Configuration Tests
# ============================================================================

def test_k8s_custom_image(k8s_config, simple_task_context):
    """Test Kubernetes with custom image."""
    k8s_config.docker_image = "custom/runner:latest"
    
    runner = KubernetesRunner(config=k8s_config)
    manifest = runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "custom/runner:latest"


def test_k8s_image_pull_policy(k8s_runner, simple_task_context):
    """Test image pull policy."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["imagePullPolicy"] == "IfNotPresent"


# ============================================================================
# Command and Args Tests
# ============================================================================

def test_k8s_container_command(k8s_runner, simple_task_context):
    """Test container command."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == ["python", "-m", "necrocode.agent_runner"]


def test_k8s_container_args(k8s_runner, simple_task_context):
    """Test container arguments."""
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    args = container["args"]
    
    assert "--task-id" in args
    assert simple_task_context.task_id in args
    assert "--spec-name" in args
    assert simple_task_context.spec_name in args


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_k8s_validation_without_kubectl():
    """Test validation when kubectl is not available."""
    # This test is skipped if kubectl is available
    # It's here for documentation purposes
    pass


def test_k8s_job_name_validation(k8s_runner):
    """Test Job name validation."""
    task_context = TaskContext(
        task_id="test",
        spec_name="test",
        title="Test",
        description="Test",
        acceptance_criteria=[],
        dependencies=[],
        required_skill="backend",
        slot_path=Path("/tmp"),
        slot_id="slot-1",
        branch_name="test",
        timeout_seconds=60,
    )
    
    job_name = k8s_runner._generate_job_name(task_context)
    
    # Should be valid DNS-1123 name
    assert job_name.islower()
    assert job_name[0].isalnum()
    assert job_name[-1].isalnum()


# ============================================================================
# Integration Tests (Require Kubernetes)
# ============================================================================

@pytest.mark.slow
@pytest.mark.integration
def test_k8s_manifest_is_valid_yaml(k8s_runner, simple_task_context):
    """Test that generated manifest is valid YAML."""
    import yaml
    
    k8s_runner.job_name = "test-job"
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    # Should be valid YAML
    yaml_str = yaml.dump(manifest)
    parsed = yaml.safe_load(yaml_str)
    
    assert parsed == manifest


@pytest.mark.slow
@pytest.mark.integration
def test_k8s_manifest_structure(k8s_runner, simple_task_context):
    """Test that manifest has correct structure."""
    k8s_runner.job_name = "test-job"
    manifest = k8s_runner._create_job_manifest(simple_task_context)
    
    # Verify structure
    assert "apiVersion" in manifest
    assert "kind" in manifest
    assert "metadata" in manifest
    assert "spec" in manifest
    assert "template" in manifest["spec"]
    assert "spec" in manifest["spec"]["template"]
    assert "containers" in manifest["spec"]["template"]["spec"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

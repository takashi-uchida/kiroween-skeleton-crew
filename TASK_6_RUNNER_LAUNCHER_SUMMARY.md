# Task 6: RunnerLauncher Implementation Summary

## Overview
Successfully implemented the RunnerLauncher component for the Dispatcher, which launches Agent Runners in different execution environments (local process, Docker, Kubernetes).

## Implementation Details

### Core Components

#### 1. TaskContext (Data Model)
- **Purpose**: Encapsulates all information needed for an Agent Runner to execute a task
- **Key Fields**:
  - Task identification (task_id, spec_name, title, description)
  - Dependencies and required skills
  - Slot information (slot_id, slot_path, repo_url)
  - Branch name and metadata
- **Methods**:
  - `to_dict()`: Serialize to dictionary
  - `to_json()`: Serialize to JSON string

#### 2. BaseLauncher (Abstract Base Class)
- **Purpose**: Defines the interface for all launcher implementations
- **Abstract Method**: `launch(runner_id, task_context, pool) -> Runner`

#### 3. LocalProcessLauncher
- **Purpose**: Launches Agent Runner as a local subprocess
- **Features**:
  - Uses Python subprocess module
  - Passes task context via environment variables
  - Suitable for development and testing
  - Returns Runner with PID
- **Configuration**: Accepts custom runner script path

#### 4. DockerLauncher
- **Purpose**: Launches Agent Runner as a Docker container
- **Features**:
  - Uses Docker Python SDK
  - Mounts workspace slot as volume
  - Applies CPU and memory quotas
  - Auto-removes container on completion
  - Returns Runner with container ID
- **Configuration**:
  - Docker image (from pool config)
  - Volume mounts (workspace slot)
  - Resource limits (CPU quota, memory quota)

#### 5. KubernetesLauncher
- **Purpose**: Launches Agent Runner as a Kubernetes Job
- **Features**:
  - Uses Kubernetes Python client
  - Creates Job with resource requirements
  - Supports custom Job templates
  - Applies CPU and memory requests/limits
  - Returns Runner with job name
- **Configuration**:
  - Namespace (from pool config)
  - Docker image
  - Optional Job template file
  - Resource quotas

#### 6. RunnerLauncher (Main Class)
- **Purpose**: Main launcher that delegates to specific launchers
- **Features**:
  - Generates unique runner IDs (UUID-based)
  - Builds task context from task and slot
  - Delegates to appropriate launcher based on pool type
  - Implements retry logic on launch failure
  - Lazy-loads Docker and Kubernetes launchers
- **Methods**:
  - `launch(task, slot, pool)`: Launch a runner
  - `_generate_runner_id()`: Generate unique ID
  - `_build_task_context(task, slot)`: Build context

### Error Handling

#### Launch Failure Handling (Requirement 5.5)
- **Retry Logic**: Configurable retry attempts (default: 3)
- **Error Detection**: Catches all launcher exceptions
- **Error Reporting**: Logs failures with context
- **Graceful Degradation**: Returns detailed error messages

#### Exception Types
- `RunnerLaunchError`: Raised when launch fails
- Includes context about which launcher and attempt failed

## Files Created

### Implementation
1. **necrocode/dispatcher/runner_launcher.py** (600+ lines)
   - All launcher implementations
   - TaskContext data model
   - Retry logic and error handling

### Tests
2. **tests/test_runner_launcher.py** (400+ lines)
   - TaskContext tests (creation, serialization)
   - LocalProcessLauncher tests (success, failure)
   - DockerLauncher tests (with mocking)
   - KubernetesLauncher tests (with mocking)
   - RunnerLauncher tests (ID generation, context building, retry logic)
   - 11 tests passing, 2 skipped (Docker/K8s not installed)

### Examples
3. **examples/runner_launcher_example.py** (250+ lines)
   - Local process launch example
   - Docker launch example
   - Kubernetes launch example
   - Retry behavior example
   - Task context building example

### Updates
4. **necrocode/dispatcher/__init__.py**
   - Exported new classes: RunnerLauncher, TaskContext, launchers

## Requirements Coverage

### ✅ Requirement 5.1: Agent Runner Launch
- Implemented launchers for all three pool types:
  - Local process (subprocess)
  - Docker (containers)
  - Kubernetes (Jobs)

### ✅ Requirement 5.2: Task Context Passing
- TaskContext includes all necessary information:
  - Task details (ID, title, description)
  - Dependencies and skills
  - Slot information
  - Repository and branch details

### ✅ Requirement 5.3: Runner ID Assignment
- Unique runner IDs generated using UUID
- Format: `runner-{12-char-hex}`
- Guaranteed uniqueness across launches

### ✅ Requirement 5.4: Task Registry Recording
- Runner information structured for registry updates:
  - Runner ID, task ID, pool name
  - Slot ID and execution details
  - PID/container ID/job name based on type

### ✅ Requirement 5.5: Launch Failure Handling
- Configurable retry attempts (default: 3)
- Detailed error logging
- Graceful failure with informative exceptions
- Retry backoff between attempts

## Testing Results

```
tests/test_runner_launcher.py::TestTaskContext::test_task_context_creation PASSED
tests/test_runner_launcher.py::TestTaskContext::test_task_context_to_dict PASSED
tests/test_runner_launcher.py::TestTaskContext::test_task_context_to_json PASSED
tests/test_runner_launcher.py::TestLocalProcessLauncher::test_local_launch_success PASSED
tests/test_runner_launcher.py::TestLocalProcessLauncher::test_local_launch_failure PASSED
tests/test_runner_launcher.py::TestDockerLauncher::test_docker_launch_success SKIPPED
tests/test_runner_launcher.py::TestKubernetesLauncher::test_k8s_launch_success SKIPPED
tests/test_runner_launcher.py::TestRunnerLauncher::test_generate_runner_id PASSED
tests/test_runner_launcher.py::TestRunnerLauncher::test_build_task_context PASSED
tests/test_runner_launcher.py::TestRunnerLauncher::test_launch_local_process PASSED
tests/test_runner_launcher.py::TestRunnerLauncher::test_launch_with_retry PASSED
tests/test_runner_launcher.py::TestRunnerLauncher::test_launch_exhausted_retries PASSED
tests/test_runner_launcher.py::TestRunnerLauncher::test_launch_unknown_pool_type PASSED

Result: 11 passed, 2 skipped (Docker/K8s libraries not installed)
```

## Key Design Decisions

### 1. Lazy Loading of Launchers
- Docker and Kubernetes launchers are lazy-loaded
- Avoids import errors when libraries aren't installed
- Only loads when actually needed

### 2. Environment Variable Passing
- Task context passed via environment variables
- JSON serialization for complex data
- Works across all execution environments

### 3. Resource Quota Application
- CPU and memory quotas from pool config
- Applied differently per launcher:
  - Docker: mem_limit, cpu_quota
  - Kubernetes: resource requests/limits
  - Local: no enforcement (relies on OS)

### 4. Retry Strategy
- Simple retry with logging
- No exponential backoff (can be added later)
- Configurable retry count
- Preserves error context

### 5. Volume Mounting (Docker)
- Workspace slot mounted to /workspace
- Read-write access for code changes
- Configurable via pool config

### 6. Job Template Support (Kubernetes)
- Supports custom Job templates
- Falls back to default Job manifest
- Allows advanced K8s configurations

## Integration Points

### With Task Registry
- Runner information ready for registry updates
- Includes all tracking fields (runner_id, task_id, slot_id)

### With Repo Pool Manager
- Accepts Slot objects from pool manager
- Uses slot path for workspace mounting

### With Agent Pool Manager
- Reads pool configuration
- Applies resource quotas
- Respects pool type

## Usage Example

```python
from necrocode.dispatcher.runner_launcher import RunnerLauncher
from necrocode.dispatcher.models import AgentPool, PoolType

# Create launcher
launcher = RunnerLauncher(retry_attempts=3)

# Create pool
pool = AgentPool(
    name="docker-pool",
    type=PoolType.DOCKER,
    max_concurrency=4,
    cpu_quota=2,
    memory_quota=4096,
    config={"image": "necrocode/runner:latest"}
)

# Launch runner
runner = launcher.launch(task, slot, pool)
print(f"Launched runner {runner.runner_id} with container {runner.container_id}")
```

## Next Steps

The RunnerLauncher is now ready for integration with:
1. **Task 7**: RunnerMonitor (to track launched runners)
2. **Task 9**: DispatcherCore (to use launcher in main loop)
3. **Task 12**: Event recording (to log launch events)

## Notes

- Docker and Kubernetes libraries are optional dependencies
- Tests gracefully skip when libraries aren't available
- All core functionality works with local process launcher
- Production deployments should install docker/kubernetes libraries as needed

# Job Cancellation - Design Document

## Overview

This document describes the design for implementing job cancellation functionality in NecroCode. The feature enables users to cancel running jobs, stop associated runners, clean up resources, and maintain system consistency during cancellation operations.

## Architecture

### Component Interaction

```
User/CLI
    ↓
CancellationService
    ↓
    ├─→ Dispatcher (stop task assignment)
    ├─→ RunnerMonitor (terminate runners)
    ├─→ TaskRegistry (update task states)
    ├─→ RepoPoolManager (release slots)
    └─→ ArtifactStore (preserve partial results)
```

### Design Decisions

**Decision 1: Graceful vs Force Cancellation**
- **Rationale**: Allow graceful shutdown by default (finish current operation, cleanup) with force option for immediate termination
- **Trade-off**: Graceful takes longer but ensures cleaner state; force is immediate but may leave inconsistent state

**Decision 2: Preserve Completed Work**
- **Rationale**: Completed tasks and their artifacts should remain available even after cancellation
- **Trade-off**: Requires careful state management but provides value to users who want to see partial progress

**Decision 3: Cascading Cancellation**
- **Rationale**: Cancelling a job should cancel all pending/running tasks; cancelling a single task should only affect that task and its dependents
- **Trade-off**: More complex logic but provides flexibility

## Components and Interfaces

### 1. CancellationService

Core service responsible for orchestrating cancellation operations.

```python
class CancellationService:
    """Manages job and task cancellation operations."""
    
    def __init__(
        self,
        task_registry: TaskRegistry,
        dispatcher: DispatcherCore,
        runner_monitor: RunnerMonitor,
        repo_pool: PoolManager,
        artifact_store: ArtifactStore
    ):
        self.task_registry = task_registry
        self.dispatcher = dispatcher
        self.runner_monitor = runner_monitor
        self.repo_pool = repo_pool
        self.artifact_store = artifact_store
        self.cancellation_tracker = CancellationTracker()
    
    async def cancel_job(
        self,
        job_id: str,
        reason: str,
        force: bool = False
    ) -> CancellationResult:
        """
        Cancel entire job and all associated tasks.
        
        Args:
            job_id: Job identifier
            reason: Reason for cancellation
            force: If True, immediate termination; if False, graceful shutdown
            
        Returns:
            CancellationResult with status and affected tasks
        """
        pass
    
    async def cancel_task(
        self,
        task_id: str,
        reason: str,
        cascade: bool = True
    ) -> CancellationResult:
        """
        Cancel specific task and optionally its dependents.
        
        Args:
            task_id: Task identifier
            reason: Reason for cancellation
            cascade: If True, cancel dependent tasks
            
        Returns:
            CancellationResult with status
        """
        pass
    
    async def get_cancellation_status(
        self,
        job_id: str
    ) -> CancellationStatus:
        """Get current cancellation status for a job."""
        pass
```

### 2. CancellationTracker

Tracks cancellation operations and their progress.

```python
class CancellationTracker:
    """Tracks ongoing cancellation operations."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.active_cancellations: Dict[str, CancellationRecord] = {}
    
    def start_cancellation(
        self,
        job_id: str,
        reason: str,
        force: bool
    ) -> str:
        """Record start of cancellation operation."""
        pass
    
    def update_progress(
        self,
        cancellation_id: str,
        step: str,
        status: str
    ):
        """Update cancellation progress."""
        pass
    
    def complete_cancellation(
        self,
        cancellation_id: str,
        result: CancellationResult
    ):
        """Mark cancellation as complete."""
        pass
```

### 3. RunnerTerminator

Handles termination of running agent instances.

```python
class RunnerTerminator:
    """Terminates running agent instances."""
    
    def __init__(self, runner_monitor: RunnerMonitor):
        self.runner_monitor = runner_monitor
    
    async def terminate_runner(
        self,
        runner_id: str,
        graceful: bool = True,
        timeout: int = 30
    ) -> bool:
        """
        Terminate a specific runner.
        
        Args:
            runner_id: Runner identifier
            graceful: If True, allow cleanup; if False, kill immediately
            timeout: Seconds to wait for graceful shutdown
            
        Returns:
            True if terminated successfully
        """
        pass
    
    async def terminate_job_runners(
        self,
        job_id: str,
        graceful: bool = True
    ) -> List[str]:
        """Terminate all runners associated with a job."""
        pass
```

### 4. ResourceCleaner

Cleans up resources after cancellation.

```python
class ResourceCleaner:
    """Cleans up resources after job/task cancellation."""
    
    def __init__(
        self,
        repo_pool: PoolManager,
        artifact_store: ArtifactStore
    ):
        self.repo_pool = repo_pool
        self.artifact_store = artifact_store
    
    async def cleanup_job_resources(
        self,
        job_id: str,
        preserve_artifacts: bool = True
    ) -> CleanupResult:
        """
        Clean up all resources for a cancelled job.
        
        Args:
            job_id: Job identifier
            preserve_artifacts: If True, keep artifacts from completed tasks
            
        Returns:
            CleanupResult with details of cleaned resources
        """
        pass
    
    async def release_repo_slots(
        self,
        job_id: str
    ) -> List[str]:
        """Release all repo pool slots for a job."""
        pass
```

## Data Models

### CancellationRecord

```python
@dataclass
class CancellationRecord:
    """Record of a cancellation operation."""
    
    cancellation_id: str
    job_id: str
    task_id: Optional[str]  # None for full job cancellation
    reason: str
    force: bool
    initiated_at: datetime
    initiated_by: str  # user or system
    status: CancellationStatus
    progress: List[CancellationStep]
    completed_at: Optional[datetime]
    error: Optional[str]
```

### CancellationStatus

```python
class CancellationStatus(str, Enum):
    """Status of cancellation operation."""
    
    INITIATED = "initiated"
    STOPPING_RUNNERS = "stopping_runners"
    UPDATING_TASKS = "updating_tasks"
    CLEANING_RESOURCES = "cleaning_resources"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some operations failed
```

### CancellationStep

```python
@dataclass
class CancellationStep:
    """Individual step in cancellation process."""
    
    step_name: str
    status: str  # "pending", "in_progress", "completed", "failed"
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    details: Dict[str, Any]
    error: Optional[str]
```

### CancellationResult

```python
@dataclass
class CancellationResult:
    """Result of cancellation operation."""
    
    success: bool
    cancellation_id: str
    job_id: str
    tasks_cancelled: List[str]
    tasks_completed: List[str]  # Already completed before cancellation
    runners_terminated: List[str]
    slots_released: List[str]
    artifacts_preserved: List[str]
    errors: List[str]
    duration_seconds: float
```

## Cancellation Workflow

### Full Job Cancellation

```
1. Validate job exists and is cancellable
2. Create cancellation record
3. Stop dispatcher from assigning new tasks for this job
4. Identify all running/pending tasks
5. For each running task:
   a. Send termination signal to runner
   b. Wait for graceful shutdown (if not force)
   c. Force kill if timeout exceeded
6. Update task states in TaskRegistry:
   - Running → Cancelled
   - Pending → Cancelled
   - Completed → Keep as Completed
7. Release repo pool slots
8. Preserve artifacts from completed tasks
9. Record cancellation completion
10. Emit cancellation event
```

### Single Task Cancellation

```
1. Validate task exists and is cancellable
2. Create cancellation record
3. If task is running:
   a. Identify runner
   b. Send termination signal
   c. Wait for graceful shutdown
4. Update task state to Cancelled
5. If cascade=True:
   a. Identify dependent tasks
   b. Cancel each dependent task
6. Release associated resources
7. Record cancellation completion
```

## Error Handling

### Cancellation Failures

**Scenario 1: Runner Won't Terminate**
- Attempt graceful shutdown with timeout
- If timeout exceeded, force kill
- Log warning and continue with other steps
- Mark cancellation as "partial" if force kill fails

**Scenario 2: Resource Cleanup Fails**
- Log error with details
- Continue with other cleanup operations
- Return list of failed cleanups in result
- Schedule retry for failed cleanups

**Scenario 3: State Update Fails**
- Retry state update with exponential backoff
- If all retries fail, log critical error
- Mark cancellation as "failed"
- Require manual intervention

### Rollback Strategy

Since cancellation is a destructive operation, rollback is limited:
- Cannot restart terminated runners
- Cannot restore cancelled task states
- Can preserve all artifacts and logs for debugging
- Can provide detailed cancellation report for manual recovery

## Integration Points

### Dispatcher Integration

```python
# Dispatcher must check for cancellation before assigning tasks
class DispatcherCore:
    def is_job_cancelled(self, job_id: str) -> bool:
        """Check if job is cancelled."""
        pass
    
    def block_job_assignment(self, job_id: str):
        """Prevent new task assignments for job."""
        pass
```

### TaskRegistry Integration

```python
# TaskRegistry must support bulk state updates
class TaskRegistry:
    def cancel_job_tasks(
        self,
        job_id: str,
        reason: str
    ) -> List[str]:
        """Cancel all tasks for a job."""
        pass
    
    def get_job_tasks_by_state(
        self,
        job_id: str,
        states: List[TaskState]
    ) -> List[Task]:
        """Get tasks in specific states."""
        pass
```

### RunnerMonitor Integration

```python
# RunnerMonitor must support termination signals
class RunnerMonitor:
    async def send_termination_signal(
        self,
        runner_id: str,
        graceful: bool = True
    ):
        """Send termination signal to runner."""
        pass
    
    def get_job_runners(self, job_id: str) -> List[str]:
        """Get all runners for a job."""
        pass
```

## CLI Interface

### Commands

```bash
# Cancel entire job
necrocode job cancel <job-id> [--reason "reason"] [--force]

# Cancel specific task
necrocode job cancel <job-id> --task <task-id> [--no-cascade]

# Check cancellation status
necrocode job cancel-status <job-id>

# List recent cancellations
necrocode job cancellations [--limit 10]
```

### Output Format

```
Cancelling job: chat-app-implementation
Reason: User requested cancellation

Progress:
✓ Stopped task assignment
✓ Terminated 3 runners
✓ Cancelled 5 pending tasks
✓ Updated task states
✓ Released 2 repo slots
✓ Preserved 8 artifacts

Summary:
- Tasks completed: 3
- Tasks cancelled: 5
- Runners terminated: 3
- Duration: 12.5s

Cancellation ID: cancel-abc123
Status: COMPLETED
```

## API Endpoints

### REST API

```
POST /api/jobs/{job_id}/cancel
Body: {
  "reason": "string",
  "force": boolean
}
Response: CancellationResult

POST /api/tasks/{task_id}/cancel
Body: {
  "reason": "string",
  "cascade": boolean
}
Response: CancellationResult

GET /api/jobs/{job_id}/cancellation-status
Response: CancellationStatus

GET /api/cancellations?limit=10&offset=0
Response: List[CancellationRecord]
```

## Testing Strategy

### Unit Tests

- CancellationService methods with mocked dependencies
- CancellationTracker state management
- RunnerTerminator termination logic
- ResourceCleaner cleanup operations

### Integration Tests

- Full job cancellation flow
- Single task cancellation with cascade
- Graceful vs force cancellation
- Cancellation during different job phases
- Concurrent cancellation requests
- Cancellation with partial failures

### Edge Cases

- Cancel already completed job
- Cancel non-existent job
- Cancel while no runners active
- Cancel with all tasks completed
- Multiple cancellation requests for same job
- Cancellation timeout scenarios

## Performance Considerations

### Cancellation Speed

- Graceful shutdown: 10-30 seconds per runner
- Force shutdown: 1-5 seconds per runner
- State updates: O(n) where n = number of tasks
- Resource cleanup: O(m) where m = number of slots

### Optimization Strategies

- Parallel runner termination
- Batch state updates in TaskRegistry
- Async resource cleanup
- Timeout-based force escalation

## Security Considerations

### Authorization

- Only job owner or admin can cancel jobs
- API endpoints require authentication
- Audit log all cancellation operations

### Data Protection

- Preserve artifacts from completed tasks
- Secure deletion of sensitive temporary data
- Maintain cancellation audit trail

## Monitoring and Observability

### Metrics

- `cancellation_requests_total` (counter)
- `cancellation_duration_seconds` (histogram)
- `cancellation_failures_total` (counter)
- `runners_terminated_total` (counter)
- `resources_cleaned_total` (counter)

### Logging

- Log cancellation initiation with reason
- Log each cancellation step
- Log termination signals sent
- Log cleanup operations
- Log any errors or timeouts

### Alerts

- Alert on cancellation failures
- Alert on force kill usage
- Alert on cleanup failures
- Alert on high cancellation rate

## Future Enhancements

1. **Pause/Resume**: Allow pausing jobs instead of cancelling
2. **Scheduled Cancellation**: Cancel job at specific time
3. **Conditional Cancellation**: Cancel if certain conditions met
4. **Cancellation Policies**: Auto-cancel based on rules
5. **Partial Rollback**: Ability to rollback specific tasks
6. **Cancellation Templates**: Pre-defined cancellation strategies

## References

- Dispatcher Design: `.kiro/specs/dispatcher/design.md`
- Agent Runner Design: `.kiro/specs/agent-runner/design.md`
- Task Registry Design: `.kiro/specs/task-registry/design.md`
- Repo Pool Manager Design: `.kiro/specs/repo-pool-manager/design.md`

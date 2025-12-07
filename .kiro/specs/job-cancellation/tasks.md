# Job Cancellation - Implementation Plan

- [ ] 1. Implement core data models and enums
  - Create `CancellationStatus`, `CancellationRecord`, `CancellationStep`, and `CancellationResult` dataclasses
  - Define cancellation-related exceptions
  - _Requirements: 1.3_

- [ ] 2. Implement CancellationTracker
  - [ ] 2.1 Create CancellationTracker class with storage management
    - Implement `start_cancellation()` to create and persist cancellation records
    - Implement `update_progress()` to track cancellation steps
    - Implement `complete_cancellation()` to finalize records
    - Add file-based persistence for cancellation history
    - _Requirements: 1.3_

  - [ ] 2.2 Add query methods for cancellation status
    - Implement `get_cancellation()` to retrieve cancellation records
    - Implement `get_job_cancellations()` to list all cancellations for a job
    - Implement `is_job_cancelled()` for quick status checks
    - _Requirements: 1.3_

- [ ] 3. Implement RunnerTerminator
  - [ ] 3.1 Create RunnerTerminator class
    - Implement `terminate_runner()` with graceful and force modes
    - Add timeout handling for graceful shutdown
    - Implement signal sending to runner processes
    - _Requirements: 1.1_

  - [ ] 3.2 Add bulk termination support
    - Implement `terminate_job_runners()` for parallel termination
    - Add progress tracking for multiple runner terminations
    - Handle partial termination failures
    - _Requirements: 1.1_

- [ ] 4. Implement ResourceCleaner
  - [ ] 4.1 Create ResourceCleaner class
    - Implement `cleanup_job_resources()` with artifact preservation
    - Implement `release_repo_slots()` to free pool resources
    - Add cleanup result tracking
    - _Requirements: 1.1_

  - [ ] 4.2 Add error handling and retry logic
    - Implement retry mechanism for failed cleanup operations
    - Add logging for cleanup failures
    - Create cleanup report generation
    - _Requirements: 1.1_

- [ ] 5. Implement CancellationService core logic
  - [ ] 5.1 Create CancellationService class with dependencies
    - Initialize with TaskRegistry, Dispatcher, RunnerMonitor, RepoPool, ArtifactStore
    - Set up CancellationTracker instance
    - Add configuration for timeouts and retry policies
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 5.2 Implement full job cancellation
    - Implement `cancel_job()` method with validation
    - Add dispatcher blocking to prevent new task assignments
    - Implement task state identification (running/pending/completed)
    - Integrate RunnerTerminator for runner shutdown
    - Update TaskRegistry states for all affected tasks
    - Integrate ResourceCleaner for cleanup
    - Add cancellation event emission
    - _Requirements: 1.1, 1.3_

  - [ ] 5.3 Implement single task cancellation
    - Implement `cancel_task()` method with validation
    - Add runner identification and termination for specific task
    - Implement cascade logic for dependent tasks
    - Update task state in TaskRegistry
    - Release task-specific resources
    - _Requirements: 1.2_

  - [ ] 5.4 Implement cancellation status queries
    - Implement `get_cancellation_status()` method
    - Add real-time progress reporting
    - Create detailed status response with all steps
    - _Requirements: 1.3_

- [ ] 6. Add Dispatcher integration
  - [ ] 6.1 Extend DispatcherCore with cancellation support
    - Add `is_job_cancelled()` method to check cancellation status
    - Implement `block_job_assignment()` to prevent new task assignments
    - Integrate cancellation checks in task assignment flow
    - _Requirements: 1.1_

  - [ ] 6.2 Add cancellation event handling
    - Subscribe to cancellation events
    - Update internal state when jobs are cancelled
    - Clean up job-related queues and assignments
    - _Requirements: 1.1_

- [ ] 7. Add TaskRegistry integration
  - [ ] 7.1 Extend TaskRegistry with bulk cancellation
    - Implement `cancel_job_tasks()` for bulk state updates
    - Add `get_job_tasks_by_state()` for filtering tasks
    - Implement atomic state transitions for cancellation
    - _Requirements: 1.1, 1.2_

  - [ ] 7.2 Add cancellation event recording
    - Record cancellation events in event store
    - Add cancellation reason to task metadata
    - Track cancellation timestamps
    - _Requirements: 1.3_

- [ ] 8. Add RunnerMonitor integration
  - [ ] 8.1 Extend RunnerMonitor with termination support
    - Implement `send_termination_signal()` for graceful shutdown
    - Add `get_job_runners()` to list runners by job
    - Implement runner state tracking during termination
    - _Requirements: 1.1_

  - [ ] 8.2 Add termination status monitoring
    - Track runner termination progress
    - Implement timeout detection
    - Add force kill escalation logic
    - _Requirements: 1.1_

- [ ] 9. Implement CLI commands
  - [ ] 9.1 Add job cancellation command
    - Create `necrocode job cancel <job-id>` command
    - Add `--reason` flag for cancellation reason
    - Add `--force` flag for immediate termination
    - Implement progress display during cancellation
    - _Requirements: 1.1_

  - [ ] 9.2 Add task cancellation command
    - Add `--task <task-id>` flag for single task cancellation
    - Add `--no-cascade` flag to prevent dependent task cancellation
    - Display affected tasks and resources
    - _Requirements: 1.2_

  - [ ] 9.3 Add cancellation status command
    - Create `necrocode job cancel-status <job-id>` command
    - Display detailed cancellation progress
    - Show completed and pending steps
    - _Requirements: 1.3_

  - [ ] 9.4 Add cancellation history command
    - Create `necrocode job cancellations` command
    - Add `--limit` flag for result pagination
    - Display cancellation summary table
    - _Requirements: 1.3_

- [ ] 10. Implement REST API endpoints
  - [ ] 10.1 Create job cancellation endpoint
    - Implement `POST /api/jobs/{job_id}/cancel`
    - Add request validation for reason and force parameters
    - Return CancellationResult in response
    - Add authentication and authorization checks
    - _Requirements: 1.1_

  - [ ] 10.2 Create task cancellation endpoint
    - Implement `POST /api/tasks/{task_id}/cancel`
    - Add request validation for reason and cascade parameters
    - Return CancellationResult in response
    - _Requirements: 1.2_

  - [ ] 10.3 Create cancellation status endpoint
    - Implement `GET /api/jobs/{job_id}/cancellation-status`
    - Return real-time cancellation status
    - Include progress details and errors
    - _Requirements: 1.3_

  - [ ] 10.4 Create cancellation history endpoint
    - Implement `GET /api/cancellations`
    - Add pagination support with limit and offset
    - Add filtering by job_id and status
    - _Requirements: 1.3_

- [ ] 11. Add error handling and recovery
  - [ ] 11.1 Implement cancellation failure handling
    - Add retry logic for failed terminations
    - Implement partial cancellation result tracking
    - Add error aggregation and reporting
    - _Requirements: 1.1_

  - [ ] 11.2 Add timeout handling
    - Implement graceful shutdown timeouts
    - Add automatic escalation to force kill
    - Track timeout occurrences in metrics
    - _Requirements: 1.1_

  - [ ] 11.3 Add state consistency checks
    - Implement validation before cancellation
    - Add post-cancellation state verification
    - Create recovery procedures for inconsistent states
    - _Requirements: 1.3_

- [ ] 12. Add monitoring and observability
  - [ ] 12.1 Implement cancellation metrics
    - Add `cancellation_requests_total` counter
    - Add `cancellation_duration_seconds` histogram
    - Add `cancellation_failures_total` counter
    - Add `runners_terminated_total` counter
    - _Requirements: 1.1, 1.3_

  - [ ] 12.2 Add structured logging
    - Log cancellation initiation with context
    - Log each cancellation step with timing
    - Log termination signals and responses
    - Log cleanup operations and results
    - _Requirements: 1.3_

  - [ ] 12.3 Add alerting rules
    - Create alerts for cancellation failures
    - Create alerts for force kill usage
    - Create alerts for cleanup failures
    - _Requirements: 1.1_

- [ ]* 13. Write unit tests
  - [ ]* 13.1 Test CancellationTracker
    - Test cancellation record creation and persistence
    - Test progress tracking and updates
    - Test query methods
    - _Requirements: 1.3_

  - [ ]* 13.2 Test RunnerTerminator
    - Test graceful termination with timeout
    - Test force termination
    - Test bulk termination with partial failures
    - _Requirements: 1.1_

  - [ ]* 13.3 Test ResourceCleaner
    - Test resource cleanup with artifact preservation
    - Test repo slot release
    - Test cleanup retry logic
    - _Requirements: 1.1_

  - [ ]* 13.4 Test CancellationService
    - Test full job cancellation flow
    - Test single task cancellation with cascade
    - Test cancellation status queries
    - Test error handling scenarios
    - _Requirements: 1.1, 1.2, 1.3_

- [ ]* 14. Write integration tests
  - [ ]* 14.1 Test end-to-end job cancellation
    - Test cancellation of running job with multiple tasks
    - Verify all runners terminated
    - Verify all resources cleaned up
    - Verify task states updated correctly
    - _Requirements: 1.1_

  - [ ]* 14.2 Test task cancellation with dependencies
    - Test single task cancellation with cascade
    - Test single task cancellation without cascade
    - Verify dependent task handling
    - _Requirements: 1.2_

  - [ ]* 14.3 Test concurrent cancellation requests
    - Test multiple cancellation requests for same job
    - Test cancellation during different job phases
    - Verify idempotency
    - _Requirements: 1.1_

  - [ ]* 14.4 Test cancellation failure scenarios
    - Test cancellation with runner termination failures
    - Test cancellation with cleanup failures
    - Test cancellation with state update failures
    - Verify partial cancellation handling
    - _Requirements: 1.1_

- [ ]* 15. Create documentation and examples
  - [ ]* 15.1 Write usage documentation
    - Document CLI commands with examples
    - Document API endpoints with request/response examples
    - Document cancellation workflow and best practices
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 15.2 Create example scripts
    - Create example for programmatic job cancellation
    - Create example for task cancellation with cascade
    - Create example for monitoring cancellation status
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 15.3 Update architecture documentation
    - Update system architecture diagrams
    - Document integration points with other services
    - Document error handling and recovery procedures
    - _Requirements: 1.1, 1.3_

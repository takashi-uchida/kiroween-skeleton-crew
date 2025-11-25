"""
Tests for RunnerOrchestrator.

This module tests the main orchestration logic of the Agent Runner,
including initialization, task context validation, and state management.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from necrocode.agent_runner import (
    RunnerOrchestrator,
    RunnerConfig,
    TaskContext,
    RunnerState,
    ExecutionMode,
    TaskContextValidationError,
)


class TestRunnerOrchestratorInit:
    """Tests for RunnerOrchestrator initialization."""
    
    def test_init_with_default_config(self, tmp_path):
        """Test initialization with default configuration."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        assert orchestrator.runner_id.startswith("runner-")
        assert orchestrator.state == RunnerState.IDLE
        assert orchestrator.config is not None
        assert orchestrator.workspace_manager is not None
        assert orchestrator.task_executor is not None
        assert orchestrator.test_runner is not None
        assert orchestrator.artifact_uploader is not None
        assert orchestrator.playbook_engine is not None
    
    def test_init_with_custom_config(self, tmp_path):
        """Test initialization with custom configuration."""
        config = RunnerConfig(
            execution_mode=ExecutionMode.DOCKER,
            default_timeout_seconds=3600,
            log_level="DEBUG",
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        
        orchestrator = RunnerOrchestrator(config=config)
        
        assert orchestrator.config.execution_mode == ExecutionMode.DOCKER
        assert orchestrator.config.default_timeout_seconds == 3600
        assert orchestrator.config.log_level == "DEBUG"
    
    def test_generate_runner_id(self, tmp_path):
        """Test runner ID generation."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator1 = RunnerOrchestrator(config=config)
        orchestrator2 = RunnerOrchestrator(config=config)
        
        # IDs should be unique
        assert orchestrator1.runner_id != orchestrator2.runner_id
        
        # IDs should have correct format
        assert orchestrator1.runner_id.startswith("runner-")
        assert len(orchestrator1.runner_id) > len("runner-")


class TestTaskContextValidation:
    """Tests for task context validation."""
    
    def test_validate_valid_context(self, tmp_path):
        """Test validation of a valid task context."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Create a temporary workspace directory
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        
        task_context = TaskContext(
            task_id="1.1",
            spec_name="test-spec",
            title="Test Task",
            description="Test description",
            acceptance_criteria=["Criterion 1", "Criterion 2"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_dir,
            slot_id="slot-1",
            branch_name="feature/test-branch",
        )
        
        # Should not raise exception
        orchestrator._validate_task_context(task_context)
    
    def test_validate_missing_task_id(self, tmp_path):
        """Test validation fails when task_id is missing."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        
        task_context = TaskContext(
            task_id="",  # Empty task_id
            spec_name="test-spec",
            title="Test Task",
            description="Test description",
            acceptance_criteria=["Criterion 1"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_dir,
            slot_id="slot-1",
            branch_name="feature/test-branch",
        )
        
        with pytest.raises(TaskContextValidationError) as exc_info:
            orchestrator._validate_task_context(task_context)
        
        assert "task_id is required" in str(exc_info.value)
    
    def test_validate_missing_spec_name(self, tmp_path):
        """Test validation fails when spec_name is missing."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        
        task_context = TaskContext(
            task_id="1.1",
            spec_name="",  # Empty spec_name
            title="Test Task",
            description="Test description",
            acceptance_criteria=["Criterion 1"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_dir,
            slot_id="slot-1",
            branch_name="feature/test-branch",
        )
        
        with pytest.raises(TaskContextValidationError) as exc_info:
            orchestrator._validate_task_context(task_context)
        
        assert "spec_name is required" in str(exc_info.value)
    
    def test_validate_nonexistent_slot_path(self, tmp_path):
        """Test validation fails when slot_path doesn't exist."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        nonexistent_path = tmp_path / "nonexistent"
        
        task_context = TaskContext(
            task_id="1.1",
            spec_name="test-spec",
            title="Test Task",
            description="Test description",
            acceptance_criteria=["Criterion 1"],
            dependencies=[],
            required_skill="backend",
            slot_path=nonexistent_path,
            slot_id="slot-1",
            branch_name="feature/test-branch",
        )
        
        with pytest.raises(TaskContextValidationError) as exc_info:
            orchestrator._validate_task_context(task_context)
        
        assert "slot_path does not exist" in str(exc_info.value)
    
    def test_validate_invalid_timeout(self, tmp_path):
        """Test validation fails when timeout is invalid."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        
        task_context = TaskContext(
            task_id="1.1",
            spec_name="test-spec",
            title="Test Task",
            description="Test description",
            acceptance_criteria=["Criterion 1"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_dir,
            slot_id="slot-1",
            branch_name="feature/test-branch",
            timeout_seconds=-1,  # Invalid timeout
        )
        
        with pytest.raises(TaskContextValidationError) as exc_info:
            orchestrator._validate_task_context(task_context)
        
        assert "timeout_seconds must be positive" in str(exc_info.value)


class TestStateManagement:
    """Tests for state management."""
    
    def test_initial_state(self, tmp_path):
        """Test initial state is IDLE."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        assert orchestrator.state == RunnerState.IDLE
    
    def test_transition_state(self, tmp_path):
        """Test state transitions."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Transition to RUNNING
        orchestrator._transition_state(RunnerState.RUNNING)
        assert orchestrator.state == RunnerState.RUNNING
        
        # Transition to COMPLETED
        orchestrator._transition_state(RunnerState.COMPLETED)
        assert orchestrator.state == RunnerState.COMPLETED
    
    def test_transition_to_failed(self, tmp_path):
        """Test transition to FAILED state."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        orchestrator._transition_state(RunnerState.RUNNING)
        orchestrator._transition_state(RunnerState.FAILED)
        
        assert orchestrator.state == RunnerState.FAILED
    
    def test_invalid_state_transition(self, tmp_path):
        """Test that invalid state transitions are rejected."""
        from necrocode.agent_runner.exceptions import RunnerError
        
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Cannot transition from IDLE to COMPLETED
        with pytest.raises(RunnerError) as exc_info:
            orchestrator._transition_state(RunnerState.COMPLETED)
        
        assert "Invalid state transition" in str(exc_info.value)
        assert orchestrator.state == RunnerState.IDLE  # State should not change
    
    def test_valid_state_transitions(self, tmp_path):
        """Test all valid state transitions."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # IDLE -> RUNNING
        assert orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.RUNNING)
        
        # RUNNING -> COMPLETED
        assert orchestrator._is_valid_transition(RunnerState.RUNNING, RunnerState.COMPLETED)
        
        # RUNNING -> FAILED
        assert orchestrator._is_valid_transition(RunnerState.RUNNING, RunnerState.FAILED)
        
        # COMPLETED -> IDLE (reset)
        assert orchestrator._is_valid_transition(RunnerState.COMPLETED, RunnerState.IDLE)
        
        # FAILED -> IDLE (reset)
        assert orchestrator._is_valid_transition(RunnerState.FAILED, RunnerState.IDLE)
        
        # Same state (no-op)
        assert orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.IDLE)
    
    def test_invalid_state_transitions(self, tmp_path):
        """Test invalid state transitions are detected."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # IDLE -> COMPLETED (invalid)
        assert not orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.COMPLETED)
        
        # IDLE -> FAILED (invalid)
        assert not orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.FAILED)
        
        # COMPLETED -> RUNNING (invalid)
        assert not orchestrator._is_valid_transition(RunnerState.COMPLETED, RunnerState.RUNNING)
        
        # FAILED -> RUNNING (invalid)
        assert not orchestrator._is_valid_transition(RunnerState.FAILED, RunnerState.RUNNING)


class TestStatePersistence:
    """Tests for state persistence functionality."""
    
    def test_persist_state_with_config(self, tmp_path):
        """Test state persistence when configured."""
        state_file = tmp_path / "state.json"
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts",
            persist_state=True,
            state_file_path=state_file
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Set some state
        orchestrator.current_task_id = "1.1"
        orchestrator.current_spec_name = "test-spec"
        orchestrator.execution_start_time = 1234567890.0
        orchestrator._transition_state(RunnerState.RUNNING)
        
        # State file should be created
        assert state_file.exists()
        
        # Load and verify state
        import json
        with open(state_file) as f:
            data = json.load(f)
        
        assert data["runner_id"] == orchestrator.runner_id
        assert data["state"] == "running"
        assert data["task_id"] == "1.1"
        assert data["spec_name"] == "test-spec"
    
    def test_persist_state_without_config(self, tmp_path):
        """Test state persistence uses default path when not configured."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts",
            persist_state=True
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Transition state to trigger persistence
        orchestrator._transition_state(RunnerState.RUNNING)
        
        # Default state file should be created
        default_state_dir = Path.home() / ".necrocode" / "runner_states"
        default_state_file = default_state_dir / f"{orchestrator.runner_id}.json"
        
        assert default_state_file.exists()
        
        # Cleanup
        default_state_file.unlink()
    
    def test_load_state(self, tmp_path):
        """Test loading state from file."""
        state_file = tmp_path / "state.json"
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts",
            persist_state=True,
            state_file_path=state_file
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Persist state
        orchestrator.current_task_id = "2.1"
        orchestrator.current_spec_name = "my-spec"
        orchestrator._transition_state(RunnerState.RUNNING)
        
        # Load state
        snapshot = orchestrator.load_state(state_file)
        
        assert snapshot is not None
        assert snapshot.runner_id == orchestrator.runner_id
        assert snapshot.state == RunnerState.RUNNING
        assert snapshot.task_id == "2.1"
        assert snapshot.spec_name == "my-spec"
    
    def test_load_nonexistent_state(self, tmp_path):
        """Test loading state when file doesn't exist."""
        state_file = tmp_path / "nonexistent.json"
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        snapshot = orchestrator.load_state(state_file)
        
        assert snapshot is None
    
    def test_clear_state(self, tmp_path):
        """Test clearing persisted state."""
        state_file = tmp_path / "state.json"
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts",
            persist_state=True,
            state_file_path=state_file
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Persist state
        orchestrator._transition_state(RunnerState.RUNNING)
        assert state_file.exists()
        
        # Clear state
        orchestrator.clear_state(state_file)
        assert not state_file.exists()
    
    def test_state_not_persisted_when_disabled(self, tmp_path):
        """Test state is not persisted when persist_state is False."""
        state_file = tmp_path / "state.json"
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts",
            persist_state=False,
            state_file_path=state_file
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        # Transition state
        orchestrator._transition_state(RunnerState.RUNNING)
        
        # State file should not be created
        assert not state_file.exists()


class TestLogging:
    """Tests for logging functionality."""
    
    def test_log_message(self, tmp_path):
        """Test logging messages."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        orchestrator._log("Test message")
        
        assert len(orchestrator.execution_logs) == 1
        assert "Test message" in orchestrator.execution_logs[0]
    
    def test_multiple_log_messages(self, tmp_path):
        """Test logging multiple messages."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        orchestrator._log("Message 1")
        orchestrator._log("Message 2")
        orchestrator._log("Message 3")
        
        assert len(orchestrator.execution_logs) == 3
        assert "Message 1" in orchestrator.execution_logs[0]
        assert "Message 2" in orchestrator.execution_logs[1]
        assert "Message 3" in orchestrator.execution_logs[2]


class TestCommitMessageGeneration:
    """Tests for commit message generation."""
    
    def test_generate_commit_message(self, tmp_path):
        """Test commit message generation."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        
        task_context = TaskContext(
            task_id="1.1",
            spec_name="user-auth",
            title="Implement JWT authentication",
            description="Add JWT auth",
            acceptance_criteria=["Criterion 1"],
            dependencies=[],
            required_skill="backend",
            slot_path=workspace_dir,
            slot_id="slot-1",
            branch_name="feature/test-branch",
        )
        
        message = orchestrator._generate_commit_message(task_context)
        
        assert message == "feat(user-auth): Implement JWT authentication [Task 1.1]"
    
    def test_commit_message_format(self, tmp_path):
        """Test commit message follows correct format."""
        config = RunnerConfig(
            artifact_store_url=f"file://{tmp_path}/artifacts"
        )
        orchestrator = RunnerOrchestrator(config=config)
        
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        
        task_context = TaskContext(
            task_id="2.3",
            spec_name="frontend-ui",
            title="Create login form",
            description="Build login UI",
            acceptance_criteria=["Criterion 1"],
            dependencies=[],
            required_skill="frontend",
            slot_path=workspace_dir,
            slot_id="slot-1",
            branch_name="feature/test-branch",
        )
        
        message = orchestrator._generate_commit_message(task_context)
        
        # Check format: feat(spec): title [Task id]
        assert message.startswith("feat(frontend-ui):")
        assert "Create login form" in message
        assert "[Task 2.3]" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

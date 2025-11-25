"""
Example demonstrating state management in Agent Runner.

This example shows how to:
1. Enable state persistence
2. Track state transitions
3. Load and recover state
4. Handle state validation
"""

from pathlib import Path
from necrocode.agent_runner import (
    RunnerOrchestrator,
    RunnerConfig,
    RunnerState,
    TaskContext,
)


def example_state_persistence():
    """Example of state persistence."""
    print("=== State Persistence Example ===\n")
    
    # Create temporary directory for state file
    state_dir = Path.home() / ".necrocode" / "examples"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "runner_state.json"
    
    # Configure runner with state persistence
    artifact_dir = Path.home() / ".necrocode" / "artifacts"
    config = RunnerConfig(
        persist_state=True,
        state_file_path=state_file,
        artifact_store_url=f"file://{artifact_dir}"
    )
    
    orchestrator = RunnerOrchestrator(config=config)
    print(f"Runner ID: {orchestrator.runner_id}")
    print(f"Initial state: {orchestrator.state.value}")
    print(f"State file: {state_file}\n")
    
    # Simulate task execution with state tracking
    print("Simulating task execution...")
    orchestrator.current_task_id = "1.1"
    orchestrator.current_spec_name = "example-spec"
    orchestrator.execution_start_time = 1234567890.0
    
    # Transition to RUNNING (state will be persisted)
    print("Transitioning to RUNNING state...")
    orchestrator._transition_state(RunnerState.RUNNING)
    print(f"Current state: {orchestrator.state.value}")
    print(f"State persisted to: {state_file}\n")
    
    # Load state from file
    print("Loading state from file...")
    snapshot = orchestrator.load_state(state_file)
    if snapshot:
        print(f"Loaded state:")
        print(f"  Runner ID: {snapshot.runner_id}")
        print(f"  State: {snapshot.state.value}")
        print(f"  Task ID: {snapshot.task_id}")
        print(f"  Spec Name: {snapshot.spec_name}")
        print(f"  Last Updated: {snapshot.last_updated}\n")
    
    # Transition to COMPLETED
    print("Transitioning to COMPLETED state...")
    orchestrator._transition_state(RunnerState.COMPLETED)
    print(f"Current state: {orchestrator.state.value}\n")
    
    # Clear state
    print("Clearing state file...")
    orchestrator.clear_state(state_file)
    print(f"State file cleared: {not state_file.exists()}\n")


def example_state_validation():
    """Example of state transition validation."""
    print("=== State Transition Validation Example ===\n")
    
    artifact_dir = Path.home() / ".necrocode" / "artifacts"
    config = RunnerConfig(
        artifact_store_url=f"file://{artifact_dir}"
    )
    orchestrator = RunnerOrchestrator(config=config)
    
    print(f"Initial state: {orchestrator.state.value}\n")
    
    # Valid transitions
    print("Valid transitions:")
    print(f"  IDLE -> RUNNING: {orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.RUNNING)}")
    print(f"  RUNNING -> COMPLETED: {orchestrator._is_valid_transition(RunnerState.RUNNING, RunnerState.COMPLETED)}")
    print(f"  RUNNING -> FAILED: {orchestrator._is_valid_transition(RunnerState.RUNNING, RunnerState.FAILED)}")
    print(f"  COMPLETED -> IDLE: {orchestrator._is_valid_transition(RunnerState.COMPLETED, RunnerState.IDLE)}")
    print(f"  FAILED -> IDLE: {orchestrator._is_valid_transition(RunnerState.FAILED, RunnerState.IDLE)}\n")
    
    # Invalid transitions
    print("Invalid transitions:")
    print(f"  IDLE -> COMPLETED: {orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.COMPLETED)}")
    print(f"  IDLE -> FAILED: {orchestrator._is_valid_transition(RunnerState.IDLE, RunnerState.FAILED)}")
    print(f"  COMPLETED -> RUNNING: {orchestrator._is_valid_transition(RunnerState.COMPLETED, RunnerState.RUNNING)}")
    print(f"  FAILED -> RUNNING: {orchestrator._is_valid_transition(RunnerState.FAILED, RunnerState.RUNNING)}\n")
    
    # Try valid transition
    print("Performing valid transition: IDLE -> RUNNING")
    orchestrator._transition_state(RunnerState.RUNNING)
    print(f"Current state: {orchestrator.state.value}\n")
    
    # Try invalid transition
    print("Attempting invalid transition: RUNNING -> IDLE")
    try:
        orchestrator._transition_state(RunnerState.IDLE)
        print("Transition succeeded (unexpected!)")
    except Exception as e:
        print(f"Transition rejected: {e}\n")


def example_state_recovery():
    """Example of state recovery after restart."""
    print("=== State Recovery Example ===\n")
    
    state_dir = Path.home() / ".necrocode" / "examples"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "recovery_state.json"
    
    # First runner instance
    print("Creating first runner instance...")
    artifact_dir = Path.home() / ".necrocode" / "artifacts"
    config1 = RunnerConfig(
        persist_state=True,
        state_file_path=state_file,
        artifact_store_url=f"file://{artifact_dir}"
    )
    runner1 = RunnerOrchestrator(config=config1)
    runner1.current_task_id = "2.1"
    runner1.current_spec_name = "recovery-spec"
    runner1._transition_state(RunnerState.RUNNING)
    print(f"Runner 1 ID: {runner1.runner_id}")
    print(f"Runner 1 state: {runner1.state.value}")
    print(f"Task: {runner1.current_task_id}\n")
    
    # Simulate restart - create new runner instance
    print("Simulating restart - creating new runner instance...")
    config2 = RunnerConfig(
        persist_state=True,
        state_file_path=state_file,
        artifact_store_url=f"file://{artifact_dir}"
    )
    runner2 = RunnerOrchestrator(config=config2)
    print(f"Runner 2 ID: {runner2.runner_id}")
    print(f"Runner 2 initial state: {runner2.state.value}\n")
    
    # Load previous state
    print("Loading previous state...")
    snapshot = runner2.load_state(state_file)
    if snapshot:
        print(f"Recovered state:")
        print(f"  Previous Runner ID: {snapshot.runner_id}")
        print(f"  Previous State: {snapshot.state.value}")
        print(f"  Previous Task: {snapshot.task_id}")
        print(f"  Previous Spec: {snapshot.spec_name}\n")
        
        # Could use this information to resume or recover
        print("State recovery successful!")
    
    # Cleanup
    runner2.clear_state(state_file)
    print(f"\nState file cleaned up")


if __name__ == "__main__":
    # Run examples
    example_state_persistence()
    print("\n" + "="*60 + "\n")
    
    example_state_validation()
    print("\n" + "="*60 + "\n")
    
    example_state_recovery()

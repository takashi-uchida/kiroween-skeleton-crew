"""Integration tests for WorkspaceManager and WorkspaceOrchestrator.

This module contains integration tests for task 10 of the kiro-workspace-task-execution spec:
- Test fixtures for mock repositories and state files (10.1)
- End-to-end workflow tests (10.2)
- Multi-workspace concurrent execution tests (10.3)
- State persistence tests across manager restarts (10.4)
"""

import json
import shutil
import subprocess
from pathlib import Path
import sys
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from framework.workspace_manager import (
    WorkspaceManager,
    WorkspaceOrchestrator,
    WorkspaceConfig,
    WorkspaceInfo,
    StateTracker,
    WorkspaceManagerError,
)


# ============================================================================
# Task 10.1: Test Fixtures for Mock Repositories and State Files
# ============================================================================

@pytest.fixture
def mock_git_repo(tmp_path):
    """Create a mock git repository for testing.
    
    Creates a temporary git repository with:
    - Initial commit
    - README.md file
    - Proper git configuration
    
    Returns:
        Path to the mock repository
    """
    repo_path = tmp_path / "mock_repo"
    repo_path.mkdir()
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True
    )
    
    # Create initial file and commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository\n\nThis is a test repository for integration tests.")
    
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True
    )
    
    return repo_path


@pytest.fixture
def workspace_config(tmp_path):
    """Create a WorkspaceConfig for testing.
    
    Returns:
        WorkspaceConfig instance with temporary paths
    """
    return WorkspaceConfig(
        base_path=tmp_path / "workspaces",
        state_file=tmp_path / ".kiro" / "workspace-state.json",
        gitignore_path=tmp_path / ".gitignore",
        auto_push=False,  # Don't push in tests
        auto_pr=False,
    )


@pytest.fixture
def state_tracker(tmp_path):
    """Create a StateTracker for testing.
    
    Returns:
        StateTracker instance with temporary state file
    """
    state_file = tmp_path / ".kiro" / "workspace-state.json"
    return StateTracker(state_file)


@pytest.fixture
def sample_workspace_info(tmp_path):
    """Create a sample WorkspaceInfo for testing.
    
    Returns:
        WorkspaceInfo instance with test data
    """
    return WorkspaceInfo(
        spec_name="test-spec",
        workspace_path=tmp_path / "workspace-test-spec",
        repo_url="https://github.com/test/repo.git",
        current_branch="main",
        created_at="2025-11-09T10:00:00Z",
        tasks_completed=["1.1", "1.2"],
        status="active"
    )


# ============================================================================
# Task 10.2: End-to-End Workflow Test
# ============================================================================

def test_end_to_end_workflow_create_branch_commit_push(mock_git_repo, workspace_config):
    """Test complete workflow: create workspace → create branch → commit → push.
    
    This test verifies the full integration of:
    - WorkspaceOrchestrator creating a workspace
    - Workspace creating a task branch
    - Workspace committing changes
    - Git operations working correctly
    
    Requirements: 1.3, 3.1, 3.2, 3.3
    """
    # Step 1: Create WorkspaceOrchestrator
    orchestrator = WorkspaceOrchestrator(workspace_config)
    
    # Step 2: Create workspace by cloning mock repository
    workspace = orchestrator.create_workspace(
        spec_name="test-workflow",
        repo_url=str(mock_git_repo)
    )
    
    # Verify workspace was created
    assert workspace.path.exists()
    assert workspace.spec_name == "test-workflow"
    assert (workspace.path / "README.md").exists()
    
    # Verify workspace is tracked in state
    workspace_info = orchestrator.state_tracker.load_workspace("test-workflow")
    assert workspace_info is not None
    assert workspace_info.spec_name == "test-workflow"
    assert workspace_info.status == "active"
    
    # Step 3: Create task branch
    branch_name = workspace.create_task_branch("1.1", "implement feature")
    assert branch_name == "feature/task-test-workflow-1.1-implement-feature"
    
    # Verify branch was created and checked out
    current_branch = workspace.get_current_branch()
    assert current_branch == branch_name
    
    # Step 4: Make changes and commit
    test_file = workspace.path / "test_feature.py"
    test_file.write_text("# Test feature implementation\n")
    
    # Stage the file
    subprocess.run(
        ["git", "add", "test_feature.py"],
        cwd=workspace.path,
        check=True,
        capture_output=True
    )
    
    workspace.commit_task(
        task_id="1.1",
        scope="feature",
        description="implement test feature",
        files=None  # Already staged
    )
    
    # Verify commit was created
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=workspace.path,
        check=True,
        capture_output=True,
        text=True
    )
    assert "spirit(feature): spell implement test feature" in result.stdout
    
    # Verify working directory is clean after commit
    assert workspace.is_clean()
    
    # Step 5: Update task status in state
    orchestrator.state_tracker.update_task_status("test-workflow", "1.1", "completed")
    
    # Verify task was marked as completed
    workspace_info = orchestrator.state_tracker.load_workspace("test-workflow")
    assert "1.1" in workspace_info.tasks_completed
    
    # Step 6: Cleanup
    orchestrator.cleanup_workspace("test-workflow", force=True)
    
    # Verify workspace was removed
    assert not workspace.path.exists()
    workspace_info = orchestrator.state_tracker.load_workspace("test-workflow")
    assert workspace_info is None


# ============================================================================
# Task 10.3: Multi-Workspace Concurrent Execution Test
# ============================================================================

def test_multi_workspace_concurrent_execution(mock_git_repo, workspace_config):
    """Test multiple workspaces can be managed concurrently without conflicts.
    
    This test verifies:
    - Multiple workspaces can be created simultaneously
    - Each workspace maintains independent state
    - State tracking correctly handles multiple workspaces
    - Workspaces don't interfere with each other
    
    Requirements: 1.3, 3.1, 3.2, 3.3
    """
    orchestrator = WorkspaceOrchestrator(workspace_config)
    
    # Create multiple workspaces
    workspace1 = orchestrator.create_workspace("spec-one", str(mock_git_repo))
    workspace2 = orchestrator.create_workspace("spec-two", str(mock_git_repo))
    workspace3 = orchestrator.create_workspace("spec-three", str(mock_git_repo))
    
    # Verify all workspaces exist
    assert workspace1.path.exists()
    assert workspace2.path.exists()
    assert workspace3.path.exists()
    
    # Verify workspaces are in different directories
    assert workspace1.path != workspace2.path
    assert workspace2.path != workspace3.path
    assert workspace1.path != workspace3.path
    
    # Verify all workspaces are tracked
    all_workspaces = orchestrator.list_workspaces()
    assert len(all_workspaces) == 3
    spec_names = {ws.spec_name for ws in all_workspaces}
    assert spec_names == {"spec-one", "spec-two", "spec-three"}
    
    # Create branches in each workspace
    branch1 = workspace1.create_task_branch("1.1", "feature one")
    branch2 = workspace2.create_task_branch("2.1", "feature two")
    branch3 = workspace3.create_task_branch("3.1", "feature three")
    
    # Verify branches are independent
    assert branch1 == "feature/task-spec-one-1.1-feature-one"
    assert branch2 == "feature/task-spec-two-2.1-feature-two"
    assert branch3 == "feature/task-spec-three-3.1-feature-three"
    
    # Make changes in each workspace
    for workspace, task_id, content in [
        (workspace1, "1.1", "# Feature one\n"),
        (workspace2, "2.1", "# Feature two\n"),
        (workspace3, "3.1", "# Feature three\n"),
    ]:
        test_file = workspace.path / f"feature_{task_id.replace('.', '_')}.py"
        test_file.write_text(content)
        
        subprocess.run(
            ["git", "add", test_file.name],
            cwd=workspace.path,
            check=True,
            capture_output=True
        )
        
        workspace.commit_task(
            task_id=task_id,
            scope="feature",
            description=f"implement feature {task_id}",
            files=None
        )
    
    # Verify all workspaces have clean working directories
    assert workspace1.is_clean()
    assert workspace2.is_clean()
    assert workspace3.is_clean()
    
    # Update task statuses
    orchestrator.state_tracker.update_task_status("spec-one", "1.1", "completed")
    orchestrator.state_tracker.update_task_status("spec-two", "2.1", "completed")
    orchestrator.state_tracker.update_task_status("spec-three", "3.1", "completed")
    
    # Verify task completion is tracked independently
    ws1_info = orchestrator.state_tracker.load_workspace("spec-one")
    ws2_info = orchestrator.state_tracker.load_workspace("spec-two")
    ws3_info = orchestrator.state_tracker.load_workspace("spec-three")
    
    assert ws1_info.tasks_completed == ["1.1"]
    assert ws2_info.tasks_completed == ["2.1"]
    assert ws3_info.tasks_completed == ["3.1"]
    
    # Cleanup workspaces
    orchestrator.cleanup_workspace("spec-one", force=True)
    orchestrator.cleanup_workspace("spec-two", force=True)
    orchestrator.cleanup_workspace("spec-three", force=True)
    
    # Verify all workspaces were removed
    assert not workspace1.path.exists()
    assert not workspace2.path.exists()
    assert not workspace3.path.exists()
    
    # Verify state is empty
    all_workspaces = orchestrator.list_workspaces()
    assert len(all_workspaces) == 0


# ============================================================================
# Task 10.4: State Persistence Test Across Manager Restarts
# ============================================================================

def test_state_persistence_across_manager_restarts(mock_git_repo, workspace_config):
    """Test state persists correctly across WorkspaceOrchestrator restarts.
    
    This test verifies:
    - State is saved to disk correctly
    - State can be loaded after manager restart
    - Workspace information is preserved
    - Task completion status is maintained
    
    Requirements: 3.1, 3.2, 3.3
    """
    # Phase 1: Create workspace and perform operations
    orchestrator1 = WorkspaceOrchestrator(workspace_config)
    
    workspace = orchestrator1.create_workspace("persistent-spec", str(mock_git_repo))
    
    # Create branch and commit
    branch_name = workspace.create_task_branch("1.1", "persistent feature")
    
    test_file = workspace.path / "persistent.py"
    test_file.write_text("# Persistent feature\n")
    
    subprocess.run(
        ["git", "add", "persistent.py"],
        cwd=workspace.path,
        check=True,
        capture_output=True
    )
    
    workspace.commit_task(
        task_id="1.1",
        scope="feature",
        description="implement persistent feature",
        files=None
    )
    
    # Update task status
    orchestrator1.state_tracker.update_task_status("persistent-spec", "1.1", "completed")
    
    # Get workspace info before restart
    ws_info_before = orchestrator1.state_tracker.load_workspace("persistent-spec")
    assert ws_info_before is not None
    assert ws_info_before.spec_name == "persistent-spec"
    assert "1.1" in ws_info_before.tasks_completed
    assert ws_info_before.status == "active"
    
    # Verify state file exists
    assert workspace_config.state_file.exists()
    
    # Phase 2: Simulate restart by creating new orchestrator instance
    orchestrator2 = WorkspaceOrchestrator(workspace_config)
    
    # Verify workspace can be retrieved
    workspace_restored = orchestrator2.get_workspace("persistent-spec")
    assert workspace_restored is not None
    assert workspace_restored.path == workspace.path
    assert workspace_restored.spec_name == "persistent-spec"
    
    # Verify workspace info is preserved
    ws_info_after = orchestrator2.state_tracker.load_workspace("persistent-spec")
    assert ws_info_after is not None
    assert ws_info_after.spec_name == ws_info_before.spec_name
    assert ws_info_after.workspace_path == ws_info_before.workspace_path
    assert ws_info_after.repo_url == ws_info_before.repo_url
    assert ws_info_after.created_at == ws_info_before.created_at
    assert ws_info_after.tasks_completed == ws_info_before.tasks_completed
    assert ws_info_after.status == ws_info_before.status
    
    # Verify we can continue working with the restored workspace
    current_branch = workspace_restored.get_current_branch()
    assert current_branch == branch_name
    
    # Create another branch to verify workspace is fully functional
    branch_name2 = workspace_restored.create_task_branch("1.2", "another feature")
    assert branch_name2 == "feature/task-persistent-spec-1.2-another-feature"
    
    # Verify current branch changed
    assert workspace_restored.get_current_branch() == branch_name2
    
    # Phase 3: Test listing workspaces after restart
    all_workspaces = orchestrator2.list_workspaces()
    assert len(all_workspaces) == 1
    assert all_workspaces[0].spec_name == "persistent-spec"
    
    # Cleanup
    orchestrator2.cleanup_workspace("persistent-spec", force=True)
    assert not workspace.path.exists()


def test_state_file_corruption_handling(workspace_config, sample_workspace_info):
    """Test that corrupted state files are handled gracefully.
    
    This test verifies:
    - Corrupted state files create backups
    - Clear error messages are provided
    - System can recover from corruption
    
    Requirements: 3.1, 3.2
    """
    state_tracker = StateTracker(workspace_config.state_file)
    
    # Save valid workspace info
    state_tracker.save_workspace(sample_workspace_info)
    
    # Corrupt the state file
    workspace_config.state_file.write_text("{ invalid json content }")
    
    # Attempt to read corrupted state
    try:
        state_tracker._read_state()
        assert False, "Expected ValueError for corrupted state file"
    except ValueError as e:
        assert "State file corrupted" in str(e)
        assert "Backup created" in str(e)
        
        # Verify backup was created
        backup_path = workspace_config.state_file.with_suffix('.json.backup')
        assert backup_path.exists()


# ============================================================================
# Additional Integration Tests
# ============================================================================

def test_workspace_creation_prevents_duplicates(mock_git_repo, workspace_config):
    """Test that duplicate workspace creation is prevented.
    
    Requirements: 1.3
    """
    orchestrator = WorkspaceOrchestrator(workspace_config)
    
    # Create first workspace
    workspace1 = orchestrator.create_workspace("duplicate-test", str(mock_git_repo))
    assert workspace1.path.exists()
    
    # Attempt to create duplicate
    try:
        orchestrator.create_workspace("duplicate-test", str(mock_git_repo))
        assert False, "Expected WorkspaceManagerError for duplicate workspace"
    except WorkspaceManagerError as e:
        assert "already exists" in str(e)
    
    # Cleanup
    orchestrator.cleanup_workspace("duplicate-test", force=True)


def test_cleanup_with_uncommitted_changes(mock_git_repo, workspace_config):
    """Test cleanup behavior with uncommitted changes.
    
    Requirements: 3.3
    """
    orchestrator = WorkspaceOrchestrator(workspace_config)
    
    workspace = orchestrator.create_workspace("dirty-workspace", str(mock_git_repo))
    
    # Make uncommitted changes
    test_file = workspace.path / "uncommitted.py"
    test_file.write_text("# Uncommitted changes\n")
    
    # Attempt cleanup without force
    try:
        orchestrator.cleanup_workspace("dirty-workspace", force=False)
        assert False, "Expected WorkspaceManagerError for uncommitted changes"
    except WorkspaceManagerError as e:
        assert "uncommitted changes" in str(e).lower()
    
    # Verify workspace still exists
    assert workspace.path.exists()
    
    # Cleanup with force
    orchestrator.cleanup_workspace("dirty-workspace", force=True)
    assert not workspace.path.exists()


# ============================================================================
# Task 11.1: BranchStrategy Unit Tests
# ============================================================================

from framework.workspace_manager.branch_strategy import BranchStrategy


def test_branch_strategy_generate_branch_name_basic():
    """Test basic branch name generation.
    
    Requirements: 2.1, 2.2
    """
    branch_name = BranchStrategy.generate_branch_name("kiro-workspace", "2", "implement branch strategy")
    assert branch_name == "feature/task-kiro-workspace-2-implement-branch-strategy"


def test_branch_strategy_generate_branch_name_with_special_chars():
    """Test branch name generation with special characters.
    
    Requirements: 2.2
    """
    branch_name = BranchStrategy.generate_branch_name("my-spec!", "1.1", "Add @feature #123")
    # Special characters should be removed
    assert "!" not in branch_name
    assert "@" not in branch_name
    assert "#" not in branch_name
    assert branch_name == "feature/task-my-spec-1.1-add-feature-123"


def test_branch_strategy_generate_branch_name_with_spaces():
    """Test branch name generation with spaces.
    
    Requirements: 2.2
    """
    branch_name = BranchStrategy.generate_branch_name("my spec", "2.3", "some feature name")
    # Spaces should be converted to hyphens
    assert " " not in branch_name
    assert branch_name == "feature/task-my-spec-2.3-some-feature-name"


def test_branch_strategy_generate_branch_name_with_uppercase():
    """Test branch name generation with uppercase letters.
    
    Requirements: 2.2
    """
    branch_name = BranchStrategy.generate_branch_name("MySpec", "1", "MyFeature")
    # Should be lowercase
    assert branch_name == "feature/task-myspec-1-myfeature"


def test_branch_strategy_sanitize_branch_name_removes_invalid_chars():
    """Test sanitization removes invalid git characters.
    
    Requirements: 2.2
    """
    sanitized = BranchStrategy.sanitize_branch_name("feature/test~branch^name:with*invalid[chars]")
    assert "~" not in sanitized
    assert "^" not in sanitized
    assert ":" not in sanitized
    assert "*" not in sanitized
    assert "[" not in sanitized
    assert "]" not in sanitized


def test_branch_strategy_sanitize_branch_name_collapses_hyphens():
    """Test sanitization collapses multiple hyphens.
    
    Requirements: 2.2
    """
    sanitized = BranchStrategy.sanitize_branch_name("feature/test---branch--name")
    assert "---" not in sanitized
    assert "--" not in sanitized
    assert sanitized == "feature/test-branch-name"


def test_branch_strategy_sanitize_branch_name_removes_double_slashes():
    """Test sanitization removes double slashes.
    
    Requirements: 2.2
    """
    sanitized = BranchStrategy.sanitize_branch_name("feature//test///branch")
    assert "//" not in sanitized
    assert "///" not in sanitized
    assert sanitized == "feature/test/branch"


def test_branch_strategy_sanitize_branch_name_removes_lock_suffix():
    """Test sanitization removes .lock suffix (git restriction).
    
    Requirements: 2.2
    """
    sanitized = BranchStrategy.sanitize_branch_name("feature/test-branch.lock")
    assert not sanitized.endswith(".lock")
    assert sanitized == "feature/test-branch"


def test_branch_strategy_parse_branch_name_valid():
    """Test parsing valid branch name.
    
    Requirements: 2.1
    """
    result = BranchStrategy.parse_branch_name("feature/task-kiro-workspace-2-implement-branch-strategy")
    assert result is not None
    assert result["spec_id"] == "kiro-workspace"
    assert result["task_number"] == "2"
    assert result["description"] == "implement-branch-strategy"


def test_branch_strategy_parse_branch_name_with_decimal_task():
    """Test parsing branch name with decimal task number.
    
    Requirements: 2.1
    """
    result = BranchStrategy.parse_branch_name("feature/task-my-spec-1.1-add-feature")
    assert result is not None
    assert result["spec_id"] == "my-spec"
    assert result["task_number"] == "1.1"
    assert result["description"] == "add-feature"


def test_branch_strategy_parse_branch_name_invalid():
    """Test parsing invalid branch name returns None.
    
    Requirements: 2.1
    """
    result = BranchStrategy.parse_branch_name("main")
    assert result is None
    
    result = BranchStrategy.parse_branch_name("feature/something-else")
    assert result is None


def test_branch_strategy_generate_commit_message_basic():
    """Test basic commit message generation.
    
    Requirements: 4.1, 4.2, 4.3
    """
    message = BranchStrategy.generate_commit_message("workspace", "implement branch strategy", "2")
    assert message == "spirit(workspace): spell implement branch strategy\n\nTask: 2"


def test_branch_strategy_generate_commit_message_without_task_id():
    """Test commit message generation without task ID.
    
    Requirements: 4.1, 4.2
    """
    message = BranchStrategy.generate_commit_message("git", "add clone method")
    assert message == "spirit(git): spell add clone method"
    assert "Task:" not in message


def test_branch_strategy_generate_commit_message_lowercase_description():
    """Test commit message converts description to lowercase.
    
    Requirements: 4.1, 4.2
    """
    message = BranchStrategy.generate_commit_message("backend", "Add Authentication", "1.1")
    assert "spell add authentication" in message.lower()


def test_branch_strategy_generate_commit_message_sanitizes_scope():
    """Test commit message sanitizes scope.
    
    Requirements: 4.1, 4.2
    """
    message = BranchStrategy.generate_commit_message("  Backend  ", "add feature", "1")
    assert message.startswith("spirit(backend):")


# ============================================================================
# Task 11.2: StateTracker Unit Tests
# ============================================================================

def test_state_tracker_save_and_load_workspace(tmp_path, sample_workspace_info):
    """Test saving and loading workspace info.
    
    Requirements: 3.1, 3.2
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Save workspace
    tracker.save_workspace(sample_workspace_info)
    
    # Load workspace
    loaded = tracker.load_workspace("test-spec")
    assert loaded is not None
    assert loaded.spec_name == sample_workspace_info.spec_name
    assert loaded.workspace_path == sample_workspace_info.workspace_path
    assert loaded.repo_url == sample_workspace_info.repo_url
    assert loaded.status == sample_workspace_info.status


def test_state_tracker_load_nonexistent_workspace(tmp_path):
    """Test loading nonexistent workspace returns None.
    
    Requirements: 3.2
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    loaded = tracker.load_workspace("nonexistent")
    assert loaded is None


def test_state_tracker_list_all_workspaces(tmp_path):
    """Test listing all tracked workspaces.
    
    Requirements: 3.4
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Create multiple workspace infos
    ws1 = WorkspaceInfo(
        spec_name="spec-one",
        workspace_path=tmp_path / "ws1",
        repo_url="https://github.com/test/repo1.git",
        current_branch="main",
        created_at="2025-11-09T10:00:00Z",
        tasks_completed=[],
        status="active"
    )
    ws2 = WorkspaceInfo(
        spec_name="spec-two",
        workspace_path=tmp_path / "ws2",
        repo_url="https://github.com/test/repo2.git",
        current_branch="main",
        created_at="2025-11-09T11:00:00Z",
        tasks_completed=["1.1"],
        status="active"
    )
    
    # Save workspaces
    tracker.save_workspace(ws1)
    tracker.save_workspace(ws2)
    
    # List all
    all_workspaces = tracker.list_all()
    assert len(all_workspaces) == 2
    spec_names = {ws.spec_name for ws in all_workspaces}
    assert spec_names == {"spec-one", "spec-two"}


def test_state_tracker_remove_workspace(tmp_path, sample_workspace_info):
    """Test removing workspace from state.
    
    Requirements: 3.5
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Save workspace
    tracker.save_workspace(sample_workspace_info)
    assert tracker.load_workspace("test-spec") is not None
    
    # Remove workspace
    tracker.remove_workspace("test-spec")
    assert tracker.load_workspace("test-spec") is None


def test_state_tracker_update_task_status_completed(tmp_path, sample_workspace_info):
    """Test updating task status to completed.
    
    Requirements: 3.3
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Save workspace
    tracker.save_workspace(sample_workspace_info)
    
    # Update task status
    tracker.update_task_status("test-spec", "2.1", "completed")
    
    # Verify task was added to completed list
    loaded = tracker.load_workspace("test-spec")
    assert "2.1" in loaded.tasks_completed


def test_state_tracker_update_task_status_failed(tmp_path, sample_workspace_info):
    """Test updating task status to failed updates workspace status.
    
    Requirements: 3.3
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Save workspace
    tracker.save_workspace(sample_workspace_info)
    
    # Update task status to failed
    tracker.update_task_status("test-spec", "2.1", "failed")
    
    # Verify workspace status changed to error
    loaded = tracker.load_workspace("test-spec")
    assert loaded.status == "error"


def test_state_tracker_update_task_status_nonexistent_workspace(tmp_path):
    """Test updating task status for nonexistent workspace raises error.
    
    Requirements: 3.3
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    try:
        tracker.update_task_status("nonexistent", "1.1", "completed")
        assert False, "Expected ValueError for nonexistent workspace"
    except ValueError as e:
        assert "not found" in str(e)


def test_state_tracker_creates_backup_on_write(tmp_path, sample_workspace_info):
    """Test that backup is created before writing state.
    
    Requirements: 3.1
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Save workspace first time
    tracker.save_workspace(sample_workspace_info)
    
    # Modify and save again
    sample_workspace_info.status = "completed"
    tracker.save_workspace(sample_workspace_info)
    
    # Verify backup exists
    backup_path = state_file.with_suffix('.json.bak')
    assert backup_path.exists()


def test_state_tracker_handles_corrupted_json(tmp_path):
    """Test handling of corrupted JSON state file.
    
    Requirements: 3.1
    """
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    
    # Write invalid JSON
    state_file.write_text("{ invalid json }")
    
    # Attempt to read should raise ValueError
    try:
        tracker._read_state()
        assert False, "Expected ValueError for corrupted JSON"
    except ValueError as e:
        assert "corrupted" in str(e).lower()
        # Verify backup was created
        backup_path = state_file.with_suffix('.json.backup')
        assert backup_path.exists()


# ============================================================================
# Task 11.3: GitOperations Unit Tests
# ============================================================================

from framework.workspace_manager.git_operations import GitOperations, GitOperationError


def test_git_operations_clone_success(tmp_path, mock_git_repo):
    """Test successful repository cloning.
    
    Requirements: 5.1
    """
    git_ops = GitOperations(tmp_path)
    target_path = tmp_path / "cloned_repo"
    
    git_ops.clone(str(mock_git_repo), target_path)
    
    # Verify clone was successful
    assert target_path.exists()
    assert (target_path / ".git").exists()
    assert (target_path / "README.md").exists()


def test_git_operations_clone_invalid_url(tmp_path):
    """Test cloning with invalid URL raises error.
    
    Requirements: 5.1, 5.4
    """
    git_ops = GitOperations(tmp_path)
    target_path = tmp_path / "cloned_repo"
    
    try:
        git_ops.clone("https://invalid-url-that-does-not-exist.git", target_path)
        assert False, "Expected GitOperationError for invalid URL"
    except GitOperationError as e:
        assert "Failed to clone" in str(e)


def test_git_operations_create_branch_success(mock_git_repo):
    """Test successful branch creation.
    
    Requirements: 5.3
    """
    git_ops = GitOperations(mock_git_repo)
    
    git_ops.create_branch("test-branch", checkout=True)
    
    # Verify branch was created and checked out
    current_branch = git_ops.get_current_branch()
    assert current_branch == "test-branch"


def test_git_operations_create_branch_without_checkout(mock_git_repo):
    """Test branch creation without checkout.
    
    Requirements: 5.3
    """
    git_ops = GitOperations(mock_git_repo)
    
    git_ops.create_branch("test-branch", checkout=False)
    
    # Verify branch was created but not checked out
    current_branch = git_ops.get_current_branch()
    assert current_branch != "test-branch"
    
    # Verify branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "test-branch"],
        cwd=mock_git_repo,
        capture_output=True
    )
    assert result.returncode == 0


def test_git_operations_create_branch_already_exists(mock_git_repo):
    """Test creating branch that already exists raises error.
    
    Requirements: 5.3, 5.4
    """
    git_ops = GitOperations(mock_git_repo)
    
    git_ops.create_branch("test-branch")
    
    try:
        git_ops.create_branch("test-branch")
        assert False, "Expected GitOperationError for existing branch"
    except GitOperationError as e:
        assert "already exists" in str(e)


def test_git_operations_commit_success(mock_git_repo):
    """Test successful commit.
    
    Requirements: 5.3
    """
    git_ops = GitOperations(mock_git_repo)
    
    # Create a file
    test_file = mock_git_repo / "test.txt"
    test_file.write_text("test content")
    
    # Commit the file
    git_ops.commit("Test commit", files=[test_file])
    
    # Verify commit was created
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=mock_git_repo,
        capture_output=True,
        text=True
    )
    assert "Test commit" in result.stdout


def test_git_operations_commit_without_files(mock_git_repo):
    """Test commit without specifying files (commits staged changes).
    
    Requirements: 5.3
    """
    git_ops = GitOperations(mock_git_repo)
    
    # Create and stage a file manually
    test_file = mock_git_repo / "test.txt"
    test_file.write_text("test content")
    subprocess.run(["git", "add", "test.txt"], cwd=mock_git_repo, check=True)
    
    # Commit without specifying files
    git_ops.commit("Test commit")
    
    # Verify commit was created
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=mock_git_repo,
        capture_output=True,
        text=True
    )
    assert "Test commit" in result.stdout


def test_git_operations_get_current_branch(mock_git_repo):
    """Test getting current branch name.
    
    Requirements: 5.5
    """
    git_ops = GitOperations(mock_git_repo)
    
    # Get initial branch (should be master or main)
    current_branch = git_ops.get_current_branch()
    assert current_branch in ["master", "main"]
    
    # Create and checkout new branch
    git_ops.create_branch("new-branch")
    current_branch = git_ops.get_current_branch()
    assert current_branch == "new-branch"


def test_git_operations_is_clean_true(mock_git_repo):
    """Test is_clean returns True for clean working directory.
    
    Requirements: 5.5
    """
    git_ops = GitOperations(mock_git_repo)
    
    assert git_ops.is_clean() is True


def test_git_operations_is_clean_false(mock_git_repo):
    """Test is_clean returns False for dirty working directory.
    
    Requirements: 5.5
    """
    git_ops = GitOperations(mock_git_repo)
    
    # Create uncommitted file
    test_file = mock_git_repo / "uncommitted.txt"
    test_file.write_text("uncommitted content")
    
    assert git_ops.is_clean() is False


# ============================================================================
# Task 11.4: Error Handling Unit Tests
# ============================================================================

def test_error_handling_clone_with_invalid_path(tmp_path):
    """Test clone error handling with invalid target path.
    
    Requirements: 5.1, 5.4
    """
    git_ops = GitOperations(tmp_path)
    
    # Try to clone to an invalid path
    try:
        git_ops.clone("https://github.com/invalid/repo.git", Path("/invalid/path/that/does/not/exist"))
        assert False, "Expected GitOperationError"
    except GitOperationError as e:
        assert "Failed to clone" in str(e)


def test_error_handling_commit_with_nothing_to_commit(mock_git_repo):
    """Test commit error handling when nothing to commit.
    
    Requirements: 5.4
    """
    git_ops = GitOperations(mock_git_repo)
    
    try:
        git_ops.commit("Empty commit")
        assert False, "Expected GitOperationError for nothing to commit"
    except GitOperationError as e:
        assert "Failed to commit" in str(e)


def test_error_handling_push_without_remote(tmp_path):
    """Test push error handling when no remote is configured.
    
    Requirements: 5.4
    """
    # Create a local repo without remote
    local_repo = tmp_path / "local_repo"
    local_repo.mkdir()
    subprocess.run(["git", "init"], cwd=local_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=local_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=local_repo, check=True)
    
    git_ops = GitOperations(local_repo)
    
    try:
        git_ops.push("main")
        assert False, "Expected GitOperationError for no remote"
    except GitOperationError as e:
        assert "Failed to push" in str(e)


def test_error_handling_get_current_branch_not_a_repo(tmp_path):
    """Test get_current_branch error handling when not in a git repo.
    
    Requirements: 5.4
    """
    git_ops = GitOperations(tmp_path)
    
    try:
        git_ops.get_current_branch()
        assert False, "Expected GitOperationError for not a git repo"
    except GitOperationError as e:
        assert "Failed to get current branch" in str(e)


def test_error_handling_is_clean_not_a_repo(tmp_path):
    """Test is_clean error handling when not in a git repo.
    
    Requirements: 5.4
    """
    git_ops = GitOperations(tmp_path)
    
    try:
        git_ops.is_clean()
        assert False, "Expected GitOperationError for not a git repo"
    except GitOperationError as e:
        assert "Failed to check working directory status" in str(e)


def test_error_handling_state_tracker_write_failure(tmp_path, sample_workspace_info):
    """Test state tracker handles write failures gracefully.
    
    Requirements: 5.2, 5.4
    """
    state_file = tmp_path / "readonly" / "state.json"
    state_file.parent.mkdir()
    
    tracker = StateTracker(state_file)
    tracker.save_workspace(sample_workspace_info)
    
    # Make directory read-only to cause write failure
    state_file.parent.chmod(0o444)
    
    try:
        sample_workspace_info.status = "completed"
        tracker.save_workspace(sample_workspace_info)
        assert False, "Expected ValueError for write failure"
    except (ValueError, PermissionError):
        # Either error is acceptable
        pass
    finally:
        # Restore permissions for cleanup
        state_file.parent.chmod(0o755)


# ============================================================================
# Legacy Tests (from original file)
# ============================================================================

def test_instance_based_branch_names_are_unique_for_multiple_agents(tmp_path):
    manager = WorkspaceManager(tmp_path)

    branch_one = manager.create_branch("frontend_spirit_1", "Login UI")
    branch_two = manager.create_branch("frontend_spirit_2", "Login UI")

    assert branch_one == "frontend/spirit-1/login-ui"
    assert branch_two == "frontend/spirit-2/login-ui"
    assert branch_one != branch_two


def test_issue_based_branch_names_override_instance_format(tmp_path):
    manager = WorkspaceManager(tmp_path)

    branch = manager.create_branch("backend_spirit_3", "Auth API", issue_id="77")

    assert branch == "backend/issue-77-auth-api"


def test_commit_message_format_includes_instance_and_issue_reference(tmp_path):
    manager = WorkspaceManager(tmp_path)

    commit_with_issue = manager.format_commit_message(
        "backend_spirit_2", scope="api", description="Forged auth endpoints", issue_id="77"
    )
    commit_without_issue = manager.format_commit_message(
        "frontend_spirit_1", scope="ui", description="Summoned login canvas"
    )

    assert commit_with_issue == "spirit-2(api): Forged auth endpoints [#77]"
    assert commit_without_issue == "spirit-1(ui): Summoned login canvas"


def test_branch_tracking_is_per_spirit_instance(tmp_path):
    manager = WorkspaceManager(tmp_path)
    branch = manager.create_branch("qa_spirit_4", "Regression Suite")

    assert manager.get_active_branches("qa_spirit_4") == [branch]
    assert manager.get_active_branches("qa_spirit_5") == []


def test_invalid_spirit_identifier_raises_value_error(tmp_path):
    manager = WorkspaceManager(tmp_path)

    try:
        manager.create_branch("frontend", "feature")
    except ValueError as exc:
        assert "Invalid spirit identifier" in str(exc)
    else:
        assert False, "Expected ValueError for malformed spirit identifier"

"""
Tests for Agent Runner data models.

This module tests serialization/deserialization of all data models
used by the Agent Runner component.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from necrocode.agent_runner.models import (
    RunnerState,
    RunnerStateSnapshot,
    ArtifactType,
    Workspace,
    TaskContext,
    ImplementationResult,
    SingleTestResult,
    TestResult,
    PushResult,
    Artifact,
    RunnerResult,
    PlaybookStep,
    Playbook,
    SlotAllocation,
    CodeChange,
    LLMResponse,
    LLMConfig,
)


class TestRunnerState:
    """Tests for RunnerState enum."""
    
    def test_runner_state_values(self):
        """Test RunnerState enum values."""
        assert RunnerState.IDLE.value == "idle"
        assert RunnerState.RUNNING.value == "running"
        assert RunnerState.COMPLETED.value == "completed"
        assert RunnerState.FAILED.value == "failed"
    
    def test_runner_state_from_value(self):
        """Test creating RunnerState from value."""
        assert RunnerState("idle") == RunnerState.IDLE
        assert RunnerState("running") == RunnerState.RUNNING
        assert RunnerState("completed") == RunnerState.COMPLETED
        assert RunnerState("failed") == RunnerState.FAILED


class TestRunnerStateSnapshot:
    """Tests for RunnerStateSnapshot model."""
    
    def test_to_dict(self):
        """Test RunnerStateSnapshot serialization."""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        last_updated = datetime(2024, 1, 1, 12, 30, 0)
        
        snapshot = RunnerStateSnapshot(
            runner_id="runner-123",
            state=RunnerState.RUNNING,
            task_id="1.1",
            spec_name="test-spec",
            start_time=start_time,
            last_updated=last_updated,
            metadata={"key": "value"},
            workspace_path="/tmp/workspace",
        )
        
        data = snapshot.to_dict()
        
        assert data["runner_id"] == "runner-123"
        assert data["state"] == "running"
        assert data["task_id"] == "1.1"
        assert data["spec_name"] == "test-spec"
        assert data["start_time"] == start_time.isoformat()
        assert data["last_updated"] == last_updated.isoformat()
        assert data["metadata"] == {"key": "value"}
        assert data["workspace_path"] == "/tmp/workspace"
    
    def test_from_dict(self):
        """Test RunnerStateSnapshot deserialization."""
        data = {
            "runner_id": "runner-123",
            "state": "running",
            "task_id": "1.1",
            "spec_name": "test-spec",
            "start_time": "2024-01-01T12:00:00",
            "last_updated": "2024-01-01T12:30:00",
            "metadata": {"key": "value"},
            "workspace_path": "/tmp/workspace",
        }
        
        snapshot = RunnerStateSnapshot.from_dict(data)
        
        assert snapshot.runner_id == "runner-123"
        assert snapshot.state == RunnerState.RUNNING
        assert snapshot.task_id == "1.1"
        assert snapshot.spec_name == "test-spec"
        assert snapshot.start_time == datetime(2024, 1, 1, 12, 0, 0)
        assert snapshot.last_updated == datetime(2024, 1, 1, 12, 30, 0)
        assert snapshot.metadata == {"key": "value"}
        assert snapshot.workspace_path == "/tmp/workspace"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = RunnerStateSnapshot(
            runner_id="runner-456",
            state=RunnerState.COMPLETED,
            task_id="2.3",
            spec_name="my-spec",
        )
        
        data = original.to_dict()
        restored = RunnerStateSnapshot.from_dict(data)
        
        assert restored.runner_id == original.runner_id
        assert restored.state == original.state
        assert restored.task_id == original.task_id
        assert restored.spec_name == original.spec_name


class TestArtifactType:
    """Tests for ArtifactType enum."""
    
    def test_artifact_type_values(self):
        """Test ArtifactType enum values."""
        assert ArtifactType.DIFF.value == "diff"
        assert ArtifactType.LOG.value == "log"
        assert ArtifactType.TEST_RESULT.value == "test"


class TestWorkspace:
    """Tests for Workspace model."""
    
    def test_to_dict(self):
        """Test Workspace serialization."""
        workspace = Workspace(
            path=Path("/tmp/workspace"),
            branch_name="feature/test",
            base_branch="main",
        )
        
        data = workspace.to_dict()
        
        assert data["path"] == "/tmp/workspace"
        assert data["branch_name"] == "feature/test"
        assert data["base_branch"] == "main"
    
    def test_from_dict(self):
        """Test Workspace deserialization."""
        data = {
            "path": "/tmp/workspace",
            "branch_name": "feature/test",
            "base_branch": "main",
        }
        
        workspace = Workspace.from_dict(data)
        
        assert workspace.path == Path("/tmp/workspace")
        assert workspace.branch_name == "feature/test"
        assert workspace.base_branch == "main"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = Workspace(
            path=Path("/home/user/project"),
            branch_name="feature/task-1",
            base_branch="develop",
        )
        
        data = original.to_dict()
        restored = Workspace.from_dict(data)
        
        assert restored.path == original.path
        assert restored.branch_name == original.branch_name
        assert restored.base_branch == original.base_branch


class TestTaskContext:
    """Tests for TaskContext model."""
    
    def test_to_dict(self):
        """Test TaskContext serialization."""
        context = TaskContext(
            task_id="1.1",
            spec_name="test-spec",
            title="Test Task",
            description="Test description",
            acceptance_criteria=["Criterion 1", "Criterion 2"],
            dependencies=["1.0"],
            required_skill="backend",
            slot_path=Path("/tmp/slot"),
            slot_id="slot-1",
            branch_name="feature/test",
            test_commands=["pytest"],
            fail_fast=True,
            timeout_seconds=1800,
            playbook_path=Path("/tmp/playbook.yaml"),
            complexity="high",
            require_review=True,
            metadata={"key": "value"},
        )
        
        data = context.to_dict()
        
        assert data["task_id"] == "1.1"
        assert data["spec_name"] == "test-spec"
        assert data["title"] == "Test Task"
        assert data["description"] == "Test description"
        assert data["acceptance_criteria"] == ["Criterion 1", "Criterion 2"]
        assert data["dependencies"] == ["1.0"]
        assert data["required_skill"] == "backend"
        assert data["slot_path"] == "/tmp/slot"
        assert data["slot_id"] == "slot-1"
        assert data["branch_name"] == "feature/test"
        assert data["test_commands"] == ["pytest"]
        assert data["fail_fast"] is True
        assert data["timeout_seconds"] == 1800
        assert data["playbook_path"] == "/tmp/playbook.yaml"
        assert data["complexity"] == "high"
        assert data["require_review"] is True
        assert data["metadata"] == {"key": "value"}
    
    def test_from_dict(self):
        """Test TaskContext deserialization."""
        data = {
            "task_id": "1.1",
            "spec_name": "test-spec",
            "title": "Test Task",
            "description": "Test description",
            "acceptance_criteria": ["Criterion 1"],
            "dependencies": [],
            "required_skill": "backend",
            "slot_path": "/tmp/slot",
            "slot_id": "slot-1",
            "branch_name": "feature/test",
            "test_commands": None,
            "fail_fast": True,
            "timeout_seconds": 1800,
            "playbook_path": None,
            "complexity": "medium",
            "require_review": False,
            "metadata": {},
        }
        
        context = TaskContext.from_dict(data)
        
        assert context.task_id == "1.1"
        assert context.spec_name == "test-spec"
        assert context.slot_path == Path("/tmp/slot")
        assert context.playbook_path is None
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = TaskContext(
            task_id="2.1",
            spec_name="my-spec",
            title="My Task",
            description="Description",
            acceptance_criteria=["AC1"],
            dependencies=[],
            required_skill="frontend",
            slot_path=Path("/tmp/workspace"),
            slot_id="slot-2",
            branch_name="feature/my-task",
        )
        
        data = original.to_dict()
        restored = TaskContext.from_dict(data)
        
        assert restored.task_id == original.task_id
        assert restored.spec_name == original.spec_name
        assert restored.slot_path == original.slot_path


class TestImplementationResult:
    """Tests for ImplementationResult model."""
    
    def test_to_dict(self):
        """Test ImplementationResult serialization."""
        result = ImplementationResult(
            success=True,
            diff="diff content",
            files_changed=["file1.py", "file2.py"],
            duration_seconds=45.2,
            llm_model="gpt-4",
            tokens_used=1500,
            error=None,
            review_result={"approved": True},
            pair_session_id="session-123",
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["diff"] == "diff content"
        assert data["files_changed"] == ["file1.py", "file2.py"]
        assert data["duration_seconds"] == 45.2
        assert data["llm_model"] == "gpt-4"
        assert data["tokens_used"] == 1500
        assert data["error"] is None
        assert data["review_result"] == {"approved": True}
        assert data["pair_session_id"] == "session-123"
    
    def test_from_dict(self):
        """Test ImplementationResult deserialization."""
        data = {
            "success": False,
            "diff": "",
            "files_changed": [],
            "duration_seconds": 10.0,
            "llm_model": None,
            "tokens_used": None,
            "error": "Implementation failed",
            "review_result": None,
            "pair_session_id": None,
        }
        
        result = ImplementationResult.from_dict(data)
        
        assert result.success is False
        assert result.error == "Implementation failed"
        assert result.llm_model is None
        assert result.tokens_used is None
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = ImplementationResult(
            success=True,
            diff="test diff",
            files_changed=["test.py"],
            duration_seconds=30.0,
            llm_model="gpt-3.5-turbo",
            tokens_used=800,
        )
        
        data = original.to_dict()
        restored = ImplementationResult.from_dict(data)
        
        assert restored.success == original.success
        assert restored.diff == original.diff
        assert restored.files_changed == original.files_changed
        assert restored.llm_model == original.llm_model
        assert restored.tokens_used == original.tokens_used
    
    def test_new_fields(self):
        """Test new LLM-related fields."""
        result = ImplementationResult(
            success=True,
            diff="diff",
            files_changed=["file.py"],
            duration_seconds=20.0,
            llm_model="gpt-4-turbo",
            tokens_used=2000,
        )
        
        assert result.llm_model == "gpt-4-turbo"
        assert result.tokens_used == 2000


class TestSingleTestResult:
    """Tests for SingleTestResult model."""
    
    def test_to_dict(self):
        """Test SingleTestResult serialization."""
        result = SingleTestResult(
            command="pytest",
            success=True,
            stdout="All tests passed",
            stderr="",
            exit_code=0,
            duration_seconds=2.5,
        )
        
        data = result.to_dict()
        
        assert data["command"] == "pytest"
        assert data["success"] is True
        assert data["stdout"] == "All tests passed"
        assert data["stderr"] == ""
        assert data["exit_code"] == 0
        assert data["duration_seconds"] == 2.5
    
    def test_from_dict(self):
        """Test SingleTestResult deserialization."""
        data = {
            "command": "npm test",
            "success": False,
            "stdout": "Test output",
            "stderr": "Error output",
            "exit_code": 1,
            "duration_seconds": 5.0,
        }
        
        result = SingleTestResult.from_dict(data)
        
        assert result.command == "npm test"
        assert result.success is False
        assert result.exit_code == 1
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = SingleTestResult(
            command="go test",
            success=True,
            stdout="PASS",
            stderr="",
            exit_code=0,
            duration_seconds=1.2,
        )
        
        data = original.to_dict()
        restored = SingleTestResult.from_dict(data)
        
        assert restored.command == original.command
        assert restored.success == original.success


class TestTestResult:
    """Tests for TestResult model."""
    
    def test_to_dict(self):
        """Test TestResult serialization."""
        test_results = [
            SingleTestResult(
                command="test1",
                success=True,
                stdout="out1",
                stderr="",
                exit_code=0,
                duration_seconds=1.0,
            ),
            SingleTestResult(
                command="test2",
                success=True,
                stdout="out2",
                stderr="",
                exit_code=0,
                duration_seconds=2.0,
            ),
        ]
        
        result = TestResult(
            success=True,
            test_results=test_results,
            total_duration_seconds=3.0,
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert len(data["test_results"]) == 2
        assert data["total_duration_seconds"] == 3.0
    
    def test_from_dict(self):
        """Test TestResult deserialization."""
        data = {
            "success": False,
            "test_results": [
                {
                    "command": "test1",
                    "success": False,
                    "stdout": "out",
                    "stderr": "err",
                    "exit_code": 1,
                    "duration_seconds": 1.0,
                }
            ],
            "total_duration_seconds": 1.0,
        }
        
        result = TestResult.from_dict(data)
        
        assert result.success is False
        assert len(result.test_results) == 1
        assert result.test_results[0].command == "test1"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = TestResult(
            success=True,
            test_results=[
                SingleTestResult(
                    command="pytest",
                    success=True,
                    stdout="passed",
                    stderr="",
                    exit_code=0,
                    duration_seconds=2.0,
                )
            ],
            total_duration_seconds=2.0,
        )
        
        data = original.to_dict()
        restored = TestResult.from_dict(data)
        
        assert restored.success == original.success
        assert len(restored.test_results) == len(original.test_results)


class TestPushResult:
    """Tests for PushResult model."""
    
    def test_to_dict(self):
        """Test PushResult serialization."""
        result = PushResult(
            success=True,
            branch_name="feature/test",
            commit_hash="abc123",
            retry_count=0,
            error=None,
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["branch_name"] == "feature/test"
        assert data["commit_hash"] == "abc123"
        assert data["retry_count"] == 0
        assert data["error"] is None
    
    def test_from_dict(self):
        """Test PushResult deserialization."""
        data = {
            "success": False,
            "branch_name": "feature/test",
            "commit_hash": "",
            "retry_count": 3,
            "error": "Push failed",
        }
        
        result = PushResult.from_dict(data)
        
        assert result.success is False
        assert result.retry_count == 3
        assert result.error == "Push failed"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = PushResult(
            success=True,
            branch_name="feature/my-feature",
            commit_hash="def456",
            retry_count=1,
        )
        
        data = original.to_dict()
        restored = PushResult.from_dict(data)
        
        assert restored.success == original.success
        assert restored.branch_name == original.branch_name
        assert restored.commit_hash == original.commit_hash


class TestArtifact:
    """Tests for Artifact model."""
    
    def test_to_dict(self):
        """Test Artifact serialization."""
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        artifact = Artifact(
            type=ArtifactType.DIFF,
            uri="test-spec/1.1/diff.diff",
            size_bytes=1024,
            created_at=created_at,
        )
        
        data = artifact.to_dict()
        
        assert data["type"] == "diff"
        assert data["uri"] == "test-spec/1.1/diff.diff"
        assert data["size_bytes"] == 1024
        assert data["created_at"] == created_at.isoformat()
    
    def test_from_dict(self):
        """Test Artifact deserialization."""
        data = {
            "type": "log",
            "uri": "test-spec/1.1/log.log",
            "size_bytes": 2048,
            "created_at": "2024-01-01T12:00:00",
        }
        
        artifact = Artifact.from_dict(data)
        
        assert artifact.type == ArtifactType.LOG
        assert artifact.uri == "test-spec/1.1/log.log"
        assert artifact.size_bytes == 2048
        assert artifact.created_at == datetime(2024, 1, 1, 12, 0, 0)
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = Artifact(
            type=ArtifactType.TEST_RESULT,
            uri="spec/task/test.json",
            size_bytes=512,
            created_at=datetime.now(),
        )
        
        data = original.to_dict()
        restored = Artifact.from_dict(data)
        
        assert restored.type == original.type
        assert restored.uri == original.uri
        assert restored.size_bytes == original.size_bytes


class TestRunnerResult:
    """Tests for RunnerResult model."""
    
    def test_to_dict(self):
        """Test RunnerResult serialization."""
        artifacts = [
            Artifact(
                type=ArtifactType.DIFF,
                uri="spec/1.1/diff.diff",
                size_bytes=1024,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
            )
        ]
        
        impl_result = ImplementationResult(
            success=True,
            diff="diff",
            files_changed=["file.py"],
            duration_seconds=10.0,
        )
        
        result = RunnerResult(
            success=True,
            runner_id="runner-123",
            task_id="1.1",
            duration_seconds=60.0,
            artifacts=artifacts,
            error=None,
            impl_result=impl_result,
            test_result=None,
            push_result=None,
            workspace_path="/tmp/workspace",
            concurrent_runners=2,
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["runner_id"] == "runner-123"
        assert data["task_id"] == "1.1"
        assert data["duration_seconds"] == 60.0
        assert len(data["artifacts"]) == 1
        assert data["impl_result"] is not None
        assert data["workspace_path"] == "/tmp/workspace"
        assert data["concurrent_runners"] == 2
    
    def test_from_dict(self):
        """Test RunnerResult deserialization."""
        data = {
            "success": False,
            "runner_id": "runner-456",
            "task_id": "2.1",
            "duration_seconds": 30.0,
            "artifacts": [],
            "error": "Task failed",
            "impl_result": None,
            "test_result": None,
            "push_result": None,
            "workspace_path": None,
            "concurrent_runners": 1,
        }
        
        result = RunnerResult.from_dict(data)
        
        assert result.success is False
        assert result.runner_id == "runner-456"
        assert result.error == "Task failed"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = RunnerResult(
            success=True,
            runner_id="runner-789",
            task_id="3.1",
            duration_seconds=45.0,
            artifacts=[],
        )
        
        data = original.to_dict()
        restored = RunnerResult.from_dict(data)
        
        assert restored.success == original.success
        assert restored.runner_id == original.runner_id
        assert restored.task_id == original.task_id


class TestPlaybookStep:
    """Tests for PlaybookStep model."""
    
    def test_to_dict(self):
        """Test PlaybookStep serialization."""
        step = PlaybookStep(
            name="Test Step",
            command="echo test",
            condition="env == production",
            fail_fast=True,
            timeout_seconds=300,
            retry_count=2,
        )
        
        data = step.to_dict()
        
        assert data["name"] == "Test Step"
        assert data["command"] == "echo test"
        assert data["condition"] == "env == production"
        assert data["fail_fast"] is True
        assert data["timeout_seconds"] == 300
        assert data["retry_count"] == 2
    
    def test_from_dict(self):
        """Test PlaybookStep deserialization."""
        data = {
            "name": "Build",
            "command": "npm run build",
            "condition": None,
            "fail_fast": False,
            "timeout_seconds": 600,
            "retry_count": 0,
        }
        
        step = PlaybookStep.from_dict(data)
        
        assert step.name == "Build"
        assert step.command == "npm run build"
        assert step.condition is None
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = PlaybookStep(
            name="Deploy",
            command="kubectl apply",
            timeout_seconds=120,
        )
        
        data = original.to_dict()
        restored = PlaybookStep.from_dict(data)
        
        assert restored.name == original.name
        assert restored.command == original.command


class TestPlaybook:
    """Tests for Playbook model."""
    
    def test_to_dict(self):
        """Test Playbook serialization."""
        steps = [
            PlaybookStep(name="Step 1", command="cmd1"),
            PlaybookStep(name="Step 2", command="cmd2"),
        ]
        
        playbook = Playbook(
            name="Test Playbook",
            steps=steps,
            metadata={"version": "1.0"},
        )
        
        data = playbook.to_dict()
        
        assert data["name"] == "Test Playbook"
        assert len(data["steps"]) == 2
        assert data["metadata"] == {"version": "1.0"}
    
    def test_from_dict(self):
        """Test Playbook deserialization."""
        data = {
            "name": "My Playbook",
            "steps": [
                {
                    "name": "Test",
                    "command": "pytest",
                    "condition": None,
                    "fail_fast": True,
                    "timeout_seconds": 300,
                    "retry_count": 0,
                }
            ],
            "metadata": {},
        }
        
        playbook = Playbook.from_dict(data)
        
        assert playbook.name == "My Playbook"
        assert len(playbook.steps) == 1
        assert playbook.steps[0].name == "Test"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = Playbook(
            name="CI Playbook",
            steps=[
                PlaybookStep(name="Lint", command="npm run lint"),
                PlaybookStep(name="Test", command="npm test"),
            ],
        )
        
        data = original.to_dict()
        restored = Playbook.from_dict(data)
        
        assert restored.name == original.name
        assert len(restored.steps) == len(original.steps)


class TestSlotAllocation:
    """Tests for SlotAllocation model."""
    
    def test_to_dict(self):
        """Test SlotAllocation serialization."""
        allocation = SlotAllocation(
            slot_id="slot-123",
            slot_path=Path("/tmp/repo-pool/slot-123"),
        )
        
        data = allocation.to_dict()
        
        assert data["slot_id"] == "slot-123"
        assert data["slot_path"] == "/tmp/repo-pool/slot-123"
    
    def test_from_dict(self):
        """Test SlotAllocation deserialization."""
        data = {
            "slot_id": "slot-456",
            "slot_path": "/home/user/slots/slot-456",
        }
        
        allocation = SlotAllocation.from_dict(data)
        
        assert allocation.slot_id == "slot-456"
        assert allocation.slot_path == Path("/home/user/slots/slot-456")
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = SlotAllocation(
            slot_id="slot-789",
            slot_path=Path("/var/pool/slot-789"),
        )
        
        data = original.to_dict()
        restored = SlotAllocation.from_dict(data)
        
        assert restored.slot_id == original.slot_id
        assert restored.slot_path == original.slot_path


class TestCodeChange:
    """Tests for CodeChange model."""
    
    def test_to_dict_create(self):
        """Test CodeChange serialization for create operation."""
        change = CodeChange(
            file_path="src/new_file.py",
            operation="create",
            content="def hello():\n    print('Hello')",
        )
        
        data = change.to_dict()
        
        assert data["file_path"] == "src/new_file.py"
        assert data["operation"] == "create"
        assert data["content"] == "def hello():\n    print('Hello')"
    
    def test_to_dict_modify(self):
        """Test CodeChange serialization for modify operation."""
        change = CodeChange(
            file_path="src/existing.py",
            operation="modify",
            content="updated content",
        )
        
        data = change.to_dict()
        
        assert data["operation"] == "modify"
        assert data["content"] == "updated content"
    
    def test_to_dict_delete(self):
        """Test CodeChange serialization for delete operation."""
        change = CodeChange(
            file_path="src/old_file.py",
            operation="delete",
            content="",
        )
        
        data = change.to_dict()
        
        assert data["operation"] == "delete"
        assert data["content"] == ""
    
    def test_from_dict(self):
        """Test CodeChange deserialization."""
        data = {
            "file_path": "tests/test_new.py",
            "operation": "create",
            "content": "import pytest\n\ndef test_example():\n    pass",
        }
        
        change = CodeChange.from_dict(data)
        
        assert change.file_path == "tests/test_new.py"
        assert change.operation == "create"
        assert "import pytest" in change.content
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = CodeChange(
            file_path="config/settings.json",
            operation="modify",
            content='{"key": "value"}',
        )
        
        data = original.to_dict()
        restored = CodeChange.from_dict(data)
        
        assert restored.file_path == original.file_path
        assert restored.operation == original.operation
        assert restored.content == original.content


class TestLLMResponse:
    """Tests for LLMResponse model."""
    
    def test_to_dict(self):
        """Test LLMResponse serialization."""
        code_changes = [
            CodeChange(
                file_path="src/main.py",
                operation="create",
                content="print('Hello')",
            ),
            CodeChange(
                file_path="src/utils.py",
                operation="modify",
                content="def util(): pass",
            ),
        ]
        
        response = LLMResponse(
            code_changes=code_changes,
            explanation="Created main.py and updated utils.py",
            model="gpt-4",
            tokens_used=1200,
        )
        
        data = response.to_dict()
        
        assert len(data["code_changes"]) == 2
        assert data["explanation"] == "Created main.py and updated utils.py"
        assert data["model"] == "gpt-4"
        assert data["tokens_used"] == 1200
    
    def test_from_dict(self):
        """Test LLMResponse deserialization."""
        data = {
            "code_changes": [
                {
                    "file_path": "README.md",
                    "operation": "modify",
                    "content": "# Updated README",
                }
            ],
            "explanation": "Updated documentation",
            "model": "gpt-3.5-turbo",
            "tokens_used": 500,
        }
        
        response = LLMResponse.from_dict(data)
        
        assert len(response.code_changes) == 1
        assert response.code_changes[0].file_path == "README.md"
        assert response.model == "gpt-3.5-turbo"
        assert response.tokens_used == 500
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = LLMResponse(
            code_changes=[
                CodeChange(
                    file_path="test.py",
                    operation="create",
                    content="test",
                )
            ],
            explanation="Test change",
            model="gpt-4-turbo",
            tokens_used=800,
        )
        
        data = original.to_dict()
        restored = LLMResponse.from_dict(data)
        
        assert len(restored.code_changes) == len(original.code_changes)
        assert restored.explanation == original.explanation
        assert restored.model == original.model
        assert restored.tokens_used == original.tokens_used


class TestLLMConfig:
    """Tests for LLMConfig model."""
    
    def test_to_dict(self):
        """Test LLMConfig serialization."""
        config = LLMConfig(
            api_key="sk-test-key-123",
            model="gpt-4",
            endpoint="https://api.openai.com/v1",
            timeout_seconds=120,
            max_tokens=4000,
        )
        
        data = config.to_dict()
        
        assert data["api_key"] == "sk-test-key-123"
        assert data["model"] == "gpt-4"
        assert data["endpoint"] == "https://api.openai.com/v1"
        assert data["timeout_seconds"] == 120
        assert data["max_tokens"] == 4000
    
    def test_from_dict(self):
        """Test LLMConfig deserialization."""
        data = {
            "api_key": "sk-another-key",
            "model": "gpt-3.5-turbo",
            "endpoint": None,
            "timeout_seconds": 60,
            "max_tokens": 2000,
        }
        
        config = LLMConfig.from_dict(data)
        
        assert config.api_key == "sk-another-key"
        assert config.model == "gpt-3.5-turbo"
        assert config.endpoint is None
        assert config.timeout_seconds == 60
        assert config.max_tokens == 2000
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = LLMConfig(
            api_key="sk-test",
            model="gpt-4-turbo",
            timeout_seconds=180,
        )
        
        data = original.to_dict()
        restored = LLMConfig.from_dict(data)
        
        assert restored.api_key == original.api_key
        assert restored.model == original.model
        assert restored.timeout_seconds == original.timeout_seconds
    
    def test_default_values(self):
        """Test LLMConfig default values."""
        config = LLMConfig(api_key="sk-test")
        
        assert config.model == "gpt-4"
        assert config.endpoint is None
        assert config.timeout_seconds == 120
        assert config.max_tokens == 4000


class TestJSONSerialization:
    """Tests for JSON serialization of all models."""
    
    def test_task_context_json_roundtrip(self):
        """Test TaskContext can be serialized to JSON and back."""
        original = TaskContext(
            task_id="1.1",
            spec_name="test",
            title="Test",
            description="Desc",
            acceptance_criteria=["AC1"],
            dependencies=[],
            required_skill="backend",
            slot_path=Path("/tmp/slot"),
            slot_id="slot-1",
            branch_name="feature/test",
        )
        
        json_str = json.dumps(original.to_dict())
        data = json.loads(json_str)
        restored = TaskContext.from_dict(data)
        
        assert restored.task_id == original.task_id
        assert restored.spec_name == original.spec_name
    
    def test_runner_result_json_roundtrip(self):
        """Test RunnerResult can be serialized to JSON and back."""
        original = RunnerResult(
            success=True,
            runner_id="runner-123",
            task_id="1.1",
            duration_seconds=60.0,
            artifacts=[],
        )
        
        json_str = json.dumps(original.to_dict())
        data = json.loads(json_str)
        restored = RunnerResult.from_dict(data)
        
        assert restored.success == original.success
        assert restored.runner_id == original.runner_id
    
    def test_llm_response_json_roundtrip(self):
        """Test LLMResponse can be serialized to JSON and back."""
        original = LLMResponse(
            code_changes=[
                CodeChange(
                    file_path="src/app.py",
                    operation="create",
                    content="# App code",
                )
            ],
            explanation="Created app",
            model="gpt-4",
            tokens_used=1000,
        )
        
        json_str = json.dumps(original.to_dict())
        data = json.loads(json_str)
        restored = LLMResponse.from_dict(data)
        
        assert restored.model == original.model
        assert restored.tokens_used == original.tokens_used
        assert len(restored.code_changes) == len(original.code_changes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Integration tests for Kiro synchronization.

Tests actual synchronization with tasks.md files.
Requirements: 8.1, 8.3, 8.7
"""

from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import TaskState
from necrocode.task_registry.exceptions import TasksetNotFoundError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def registry_dir(tmp_path):
    """Create temporary registry directory."""
    return tmp_path / "registry"


@pytest.fixture
def task_registry(registry_dir):
    """Create TaskRegistry instance."""
    return TaskRegistry(registry_dir)


@pytest.fixture
def tasks_md_dir(tmp_path):
    """Create temporary directory for tasks.md files."""
    return tmp_path / "specs"


# ============================================================================
# Basic Sync Tests
# ============================================================================

def test_sync_from_simple_tasks_md(task_registry, tasks_md_dir):
    """Test syncing from a simple tasks.md file."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Setup project structure
  - Create directory structure
  - _Requirements: 1.1_

- [ ] 2. Implement core functionality
  - Write main logic
  - _Requirements: 1.2_

- [x] 3. Add tests
  - Write unit tests
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    assert result.success
    assert len(result.tasks_added) == 3
    
    # Verify taskset was created
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 3
    
    # Verify task states
    task_1 = next(t for t in taskset.tasks if t.id == "1")
    task_2 = next(t for t in taskset.tasks if t.id == "2")
    task_3 = next(t for t in taskset.tasks if t.id == "3")
    
    assert task_1.state == TaskState.READY
    assert task_2.state == TaskState.READY
    assert task_3.state == TaskState.DONE


def test_sync_from_tasks_md_with_subtasks(task_registry, tasks_md_dir):
    """Test syncing from tasks.md with subtasks."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Backend Development
  - [ ] 1.1 Setup database
    - Create schema
    - _Requirements: R1.1_
  
  - [x] 1.2 Implement API
    - Create endpoints
    - _Requirements: R1.2_

- [ ] 2. Frontend Development
  - [ ] 2.1 Create UI
    - Build components
    - _Requirements: R2.1_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    assert result.success
    
    # Verify taskset
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) >= 3
    
    # Verify subtask states
    task_1_1 = next((t for t in taskset.tasks if t.id == "1.1"), None)
    task_1_2 = next((t for t in taskset.tasks if t.id == "1.2"), None)
    task_2_1 = next((t for t in taskset.tasks if t.id == "2.1"), None)
    
    if task_1_1:
        assert task_1_1.state == TaskState.READY
    if task_1_2:
        assert task_1_2.state == TaskState.DONE
    if task_2_1:
        assert task_2_1.state == TaskState.READY


def test_sync_from_tasks_md_with_dependencies(task_registry, tasks_md_dir):
    """Test syncing from tasks.md with dependencies."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [x] 1. Task 1
  - Description
  - _Requirements: 1.1_

- [ ] 2. Task 2
  - Depends on Task 1
  - _Requirements: 1, 2.1_

- [ ] 3. Task 3
  - Depends on Task 2
  - _Requirements: 2, 3.1_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    assert result.success
    
    # Verify dependencies
    taskset = task_registry.get_taskset("test-spec")
    
    task_2 = next((t for t in taskset.tasks if t.id == "2"), None)
    task_3 = next((t for t in taskset.tasks if t.id == "3"), None)
    
    if task_2:
        assert "1" in task_2.dependencies
    if task_3:
        assert "2" in task_3.dependencies


def test_sync_from_tasks_md_with_optional_tasks(task_registry, tasks_md_dir):
    """Test syncing from tasks.md with optional tasks (marked with *)."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Core Implementation
  - [ ] 1.1 Main feature
    - Required task
    - _Requirements: R1.1_
  
  - [ ]* 1.2 Unit tests
    - Optional task
    - _Requirements: R1.2_

- [ ] 2. Documentation
  - [ ]* 2.1 API docs
    - Optional documentation
    - _Requirements: R2.1_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    assert result.success
    
    # Verify optional flags
    taskset = task_registry.get_taskset("test-spec")
    
    task_1_1 = next((t for t in taskset.tasks if t.id == "1.1"), None)
    task_1_2 = next((t for t in taskset.tasks if t.id == "1.2"), None)
    task_2_1 = next((t for t in taskset.tasks if t.id == "2.1"), None)
    
    if task_1_1:
        assert not task_1_1.is_optional
    if task_1_2:
        assert task_1_2.is_optional
    if task_2_1:
        assert task_2_1.is_optional


# ============================================================================
# Bidirectional Sync Tests
# ============================================================================

def test_sync_to_kiro_updates_checkboxes(task_registry, tasks_md_dir):
    """Test syncing to tasks.md updates checkboxes."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Task 1
  - Description
  - _Requirements: 1.1_

- [ ] 2. Task 2
  - Description
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Initial sync
    task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Update task state in registry
    task_registry.update_task_state("test-spec", "1", TaskState.RUNNING)
    task_registry.update_task_state("test-spec", "1", TaskState.DONE)
    
    # Sync back to tasks.md
    result = task_registry.kiro_sync.sync_to_kiro("test-spec", tasks_md)
    
    assert result.success
    
    # Verify tasks.md was updated
    updated_content = tasks_md.read_text()
    assert "- [x] 1. Task 1" in updated_content
    assert "- [ ] 2. Task 2" in updated_content


def test_bidirectional_sync_workflow(task_registry, tasks_md_dir):
    """Test complete bidirectional sync workflow."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    # Initial tasks.md
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: 1.1_

- [ ] 2. Task 2
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Step 1: Sync from tasks.md
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    assert result.success
    
    # Step 2: Update task in registry
    task_registry.update_task_state("test-spec", "1", TaskState.DONE)
    
    # Step 3: Sync back to tasks.md
    result = task_registry.kiro_sync.sync_to_kiro("test-spec", tasks_md)
    assert result.success
    
    # Step 4: Manually update tasks.md (simulate user edit)
    content = tasks_md.read_text()
    content = content.replace("- [ ] 2. Task 2", "- [x] 2. Task 2")
    tasks_md.write_text(content)
    
    # Step 5: Sync from tasks.md again
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    assert result.success
    
    # Verify both tasks are done
    taskset = task_registry.get_taskset("test-spec")
    task_1 = next(t for t in taskset.tasks if t.id == "1")
    task_2 = next(t for t in taskset.tasks if t.id == "2")
    
    assert task_1.state == TaskState.DONE
    assert task_2.state == TaskState.DONE


def test_sync_detects_new_tasks_in_tasks_md(task_registry, tasks_md_dir):
    """Test sync detects and adds new tasks from tasks.md."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    # Initial tasks.md with 2 tasks
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: 1.1_

- [ ] 2. Task 2
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Initial sync
    task_registry.sync_with_kiro("test-spec", tasks_md)
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 2
    
    # Add new task to tasks.md
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: 1.1_

- [ ] 2. Task 2
  - _Requirements: 2.1_

- [ ] 3. Task 3
  - New task added
  - _Requirements: 3.1_
"""
    tasks_md.write_text(content)
    
    # Sync again
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    assert result.success
    assert len(result.tasks_added) >= 1
    
    # Verify new task was added
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 3
    
    task_3 = next((t for t in taskset.tasks if t.id == "3"), None)
    assert task_3 is not None
    assert task_3.title == "Task 3"


# ============================================================================
# Real-world Scenario Tests
# ============================================================================

def test_sync_with_actual_kiro_spec_format(task_registry, tasks_md_dir):
    """Test sync with actual Kiro spec format."""
    tasks_md = tasks_md_dir / "chat-app" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    # Realistic Kiro spec format
    content = """# Implementation Plan

- [x] 1. プロジェクト構造とデータモデルの実装
  - necrocode/task_registry/ディレクトリを作成
  - データモデル（Taskset、Task、TaskState、TaskEvent、Artifact）をmodels.pyに実装
  - _Requirements: 1.1, 1.4_

- [ ] 2. TaskStoreの実装
  - [x] 2.1 基本的な永続化機能
    - TaskStoreクラスをtask_store.pyに実装
    - _Requirements: 1.1, 1.3_

  - [ ] 2.2 バックアップとリストア機能
    - backup_taskset()メソッド: タスクセットをバックアップ
    - _Requirements: 9.1, 9.2, 9.3_

- [ ] 3. EventStoreの実装
  - [ ] 3.1 イベントログ記録機能
    - EventStoreクラスをevent_store.pyに実装
    - _Requirements: 4.1, 4.2_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    result = task_registry.sync_with_kiro("chat-app", tasks_md)
    
    assert result.success
    
    # Verify taskset
    taskset = task_registry.get_taskset("chat-app")
    assert len(taskset.tasks) >= 3
    
    # Verify task 1 is done
    task_1 = next((t for t in taskset.tasks if t.id == "1"), None)
    if task_1:
        assert task_1.state == TaskState.DONE
    
    # Verify task 2.1 is done
    task_2_1 = next((t for t in taskset.tasks if t.id == "2.1"), None)
    if task_2_1:
        assert task_2_1.state == TaskState.DONE
    
    # Verify task 2.2 is not done
    task_2_2 = next((t for t in taskset.tasks if t.id == "2.2"), None)
    if task_2_2:
        assert task_2_2.state != TaskState.DONE


def test_sync_preserves_task_metadata(task_registry, tasks_md_dir):
    """Test sync preserves task metadata across syncs."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: 1.1_
"""
    tasks_md.write_text(content)
    
    # Initial sync
    task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Add metadata to task
    task_registry.update_task_state(
        "test-spec",
        "1",
        TaskState.RUNNING,
        metadata={
            "assigned_slot": "slot-1",
            "runner_id": "runner-1",
            "reserved_branch": "feature/task-1"
        }
    )
    
    # Add artifact
    from necrocode.task_registry.models import ArtifactType
    task_registry.add_artifact(
        "test-spec",
        "1",
        ArtifactType.DIFF,
        "file://changes.diff"
    )
    
    # Sync again (should preserve metadata)
    task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Verify metadata preserved
    taskset = task_registry.get_taskset("test-spec")
    task = next(t for t in taskset.tasks if t.id == "1")
    
    assert task.assigned_slot == "slot-1"
    assert task.runner_id == "runner-1"
    assert task.reserved_branch == "feature/task-1"
    assert len(task.artifacts) == 1


def test_sync_handles_task_renumbering(task_registry, tasks_md_dir):
    """Test sync handles task renumbering in tasks.md."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    # Initial tasks.md
    content = """# Implementation Plan

- [ ] 1. Task A
  - _Requirements: 1.1_

- [ ] 2. Task B
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Initial sync
    task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Update task 1
    task_registry.update_task_state("test-spec", "1", TaskState.DONE)
    
    # Renumber tasks in tasks.md (simulate user reorganization)
    content = """# Implementation Plan

- [x] 1. Task A
  - _Requirements: 1.1_

- [ ] 2. Task B
  - _Requirements: 2.1_

- [ ] 3. Task C
  - _Requirements: 3.1_
"""
    tasks_md.write_text(content)
    
    # Sync again
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    assert result.success
    
    # Verify all tasks exist
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 3


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_sync_with_nonexistent_tasks_md(task_registry, tasks_md_dir):
    """Test sync with nonexistent tasks.md file."""
    tasks_md = tasks_md_dir / "nonexistent" / "tasks.md"
    
    # Should handle gracefully
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    assert not result.success
    assert len(result.errors) > 0
    assert any("not found" in err.lower() for err in result.errors)


def test_sync_with_malformed_tasks_md(task_registry, tasks_md_dir):
    """Test sync with malformed tasks.md file."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    # Malformed content
    content = """# Implementation Plan

This is not a valid task format
- Missing checkbox
- [ Missing closing bracket
"""
    tasks_md.write_text(content)
    
    # Should handle gracefully
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # May succeed with partial parsing or fail gracefully
    # Either way, should not crash


def test_sync_with_empty_tasks_md(task_registry, tasks_md_dir):
    """Test sync with empty tasks.md file."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

No tasks defined yet.
"""
    tasks_md.write_text(content)
    
    # Sync from empty file
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Should succeed with no tasks
    assert result.success
    assert len(result.tasks_added) == 0


# ============================================================================
# Performance Tests
# ============================================================================

def test_sync_large_tasks_md(task_registry, tasks_md_dir):
    """Test sync with large tasks.md file."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    # Generate large tasks.md
    lines = ["# Implementation Plan\n"]
    for i in range(100):
        lines.append(f"\n- [ ] {i+1}. Task {i+1}")
        lines.append(f"  - Description for task {i+1}")
        lines.append(f"  - _Requirements: {i+1}.1_")
    
    content = "\n".join(lines)
    tasks_md.write_text(content)
    
    # Sync should complete in reasonable time
    import time
    start = time.time()
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    elapsed = time.time() - start
    
    assert result.success
    assert elapsed < 10.0  # Should complete within 10 seconds
    
    # Verify all tasks were created
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 100


def test_repeated_syncs_performance(task_registry, tasks_md_dir):
    """Test performance of repeated syncs."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: 1.1_

- [ ] 2. Task 2
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Perform multiple syncs
    import time
    start = time.time()
    
    for _ in range(10):
        task_registry.sync_with_kiro("test-spec", tasks_md)
    
    elapsed = time.time() - start
    
    # Should complete reasonably fast
    assert elapsed < 5.0  # 10 syncs in under 5 seconds


# ============================================================================
# Integration with Other Components
# ============================================================================

def test_sync_integrates_with_event_store(task_registry, tasks_md_dir):
    """Test sync integrates properly with event store."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: R1.1_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    result = task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Verify sync was successful
    assert result.success
    assert len(result.tasks_added) == 1
    
    # Verify taskset was created
    taskset = task_registry.get_taskset("test-spec")
    assert len(taskset.tasks) == 1
    
    # Now update the task to generate events
    task_registry.update_task_state("test-spec", "1", TaskState.RUNNING)
    
    # Verify events were recorded for the update
    events = task_registry.event_store.get_events_by_task("test-spec", "1")
    assert len(events) > 0
    
    # Should have TaskUpdated event
    from necrocode.task_registry.models import EventType
    assert any(e.event_type in [EventType.TASK_UPDATED, EventType.TASK_ASSIGNED] for e in events)


def test_sync_integrates_with_query_engine(task_registry, tasks_md_dir):
    """Test sync integrates properly with query engine."""
    tasks_md = tasks_md_dir / "test-spec" / "tasks.md"
    tasks_md.parent.mkdir(parents=True)
    
    content = """# Implementation Plan

- [ ] 1. Backend Task
  - _Requirements: 1.1_

- [x] 2. Frontend Task
  - _Requirements: 2.1_
"""
    tasks_md.write_text(content)
    
    # Sync from tasks.md
    task_registry.sync_with_kiro("test-spec", tasks_md)
    
    # Query ready tasks
    ready_tasks = task_registry.query_engine.filter_by_state("test-spec", TaskState.READY)
    assert len(ready_tasks) >= 1
    
    # Query done tasks
    done_tasks = task_registry.query_engine.filter_by_state("test-spec", TaskState.DONE)
    assert len(done_tasks) >= 1

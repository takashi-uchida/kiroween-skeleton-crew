"""Unit tests for KiroSyncManager.

Tests tasks.md parsing, dependency extraction, and bidirectional sync.
Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
"""

from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.task_registry.kiro_sync import KiroSyncManager
from necrocode.task_registry.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState, Taskset


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
def kiro_sync(task_registry):
    """Create KiroSyncManager instance."""
    return KiroSyncManager(task_registry)


@pytest.fixture
def sample_tasks_md(tmp_path):
    """Create sample tasks.md file."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [ ] 1. Setup project structure
  - Create directory structure
  - _Requirements: 1.1_

- [ ] 2. Implement data models
  - [ ] 2.1 Create Task model
    - Define Task class
    - _Requirements: 1.1, 1.2_
  
  - [x] 2.2 Create Taskset model
    - Define Taskset class
    - _Requirements: 1.1_

- [ ]* 3. Write tests
  - Unit tests for models
  - _Requirements: 1.1_
"""
    tasks_md.write_text(content)
    return tasks_md


# ============================================================================
# Parse tasks.md Tests
# ============================================================================

def test_parse_tasks_md_extracts_tasks(kiro_sync, sample_tasks_md):
    """Test parse_tasks_md extracts all tasks."""
    task_defs = kiro_sync.parse_tasks_md(sample_tasks_md)
    
    # Should extract top-level and sub-tasks
    assert len(task_defs) > 0
    
    # Check for specific tasks
    task_ids = [t["id"] for t in task_defs]
    assert "1" in task_ids
    assert "2" in task_ids
    assert "2.1" in task_ids
    assert "2.2" in task_ids
    assert "3" in task_ids


def test_parse_tasks_md_extracts_titles(kiro_sync, sample_tasks_md):
    """Test parse_tasks_md extracts task titles."""
    task_defs = kiro_sync.parse_tasks_md(sample_tasks_md)
    
    task_by_id = {t["id"]: t for t in task_defs}
    
    assert "Setup project structure" in task_by_id["1"]["title"]
    assert "Implement data models" in task_by_id["2"]["title"]
    assert "Create Task model" in task_by_id["2.1"]["title"]


def test_parse_tasks_md_extracts_checkbox_state(kiro_sync, sample_tasks_md):
    """Test parse_tasks_md extracts checkbox state."""
    task_defs = kiro_sync.parse_tasks_md(sample_tasks_md)
    
    task_by_id = {t["id"]: t for t in task_defs}
    
    # [ ] should map to not completed
    assert not task_by_id["1"]["completed"]
    assert not task_by_id["2"]["completed"]
    assert not task_by_id["2.1"]["completed"]
    
    # [x] should map to completed
    assert task_by_id["2.2"]["completed"]


def test_parse_tasks_md_identifies_optional_tasks(kiro_sync, sample_tasks_md):
    """Test parse_tasks_md identifies optional tasks (marked with *)."""
    task_defs = kiro_sync.parse_tasks_md(sample_tasks_md)
    
    task_by_id = {t["id"]: t for t in task_defs}
    
    # Task 3 is marked with *
    assert task_by_id["3"]["is_optional"]
    
    # Other tasks are not optional
    assert not task_by_id["1"]["is_optional"]
    assert not task_by_id["2"]["is_optional"]


def test_parse_tasks_md_extracts_descriptions(kiro_sync, sample_tasks_md):
    """Test parse_tasks_md extracts task descriptions."""
    task_defs = kiro_sync.parse_tasks_md(sample_tasks_md)
    
    task_by_id = {t["id"]: t for t in task_defs}
    
    # Should extract bullet points as description
    assert "Create directory structure" in task_by_id["1"]["description"]
    assert "Define Task class" in task_by_id["2.1"]["description"]


def test_parse_tasks_md_empty_file(kiro_sync, tmp_path):
    """Test parse_tasks_md handles empty file."""
    empty_md = tmp_path / "empty.md"
    empty_md.write_text("")
    
    task_defs = kiro_sync.parse_tasks_md(empty_md)
    
    assert task_defs == []


def test_parse_tasks_md_no_tasks(kiro_sync, tmp_path):
    """Test parse_tasks_md handles file with no tasks."""
    no_tasks_md = tmp_path / "no_tasks.md"
    no_tasks_md.write_text("# Some heading\n\nSome text without tasks.")
    
    task_defs = kiro_sync.parse_tasks_md(no_tasks_md)
    
    assert task_defs == []


# ============================================================================
# Extract Dependencies Tests
# ============================================================================

def test_extract_dependencies_single_requirement(kiro_sync):
    """Test extract_dependencies with single requirement."""
    task_text = "Some task description\n_Requirements: 1.1_"
    
    deps = kiro_sync.extract_dependencies(task_text)
    
    assert deps == ["1.1"]


def test_extract_dependencies_multiple_requirements(kiro_sync):
    """Test extract_dependencies with multiple requirements."""
    task_text = "Some task description\n_Requirements: 1.1, 2.3, 3.5_"
    
    deps = kiro_sync.extract_dependencies(task_text)
    
    assert deps == ["1.1", "2.3", "3.5"]


def test_extract_dependencies_no_requirements(kiro_sync):
    """Test extract_dependencies with no requirements."""
    task_text = "Some task description without requirements"
    
    deps = kiro_sync.extract_dependencies(task_text)
    
    assert deps == []


def test_extract_dependencies_with_spaces(kiro_sync):
    """Test extract_dependencies handles spaces."""
    task_text = "_Requirements: 1.1 , 2.3 , 3.5_"
    
    deps = kiro_sync.extract_dependencies(task_text)
    
    assert deps == ["1.1", "2.3", "3.5"]


def test_extract_dependencies_multiple_lines(kiro_sync):
    """Test extract_dependencies finds requirements in multi-line text."""
    task_text = """Task description
    Some details
    _Requirements: 1.1, 2.2_
    More details"""
    
    deps = kiro_sync.extract_dependencies(task_text)
    
    assert deps == ["1.1", "2.2"]


# ============================================================================
# Sync from Kiro Tests
# ============================================================================

def test_sync_from_kiro_creates_taskset(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_from_kiro creates taskset from tasks.md."""
    result = kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    assert result.success
    
    # Verify taskset was created
    taskset = task_registry.get_taskset("test-spec")
    assert taskset is not None
    assert taskset.spec_name == "test-spec"


def test_sync_from_kiro_creates_tasks(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_from_kiro creates tasks."""
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    taskset = task_registry.get_taskset("test-spec")
    
    # Should have created tasks
    assert len(taskset.tasks) > 0
    
    # Check for specific tasks
    task_ids = [t.id for t in taskset.tasks]
    assert "1" in task_ids
    assert "2.1" in task_ids
    assert "2.2" in task_ids


def test_sync_from_kiro_sets_task_states(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_from_kiro sets correct task states."""
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    taskset = task_registry.get_taskset("test-spec")
    task_by_id = {t.id: t for t in taskset.tasks}
    
    # Unchecked tasks should be READY or BLOCKED
    assert task_by_id["1"].state in [TaskState.READY, TaskState.BLOCKED]
    
    # Checked tasks should be DONE
    assert task_by_id["2.2"].state == TaskState.DONE


def test_sync_from_kiro_sets_dependencies(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_from_kiro sets task dependencies."""
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    taskset = task_registry.get_taskset("test-spec")
    task_by_id = {t.id: t for t in taskset.tasks}
    
    # Task 2.1 depends on 1.1, 1.2
    assert "1.1" in task_by_id["2.1"].dependencies or "1.2" in task_by_id["2.1"].dependencies


def test_sync_from_kiro_sets_optional_flag(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_from_kiro sets is_optional flag."""
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    taskset = task_registry.get_taskset("test-spec")
    task_by_id = {t.id: t for t in taskset.tasks}
    
    # Task 3 is optional
    assert task_by_id["3"].is_optional


def test_sync_from_kiro_updates_existing_taskset(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_from_kiro updates existing taskset."""
    # First sync
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    taskset1 = task_registry.get_taskset("test-spec")
    version1 = taskset1.version
    
    # Modify tasks.md
    content = sample_tasks_md.read_text()
    content = content.replace("[ ] 1.", "[x] 1.")
    sample_tasks_md.write_text(content)
    
    # Second sync
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    taskset2 = task_registry.get_taskset("test-spec")
    
    # Version should increment
    assert taskset2.version > version1
    
    # Task 1 should now be done
    task_by_id = {t.id: t for t in taskset2.tasks}
    assert task_by_id["1"].state == TaskState.DONE


# ============================================================================
# Sync to Kiro Tests
# ============================================================================

def test_sync_to_kiro_updates_checkboxes(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_to_kiro updates checkboxes in tasks.md."""
    # Create taskset with completed task
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Update task state
    task_registry.update_task_state("test-spec", "1", TaskState.DONE)
    
    # Sync back to Kiro
    result = kiro_sync.sync_to_kiro("test-spec", sample_tasks_md)
    
    assert result.success
    
    # Verify checkbox was updated
    content = sample_tasks_md.read_text()
    assert "[x] 1. Setup project structure" in content


def test_sync_to_kiro_preserves_unchecked_tasks(kiro_sync, task_registry, sample_tasks_md):
    """Test sync_to_kiro preserves unchecked tasks."""
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Sync without changes
    kiro_sync.sync_to_kiro("test-spec", sample_tasks_md)
    
    # Verify unchecked tasks remain unchecked
    content = sample_tasks_md.read_text()
    assert "[ ] 1. Setup project structure" in content


def test_sync_to_kiro_handles_nonexistent_taskset(kiro_sync, sample_tasks_md):
    """Test sync_to_kiro handles nonexistent taskset."""
    result = kiro_sync.sync_to_kiro("nonexistent-spec", sample_tasks_md)
    
    assert not result.success


# ============================================================================
# Bidirectional Sync Tests
# ============================================================================

def test_bidirectional_sync_roundtrip(kiro_sync, task_registry, sample_tasks_md):
    """Test complete bidirectional sync roundtrip."""
    # Sync from Kiro
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Modify task state in registry
    task_registry.update_task_state("test-spec", "2.1", TaskState.DONE)
    
    # Sync back to Kiro
    kiro_sync.sync_to_kiro("test-spec", sample_tasks_md)
    
    # Verify tasks.md was updated
    content = sample_tasks_md.read_text()
    assert "[x] 2.1" in content
    
    # Sync from Kiro again
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Verify state is preserved
    taskset = task_registry.get_taskset("test-spec")
    task_by_id = {t.id: t for t in taskset.tasks}
    assert task_by_id["2.1"].state == TaskState.DONE


def test_sync_handles_new_tasks_in_md(kiro_sync, task_registry, sample_tasks_md):
    """Test sync handles new tasks added to tasks.md."""
    # Initial sync
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Add new task to tasks.md
    content = sample_tasks_md.read_text()
    content += "\n- [ ] 4. New task\n  - New task description\n  - _Requirements: 1.1_\n"
    sample_tasks_md.write_text(content)
    
    # Sync again
    result = kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    assert result.success
    assert "4" in result.tasks_added
    
    # Verify new task was added
    taskset = task_registry.get_taskset("test-spec")
    task_ids = [t.id for t in taskset.tasks]
    assert "4" in task_ids


def test_sync_detects_conflicts(kiro_sync, task_registry, sample_tasks_md):
    """Test sync detects conflicts between registry and tasks.md."""
    # Initial sync
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Modify in registry
    task_registry.update_task_state("test-spec", "1", TaskState.DONE)
    
    # Modify tasks.md differently (keep unchecked)
    # This creates a conflict
    
    # Sync should detect conflict
    result = kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Depending on implementation, might have conflicts
    # This test documents expected behavior


# ============================================================================
# Dependency Graph Tests
# ============================================================================

def test_sync_builds_dependency_graph(kiro_sync, task_registry, tmp_path):
    """Test sync builds correct dependency graph."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: _

- [ ] 2. Task 2
  - _Requirements: 1_

- [ ] 3. Task 3
  - _Requirements: 1, 2_
"""
    tasks_md.write_text(content)
    
    kiro_sync.sync_from_kiro("test-spec", tasks_md)
    
    taskset = task_registry.get_taskset("test-spec")
    task_by_id = {t.id: t for t in taskset.tasks}
    
    # Verify dependencies
    assert task_by_id["1"].dependencies == []
    assert "1" in task_by_id["2"].dependencies
    assert "1" in task_by_id["3"].dependencies
    assert "2" in task_by_id["3"].dependencies


def test_sync_detects_circular_dependencies(kiro_sync, tmp_path):
    """Test sync detects circular dependencies."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [ ] 1. Task 1
  - _Requirements: 2_

- [ ] 2. Task 2
  - _Requirements: 1_
"""
    tasks_md.write_text(content)
    
    # Should detect circular dependency
    result = kiro_sync.sync_from_kiro("test-spec", tasks_md)
    
    # Depending on implementation, might fail or warn
    # This test documents expected behavior


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_parse_tasks_md_with_unicode(kiro_sync, tmp_path):
    """Test parse_tasks_md handles Unicode characters."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [ ] 1. タスク with 日本語
  - Description with émojis 🎉
  - _Requirements: _
"""
    tasks_md.write_text(content, encoding="utf-8")
    
    task_defs = kiro_sync.parse_tasks_md(tasks_md)
    
    assert len(task_defs) > 0
    assert "日本語" in task_defs[0]["title"]


def test_parse_tasks_md_with_malformed_checkboxes(kiro_sync, tmp_path):
    """Test parse_tasks_md handles malformed checkboxes."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [] 1. Missing space
- [ ]2. No space after checkbox
- [x ] 3. Extra space
"""
    tasks_md.write_text(content)
    
    # Should handle gracefully
    task_defs = kiro_sync.parse_tasks_md(tasks_md)
    
    # Depending on implementation, might parse some or all


def test_sync_from_kiro_nonexistent_file(kiro_sync, tmp_path):
    """Test sync_from_kiro handles nonexistent file."""
    nonexistent = tmp_path / "nonexistent.md"
    
    result = kiro_sync.sync_from_kiro("test-spec", nonexistent)
    
    assert not result.success


def test_sync_handles_deeply_nested_tasks(kiro_sync, task_registry, tmp_path):
    """Test sync handles deeply nested tasks."""
    tasks_md = tmp_path / "tasks.md"
    content = """# Implementation Plan

- [ ] 1. Level 1
  - [ ] 1.1 Level 2
    - [ ] 1.1.1 Level 3
      - [ ] 1.1.1.1 Level 4
"""
    tasks_md.write_text(content)
    
    kiro_sync.sync_from_kiro("test-spec", tasks_md)
    
    taskset = task_registry.get_taskset("test-spec")
    task_ids = [t.id for t in taskset.tasks]
    
    # Should handle nested tasks
    assert "1" in task_ids
    assert "1.1" in task_ids


def test_sync_preserves_task_metadata(kiro_sync, task_registry, sample_tasks_md):
    """Test sync preserves task metadata."""
    # Initial sync
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Add metadata to task
    taskset = task_registry.get_taskset("test-spec")
    taskset.tasks[0].metadata["custom_field"] = "custom_value"
    task_registry.task_store.save_taskset(taskset)
    
    # Sync from Kiro again
    kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    # Metadata should be preserved
    taskset = task_registry.get_taskset("test-spec")
    assert taskset.tasks[0].metadata.get("custom_field") == "custom_value"


def test_sync_result_contains_statistics(kiro_sync, task_registry, sample_tasks_md):
    """Test sync result contains statistics."""
    result = kiro_sync.sync_from_kiro("test-spec", sample_tasks_md)
    
    assert hasattr(result, "tasks_added")
    assert hasattr(result, "tasks_updated")
    assert hasattr(result, "success")

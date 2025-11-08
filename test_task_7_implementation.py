"""Test Task 7 implementation - Spirit updates with workload tracking and routing."""

import sys
from pathlib import Path

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent))

from framework.agents.architect_agent import ArchitectSpirit
from framework.agents.scrum_master_agent import ScrumMasterSpirit
from framework.agents.frontend_agent import FrontendSpirit
from framework.agents.backend_agent import BackendSpirit
from framework.agents.database_agent import DatabaseSpirit
from framework.agents.qa_agent import QASpirit
from framework.agents.devops_agent import DevOpsSpirit
from framework.communication.message_bus import MessageBus
from framework.workspace_manager.workspace_manager import WorkspaceManager


def test_architect_workload_tracking():
    """Test ArchitectSpirit has workload tracking."""
    architect = ArchitectSpirit(role="architect", skills=["design"], instance_number=1)
    
    # Test workload tracking
    assert architect.get_workload() == 0
    architect.assign_task("TASK-001")
    assert architect.get_workload() == 1
    architect.complete_task("TASK-001")
    assert architect.get_workload() == 0
    assert "TASK-001" in architect.completed_tasks
    print("✅ ArchitectSpirit workload tracking works")


def test_scrum_master_issue_creation():
    """Test ScrumMasterSpirit creates Issue objects."""
    message_bus = MessageBus()
    scrum = ScrumMasterSpirit(
        role="scrum_master",
        skills=["planning"],
        instance_number=1,
        message_bus=message_bus
    )
    
    # Test decompose_job creates Issue objects
    job_desc = "認証機能が必要です。リアルタイムチャットも実装してください。"
    architecture = {"frontend": "React", "backend": "Node.js"}
    stories = scrum.decompose_job(job_desc, architecture)
    
    # Verify stories have issues
    assert len(stories) > 0
    for story in stories:
        if "issues" in story:
            assert len(story["issues"]) > 0
            for issue in story["issues"]:
                assert hasattr(issue, "id")
                assert hasattr(issue, "title")
                assert hasattr(issue, "labels")
                assert issue.id.startswith("ISSUE-")
    
    print(f"✅ ScrumMasterSpirit created {scrum.issue_counter} issues")


def test_development_spirits_workload():
    """Test development spirits have workload tracking and message handlers."""
    message_bus = MessageBus()
    workspace_mgr = WorkspaceManager(".")
    
    # Test FrontendSpirit
    frontend = FrontendSpirit(
        role="frontend",
        skills=["react"],
        instance_number=1,
        message_bus=message_bus,
        workspace_manager=workspace_mgr
    )
    assert frontend.get_workload() == 0
    frontend.assign_task("TASK-001")
    assert frontend.get_workload() == 1
    
    # Test BackendSpirit
    backend = BackendSpirit(
        role="backend",
        skills=["nodejs"],
        instance_number=1,
        message_bus=message_bus,
        workspace_manager=workspace_mgr
    )
    assert backend.get_workload() == 0
    backend.assign_task("TASK-002")
    assert backend.get_workload() == 1
    
    # Test DatabaseSpirit
    database = DatabaseSpirit(
        role="database",
        skills=["postgres"],
        instance_number=1,
        message_bus=message_bus,
        workspace_manager=workspace_mgr
    )
    assert database.get_workload() == 0
    database.assign_task("TASK-003")
    assert database.get_workload() == 1
    
    print("✅ Development spirits workload tracking works")


def test_qa_devops_spirits():
    """Test QA and DevOps spirits have workload tracking."""
    message_bus = MessageBus()
    workspace_mgr = WorkspaceManager(".")
    
    # Test QASpirit
    qa = QASpirit(
        role="qa",
        skills=["testing"],
        instance_number=1,
        message_bus=message_bus,
        workspace_manager=workspace_mgr
    )
    assert qa.get_workload() == 0
    qa.assign_task("TASK-004")
    assert qa.get_workload() == 1
    
    # Test bug reporting with issue_id
    bug_report = qa.report_bug(
        {"component": "auth", "error": "login fails"},
        issue_id="42"
    )
    assert "#42" in bug_report
    
    # Test DevOpsSpirit
    devops = DevOpsSpirit(
        role="devops",
        skills=["docker"],
        instance_number=1,
        message_bus=message_bus,
        workspace_manager=workspace_mgr
    )
    assert devops.get_workload() == 0
    devops.assign_task("TASK-005")
    assert devops.get_workload() == 1
    
    print("✅ QA and DevOps spirits workload tracking works")


def test_branch_creation_integration():
    """Test spirits can create branches with new naming convention."""
    workspace_mgr = WorkspaceManager(".")
    
    frontend = FrontendSpirit(
        role="frontend",
        skills=["react"],
        instance_number=1,
        workspace_manager=workspace_mgr
    )
    
    # Test branch creation
    branch = workspace_mgr.create_branch(frontend.identifier, "login-ui", "42")
    assert branch == "frontend/issue-42-login-ui"
    
    # Test commit message formatting
    commit_msg = workspace_mgr.format_commit_message(
        frontend.identifier,
        "ui",
        "summon login form component",
        "42"
    )
    assert commit_msg == "spirit-1(ui): summon login form component [#42]"
    
    print("✅ Branch creation and commit formatting works")


if __name__ == "__main__":
    print("\n🧪 Testing Task 7 Implementation\n")
    
    test_architect_workload_tracking()
    test_scrum_master_issue_creation()
    test_development_spirits_workload()
    test_qa_devops_spirits()
    test_branch_creation_integration()
    
    print("\n✨ All Task 7 tests passed!\n")

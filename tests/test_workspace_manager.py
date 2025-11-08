"""Tests for WorkspaceManager branch + commit strategies (Spec task 10.3)."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from framework.workspace_manager import SpiritWorkspaceManager


def test_instance_based_branch_names_are_unique_for_multiple_agents(tmp_path):
    manager = SpiritWorkspaceManager(tmp_path)

    branch_one = manager.create_branch("frontend_spirit_1", "Login UI")
    branch_two = manager.create_branch("frontend_spirit_2", "Login UI")

    assert branch_one == "frontend/spirit-1/login-ui"
    assert branch_two == "frontend/spirit-2/login-ui"
    assert branch_one != branch_two


def test_issue_based_branch_names_override_instance_format(tmp_path):
    manager = SpiritWorkspaceManager(tmp_path)

    branch = manager.create_branch("backend_spirit_3", "Auth API", issue_id="77")

    assert branch == "backend/issue-77-auth-api"


def test_commit_message_format_includes_instance_and_issue_reference(tmp_path):
    manager = SpiritWorkspaceManager(tmp_path)

    commit_with_issue = manager.format_commit_message(
        "backend_spirit_2", scope="api", description="Forged auth endpoints", issue_id="77"
    )
    commit_without_issue = manager.format_commit_message(
        "frontend_spirit_1", scope="ui", description="Summoned login canvas"
    )

    assert commit_with_issue == "spirit-2(api): Forged auth endpoints [#77]"
    assert commit_without_issue == "spirit-1(ui): Summoned login canvas"


def test_branch_tracking_is_per_spirit_instance(tmp_path):
    manager = SpiritWorkspaceManager(tmp_path)
    branch = manager.create_branch("qa_spirit_4", "Regression Suite")

    assert manager.get_active_branches("qa_spirit_4") == [branch]
    assert manager.get_active_branches("qa_spirit_5") == []


def test_invalid_spirit_identifier_raises_value_error(tmp_path):
    manager = SpiritWorkspaceManager(tmp_path)

    try:
        manager.create_branch("frontend", "feature")
    except ValueError as exc:
        assert "Invalid spirit identifier" in str(exc)
    else:
        assert False, "Expected ValueError for malformed spirit identifier"

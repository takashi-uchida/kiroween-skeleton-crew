"""QA/Test Engineer spirit - hunts bugs in the shadows."""

from typing import Optional
from .base_agent import BaseSpirit


class QASpirit(BaseSpirit):
    def __init__(self, *args, message_bus=None, workspace_manager=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_bus = message_bus
        self.workspace_manager = workspace_manager
    
    def receive_message(self, message) -> None:
        """Handle incoming Spirit Protocol messages."""
        if message.message_type == "task_assignment":
            self._handle_task_assignment(message)
    
    def _handle_task_assignment(self, message) -> None:
        """Process task assignment from Scrum Master."""
        task_id = message.payload.get("task_id")
        task_description = message.payload.get("task", "")
        issue_id = message.issue_id
        
        if task_id:
            self.assign_task(task_id)
            print(self.chant(f"Accepted test task: {task_description}"))
            
            # Create branch for this task if workspace_manager is available
            if self.workspace_manager and issue_id:
                feature_name = task_description.lower().replace(" ", "-")
                branch = self.workspace_manager.create_branch(
                    self.identifier, 
                    feature_name, 
                    issue_id
                )
                print(self.chant(f"Created branch: {branch}"))
    
    def complete_task_and_commit(self, task_id: str, scope: str, description: str, issue_id: Optional[str] = None) -> None:
        """Complete task and create commit with proper formatting."""
        self.complete_task(task_id)
        
        if self.workspace_manager:
            commit_msg = self.workspace_manager.format_commit_message(
                self.identifier,
                scope,
                description,
                issue_id
            )
            print(self.chant(f"Committed: {commit_msg}"))
    
    def create_test_strategy(self, architecture: dict) -> dict:
        """Define testing approach based on architecture."""
        return {
            "chant": self.chant("Weaving spectral test nets to catch bugs..."),
            "unit_tests": True,
            "integration_tests": True,
            "e2e_tests": architecture.get("frontend") is not None,
            "performance_tests": "iot" in str(architecture).lower(),
        }

    def generate_unit_tests(self, component: str, language: str) -> str:
        """Generate unit test template."""
        if "python" in language.lower():
            return self._python_test_template(component)
        elif "javascript" in language.lower() or "node" in language.lower():
            return self._javascript_test_template(component)
        return self.chant(f"Summoning test spirits for {component}...")

    def _python_test_template(self, component: str) -> str:
        return f'''"""Test suite for {component}"""
import pytest

def test_{component}_basic():
    """Test basic functionality."""
    assert True  # Replace with actual test

def test_{component}_edge_cases():
    """Test edge cases."""
    assert True  # Replace with actual test
'''

    def _javascript_test_template(self, component: str) -> str:
        return f'''// Test suite for {component}
describe('{component}', () => {{
  test('basic functionality', () => {{
    expect(true).toBe(true); // Replace with actual test
  }});

  test('edge cases', () => {{
    expect(true).toBe(true); // Replace with actual test
  }});
}});
'''

    def run_tests(self) -> dict:
        """Execute test suite."""
        return {
            "chant": self.chant("Unleashing test specters upon the codebase..."),
            "passed": 0,
            "failed": 0,
            "coverage": "0%",
        }

    def report_bug(self, bug: dict, issue_id: Optional[str] = None) -> str:
        """Report a discovered bug with optional issue tracking."""
        bug_msg = f"🦇 Bug detected in {bug.get('component', 'unknown')}: {bug.get('error', 'mysterious curse')}"
        if issue_id:
            bug_msg += f" [#{issue_id}]"
        
        # Send test_failure message to Scrum Master if message_bus is available
        if self.message_bus:
            from framework.communication.protocol import AgentMessage, MessageType
            message = AgentMessage(
                sender=self.identifier,
                receiver="scrum_master",
                workspace=self.workspace,
                message_type=MessageType.TEST_FAILURE,
                payload={
                    "component": bug.get('component', 'unknown'),
                    "error": bug.get('error', 'mysterious curse'),
                    "severity": bug.get('severity', 'medium')
                },
                issue_id=issue_id
            )
            self.message_bus.dispatch(message)
        
        return self.chant(bug_msg)

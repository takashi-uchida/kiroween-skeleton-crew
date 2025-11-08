"""Frontend specialist spirit."""

from typing import Optional
from .base_agent import BaseSpirit


class FrontendSpirit(BaseSpirit):
    def __init__(self, *args, message_bus=None, workspace_manager=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_bus = message_bus
        self.workspace_manager = workspace_manager
    
    def receive_message(self, message) -> None:
        """Handle incoming Spirit Protocol messages."""
        if message.message_type == "task_assignment":
            self._handle_task_assignment(message)
        elif message.message_type == "api_ready":
            self._handle_api_ready(message)
    
    def _handle_task_assignment(self, message) -> None:
        """Process task assignment from Scrum Master."""
        task_id = message.payload.get("task_id")
        task_description = message.payload.get("task", "")
        issue_id = message.issue_id
        
        if task_id:
            self.assign_task(task_id)
            print(self.chant(f"Accepted UI task: {task_description}"))
            
            # Create branch for this task if workspace_manager is available
            if self.workspace_manager and issue_id:
                feature_name = task_description.lower().replace(" ", "-")
                branch = self.workspace_manager.create_branch(
                    self.identifier, 
                    feature_name, 
                    issue_id
                )
                print(self.chant(f"Created branch: {branch}"))
    
    def _handle_api_ready(self, message) -> None:
        """Handle notification that backend API is ready."""
        api_info = message.payload.get("api_info", {})
        print(self.chant(f"Backend API ready for integration: {api_info.get('endpoint', 'unknown')}"))
    
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
    
    def summon_ui(self) -> str:
        return self.chant("Sketching spectral UI components...")

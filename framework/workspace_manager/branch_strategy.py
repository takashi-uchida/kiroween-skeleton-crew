"""Branch naming and commit message formatting strategies.

This module implements the Spirit Protocol for commit messages and provides
utilities for generating and parsing feature branch names.
"""

import re
from typing import Dict, Optional


class BranchStrategy:
    """Handles branch naming conventions and Spirit Protocol commit formatting."""

    # Pattern for feature branch names
    BRANCH_PREFIX = "feature/task"
    BRANCH_PATTERN = re.compile(
        r"^feature/task-(?P<spec_id>[^-]+)-(?P<task_number>[^-]+)-(?P<description>.+)$"
    )

    # Invalid characters for git branch names
    INVALID_CHARS = re.compile(r"[^a-zA-Z0-9\-_/]")
    MULTIPLE_HYPHENS = re.compile(r"-+")

    @staticmethod
    def generate_branch_name(spec_id: str, task_number: str, description: str) -> str:
        """Generate a feature branch name following the pattern.

        Pattern: feature/task-{spec-id}-{task-number}-{description}

        Args:
            spec_id: The specification identifier
            task_number: The task number (e.g., "2" or "2.1")
            description: Brief description of the task

        Returns:
            Sanitized branch name following the convention

        Example:
            >>> BranchStrategy.generate_branch_name("kiro-workspace", "2", "implement branch strategy")
            'feature/task-kiro-workspace-2-implement-branch-strategy'
        """
        # Sanitize each component
        clean_spec_id = BranchStrategy._sanitize_component(spec_id)
        clean_task_number = BranchStrategy._sanitize_component(task_number)
        clean_description = BranchStrategy._sanitize_component(description)

        # Build branch name
        branch_name = f"{BranchStrategy.BRANCH_PREFIX}-{clean_spec_id}-{clean_task_number}-{clean_description}"

        return BranchStrategy.sanitize_branch_name(branch_name)

    @staticmethod
    def _sanitize_component(component: str) -> str:
        """Sanitize a single component of the branch name.

        Args:
            component: The component to sanitize

        Returns:
            Sanitized component with lowercase and hyphens
        """
        # Convert to lowercase
        component = component.lower()
        # Replace spaces with hyphens
        component = component.replace(" ", "-")
        # Remove invalid characters
        component = BranchStrategy.INVALID_CHARS.sub("", component)
        # Collapse multiple hyphens
        component = BranchStrategy.MULTIPLE_HYPHENS.sub("-", component)
        # Strip leading/trailing hyphens
        component = component.strip("-")

        return component

    @staticmethod
    def sanitize_branch_name(name: str) -> str:
        """Remove invalid git characters and ensure git compatibility.

        Git branch names cannot contain:
        - Spaces
        - Special characters like ~, ^, :, ?, *, [
        - Double dots (..)
        - End with a dot or slash
        - Contain consecutive slashes

        Args:
            name: The branch name to sanitize

        Returns:
            Sanitized branch name safe for git operations
        """
        # Replace spaces with hyphens
        name = name.replace(" ", "-")

        # Remove invalid characters (keep alphanumeric, hyphens, underscores, slashes)
        name = BranchStrategy.INVALID_CHARS.sub("", name)

        # Collapse multiple hyphens
        name = BranchStrategy.MULTIPLE_HYPHENS.sub("-", name)

        # Remove double slashes
        name = re.sub(r"/+", "/", name)

        # Remove leading/trailing slashes and hyphens
        name = name.strip("/-")

        # Ensure it doesn't end with .lock (git restriction)
        if name.endswith(".lock"):
            name = name[:-5]

        return name

    @staticmethod
    def parse_branch_name(branch_name: str) -> Optional[Dict[str, str]]:
        """Extract spec_id, task_number, and description from branch name.

        Args:
            branch_name: The branch name to parse

        Returns:
            Dictionary with 'spec_id', 'task_number', and 'description' keys,
            or None if the branch name doesn't match the expected pattern

        Example:
            >>> BranchStrategy.parse_branch_name("feature/task-kiro-workspace-2-implement-branch-strategy")
            {'spec_id': 'kiro-workspace', 'task_number': '2', 'description': 'implement-branch-strategy'}
        """
        match = BranchStrategy.BRANCH_PATTERN.match(branch_name)
        if not match:
            return None

        return {
            "spec_id": match.group("spec_id"),
            "task_number": match.group("task_number"),
            "description": match.group("description"),
        }

    @staticmethod
    def generate_commit_message(scope: str, description: str, task_id: Optional[str] = None) -> str:
        """Generate Spirit Protocol commit message.

        Format: spirit(scope): spell description

        The commit body includes the task ID for traceability.

        Args:
            scope: The scope of the change (e.g., 'workspace', 'git', 'state')
            description: Brief description of what the commit does
            task_id: Optional task identifier for traceability

        Returns:
            Formatted commit message following Spirit Protocol

        Example:
            >>> BranchStrategy.generate_commit_message("workspace", "implement branch strategy", "2")
            'spirit(workspace): spell implement branch strategy\\n\\nTask: 2'
        """
        # Sanitize scope and description
        clean_scope = scope.strip().lower()
        clean_description = description.strip()

        # Ensure description starts with lowercase (conventional commit style)
        if clean_description and clean_description[0].isupper():
            clean_description = clean_description[0].lower() + clean_description[1:]

        # Build commit message
        commit_msg = f"spirit({clean_scope}): spell {clean_description}"

        # Add task ID to body if provided
        if task_id:
            commit_msg += f"\n\nTask: {task_id}"

        return commit_msg

"""Workspace management utilities for branch + commit strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


def _slugify(value: str) -> str:
    """Convert arbitrary strings into git-friendly slugs."""
    slug = value.strip().lower().replace(" ", "-")
    safe_chars = []
    for char in slug:
        if char.isalnum() or char in {"-", "_"}:
            safe_chars.append(char)
        else:
            safe_chars.append("-")
    collapsed = []
    for char in safe_chars:
        if not collapsed or char != "-" or collapsed[-1] != "-":
            collapsed.append(char)
    return "".join(collapsed).strip("-")


@dataclass
class WorkspaceManager:
    """Manage branch naming + commit formatting for spirit workspaces."""

    workspace_root: Path | str
    branches_by_spirit: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.workspace_root = Path(self.workspace_root)

    def create_branch(self, spirit_id: str, feature: str, issue_id: Optional[str] = None) -> str:
        """Generate branch names using instance-based or issue-based formats."""
        role, instance = self._parse_spirit_identifier(spirit_id)
        feature_slug = _slugify(feature)
        issue_value = self._normalize_issue(issue_id) if issue_id else None

        if issue_value:
            branch = f"{role}/issue-{issue_value}-{feature_slug}"
        else:
            branch = f"{role}/spirit-{instance}/{feature_slug}"

        self.branches_by_spirit.setdefault(spirit_id, []).append(branch)
        return branch

    def format_commit_message(
        self,
        spirit_id: str,
        scope: str,
        description: str,
        issue_id: Optional[str] = None,
    ) -> str:
        """Return commit messages matching spec requirement 4.5."""
        _, instance = self._parse_spirit_identifier(spirit_id)
        scope_slug = _slugify(scope)
        description_clean = description.strip()
        base = f"spirit-{instance}({scope_slug}): {description_clean}"
        if issue_id:
            issue_value = self._normalize_issue(issue_id)
            return f"{base} [#{issue_value}]"
        return base

    def get_active_branches(self, spirit_id: str) -> List[str]:
        """Return tracked branches belonging to the provided spirit."""
        return list(self.branches_by_spirit.get(spirit_id, []))

    def _parse_spirit_identifier(self, spirit_id: str) -> tuple[str, str]:
        """Split identifiers like 'frontend_spirit_2' into components."""
        parts = spirit_id.split("_")
        if len(parts) < 3 or parts[-2] != "spirit":
            raise ValueError(f"Invalid spirit identifier: {spirit_id}")
        role = "_".join(parts[:-2])  # Join all parts except last two
        instance = parts[-1]
        return role, instance

    @staticmethod
    def _normalize_issue(issue_id: str) -> str:
        """Strip formatting like '#42' → '42'."""
        return issue_id.lstrip("#").strip()


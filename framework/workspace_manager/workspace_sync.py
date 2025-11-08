"""Sync state across multiple repos."""

from pathlib import Path


class WorkspaceSync:
    def __init__(self, workspaces: list[Path]):
        self.workspaces = workspaces

    def status(self) -> dict[str, bool]:
        report = {}
        for workspace in self.workspaces:
            report[str(workspace)] = workspace.exists()
        return report

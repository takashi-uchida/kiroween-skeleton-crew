"""Small wrapper around git commands for spirits."""

import subprocess
from pathlib import Path
from typing import List, Optional, Sequence


class GitOperationError(Exception):
    """Raised when a git operation fails."""
    pass


class GitOperations:
    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    def run(self, *args: Sequence[str]) -> None:
        subprocess.run(["git", *args], check=True, cwd=self.cwd)

    def clone(self, repo_url: str, target_path: Path) -> None:
        """Clone repository to target path.
        
        Args:
            repo_url: URL of the repository to clone
            target_path: Destination path for the cloned repository
            
        Raises:
            GitOperationError: If clone operation fails
        """
        try:
            subprocess.run(
                ["git", "clone", repo_url, str(target_path)],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"Failed to clone repository from {repo_url}: {e.stderr}"
            ) from e

    def create_branch(self, branch_name: str, checkout: bool = True) -> None:
        """Create new branch and optionally checkout.
        
        Args:
            branch_name: Name of the branch to create
            checkout: Whether to checkout the branch after creation
            
        Raises:
            GitOperationError: If branch creation fails
        """
        try:
            # Check if branch already exists
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                raise GitOperationError(
                    f"Branch '{branch_name}' already exists"
                )
            
            # Create the branch
            if checkout:
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    check=True,
                    cwd=self.cwd,
                    capture_output=True,
                    text=True
                )
            else:
                subprocess.run(
                    ["git", "branch", branch_name],
                    check=True,
                    cwd=self.cwd,
                    capture_output=True,
                    text=True
                )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"Failed to create branch '{branch_name}': {e.stderr}"
            ) from e

    def commit(self, message: str, files: Optional[List[Path]] = None) -> None:
        """Commit changes with message.
        
        Args:
            message: Commit message
            files: Optional list of specific files to commit. If None, commits all staged changes.
            
        Raises:
            GitOperationError: If commit operation fails
        """
        try:
            # Stage files if specified
            if files:
                for file in files:
                    subprocess.run(
                        ["git", "add", str(file)],
                        check=True,
                        cwd=self.cwd,
                        capture_output=True,
                        text=True
                    )
            
            # Commit the changes
            subprocess.run(
                ["git", "commit", "-m", message],
                check=True,
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"Failed to commit changes: {e.stderr}"
            ) from e

    def push(self, branch: str, set_upstream: bool = True) -> None:
        """Push branch to remote.
        
        Args:
            branch: Name of the branch to push
            set_upstream: Whether to set upstream tracking
            
        Raises:
            GitOperationError: If push operation fails
        """
        try:
            cmd = ["git", "push"]
            if set_upstream:
                cmd.extend(["-u", "origin", branch])
            else:
                cmd.extend(["origin", branch])
            
            subprocess.run(
                cmd,
                check=True,
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"Failed to push branch '{branch}': {e.stderr}"
            ) from e

    def get_current_branch(self) -> str:
        """Get current branch name.
        
        Returns:
            Name of the current branch
            
        Raises:
            GitOperationError: If unable to determine current branch
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"Failed to get current branch: {e.stderr}"
            ) from e

    def is_clean(self) -> bool:
        """Check if working directory is clean.
        
        Returns:
            True if working directory has no uncommitted changes, False otherwise
            
        Raises:
            GitOperationError: If unable to check status
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                cwd=self.cwd,
                capture_output=True,
                text=True
            )
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"Failed to check working directory status: {e.stderr}"
            ) from e

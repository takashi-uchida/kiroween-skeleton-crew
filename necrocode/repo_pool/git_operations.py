"""Git operations abstraction for Repo Pool Manager."""

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from necrocode.repo_pool.exceptions import GitOperationError
from necrocode.repo_pool.models import GitResult


class GitOperations:
    """Git command abstraction with error handling and retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize GitOperations.
        
        Args:
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _run_git_command(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        retry: bool = True
    ) -> GitResult:
        """
        Run a git command with retry logic.
        
        Args:
            command: Git command as list of strings
            cwd: Working directory for the command
            retry: Whether to retry on failure
            
        Returns:
            GitResult with command execution details
            
        Raises:
            GitOperationError: If command fails after all retries
        """
        cmd_str = " ".join(command)
        attempts = self.max_retries if retry else 1
        
        for attempt in range(1, attempts + 1):
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    command,
                    cwd=str(cwd) if cwd else None,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                duration = time.time() - start_time
                
                git_result = GitResult(
                    success=result.returncode == 0,
                    command=cmd_str,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    duration_seconds=duration
                )
                
                if git_result.success:
                    return git_result
                
                # If not successful and we have retries left, continue
                if attempt < attempts:
                    time.sleep(self.retry_delay)
                    continue
                
                # Last attempt failed
                raise GitOperationError(
                    f"Git command failed after {attempts} attempts: {cmd_str}\n"
                    f"Exit code: {result.returncode}\n"
                    f"Stderr: {result.stderr}"
                )
                
            except subprocess.TimeoutExpired as e:
                duration = time.time() - start_time
                if attempt < attempts:
                    time.sleep(self.retry_delay)
                    continue
                    
                raise GitOperationError(
                    f"Git command timed out after {attempts} attempts: {cmd_str}"
                ) from e
                
            except Exception as e:
                duration = time.time() - start_time
                if attempt < attempts:
                    time.sleep(self.retry_delay)
                    continue
                    
                raise GitOperationError(
                    f"Git command failed with exception after {attempts} attempts: {cmd_str}\n"
                    f"Error: {str(e)}"
                ) from e
        
        # Should not reach here, but for type safety
        raise GitOperationError(f"Unexpected error in git command: {cmd_str}")
    
    # ===== Basic Git Operations (Task 2.1) =====
    
    def clone_repo(self, repo_url: str, target_dir: Path) -> GitResult:
        """
        Clone a repository.
        
        Args:
            repo_url: Repository URL to clone
            target_dir: Target directory for the clone
            
        Returns:
            GitResult with clone operation details
            
        Raises:
            GitOperationError: If clone fails after retries
        """
        # Ensure parent directory exists
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        
        command = ["git", "clone", repo_url, str(target_dir)]
        return self._run_git_command(command, retry=True)
    
    def fetch_all(self, repo_dir: Path) -> GitResult:
        """
        Fetch all remote branches.
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            GitResult with fetch operation details
            
        Raises:
            GitOperationError: If fetch fails after retries
        """
        command = ["git", "fetch", "--all", "--prune"]
        return self._run_git_command(command, cwd=repo_dir, retry=True)
    
    def clean(self, repo_dir: Path, force: bool = True) -> GitResult:
        """
        Remove untracked files from working directory.
        
        Args:
            repo_dir: Repository directory
            force: Force removal of untracked files and directories
            
        Returns:
            GitResult with clean operation details
            
        Raises:
            GitOperationError: If clean fails after retries
        """
        flags = "-fdx" if force else "-fd"
        command = ["git", "clean", flags]
        return self._run_git_command(command, cwd=repo_dir, retry=True)
    
    def reset_hard(self, repo_dir: Path, ref: str = "HEAD") -> GitResult:
        """
        Reset working directory to a specific ref.
        
        Args:
            repo_dir: Repository directory
            ref: Git reference to reset to (default: HEAD)
            
        Returns:
            GitResult with reset operation details
            
        Raises:
            GitOperationError: If reset fails after retries
        """
        command = ["git", "reset", "--hard", ref]
        return self._run_git_command(command, cwd=repo_dir, retry=True)
    
    # ===== Branch Operations (Task 2.2) =====
    
    def checkout(self, repo_dir: Path, branch: str) -> GitResult:
        """
        Checkout a branch.
        
        Args:
            repo_dir: Repository directory
            branch: Branch name to checkout
            
        Returns:
            GitResult with checkout operation details
            
        Raises:
            GitOperationError: If checkout fails after retries
        """
        command = ["git", "checkout", branch]
        return self._run_git_command(command, cwd=repo_dir, retry=True)
    
    def get_current_branch(self, repo_dir: Path) -> str:
        """
        Get current branch name.
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            Current branch name
            
        Raises:
            GitOperationError: If command fails
        """
        command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        result = self._run_git_command(command, cwd=repo_dir, retry=False)
        return result.stdout.strip()
    
    def get_current_commit(self, repo_dir: Path) -> str:
        """
        Get current commit hash.
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            Current commit hash (full SHA)
            
        Raises:
            GitOperationError: If command fails
        """
        command = ["git", "rev-parse", "HEAD"]
        result = self._run_git_command(command, cwd=repo_dir, retry=False)
        return result.stdout.strip()
    
    def list_remote_branches(self, repo_dir: Path) -> List[str]:
        """
        Get list of remote branches.
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            List of remote branch names (without 'origin/' prefix)
            
        Raises:
            GitOperationError: If command fails
        """
        command = ["git", "branch", "-r"]
        result = self._run_git_command(command, cwd=repo_dir, retry=False)
        
        branches = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or "->" in line:  # Skip empty lines and HEAD pointer
                continue
            # Remove 'origin/' prefix if present
            if line.startswith("origin/"):
                line = line[7:]
            branches.append(line)
        
        return branches
    
    def is_clean_working_tree(self, repo_dir: Path) -> bool:
        """
        Check if working tree is clean (no uncommitted changes).
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            True if working tree is clean, False otherwise
        """
        try:
            command = ["git", "status", "--porcelain"]
            result = self._run_git_command(command, cwd=repo_dir, retry=False)
            return len(result.stdout.strip()) == 0
        except GitOperationError:
            return False
    
    # ===== Parallel Operations (Task 10.1) =====
    
    def fetch_all_parallel(
        self,
        repo_dirs: List[Path],
        max_workers: Optional[int] = None
    ) -> Dict[str, GitResult]:
        """
        Fetch all remote branches for multiple repositories in parallel.
        
        This method uses ThreadPoolExecutor to run git fetch operations
        concurrently, significantly reducing total fetch time when working
        with multiple slots.
        
        Args:
            repo_dirs: List of repository directories to fetch
            max_workers: Maximum number of parallel workers (default: min(32, len(repo_dirs)))
            
        Returns:
            Dictionary mapping repo_dir path to GitResult
            
        Requirements: 10.1
        """
        if not repo_dirs:
            return {}
        
        # Default to reasonable number of workers
        if max_workers is None:
            max_workers = min(32, len(repo_dirs))
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_repo = {
                executor.submit(self.fetch_all, repo_dir): repo_dir
                for repo_dir in repo_dirs
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_repo):
                repo_dir = future_to_repo[future]
                try:
                    result = future.result()
                    results[str(repo_dir)] = result
                except Exception as e:
                    # Create error result for failed fetch
                    results[str(repo_dir)] = GitResult(
                        success=False,
                        command=f"git fetch --all --prune (parallel)",
                        stdout="",
                        stderr=str(e),
                        exit_code=-1,
                        duration_seconds=0.0
                    )
        
        return results

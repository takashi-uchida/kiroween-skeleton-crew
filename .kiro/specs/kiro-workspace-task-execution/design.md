# Design Document: Kiro Workspace Task Execution

## Overview

This design implements a workspace management system that enables Kiro to execute spec tasks in isolated git repositories. The system clones target repositories into workspace subdirectories, manages feature branches per task, and enforces the Spirit Protocol commit format. This architecture supports concurrent execution of multiple specs without conflicts.

## Architecture

### Component Hierarchy

```
WorkspaceManager (orchestrator)
├── WorkspaceConfig (configuration)
├── GitOperations (existing, enhanced)
├── BranchStrategy (naming & lifecycle)
└── StateTracker (persistence)
```

### Key Design Decisions

1. **Workspace Isolation**: Each spec gets its own cloned repository to prevent conflicts
2. **State Persistence**: JSON-based state file for tracking workspaces across sessions
3. **Branch Naming Convention**: `feature/task-{spec-id}-{task-number}-{description}` for clarity
4. **Single Responsibility**: Separate classes for git ops, branch management, and state tracking
5. **Existing Integration**: Enhance existing `GitOperations` class rather than replacing it

## Components and Interfaces

### WorkspaceManager

Main orchestrator for workspace lifecycle management.

```python
class WorkspaceManager:
    def __init__(self, base_path: Path, state_file: Path):
        """Initialize with base directory for all workspaces."""
        
    def create_workspace(self, spec_name: str, repo_url: str) -> Workspace:
        """Clone repository into spec-named subdirectory."""
        
    def get_workspace(self, spec_name: str) -> Workspace | None:
        """Retrieve existing workspace by spec name."""
        
    def list_workspaces(self) -> list[WorkspaceInfo]:
        """List all active workspaces with their status."""
        
    def cleanup_workspace(self, spec_name: str, force: bool = False) -> None:
        """Remove workspace directory and update state."""
```

### Workspace

Represents a single workspace instance with git operations.

```python
class Workspace:
    def __init__(self, path: Path, spec_name: str, git_ops: GitOperations):
        """Initialize workspace with path and git operations."""
        
    def create_task_branch(self, task_id: str, task_description: str) -> str:
        """Create and checkout feature branch for task."""
        
    def commit_task(self, task_id: str, scope: str, description: str, files: list[Path]) -> None:
        """Commit changes following Spirit Protocol format."""
        
    def push_branch(self, branch_name: str) -> None:
        """Push feature branch to remote."""
        
    def get_current_branch(self) -> str:
        """Get name of current branch."""
        
    def is_clean(self) -> bool:
        """Check if working directory has uncommitted changes."""
```

### BranchStrategy

Handles branch naming and validation.

```python
class BranchStrategy:
    @staticmethod
    def generate_branch_name(spec_id: str, task_number: str, description: str) -> str:
        """Generate branch name: feature/task-{spec-id}-{task-number}-{description}."""
        
    @staticmethod
    def sanitize_branch_name(name: str) -> str:
        """Remove invalid characters and ensure git compatibility."""
        
    @staticmethod
    def parse_branch_name(branch_name: str) -> dict[str, str]:
        """Extract spec_id, task_number, description from branch name."""
        
    @staticmethod
    def generate_commit_message(scope: str, description: str, task_id: str) -> str:
        """Generate Spirit Protocol commit: spirit(scope): description."""
```

### StateTracker

Manages workspace state persistence.

```python
class StateTracker:
    def __init__(self, state_file: Path):
        """Initialize with path to state JSON file."""
        
    def save_workspace(self, workspace_info: WorkspaceInfo) -> None:
        """Persist workspace information to state file."""
        
    def load_workspace(self, spec_name: str) -> WorkspaceInfo | None:
        """Load workspace info from state file."""
        
    def list_all(self) -> list[WorkspaceInfo]:
        """Return all tracked workspaces."""
        
    def remove_workspace(self, spec_name: str) -> None:
        """Remove workspace from state tracking."""
        
    def update_task_status(self, spec_name: str, task_id: str, status: str) -> None:
        """Update completion status for a task."""
```

### WorkspaceConfig

Configuration data class.

```python
@dataclass
class WorkspaceConfig:
    base_path: Path
    state_file: Path
    gitignore_path: Path
    auto_push: bool = True
    auto_pr: bool = False
```

### WorkspaceInfo

State data class.

```python
@dataclass
class WorkspaceInfo:
    spec_name: str
    workspace_path: Path
    repo_url: str
    current_branch: str
    created_at: str
    tasks_completed: list[str]
    status: str  # 'active', 'completed', 'error'
```

## Data Models

### State File Format (JSON)

```json
{
  "workspaces": {
    "kiro-workspace-task-execution": {
      "spec_name": "kiro-workspace-task-execution",
      "workspace_path": "./workspace-kiro-workspace-task-execution",
      "repo_url": "https://github.com/user/repo.git",
      "current_branch": "feature/task-kiro-1-1-workspace-manager",
      "created_at": "2025-11-09T10:30:00Z",
      "tasks_completed": ["1.1", "1.2"],
      "status": "active"
    }
  }
}
```

### .gitignore Entry

```
# Kiro workspace directories
workspace-*/
.kiro/workspace-state.json
```

## Error Handling

### Clone Failures
- Verify network connectivity
- Check repository URL validity
- Provide clear error messages with suggested fixes
- Rollback: Remove partially created workspace directory

### Branch Conflicts
- Check if branch already exists before creation
- Offer to checkout existing branch or create with suffix
- Prevent force-push without explicit user confirmation

### Dirty Working Directory
- Check `git status` before branch operations
- Prompt user to commit or stash changes
- Provide option to auto-stash with recovery

### State File Corruption
- Validate JSON structure on load
- Create backup before writes
- Fallback to empty state if corrupted
- Log corruption events for debugging

## Testing Strategy

### Unit Tests

1. **BranchStrategy Tests**
   - Branch name generation with various inputs
   - Sanitization of special characters
   - Commit message formatting
   - Branch name parsing

2. **StateTracker Tests**
   - Save and load workspace info
   - Handle missing state file
   - Handle corrupted JSON
   - Concurrent access safety

3. **WorkspaceManager Tests**
   - Workspace creation flow
   - Duplicate workspace handling
   - Cleanup operations
   - State synchronization

### Integration Tests

1. **End-to-End Workflow**
   - Create workspace → create branch → commit → push
   - Multiple concurrent workspaces
   - State persistence across restarts

2. **Git Operations**
   - Clone real repository
   - Create and switch branches
   - Commit with Spirit Protocol format
   - Push to remote (using test repository)

### Test Fixtures

- Mock git repository structure
- Sample state JSON files
- Test workspace directories (auto-cleaned)
- Mock GitOperations for unit tests

## Implementation Notes

### Enhancing Existing GitOperations

The existing `GitOperations` class will be extended with additional methods:

```python
def clone(self, repo_url: str, target_path: Path) -> None:
    """Clone repository to target path."""
    
def create_branch(self, branch_name: str, checkout: bool = True) -> None:
    """Create new branch and optionally checkout."""
    
def commit(self, message: str, files: list[Path] | None = None) -> None:
    """Commit changes with message."""
    
def push(self, branch: str, set_upstream: bool = True) -> None:
    """Push branch to remote."""
    
def get_current_branch(self) -> str:
    """Get current branch name."""
    
def is_clean(self) -> bool:
    """Check if working directory is clean."""
```

### Integration with Kiro Spec Workflow

When a user clicks "Start task" in the tasks.md file:

1. Kiro checks if workspace exists for this spec
2. If not, prompts for repository URL and creates workspace
3. Creates feature branch for the task
4. Executes task implementation
5. Commits changes with Spirit Protocol format
6. Pushes branch and optionally creates PR
7. Updates task checkbox in tasks.md
8. Updates state file

### Configuration Location

Workspace configuration will be stored in `.kiro/workspace-config.json`:

```json
{
  "base_path": ".",
  "state_file": ".kiro/workspace-state.json",
  "gitignore_path": ".gitignore",
  "auto_push": true,
  "auto_pr": false
}
```

## Future Enhancements

1. **PR Template Integration**: Auto-generate PR descriptions from task details
2. **Multi-Remote Support**: Handle forks and upstream repositories
3. **Workspace Templates**: Pre-configured workspace setups for common project types
4. **Conflict Resolution**: Interactive merge conflict resolution
5. **Workspace Sharing**: Export/import workspace state for team collaboration

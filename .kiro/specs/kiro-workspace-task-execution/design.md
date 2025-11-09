# Design Document: Kiro Workspace Task Execution

## Overview

This design implements a workspace management system that enables Kiro to execute spec tasks in isolated git repositories using AI-powered agents. The system integrates the strandsagents library to leverage OpenAI LLMs for code generation, clones target repositories into workspace subdirectories, manages feature branches per task, and enforces the Spirit Protocol commit format. This architecture supports concurrent execution of multiple specs without conflicts while automating code implementation through AI.

## Architecture

### Component Hierarchy

```
TaskExecutionOrchestrator (top-level coordinator)
├── SpecTaskRunner (task parsing & execution)
│   ├── StrandsAgent (AI-powered code generation)
│   │   └── OpenAIChatClient (LLM communication)
│   └── Task Parser (tasks.md parsing)
├── WorkspaceManager (workspace lifecycle)
│   ├── WorkspaceConfig (configuration)
│   ├── GitOperations (existing, enhanced)
│   ├── BranchStrategy (naming & lifecycle)
│   └── StateTracker (persistence)
└── Integration Layer (connects agents to workspace)
```

### Key Design Decisions

1. **AI-Powered Execution**: Use StrandsAgent with OpenAI LLMs for automated code generation
2. **Workspace Isolation**: Each spec gets its own cloned repository to prevent conflicts
3. **State Persistence**: JSON-based state file for tracking workspaces across sessions
4. **Branch Naming Convention**: `feature/task-{spec-id}-{task-number}-{description}` for clarity
5. **Single Responsibility**: Separate classes for git ops, branch management, state tracking, and AI execution
6. **Existing Integration**: Enhance existing `GitOperations` class and integrate strandsagents library
7. **Default LLM Model**: Use gpt-5-codex medium as the default model for reliable code generation

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

### SpecTaskRunner

Parses tasks from tasks.md and executes them via StrandsAgent.

```python
class SpecTaskRunner:
    def __init__(
        self,
        agent: StrandsAgent | None = None,
        model: str = "gpt-5-codex",
        llm_client: OpenAIChatClient | None = None,
    ):
        """Initialize with optional custom agent or model."""
        
    def load_tasks(self, tasks_path: Path) -> list[SpecTask]:
        """Parse tasks.md file and extract task information."""
        
    def run(self, tasks_path: Path) -> list[dict]:
        """Execute all tasks from tasks.md file."""
        
    def run_single_task(self, task: SpecTask, context: dict | None = None) -> dict:
        """Execute a single task with optional context."""
```

### StrandsAgent

LLM-backed agent that generates code implementations.

```python
class StrandsAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str | None = None,
        model: str = "gpt-5-codex",
        llm_client: OpenAIChatClient | None = None,
        temperature: float = 0.2,
        max_tokens: int = 900,
    ):
        """Initialize agent with LLM configuration."""
        
    def run_task(self, task: StrandsTask, context: dict | None = None) -> dict:
        """Execute task via LLM and return generated implementation."""
        
    def _render_prompt(self, task: StrandsTask, context: dict) -> str:
        """Format task information into LLM prompt."""
```

### OpenAIChatClient

Handles communication with OpenAI API.

```python
class OpenAIChatClient:
    def __init__(
        self,
        model: str = "gpt-5-codex",
        api_key: str | None = None,
        api_base: str = "https://api.openai.com/v1",
        timeout: int = 60,
    ):
        """Initialize with API configuration."""
        
    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        """Send messages to OpenAI and return completion."""
```

### TaskExecutionOrchestrator

Coordinates task execution with workspace management.

```python
class TaskExecutionOrchestrator:
    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        spec_task_runner: SpecTaskRunner,
    ):
        """Initialize with workspace manager and task runner."""
        
    def execute_task(
        self,
        spec_name: str,
        task_id: str,
        tasks_path: Path,
        requirements_path: Path | None = None,
        design_path: Path | None = None,
    ) -> dict:
        """Execute a single task: parse → generate code → commit → push."""
        
    def execute_all_tasks(
        self,
        spec_name: str,
        tasks_path: Path,
        requirements_path: Path | None = None,
        design_path: Path | None = None,
    ) -> list[dict]:
        """Execute all tasks from a spec sequentially."""
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

### OpenAI API Failures
- Check for OPENAI_API_KEY environment variable before execution
- Provide clear error message if API key is missing
- Handle HTTP errors (rate limits, authentication failures, timeouts)
- Retry with exponential backoff for transient failures
- Log API errors with request details for debugging

### Task Parsing Failures
- Validate tasks.md format before parsing
- Handle malformed task entries gracefully
- Provide line numbers for parsing errors
- Skip invalid tasks and continue with valid ones
- Log parsing warnings for user review

### Code Generation Failures
- Validate LLM output before writing to files
- Handle incomplete or malformed code responses
- Provide option to retry with different prompt
- Save failed attempts for debugging
- Allow manual intervention when AI generation fails

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
- Mock OpenAIChatClient (StubLLMClient) for testing without API calls
- Sample tasks.md files with various task formats
- Sample requirements.md and design.md for context testing

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
3. TaskExecutionOrchestrator loads task from tasks.md via SpecTaskRunner
4. Creates feature branch for the task via WorkspaceManager
5. Loads requirements.md and design.md as context (if available)
6. StrandsAgent generates code implementation via OpenAI LLM
7. Generated code is written to workspace files
8. Commits changes with Spirit Protocol format via WorkspaceManager
9. Pushes branch and optionally creates PR
10. Updates task checkbox in tasks.md
11. Updates state file with task completion

### AI Agent Context Building

To ensure high-quality code generation, the system provides rich context to the LLM:

```python
context = {
    "task_id": "1.1",
    "task_title": "Implement WorkspaceManager",
    "description": "Create main orchestrator for workspace lifecycle...",
    "checklist": ["Initialize with base directory", "Implement create_workspace", ...],
    "requirements": "Content from requirements.md",
    "design": "Content from design.md",
    "existing_code": "Relevant existing code from workspace",
}
```

The StrandsAgent formats this into a comprehensive prompt that includes:
- System role definition (technical writer and engineer)
- Task objectives and acceptance criteria
- Design constraints and patterns
- Request for clear plan and verification steps

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

## Data Flow

### Task Execution Flow

```
User clicks "Start task" in tasks.md
    ↓
TaskExecutionOrchestrator.execute_task()
    ↓
SpecTaskRunner.load_tasks() → Parse tasks.md
    ↓
Load context (requirements.md, design.md)
    ↓
WorkspaceManager.create_task_branch() → Create feature branch
    ↓
StrandsAgent.run_task() → Generate code via OpenAI
    ↓
OpenAIChatClient.complete() → Call OpenAI API
    ↓
Write generated code to workspace files
    ↓
WorkspaceManager.commit_task() → Commit with Spirit Protocol
    ↓
WorkspaceManager.push_branch() → Push to remote
    ↓
StateTracker.update_task_status() → Update state file
    ↓
Return execution result to user
```

## Future Enhancements

1. **PR Template Integration**: Auto-generate PR descriptions from task details
2. **Multi-Remote Support**: Handle forks and upstream repositories
3. **Workspace Templates**: Pre-configured workspace setups for common project types
4. **Conflict Resolution**: Interactive merge conflict resolution
5. **Workspace Sharing**: Export/import workspace state for team collaboration
6. **Multi-Model Support**: Allow switching between different LLM providers (Anthropic, local models)
7. **Incremental Context**: Load only relevant code files instead of entire codebase
8. **Code Review Agent**: Separate agent for reviewing generated code before commit
9. **Test Generation**: Automatically generate tests for implemented code
10. **Rollback Support**: Undo task execution and restore previous state

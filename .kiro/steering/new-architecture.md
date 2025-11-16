# NecroCode v2: Kiro-Native Architecture

## Core Insight
**Kiro IS the agent.** We don't need to simulate multiple agents - we need to orchestrate Kiro instances working on different branches.

## Architecture Overview

```
User Input: "Create a chat app"
     ↓
[Task Planner] - Breaks down into tasks
     ↓
[Task Queue] - Stores tasks with metadata
     ↓
[Kiro Orchestrator] - Executes tasks SEQUENTIALLY
     ↓
For Each Task (in dependency order):
  1. Checkout new branch
  2. Write task context to .kiro/current-task.md
  3. Trigger Kiro Hook (or manual execution)
  4. Kiro implements solution
  5. Commit changes
  6. Create PR
  7. Move to next task
```

**Note**: Parallel execution is NOT feasible with current Kiro architecture.
Tasks are executed sequentially, respecting dependencies.

## Key Components

### 1. Task Planner (Python)
**Purpose**: Convert job description into structured tasks

```python
class TaskPlanner:
    def plan(self, job_description: str) -> List[Task]:
        """
        Uses Kiro to analyze job description and create task breakdown
        Returns structured task list with:
        - task_id
        - title
        - description
        - dependencies
        - estimated_complexity
        - required_skills (frontend/backend/db/etc)
        """
```

**Output Format** (`.kiro/tasks/{project}/tasks.json`):
```json
{
  "project": "chat-app",
  "tasks": [
    {
      "id": "1",
      "title": "Setup database schema",
      "description": "Create User and Message models with MongoDB",
      "dependencies": [],
      "type": "backend",
      "files_to_create": ["models/User.js", "models/Message.js"],
      "acceptance_criteria": [
        "User model has email, password, username fields",
        "Message model has sender, content, timestamp"
      ]
    },
    {
      "id": "2",
      "title": "Implement JWT authentication",
      "description": "Add login/register endpoints with JWT",
      "dependencies": ["1"],
      "type": "backend",
      "files_to_create": ["routes/auth.js", "middleware/auth.js"]
    }
  ]
}
```

### 2. Kiro Orchestrator (Python)
**Purpose**: Manage parallel Kiro sessions

```python
class KiroOrchestrator:
    def execute_tasks(self, project: str):
        """
        1. Load tasks from .kiro/tasks/{project}/tasks.json
        2. Resolve dependencies (topological sort)
        3. For each ready task:
           - Create branch: feature/task-{id}-{slug}
           - Write task context to .kiro/current-task.md
           - Invoke Kiro via CLI/API
           - Monitor completion
           - Create PR via GitHub API
        """
```

### 3. Task Context File
**Purpose**: Give Kiro all context needed for a task

**Location**: `.kiro/current-task.md` (temporary, per session)

```markdown
# Task: Implement JWT Authentication

## Task ID
2

## Description
Add login and register endpoints with JWT token generation and validation.

## Dependencies Completed
- Task 1: Database schema (User model exists)

## Files to Create/Modify
- `routes/auth.js` - Login/register endpoints
- `middleware/auth.js` - JWT validation middleware
- `tests/auth.test.js` - Unit tests

## Acceptance Criteria
- [ ] POST /api/auth/register creates new user
- [ ] POST /api/auth/login returns JWT token
- [ ] Middleware validates JWT on protected routes
- [ ] Passwords are hashed with bcrypt
- [ ] Tests cover happy path and error cases

## Technical Context
- Stack: Node.js + Express + MongoDB
- JWT library: jsonwebtoken
- Password hashing: bcrypt
- Existing code: models/User.js (from Task 1)

## Related Files
#[[file:models/User.js]]
#[[file:package.json]]
```

### 4. Kiro Hook: Auto-Execute Task
**Purpose**: Trigger Kiro when task context is written

**Location**: `.kiro/hooks/on_task_ready.py`

```python
# Trigger: When .kiro/current-task.md is created/updated
# Action: Execute task implementation

def on_task_ready(context):
    task_file = Path(".kiro/current-task.md")
    if task_file.exists():
        # Kiro reads the task context
        # Implements the solution
        # Commits with format: "feat(task-{id}): {title}"
        # Marks task as complete
        pass
```

### 5. GitHub Integration
**Purpose**: Create PRs automatically

```python
class GitHubIntegration:
    def create_pr(self, branch: str, task: Task):
        """
        Creates PR with:
        - Title: "Task {id}: {title}"
        - Body: Task description + acceptance criteria
        - Labels: task.type (backend/frontend/etc)
        - Reviewers: (optional)
        """
```

## Workflow Example

### Step 1: User Input
```bash
python necrocode.py "Create a real-time chat app with authentication"
```

### Step 2: Task Planning
```
[Task Planner] Analyzing requirements...
Created 8 tasks:
  1. Database schema (backend)
  2. JWT authentication (backend)
  3. WebSocket server (backend)
  4. Login UI (frontend)
  5. Chat interface (frontend)
  6. Message persistence (backend)
  7. User presence (backend)
  8. Integration tests (qa)
```

### Step 3: Sequential Execution
```
[Orchestrator] Starting task execution...

Task 1:
  ✓ Branch created: feature/task-1-database-schema
  ✓ Task context written to .kiro/current-task.md
  ✓ Kiro Hook triggered (or manual: "Kiro, implement current task")
  ✓ Files created: models/User.js, models/Message.js
  ✓ Committed: feat(task-1): setup database schema
  ✓ PR created: #101
  ✓ Merged to main

Task 2 (depends on Task 1):
  ✓ Branch created: feature/task-2-jwt-auth
  ✓ Task context written (includes Task 1 results)
  ✓ Kiro implements...
  ✓ Committed: feat(task-2): implement JWT authentication
  ✓ PR created: #102
  ...
```

## Key Differences from Old Architecture

### Old (Spirit-based)
- ❌ Abstract "spirits" that don't map to real capabilities
- ❌ Complex inter-spirit communication
- ❌ Simulated parallelism
- ❌ No clear execution model

### New (Kiro-native)
- ✅ Kiro is the agent (real, not simulated)
- ✅ Simple task queue with dependencies
- ✅ Sequential execution (realistic for single Kiro instance)
- ✅ Clear execution: 1 task = 1 branch = 1 PR
- ✅ Leverages Kiro's actual strengths (code generation, file manipulation)
- ✅ Can be semi-automated with Hooks or fully manual

## Implementation Priority

1. **Task Planner** - Convert job description to tasks.json
2. **Task Context Generator** - Create .kiro/current-task.md
3. **Manual Execution** - User runs Kiro with task context
4. **Git Automation** - Auto-create branches and commits
5. **GitHub Integration** - Auto-create PRs
6. **Orchestrator** - Sequential task execution with Hooks

## Execution Modes

### Mode 1: Fully Manual
```bash
python necrocode.py plan "Create chat app"  # Creates tasks.json
python necrocode.py next                     # Writes current-task.md
# User: "Kiro, implement the current task"
python necrocode.py complete                 # Commits & creates PR
python necrocode.py next                     # Next task
```

### Mode 2: Semi-Automated (Hooks)
```bash
python necrocode.py plan "Create chat app"
python necrocode.py start                    # Starts orchestrator
# Orchestrator writes task context
# Kiro Hook triggers automatically
# User reviews and approves
# Moves to next task
```

### Mode 3: Batch Mode (Future)
```bash
python necrocode.py batch "Create chat app"
# Executes all tasks overnight
# Creates multiple PRs
# User reviews in the morning
```

## References

### Claude Agent Skills
- Use structured task definitions
- Clear acceptance criteria
- File-level context

### cc-sdd Pattern
- Specification-driven development
- Task breakdown with dependencies
- Automated execution

### Kiro Features to Leverage
- Specs for task definitions
- Hooks for automation
- File context (#[[file:...]])
- Git operations
- Diagnostic tools

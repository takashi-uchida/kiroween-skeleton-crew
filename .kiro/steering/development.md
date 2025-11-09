# NecroCode Development Guide
## Quick Reference
- **Purpose**: Guide spirits through implementation details.
- **Audience**: Contributors executing tasks, DocumentationSpirit, Dev/QA spirits.
- **Cross-Links**: Product overview → overview.md, system design → architecture.md.
## Directory Structure & Conventions
```
necrocode/                              # Root directory
├── .kiro/                              # Kiro configuration
│   ├── steering/                       # Framework documentation
│   │   ├── product.md                  # Product overview
│   │   ├── tech.md                     # Technical stack
│   │   ├── structure.md                # This file
│   │   └── spirit-workflow.md           # Spirit collaboration flow
│   │
│   ├── specs/                          # Spec definitions
│   │   ├── necrocode-spirit-orchestration/
│   │   │   ├── requirements.md
│   │   │   ├── design.md
│   │   │   └── tasks.md
│   │   ├── kiro-workspace-task-execution/
│   │   │   ├── requirements.md
│   │   │   ├── design.md
│   │   │   └── tasks.md
│   │   └── spirit-protocol/
│   │       ├── requirements.md
│   │       ├── design.md
│   │       └── tasks.md
│   │
│   ├── hooks/                          # Spirit hooks
│   │   ├── on_spec_complete.py
│   │   ├── on_task_start.py
│   │   └── on_task_complete.py
│   │
│   └── workspace-state.json            # Active workspace tracking
│
├── framework/                          # Core framework
│   ├── necromancer/
│   │   ├── __init__.py
│   │   ├── necromancer.py              # Main necromancer
│   │   ├── job_parser.py               # Parse job descriptions
│   │   ├── issue_router.py             # Route tasks to spirits
│   │   └── spec_generator.py           # Generate specs
│   │
│   ├── spirits/
│   │   ├── __init__.py
│   │   ├── base_spirit.py               # Base spirit class
│   │   ├── architect_spirit.py          # Spec creation
│   │   ├── scrum_master_spirit.py       # Task breakdown
│   │   ├── frontend_spirit.py           # Frontend development
│   │   ├── backend_spirit.py            # Backend development
│   │   ├── database_spirit.py           # Database design
│   │   ├── qa_spirit.py                 # Testing
│   │   └── devops_spirit.py             # Deployment
│   │
│   ├── workspace_manager/
│   │   ├── __init__.py
│   │   ├── workspace_manager.py        # Workspace orchestration
│   │   ├── workspace.py                # Single workspace
│   │   ├── branch_strategy.py          # Branch naming
│   │   ├── state_tracker.py            # State persistence
│   │   └── git_operations.py           # Git commands
│   │
│   ├── communication/
│   │   ├── __init__.py
│   │   ├── spirit_protocol.py          # Protocol implementation
│   │   └── message_bus.py              # Event coordination
│   │
│   └── task_executor/
│       ├── __init__.py
│       ├── task_loader.py              # Load tasks from specs
│       └── task_tracker.py             # Track task progress
│
├── examples/                           # Demo applications
│   ├── workspace1/                     # Sample: Collaboration tool
│   │   ├── README.md                   # "Built with NecroCode"
│   │   ├── .kiro/
│   │   │   └── specs/
│   │   │       └── whiteboard-app/
│   │   │           ├── requirements.md
│   │   │           ├── design.md
│   │   │           └── tasks.md
│   │   ├── frontend/
│   │   ├── backend/
│   │   └── ...
│   │
│   └── workspace2/                     # Sample: IoT dashboard
│       ├── README.md                   # "Built with NecroCode"
│       ├── .kiro/
│       │   └── specs/
│       │       └── iot-dashboard/
│       │           ├── requirements.md
│       │           ├── design.md
│       │           └── tasks.md
│       ├── frontend/
│       ├── backend/
│       └── ...
│
├── tests/                              # Test suite
│   ├── test_necromancer.py
│   ├── test_workspace_manager.py
│   ├── test_spirits.py
│   └── ...
│
├── docs/                               # Documentation
│   ├── getting-started.md
│   ├── architecture.md
│   └── api-reference.md
│
├── demo_multi_spirit.py                 # Multi-spirit demo
├── demo_logging_monitoring.py          # Logging demo
├── README.md                           # Main README
├── DEMO_README.md                      # Demo documentation
├── LICENSE
└── .gitignore
```

### `.kiro/`
Configuration and metadata for the NecroCode framework itself.

- **steering/**: Documentation that guides AI spirits working on NecroCode
- **specs/**: Specifications for NecroCode features (not user projects)
- **hooks/**: Automation triggers for framework development
- **workspace-state.json**: Tracks dynamically created user workspaces

### `framework/`
The core NecroCode implementation.

- **necromancer/**: Necromancer and coordination logic
- **spirits/**: All spirit implementations
- **workspace_manager/**: Workspace isolation and Git operations
- **communication/**: Inter-spirit messaging
- **task_executor/**: Task loading and tracking

### `examples/`
**Important**: These are NOT used by the framework at runtime!

These are sample applications created WITH NecroCode to demonstrate capabilities:
- workspace1: Real-time collaboration tool
- workspace2: IoT dashboard

Each includes:
- Full source code
- README explaining it was built with NecroCode
- Original specs used to generate it

### Dynamic Workspaces
When users run NecroCode, it creates workspaces dynamically:

```
necrocode/
├── workspace-my-chat-app/          # Created at runtime
│   ├── .git/                       # Cloned from user's repo
│   ├── frontend/
│   ├── backend/
│   └── ...
│
├── workspace-another-project/      # Another user project
│   ├── .git/
│   └── ...
```

These are:
- Created by cloning user's GitHub workspace
- Automatically added to `.gitignore`
- Tracked in `workspace-state.json`
- Cleaned up after completion

### Necromancer Module
```python
from framework.necromancer import Necromancer, JobParser, IssueRouter

necromancer = Necromancer(workspace=".")
necromancer.summon_team(job_description, role_requests)
```

### Spirits Module
```python
from framework.spirits import (
    ArchitectSpirit,
    ScrumMasterSpirit,
    BackendSpirit,
    FrontendSpirit
)

architect = ArchitectSpirit(workspace)
specs = architect.create_specs(job_description)
```

### Workspace Manager Module
```python
from framework.workspace_manager import (
    WorkspaceNecromancer,
    Workspace,
    BranchStrategy
)

necromancer = WorkspaceNecromancer(config)
workspace = necromancer.create_workspace(spec_name, repo_url)
```

### Communication Module
```python
from framework.communication import SpiritProtocol, MessageBus

protocol = SpiritProtocol()
message = protocol.format_commit("backend", "Add auth", "1.1")
```

All imports use absolute paths from project root:

```python

### `.kiro/workspace-state.json`
Tracks all active workspaces:
```json
{
  "workspaces": {
    "my-chat-app": {
      "spec_name": "my-chat-app",
      "workspace_path": "./workspace-my-chat-app",
      "repo_url": "https://github.com/user/my-chat-app.git",
      "current_branch": "main",
      "created_at": "2025-11-09T15:30:00Z",
      "tasks_completed": ["1.1", "1.2"],
      "status": "active"
    }
  }
}
```

### `.gitignore`
Excludes dynamic workspaces:
```
workspace-*/
__pycache__/
*.pyc
.pytest_cache/
```

### Files
- Python modules: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`

### Directories
- Framework modules: `snake_case/`
- Dynamic workspaces: `workspace-{spec-name}/`
- Example apps: `workspace1/`, `workspace2/`

### Git Branches
- Task branches: `feature/task-{spec}-{task-id}-{description}`
- Spirit branches: `{role}/spirit-{instance}/{feature}`
## Extension Points & Best Practices
### Adding New Spirit Types
1. Create `framework/spirits/new_spirit.py`
2. Inherit from `BaseSpirit`
3. Implement required methods
4. Register in `Necromancer.summon_team()`

### Adding New Hooks
1. Create `.kiro/hooks/on_event.py`
2. Define trigger conditions
3. Implement hook logic

### Custom Branch Strategies
1. Extend `BranchStrategy` class
2. Override `generate_branch_name()`
3. Configure in `WorkspaceNecromancer`

1. **Never modify examples/**: These are static demos
2. **Use WorkspaceNecromancer**: Don't create workspaces manually
3. **Follow Spirit Protocol**: All commits must use standard format
4. **Track state**: Always update workspace-state.json
5. **Clean up**: Remove workspaces after completion
## Spirit Collaboration Workflow
This document describes how NecroCode spirits (spirits) collaborate to transform a job description into a fully implemented application.

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Summoning & Planning                               │
└─────────────────────────────────────────────────────────────┘

User Input: "Create a real-time chat app with authentication"
     ↓
[🧙 Necromancer]
  - Parse job description
  - Determine required spirits
  - Clone user's workspace → workspace-chat-app/
     ↓
[👻 Architect Spirit]
  - Analyze requirements
  - Design system architecture
  - Generate specs → .kiro/specs/chat-app/
    ├── requirements.md
    ├── design.md (React + Node.js + MongoDB)
    └── tasks.md (15 tasks defined)
     ↓
[📋 Scrum Master Spirit]
  - Parse tasks from specs
  - Analyze dependencies
  - Assign tasks to appropriate spirits
  - Balance workload across instances

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Parallel Execution                                 │
└─────────────────────────────────────────────────────────────┘

[⚙️ Backend Spirit 1] Task 1.1: Database Schema
  1. Create branch: feature/task-chat-app-1.1-database-schema
  2. Implement: models/User.js, models/Message.js
  3. Commit: spirit(database): summon user and message schemas [Task 1.1]
  4. Push & Create PR #1

[⚙️ Backend Spirit 2] Task 1.2: JWT Authentication
  1. Create branch: feature/task-chat-app-1.2-jwt-auth
  2. Implement: routes/auth.js, middleware/auth.js
  3. Commit: spirit(backend): cast JWT authentication spell [Task 1.2]
  4. Push & Create PR #2

[💻 Frontend Spirit 1] Task 2.1: Login UI
  1. Create branch: feature/task-chat-app-2.1-login-ui
  2. Implement: components/Login.jsx, styles/login.css
  3. Commit: spirit(frontend): summon login form [Task 2.1]
  4. Push & Create PR #3

[💻 Frontend Spirit 2] Task 2.2: Chat Interface
  1. Create branch: feature/task-chat-app-2.2-chat-ui
  2. Implement: components/ChatRoom.jsx, components/MessageList.jsx
  3. Commit: spirit(frontend): weave chat interface [Task 2.2]
  4. Push & Create PR #4

... (11 more tasks in parallel)

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Quality Assurance                                  │
└─────────────────────────────────────────────────────────────┘

[🧪 QA Spirit]
  - Review all PRs
  - Run automated tests
  - Create test coverage reports
  - Approve or request changes

┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Deployment                                         │
└─────────────────────────────────────────────────────────────┘

[🚀 DevOps Spirit]
  - Setup CI/CD pipeline
  - Configure deployment
  - Create Docker containers
  - Deploy to staging

┌─────────────────────────────────────────────────────────────┐
│ Result: 15 PRs ready for review                            │
└─────────────────────────────────────────────────────────────┘
```

### 🧙 Necromancer (Necromancer)
**Purpose**: Coordinate the entire development lifecycle

**Responsibilities**:
- Parse natural language job descriptions
- Summon appropriate spirits based on requirements
- Create and manage workspaces
- Coordinate sprint execution
- Monitor overall progress
- Handle spirit lifecycle (summon → execute → banish)

**Key Methods**:
```python
necromancer.summon_team(job_description, role_requests)
necromancer.execute_sprint()
necromancer.banish_spirits()
```

### 👻 Architect Spirit
**Purpose**: Design system architecture and create specifications

**Responsibilities**:
- Analyze job description requirements
- Design system architecture
- Choose technology stack
- Generate detailed specs (requirements, design, tasks)
- Define component boundaries
- Plan data models

**Output**:
```
.kiro/specs/{project-name}/
├── requirements.md    # What needs to be built
├── design.md         # How it will be built
└── tasks.md          # Breakdown into implementable tasks
```

### 📋 Scrum Master Spirit
**Purpose**: Task management and assignment

**Responsibilities**:
- Parse tasks from architect's specs
- Analyze task dependencies
- Route tasks to appropriate spirits
- Balance workload across multiple instances
- Track task progress
- Manage sprint execution

**Routing Logic**:
```python

### Spirit Protocol Format

All inter-spirit communication follows the Spirit Protocol:

#### Commit Messages
```
spirit(scope): description [Task X.Y]

Examples:
spirit(backend): summon JWT authentication [Task 1.2]
spirit(frontend): cast login form spell [Task 2.1]
spirit(database): weave user schema enchantment [Task 3.1]
```

#### Branch Names
```
feature/task-{spec-id}-{task-number}-{description}

Examples:
feature/task-chat-app-1.2-jwt-authentication
feature/task-iot-dashboard-2.3-sensor-visualization
```

#### Spirit Instance Branches
```
{role}/spirit-{instance}/{feature-name}

Examples:
frontend/spirit-1/login-ui
frontend/spirit-2/dashboard-ui
backend/spirit-1/auth-api
backend/spirit-2/websocket-server
```

### Message Bus

Spirits communicate via the Message Bus:

```python

### Multi-Instance Support

Multiple spirits of the same type work in parallel:

```python

Each spec gets its own isolated workspace:

```
necrocode/
├── workspace-chat-app/          # Spec 1
│   ├── .git/
│   ├── backend/
│   └── frontend/
│
├── workspace-iot-dashboard/     # Spec 2
│   ├── .git/
│   ├── backend/
│   └── frontend/
```

**Benefits**:
- No conflicts between concurrent specs
- Clean Git history per project
- Independent branch management
- Easy cleanup after completion

### Task Failure
```python
try:
    spirit.execute_task(task)
except TaskExecutionError as e:
    # Retry with different spirit
    scrum_master.reassign_task(task, exclude=[spirit])
    # Or escalate to Necromancer
    necromancer.handle_failure(task, e)
```

### Spirit Failure
```python
if spirit.is_unresponsive():
    # Summon replacement
    new_spirit = necromancer.summon_replacement(spirit.role)
    # Transfer workload
    new_spirit.take_over(spirit.current_tasks)
```

### Workload Visualization
```
BACKEND Spirits:
  backend_spirit_1    | Active: 2 | Completed: 3 | ████░
  backend_spirit_2    | Active: 1 | Completed: 4 | ███░░
  backend_spirit_3    | Active: 2 | Completed: 2 | ███░░

FRONTEND Spirits:
  frontend_spirit_1   | Active: 1 | Completed: 2 | ██░░░
  frontend_spirit_2   | Active: 0 | Completed: 3 | ██░░░
```

### Progress Tracking
```python
progress = {
    "total_tasks": 15,
    "completed": 8,
    "in_progress": 5,
    "pending": 2,
    "percentage": 53.3
}
```

1. **Single Responsibility**: Each spirit focuses on its domain
2. **Clear Communication**: Use Spirit Protocol consistently
3. **Parallel Work**: Maximize concurrent task execution
4. **Clean Branches**: One branch per task
5. **Atomic Commits**: Small, focused commits
6. **Test Coverage**: QA spirit validates all changes
7. **Documentation**: Update specs as implementation evolves

```python
## See Also
- [overview.md](overview.md) — Vision and target users
- [architecture.md](architecture.md) — Protocols, components, data models

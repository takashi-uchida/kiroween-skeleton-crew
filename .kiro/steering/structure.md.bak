# NecroCode - Framework Structure

## Directory Layout

```
necrocode/                              # Root directory
├── .kiro/                              # Kiro configuration
│   ├── steering/                       # Framework documentation
│   │   ├── product.md                  # Product overview
│   │   ├── tech.md                     # Technical stack
│   │   ├── structure.md                # This file
│   │   └── agent-workflow.md           # Agent collaboration flow
│   │
│   ├── specs/                          # Spec definitions
│   │   ├── necrocode-agent-orchestration/
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
│   ├── hooks/                          # Agent hooks
│   │   ├── on_spec_complete.py
│   │   ├── on_task_start.py
│   │   └── on_task_complete.py
│   │
│   └── workspace-state.json            # Active workspace tracking
│
├── framework/                          # Core framework
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── necromancer.py              # Main orchestrator
│   │   ├── job_parser.py               # Parse job descriptions
│   │   ├── issue_router.py             # Route tasks to agents
│   │   └── spec_generator.py           # Generate specs
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py               # Base spirit class
│   │   ├── architect_agent.py          # Spec creation
│   │   ├── scrum_master_agent.py       # Task breakdown
│   │   ├── frontend_agent.py           # Frontend development
│   │   ├── backend_agent.py            # Backend development
│   │   ├── database_agent.py           # Database design
│   │   ├── qa_agent.py                 # Testing
│   │   └── devops_agent.py             # Deployment
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
│   ├── test_agents.py
│   └── ...
│
├── docs/                               # Documentation
│   ├── getting-started.md
│   ├── architecture.md
│   └── api-reference.md
│
├── demo_multi_agent.py                 # Multi-agent demo
├── demo_logging_monitoring.py          # Logging demo
├── README.md                           # Main README
├── DEMO_README.md                      # Demo documentation
├── LICENSE
└── .gitignore
```

## Key Directories Explained

### `.kiro/`
Configuration and metadata for the NecroCode framework itself.

- **steering/**: Documentation that guides AI agents working on NecroCode
- **specs/**: Specifications for NecroCode features (not user projects)
- **hooks/**: Automation triggers for framework development
- **workspace-state.json**: Tracks dynamically created user workspaces

### `framework/`
The core NecroCode implementation.

- **orchestrator/**: Necromancer and coordination logic
- **agents/**: All spirit implementations
- **workspace_manager/**: Workspace isolation and Git operations
- **communication/**: Inter-agent messaging
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
- Created by cloning user's GitHub repository
- Automatically added to `.gitignore`
- Tracked in `workspace-state.json`
- Cleaned up after completion

## Module Organization

### Orchestrator Module
```python
from framework.orchestrator import Necromancer, JobParser, IssueRouter

necromancer = Necromancer(workspace=".")
necromancer.summon_team(job_description, role_requests)
```

### Agents Module
```python
from framework.agents import (
    ArchitectAgent,
    ScrumMasterAgent,
    BackendAgent,
    FrontendAgent
)

architect = ArchitectAgent(workspace)
specs = architect.create_specs(job_description)
```

### Workspace Manager Module
```python
from framework.workspace_manager import (
    WorkspaceOrchestrator,
    Workspace,
    BranchStrategy
)

orchestrator = WorkspaceOrchestrator(config)
workspace = orchestrator.create_workspace(spec_name, repo_url)
```

### Communication Module
```python
from framework.communication import SpiritProtocol, MessageBus

protocol = SpiritProtocol()
message = protocol.format_commit("backend", "Add auth", "1.1")
```

## Import Paths

All imports use absolute paths from project root:

```python
# Correct
from framework.orchestrator.necromancer import Necromancer
from framework.agents.base_agent import BaseSpirit
from framework.workspace_manager import WorkspaceOrchestrator

# Incorrect
from orchestrator.necromancer import Necromancer  # Missing framework
from ..agents.base_agent import BaseSpirit        # Relative imports
```

## Configuration Files

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

## Naming Conventions

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

## Extension Points

### Adding New Agent Types
1. Create `framework/agents/new_agent.py`
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
3. Configure in `WorkspaceOrchestrator`

## Best Practices

1. **Never modify examples/**: These are static demos
2. **Use WorkspaceOrchestrator**: Don't create workspaces manually
3. **Follow Spirit Protocol**: All commits must use standard format
4. **Track state**: Always update workspace-state.json
5. **Clean up**: Remove workspaces after completion

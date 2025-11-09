# NecroCode - Technical Stack

## Core Technologies

### Language & Runtime
- **Python 3.11+**: Main implementation language
- **Type Hints**: Full type annotation for better IDE support
- **Dataclasses**: For structured data models

### Version Control
- **Git**: Core VCS for workspace management
- **GitHub API**: For PR creation and repository operations
- **GitPython**: Python library for Git operations

### AI & Agents
- **Kiro AI**: Primary AI agent platform
- **Spirit Protocol**: Custom inter-agent communication protocol
- **Message Bus**: Event-driven coordination system

## Architecture Patterns

### Multi-Agent System
- **Orchestrator Pattern**: Necromancer coordinates all spirits
- **Worker Pattern**: Spirits execute tasks independently
- **Load Balancing**: Distribute tasks across agent instances
- **Event-Driven**: Message-based communication

### Workspace Isolation
- **Repository Cloning**: Each spec gets isolated workspace
- **Branch Strategy**: Unique branches per agent instance
- **State Tracking**: JSON-based workspace state management
- **Conflict Prevention**: Isolated workspaces prevent interference

### Communication Protocol

#### Spirit Protocol Format
```
spirit(scope): description [Task X.Y]

Examples:
- spirit(backend): summon JWT authentication [Task 1.1]
- spirit(frontend): cast login form spell [Task 2.1]
- spirit(database): weave user schema enchantment [Task 3.1]
```

#### Branch Naming Convention
```
feature/task-{spec-id}-{task-number}-{description}

Examples:
- feature/task-chat-app-1.1-jwt-authentication
- feature/task-iot-dashboard-2.3-sensor-visualization
```

#### Spirit Instance Branches
```
{role}/spirit-{instance}/{feature-name}

Examples:
- frontend/spirit-1/login-ui
- frontend/spirit-2/dashboard-ui
- backend/spirit-1/auth-api
```

## Key Components

### Necromancer (Orchestrator)
- Job description parsing
- Spirit summoning and lifecycle management
- Workspace orchestration
- Sprint execution coordination

### Workspace Manager
- Repository cloning
- Branch creation and management
- Commit formatting (Spirit Protocol)
- State persistence

### Issue Router
- Keyword-based routing
- Load balancing across instances
- Workload tracking
- Multi-language support (English/Japanese)

### Spirits (Agents)
- Base spirit with workload tracking
- Specialized implementations per role
- Task execution capabilities
- Branch and commit management
- Documentation spirit for content organization

## Data Models

### WorkspaceInfo
```python
@dataclass
class WorkspaceInfo:
    spec_name: str
    workspace_path: Path
    repo_url: str
    current_branch: str
    created_at: str
    tasks_completed: List[str]
    status: str
```

### Spirit
```python
@dataclass
class BaseSpirit:
    identifier: str
    role: str
    skills: List[str]
    current_tasks: List[str]
    completed_tasks: List[str]
```

## File Structure

```
necrocode/
├── framework/
│   ├── orchestrator/
│   │   ├── necromancer.py          # Main orchestrator
│   │   ├── job_parser.py           # Parse job descriptions
│   │   └── issue_router.py         # Route tasks to agents
│   ├── agents/
│   │   ├── base_agent.py           # Base spirit class
│   │   ├── architect_agent.py      # Spec generation
│   │   ├── scrum_master_agent.py   # Task breakdown
│   │   ├── documentation_agent.py  # Documentation organization
│   │   └── [role]_agent.py         # Specialized spirits
│   ├── workspace_manager/
│   │   ├── workspace_manager.py    # Workspace orchestration
│   │   ├── workspace.py            # Single workspace
│   │   ├── branch_strategy.py      # Branch naming
│   │   └── git_operations.py       # Git commands
│   └── communication/
│       ├── spirit_protocol.py      # Protocol implementation
│       └── message_bus.py          # Event coordination
└── .kiro/
    ├── specs/                      # Generated specs
    ├── steering/                   # Framework docs
    └── workspace-state.json        # Active workspaces
```

## Dependencies

### Core
- `gitpython`: Git operations
- `dataclasses`: Data structures (built-in)
- `pathlib`: Path handling (built-in)
- `json`: State persistence (built-in)

### Future Considerations
- `asyncio`: For true parallel execution
- `pytest`: Testing framework
- `requests`: GitHub API calls
- `pydantic`: Enhanced data validation

## Performance Characteristics

- **Workspace Creation**: O(1) + git clone time
- **Issue Routing**: O(n) where n = number of agents
- **Load Balancing**: O(n) where n = agents of same type
- **State Tracking**: O(1) per operation

## Security Considerations

- Git credentials managed via system git config
- No hardcoded secrets
- Workspace isolation prevents cross-contamination
- State file contains no sensitive data

## Scalability

- Supports unlimited agent instances per role
- Concurrent workspace management
- Efficient state tracking with JSON
- Minimal memory footprint per spirit

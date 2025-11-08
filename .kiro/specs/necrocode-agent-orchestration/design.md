# Design Document

## Overview

NecroCode implements an event-driven agent orchestration architecture where specialized AI agents (Spirits) collaborate through a message bus to execute agile development workflows. The system follows a layered architecture with clear separation between orchestration, agent logic, communication, and workspace management.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Necromancer                          │
│                   (Main Orchestrator)                       │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌────────────────────────┐      ┌────────────────────────────┐
│    Job Parser          │      │    Team Builder            │
│  - NLP Analysis        │      │  - Spirit Registry         │
│  - Role Extraction     │      │  - Spirit Instantiation    │
└────────────────────────┘      └────────────────────────────┘
             │                                │
             └────────────┬───────────────────┘
                          ▼
             ┌────────────────────────┐
             │     Message Bus        │
             │  (Spirit Protocol)     │
             └────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Architect   │  │ Scrum Master │  │  Dev Spirits │
│   Spirit     │  │    Spirit    │  │  (Frontend,  │
│              │  │              │  │   Backend,   │
│              │  │              │  │   Database,  │
│              │  │              │  │   QA, DevOps)│
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
             ┌────────────────────────┐
             │  Workspace Manager     │
             │  - Git Operations      │
             │  - Branch Management   │
             │  - Multi-repo Support  │
             └────────────────────────┘
```

### Architectural Patterns

1. **Event-Driven Architecture**: Spirits communicate asynchronously through the Message Bus
2. **Registry Pattern**: Spirit Registry maintains all active agent instances
3. **Strategy Pattern**: Different Spirit types implement specialized behaviors
4. **Observer Pattern**: Message Bus notifies subscribed handlers of events
5. **Factory Pattern**: Team Builder creates Spirit instances based on job requirements

## Components and Interfaces

### 1. Necromancer (Main Orchestrator)

**Responsibilities:**
- Parse job descriptions
- Summon appropriate Spirit team
- Coordinate sprint execution
- Manage workspace lifecycle

**Key Methods:**
```python
class Necromancer:
    def summon_team(job_description: str) -> Dict
    def execute_sprint() -> Dict
    def banish_spirits() -> None
```

**Workflow:**
1. Receive job description
2. Summon Architect Spirit → Design system
3. Summon Scrum Master Spirit → Create sprint
4. Summon Development Spirits → Assign to workspace
5. Execute sprint with task coordination
6. Monitor progress and handle conflicts

### 2. Job Parser

**Responsibilities:**
- Analyze natural language job descriptions
- Extract technical requirements
- Identify required agent roles

**Key Methods:**
```python
class JobParser:
    def parse(description: str) -> List[RoleRequest]
    def extract_features(description: str) -> List[str]
    def detect_language(description: str) -> str
```

**Feature Detection Logic:**
- Authentication: Keywords "認証", "auth", "login"
- Real-time: Keywords "realtime", "websocket", "リアルタイム"
- Data viz: Keywords "dashboard", "chart", "ダッシュボード"
- IoT: Keywords "sensor", "device", "センサー", "iot"

### 2.5. Issue Router (NEW)

**Responsibilities:**
- Analyze incoming issues/tasks
- Automatically determine appropriate agent type
- Route issues to available agents
- Balance workload across multiple agents

**Key Methods:**
```python
class IssueRouter:
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.routing_rules = self._load_routing_rules()
    
    def route_issue(issue: Dict) -> str:
        """Analyze issue and return appropriate agent identifier"""
        
    def _analyze_keywords(content: str) -> str:
        """Extract keywords and determine agent type"""
        
    def _get_agent_by_type(agent_type: str) -> str:
        """Find available agent of specified type"""
        
    def _balance_load(agents: List[BaseSpirit]) -> BaseSpirit:
        """Select least-busy agent from list"""
```

**Routing Rules (Keyword-based):**

```python
ROUTING_RULES = {
    'frontend': [
        'ui', 'ux', 'component', 'style', 'css', 'html',
        'react', 'vue', 'angular', 'フロント', 'コンポーネント',
        'button', 'form', 'page', 'layout', 'responsive'
    ],
    'backend': [
        'api', 'endpoint', 'server', 'logic', 'service',
        'rest', 'graphql', 'バックエンド', 'サーバー',
        'authentication', 'authorization', 'middleware'
    ],
    'database': [
        'schema', 'query', 'migration', 'database', 'db',
        'sql', 'nosql', 'データベース', 'スキーマ',
        'table', 'collection', 'index', 'transaction'
    ],
    'qa': [
        'bug', 'test', 'quality', 'coverage', 'テスト',
        'バグ', 'unit test', 'integration', 'e2e',
        'assertion', 'mock', 'fixture'
    ],
    'devops': [
        'deploy', 'docker', 'ci', 'cd', 'infrastructure',
        'デプロイ', 'インフラ', 'kubernetes', 'aws',
        'pipeline', 'container', 'orchestration'
    ],
    'architect': [
        'architecture', 'design', 'tech stack', '設計',
        'アーキテクチャ', 'pattern', 'structure',
        'scalability', 'performance'
    ]
}
```

**Load Balancing Strategy:**

1. **Round-robin**: Distribute issues evenly
2. **Least-busy**: Assign to agent with fewest active tasks
3. **Skill-based**: Match issue requirements to agent skills
4. **Priority-based**: High-priority issues to most experienced agents

### 3. Spirit Base Class

**Responsibilities:**
- Provide common Spirit interface
- Handle message reception
- Manage workspace assignment
- **Track assigned tasks and workload**

**Interface:**
```python
@dataclass
class BaseSpirit:
    role: str
    skills: List[str]
    workspace: str
    identifier: str              # Unique ID like 'frontend_spirit_1'
    instance_number: int         # NEW: Instance number for load balancing
    current_tasks: List[str]     # NEW: Currently assigned task IDs
    completed_tasks: List[str]   # NEW: Completed task IDs
    
    def chant(message: str) -> str
    def receive_message(message: AgentMessage) -> None
    def send_message(receiver: str, message_type: str, payload: Dict) -> None
    def assign_task(task_id: str) -> None  # NEW: Add task to workload
    def complete_task(task_id: str) -> None  # NEW: Mark task complete
    def get_workload() -> int  # NEW: Return number of active tasks
```

**Instance Identifier Format:**
```
{role}_spirit_{instance_number}

Examples:
- frontend_spirit_1
- frontend_spirit_2
- backend_spirit_1
- backend_spirit_2
- database_spirit_1
```

### 4. Architect Spirit

**Responsibilities:**
- Analyze job requirements
- Design system architecture
- Select technology stack
- Define API contracts

**Key Methods:**
```python
class ArchitectSpirit(BaseSpirit):
    def design_system(job_description: str) -> Dict
    def _divine_tech_stack(description: str) -> Dict
    def _design_architecture(description: str) -> Dict
    def _design_api(description: str) -> List[Dict]
    def create_documentation() -> str
```

**Tech Stack Selection Logic:**
```
Frontend:
  - Default: React
  - If "vue" → Vue.js
  - If "angular" → Angular

Backend:
  - Default: Node.js + Express
  - If "python" or "fastapi" → Python + FastAPI
  - If "django" → Python + Django

Database:
  - Default: MongoDB
  - If "postgres" or "sql" → PostgreSQL
  - If "timescale" or "時系列" → TimescaleDB

Real-time:
  - If "websocket" or "realtime" → Socket.io or WebSocket
```

### 5. Scrum Master Spirit

**Responsibilities:**
- Decompose job into user stories
- Create sprint backlog
- Assign tasks to spirits
- **Automatically route issues to appropriate agents**
- Track dependencies
- Resolve conflicts
- Manage multiple instances of same agent type

**Key Methods:**
```python
class ScrumMasterSpirit(BaseSpirit):
    def decompose_job(job_description: str, architecture: Dict) -> List[Dict]
    def create_sprint(sprint_number: int) -> Dict
    def assign_tasks(story: Dict) -> List[Dict]
    def route_issue(issue: Dict) -> str  # NEW: Auto-assign agent
    def _analyze_issue_content(issue: Dict) -> str  # NEW: Determine agent type
    def _get_available_agent(agent_type: str) -> str  # NEW: Load balancing
    def _get_blockers(agent: str, all_tasks: List[Dict]) -> List[str]
    def resolve_conflict(conflict: Dict) -> str
    def track_progress() -> Dict
```

**Issue Auto-Routing Logic:**

The Scrum Master analyzes issue content to determine the appropriate agent:

```python
def route_issue(issue: Dict) -> str:
    """
    Analyze issue and automatically assign to appropriate agent.
    
    Keywords mapping:
    - UI/UX/Component/Style → Frontend Agent
    - API/Endpoint/Server/Logic → Backend Agent
    - Schema/Query/Migration/Database → Database Agent
    - Bug/Test/Quality/Coverage → QA Agent
    - Deploy/Docker/CI/CD/Infrastructure → DevOps Agent
    - Architecture/Design/Tech Stack → Architect Agent
    """
    content = f"{issue['title']} {issue['description']}".lower()
    
    # Frontend keywords
    if any(kw in content for kw in ['ui', 'ux', 'component', 'style', 'css', 'react', 'vue', 'フロント']):
        return self._get_available_agent('frontend')
    
    # Backend keywords
    if any(kw in content for kw in ['api', 'endpoint', 'server', 'logic', 'バックエンド', 'rest']):
        return self._get_available_agent('backend')
    
    # Database keywords
    if any(kw in content for kw in ['schema', 'query', 'migration', 'database', 'db', 'データベース']):
        return self._get_available_agent('database')
    
    # QA keywords
    if any(kw in content for kw in ['bug', 'test', 'quality', 'coverage', 'テスト', 'バグ']):
        return self._get_available_agent('qa')
    
    # DevOps keywords
    if any(kw in content for kw in ['deploy', 'docker', 'ci', 'cd', 'infrastructure', 'デプロイ']):
        return self._get_available_agent('devops')
    
    # Architecture keywords
    if any(kw in content for kw in ['architecture', 'design', 'tech stack', '設計', 'アーキテクチャ']):
        return self._get_available_agent('architect')
    
    # Default: assign to Scrum Master for manual routing
    return 'scrum_master'
```

**Load Balancing for Multiple Agents:**

When multiple agents of the same type exist, the Scrum Master distributes work:

```python
def _get_available_agent(agent_type: str) -> str:
    """
    Select least-busy agent of the requested type.
    Returns agent identifier like 'frontend_spirit_1', 'frontend_spirit_2', etc.
    """
    agents = [s for s in self.message_bus.spirits if s.role == agent_type]
    
    if not agents:
        raise SummoningError(f"No {agent_type} agents available")
    
    # Find agent with fewest assigned tasks
    agent_workload = {a.identifier: a.current_tasks for a in agents}
    least_busy = min(agent_workload, key=agent_workload.get)
    
    return least_busy
```

**Dependency Rules:**
```
Database → Backend → Frontend → QA
         ↓
       DevOps (parallel)
       
Multiple instances of same type work in parallel
```

### 6. Development Spirits

**Frontend Spirit:**
```python
class FrontendSpirit(BaseSpirit):
    def summon_ui() -> str
    def create_component(spec: Dict) -> str
    def integrate_api(endpoint: Dict) -> str
```

**Backend Spirit:**
```python
class BackendSpirit(BaseSpirit):
    def forge_api() -> str
    def implement_endpoint(spec: Dict) -> str
    def connect_database(schema: Dict) -> str
```

**Database Spirit:**
```python
class DatabaseSpirit(BaseSpirit):
    def weave_schema() -> str
    def create_migration(schema: Dict) -> str
    def optimize_queries() -> str
```

### 7. QA Spirit

**Responsibilities:**
- Define test strategy
- Generate test templates
- Execute test suites
- Report bugs

**Key Methods:**
```python
class QASpirit(BaseSpirit):
    def create_test_strategy(architecture: Dict) -> Dict
    def generate_unit_tests(component: str, language: str) -> str
    def run_tests() -> Dict
    def report_bug(bug: Dict) -> str
```

**Test Strategy:**
- Unit tests: Always enabled
- Integration tests: Always enabled
- E2E tests: If frontend exists
- Performance tests: If IoT/high-load system

### 8. DevOps Spirit

**Responsibilities:**
- Configure infrastructure
- Set up CI/CD
- Manage deployments

**Key Methods:**
```python
class DevOpsSpirit(BaseSpirit):
    def create_docker_config() -> str
    def setup_cicd() -> str
    def deploy(environment: str) -> Dict
```

### 9. Spirit Protocol (Message Bus)

**Message Structure:**
```python
@dataclass
class AgentMessage:
    sender: str              # "architect_spirit"
    receiver: str            # "backend_spirit"
    workspace: str           # "workspace1"
    message_type: str        # "api_ready"
    payload: Dict            # Message-specific data
    timestamp: datetime      # Auto-generated
```

**Message Types:**
- `summoning`: Necromancer → Spirit (initialization)
- `task_assignment`: Scrum Master → Dev Spirit
- `task_completed`: Dev Spirit → Scrum Master
- `api_ready`: Backend → Frontend
- `schema_ready`: Database → Backend
- `test_failure`: QA → Scrum Master
- `conflict_resolution`: Scrum Master → Any Spirit
- `deployment_ready`: DevOps → Necromancer

**Message Bus Interface:**
```python
class MessageBus:
    spirits: List[BaseSpirit]
    handlers: List[Callable]
    
    def register(spirit: BaseSpirit) -> None
    def subscribe(handler: Callable) -> None
    def dispatch(message: AgentMessage) -> None
    def broadcast(message: AgentMessage) -> None
```

### 10. Workspace Manager

**Responsibilities:**
- Manage Git repositories
- Handle branch operations
- Coordinate multi-repo workflows
- **Support multiple agents of same type with unique branch names**

**Key Methods:**
```python
class WorkspaceManager:
    def initialize_workspace(workspace_id: str) -> None
    def create_branch(spirit_id: str, feature: str, issue_id: str = None) -> str
    def commit(branch: str, message: str, files: List[str]) -> None
    def create_pull_request(branch: str, description: str) -> str
    def merge(branch: str) -> None
    def get_active_branches(spirit_id: str) -> List[str]
```

**Branch Naming Convention (Updated for Multiple Agents):**

```
{role}/{agent-instance-id}/{feature-name}
or
{role}/{issue-id}-{feature-name}

Examples with multiple agents:
- frontend/spirit-1/login-ui
- frontend/spirit-2/dashboard-ui
- backend/spirit-1/auth-api
- backend/spirit-2/payment-api

Examples with issue tracking:
- frontend/issue-42-login-ui
- backend/issue-43-auth-api
- database/issue-44-user-schema
- qa/issue-45-auth-tests
- devops/issue-46-docker-setup

Legacy format (single agent):
- architect/system-design
```

**Branch Creation Logic:**

```python
def create_branch(spirit_id: str, feature: str, issue_id: str = None) -> str:
    """
    Create unique branch name for spirit.
    
    Args:
        spirit_id: Full identifier like 'frontend_spirit_1'
        feature: Feature name like 'login-ui'
        issue_id: Optional issue number like '42'
    
    Returns:
        Branch name like 'frontend/spirit-1/login-ui' or 'frontend/issue-42-login-ui'
    """
    role = spirit_id.split('_')[0]  # Extract 'frontend' from 'frontend_spirit_1'
    
    if issue_id:
        # Issue-based naming (preferred for tracking)
        branch_name = f"{role}/issue-{issue_id}-{feature}"
    else:
        # Instance-based naming (for parallel work)
        instance_id = spirit_id.split('_')[-1]  # Extract '1' from 'frontend_spirit_1'
        branch_name = f"{role}/spirit-{instance_id}/{feature}"
    
    return branch_name
```

**Commit Message Format:**
```
spirit(scope): spell description [#issue-id]

Examples:
- frontend(ui): summon login form component [#42]
- backend(auth): implement JWT token generation [#43]
- database(schema): create user and session tables [#44]
- qa(tests): conjure authentication test suite [#45]
- devops(docker): prepare deployment catacombs [#46]

With multiple agents:
- frontend-1(ui): summon login form component [#42]
- frontend-2(ui): summon dashboard component [#47]
- backend-1(auth): implement JWT token generation [#43]
- backend-2(payment): forge payment API [#48]
```

**Pull Request Naming:**
```
[{role}-{instance}] {feature-name} (Fixes #{issue-id})

Examples:
- [frontend-1] Login UI Component (Fixes #42)
- [backend-2] Payment API Implementation (Fixes #48)
- [database] User Schema Migration (Fixes #44)
```

## Data Models

### RoleRequest
```python
@dataclass
class RoleRequest:
    name: str              # "frontend", "backend", etc.
    skills: List[str]      # ["react", "websocket"]
    count: int = 1         # NEW: Number of agents to summon (default 1)
```

### Issue (NEW)
```python
@dataclass
class Issue:
    id: str                # "ISSUE-042"
    title: str             # "Implement login UI"
    description: str       # Detailed description
    labels: List[str]      # ["frontend", "ui", "authentication"]
    priority: str          # "high", "medium", "low"
    assigned_to: str       # Agent identifier like "frontend_spirit_1"
    status: str            # "open", "assigned", "in_progress", "completed"
    created_at: datetime
    updated_at: datetime
```

### UserStory
```python
@dataclass
class UserStory:
    id: str                # "US-001"
    title: str             # "User Authentication"
    description: str       # "As a user, I want to..."
    tasks: List[Task]      # List of implementation tasks
    issues: List[Issue]    # NEW: Related issues
    priority: str          # "high", "medium", "low"
```

### Task
```python
@dataclass
class Task:
    id: str                # NEW: "TASK-001"
    agent: str             # "database" (agent type)
    agent_instance: str    # NEW: "database_spirit_1" (specific instance)
    task: str              # "Create User schema"
    issue_id: str          # NEW: Related issue ID
    status: str            # "assigned", "in_progress", "completed"
    blocking: List[str]    # ["backend", "frontend"]
    branch_name: str       # NEW: Git branch for this task
```

### AgentInstance (NEW)
```python
@dataclass
class AgentInstance:
    identifier: str        # "frontend_spirit_1"
    role: str              # "frontend"
    instance_number: int   # 1
    skills: List[str]      # ["react", "websocket"]
    workspace: str         # "workspace1"
    current_tasks: List[str]      # ["TASK-001", "TASK-005"]
    completed_tasks: List[str]    # ["TASK-002", "TASK-003"]
    active_branches: List[str]    # ["frontend/issue-42-login-ui"]
    status: str            # "idle", "busy", "blocked"
```

### Architecture
```python
@dataclass
class Architecture:
    tech_stack: Dict       # Frontend, backend, database choices
    architecture: Dict     # Pattern, layers, communication
    api_design: List[Dict] # Endpoint specifications
```

### TeamConfiguration
```python
@dataclass
class TeamConfiguration:
    team: List[str]        # List of spirit identifiers
    architecture: Architecture
    sprint: Sprint
    stories: List[UserStory]
```

## Error Handling

### Error Categories

1. **Parsing Errors**
   - Invalid job description format
   - Unsupported language
   - Missing required information

2. **Summoning Errors**
   - Unknown spirit type
   - Workspace initialization failure
   - Insufficient resources

3. **Communication Errors**
   - Message delivery failure
   - Handler exception
   - Timeout waiting for response

4. **Execution Errors**
   - Task execution failure
   - Dependency deadlock
   - Git operation failure

### Error Handling Strategy

```python
class NecroCodeError(Exception):
    """Base exception for NecroCode"""
    pass

class SummoningError(NecroCodeError):
    """Failed to summon spirit"""
    pass

class CommunicationError(NecroCodeError):
    """Spirit protocol communication failed"""
    pass

class ExecutionError(NecroCodeError):
    """Task execution failed"""
    pass
```

**Error Messages (Halloween-themed):**
```
🕸️ A curse has been placed on the codebase!
🦇 The spirits are restless... merge conflict detected
💀 Fatal hex: Cannot summon agent without Job Description
👻 Spirit communication disrupted in the ethereal plane
⚰️ Task execution failed: {error_details}
🕷️ Dependency deadlock detected in the spirit realm
```

### Recovery Strategies

1. **Parsing Failure**: Request clarification from user
2. **Summoning Failure**: Retry with default configuration
3. **Communication Failure**: Queue message for retry
4. **Execution Failure**: Notify Scrum Master for conflict resolution
5. **Dependency Deadlock**: Scrum Master reorders tasks

## Testing Strategy

### Unit Tests

**Components to Test:**
- JobParser: Parse various job descriptions
- TeamBuilder: Spirit instantiation logic
- Each Spirit: Individual methods
- MessageBus: Message routing
- WorkspaceManager: Git operations

**Test Framework:** pytest (Python)

### Integration Tests

**Scenarios:**
1. End-to-end team summoning
2. Sprint execution with task coordination
3. Multi-workspace parallel execution
4. Spirit Protocol message flow
5. Error handling and recovery

### Test Data

**Sample Job Descriptions:**
```python
JOB_DESCRIPTIONS = {
    "realtime_collab": """
        リアルタイムでホワイトボード共有できるコラボツール。
        WebSocket通信、ユーザー認証、描画データの永続化が必要。
    """,
    "iot_dashboard": """
        センサーデータをリアルタイム可視化するダッシュボード。
        時系列データ分析、アラート機能、デバイス管理が必要。
    """,
    "simple_crud": """
        Simple CRUD application with user authentication
        and PostgreSQL database.
    """
}
```

### Performance Requirements

- Job parsing: < 1 second
- Team summoning: < 5 seconds
- Message delivery: < 100 milliseconds
- Sprint initialization: < 3 seconds
- Workspace cleanup: < 2 seconds

## Deployment Considerations

### Environment Variables

```bash
NECROCODE_WORKSPACE_ROOT=/path/to/workspaces
NECROCODE_LOG_LEVEL=INFO
NECROCODE_THEME=halloween  # or "professional"
NECROCODE_MAX_SPIRITS=10
NECROCODE_MESSAGE_TIMEOUT=30
```

### Dependencies

```
Python 3.10+
- dataclasses
- typing
- datetime

Optional:
- gitpython (for Git operations)
- pyyaml (for config files)
```

### Logging

**Log Levels:**
- DEBUG: All spirit messages
- INFO: Major workflow steps (summoning, sprint start)
- WARNING: Recoverable errors
- ERROR: Fatal errors requiring intervention

**Log Format:**
```
[{timestamp}] {emoji} {spirit_id}: {message}

Example:
[2024-11-09 10:30:45] 🧙 necromancer: Summoning team for workspace1
[2024-11-09 10:30:46] 👻 architect_spirit: Designing system architecture...
[2024-11-09 10:30:47] 📋 scrum_master_spirit: Created 4 user stories
```

## Future Enhancements

1. **Persistent State**: Save team configuration and progress to database
2. **Web UI**: Dashboard for monitoring spirit activity
3. **Advanced NLP**: Use LLM for better job description analysis
4. **Git Integration**: Actual Git operations (currently simulated)
5. **Multi-language Support**: Expand beyond Japanese and English
6. **Spirit Learning**: Spirits learn from past projects
7. **Parallel Execution**: True concurrent task execution
8. **Cloud Deployment**: Deploy spirits as microservices

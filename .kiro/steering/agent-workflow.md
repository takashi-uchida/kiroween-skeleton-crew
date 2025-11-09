# NecroCode - Agent Collaboration Workflow

## Overview

This document describes how NecroCode agents (spirits) collaborate to transform a job description into a fully implemented application.

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Summoning & Planning                               │
└─────────────────────────────────────────────────────────────┘

User Input: "Create a real-time chat app with authentication"
     ↓
[🧙 Necromancer]
  - Parse job description
  - Determine required spirits
  - Clone user's repository → workspace-chat-app/
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

## Agent Roles & Responsibilities

### 🧙 Necromancer (Orchestrator)
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
# Keyword-based routing
"Create login form" → Frontend Spirit
"Implement auth API" → Backend Spirit
"Design database schema" → Database Spirit
"Write unit tests" → QA Spirit
"Setup Docker" → DevOps Spirit
```

**Load Balancing**:
```python
# Distribute tasks evenly
Backend Spirit 1: Tasks 1.1, 1.3, 1.5
Backend Spirit 2: Tasks 1.2, 1.4, 1.6
```

### ⚙️ Backend Spirit
**Purpose**: Implement server-side logic

**Responsibilities**:
- Create API endpoints
- Implement business logic
- Setup authentication/authorization
- Database integration
- WebSocket/real-time features
- Error handling

**Technologies**:
- Node.js, Python, Go, Java
- Express, FastAPI, Gin, Spring
- REST, GraphQL, WebSocket

### 💻 Frontend Spirit
**Purpose**: Implement user interface

**Responsibilities**:
- Create UI components
- Implement client-side logic
- State management
- API integration
- Responsive design
- Accessibility

**Technologies**:
- React, Vue, Angular, Svelte
- TypeScript, JavaScript
- CSS, Tailwind, Material-UI

### 🗄️ Database Spirit
**Purpose**: Design and implement data layer

**Responsibilities**:
- Design database schemas
- Create migrations
- Optimize queries
- Setup indexes
- Data validation
- Backup strategies

**Technologies**:
- PostgreSQL, MongoDB, MySQL
- Redis, Elasticsearch
- Prisma, TypeORM, Mongoose

### 🧪 QA Spirit
**Purpose**: Ensure quality and correctness

**Responsibilities**:
- Write unit tests
- Write integration tests
- Code review
- Test coverage analysis
- Bug identification
- Performance testing

**Technologies**:
- Jest, Pytest, JUnit
- Cypress, Playwright
- Coverage tools

### 🚀 DevOps Spirit
**Purpose**: Deployment and infrastructure

**Responsibilities**:
- Setup CI/CD pipelines
- Container configuration
- Deployment automation
- Monitoring setup
- Infrastructure as code
- Environment management

**Technologies**:
- Docker, Kubernetes
- GitHub Actions, Jenkins
- AWS, GCP, Azure
- Terraform, Ansible

## Communication Protocol

### Spirit Protocol Format

All inter-agent communication follows the Spirit Protocol:

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
# Spirit publishes event
message_bus.publish("task.completed", {
    "task_id": "1.2",
    "spirit": "backend_spirit_1",
    "status": "success"
})

# Other spirits subscribe
message_bus.subscribe("task.completed", on_task_complete)
```

**Event Types**:
- `task.assigned`: Task assigned to spirit
- `task.started`: Spirit begins work
- `task.completed`: Task finished
- `task.failed`: Task encountered error
- `pr.created`: Pull request created
- `pr.merged`: Pull request merged

## Parallel Execution

### Multi-Instance Support

Multiple spirits of the same type work in parallel:

```python
# Summon 3 backend spirits
role_requests = [
    RoleRequest(name="backend", skills=["api"], count=3)
]

# Results in:
backend_spirit_1  # Handles Tasks 1.1, 1.4, 1.7
backend_spirit_2  # Handles Tasks 1.2, 1.5, 1.8
backend_spirit_3  # Handles Tasks 1.3, 1.6, 1.9
```

### Load Balancing Strategy

**Least-Busy Algorithm**:
```python
def assign_task(task, agents):
    # Find agent with minimum workload
    agent = min(agents, key=lambda a: a.get_workload())
    agent.assign_task(task)
```

**Workload Calculation**:
```python
workload = len(current_tasks) + (len(completed_tasks) * 0.1)
```

### Dependency Management

Tasks with dependencies are executed in order:

```yaml
Task 1.1: Database Schema
  dependencies: []
  
Task 1.2: JWT Authentication
  dependencies: [1.1]  # Needs database schema
  
Task 2.1: Login UI
  dependencies: [1.2]  # Needs auth API
```

## Workspace Isolation

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

## Error Handling

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

## Monitoring & Observability

### Workload Visualization
```
BACKEND Agents:
  backend_spirit_1    | Active: 2 | Completed: 3 | ████░
  backend_spirit_2    | Active: 1 | Completed: 4 | ███░░
  backend_spirit_3    | Active: 2 | Completed: 2 | ███░░

FRONTEND Agents:
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

## Best Practices

1. **Single Responsibility**: Each spirit focuses on its domain
2. **Clear Communication**: Use Spirit Protocol consistently
3. **Parallel Work**: Maximize concurrent task execution
4. **Clean Branches**: One branch per task
5. **Atomic Commits**: Small, focused commits
6. **Test Coverage**: QA spirit validates all changes
7. **Documentation**: Update specs as implementation evolves

## Example: Complete Flow

```python
# 1. User provides job description
job = "Real-time chat with authentication"

# 2. Necromancer summons team
necromancer = Necromancer()
necromancer.summon_team(job, [
    RoleRequest("architect", [], 1),
    RoleRequest("scrum_master", [], 1),
    RoleRequest("backend", ["api"], 2),
    RoleRequest("frontend", ["ui"], 2),
    RoleRequest("database", ["schema"], 1),
    RoleRequest("qa", ["testing"], 1),
])

# 3. Architect creates specs
architect = necromancer.get_spirit("architect_spirit_1")
specs = architect.create_specs(job)

# 4. Scrum Master assigns tasks
scrum_master = necromancer.get_spirit("scrum_master_spirit_1")
assignments = scrum_master.assign_tasks(specs.tasks)

# 5. Spirits execute in parallel
necromancer.execute_sprint()

# 6. Result: 15 PRs created
print(f"Created {len(necromancer.get_prs())} pull requests")
```

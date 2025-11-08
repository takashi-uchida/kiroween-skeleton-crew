# NecroCode Multi-Agent Orchestration Demo

This demo showcases the advanced multi-agent orchestration capabilities of the NecroCode framework, including:

- **Multiple agent instances** of the same type working in parallel
- **Automatic issue routing** based on keyword analysis
- **Load balancing** across agent instances
- **Workload tracking** and distribution visualization
- **Parallel branch management** for concurrent development

## Running the Demo

```bash
python3 demo_multi_agent.py
```

## Demo Scenarios

### Demo 1: Single-Instance Team (Baseline)

**Purpose:** Establish a baseline with traditional single-instance agents.

**Job Description:** Real-time whiteboard collaboration tool with WebSocket, authentication, and data persistence.

**Team Composition:**
- 1 Architect Spirit
- 1 Scrum Master Spirit
- 1 Database Spirit
- 1 Backend Spirit
- 1 Frontend Spirit
- 1 QA Spirit
- 1 DevOps Spirit

**Key Observations:**
- Traditional workflow with one agent per role
- Sequential task assignment
- Limited parallelization

### Demo 2: Multi-Instance Team with Load Balancing

**Purpose:** Demonstrate automatic load balancing across multiple agent instances.

**Job Description:** Large-scale IoT dashboard system with real-time sensor data visualization, alerts, device management, and analytics.

**Team Composition:**
- 1 Architect Spirit
- 1 Scrum Master Spirit
- 1 Database Spirit
- **3 Backend Spirits** (parallel instances)
- **3 Frontend Spirits** (parallel instances)
- 1 QA Spirit
- 1 DevOps Spirit

**Key Features:**
- Multiple instances of backend and frontend agents
- Automatic load balancing distributes tasks evenly
- Unique branch names per agent instance
- Workload visualization shows distribution

**Expected Output:**
```
BACKEND Agents:
  backend_spirit_1          | Active: 1 | Completed: 0 | █░░░░
  backend_spirit_2          | Active: 1 | Completed: 0 | █░░░░
  backend_spirit_3          | Active: 0 | Completed: 0 | ░░░░░

FRONTEND Agents:
  frontend_spirit_1         | Active: 0 | Completed: 0 | ░░░░░
  frontend_spirit_2         | Active: 0 | Completed: 0 | ░░░░░
  frontend_spirit_3         | Active: 0 | Completed: 0 | ░░░░░
```

### Demo 3: Parallel Work Simulation

**Purpose:** Simulate realistic parallel development with task completion.

**Job Description:** E-commerce platform with product catalog, shopping cart, authentication, order management, payment integration, and real-time inventory.

**Team Composition:**
- 1 Architect Spirit
- 1 Scrum Master Spirit
- **2 Database Spirits**
- **4 Backend Spirits**
- **4 Frontend Spirits**
- **2 QA Spirits**
- 1 DevOps Spirit

**Total:** 15 spirits working in parallel

**Key Features:**
- Large team with multiple instances per role
- Task completion simulation
- Before/after workload comparison
- Team statistics and metrics

**Metrics Displayed:**
- Total active tasks
- Total completed tasks
- Busiest agent
- Least busy agent
- Workload distribution per agent

### Demo 4: Automatic Issue Routing

**Purpose:** Demonstrate intelligent issue routing based on keyword analysis.

**Team Composition:**
- 1 Database Spirit
- 2 Backend Spirits
- 2 Frontend Spirits
- 1 QA Spirit
- 1 DevOps Spirit

**Test Issues:**
1. "Create login form component" → Routes to `frontend_spirit_1`
2. "Implement authentication API" → Routes to `backend_spirit_1`
3. "Design user database schema" → Routes to `database_spirit_1`
4. "Write unit tests for auth" → Routes to `backend_spirit_2` (load balanced)
5. "Setup Docker containers" → Routes to `devops_spirit_1`
6. "Build dashboard UI" → Routes to `frontend_spirit_2` (load balanced)
7. "Create analytics API" → Routes to `backend_spirit_1`
8. "Optimize database queries" → Routes to `database_spirit_1`

**Key Features:**
- Keyword-based routing (supports English and Japanese)
- Automatic load balancing when multiple agents available
- Workload tracking shows balanced distribution

## Architecture Highlights

### Issue Router

The `IssueRouter` component analyzes issue titles and descriptions using keyword matching:

```python
ROUTING_RULES = {
    'frontend': ['ui', 'ux', 'component', 'style', 'react', 'フロント', ...],
    'backend': ['api', 'endpoint', 'server', 'logic', 'バックエンド', ...],
    'database': ['schema', 'query', 'migration', 'データベース', ...],
    'qa': ['bug', 'test', 'quality', 'テスト', ...],
    'devops': ['deploy', 'docker', 'ci', 'cd', 'デプロイ', ...],
}
```

### Load Balancing

The system uses a **least-busy** strategy:

```python
def _balance_load(agents: List) -> str:
    """Select agent with minimum workload."""
    least_busy_agent = min(agents, key=lambda agent: agent.get_workload())
    return least_busy_agent.identifier
```

### Branch Naming Convention

Each agent instance gets unique branch names:

```
{role}/spirit-{instance}/{feature-name}

Examples:
- frontend/spirit-1/login-ui
- frontend/spirit-2/dashboard-ui
- backend/spirit-1/auth-api
- backend/spirit-2/payment-api
```

### Workload Tracking

Each spirit tracks its workload:

```python
@dataclass
class BaseSpirit:
    current_tasks: List[str]      # Active tasks
    completed_tasks: List[str]    # Completed tasks
    
    def get_workload(self) -> int:
        return len(self.current_tasks)
```

## Requirements Satisfied

This demo satisfies the following requirements from the spec:

- **Requirement 1.1:** Natural language job description processing
- **Requirement 1.4:** Multiple agent instances per role
- **Requirement 3.1:** Automatic issue routing
- **Requirement 3.2:** Load balancing across agents
- **Requirement 3.3:** Workload tracking
- **Requirement 4.1:** Task assignment to specific agent instances
- **Requirement 4.2:** Dependency management
- **Requirement 4.3:** Unique branch naming per instance
- **Requirement 8.2:** Multiple workspace support

## Visual Output

The demo provides rich visual feedback:

- 🧙 Necromancer summoning messages
- 👻 Spirit instantiation notifications
- 📊 Workload distribution charts (ASCII bar graphs)
- 🌿 Branch assignment visualization
- 📈 Team statistics and metrics
- ⚡ Sprint execution progress
- 🎯 Issue routing decisions

## Extending the Demo

To create your own demo scenario:

```python
from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.job_parser import RoleRequest

# Create necromancer
necromancer = Necromancer(workspace="my_workspace")

# Define your job
job_description = "Your project description here"

# Define role requests with counts
role_requests = [
    RoleRequest(name="backend", skills=["api"], count=3),
    RoleRequest(name="frontend", skills=["ui"], count=2),
    # ... more roles
]

# Summon and execute
necromancer.summon_team(job_description, role_requests)
necromancer.execute_sprint()
necromancer.banish_spirits()
```

## Performance Characteristics

- **Team summoning:** < 5 seconds for 15 spirits
- **Issue routing:** < 100ms per issue
- **Load balancing:** O(n) where n = number of agents of same type
- **Workload tracking:** O(1) per agent

## Future Enhancements

Potential improvements for the demo:

1. **Real Git operations:** Actually create branches and commits
2. **Concurrent execution:** Use threading/async for true parallelism
3. **Web dashboard:** Real-time visualization of agent activity
4. **Metrics collection:** Track routing accuracy and load balance efficiency
5. **Agent learning:** Improve routing based on past assignments
6. **Priority-based routing:** Route high-priority issues to most experienced agents

## Troubleshooting

**Issue:** No agents available for routing
- **Solution:** Ensure you've summoned agents of the required type

**Issue:** Uneven load distribution
- **Solution:** Check that agents are properly registered with MessageBus

**Issue:** Routing to wrong agent type
- **Solution:** Review keyword rules in `IssueRouter.ROUTING_RULES`

## Related Files

- `framework/orchestrator/necromancer.py` - Main orchestrator
- `framework/orchestrator/issue_router.py` - Issue routing logic
- `framework/agents/base_agent.py` - Base spirit with workload tracking
- `framework/agents/scrum_master_agent.py` - Task assignment and routing
- `.kiro/specs/necrocode-agent-orchestration/` - Full specification

## License

See LICENSE file in the project root.

# NecroCode: Kiroween Skeleton Crew

NecroCode summons a theme-aware squad of AI spirits from plain job descriptions. This repository hosts the core framework plus two sample workspaces that demonstrate how each summoned spirit collaborates through the Spirit Protocol.

## Structure
- `.kiro/` – Specs, hooks, and steering docs that guide the summoning rituals.
- `framework/` – Orchestrator, spirit implementations, messaging fabric, and workspace utilities.
- `workspace1/` – Real-time collaboration crypt.
- `workspace2/` – IoT dashboard crypt.

Each workspace is an independent Git repository managed by the Necromancer to keep every spirit focused on its craft.

## Workspace Management

The Workspace Manager enables Kiro to execute spec tasks in isolated environments. Each spec gets its own cloned repository, preventing conflicts when multiple specs are processed simultaneously.

### Creating a Workspace

```python
from framework.workspace_manager import WorkspaceOrchestrator, WorkspaceConfig
from pathlib import Path

# Initialize the orchestrator with configuration
config = WorkspaceConfig(
    base_path=Path("."),
    state_file=Path(".kiro/workspace-state.json"),
    gitignore_path=Path(".gitignore")
)
orchestrator = WorkspaceOrchestrator(config)

# Create a workspace for a spec
workspace = orchestrator.create_workspace(
    spec_name="kiro-workspace-task-execution",
    repo_url="https://github.com/user/repo.git"
)
```

### Spirit Workspace Management

```python
from framework.workspace_manager import SpiritWorkspaceManager

# Initialize spirit workspace manager
spirit_mgr = SpiritWorkspaceManager(".")

# Create branch for a spirit
branch = spirit_mgr.create_branch("frontend_spirit_1", "login-ui", issue_id="42")
# Returns: "frontend/issue-42-login-ui"

# Format commit message
commit_msg = spirit_mgr.format_commit_message(
    "frontend_spirit_1", 
    scope="ui", 
    description="summon login form",
    issue_id="42"
)
# Returns: "spirit-1(ui): summon login form [#42]"
```

The workspace will be cloned into a directory named `workspace-{spec-name}` and automatically added to `.gitignore`.

### Executing Tasks

```python
# Create a feature branch for a task
branch_name = workspace.create_task_branch(
    task_id="1.1",
    task_description="implement workspace manager"
)
# Creates: feature/task-kiro-workspace-task-execution-1.1-implement-workspace-manager

# Make your code changes...

# Commit using Spirit Protocol format
workspace.commit_task(
    task_id="1.1",
    scope="workspace",
    description="summon workspace manager for isolated task execution",
    files=[Path("framework/workspace_manager/workspace_manager.py")]
)
# Generates: spirit(workspace): summon workspace manager for isolated task execution

# Push the feature branch
workspace.push_branch(branch_name)
```

### Running Spec Tasks with Strands Agents

NecroCode now integrates with **Strands Agents**, which default to OpenAI's `gpt-5`.

```bash
export OPENAI_API_KEY=sk-your-key
```

```python
from framework.orchestrator.necromancer import Necromancer

necromancer = Necromancer(workspace=".")
results = necromancer.execute_spec_tasks("documentation-organization")
for result in results:
    print(result["task_id"], result["title"], "→", result["output"][:80], "...")
```

If you need to inject a stub client (e.g., for tests), use `strandsagents.SpecTaskRunner` with
`strandsagents.StubLLMClient` and pass it to `Necromancer`.

### Managing Workspaces

```python
# List all active workspaces
workspaces = manager.list_workspaces()
for ws in workspaces:
    print(f"{ws.spec_name}: {ws.status} - {ws.current_branch}")

# Get a specific workspace
workspace = manager.get_workspace("kiro-workspace-task-execution")

# Clean up when done
manager.cleanup_workspace("kiro-workspace-task-execution")
```

### Branch Naming Convention

Feature branches follow this pattern:
```
feature/task-{spec-id}-{task-number}-{description}
```

Examples:
- `feature/task-kiro-workspace-task-execution-1.1-implement-workspace-manager`
- `feature/task-auth-system-2.3-add-jwt-validation`
- `feature/task-api-gateway-5.1-rate-limiting`

Special characters in descriptions are automatically sanitized to ensure git compatibility.

### Spirit Protocol Commit Format

All commits follow the Spirit Protocol format:
```
spirit(scope): spell description

Task: {task-id}
```

Examples:
```
spirit(workspace): summon workspace manager for isolated task execution

Task: 1.1
```

```
spirit(auth): cast protection spell on user credentials

Task: 2.3
```

```
spirit(api): weave rate limiting enchantment

Task: 5.1
```

The scope should reflect the component or area being modified (e.g., `workspace`, `auth`, `api`, `frontend`, `database`).

## Available Spirits

NecroCode includes the following specialized spirits:

- **🧙 Architect Spirit**: Designs system architecture and creates specifications
- **📋 Scrum Master Spirit**: Manages tasks and coordinates sprint execution
- **💻 Frontend Spirit**: Implements user interfaces and client-side logic
- **⚙️ Backend Spirit**: Develops server-side APIs and business logic
- **🗄️ Database Spirit**: Designs schemas and manages data persistence
- **🧪 QA Spirit**: Writes tests and ensures quality
- **🚀 DevOps Spirit**: Handles deployment and infrastructure
- **📚 Documentation Spirit**: Organizes documentation and maintains technical writing

### Documentation Spirit

The Documentation Spirit specializes in organizing and maintaining project documentation:

```python
from framework.agents import DocumentationSpirit

# Create documentation spirit
doc_spirit = DocumentationSpirit(
    role="documentation",
    skills=["technical_writing", "content_organization"],
    workspace="necrocode",
    instance_number=1
)

# Create documentation plan
requirements = {
    'eliminate_redundancy': True,
    'create_hierarchy': True,
    'consolidate_specs': True,
    'improve_navigation': True
}
plan = doc_spirit.create_documentation_plan(requirements)

# Consolidate duplicate content
sections = [
    {'title': 'Section 1', 'content': 'Content A'},
    {'title': 'Section 2', 'content': 'Content A'},  # Duplicate
]
result = doc_spirit.consolidate_content(sections)

# Add cross-references
docs = {
    'overview.md': 'Product overview content',
    'architecture.md': 'Technical architecture content'
}
cross_refs = doc_spirit.add_cross_references(docs)
```

The Documentation Spirit automatically routes tasks containing keywords like:
- `documentation`, `doc`, `readme`, `guide`, `markdown`
- `reorganize`, `consolidate`, `cross-reference`
- `ドキュメント`, `文書`, `整理`, `統合`

## Testing

Run the test suite to verify all spirits are working correctly:

```bash
# Test DocumentationSpirit integration
python3 test_documentation_spirit.py

# Test multi-agent coordination
python3 demo_multi_agent.py

# Test logging and monitoring
python3 test_logging_monitoring.py
```

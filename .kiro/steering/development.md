# NecroCode Development Guide

## Quick Reference
- **Purpose**: Describe how to build, extend, and operate NecroCode.
- **Audience**: Spirits implementing tasks and humans maintaining the framework.
- **Related Docs**: Product framing → `overview.md`, system design → `architecture.md`.

## Directory Layout
```
.
├── .kiro/
│   ├── specs/                # Framework specs + task plans
│   └── steering/             # Overview, architecture, and this guide
├── framework/
│   ├── agents/               # Spirit abstractions and helpers
│   ├── communication/        # Spirit Protocol + bus utilities
│   ├── orchestrator/         # Necromancer, issue routing, workload monitors
│   └── workspace_manager/    # Git + workspace lifecycle
├── necrocode/task_registry/  # Task/event/artifact persistence
├── strandsagents/            # LLM runners (StrandsAgent, SpecTaskRunner)
├── examples/                 # Usage demos and notebooks
├── tests/                    # Pytest suites
└── demo_* / scripts/         # Scenario walkthroughs
```

### `.kiro/`
- `steering/` hosts canonical steering docs; historical inputs live as `.bak` backups.
- `specs/` contains requirements/design/tasks for every subsystem (agent runner, repo pool, dispatcher, etc.). Specs sync with the Task Registry through `necrocode/task_registry/kiro_sync.py`.

### `framework/`
- `agents/`: Higher-level spirit logic (task planners, team builders).
- `communication/`: Spirit Protocol serialization and bus helpers (future dispatcher hooks).
- `orchestrator/`: Necromancer coordination (`necromancer.py`), issue routing, workload monitoring, and team composition.
- `workspace_manager/`: `BranchStrategy`, `GitOperations`, `Workspace`, `WorkspaceManager`, `.gitignore` manager, and `StateTracker`.

### `necrocode/task_registry/`
Implements `TaskRegistry`, persistence stores, locking, query/graph engines, and kiro-sync utilities. All data is JSON or JSONL for easy inspection.

### `strandsagents/`
Contains `StrandsAgent`, `SpecTaskRunner`, and OpenAI client wrappers used by orchestration flows and upcoming TaskExecutionOrchestrator features.

### `examples/` & `demos/`
Self-contained scripts such as `examples/basic_usage.py`, `demo_multi_agent.py`, and `demo_task_registry_graph.py` illustrate standard flows. Treat these as living runbooks.

## Module Organization & Imports
- Always prefer absolute imports (e.g., `from framework.workspace_manager.workspace import Workspace`).
- Keep domain dataclasses next to their modules (`WorkspaceInfo` in `workspace_manager/models.py`, `Taskset` in `task_registry/models.py`).
- Orchestrator modules should be thin: call into dedicated helpers rather than embedding Git or registry logic directly.

## Naming Conventions
- **Branches**: `feature/task-{spec-id}-{task-number}-{slug}` generated via `BranchStrategy.generate_branch_name`. Multi-instance spirits may use `{role}/spirit-{instance}/{slug}`.
- **Commits**: `spirit(scope): <spell description> [Task X.Y]` via `Workspace.commit_task`.
- **Specs/Tasks**: Decimal numbering (1, 1.1, 1.1.1) with `_Requirements:` breadcrumbs that match requirement IDs.
- **Code**: Modules/folders snake_case, classes PascalCase, functions snake_case, constants UPPER_SNAKE_CASE, exports defined in each `__all__`.

## Spirit Workflow
1. **Summoning** – `framework/orchestrator/team_builder.py` reads role requests, instantiates spirits (possibly multiple instances per role), and registers them with the message bus.
2. **Planning** – Architect/ScrumMaster spirits parse `.kiro/specs/*/tasks.md`; `necrocode/task_registry/kiro_sync.py` mirrors them into the Task Registry with dependency graphs.
3. **Execution** – Agent Runner (spec) or other spirits request workspaces from `WorkspaceManager`, apply code changes, and follow Spirit Protocol formatting for branches/commits.
4. **Reporting** – Events flow into `event_store.py`; artifacts attach via `TaskRegistry.add_artifact`. Dispatcher/Review PR Service specs describe how results return to humans.
5. **Completion** – Dependent tasks unblock automatically (`TaskRegistry.update_task_state`), workspaces are cleaned with `WorkspaceManager.cleanup_workspace`, and Repo Pool slots return to the pool.

## Context Building & Prompting
- `SpecTaskRunner` (`strandsagents/spec_runner.py`) parses tasks and produces `StrandsTask`s.
- Feed requirements/design snippets into the optional `context` dict when invoking `StrandsAgent.run_task`; prompts already include identifiers, descriptions, and checklists.
- Default LLM model is `gpt-5-codex`; override via the runner, agent, or `OPENAI_MODEL` environment variable when experimenting.

## Parallel Execution & Load Balancing
- Multi-instance routing is implemented per `.kiro/specs/necrocode-agent-orchestration`: IssueRouter checks bilingual keyword rules, then asks each spirit for `get_workload()` to choose the least busy instance.
- Workspace Manager is concurrency-safe thanks to file locks in `lock_manager.py`; open separate `Workspace` objects per task to avoid shared mutable state.
- Repo Pool Manager (spec) will furnish pre-warmed git slots. Keep new code stateless so it can run on multiple runners behind the Dispatcher.

## Error Handling & Monitoring
- Git operations raise descriptive exceptions; wrap whole task executions in try/except to add task context before bubbling up.
- `strandsagents/llm.OpenAIChatClient` validates `OPENAI_API_KEY` and should be wrapped with retry/backoff logic when TaskExecutionOrchestrator lands (spec tasks 17–19).
- Emit structured logs (see `demo_logging_monitoring.py`) including task IDs, workspace paths, and agent instances. Metric hooks planned in the agent-runner spec should capture runtime, retries, and artifact counts.

## Testing Strategy
- Unit tests live in `tests/` (e.g., `tests/test_task_registry.py`, `tests/test_lock_manager.py`, `tests/test_ai_components.py`). Use pytest fixtures/temp directories for filesystem work.
- Integration tests at repo root (`test_graph_visualization.py`, `test_logging_monitoring.py`, etc.) ensure multiple modules cooperate correctly.
- When adding new services, create targeted fixtures (mock git repos, stub LLM clients) and document them in `tests/README.md` if patterns become reusable.

## Extension Points
- **TaskExecutionOrchestrator** (`framework/task_executor/` spec) will coordinate StrandsAgent output, file writes, commits, and pushes.
- **Dispatcher** will pull ready tasks from Task Registry and hand them to Agent Runner instances.
- **Artifact Store** persists logs/diffs/binaries for Review PR Service and downstream analysis.
- **Review PR Service** automates diff review and emits findings back into Task Registry events.

## Best Practices
- Never mutate files under `examples/`; treat them as golden demos.
- Use `WorkspaceManager` for every branch/commit—manual git commands can bypass Spirit Protocol conventions.
- Always update Task Registry state alongside workspace actions to keep kiro-sync in agreement with the Markdown specs.
- Clean up temporary workspaces/slots even on failure to avoid stale locks.

## Cross-References
- High-level value prop & workflow: `overview.md`
- Component responsibilities & Spirit Protocol: `architecture.md`
- Detailed requirements: `.kiro/specs/<service>/requirements.md`

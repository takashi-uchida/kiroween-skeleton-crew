# NecroCode v2: Kiro Parallel Execution with Git Worktree

## Core Concept
One repository, multiple worktrees (physically independent directories). Each worktree runs an independent Kiro instance in parallel, with coordination and synchronization managed by a central task registry.

## Git Worktree Advantages
- **Physical Isolation**: Each worktree is an independent directory.
- **Git Integration**: Shares the same repository, but branches are independent.
- **Parallel Safety**: No filesystem-level conflicts.
- **Efficiency**: Shared `.git` directory, minimizing disk usage.

## Architecture Diagram

```
project/
├── .git/                          # Shared Git repository
├── main/                          # Main worktree
│   ├── necrocode/                 # Orchestrator
│   ├── .kiro/
│   │   ├── tasks/
│   │   │   └── chat-app/
│   │   │       └── tasks.json     # Task definitions
│   │   └── registry/              # Shared Task Registry
│   │       ├── tasks.jsonl
│   │       └── events.jsonl
│   └── ...
│
├── worktree-task-1/               # Worktree dedicated to Task 1
│   ├── .kiro/
│   │   └── current-task.md        # Task 1 Context
│   └── [Branch: feature/task-1-auth]
│
├── worktree-task-2/               # Worktree dedicated to Task 2
│   ├── .kiro/
│   │   └── current-task.md        # Task 2 Context
│   └── [Branch: feature/task-2-websocket]
│
└── worktree-task-3/               # Worktree dedicated to Task 3
    └── [Branch: feature/task-3-login-ui]
```

## Core Components

### 1. Worktree Manager (`necrocode/worktree_manager.py`)
Manages Git worktree operations (create, remove, list).

```python
# ... (Class definition from user's proposal) ...
```

### 2. Parallel Orchestrator (`necrocode/parallel_orchestrator.py`)
Orchestrates parallel task execution.

```python
# ... (Class definition from user's proposal) ...
```

### 3. Task Context Generator (`necrocode/task_context.py`)
Generates the `current-task.md` context file for Kiro.

```python
# ... (Class definition from user's proposal) ...
```

### 4. Kiro Invoker (`necrocode/kiro_invoker.py`)
Invokes the Kiro CLI (or API) within a worktree.

```python
# ... (Class definition from user's proposal) ...
```

### 5. CLI Interface (`necrocode/cli.py`)
Provides command-line interaction (`plan`, `execute`, `status`).

```python
# ... (CLI Interface definition from user's proposal) ...
```

## Workflow Example
```bash
# 1. Plan tasks
necrocode plan "認証機能付きチャットアプリ"

# 2. Execute in parallel (e.g., 3 Kiro instances)
necrocode execute chat-app --workers 3

# Execution in progress:
# [Worktree 1] Task 1: Database schema implementation...
# [Worktree 2] Task 2: JWT authentication implementation...
# [Worktree 3] Task 4: Login UI implementation...
# ✓ Task 1 completed → PR #101
# [Worktree 1] Task 3: WebSocket server implementation...
# ✓ Task 2 completed → PR #102
# ...

# 3. Check status
necrocode status
```

## Key Advantages
1.  **True Parallel Execution**: Multiple Kiro instances operate in physically isolated environments.
2.  **Git Integration**: Worktrees are a native Git feature.
3.  **No Conflicts**: Filesystem-level isolation prevents conflicts.
4.  **Efficiency**: Shared `.git` directory, efficient disk usage.
5.  **Simplicity**: Avoids complex inter-agent communication overhead.
6.  **Scalability**: Configurable number of workers.

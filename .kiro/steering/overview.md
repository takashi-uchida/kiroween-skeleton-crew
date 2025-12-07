# NecroCode Overview
## Quick Reference
- **Purpose**: Explain NecroCode's value, concepts, and who benefits.
- **Audience**: Stakeholders, onboarding developers, and spirits needing context.
- **Read Next**: Technical design → architecture.md, implementation guide → development.md.
## Product Vision
NecroCode is an AI-powered Kiro-native parallel development framework that transforms natural language job descriptions into fully implemented applications. It orchestrates independent Kiro instances, each operating within an isolated Git worktree, to collaborate autonomously and design, implement, test, and deploy software projects.
## Core Concept
Instead of manual coordination, NecroCode:
1. Takes a plain English/Japanese job description.
2. The Task Planner breaks it down into structured tasks with dependencies.
3. The Parallel Orchestrator creates isolated Git worktrees for tasks.
4. Each worktree runs an independent Kiro instance, executing tasks in parallel.
5. Kiro instances implement solutions, commit changes, and the Orchestrator handles PR creation.
## Key Features


### 🔄 Multi-Instance Support
- Multiple independent Kiro instances run in parallel within isolated Git worktrees.
- Automatic distribution of tasks across available Kiro instances.
- Each worktree operates on a unique Git branch.

### 🏗️ Workspace Management
- Clones user's GitHub workspace dynamically
- Creates isolated workspaces per spec
- Manages branches and commits automatically
- Prevents conflicts between concurrent specs
## High-Level Workflow
NecroCode now follows this workflow, leveraging Git worktrees for parallel execution. See `architecture.md` for component internals.
```
ユーザー入力: "認証機能付きのリアルタイムチャットアプリを作成"
     ↓
necrocode plan "Create a real-time chat app with authentication"
     ↓
Task Planner generates tasks → .kiro/tasks/chat-app/tasks.json
     ↓
necrocode execute chat-app --workers 3
     ↓
Parallel Orchestrator creates isolated Git worktrees for tasks
     ↓
Independent Kiro instances in each worktree implement assigned tasks
     ↓
Each Kiro instance commits changes to its worktree's branch
     ↓
Parallel Orchestrator creates PRs for completed tasks
     ↓
Result: Multiple PRs ready for review in your GitHub repo, potentially in parallel.
```
## Target Users
- Solo developers who need to scale productivity
- Teams wanting to automate routine development tasks
- Startups needing rapid prototyping
- Anyone who wants to describe what they want and get working code
## Differentiation
Unlike traditional code generators:
- **Kiro-native parallel collaboration**: Independent Kiro instances collaborate in parallel via isolated Git worktrees.
- **Spec-driven**: Creates detailed design docs before coding.
- **Git-native**: Works directly with your workspace, leveraging Git worktrees.
- **True parallel execution**: Multiple Kiro instances work simultaneously.
- **Task-aware**: Understands dependencies and execution order.
## See Also
- [architecture.md](architecture.md) — Kiro-native Parallel Architecture, components, data models


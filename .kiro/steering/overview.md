# NecroCode Overview
## Quick Reference
- **Purpose**: Explain NecroCode's value, concepts, and who benefits.
- **Audience**: Stakeholders, onboarding developers, and spirits needing context.
- **Read Next**: Technical design → architecture.md, implementation guide → development.md.
## Product Vision
NecroCode is an AI-powered multi-spirit development framework that transforms natural language job descriptions into fully implemented applications. It summons a team of specialized AI "spirits" that collaborate autonomously to design, implement, test, and deploy software projects.
## Core Concept
Instead of manually coordinating multiple developers, NecroCode:
1. Takes a plain English/Japanese job description
2. Summons specialized AI spirits (spirits) for each role
3. Automatically generates detailed specs and task breakdowns
4. Executes tasks in parallel across multiple spirit instances
5. Creates pull requests in your GitHub workspace
## Key Features
### 🧙 Necromancer (Necromancer)
- Parses job descriptions
- Summons appropriate spirits
- Coordinates the entire development lifecycle
- Manages workspace isolation

### 👻 Specialized Spirits
- **Architect Spirit**: Creates specs from job descriptions
- **Scrum Master Spirit**: Breaks down specs into tasks, assigns to spirits
- **Developer Spirits**: Frontend, Backend, Database specialists
- **QA Spirit**: Testing and quality assurance
- **DevOps Spirit**: Deployment and infrastructure

### 🔄 Multi-Instance Support
- Multiple instances of the same spirit type work in parallel
- Automatic load balancing across instances
- Unique branch naming per instance (e.g., `frontend/spirit-1/login-ui`)

### 📡 Spirit Protocol
- Standardized communication format between spirits
- Commit message format: `spirit(scope): description [Task X.Y]`
- Branch naming: `feature/task-{spec}-{task-id}-{description}`

### 🏗️ Workspace Management
- Clones user's GitHub workspace dynamically
- Creates isolated workspaces per spec
- Manages branches and commits automatically
- Prevents conflicts between concurrent specs
## High-Level Workflow
NecroCode always follows the same ritualized flow. See `architecture.md` for component internals and `development.md` for implementation details.
```
User Input: "Create a real-time chat app with authentication"
     ↓
Necromancer clones your repo → workspace-chat-app/
     ↓
Architect Spirit generates specs → .kiro/specs/chat-app/
     ↓
Scrum Master breaks into 15 tasks
     ↓
Backend Spirit 1 → Task 1.1 (JWT auth)
Backend Spirit 2 → Task 1.2 (WebSocket)
Frontend Spirit 1 → Task 2.1 (Login UI)
Frontend Spirit 2 → Task 2.2 (Chat UI)
     ↓
Each spirit creates branch, commits, pushes PR
     ↓
Result: 15 PRs ready for review in your GitHub repo
```
## Target Users
- Solo developers who need to scale productivity
- Teams wanting to automate routine development tasks
- Startups needing rapid prototyping
- Anyone who wants to describe what they want and get working code
## Differentiation
Unlike traditional code generators:
- **Multi-spirit collaboration**: Spirits work together like a real team
- **Spec-driven**: Creates detailed design docs before coding
- **Git-native**: Works directly with your workspace
- **Parallel execution**: Multiple spirits work simultaneously
- **Task-aware**: Understands dependencies and execution order
## See Also
- [architecture.md](architecture.md) — Spirit Protocol, components, data models
- [development.md](development.md) — Directory structure, workflows, best practices

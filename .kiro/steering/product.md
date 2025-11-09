# NecroCode - Product Overview

## What is NecroCode?

NecroCode is an AI-powered multi-agent development framework that transforms natural language job descriptions into fully implemented applications. It summons a team of specialized AI "spirits" that collaborate autonomously to design, implement, test, and deploy software projects.

## Core Concept

Instead of manually coordinating multiple developers, NecroCode:
1. Takes a plain English/Japanese job description
2. Summons specialized AI agents (spirits) for each role
3. Automatically generates detailed specs and task breakdowns
4. Executes tasks in parallel across multiple agent instances
5. Creates pull requests in your GitHub repository

## Key Features

### 🧙 Necromancer (Orchestrator)
- Parses job descriptions
- Summons appropriate spirits
- Coordinates the entire development lifecycle
- Manages workspace isolation

### 👻 Specialized Spirits
- **Architect Spirit**: Creates specs from job descriptions
- **Scrum Master Spirit**: Breaks down specs into tasks, assigns to agents
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
- Clones user's GitHub repository dynamically
- Creates isolated workspaces per spec
- Manages branches and commits automatically
- Prevents conflicts between concurrent specs

## How It Works

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
- **Multi-agent collaboration**: Spirits work together like a real team
- **Spec-driven**: Creates detailed design docs before coding
- **Git-native**: Works directly with your repository
- **Parallel execution**: Multiple agents work simultaneously
- **Task-aware**: Understands dependencies and execution order

## Technology Stack

- **Language**: Python 3.11+
- **VCS**: Git (GitHub integration)
- **AI**: Kiro AI agents
- **Protocol**: Spirit Protocol (custom communication format)
- **Architecture**: Event-driven, message-based coordination

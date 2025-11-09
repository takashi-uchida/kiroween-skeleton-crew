# Real-time Collaboration Tool

**Built with NecroCode Framework** 🧙‍♂️

This application was created using the NecroCode multi-agent development framework. It demonstrates how NecroCode transforms a simple job description into a fully implemented application.

## Project Overview

A real-time collaborative whiteboard application with WebSocket communication, user authentication, and data persistence.

## How It Was Built

### Job Description
```
"Create a real-time collaboration tool with whiteboard functionality, 
user authentication, and persistent storage"
```

### NecroCode Process

1. **Necromancer** parsed the job description and cloned this repository
2. **Architect Spirit** designed the system architecture and generated specs
3. **Scrum Master Spirit** broke down the specs into 15 implementable tasks
4. **Developer Spirits** (Backend, Frontend, Database) executed tasks in parallel
5. **QA Spirit** validated all implementations
6. **DevOps Spirit** configured deployment

### Generated Specifications

The complete specs used to build this application are available in:
```
.kiro/specs/whiteboard-app/
├── requirements.md    # Functional and non-functional requirements
├── design.md         # Architecture, tech stack, component design
└── tasks.md          # 15 tasks with dependencies
```

### Technology Stack

**Decided by Architect Spirit:**
- **Frontend**: React + TypeScript + Canvas API
- **Backend**: Node.js + Express + Socket.io
- **Database**: MongoDB + Redis (for real-time state)
- **Authentication**: JWT

### Tasks Executed

15 tasks were executed in parallel by multiple spirit instances:

**Backend Spirits:**
- Task 1.1: Database schema design
- Task 1.2: JWT authentication system
- Task 1.3: WebSocket server setup
- Task 1.4: Drawing data persistence
- Task 1.5: User session management

**Frontend Spirits:**
- Task 2.1: Login/registration UI
- Task 2.2: Canvas drawing component
- Task 2.3: Real-time cursor tracking
- Task 2.4: Collaboration features
- Task 2.5: Responsive layout

**Database Spirit:**
- Task 3.1: MongoDB schema
- Task 3.2: Redis caching layer
- Task 3.3: Data migration scripts

**QA Spirit:**
- Task 4.1: Unit tests
- Task 4.2: Integration tests

**DevOps Spirit:**
- Task 5.1: Docker configuration

### Pull Requests Created

Each task resulted in a separate pull request with:
- Feature branch: `feature/task-whiteboard-app-{task-id}-{description}`
- Commit message: `spirit(scope): description [Task X.Y]`
- Code review by QA Spirit

## Features

- ✅ Real-time collaborative drawing
- ✅ Multi-user cursor tracking
- ✅ User authentication (JWT)
- ✅ Persistent canvas state
- ✅ WebSocket communication
- ✅ Responsive design
- ✅ Session management

## Running the Application

```bash
# Install dependencies
npm install

# Start backend
cd backend && npm start

# Start frontend (in another terminal)
cd frontend && npm start
```

## About NecroCode

NecroCode is an AI-powered multi-agent development framework that:
- Transforms natural language descriptions into working applications
- Coordinates multiple specialized AI agents (spirits)
- Generates detailed specifications before coding
- Executes tasks in parallel for maximum efficiency
- Creates pull requests ready for review

Learn more: [NecroCode Repository](../../README.md)

## License

See [LICENSE](../../LICENSE)

# NecroCode Quick Start Guide

Get started with NecroCode in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- Docker (optional, for containerized runners)
- GitHub/GitLab account with API token

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/necrocode.git
cd necrocode

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x necrocode_cli.py
```

## Quick Start

### 1. Setup Services

Initialize NecroCode services with default configuration:

```bash
python necrocode_cli.py setup
```

This creates configuration files in `.necrocode/`:
- `task_registry.json` - Task persistence
- `repo_pool.json` - Repository workspace management
- `dispatcher.json` - Task scheduling
- `artifact_store.json` - Build artifacts
- `review_pr_service.json` - PR automation

### 2. Configure Credentials

Set required environment variables:

```bash
# GitHub token (required for PR creation)
export GITHUB_TOKEN="your_github_token"

# LLM API key (required for task implementation)
export OPENAI_API_KEY="your_openai_api_key"

# Optional: GitLab token
export GITLAB_TOKEN="your_gitlab_token"
```

### 3. Submit a Job

Submit a job description in natural language:

```bash
python necrocode_cli.py submit \
  --project my-api \
  --repo https://github.com/your-org/my-api.git \
  "Create a REST API with user authentication and CRUD operations"
```

This will:
- Parse the job description
- Generate a task breakdown
- Create tasks in Task Registry
- Return a job ID for tracking

### 4. Start Services

Start all NecroCode services:

```bash
# Start in foreground (Ctrl+C to stop)
python necrocode_cli.py start

# Or start in background
python necrocode_cli.py start --detached
```

Services will:
- Monitor Task Registry for ready tasks
- Allocate workspace slots
- Launch Agent Runners (Docker containers or local processes)
- Execute tasks with LLM
- Create PRs automatically

### 5. Monitor Progress

Check job status:

```bash
python necrocode_cli.py job status <job-id>
```

View service logs:

```bash
# All services
python necrocode_cli.py logs

# Specific service
python necrocode_cli.py logs --service dispatcher

# Follow logs
python necrocode_cli.py logs --follow
```

Check service health:

```bash
python necrocode_cli.py status
```

### 6. Review Pull Requests

Once tasks complete, PRs will be created automatically on GitHub/GitLab.

Review and merge PRs:
1. Go to your repository on GitHub
2. Review the automated PRs
3. Merge approved PRs

## Example Workflow

```bash
# 1. Setup
python necrocode_cli.py setup

# 2. Configure credentials
export GITHUB_TOKEN="ghp_..."
export OPENAI_API_KEY="sk-..."

# 3. Submit job
JOB_ID=$(python necrocode_cli.py submit \
  --project chat-app \
  --repo https://github.com/me/chat-app.git \
  "Create a real-time chat application with WebSocket support" | grep "Job submitted" | awk '{print $3}')

# 4. Start services
python necrocode_cli.py start --detached

# 5. Monitor
watch -n 5 "python necrocode_cli.py job status $JOB_ID"

# 6. Stop when done
python necrocode_cli.py stop
```

## Configuration

### Dispatcher Configuration

Edit `.necrocode/dispatcher.json`:

```json
{
  "poll_interval": 5,
  "scheduling_policy": "priority",
  "max_global_concurrency": 10,
  "agent_pools": [
    {
      "name": "docker",
      "type": "docker",
      "max_concurrency": 5,
      "cpu_quota": 4,
      "memory_quota": 8192,
      "config": {
        "image": "necrocode/runner:latest"
      }
    }
  ]
}
```

### Skill Mapping

Map task types to agent pools:

```json
{
  "skill_mapping": {
    "backend": ["docker"],
    "frontend": ["docker"],
    "database": ["docker"],
    "qa": ["local"],
    "default": ["local"]
  }
}
```

## Docker Runner Setup

Build the runner image:

```bash
cd docker
docker build -t necrocode/runner:latest .
```

Or use pre-built image:

```bash
docker pull necrocode/runner:latest
```

## Kubernetes Setup

For production deployments:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Configure dispatcher for Kubernetes
# Edit .necrocode/dispatcher.json:
{
  "agent_pools": [
    {
      "name": "k8s",
      "type": "kubernetes",
      "max_concurrency": 20,
      "config": {
        "namespace": "necrocode-agents",
        "image": "necrocode/runner:latest"
      }
    }
  ]
}
```

## Troubleshooting

### Services won't start

Check logs:
```bash
python necrocode_cli.py logs
```

Verify configuration:
```bash
ls -la .necrocode/
cat .necrocode/dispatcher.json
```

### Tasks not executing

1. Check Dispatcher is running:
   ```bash
   python necrocode_cli.py status
   ```

2. Verify Task Registry has tasks:
   ```bash
   ls -la .necrocode/data/task_registry/
   ```

3. Check agent pool configuration:
   ```bash
   cat .necrocode/dispatcher.json | jq '.agent_pools'
   ```

### PRs not created

1. Verify GitHub token:
   ```bash
   echo $GITHUB_TOKEN
   ```

2. Check Review PR Service logs:
   ```bash
   python necrocode_cli.py logs --service review_pr_service
   ```

3. Verify webhook configuration (if using webhooks)

## Advanced Usage

### Custom Task Breakdown

Provide custom task breakdown instead of LLM generation:

```python
from necrocode.orchestration.job_submitter import JobSubmitter
from necrocode.task_registry.models import Task, TaskState

submitter = JobSubmitter()

# Create custom tasks
tasks = [
    Task(
        id="1",
        title="Setup database schema",
        description="Create User and Post models",
        state=TaskState.PENDING,
        dependencies=[],
        required_skill="database"
    ),
    Task(
        id="2",
        title="Implement API endpoints",
        description="Create REST endpoints for CRUD operations",
        state=TaskState.PENDING,
        dependencies=["1"],
        required_skill="backend"
    )
]

# Submit with custom tasks
job_id = submitter.submit_job_with_tasks(
    project_name="my-api",
    tasks=tasks,
    repo_url="https://github.com/me/my-api.git"
)
```

### Parallel Execution

Configure parallel execution limits:

```json
{
  "max_global_concurrency": 20,
  "agent_pools": [
    {
      "name": "docker-pool-1",
      "max_concurrency": 10
    },
    {
      "name": "docker-pool-2",
      "max_concurrency": 10
    }
  ]
}
```

### Custom Playbooks

Define custom execution playbooks:

```yaml
# .necrocode/playbooks/backend-api.yaml
name: Backend API Implementation
steps:
  - name: Setup
    commands:
      - npm install
  - name: Implement
    llm_prompt: "Implement the API endpoint as described"
  - name: Test
    commands:
      - npm test
  - name: Lint
    commands:
      - npm run lint
```

## Next Steps

- Read [Architecture Guide](architecture.md) for system design
- See [Development Guide](development.md) for contributing
- Check [Examples](examples/) for more use cases
- Join our [Discord](https://discord.gg/necrocode) for support

## Support

- Documentation: https://necrocode.dev/docs
- Issues: https://github.com/your-org/necrocode/issues
- Discord: https://discord.gg/necrocode
- Email: support@necrocode.dev

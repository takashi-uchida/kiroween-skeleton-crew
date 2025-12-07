# Review & PR Service

Review & PR Serviceは、プルリクエストの作成、管理、ライフサイクル処理を自動化するNecroCodeシステムのコンポーネントです。複数のGitホスティングプラットフォーム（GitHub、GitLab、Bitbucket）と統合し、包括的なPR自動化機能を提供します。

## 目次

- [機能](#機能)
- [インストール](#インストール)
- [クイックスタート](#クイックスタート)
- [アーキテクチャ](#アーキテクチャ)
- [コンポーネント](#コンポーネント)
- [設定](#設定)
- [APIリファレンス](#APIリファレンス)
- [使用例](#使用例)
- [Webhook統合](#Webhook統合)
- [テスト](#テスト)
- [開発ステータス](#開発ステータス)

## インストール

### 要件

- Python 3.11+
- Git
- GitHub、GitLab、またはBitbucket APIへのアクセス

### 依存関係のインストール

```bash
pip install PyGithub python-gitlab atlassian-python-api jinja2 PyYAML aiohttp
```

または、requirementsファイルからインストール：

```bash
pip install -r requirements.txt
```

### 環境設定

Gitホストの認証情報を設定：

```bash
# For GitHub
export GITHUB_TOKEN="ghp_xxxxx"

# For GitLab
export GITLAB_TOKEN="glpat-xxxxx"

# For Bitbucket
export BITBUCKET_TOKEN="xxxxx"
```

## クイックスタート

### 基本的な使用方法

```python
from necrocode.review_pr_service import PRService, PRServiceConfig, GitHostType
from necrocode.task_registry.models import Task, TaskState
from datetime import datetime

# サービスを設定
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="your-github-token"
)

# サービスを初期化
pr_service = PRService(config)

# タスクを作成
task = Task(
    id="1.1",
    title="Implement user authentication",
    description="Add JWT-based authentication",
    state=TaskState.DONE,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# PRを作成
pr = pr_service.create_pr(
    task=task,
    branch_name="feature/task-1.1-auth",
    acceptance_criteria=[
        "User can login with email and password",
        "JWT token is returned on successful login"
    ]
)

print(f"Created PR #{pr.pr_number}: {pr.url}")
```

## 機能

- **自動PR作成**: Agent Runnerアーティファクトから生成された説明でPRを作成
- **Multi-Platform Support**: Works with GitHub, GitLab, and Bitbucket
- **Template Engine**: Generates PR descriptions using customizable Jinja2 templates
- **CI Integration**: Monitors CI status and updates Task Registry accordingly
- **Label Management**: Automatically applies labels based on task type and priority
- **Reviewer Assignment**: Supports multiple strategies (round-robin, load-balanced, CODEOWNERS)
- **Merge Automation**: Configurable merge strategies with auto-merge support
- **Webhook Handling**: Receives and processes Git host webhooks
- **Draft PR Support**: Creates PRs as drafts and converts them when ready
- **Conflict Detection**: Automatically detects, notifies, and tracks merge conflicts
- **Periodic Conflict Checking**: Monitors open PRs for conflicts that arise from target branch updates
- **Metrics Collection**: Tracks PR metrics for analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Review & PR Service                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  PRService       │      │  PRTemplateEngine│           │
│  │  (Main API)      │◄────►│  (Template)      │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  GitHostClient   │      │  CIStatusMonitor │           │
│  │  (Abstract)      │      │  (CI Polling)    │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  GitHubClient    │      │  WebhookHandler  │           │
│  │  GitLabClient    │      │  (Webhook)       │           │
│  │  BitbucketClient │      └──────────────────┘           │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### PRTemplateEngine

The `PRTemplateEngine` generates PR descriptions and comments using Jinja2 templates. It supports:

- **Template Loading**: Load templates from files or use the default inline template
- **PR Description Generation**: Generate comprehensive PR descriptions with task info, test results, and artifacts
- **Test Results Formatting**: Format test statistics with pass rates and durations
- **Artifact Links**: Generate organized links to diffs, logs, and test results
- **Execution Logs**: Format execution logs with timing and error information
- **Custom Sections**: Add custom sections to PR descriptions
- **Comment Generation**: Generate PR comments using templates
- **Template Validation**: Validate template syntax before use

**Example Usage:**

```python
from necrocode.review_pr_service import PRServiceConfig, PRTemplateEngine
from necrocode.task_registry.models import Task, TaskState

# Create configuration
config = PRServiceConfig(
    repository="owner/repo",
    template=TemplateConfig(
        template_path="templates/pr-template.md",
        include_test_results=True,
        include_artifact_links=True
    )
)

# Initialize engine
engine = PRTemplateEngine(config)

# Generate PR description
task = Task(
    id="2.1",
    title="Implement Authentication",
    description="Add JWT authentication endpoints",
    state=TaskState.DONE
)

description = engine.generate(
    task=task,
    acceptance_criteria=[
        "POST /api/auth/login returns JWT token",
        "Middleware validates JWT on protected routes"
    ]
)

# Add custom sections
engine.set_custom_section("Breaking Changes", "None")

# Generate comment
comment = engine.generate_comment(
    message="Test failure detected",
    details={"Failed Test": "test_login", "Error": "AssertionError"}
)
```

See `examples/pr_template_engine_example.py` for more examples.

### CIStatusMonitor

The `CIStatusMonitor` monitors CI/CD pipeline status for pull requests. It supports both synchronous status checks and background polling with callbacks.

**Features:**
- **Synchronous Status Check**: Get current CI status on-demand
- **Background Monitoring**: Poll CI status at configured intervals
- **Status Change Detection**: Detect and record CI status changes
- **Task Registry Integration**: Record CI events (success, failure, status changes)
- **Callback Support**: Trigger custom actions on CI events
- **Multiple PR Monitoring**: Monitor multiple PRs simultaneously
- **Timeout Handling**: Stop monitoring after configured timeout
- **Thread Management**: Clean thread lifecycle management

**Example Usage:**

```python
from necrocode.review_pr_service import PRService, PRServiceConfig, CIStatusMonitor

# Configure service
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="your-token"
)

# Customize CI monitoring settings
config.ci.enabled = True
config.ci.polling_interval = 60  # Poll every 60 seconds
config.ci.timeout = 3600  # 1 hour timeout

# Initialize service
pr_service = PRService(config)

# Create CI monitor
ci_monitor = CIStatusMonitor(
    git_host_client=pr_service.git_host_client,
    config=config,
    task_registry=pr_service.task_registry
)

# Synchronous status check
ci_status = ci_monitor.monitor_ci_status(pr)
print(f"Current CI status: {ci_status.value}")

# Background monitoring with callbacks
def on_success(pr, status):
    print(f"✅ CI succeeded for PR #{pr.pr_number}")
    # Auto-merge or other actions

def on_failure(pr, status):
    print(f"❌ CI failed for PR #{pr.pr_number}")
    # Post comment or notify team

ci_monitor.start_monitoring(
    pr=pr,
    on_success=on_success,
    on_failure=on_failure
)

# Check monitoring status
status = ci_monitor.get_monitoring_status(pr.pr_id)
print(f"Monitoring: {status}")

# Stop monitoring when done
ci_monitor.stop_monitoring(pr.pr_id)
```

**CI Events Recorded to Task Registry:**
- `TASK_UPDATED`: CI status changed (pending → running → success/failure)
- `TASK_COMPLETED`: CI succeeded
- `TASK_FAILED`: CI failed
- `TASK_UPDATED`: CI monitoring timeout

See `examples/ci_status_monitor_example.py` for more examples.

## Data Models

### PullRequest

Core data model representing a pull request with all metadata:

```python
from necrocode.review_pr_service import PullRequest, PRState, CIStatus
from datetime import datetime

pr = PullRequest(
    pr_id="123",
    pr_number=42,
    title="Task 1.1: Implement authentication",
    description="Implements JWT authentication...",
    source_branch="feature/task-1-1-auth",
    target_branch="main",
    url="https://github.com/org/repo/pull/42",
    state=PRState.OPEN,
    draft=False,
    created_at=datetime.now(),
    ci_status=CIStatus.PENDING
)
```

### PRState

Enumeration of PR states:
- `OPEN`: PR is open and ready for review
- `MERGED`: PR has been merged
- `CLOSED`: PR was closed without merging
- `DRAFT`: PR is in draft state

### CIStatus

Enumeration of CI statuses:
- `PENDING`: CI has not started yet
- `RUNNING`: CI is currently running
- `SUCCESS`: CI passed successfully
- `FAILURE`: CI failed
- `CANCELLED`: CI was cancelled
- `SKIPPED`: CI was skipped

## Configuration

### Basic Configuration

```python
from necrocode.review_pr_service import PRServiceConfig
from necrocode.review_pr_service.config import GitHostType

config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="org/repo",
    api_token="ghp_xxxxx"
)
```

### YAML Configuration

```yaml
pr_service:
  git_host_type: github
  repository: org/repo
  
  labels:
    enabled: true
    rules:
      backend: [backend, api]
      frontend: [frontend, ui]
  
  reviewers:
    enabled: true
    strategy: round-robin
    default_reviewers:
      - reviewer1
      - reviewer2
  
  merge:
    strategy: squash
    auto_merge_enabled: false
    delete_branch_after_merge: true
    required_approvals: 1
  
  draft:
    enabled: true
    create_as_draft: true
    convert_on_ci_success: true
  
  conflict_detection:
    enabled: true
    check_on_creation: true
    auto_comment: true
    periodic_check: true
    check_interval: 3600  # seconds
    recheck_on_push: true
```

Load from file:

```python
config = PRServiceConfig.from_yaml("config/pr-service.yaml")
```

## API Reference

### PRService Class

Main service class for PR automation.

#### `__init__(config: PRServiceConfig)`

Initialize the PR Service.

**Parameters:**
- `config` (PRServiceConfig): Service configuration

**Raises:**
- `PRServiceError`: If initialization fails

**Example:**
```python
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="token"
)
service = PRService(config)
```

#### `create_pr(task, branch_name, base_branch="main", acceptance_criteria=None, custom_data=None) -> PullRequest`

Create a pull request for a task.

**Parameters:**
- `task` (Task): Task object with task information
- `branch_name` (str): Source branch name
- `base_branch` (str, optional): Target branch (default: "main")
- `acceptance_criteria` (List[str], optional): Acceptance criteria list
- `custom_data` (Dict[str, Any], optional): Additional template data

**Returns:**
- `PullRequest`: Created PR object

**Raises:**
- `PRCreationError`: If PR creation fails
- `AuthenticationError`: If authentication fails
- `NetworkError`: If network request fails

**Example:**
```python
pr = service.create_pr(
    task=task,
    branch_name="feature/my-feature",
    base_branch="develop",
    acceptance_criteria=["Criterion 1", "Criterion 2"]
)
```

#### `update_pr_description(pr_id, updates) -> None`

Update PR description with additional information.

**Parameters:**
- `pr_id` (str): Pull request identifier
- `updates` (Dict[str, Any]): Updates to add
  - `execution_logs`: Execution logs (str or List[Dict])
  - `test_results`: Test results (str or Dict)
  - `execution_time`: Execution time in seconds (float)
  - Custom keys: Any additional data

**Raises:**
- `PRServiceError`: If update fails

**Example:**
```python
service.update_pr_description(
    pr_id="123",
    updates={
        "execution_time": 45.2,
        "test_results": {"total": 10, "passed": 10}
    }
)
```

#### `post_comment(pr_id, message, details=None, use_template=True) -> None`

Post a comment to a pull request.

**Parameters:**
- `pr_id` (str): Pull request identifier
- `message` (str): Comment message
- `details` (Dict[str, Any], optional): Additional details
- `use_template` (bool): Use comment template (default: True)

**Example:**
```python
service.post_comment(
    pr_id="123",
    message="Please review security changes",
    details={"Priority": "High"}
)
```

#### `post_test_failure_comment(pr_id, test_results, error_log_url=None, artifact_links=None) -> None`

Post automatic comment when tests fail.

**Parameters:**
- `pr_id` (str): Pull request identifier
- `test_results` (Dict[str, Any]): Test results with keys:
  - `total` (int): Total tests
  - `passed` (int): Passed tests
  - `failed` (int): Failed tests
  - `skipped` (int): Skipped tests
  - `duration` (float, optional): Test duration
  - `failed_tests` (List[Dict], optional): Failed test details
- `error_log_url` (str, optional): URL to error logs
- `artifact_links` (Dict[str, str], optional): Artifact name to URL mapping

**Example:**
```python
service.post_test_failure_comment(
    pr_id="123",
    test_results={
        "total": 50,
        "passed": 45,
        "failed": 5,
        "failed_tests": [
            {"name": "test_auth", "error": "AssertionError"}
        ]
    },
    error_log_url="https://ci.example.com/logs/456"
)
```

#### `handle_pr_merged(pr_id) -> None`

Handle PR merge event.

**Parameters:**
- `pr_id` (str): Pull request identifier

**Actions:**
- Records PR merge event in Task Registry
- Returns repo pool slot (if configured)
- Deletes branch (if configured)
- Unblocks dependent tasks

**Example:**
```python
service.handle_pr_merged("123")
```

#### `check_merge_conflicts(pr_id) -> Dict[str, Any]`

Check for merge conflicts in a PR.

**Parameters:**
- `pr_id` (str): Pull request identifier

**Returns:**
- Dict with keys:
  - `has_conflicts` (bool): Whether conflicts exist
  - `details` (str): Conflict details
  - `conflicting_files` (List[str]): List of conflicting files

**Example:**
```python
result = service.check_merge_conflicts("123")
if result['has_conflicts']:
    print(f"Conflicts in: {result['conflicting_files']}")
```

#### `post_conflict_comment(pr_id, conflict_details) -> None`

Post comment about merge conflicts.

**Parameters:**
- `pr_id` (str): Pull request identifier
- `conflict_details` (str): Conflict details

**Example:**
```python
service.post_conflict_comment(
    pr_id="123",
    conflict_details="Conflicts in src/auth.py"
)
```

#### `recheck_conflicts_after_resolution(pr_id, post_success_comment=True) -> bool`

Re-check conflicts after resolution attempt.

**Parameters:**
- `pr_id` (str): Pull request identifier
- `post_success_comment` (bool): Post comment if resolved (default: True)

**Returns:**
- `bool`: True if conflicts resolved, False otherwise

**Example:**
```python
resolved = service.recheck_conflicts_after_resolution("123")
if resolved:
    print("Conflicts resolved!")
```

#### `periodic_conflict_check(pr_ids, only_open_prs=True) -> Dict[str, bool]`

Check multiple PRs for conflicts periodically.

**Parameters:**
- `pr_ids` (List[str]): List of PR identifiers
- `only_open_prs` (bool): Only check open PRs (default: True)

**Returns:**
- Dict mapping PR ID to conflict status (bool)

**Example:**
```python
results = service.periodic_conflict_check(["123", "124", "125"])
for pr_id, has_conflicts in results.items():
    print(f"PR {pr_id}: {'⚠️' if has_conflicts else '✅'}")
```

### PRTemplateEngine Class

Template engine for generating PR descriptions and comments.

#### `generate(task, acceptance_criteria=None, test_results=None, artifacts=None, custom_data=None) -> str`

Generate PR description from template.

**Parameters:**
- `task` (Task): Task object
- `acceptance_criteria` (List[str], optional): Acceptance criteria
- `test_results` (Dict, optional): Test results
- `artifacts` (List[Artifact], optional): Task artifacts
- `custom_data` (Dict, optional): Custom template data

**Returns:**
- `str`: Generated PR description

**Example:**
```python
engine = PRTemplateEngine(config)
description = engine.generate(
    task=task,
    acceptance_criteria=["Criterion 1", "Criterion 2"],
    test_results={"total": 10, "passed": 10}
)
```

#### `generate_comment(message, details=None) -> str`

Generate comment from template.

**Parameters:**
- `message` (str): Main message
- `details` (Dict, optional): Additional details

**Returns:**
- `str`: Generated comment

#### `set_custom_section(name, content) -> None`

Add custom section to PR description.

**Parameters:**
- `name` (str): Section name
- `content` (str): Section content

**Example:**
```python
engine.set_custom_section("Breaking Changes", "None")
```

### CIStatusMonitor Class

Monitor CI/CD pipeline status for pull requests.

#### `monitor_ci_status(pr) -> CIStatus`

Get current CI status for a PR.

**Parameters:**
- `pr` (PullRequest): Pull request object

**Returns:**
- `CIStatus`: Current CI status

**Example:**
```python
monitor = CIStatusMonitor(git_host_client, config, task_registry)
status = monitor.monitor_ci_status(pr)
print(f"CI Status: {status.value}")
```

#### `start_monitoring(pr, on_success=None, on_failure=None, on_status_change=None) -> None`

Start background monitoring of CI status.

**Parameters:**
- `pr` (PullRequest): Pull request to monitor
- `on_success` (Callable, optional): Callback for CI success
- `on_failure` (Callable, optional): Callback for CI failure
- `on_status_change` (Callable, optional): Callback for any status change

**Example:**
```python
def on_success(pr, status):
    print(f"CI passed for PR #{pr.pr_number}")

monitor.start_monitoring(pr, on_success=on_success)
```

#### `stop_monitoring(pr_id) -> None`

Stop monitoring a PR.

**Parameters:**
- `pr_id` (str): Pull request identifier

#### `get_monitoring_status(pr_id) -> Optional[str]`

Get monitoring status for a PR.

**Parameters:**
- `pr_id` (str): Pull request identifier

**Returns:**
- `str` or `None`: "monitoring" if active, None otherwise

### WebhookHandler Class

Handle webhooks from Git hosting platforms.

#### `__init__(config, on_pr_merged=None, on_ci_status_changed=None)`

Initialize webhook handler.

**Parameters:**
- `config` (PRServiceConfig): Service configuration
- `on_pr_merged` (Callable, optional): PR merge event callback
- `on_ci_status_changed` (Callable, optional): CI status change callback

**Example:**
```python
def on_merge(event):
    print(f"PR #{event.pr_number} merged")

handler = WebhookHandler(config, on_pr_merged=on_merge)
```

#### `start() -> None`

Start webhook HTTP server.

**Example:**
```python
handler.start()
print("Webhook server running on port 8080")
```

#### `stop() -> None`

Stop webhook server gracefully.

#### `register_pr_merged_handler(handler) -> None`

Register callback for PR merge events.

**Parameters:**
- `handler` (Callable[[WebhookEvent], None]): Event handler

#### `register_ci_status_handler(handler) -> None`

Register callback for CI status events.

**Parameters:**
- `handler` (Callable[[WebhookEvent], None]): Event handler

### Data Models

#### PullRequest

```python
@dataclass
class PullRequest:
    pr_id: str                      # Unique PR identifier
    pr_number: int                  # PR number in repository
    title: str                      # PR title
    description: str                # PR description
    source_branch: str              # Source branch name
    target_branch: str              # Target branch name
    url: str                        # PR URL
    state: PRState                  # PR state (OPEN/MERGED/CLOSED)
    draft: bool                     # Whether PR is draft
    created_at: datetime            # Creation timestamp
    merged_at: Optional[datetime]   # Merge timestamp
    ci_status: CIStatus            # CI status
    labels: List[str]              # PR labels
    reviewers: List[str]           # Assigned reviewers
```

#### PRState (Enum)

- `OPEN`: PR is open
- `MERGED`: PR is merged
- `CLOSED`: PR is closed
- `DRAFT`: PR is draft

#### CIStatus (Enum)

- `PENDING`: CI pending
- `RUNNING`: CI running
- `SUCCESS`: CI succeeded
- `FAILURE`: CI failed
- `CANCELLED`: CI cancelled
- `SKIPPED`: CI skipped

#### WebhookEvent

```python
@dataclass
class WebhookEvent:
    event_type: WebhookEventType    # Event type
    pr_id: str                      # PR identifier
    pr_number: int                  # PR number
    repository: str                 # Repository name
    timestamp: datetime             # Event timestamp
    payload: Dict[str, Any]         # Full webhook payload
    merged_by: Optional[str]        # User who merged (for merge events)
    ci_status: Optional[CIStatus]   # CI status (for CI events)
```

## Conflict Detection

The service provides comprehensive conflict detection and management:

### Automatic Detection on PR Creation

```python
# Enable conflict detection
config.conflict_detection.enabled = True
config.conflict_detection.check_on_creation = True
config.conflict_detection.auto_comment = True

# Create PR - conflicts checked automatically
pr = service.create_pr(task, branch_name="feature/my-feature")
# If conflicts exist, a comment is automatically posted
```

### Manual Conflict Checking

```python
# Check for conflicts in an existing PR
conflict_result = service.check_merge_conflicts(pr_id="123")

if conflict_result['has_conflicts']:
    print("⚠️ Conflicts detected!")
    print(f"Details: {conflict_result['details']}")
    
    # Post conflict comment
    service.post_conflict_comment(
        pr_id="123",
        conflict_details=conflict_result['details']
    )
```

### Re-checking After Resolution

```python
# After developer resolves conflicts
conflicts_resolved = service.recheck_conflicts_after_resolution(
    pr_id="123",
    post_success_comment=True  # Post success comment if resolved
)

if conflicts_resolved:
    print("✅ Conflicts resolved!")
else:
    print("⚠️ Conflicts still exist")
```

### Periodic Conflict Checking

```python
# Check multiple PRs periodically (e.g., via cron job)
pr_ids = ["123", "124", "125"]
results = service.periodic_conflict_check(
    pr_ids=pr_ids,
    only_open_prs=True
)

for pr_id, has_conflicts in results.items():
    if has_conflicts:
        print(f"PR {pr_id}: ⚠️ Conflicts detected")
    else:
        print(f"PR {pr_id}: ✅ No conflicts")
```

### Configuration Options

```python
# Customize conflict detection behavior
config.conflict_detection.enabled = True              # Master enable/disable
config.conflict_detection.check_on_creation = True    # Check when PR is created
config.conflict_detection.auto_comment = True         # Auto-post conflict comments
config.conflict_detection.periodic_check = True       # Enable periodic checking
config.conflict_detection.check_interval = 1800       # Check every 30 minutes
config.conflict_detection.recheck_on_push = True      # Re-check on code push
```

## Exception Handling

The service provides comprehensive exception handling:

```python
from necrocode.review_pr_service.exceptions import (
    PRServiceError,
    AuthenticationError,
    RateLimitError,
    PRCreationError,
    NetworkError
)

try:
    pr = service.create_pr(task, branch_name)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded, reset at: {e.reset_time}")
except PRCreationError as e:
    print(f"Failed to create PR: {e.message}")
    print(f"Details: {e.details}")
```

## Integration with NecroCode

The Review & PR Service integrates with other NecroCode components:

- **Agent Runner**: Receives completion notifications and artifact references
- **Artifact Store**: Downloads diffs, logs, and test results
- **Task Registry**: Records PR events and updates task states
- **Repo Pool Manager**: Returns workspace slots after PR merge

## Environment Variables

The service uses the following environment variables:

- `GITHUB_TOKEN` / `GITLAB_TOKEN` / `BITBUCKET_TOKEN`: API authentication token
- `GITHUB_URL` / `GITLAB_URL` / `BITBUCKET_URL`: Git host URL (for self-hosted)
- `REPOSITORY`: Repository in format "org/repo"
- `ARTIFACT_STORE_URL`: URL of the Artifact Store service
- `TASK_REGISTRY_PATH`: Path to Task Registry data
- `WEBHOOK_SECRET`: Secret for webhook signature verification

## Development Status

This is the initial implementation of the Review & PR Service. The following components have been implemented:

- ✅ Data models (PullRequest, PRState, CIStatus)
- ✅ Exception classes
- ✅ Configuration management
- ⏳ Git host clients (GitHub, GitLab, Bitbucket)
- ⏳ PR template engine
- ⏳ CI status monitor
- ⏳ Webhook handler
- ⏳ Main PR service implementation

## Requirements

- Python 3.11+
- PyGithub (for GitHub support)
- python-gitlab (for GitLab support)
- atlassian-python-api (for Bitbucket support)
- Jinja2 (for template engine)
- PyYAML (for configuration)

## See Also

- [Requirements Document](.kiro/specs/review-pr-service/requirements.md)
- [Design Document](.kiro/specs/review-pr-service/design.md)
- [Implementation Tasks](.kiro/specs/review-pr-service/tasks.md)


## Task 4 Implementation: PRService Main Class

Task 4 "PRServiceメインクラスの実装" has been completed with all subtasks:

### 4.1 初期化とコンポーネント統合 ✅

The `PRService` class has been implemented with comprehensive component initialization:

```python
from necrocode.review_pr_service import PRService, PRServiceConfig, GitHostType

# Configure the service
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="your-github-token",
    task_registry_path="~/.necrocode/task_registry",
    artifact_store_url="file:///tmp/artifacts"
)

# Initialize PRService
pr_service = PRService(config)
```

**Initialized Components:**
- `GitHostClient`: Automatically created based on `git_host_type` (GitHub/GitLab/Bitbucket)
- `PRTemplateEngine`: Template engine for generating PR descriptions
- `TaskRegistry`: Optional integration for recording PR events
- `ArtifactStore`: Optional integration for downloading task artifacts

### 4.2 PR作成機能 ✅

The `create_pr()` method provides comprehensive PR creation functionality:

```python
from necrocode.task_registry.models import Task, TaskState
from datetime import datetime

# Create a task
task = Task(
    id="1.1",
    title="Implement user authentication",
    description="Add JWT-based authentication to the API",
    state=TaskState.DONE,
    dependencies=[],
    created_at=datetime.now(),
    updated_at=datetime.now(),
    metadata={
        "type": "backend",
        "priority": "high",
        "reviewers": ["reviewer1", "reviewer2"],
    }
)

# Create PR
pr = pr_service.create_pr(
    task=task,
    branch_name="feature/task-1.1-user-auth",
    base_branch="main",
    acceptance_criteria=[
        "User can register with email and password",
        "User can login and receive JWT token",
        "Protected endpoints validate JWT token",
        "Passwords are hashed with bcrypt",
    ]
)

print(f"Created PR #{pr.pr_number}: {pr.url}")
```

**PR Creation Flow:**
1. Downloads artifacts from Artifact Store
2. Generates PR description using PRTemplateEngine
3. Creates PR using GitHostClient
4. Applies labels based on task metadata
5. Assigns reviewers based on configuration
6. Records PR creation event in Task Registry

### 4.3 Task Registryへの記録 ✅

The `_record_pr_created()` method records PR creation events in the Task Registry:

```python
# Automatically called during create_pr()
# Records event with details:
{
    "event": "pr_created",
    "pr_url": "https://github.com/owner/repo/pull/42",
    "pr_number": 42,
    "pr_id": "12345",
    "source_branch": "feature/task-1.1-user-auth",
    "target_branch": "main",
    "draft": false
}
```

**Features:**
- Records full PR details for traceability
- Handles cases where Task Registry is not configured
- Logs errors without failing PR creation

### 4.4 PR説明文の更新 ✅

The `update_pr_description()` method updates PR descriptions with execution results:

```python
# Update PR with execution results
pr_service.update_pr_description(
    pr_id=pr.pr_id,
    updates={
        "execution_time": 45.2,
        "test_results": {
            "total": 25,
            "passed": 24,
            "failed": 1,
            "skipped": 0,
            "duration": 12.5,
        },
        "execution_logs": [
            {
                "name": "Build Log",
                "url": "https://example.com/logs/build.log"
            },
            {
                "name": "Test Log",
                "url": "https://example.com/logs/test.log"
            },
        ],
    }
)
```

**Update Sections:**
- Execution logs with links
- Test results with formatted summaries
- Execution time
- Custom sections
- Timestamp of update

## PRService API Reference

### Constructor

```python
PRService(config: PRServiceConfig)
```

Initializes the PR Service with the given configuration.

**Parameters:**
- `config`: PRServiceConfig instance with Git host, repository, and feature settings

**Raises:**
- `PRServiceError`: If Git host client creation fails

### create_pr()

```python
create_pr(
    task: Task,
    branch_name: str,
    base_branch: str = "main",
    acceptance_criteria: Optional[List[str]] = None,
    custom_data: Optional[Dict[str, Any]] = None
) -> PullRequest
```

Creates a pull request for a task.

**Parameters:**
- `task`: Task object containing task information
- `branch_name`: Source branch name
- `base_branch`: Target branch name (default: "main")
- `acceptance_criteria`: List of acceptance criteria (optional)
- `custom_data`: Additional custom data for template (optional)

**Returns:**
- `PullRequest`: Created PR object with details

**Raises:**
- `PRCreationError`: If PR creation fails

**Requirements:** 1.1, 1.2, 1.3, 1.4

### update_pr_description()

```python
update_pr_description(
    pr_id: str,
    updates: Dict[str, Any]
) -> None
```

Updates PR description with additional information.

**Parameters:**
- `pr_id`: Pull request identifier
- `updates`: Dictionary containing updates to add
  - `execution_logs`: Execution logs (string or list of dicts)
  - `test_results`: Test results (string or dict with stats)
  - `execution_time`: Execution time in seconds (float)
  - Custom keys: Any other key-value pairs

**Raises:**
- `PRUpdateError`: If PR update fails

**Requirements:** 10.1, 10.2, 10.3, 10.4, 10.5

## Examples

### Complete Example

```python
from necrocode.review_pr_service import PRService, PRServiceConfig, GitHostType
from necrocode.task_registry.models import Task, TaskState, Artifact, ArtifactType
from datetime import datetime

# Configure PR Service
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="ghp_xxxxx",
    task_registry_path="~/.necrocode/task_registry",
)

# Enable features
config.labels.enabled = True
config.reviewers.enabled = True
config.draft.enabled = True
config.draft.create_as_draft = True

# Initialize service
pr_service = PRService(config)

# Create task with artifacts
task = Task(
    id="2.1",
    title="Implement login endpoint",
    description="Add POST /api/auth/login endpoint",
    state=TaskState.DONE,
    dependencies=["1.1"],
    created_at=datetime.now(),
    updated_at=datetime.now(),
    metadata={
        "type": "backend",
        "priority": "high",
        "reviewers": ["backend-team"],
    }
)

task.artifacts = [
    Artifact(
        type=ArtifactType.DIFF,
        uri="https://artifacts.example.com/task-2.1/diff.txt",
        size_bytes=2048,
        created_at=datetime.now(),
    ),
    Artifact(
        type=ArtifactType.TEST_RESULT,
        uri="https://artifacts.example.com/task-2.1/tests.json",
        size_bytes=4096,
        created_at=datetime.now(),
        metadata={
            "total_tests": 15,
            "passed": 15,
            "failed": 0,
            "duration": 8.2,
        }
    ),
]

# Create PR
pr = pr_service.create_pr(
    task=task,
    branch_name="feature/task-2.1-login-endpoint",
    base_branch="develop",
    acceptance_criteria=[
        "POST /api/auth/login accepts email and password",
        "Returns JWT token on successful authentication",
        "Returns 401 on invalid credentials",
        "All tests pass",
    ]
)

print(f"✅ Created PR #{pr.pr_number}")
print(f"   URL: {pr.url}")
print(f"   Draft: {pr.draft}")
print(f"   Labels: {pr.labels}")
print(f"   Reviewers: {pr.reviewers}")

# Later, update with execution results
pr_service.update_pr_description(
    pr_id=pr.pr_id,
    updates={
        "execution_time": 32.5,
        "test_results": {
            "total": 15,
            "passed": 15,
            "failed": 0,
            "duration": 8.2,
        }
    }
)

print(f"✅ Updated PR description")
```

See `examples/pr_service_example.py` for more examples.

## Testing

Comprehensive tests have been implemented in `tests/test_pr_service.py`:

```bash
pytest tests/test_pr_service.py -v
```

**Test Coverage:**
- PRService initialization with different Git hosts
- PR creation with various configurations
- Label management based on task metadata
- Reviewer assignment strategies
- PR description updates
- Task Registry integration
- Error handling

## Task 9 Implementation: Review Comment Automation

Task 9 "レビューコメントの実装" has been completed with all subtasks:

### 9.1 自動コメント投稿 ✅

The `post_comment()` and `post_test_failure_comment()` methods provide automatic comment posting:

```python
# Post a simple comment
pr_service.post_comment(
    pr_id="123",
    message="This PR requires manual review",
    details={
        "Reason": "Security changes detected",
        "Reviewer": "security-team@example.com"
    }
)

# Post test failure comment automatically
test_results = {
    "total": 50,
    "passed": 45,
    "failed": 5,
    "skipped": 0,
    "duration": 123.45,
    "failed_tests": [
        {
            "name": "test_authentication",
            "error": "AssertionError: Expected 200, got 401"
        }
    ]
}

pr_service.post_test_failure_comment(
    pr_id="123",
    test_results=test_results,
    error_log_url="https://ci.example.com/logs/456",
    artifact_links={
        "Test Report": "https://artifacts.example.com/report.html",
        "Coverage": "https://artifacts.example.com/coverage.html"
    }
)
```

**Features:**
- Automatic comment posting on test failures
- Template-based or plain text formatting
- Detailed test failure information
- Error log links
- Artifact links
- Next steps guidance

### 9.2 コメント内容 ✅

Test failure comments include comprehensive details:

**Test Results Summary:**
- Total, passed, failed, and skipped test counts
- Test duration
- Pass rate visualization (✅/❌)

**Failed Test Details:**
- Test names
- Error messages
- Stack traces (when available)
- Limited to first 10 tests to prevent overly long comments

**Error Logs:**
- Direct links to full error logs
- Links to CI build pages

**Artifact Links:**
- Test reports
- Coverage reports
- Screenshots
- Any other relevant artifacts

### 9.3 コメントテンプレート ✅

Comment templates can be customized using Jinja2:

```python
# Configure custom comment template
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="your-token"
)

# Set custom template path
config.template.comment_template_path = "templates/custom-comment.md"

# Disable auto-comments if needed
config.ci.auto_comment_on_failure = False

# Initialize service
pr_service = PRService(config)
```

**Template Example** (`templates/comment-template.md`):
```markdown
{{message}}

{% if details %}
### Details
{% for key, value in details.items() %}
- **{{key}}:** {{value}}
{% endfor %}
{% endif %}

---
*Posted by NecroCode Review & PR Service*
```

**Configuration Options:**
- `ci.auto_comment_on_failure`: Enable/disable automatic comments (default: `True`)
- `template.comment_template_path`: Path to custom comment template
- Template fallback to plain text if template not found

## Review Comment API Reference

### post_comment()

```python
post_comment(
    pr_id: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    use_template: bool = True
) -> None
```

Posts a comment to a pull request.

**Parameters:**
- `pr_id`: Pull request identifier
- `message`: Main comment message
- `details`: Optional dictionary of additional details
- `use_template`: Whether to use comment template (default: True)

**Raises:**
- `PRServiceError`: If comment posting fails

**Requirements:** 6.1

### post_test_failure_comment()

```python
post_test_failure_comment(
    pr_id: str,
    test_results: Dict[str, Any],
    error_log_url: Optional[str] = None,
    artifact_links: Optional[Dict[str, str]] = None
) -> None
```

Posts an automatic comment when tests fail.

**Parameters:**
- `pr_id`: Pull request identifier
- `test_results`: Dictionary containing test results
  - `total`: Total number of tests
  - `passed`: Number of passed tests
  - `failed`: Number of failed tests
  - `skipped`: Number of skipped tests
  - `duration`: Test execution duration (optional)
  - `failed_tests`: List of failed test details (optional)
- `error_log_url`: Optional URL to error logs
- `artifact_links`: Optional dictionary of artifact names to URLs

**Requirements:** 6.1, 6.2, 6.3

**Example:**
```python
pr_service.post_test_failure_comment(
    pr_id="123",
    test_results={
        "total": 100,
        "passed": 95,
        "failed": 5,
        "skipped": 0,
        "duration": 456.78,
        "failed_tests": [
            {
                "name": "test_critical_feature",
                "error": "AssertionError: Feature broken"
            }
        ]
    },
    error_log_url="https://ci.example.com/logs/789",
    artifact_links={
        "Test Report": "https://artifacts.example.com/report.html",
        "Coverage Report": "https://artifacts.example.com/coverage.html"
    }
)
```

See `examples/review_comment_example.py` for more examples.

## Development Status Update

- ✅ Data models (PullRequest, PRState, CIStatus)
- ✅ Exception classes
- ✅ Configuration management
- ✅ Git host clients (GitHub, GitLab, Bitbucket)
- ✅ PR template engine
- ✅ **PRService main class (Task 4)**
- ✅ **Label management (Task 5)**
- ✅ **Reviewer assignment (Task 6)**
- ✅ **CI status monitor (Task 7)**
- ✅ **PR event handling (Task 8)**
- ✅ **Review comment automation (Task 9)**
- ⏳ Merge strategy (Task 10)
- ⏳ Webhook handler (Task 11)
- ⏳ Draft PR functionality (Task 12)
- ⏳ Conflict detection (Task 13)
- ⏳ Metrics collection (Task 14)
- ⏳ Error handling and retry (Task 15)

## Next Steps

The following tasks are planned for future implementation:

- **Task 10**: Merge strategy - Auto-merge, conflict detection, merge methods
- **Task 11**: Webhook handler - Receive and process Git host webhooks
- **Task 12**: Draft PR functionality - Auto-convert drafts on CI success
- **Task 13**: Conflict detection - Detect and report merge conflicts
- **Task 14**: Metrics collection - Track PR metrics for analysis
- **Task 15**: Error handling - Retry logic and rate limit handling
- **Task 16**: Unit tests - Comprehensive test coverage
- **Task 17**: Integration tests - End-to-end testing
- **Task 18**: Documentation - API docs and usage examples


## Task 11 Implementation: Webhook Handler

Task 11 "WebhookHandlerの実装" has been completed with all subtasks:

### 11.1 Webhookエンドポイント ✅

The `WebhookHandler` class provides an HTTP server for receiving webhooks from Git hosts:

```python
from necrocode.review_pr_service import PRServiceConfig, GitHostType
from necrocode.review_pr_service.webhook_handler import WebhookHandler
from necrocode.review_pr_service.config import WebhookConfig

# Configure webhook
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="your-token",
    webhook=WebhookConfig(
        enabled=True,
        port=8080,
        secret="your-webhook-secret",
        verify_signature=True,
        async_processing=True
    )
)

# Create webhook handler
webhook_handler = WebhookHandler(config)

# Start webhook server
webhook_handler.start()

# Server is now listening on http://0.0.0.0:8080/webhook
```

**Features:**
- HTTP server using aiohttp
- Health check endpoint at `/health`
- Webhook endpoint at `/webhook`
- Runs in separate thread for non-blocking operation
- Graceful shutdown support

### 11.2 Webhook署名の検証 ✅

Webhook signatures are verified for all supported Git hosts:

**GitHub (HMAC SHA256):**
```python
# GitHub sends signature in X-Hub-Signature-256 header
# Format: "sha256=<signature>"
# Verified using HMAC SHA256 with webhook secret
```

**GitLab (Token):**
```python
# GitLab sends token in X-Gitlab-Token header
# Verified by comparing with configured secret
```

**Bitbucket (HMAC SHA256):**
```python
# Bitbucket sends signature in X-Hub-Signature header
# Format: "sha256=<signature>"
# Verified using HMAC SHA256 with webhook secret
```

**Configuration:**
```python
# Enable signature verification (recommended for production)
config.webhook.verify_signature = True
config.webhook.secret = "your-webhook-secret"

# Disable for development only
config.webhook.verify_signature = False
config.webhook.secret = None
```

### 11.3 PRマージイベントの受信 ✅

The webhook handler processes PR merge events from all Git hosts:

```python
def handle_pr_merged(event: WebhookEvent):
    """Callback for PR merge events"""
    print(f"PR #{event.pr_number} was merged!")
    print(f"Repository: {event.repository}")
    print(f"Merged by: {event.merged_by}")
    print(f"Timestamp: {event.timestamp}")
    
    # Clean up resources
    # - Return repo pool slot
    # - Update task registry
    # - Delete branch if configured

# Register handler
webhook_handler = WebhookHandler(
    config=config,
    on_pr_merged=handle_pr_merged
)
```

**Event Data:**
- `event_type`: `WebhookEventType.PR_MERGED`
- `pr_id`: Pull request identifier
- `pr_number`: Pull request number
- `repository`: Repository name
- `merged_by`: Username who merged the PR
- `timestamp`: Event timestamp
- `payload`: Full webhook payload

### 11.4 CI状態変更イベントの受信 ✅

The webhook handler processes CI status change events:

```python
def handle_ci_status_changed(event: WebhookEvent):
    """Callback for CI status change events"""
    print(f"CI status changed: {event.ci_status}")
    print(f"PR #{event.pr_number}")
    
    if event.ci_status == CIStatus.SUCCESS:
        print("CI passed! Ready for review.")
    elif event.ci_status == CIStatus.FAILURE:
        print("CI failed! Adding comment...")

# Register handler
webhook_handler = WebhookHandler(
    config=config,
    on_ci_status_changed=handle_ci_status_changed
)
```

**Supported CI Events:**
- **GitHub**: `status` and `check_suite` events
- **GitLab**: `Pipeline Hook` events
- **Bitbucket**: Build status events

**CI Status Mapping:**
- `PENDING`: CI queued or running
- `SUCCESS`: CI passed
- `FAILURE`: CI failed or errored

### 11.5 非同期処理 ✅

Webhook events are processed asynchronously to avoid blocking:

```python
# Webhook handler returns 202 Accepted immediately
# Event processing happens in background

async def _process_event(self, event: WebhookEvent) -> None:
    """Process webhook event asynchronously"""
    # Callbacks run in thread pool executor
    # Non-blocking for webhook server
    # Errors are logged but don't affect webhook response
```

**Benefits:**
- Fast webhook response (< 100ms)
- No timeout issues with Git hosts
- Parallel event processing
- Error isolation

## Webhook Handler API Reference

### Constructor

```python
WebhookHandler(
    config: PRServiceConfig,
    on_pr_merged: Optional[Callable[[WebhookEvent], None]] = None,
    on_ci_status_changed: Optional[Callable[[WebhookEvent], None]] = None
)
```

Initializes the webhook handler.

**Parameters:**
- `config`: PRServiceConfig with webhook settings
- `on_pr_merged`: Optional callback for PR merge events
- `on_ci_status_changed`: Optional callback for CI status events

### start()

```python
start() -> None
```

Starts the webhook HTTP server in a background thread.

**Requirements:** 11.1

### stop()

```python
stop() -> None
```

Stops the webhook HTTP server gracefully.

### register_pr_merged_handler()

```python
register_pr_merged_handler(handler: Callable[[WebhookEvent], None]) -> None
```

Registers a callback for PR merge events.

**Parameters:**
- `handler`: Callback function that receives WebhookEvent

### register_ci_status_handler()

```python
register_ci_status_handler(handler: Callable[[WebhookEvent], None]) -> None
```

Registers a callback for CI status change events.

**Parameters:**
- `handler`: Callback function that receives WebhookEvent

## Webhook Configuration Guide

### GitHub Webhook Setup

1. Go to repository Settings → Webhooks → Add webhook
2. Configure:
   - **Payload URL**: `http://your-server:8080/webhook`
   - **Content type**: `application/json`
   - **Secret**: Your webhook secret
   - **Events**: Select "Pull requests" and "Check suites"
3. Save webhook

### GitLab Webhook Setup

1. Go to project Settings → Webhooks
2. Configure:
   - **URL**: `http://your-server:8080/webhook`
   - **Secret Token**: Your webhook secret
   - **Trigger**: Select "Merge request events" and "Pipeline events"
3. Add webhook

### Bitbucket Webhook Setup

1. Go to repository Settings → Webhooks → Add webhook
2. Configure:
   - **Title**: NecroCode Webhook
   - **URL**: `http://your-server:8080/webhook`
   - **Secret**: Your webhook secret
   - **Triggers**: Select "Pull Request Merged" and "Build Status Updated"
3. Save webhook

## Webhook Integration Example

Complete example integrating webhook with PR service:

```python
from necrocode.review_pr_service import PRService, PRServiceConfig, GitHostType
from necrocode.review_pr_service.webhook_handler import WebhookHandler, WebhookEvent
from necrocode.review_pr_service.config import WebhookConfig
import time

# Configure service
config = PRServiceConfig(
    git_host_type=GitHostType.GITHUB,
    repository="owner/repo",
    api_token="ghp_xxxxx",
    webhook=WebhookConfig(
        enabled=True,
        port=8080,
        secret="webhook-secret-123"
    )
)

# Create PR service
pr_service = PRService(config)

# Define webhook handlers
def on_pr_merged(event: WebhookEvent):
    """Handle PR merge"""
    print(f"Processing merge for PR #{event.pr_number}")
    
    # Use PR service to handle post-merge tasks
    pr_service.handle_pr_merged(str(event.pr_number))
    
    print(f"✅ Cleaned up resources for PR #{event.pr_number}")

def on_ci_status(event: WebhookEvent):
    """Handle CI status change"""
    print(f"CI status changed to {event.ci_status.value}")
    
    if event.ci_status.value == "failure":
        # Post comment about failure
        pr_service.post_comment(
            pr_id=str(event.pr_number),
            message="⚠️ CI checks failed. Please review the errors.",
            details={
                "Status": event.ci_status.value,
                "Timestamp": event.timestamp.isoformat()
            }
        )

# Create and start webhook handler
webhook_handler = WebhookHandler(
    config=config,
    on_pr_merged=on_pr_merged,
    on_ci_status_changed=on_ci_status
)

webhook_handler.start()

print("🚀 Webhook server running on port 8080")
print("Configure your Git host webhook to point to:")
print("  http://your-server:8080/webhook")

try:
    # Keep server running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Shutting down webhook server...")
    webhook_handler.stop()
    print("✅ Server stopped")
```

See `examples/webhook_handler_example.py` for more examples.

## Webhook Security Best Practices

1. **Always use signature verification in production:**
   ```python
   config.webhook.verify_signature = True
   config.webhook.secret = "strong-random-secret"
   ```

2. **Use HTTPS in production:**
   - Deploy behind reverse proxy (nginx, Apache)
   - Configure SSL/TLS certificates
   - Update webhook URL to `https://`

3. **Restrict webhook source IPs:**
   - Configure firewall rules
   - Allow only Git host IP ranges
   - GitHub IPs: https://api.github.com/meta
   - GitLab IPs: Check your instance settings

4. **Monitor webhook failures:**
   - Log all webhook events
   - Alert on signature verification failures
   - Track processing errors

5. **Use environment variables for secrets:**
   ```python
   import os
   config.webhook.secret = os.getenv("WEBHOOK_SECRET")
   ```

## Testing Webhooks

### Manual Testing with curl

**GitHub PR Merged:**
```bash
# Generate signature
SECRET="your-secret"
PAYLOAD='{"action":"closed","pull_request":{"id":123,"number":42,"merged":true,"merged_by":{"login":"user"}},"repository":{"full_name":"owner/repo"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

# Send webhook
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

**GitHub CI Status:**
```bash
PAYLOAD='{"state":"success","sha":"abc123","repository":{"full_name":"owner/repo"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: status" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

### Automated Testing

Run webhook handler tests:

```bash
pytest tests/test_webhook_handler.py -v
```

**Test Coverage:**
- Webhook endpoint functionality
- Signature verification for all Git hosts
- Event parsing (GitHub, GitLab, Bitbucket)
- PR merge event handling
- CI status event handling
- Async event processing
- Error handling

## Development Status Update

- ✅ Data models (PullRequest, PRState, CIStatus)
- ✅ Exception classes
- ✅ Configuration management
- ✅ Git host clients (GitHub, GitLab, Bitbucket)
- ✅ PR template engine
- ✅ PRService main class (Task 4)
- ✅ Label management (Task 5)
- ✅ Reviewer assignment (Task 6)
- ✅ CI status monitor (Task 7)
- ✅ PR event handling (Task 8)
- ✅ Review comment automation (Task 9)
- ✅ Merge strategy (Task 10)
- ✅ **Webhook handler (Task 11)**
- ⏳ Draft PR functionality (Task 12)
- ⏳ Conflict detection (Task 13)
- ⏳ Metrics collection (Task 14)
- ⏳ Error handling and retry (Task 15)

## Dependencies

The webhook handler requires the following additional dependencies:

```txt
aiohttp>=3.9.0  # Async HTTP server
```

Install with:
```bash
pip install aiohttp
```

Or add to your `requirements.txt`:
```txt
PyGithub>=2.1.0
python-gitlab>=3.15.0
atlassian-python-api>=3.41.0
jinja2>=3.1.0
PyYAML>=6.0
aiohttp>=3.9.0
```

# Review & PR Service Design Document

## Overview

Review & PR Serviceは、Agent Runnerの成果物をもとにPull Requestを自動作成し、テンプレート生成、CI状態の連携、PRイベントの処理を行うコンポーネントです。GitHub、GitLab、Bitbucketなど複数のGitホストをサポートし、Webhook受信、自動マージ、レビュアー割当などの機能を提供します。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent Runner ──────► Review & PR Service ◄────── Git Host │
│                           │                                 │
│                           ▼                                 │
│                    Artifact Store                           │
│                           │                                 │
│                           ▼                                 │
│                    Task Registry                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

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

## Components and Interfaces

See full design for detailed specifications.


## Components and Interfaces (Detailed)

### 1. PRService (Main API)

```python
class PRService:
    """Review & PR Serviceのメインクラス"""
    
    def __init__(self, config: PRServiceConfig):
        self.config = config
        self.git_host_client = self._create_git_host_client(config.git_host_type)
        self.template_engine = PRTemplateEngine(config)
        self.ci_monitor = CIStatusMonitor(self.git_host_client)
        self.webhook_handler = WebhookHandler(config)
    
    def create_pr(
        self,
        task: Task,
        branch_name: str,
        base_branch: str = "main"
    ) -> PullRequest:
        """PRを作成"""
        # 1. 成果物をダウンロード
        artifacts = self._download_artifacts(task)
        
        # 2. PR説明文を生成
        description = self.template_engine.generate(task, artifacts)
        
        # 3. PRを作成
        pr = self.git_host_client.create_pull_request(
            title=f"Task {task.id}: {task.title}",
            description=description,
            source_branch=branch_name,
            target_branch=base_branch,
            draft=self.config.create_as_draft
        )
        
        # 4. ラベルを付ける
        self._apply_labels(pr, task)
        
        # 5. レビュアーを割り当て
        self._assign_reviewers(pr, task)
        
        # 6. Task Registryに記録
        self._record_pr_created(task, pr)
        
        return pr
    
    def update_pr_description(self, pr_id: str, updates: Dict) -> None:
        """PR説明文を更新"""
        pass
    
    def monitor_ci_status(self, pr_id: str) -> CIStatus:
        """CI状態を監視"""
        pass
    
    def handle_pr_merged(self, pr_id: str) -> None:
        """PRマージイベントを処理"""
        pass
```

### 2. GitHostClient (Abstract Interface)

```python
class GitHostClient(ABC):
    """GitホストAPIの抽象インターフェース"""
    
    @abstractmethod
    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False
    ) -> PullRequest:
        """PRを作成"""
        pass
    
    @abstractmethod
    def get_ci_status(self, pr_id: str) -> CIStatus:
        """CI状態を取得"""
        pass
    
    @abstractmethod
    def add_comment(self, pr_id: str, comment: str) -> None:
        """コメントを追加"""
        pass
    
    @abstractmethod
    def add_labels(self, pr_id: str, labels: List[str]) -> None:
        """ラベルを追加"""
        pass
    
    @abstractmethod
    def assign_reviewers(self, pr_id: str, reviewers: List[str]) -> None:
        """レビュアーを割り当て"""
        pass

class GitHubClient(GitHostClient):
    """GitHub APIクライアント"""
    pass

class GitLabClient(GitHostClient):
    """GitLab APIクライアント"""
    pass

class BitbucketClient(GitHostClient):
    """Bitbucket APIクライアント"""
    pass
```

### 3. PRTemplateEngine

```python
class PRTemplateEngine:
    """PRテンプレートエンジン"""
    
    def generate(self, task: Task, artifacts: List[Artifact]) -> str:
        """PR説明文を生成"""
        template = self._load_template()
        
        context = {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "acceptance_criteria": task.acceptance_criteria,
            "test_results": self._format_test_results(artifacts),
            "artifact_links": self._format_artifact_links(artifacts)
        }
        
        return template.render(context)
```

## Data Models

### PullRequest

```python
@dataclass
class PullRequest:
    """Pull Request情報"""
    pr_id: str
    pr_number: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    url: str
    state: PRState
    draft: bool
    created_at: datetime
    merged_at: Optional[datetime] = None

class PRState(Enum):
    """PR状態"""
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"

class CIStatus(Enum):
    """CI状態"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
```

## PR Template Example

```markdown
## Task: {{task_id}} - {{title}}

### Description
{{description}}

### Acceptance Criteria
{% for criterion in acceptance_criteria %}
- [ ] {{criterion}}
{% endfor %}

### Test Results
{{test_results}}

### Artifacts
- [Diff]({{diff_link}})
- [Logs]({{log_link}})
- [Test Results]({{test_result_link}})

---
*This PR was automatically created by NecroCode*
```

## Configuration

```yaml
# ~/.necrocode/config/pr-service.yaml
pr_service:
  git_host_type: github  # github/gitlab/bitbucket
  create_as_draft: true
  auto_merge_enabled: false
  delete_branch_after_merge: true
  
  labels:
    enabled: true
    rules:
      backend: [backend, api]
      frontend: [frontend, ui]
  
  reviewers:
    enabled: true
    strategy: round-robin  # round-robin/load-balanced/codeowners
```

## Testing Strategy

- Unit tests for each component
- Integration tests with Git host APIs
- Webhook handling tests

## Dependencies

```python
# requirements.txt
PyGithub>=2.1.0  # GitHub API
python-gitlab>=3.15.0  # GitLab API
atlassian-python-api>=3.41.0  # Bitbucket API
jinja2>=3.1.0  # Template engine
```

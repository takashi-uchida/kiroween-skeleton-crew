# Agent Runner

Agent Runnerは、NecroCodeシステムにおいてタスクを実行するステートレスなワーカーコンポーネントです。コンテナベースで起動し、Repo Pool Managerから割り当てられたワークスペースで、fetch→rebase→branch→実装→テスト→pushの一連の処理を自動実行します。

## 特徴

- **ステートレス設計**: 完全にステートレスで、水平スケールが可能
- **複数の実行環境**: local-process/docker/k8sをサポート
- **Playbook対応**: YAML形式のPlaybookでタスク実行手順をカスタマイズ可能
- **自動テスト実行**: 実装後に自動的にテストを実行
- **成果物管理**: diff、ログ、テスト結果をArtifact Storeにアップロード
- **エラーリトライ**: Git操作やネットワークエラーを自動的にリトライ

## インストール

```bash
# 基本的な依存関係
pip install gitpython pyyaml requests psutil

# Dockerモード用（オプション）
pip install docker

# Kubernetesモード用（オプション）
pip install kubernetes
```

## 基本的な使用方法

### 1. タスクコンテキストの準備

```python
from pathlib import Path
from necrocode.agent_runner import TaskContext, RunnerOrchestrator, RunnerConfig

# タスクコンテキストを作成
task_context = TaskContext(
    task_id="1.1",
    spec_name="chat-app",
    title="データベーススキーマの実装",
    description="UserとMessageモデルを作成",
    acceptance_criteria=[
        "Userモデルにemail、password、usernameフィールドがある",
        "Messageモデルにsender、content、timestampフィールドがある"
    ],
    dependencies=[],
    required_skill="backend",
    slot_path=Path("/path/to/workspace"),
    slot_id="slot-1",
    branch_name="feature/task-1.1-database-schema"
)
```

### 2. Runnerの実行

```python
# Runner設定
config = RunnerConfig(
    execution_mode="local-process",
    default_timeout_seconds=1800,
    log_level="INFO"
)

# Runnerを作成して実行
orchestrator = RunnerOrchestrator(config)
result = orchestrator.run(task_context)

if result.success:
    print(f"タスク完了: {result.artifacts}")
else:
    print(f"タスク失敗: {result.error}")
```

## 実行環境

### Local Process Mode

ローカルプロセスとして実行します（開発・テスト用）。

```python
config = RunnerConfig(execution_mode="local-process")
orchestrator = RunnerOrchestrator(config)
```

### Docker Container Mode

Dockerコンテナとして実行します。

```python
config = RunnerConfig(
    execution_mode="docker",
    docker_image="necrocode/agent-runner:latest",
    docker_volumes={
        "/path/to/workspace": "/workspace"
    }
)
orchestrator = DockerRunner(config)
```

### Kubernetes Job Mode

Kubernetes Jobとして実行します。

```python
config = RunnerConfig(
    execution_mode="kubernetes",
    k8s_namespace="necrocode",
    k8s_image="necrocode/agent-runner:latest",
    k8s_secrets=["git-token"]
)
orchestrator = KubernetesRunner(config)
```

## Playbook

Playbookを使用して、タスク実行手順をカスタマイズできます。

### Playbookの作成

```yaml
# playbooks/backend-task.yaml
name: Backend Task Playbook
steps:
  - name: Install dependencies
    command: npm install
    timeout_seconds: 300
    retry_count: 2
  
  - name: Run linter
    command: npm run lint
    condition: lint_enabled == true
    fail_fast: false
  
  - name: Run unit tests
    command: npm test
    timeout_seconds: 600
    fail_fast: true
```

### Playbookの使用

```python
task_context = TaskContext(
    # ... 他のフィールド
    playbook_path=Path("playbooks/backend-task.yaml")
)
```

## 設定オプション

### RunnerConfig

```python
@dataclass
class RunnerConfig:
    # 実行環境
    execution_mode: str = "local-process"  # local-process/docker/kubernetes
    
    # タイムアウト
    default_timeout_seconds: int = 1800  # 30分
    
    # リトライ
    git_retry_count: int = 3
    network_retry_count: int = 3
    
    # リソース制限
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[int] = None
    
    # ログ
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # セキュリティ
    git_token_env_var: str = "GIT_TOKEN"
    mask_secrets: bool = True
    
    # Artifact Store
    artifact_store_url: str = "file://~/.necrocode/artifacts"
```

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `GIT_TOKEN` | Gitリポジトリへのアクセストークン | - |
| `ARTIFACT_STORE_URL` | Artifact StoreのURL | `file://~/.necrocode/artifacts` |
| `RUNNER_LOG_LEVEL` | ログレベル | `INFO` |
| `RUNNER_TIMEOUT` | タスクのタイムアウト（秒） | `1800` |

## コンポーネント

### RunnerOrchestrator

タスク実行のメインコントローラー。

```python
class RunnerOrchestrator:
    def run(self, task_context: TaskContext) -> RunnerResult:
        """タスクを実行"""
```

### WorkspaceManager

ワークスペースのGit操作を管理。

```python
class WorkspaceManager:
    def prepare_workspace(self, slot_path: Path, branch_name: str) -> Workspace:
        """ワークスペースを準備"""
    
    def commit_changes(self, workspace: Workspace, commit_message: str) -> str:
        """変更をコミット"""
    
    def push_branch(self, workspace: Workspace, branch_name: str) -> PushResult:
        """ブランチをプッシュ"""
```

### TaskExecutor

タスクの実装を実行。

```python
class TaskExecutor:
    def execute(self, task_context: TaskContext, workspace: Workspace) -> ImplementationResult:
        """タスクを実装"""
```

### TestRunner

テストの実行を管理。

```python
class TestRunner:
    def run_tests(self, task_context: TaskContext, workspace: Workspace) -> TestResult:
        """テストを実行"""
```

### ArtifactUploader

成果物のアップロードを管理。

```python
class ArtifactUploader:
    def upload_artifacts(
        self,
        task_context: TaskContext,
        impl_result: ImplementationResult,
        test_result: TestResult,
        logs: str
    ) -> List[Artifact]:
        """成果物をアップロード"""
```

### PlaybookEngine

Playbookの実行を管理。

```python
class PlaybookEngine:
    def load_playbook(self, playbook_path: Path) -> Playbook:
        """Playbookを読み込み"""
    
    def execute_playbook(self, playbook: Playbook, context: Dict[str, Any]) -> PlaybookResult:
        """Playbookを実行"""
```

## エラーハンドリング

### 例外階層

```python
RunnerError                      # ベース例外
├── TaskContextValidationError   # タスクコンテキスト検証エラー
├── WorkspacePreparationError    # ワークスペース準備エラー
├── ImplementationError          # 実装エラー
├── TestExecutionError           # テスト実行エラー
├── PushError                    # プッシュエラー
├── ArtifactUploadError          # 成果物アップロードエラー
└── TimeoutError                 # タイムアウトエラー
```

### リトライ戦略

Git操作とネットワークエラーは自動的にリトライされます（指数バックオフ）。

```python
config = RunnerConfig(
    git_retry_count=3,           # Git操作のリトライ回数
    network_retry_count=3        # ネットワークエラーのリトライ回数
)
```

## セキュリティ

- Gitトークンは環境変数またはSecret Mountから取得
- ログから機密情報を自動的にマスク
- タスクスコープに限定された権限のみを使用
- 実行終了時にすべての認証情報をメモリから削除

## モニタリング

### 構造化ログ

JSON形式のログを出力します。

```python
config = RunnerConfig(
    log_level="INFO",
    structured_logging=True
)
```

### メトリクス

実行メトリクス（実行時間、メモリ使用量、CPU使用率）を記録します。

```python
result = orchestrator.run(task_context)
print(f"実行時間: {result.duration_seconds}秒")
print(f"メモリ使用量: {result.metrics.memory_mb}MB")
print(f"CPU使用率: {result.metrics.cpu_percent}%")
```

## トラブルシューティング

### タイムアウトエラー

タスクの実行時間が長すぎる場合、タイムアウトを延長します。

```python
config = RunnerConfig(default_timeout_seconds=3600)  # 1時間
```

### Git操作の失敗

Git操作が失敗する場合、リトライ回数を増やします。

```python
config = RunnerConfig(git_retry_count=5)
```

### メモリ不足

メモリ使用量が多い場合、制限を設定します。

```python
config = RunnerConfig(max_memory_mb=2048)  # 2GB
```

## サンプルコード

詳細なサンプルコードは `examples/` ディレクトリを参照してください。

- `examples/basic_runner_usage.py` - 基本的な使用例
- `examples/custom_playbook.py` - カスタムPlaybookの例
- `examples/docker_runner.py` - Docker実行の例
- `examples/kubernetes_runner.py` - Kubernetes実行の例

## ライセンス

MIT License

## 関連ドキュメント

- [Requirements](.kiro/specs/agent-runner/requirements.md)
- [Design](.kiro/specs/agent-runner/design.md)
- [Tasks](.kiro/specs/agent-runner/tasks.md)

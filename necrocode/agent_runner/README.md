# Agent Runner

Agent Runnerは、NecroCodeシステムにおいてタスクを実行するステートレスなワーカーコンポーネントです。コンテナベースで起動し、Repo Pool Managerから割り当てられたワークスペースで、fetch→rebase→branch→実装→テスト→pushの一連の処理を自動実行します。

## アーキテクチャ

Agent Runnerは以下の外部サービスと統合されています：

- **LLM Service (OpenAI等)**: コード生成エンジン
- **Task Registry**: タスク状態管理とイベント記録
- **Repo Pool Manager**: ワークスペース（スロット）の割り当て・返却
- **Artifact Store**: 成果物（diff、ログ、テスト結果）の保存

```
┌──────────────┐
│  Dispatcher  │ ──HTTP/gRPC──► ┌──────────────┐
└──────────────┘                │ Agent Runner │
                                └──────────────┘
┌──────────────┐                       │
│Task Registry │ ◄──REST API───────────┤
└──────────────┘                       │
                                       │
┌──────────────┐                       │
│ Repo Pool    │ ◄──REST API───────────┤
│ Manager      │                       │
└──────────────┘                       │
                                       │
┌──────────────┐                       │
│ Artifact     │ ◄──REST API───────────┤
│ Store        │                       │
└──────────────┘                       │
                                       │
┌──────────────┐                       │
│ LLM Service  │ ◄──OpenAI API─────────┘
│ (OpenAI)     │
└──────────────┘
```

## 特徴

- **ステートレス設計**: 完全にステートレスで、水平スケールが可能
- **LLM統合**: OpenAI等のLLMサービスを使用してコードを自動生成
- **外部サービス統合**: Task Registry、Repo Pool Manager、Artifact Storeと連携
- **複数の実行環境**: local-process/docker/k8sをサポート
- **Playbook対応**: YAML形式のPlaybookでタスク実行手順をカスタマイズ可能
- **自動テスト実行**: 実装後に自動的にテストを実行
- **成果物管理**: diff、ログ、テスト結果をArtifact Storeにアップロード
- **エラーリトライ**: Git操作、ネットワークエラー、LLMレート制限を自動的にリトライ

## インストール

```bash
# 基本的な依存関係
pip install gitpython pyyaml requests psutil openai

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

### 2. LLM設定

```python
from necrocode.agent_runner import LLMConfig

# LLM設定を作成
llm_config = LLMConfig(
    api_key="your-openai-api-key",  # または環境変数 OPENAI_API_KEY
    model="gpt-4",
    timeout_seconds=120
)
```

### 3. 外部サービス設定

```python
# Runner設定（外部サービスのURLを指定）
config = RunnerConfig(
    execution_mode="local-process",
    default_timeout_seconds=1800,
    log_level="INFO",
    task_registry_url="http://localhost:8001",
    repo_pool_url="http://localhost:8002",
    artifact_store_url="http://localhost:8003",
    llm_config=llm_config
)
```

### 4. Runnerの実行

```python
# Runnerを作成して実行
orchestrator = RunnerOrchestrator(config)
result = orchestrator.run(task_context)

if result.success:
    print(f"タスク完了: {result.artifacts}")
    print(f"LLMモデル: {result.impl_result.llm_model}")
    print(f"トークン使用量: {result.impl_result.tokens_used}")
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
    
    # 外部サービス
    task_registry_url: str = "http://localhost:8001"
    repo_pool_url: str = "http://localhost:8002"
    artifact_store_url: str = "http://localhost:8003"
    
    # LLM設定
    llm_config: Optional[LLMConfig] = None
    
    # タイムアウト
    default_timeout_seconds: int = 1800  # 30分
    
    # リトライ
    git_retry_count: int = 3
    network_retry_count: int = 3
    llm_retry_count: int = 3
    
    # リソース制限
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[int] = None
    
    # ログ
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # セキュリティ
    git_token_env_var: str = "GIT_TOKEN"
    llm_api_key_env_var: str = "OPENAI_API_KEY"
    mask_secrets: bool = True
```

### LLMConfig

```python
@dataclass
class LLMConfig:
    api_key: str                          # LLM APIキー
    model: str = "gpt-4"                  # モデル名
    endpoint: Optional[str] = None        # カスタムエンドポイント
    timeout_seconds: int = 120            # タイムアウト
```

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `GIT_TOKEN` | Gitリポジトリへのアクセストークン | - |
| `OPENAI_API_KEY` | OpenAI APIキー | - |
| `TASK_REGISTRY_URL` | Task RegistryのURL | `http://localhost:8001` |
| `REPO_POOL_URL` | Repo Pool ManagerのURL | `http://localhost:8002` |
| `ARTIFACT_STORE_URL` | Artifact StoreのURL | `http://localhost:8003` |
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

タスクの実装を実行（LLMを使用してコードを生成）。

```python
class TaskExecutor:
    def __init__(self, llm_config: LLMConfig):
        self.llm_client = LLMClient(llm_config)
    
    def execute(self, task_context: TaskContext, workspace: Workspace) -> ImplementationResult:
        """タスクを実装（LLMでコード生成）"""
```

### LLMClient

LLMサービスとの通信を管理。

```python
class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
    
    def generate_code(
        self,
        prompt: str,
        workspace_path: Path,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """コードを生成"""
```

### 外部サービスクライアント

#### TaskRegistryClient

```python
class TaskRegistryClient:
    def update_task_status(self, task_id: str, status: str) -> None:
        """タスク状態を更新"""
    
    def add_event(self, task_id: str, event_type: str, data: Dict) -> None:
        """イベントを記録"""
    
    def add_artifact(self, task_id: str, artifact_type: str, uri: str) -> None:
        """成果物を記録"""
```

#### RepoPoolClient

```python
class RepoPoolClient:
    def allocate_slot(self, repo_url: str, required_by: str) -> SlotAllocation:
        """スロットを割り当て"""
    
    def release_slot(self, slot_id: str) -> None:
        """スロットを返却"""
```

#### ArtifactStoreClient

```python
class ArtifactStoreClient:
    def upload(self, artifact_type: str, content: bytes) -> str:
        """成果物をアップロード（URIを返す）"""
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

## 設定ファイル例

### config.yaml

```yaml
# 基本設定
execution_mode: local-process
default_timeout_seconds: 1800
log_level: INFO

# 外部サービス
task_registry_url: http://localhost:8001
repo_pool_url: http://localhost:8002
artifact_store_url: http://localhost:8003

# LLM設定
llm:
  model: gpt-4
  timeout_seconds: 120

# リトライ設定
git_retry_count: 3
network_retry_count: 3
llm_retry_count: 3

# リソース制限
max_memory_mb: 2048
max_cpu_percent: 80
```

### config.docker.yaml

```yaml
execution_mode: docker
docker_image: necrocode/agent-runner:latest
docker_volumes:
  /var/necrocode/workspaces: /workspaces

# 外部サービス（Dockerネットワーク内）
task_registry_url: http://task-registry:8001
repo_pool_url: http://repo-pool:8002
artifact_store_url: http://artifact-store:8003

llm:
  model: gpt-4
  timeout_seconds: 120
```

### config.k8s.yaml

```yaml
execution_mode: kubernetes
k8s_namespace: necrocode
k8s_image: necrocode/agent-runner:latest
k8s_secrets:
  - git-token
  - openai-api-key

# 外部サービス（Kubernetes内）
task_registry_url: http://task-registry.necrocode.svc.cluster.local:8001
repo_pool_url: http://repo-pool.necrocode.svc.cluster.local:8002
artifact_store_url: http://artifact-store.necrocode.svc.cluster.local:8003

llm:
  model: gpt-4
  timeout_seconds: 120

# リソース制限
max_memory_mb: 4096
max_cpu_percent: 200
```

## サンプルコード

詳細なサンプルコードは `examples/` ディレクトリを参照してください。

- `examples/basic_runner_usage.py` - 基本的な使用例（外部サービス統合を含む）
- `examples/llm_integration.py` - LLM統合の例
- `examples/external_services.py` - 外部サービス統合の例
- `examples/custom_playbook.py` - カスタムPlaybookの例
- `examples/docker_runner.py` - Docker実行の例
- `examples/kubernetes_runner.py` - Kubernetes実行の例

## ライセンス

MIT License

## 関連ドキュメント

- [Requirements](.kiro/specs/agent-runner/requirements.md)
- [Design](.kiro/specs/agent-runner/design.md)
- [Tasks](.kiro/specs/agent-runner/tasks.md)

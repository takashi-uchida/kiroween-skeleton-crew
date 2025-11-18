# Agent Runner Design Document

## Overview

Agent Runnerは、タスクを実行するステートレスなワーカーコンポーネントです。コンテナベースで起動し、Repo Pool Managerから割り当てられたワークスペースで、fetch→rebase→branch→実装→テスト→pushの一連の処理を自動実行します。複数の実行環境（local-process/docker/k8s）をサポートし、水平スケールが可能です。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Dispatcher ──────► Agent Runner ◄────── Task Registry     │
│                           │                                 │
│                           ▼                                 │
│                    Repo Pool Manager                        │
│                           │                                 │
│                           ▼                                 │
│                    Workspace (Git)                          │
│                           │                                 │
│                           ▼                                 │
│                    Artifact Store                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Runner                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  RunnerOrchestrator      │  TaskExecutor    │           │
│  │  (Main Controller)│◄────►│  (Task Impl)     │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  WorkspaceManager│      │  TestRunner      │           │
│  │  (Git Ops)       │      │  (Test Exec)     │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  ArtifactUploader│      │  PlaybookEngine  │           │
│  │  (Upload)        │      │  (Playbook)      │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. RunnerOrchestrator (Main Controller)

Agent Runnerの実行フローを制御します。

```python
class RunnerOrchestrator:
    """Agent Runnerのメインコントローラー"""
    
    def __init__(self, config: RunnerConfig):
        """
        Args:
            config: Runner設定
        """
        self.config = config
        self.runner_id = self._generate_runner_id()
        self.state = RunnerState.IDLE
        
        # A2Aプロトコルの初期化
        self.message_bus = MessageBus(config.message_bus_config)
        self.agent_registry = AgentRegistry(config.registry_storage)
        self.a2a_client = A2AClient(
            agent_id=self.runner_id,
            capabilities=config.capabilities,
            message_bus=self.message_bus,
            agent_registry=self.agent_registry
        )
        
        # コンポーネントの初期化（A2Aクライアントを渡す）
        self.workspace_manager = WorkspaceManager()
        self.task_executor = TaskExecutor(self.a2a_client)
        self.test_runner = TestRunner()
        self.artifact_uploader = ArtifactUploader()
        self.playbook_engine = PlaybookEngine()
        
        # A2Aメッセージハンドラーを登録
        self._register_a2a_handlers()
    
    def run(self, task_context: TaskContext) -> RunnerResult:
        """タスクを実行"""
        try:
            self._validate_task_context(task_context)
            self._transition_state(RunnerState.RUNNING)
            
            # 1. ワークスペース準備
            workspace = self._prepare_workspace(task_context)
            
            # 2. タスク実装
            impl_result = self._execute_task(task_context, workspace)
            
            # 3. テスト実行
            test_result = self._run_tests(task_context, workspace)
            
            # 4. コミット＆プッシュ
            push_result = self._commit_and_push(task_context, workspace)
            
            # 5. 成果物アップロード
            artifacts = self._upload_artifacts(task_context, impl_result, test_result)
            
            # 6. 完了報告
            self._report_completion(task_context, artifacts)
            
            self._transition_state(RunnerState.COMPLETED)
            return RunnerResult(success=True, artifacts=artifacts)
            
        except Exception as e:
            self._handle_error(task_context, e)
            self._transition_state(RunnerState.FAILED)
            return RunnerResult(success=False, error=str(e))
        
        finally:
            self._cleanup(task_context)
    
    def _prepare_workspace(self, task_context: TaskContext) -> Workspace:
        """ワークスペースを準備"""
        pass
    
    def _execute_task(self, task_context: TaskContext, workspace: Workspace) -> ImplementationResult:
        """タスクを実装"""
        pass
    
    def _run_tests(self, task_context: TaskContext, workspace: Workspace) -> TestResult:
        """テストを実行"""
        pass
    
    def _commit_and_push(self, task_context: TaskContext, workspace: Workspace) -> PushResult:
        """コミットしてプッシュ"""
        pass
    
    def _upload_artifacts(
        self,
        task_context: TaskContext,
        impl_result: ImplementationResult,
        test_result: TestResult
    ) -> List[Artifact]:
        """成果物をアップロード"""
        pass
    
    def _report_completion(self, task_context: TaskContext, artifacts: List[Artifact]) -> None:
        """完了を報告"""
        pass
    
    def _handle_error(self, task_context: TaskContext, error: Exception) -> None:
        """エラーを処理"""
        pass
    
    def _cleanup(self, task_context: TaskContext) -> None:
        """クリーンアップ"""
        pass

### 2. WorkspaceManager (Git Operations)

ワークスペースのGit操作を管理します。

```python
class WorkspaceManager:
    """ワークスペースのGit操作"""
    
    def __init__(self):
        self.git_ops = GitOperations()
    
    def prepare_workspace(
        self,
        slot_path: Path,
        branch_name: str
    ) -> Workspace:
        """ワークスペースを準備"""
        # 1. git checkout main
        # 2. git fetch origin
        # 3. git rebase origin/main
        # 4. git checkout -b {branch_name}
        pass
    
    def commit_changes(
        self,
        workspace: Workspace,
        commit_message: str
    ) -> str:
        """変更をコミット"""
        # 1. git add .
        # 2. git commit -m "{commit_message}"
        # 3. コミットハッシュを返す
        pass
    
    def push_branch(
        self,
        workspace: Workspace,
        branch_name: str,
        retry_count: int = 3
    ) -> PushResult:
        """ブランチをプッシュ"""
        pass
    
    def get_diff(self, workspace: Workspace) -> str:
        """変更のdiffを取得"""
        pass
    
    def rollback(self, workspace: Workspace) -> None:
        """変更をロールバック"""
        pass

### 3. TaskExecutor (Task Implementation)

タスクの実装を実行します。A2Aプロトコルを使用して他のエージェントと協調します。

```python
class TaskExecutor:
    """タスクの実装"""
    
    def __init__(self, a2a_client: A2AClient):
        self.kiro_client = KiroClient()
        self.a2a_client = a2a_client
        self.code_review_collab = CodeReviewCollaboration(a2a_client)
        self.pair_programming_collab = PairProgrammingCollaboration(a2a_client)
    
    def execute(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> ImplementationResult:
        """タスクを実装"""
        try:
            # 1. 複雑なタスクの場合はペアプログラミングを検討
            if task_context.complexity == "high":
                return self._execute_with_pair(task_context, workspace)
            
            # 2. タスクコンテキストをKiroに渡す
            prompt = self._build_implementation_prompt(task_context)
            
            # 3. Kiroに実装を依頼
            impl_response = self.kiro_client.implement(prompt, workspace.path)
            
            # 4. 実装結果を検証
            if not self._verify_implementation(impl_response):
                raise ImplementationError("Implementation verification failed")
            
            # 5. 変更内容をdiffとして保存
            diff = workspace.get_diff()
            
            # 6. コードレビューを依頼
            if task_context.require_review:
                review_result = self.code_review_collab.request_review(
                    task_id=task_context.task_id,
                    diff=diff,
                    files_changed=impl_response.files_changed,
                    implementation_notes=impl_response.notes
                )
                
                # レビューが承認されなかった場合は修正
                if not review_result.approved:
                    return self._fix_review_issues(
                        task_context,
                        workspace,
                        review_result
                    )
            
            return ImplementationResult(
                success=True,
                diff=diff,
                files_changed=impl_response.files_changed,
                duration_seconds=impl_response.duration,
                review_result=review_result if task_context.require_review else None
            )
            
        except Exception as e:
            return ImplementationResult(
                success=False,
                error=str(e)
            )
    
    def _execute_with_pair(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> ImplementationResult:
        """ペアプログラミングで実装"""
        # ペアセッションを開始
        session = self.pair_programming_collab.start_session(
            task_id=task_context.task_id,
            task_description=task_context.description,
            required_capability="backend"  # タスクに応じて変更
        )
        
        # 協調して実装
        # （実装の詳細は省略）
        
        return ImplementationResult(
            success=True,
            diff=workspace.get_diff(),
            files_changed=[],
            duration_seconds=0,
            pair_session_id=session.session_id
        )
    
    def _fix_review_issues(
        self,
        task_context: TaskContext,
        workspace: Workspace,
        review_result: ReviewResult
    ) -> ImplementationResult:
        """レビュー指摘を修正"""
        # レビューコメントに基づいて修正
        fix_prompt = self._build_fix_prompt(review_result)
        fix_response = self.kiro_client.implement(fix_prompt, workspace.path)
        
        return ImplementationResult(
            success=True,
            diff=workspace.get_diff(),
            files_changed=fix_response.files_changed,
            duration_seconds=fix_response.duration,
            review_result=review_result
        )
    
    def _build_implementation_prompt(self, task_context: TaskContext) -> str:
        """実装プロンプトを構築"""
        pass
    
    def _verify_implementation(self, impl_response: Any) -> bool:
        """実装を検証"""
        pass

### 4. TestRunner (Test Execution)

テストの実行を管理します。

```python
class TestRunner:
    """テストの実行"""
    
    def __init__(self):
        self.command_executor = CommandExecutor()
    
    def run_tests(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> TestResult:
        """テストを実行"""
        test_commands = task_context.test_commands or self._get_default_test_commands()
        
        results = []
        for cmd in test_commands:
            result = self._run_single_test(cmd, workspace)
            results.append(result)
            
            if not result.success and task_context.fail_fast:
                break
        
        return TestResult(
            success=all(r.success for r in results),
            test_results=results,
            total_duration_seconds=sum(r.duration_seconds for r in results)
        )
    
    def _run_single_test(
        self,
        command: str,
        workspace: Workspace
    ) -> SingleTestResult:
        """単一のテストを実行"""
        pass
    
    def _get_default_test_commands(self) -> List[str]:
        """デフォルトのテストコマンドを取得"""
        pass

### 5. ArtifactUploader (Artifact Upload)

成果物のアップロードを管理します。

```python
class ArtifactUploader:
    """成果物のアップロード"""
    
    def __init__(self):
        self.artifact_store_client = ArtifactStoreClient()
    
    def upload_artifacts(
        self,
        task_context: TaskContext,
        impl_result: ImplementationResult,
        test_result: TestResult,
        logs: str
    ) -> List[Artifact]:
        """成果物をアップロード"""
        artifacts = []
        
        # 1. diffをアップロード
        if impl_result.diff:
            diff_artifact = self._upload_diff(task_context, impl_result.diff)
            artifacts.append(diff_artifact)
        
        # 2. ログをアップロード
        log_artifact = self._upload_log(task_context, logs)
        artifacts.append(log_artifact)
        
        # 3. テスト結果をアップロード
        if test_result:
            test_artifact = self._upload_test_result(task_context, test_result)
            artifacts.append(test_artifact)
        
        return artifacts
    
    def _upload_diff(self, task_context: TaskContext, diff: str) -> Artifact:
        """diffをアップロード"""
        pass
    
    def _upload_log(self, task_context: TaskContext, logs: str) -> Artifact:
        """ログをアップロード"""
        pass
    
    def _upload_test_result(self, task_context: TaskContext, test_result: TestResult) -> Artifact:
        """テスト結果をアップロード"""
        pass

### 6. PlaybookEngine (Playbook Execution)

Playbookの実行を管理します。

```python
class PlaybookEngine:
    """Playbookの実行"""
    
    def __init__(self):
        self.command_executor = CommandExecutor()
    
    def load_playbook(self, playbook_path: Path) -> Playbook:
        """Playbookを読み込み"""
        pass
    
    def execute_playbook(
        self,
        playbook: Playbook,
        context: Dict[str, Any]
    ) -> PlaybookResult:
        """Playbookを実行"""
        results = []
        
        for step in playbook.steps:
            if not self._should_execute_step(step, context):
                continue
            
            result = self._execute_step(step, context)
            results.append(result)
            
            if not result.success and step.fail_fast:
                break
        
        return PlaybookResult(
            success=all(r.success for r in results),
            step_results=results
        )
    
    def _should_execute_step(self, step: PlaybookStep, context: Dict) -> bool:
        """ステップを実行すべきか判定"""
        pass
    
    def _execute_step(self, step: PlaybookStep, context: Dict) -> StepResult:
        """ステップを実行"""
        pass

## Data Models

### TaskContext

```python
@dataclass
class TaskContext:
    """タスクコンテキスト"""
    task_id: str
    spec_name: str
    title: str
    description: str
    acceptance_criteria: List[str]
    dependencies: List[str]
    required_skill: str
    
    # ワークスペース情報
    slot_path: Path
    slot_id: str
    branch_name: str
    
    # テスト設定
    test_commands: Optional[List[str]] = None
    fail_fast: bool = True
    
    # タイムアウト設定
    timeout_seconds: int = 1800  # 30分
    
    # Playbook
    playbook_path: Optional[Path] = None
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)

### RunnerState

```python
class RunnerState(Enum):
    """Runnerの状態"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

### RunnerResult

```python
@dataclass
class RunnerResult:
    """Runner実行結果"""
    success: bool
    runner_id: str
    task_id: str
    duration_seconds: float
    artifacts: List[Artifact]
    error: Optional[str] = None
    
    # 詳細結果
    impl_result: Optional[ImplementationResult] = None
    test_result: Optional[TestResult] = None
    push_result: Optional[PushResult] = None

### ImplementationResult

```python
@dataclass
class ImplementationResult:
    """実装結果"""
    success: bool
    diff: str
    files_changed: List[str]
    duration_seconds: float
    error: Optional[str] = None

### TestResult

```python
@dataclass
class TestResult:
    """テスト結果"""
    success: bool
    test_results: List[SingleTestResult]
    total_duration_seconds: float

@dataclass
class SingleTestResult:
    """単一のテスト結果"""
    command: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float

### PushResult

```python
@dataclass
class PushResult:
    """プッシュ結果"""
    success: bool
    branch_name: str
    commit_hash: str
    retry_count: int
    error: Optional[str] = None

### Artifact

```python
@dataclass
class Artifact:
    """成果物"""
    type: ArtifactType
    uri: str
    size_bytes: int
    created_at: datetime

class ArtifactType(Enum):
    """成果物のタイプ"""
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"

### Playbook

```python
@dataclass
class Playbook:
    """Playbook定義"""
    name: str
    steps: List[PlaybookStep]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlaybookStep:
    """Playbookステップ"""
    name: str
    command: str
    condition: Optional[str] = None  # 例: "test_enabled == true"
    fail_fast: bool = True
    timeout_seconds: int = 300
    retry_count: int = 0

## Execution Environments

### Local Process Mode

```python
class LocalProcessRunner(RunnerOrchestrator):
    """ローカルプロセスとして実行"""
    
    def __init__(self, config: RunnerConfig):
        super().__init__(config)
        self.execution_mode = ExecutionMode.LOCAL_PROCESS

### Docker Container Mode

```python
class DockerRunner(RunnerOrchestrator):
    """Dockerコンテナとして実行"""
    
    def __init__(self, config: RunnerConfig):
        super().__init__(config)
        self.execution_mode = ExecutionMode.DOCKER
        self.container_id = None
    
    def run(self, task_context: TaskContext) -> RunnerResult:
        """Dockerコンテナ内で実行"""
        # ワークスペースをマウント
        # 環境変数を注入
        # コンテナ内でタスクを実行
        pass

### Kubernetes Job Mode

```python
class KubernetesRunner(RunnerOrchestrator):
    """Kubernetes Jobとして実行"""
    
    def __init__(self, config: RunnerConfig):
        super().__init__(config)
        self.execution_mode = ExecutionMode.KUBERNETES
        self.job_name = None
    
    def run(self, task_context: TaskContext) -> RunnerResult:
        """Kubernetes Job内で実行"""
        # Jobマニフェストを生成
        # Secretをマウント
        # Jobを起動して完了を待機
        pass

## Configuration

### RunnerConfig

```python
@dataclass
class RunnerConfig:
    """Runner設定"""
    # 実行環境
    execution_mode: ExecutionMode = ExecutionMode.LOCAL_PROCESS
    
    # タイムアウト
    default_timeout_seconds: int = 1800
    
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
    
    # Playbook
    default_playbook_path: Optional[Path] = None

class ExecutionMode(Enum):
    """実行モード"""
    LOCAL_PROCESS = "local-process"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"

## Playbook Example

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
  
  - name: Build project
    command: npm run build
    timeout_seconds: 300
```

## Error Handling

### Exception Hierarchy

```python
class RunnerError(Exception):
    """Base exception for Runner"""
    pass

class TaskContextValidationError(RunnerError):
    """Task context validation failed"""
    pass

class WorkspacePreparationError(RunnerError):
    """Workspace preparation failed"""
    pass

class ImplementationError(RunnerError):
    """Implementation failed"""
    pass

class TestExecutionError(RunnerError):
    """Test execution failed"""
    pass

class PushError(RunnerError):
    """Push failed"""
    pass

class ArtifactUploadError(RunnerError):
    """Artifact upload failed"""
    pass

class TimeoutError(RunnerError):
    """Execution timeout"""
    pass
```

### Retry Strategy

```python
@dataclass
class RetryConfig:
    """リトライ設定"""
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    
    def get_delay(self, attempt: int) -> float:
        """リトライ遅延を計算（指数バックオフ）"""
        delay = self.initial_delay_seconds * (self.exponential_base ** attempt)
        return min(delay, self.max_delay_seconds)
```

## Testing Strategy

### Unit Tests

- `test_runner_orchestrator.py`: RunnerOrchestratorの実行フロー
- `test_workspace_manager.py`: WorkspaceManagerのGit操作
- `test_task_executor.py`: TaskExecutorの実装機能
- `test_test_runner.py`: TestRunnerのテスト実行
- `test_artifact_uploader.py`: ArtifactUploaderのアップロード
- `test_playbook_engine.py`: PlaybookEngineのPlaybook実行

### Integration Tests

- `test_runner_integration.py`: 実際のタスク実行の統合テスト
- `test_docker_runner.py`: Dockerコンテナでの実行
- `test_kubernetes_runner.py`: Kubernetes Jobでの実行

### Performance Tests

- `test_runner_performance.py`: 実行時間の測定
- `test_parallel_runners.py`: 並列実行の性能

## Dependencies

```python
# requirements.txt
gitpython>=3.1.0
pyyaml>=6.0
requests>=2.31.0
docker>=6.1.0  # Dockerモード用
kubernetes>=27.2.0  # Kubernetesモード用
psutil>=5.9.0  # リソース監視
```

## Future Enhancements

1. **キャッシュ機構**: 依存関係のキャッシュで実行時間を短縮
2. **インクリメンタル実装**: 大きなタスクを段階的に実装
3. **自動修正**: テスト失敗時の自動修正機能
4. **並列テスト**: テストの並列実行
5. **リアルタイムログストリーミング**: 実行中のログをリアルタイムで配信

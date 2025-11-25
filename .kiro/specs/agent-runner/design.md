# Agent Runner Design Document

## Overview

Agent Runnerは、タスクを実行するステートレスなワーカーコンポーネントです。Dispatcherから受け取ったタスクを、Repo Pool Managerから割り当てられたワークスペースで実行します。Kiroをコード生成エンジンとして利用し、fetch→rebase→branch→実装→テスト→pushの一連の処理を自動実行します。複数の実行環境（local-process/docker/k8s）をサポートし、水平スケールが可能です。

## Core Principle

**Agent Runner = タスク実行オーケストレーター + Kiro（コード生成エンジン）**

Agent Runnerは「エージェント」ではなく、Kiroを呼び出してコードを生成させる「オーケストレーター」です。実際のコード生成はKiroが担当します。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Dispatcher ──────► Agent Runner ◄────── Task Registry     │
│                           │                                 │
│                           ├──────► Kiro (LLM Service)       │
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
│  │  (Main Controller)│◄────►│  (Kiro Invoker)  │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           │                         ▼                      │
│           │                ┌──────────────────┐           │
│           │                │  LLMClient       │           │
│           │                │  (OpenAI/etc)    │           │
│           │                └──────────────────┘           │
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

### 外部サービスとの統合

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
        
        # 外部サービスクライアントの初期化
        self.task_registry_client = TaskRegistryClient(config.task_registry_url)
        self.repo_pool_client = RepoPoolClient(config.repo_pool_url)
        self.artifact_store_client = ArtifactStoreClient(config.artifact_store_url)
        
        # コンポーネントの初期化
        self.workspace_manager = WorkspaceManager()
        self.task_executor = TaskExecutor(config.llm_config)
        self.test_runner = TestRunner()
        self.artifact_uploader = ArtifactUploader(self.artifact_store_client)
        self.playbook_engine = PlaybookEngine()
    
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

タスクの実装を実行します。LLMサービス（OpenAI等）を使用してコードを生成します。

```python
class TaskExecutor:
    """タスクの実装"""
    
    def __init__(self, llm_config: LLMConfig):
        """
        Args:
            llm_config: LLM設定（APIキー、モデル名等）
        """
        self.llm_client = LLMClient(llm_config)
    
    def execute(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> ImplementationResult:
        """タスクを実装"""
        try:
            # 1. タスクコンテキストからプロンプトを構築
            prompt = self._build_implementation_prompt(task_context, workspace)
            
            # 2. LLMにコード生成を依頼
            start_time = time.time()
            llm_response = self.llm_client.generate_code(
                prompt=prompt,
                workspace_path=workspace.path,
                max_tokens=task_context.max_tokens or 4000
            )
            duration = time.time() - start_time
            
            # 3. 生成されたコードをワークスペースに適用
            files_changed = self._apply_code_changes(
                workspace,
                llm_response.code_changes
            )
            
            # 4. 実装結果を検証
            if not self._verify_implementation(workspace, files_changed):
                raise ImplementationError("Implementation verification failed")
            
            # 5. 変更内容をdiffとして保存
            diff = workspace.get_diff()
            
            return ImplementationResult(
                success=True,
                diff=diff,
                files_changed=files_changed,
                duration_seconds=duration,
                llm_model=llm_response.model,
                tokens_used=llm_response.tokens_used
            )
            
        except Exception as e:
            return ImplementationResult(
                success=False,
                error=str(e)
            )
    
    def _apply_code_changes(
        self,
        workspace: Workspace,
        code_changes: List[CodeChange]
    ) -> List[str]:
        """コード変更をワークスペースに適用"""
        files_changed = []
        
        for change in code_changes:
            file_path = workspace.path / change.file_path
            
            if change.operation == "create":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(change.content)
                files_changed.append(str(change.file_path))
                
            elif change.operation == "modify":
                if not file_path.exists():
                    raise ImplementationError(f"File not found: {change.file_path}")
                file_path.write_text(change.content)
                files_changed.append(str(change.file_path))
                
            elif change.operation == "delete":
                if file_path.exists():
                    file_path.unlink()
                    files_changed.append(str(change.file_path))
        
        return files_changed
    
    def _build_implementation_prompt(
        self,
        task_context: TaskContext,
        workspace: Workspace
    ) -> str:
        """実装プロンプトを構築"""
        prompt_parts = [
            f"# Task: {task_context.title}",
            f"\n## Description\n{task_context.description}",
            "\n## Acceptance Criteria"
        ]
        
        for i, criteria in enumerate(task_context.acceptance_criteria, 1):
            prompt_parts.append(f"{i}. {criteria}")
        
        # 依存タスクの情報を追加
        if task_context.dependencies:
            prompt_parts.append("\n## Completed Dependencies")
            for dep_id in task_context.dependencies:
                prompt_parts.append(f"- Task {dep_id}")
        
        # 既存のファイル構造を追加
        prompt_parts.append("\n## Current Workspace Structure")
        prompt_parts.append(self._get_workspace_structure(workspace))
        
        # 関連ファイルの内容を追加
        if task_context.related_files:
            prompt_parts.append("\n## Related Files")
            for file_path in task_context.related_files:
                content = workspace.read_file(file_path)
                prompt_parts.append(f"\n### {file_path}\n```\n{content}\n```")
        
        prompt_parts.append("\n## Instructions")
        prompt_parts.append("Generate the code changes needed to implement this task.")
        prompt_parts.append("Return the changes in the following JSON format:")
        prompt_parts.append("""
{
  "code_changes": [
    {
      "file_path": "path/to/file.py",
      "operation": "create|modify|delete",
      "content": "file content here"
    }
  ],
  "explanation": "Brief explanation of changes"
}
""")
        
        return "\n".join(prompt_parts)
    
    def _get_workspace_structure(self, workspace: Workspace) -> str:
        """ワークスペースの構造を取得"""
        # 簡易的なファイルツリーを生成
        # 実装の詳細は省略
        return "src/\n  main.py\n  utils.py\ntests/\n  test_main.py"
    
    def _verify_implementation(
        self,
        workspace: Workspace,
        files_changed: List[str]
    ) -> bool:
        """実装を検証"""
        # 基本的な検証
        if not files_changed:
            return False
        
        # 変更されたファイルが存在するか確認
        for file_path in files_changed:
            full_path = workspace.path / file_path
            if not full_path.exists():
                return False
        
        return True

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
    
    def __init__(self, artifact_store_client: ArtifactStoreClient):
        """
        Args:
            artifact_store_client: Artifact Storeクライアント
        """
        self.artifact_store_client = artifact_store_client
    
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

## External Service Clients

### TaskRegistryClient

```python
class TaskRegistryClient:
    """Task Registryとの通信クライアント"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """タスクの状態を更新"""
        response = self.session.put(
            f"{self.base_url}/tasks/{task_id}/status",
            json={"status": status, "metadata": metadata}
        )
        response.raise_for_status()
    
    def add_event(
        self,
        task_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """イベントを記録"""
        response = self.session.post(
            f"{self.base_url}/tasks/{task_id}/events",
            json={"event_type": event_type, "data": data}
        )
        response.raise_for_status()
    
    def add_artifact(
        self,
        task_id: str,
        artifact_type: str,
        uri: str,
        size_bytes: int
    ) -> None:
        """成果物を記録"""
        response = self.session.post(
            f"{self.base_url}/tasks/{task_id}/artifacts",
            json={
                "type": artifact_type,
                "uri": uri,
                "size_bytes": size_bytes
            }
        )
        response.raise_for_status()
```

### RepoPoolClient

```python
class RepoPoolClient:
    """Repo Pool Managerとの通信クライアント"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def allocate_slot(
        self,
        repo_url: str,
        required_by: str
    ) -> SlotAllocation:
        """スロットを割り当て"""
        response = self.session.post(
            f"{self.base_url}/slots/allocate",
            json={"repo_url": repo_url, "required_by": required_by}
        )
        response.raise_for_status()
        data = response.json()
        return SlotAllocation(
            slot_id=data["slot_id"],
            slot_path=Path(data["slot_path"])
        )
    
    def release_slot(self, slot_id: str) -> None:
        """スロットを返却"""
        response = self.session.post(
            f"{self.base_url}/slots/{slot_id}/release"
        )
        response.raise_for_status()
```

### ArtifactStoreClient

```python
class ArtifactStoreClient:
    """Artifact Storeとの通信クライアント"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def upload(
        self,
        artifact_type: str,
        content: bytes,
        metadata: Dict[str, Any] = None
    ) -> str:
        """成果物をアップロード"""
        files = {"file": content}
        data = {"type": artifact_type, "metadata": json.dumps(metadata or {})}
        
        response = self.session.post(
            f"{self.base_url}/artifacts",
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()["uri"]
```

### LLMClient

```python
class LLMClient:
    """LLMサービスとの通信クライアント"""
    
    def __init__(self, config: LLMConfig):
        """
        Args:
            config: LLM設定（APIキー、モデル名、エンドポイント等）
        """
        self.config = config
        self.client = openai.OpenAI(api_key=config.api_key)
    
    def generate_code(
        self,
        prompt: str,
        workspace_path: Path,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """コードを生成"""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are a code generation assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        
        # JSONレスポンスをパース
        try:
            data = json.loads(content)
            code_changes = [
                CodeChange(**change) for change in data["code_changes"]
            ]
            explanation = data.get("explanation", "")
        except json.JSONDecodeError:
            raise ImplementationError("Failed to parse LLM response")
        
        return LLMResponse(
            code_changes=code_changes,
            explanation=explanation,
            model=response.model,
            tokens_used=response.usage.total_tokens
        )
```

## Data Models

### SlotAllocation

```python
@dataclass
class SlotAllocation:
    """スロット割り当て情報"""
    slot_id: str
    slot_path: Path
```

### CodeChange

```python
@dataclass
class CodeChange:
    """コード変更"""
    file_path: str
    operation: str  # "create", "modify", "delete"
    content: str = ""
```

### LLMResponse

```python
@dataclass
class LLMResponse:
    """LLMレスポンス"""
    code_changes: List[CodeChange]
    explanation: str
    model: str
    tokens_used: int
```

### LLMConfig

```python
@dataclass
class LLMConfig:
    """LLM設定"""
    api_key: str
    model: str = "gpt-4"
    endpoint: Optional[str] = None
    timeout_seconds: int = 120
```

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
    llm_model: Optional[str] = None
    tokens_used: Optional[int] = None
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
# Git操作
gitpython>=3.1.0

# 設定ファイル
pyyaml>=6.0

# HTTP通信
requests>=2.31.0

# LLMサービス
openai>=1.0.0

# コンテナ実行環境
docker>=6.1.0  # Dockerモード用
kubernetes>=27.2.0  # Kubernetesモード用

# リソース監視
psutil>=5.9.0

# ロギング
structlog>=23.1.0
```

## Configuration Example

```yaml
# config.yaml
runner:
  runner_id: "runner-001"
  execution_mode: "local-process"
  
  # タイムアウト
  default_timeout_seconds: 1800
  
  # リトライ
  git_retry_count: 3
  network_retry_count: 3
  
  # リソース制限
  max_memory_mb: 4096
  max_cpu_percent: 80
  
  # ログ
  log_level: "INFO"
  structured_logging: true

# 外部サービス
task_registry:
  url: "http://task-registry:8080"
  
repo_pool:
  url: "http://repo-pool:8081"
  
artifact_store:
  url: "http://artifact-store:8082"

# LLM設定
llm:
  provider: "openai"
  model: "gpt-4"
  api_key_env: "OPENAI_API_KEY"
  timeout_seconds: 120
  max_tokens: 4000

# セキュリティ
security:
  git_token_env: "GIT_TOKEN"
  mask_secrets: true
```

## Future Enhancements

1. **キャッシュ機構**: 依存関係のキャッシュで実行時間を短縮
2. **インクリメンタル実装**: 大きなタスクを段階的に実装
3. **自動修正**: テスト失敗時の自動修正機能
4. **並列テスト**: テストの並列実行
5. **リアルタイムログストリーミング**: 実行中のログをリアルタイムで配信

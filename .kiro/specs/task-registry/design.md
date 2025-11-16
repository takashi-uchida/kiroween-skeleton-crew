# Task Registry Design Document

## Overview

Task Registryは、NecroCodeシステムの中核となるタスク管理コンポーネントです。Kiroの`.kiro/specs/{spec-name}/tasks.md`と双方向同期しながら、タスクの状態管理、依存関係の解決、イベント履歴の記録を行います。ファイルベースの永続化とロック機構により、複数のDispatcherとAgent Runnerからの並行アクセスをサポートします。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task Planner ──────► Task Registry ◄────── Dispatcher     │
│                           │                                 │
│                           │                                 │
│  Kiro tasks.md ◄─────────┤                                 │
│                           │                                 │
│                           ▼                                 │
│                    Event Store                              │
│                           │                                 │
│  Agent Runner ────────────┴──────► Artifact Store          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Task Registry                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  TaskRegistry    │      │  KiroSyncManager │           │
│  │  (Main API)      │◄────►│  (tasks.md sync) │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  TaskStore       │      │  EventStore      │           │
│  │  (Persistence)   │      │  (Audit Log)     │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  LockManager     │      │  QueryEngine     │           │
│  │  (Concurrency)   │      │  (Search/Filter) │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. TaskRegistry (Main API)

タスク管理の主要なインターフェースを提供します。

```python
class TaskRegistry:
    """Task Registryのメインクラス"""
    
    def __init__(self, registry_dir: Path):
        """
        Args:
            registry_dir: レジストリデータの保存ディレクトリ
        """
        self.registry_dir = registry_dir
        self.task_store = TaskStore(registry_dir / "tasksets")
        self.event_store = EventStore(registry_dir / "events")
        self.lock_manager = LockManager(registry_dir / "locks")
        self.kiro_sync = KiroSyncManager(self)
        self.query_engine = QueryEngine(self.task_store)
    
    def create_taskset(self, spec_name: str, tasks: List[TaskDefinition]) -> Taskset:
        """新しいタスクセットを作成"""
        pass
    
    def get_taskset(self, spec_name: str) -> Taskset:
        """タスクセットを取得"""
        pass
    
    def update_task_state(
        self, 
        spec_name: str, 
        task_id: str, 
        new_state: TaskState,
        metadata: Optional[Dict] = None
    ) -> None:
        """タスクの状態を更新"""
        pass
    
    def get_ready_tasks(
        self, 
        spec_name: str,
        required_skill: Optional[str] = None
    ) -> List[Task]:
        """実行可能なタスクを取得"""
        pass
    
    def add_artifact(
        self,
        spec_name: str,
        task_id: str,
        artifact_type: ArtifactType,
        uri: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """成果物の参照を追加"""
        pass
    
    def sync_with_kiro(self, spec_name: str) -> SyncResult:
        """Kiro tasks.mdと同期"""
        pass

### 2. TaskStore (Persistence Layer)

タスクセットの永続化を担当します。

```python
class TaskStore:
    """タスクセットの永続化"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_taskset(self, taskset: Taskset) -> None:
        """タスクセットをJSONファイルに保存"""
        # ファイルパス: {storage_dir}/{spec_name}/taskset.json
        pass
    
    def load_taskset(self, spec_name: str) -> Taskset:
        """タスクセットをJSONファイルから読み込み"""
        pass
    
    def list_tasksets(self) -> List[str]:
        """すべてのタスクセット名を取得"""
        pass
    
    def backup_taskset(self, spec_name: str, backup_dir: Path) -> Path:
        """タスクセットをバックアップ"""
        pass
    
    def restore_taskset(self, backup_path: Path) -> str:
        """バックアップから復元"""
        pass

### 3. EventStore (Audit Log)

イベント履歴をJSON Lines形式で記録します。

```python
class EventStore:
    """イベント履歴の記録"""
    
    def __init__(self, events_dir: Path):
        self.events_dir = events_dir
        self.events_dir.mkdir(parents=True, exist_ok=True)
    
    def record_event(self, event: TaskEvent) -> None:
        """イベントを記録"""
        # ファイルパス: {events_dir}/{spec_name}/events.jsonl
        pass
    
    def get_events_by_task(
        self, 
        spec_name: str, 
        task_id: str
    ) -> List[TaskEvent]:
        """特定タスクのイベントを取得"""
        pass
    
    def get_events_by_timerange(
        self,
        spec_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[TaskEvent]:
        """期間内のイベントを取得"""
        pass
    
    def rotate_logs(self, max_size_mb: int = 100) -> None:
        """ログファイルをローテーション"""
        pass

### 4. LockManager (Concurrency Control)

ファイルベースのロック機構を提供します。

```python
class LockManager:
    """並行アクセス制御"""
    
    def __init__(self, locks_dir: Path):
        self.locks_dir = locks_dir
        self.locks_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def acquire_lock(
        self,
        spec_name: str,
        timeout: float = 30.0,
        retry_interval: float = 0.1
    ) -> Generator[None, None, None]:
        """ロックを取得（コンテキストマネージャー）"""
        # ファイルパス: {locks_dir}/{spec_name}.lock
        pass
    
    def is_locked(self, spec_name: str) -> bool:
        """ロック状態を確認"""
        pass
    
    def force_unlock(self, spec_name: str) -> None:
        """強制的にロックを解除（デッドロック対策）"""
        pass

### 5. KiroSyncManager (Kiro Integration)

Kiroの`tasks.md`との双方向同期を管理します。

```python
class KiroSyncManager:
    """Kiro tasks.mdとの同期"""
    
    def __init__(self, registry: TaskRegistry):
        self.registry = registry
    
    def sync_from_kiro(self, spec_name: str) -> SyncResult:
        """tasks.mdからTask Registryへ同期"""
        # 1. tasks.mdを解析
        # 2. チェックボックス状態を読み取り
        # 3. Task Registryの状態を更新
        pass
    
    def sync_to_kiro(self, spec_name: str) -> SyncResult:
        """Task Registryからtasks.mdへ同期"""
        # 1. Task Registryの状態を取得
        # 2. tasks.mdのチェックボックスを更新
        pass
    
    def parse_tasks_md(self, tasks_md_path: Path) -> List[TaskDefinition]:
        """tasks.mdを解析してタスク定義を抽出"""
        pass
    
    def update_tasks_md(
        self,
        tasks_md_path: Path,
        task_states: Dict[str, TaskState]
    ) -> None:
        """tasks.mdのチェックボックスを更新"""
        pass
    
    def extract_dependencies(self, task_text: str) -> List[str]:
        """タスクテキストから依存関係を抽出"""
        # 例: "_Requirements: 1.1, 2.3_" → ["1.1", "2.3"]
        pass

### 6. QueryEngine (Search and Filter)

タスクの検索とフィルタリング機能を提供します。

```python
class QueryEngine:
    """タスクのクエリとフィルタリング"""
    
    def __init__(self, task_store: TaskStore):
        self.task_store = task_store
    
    def filter_by_state(
        self,
        spec_name: str,
        state: TaskState
    ) -> List[Task]:
        """状態でフィルタリング"""
        pass
    
    def filter_by_skill(
        self,
        spec_name: str,
        required_skill: str
    ) -> List[Task]:
        """必要スキルでフィルタリング"""
        pass
    
    def sort_by_priority(
        self,
        tasks: List[Task],
        descending: bool = True
    ) -> List[Task]:
        """優先度でソート"""
        pass
    
    def query(
        self,
        spec_name: str,
        filters: Dict[str, Any],
        sort_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """複合クエリ"""
        pass

## Data Models

### Taskset

```python
@dataclass
class Taskset:
    """タスクセット"""
    spec_name: str
    version: int
    created_at: datetime
    updated_at: datetime
    tasks: List[Task]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Taskset":
        """辞書から復元"""
        pass

### Task

```python
@dataclass
class Task:
    """個別タスク"""
    id: str  # 例: "1.1", "2.3"
    title: str
    description: str
    state: TaskState
    dependencies: List[str]  # 依存タスクのID
    required_skill: Optional[str]
    priority: int
    is_optional: bool  # tasks.mdの*マーク
    
    # 実行時情報
    assigned_slot: Optional[str] = None
    reserved_branch: Optional[str] = None
    runner_id: Optional[str] = None
    
    # 成果物
    artifacts: List[Artifact] = field(default_factory=list)
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

### TaskState

```python
class TaskState(Enum):
    """タスクの状態"""
    READY = "ready"      # 実行可能
    RUNNING = "running"  # 実行中
    BLOCKED = "blocked"  # 依存タスク待ち
    DONE = "done"        # 完了
    FAILED = "failed"    # 失敗

### TaskEvent

```python
@dataclass
class TaskEvent:
    """タスクイベント"""
    event_type: EventType
    spec_name: str
    task_id: str
    timestamp: datetime
    details: Dict[str, Any]
    
    def to_jsonl(self) -> str:
        """JSON Lines形式に変換"""
        pass

### EventType

```python
class EventType(Enum):
    """イベントタイプ"""
    TASK_CREATED = "TaskCreated"
    TASK_UPDATED = "TaskUpdated"
    TASK_READY = "TaskReady"
    TASK_ASSIGNED = "TaskAssigned"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"
    RUNNER_STARTED = "RunnerStarted"
    RUNNER_FINISHED = "RunnerFinished"
    PR_OPENED = "PROpened"
    PR_MERGED = "PRMerged"

### Artifact

```python
@dataclass
class Artifact:
    """成果物の参照"""
    type: ArtifactType
    uri: str
    size_bytes: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

### ArtifactType

```python
class ArtifactType(Enum):
    """成果物のタイプ"""
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"

## File Structure

```
~/.necrocode/registry/
├── tasksets/
│   ├── chat-app/
│   │   └── taskset.json
│   ├── iot-dashboard/
│   │   └── taskset.json
│   └── ...
├── events/
│   ├── chat-app/
│   │   ├── events.jsonl
│   │   └── events.jsonl.1  # ローテーション後
│   └── ...
└── locks/
    ├── chat-app.lock
    └── ...
```

### taskset.json Example

```json
{
  "spec_name": "chat-app",
  "version": 3,
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T12:30:00Z",
  "tasks": [
    {
      "id": "1.1",
      "title": "Setup database schema",
      "description": "Create User and Message models",
      "state": "done",
      "dependencies": [],
      "required_skill": "backend",
      "priority": 1,
      "is_optional": false,
      "assigned_slot": "workspace-chat-app-slot1",
      "reserved_branch": "feature/task-chat-app-1.1",
      "runner_id": "runner-backend-1",
      "artifacts": [
        {
          "type": "diff",
          "uri": "file://~/.necrocode/artifacts/chat-app/1.1/changes.diff",
          "size_bytes": 2048,
          "created_at": "2025-11-15T11:00:00Z"
        }
      ],
      "metadata": {
        "acceptance": ["User model created", "Message model created"]
      },
      "created_at": "2025-11-15T10:00:00Z",
      "updated_at": "2025-11-15T11:00:00Z"
    }
  ],
  "metadata": {
    "kiro_spec_path": ".kiro/specs/chat-app/tasks.md"
  }
}
```

### events.jsonl Example

```jsonl
{"event_type":"TaskCreated","spec_name":"chat-app","task_id":"1.1","timestamp":"2025-11-15T10:00:00Z","details":{"title":"Setup database schema"}}
{"event_type":"TaskAssigned","spec_name":"chat-app","task_id":"1.1","timestamp":"2025-11-15T10:30:00Z","details":{"runner_id":"runner-backend-1","slot":"workspace-chat-app-slot1"}}
{"event_type":"RunnerStarted","spec_name":"chat-app","task_id":"1.1","timestamp":"2025-11-15T10:31:00Z","details":{"runner_id":"runner-backend-1"}}
{"event_type":"TaskCompleted","spec_name":"chat-app","task_id":"1.1","timestamp":"2025-11-15T11:00:00Z","details":{"duration_seconds":1740}}
```

## Error Handling

### Exception Hierarchy

```python
class TaskRegistryError(Exception):
    """Base exception for Task Registry"""
    pass

class TaskNotFoundError(TaskRegistryError):
    """Task not found"""
    pass

class TasksetNotFoundError(TaskRegistryError):
    """Taskset not found"""
    pass

class InvalidStateTransitionError(TaskRegistryError):
    """Invalid state transition"""
    pass

class CircularDependencyError(TaskRegistryError):
    """Circular dependency detected"""
    pass

class LockTimeoutError(TaskRegistryError):
    """Lock acquisition timeout"""
    pass

class SyncError(TaskRegistryError):
    """Kiro sync error"""
    pass
```

### Error Handling Strategy

1. **ロック取得失敗**: リトライ後、タイムアウトで例外
2. **状態遷移エラー**: 即座に例外を投げ、呼び出し元で処理
3. **ファイルI/Oエラー**: 3回リトライ後、例外
4. **同期エラー**: エラーログを記録し、部分的な同期を許可

## Testing Strategy

### Unit Tests

- `test_task_store.py`: TaskStoreの永続化機能
- `test_event_store.py`: EventStoreのログ記録
- `test_lock_manager.py`: LockManagerの並行制御
- `test_kiro_sync.py`: KiroSyncManagerの同期機能
- `test_query_engine.py`: QueryEngineの検索機能

### Integration Tests

- `test_task_registry_integration.py`: コンポーネント間の連携
- `test_kiro_sync_integration.py`: tasks.mdとの実際の同期
- `test_concurrent_access.py`: 複数プロセスからの同時アクセス

### Performance Tests

- `test_large_taskset.py`: 1000タスク以上の大規模タスクセット
- `test_event_log_performance.py`: イベントログの書き込み性能

## Dependencies

```python
# requirements.txt
pyyaml>=6.0
python-dateutil>=2.8.0
filelock>=3.12.0  # ファイルロック
```

## Configuration

```python
@dataclass
class RegistryConfig:
    """Task Registry設定"""
    registry_dir: Path = Path.home() / ".necrocode" / "registry"
    lock_timeout: float = 30.0
    lock_retry_interval: float = 0.1
    event_log_max_size_mb: int = 100
    backup_enabled: bool = True
    backup_interval_hours: int = 24
```

## Future Enhancements

1. **SQLiteバックエンド**: 大規模タスクセット向けの高速クエリ
2. **リモート同期**: 複数マシン間でのTask Registry共有
3. **Webhookサポート**: イベント発生時の外部通知
4. **メトリクス収集**: タスク実行時間、成功率などの統計
5. **GraphQL API**: 柔軟なクエリインターフェース

# Task Registry

Task Registryは、NecroCodeシステムにおけるタスクの状態管理、バージョン管理、イベント履歴を一元管理する永続ストレージコンポーネントです。

## 概要

Task Registryは以下の機能を提供します：

- **タスクセット管理**: 複数のタスクセットをJSON形式で永続化
- **状態管理**: タスクの状態遷移（Ready/Running/Blocked/Done）を追跡
- **依存関係解決**: タスク間の依存関係を管理し、実行順序を制御
- **イベント履歴**: すべてのタスクイベントを時系列で記録
- **Kiro同期**: `.kiro/specs/{spec-name}/tasks.md`との双方向同期
- **並行アクセス制御**: ファイルベースのロック機構で整合性を保証
- **成果物管理**: タスク実行の成果物（diff、ログ、テスト結果）への参照を保存

## インストール

```bash
# 依存パッケージのインストール
pip install pyyaml python-dateutil filelock
```

## クイックスタート

### 基本的な使用例

```python
from pathlib import Path
from necrocode.task_registry import TaskRegistry, Task, TaskState

# Task Registryの初期化
registry = TaskRegistry(registry_dir=Path.home() / ".necrocode" / "registry")

# タスクセットの作成
tasks = [
    Task(
        id="1.1",
        title="Setup database schema",
        description="Create User and Message models",
        state=TaskState.READY,
        dependencies=[],
        required_skill="backend",
        priority=1
    ),
    Task(
        id="1.2",
        title="Implement JWT authentication",
        description="Add login/register endpoints",
        state=TaskState.BLOCKED,
        dependencies=["1.1"],
        required_skill="backend",
        priority=1
    )
]

taskset = registry.create_taskset(spec_name="chat-app", tasks=tasks)
print(f"Created taskset: {taskset.spec_name} v{taskset.version}")

# タスクの状態を更新
registry.update_task_state(
    spec_name="chat-app",
    task_id="1.1",
    new_state=TaskState.RUNNING,
    metadata={
        "assigned_slot": "workspace-chat-app-slot1",
        "runner_id": "runner-backend-1"
    }
)

# 実行可能なタスクを取得
ready_tasks = registry.get_ready_tasks(spec_name="chat-app")
for task in ready_tasks:
    print(f"Ready: {task.id} - {task.title}")

# 成果物の追加
registry.add_artifact(
    spec_name="chat-app",
    task_id="1.1",
    artifact_type="diff",
    uri="file://~/.necrocode/artifacts/chat-app/1.1/changes.diff",
    metadata={"size_bytes": 2048}
)
```

### Kiro tasks.mdとの同期

```python
from necrocode.task_registry import TaskRegistry

registry = TaskRegistry()

# tasks.mdからTask Registryへ同期
result = registry.sync_with_kiro(spec_name="chat-app", direction="from_kiro")
print(f"Synced {result.tasks_updated} tasks from Kiro")

# Task Registryからtasks.mdへ同期
result = registry.sync_with_kiro(spec_name="chat-app", direction="to_kiro")
print(f"Updated {result.tasks_updated} checkboxes in tasks.md")
```

### イベント履歴の取得

```python
# 特定タスクのイベントを取得
events = registry.event_store.get_events_by_task(
    spec_name="chat-app",
    task_id="1.1"
)
for event in events:
    print(f"{event.timestamp}: {event.event_type} - {event.details}")

# 期間内のイベントを取得
from datetime import datetime, timedelta
start = datetime.now() - timedelta(days=7)
end = datetime.now()
events = registry.event_store.get_events_by_timerange(
    spec_name="chat-app",
    start_time=start,
    end_time=end
)
```

### クエリとフィルタリング

```python
# 状態でフィルタリング
running_tasks = registry.query_engine.filter_by_state(
    spec_name="chat-app",
    state=TaskState.RUNNING
)

# 必要スキルでフィルタリング
backend_tasks = registry.query_engine.filter_by_skill(
    spec_name="chat-app",
    required_skill="backend"
)

# 複合クエリ
tasks = registry.query_engine.query(
    spec_name="chat-app",
    filters={
        "state": TaskState.READY,
        "required_skill": "backend"
    },
    sort_by="priority",
    limit=10
)
```

### 並行アクセス

```python
from necrocode.task_registry import TaskRegistry

# 複数プロセスから安全にアクセス
registry = TaskRegistry()

with registry.lock_manager.acquire_lock(spec_name="chat-app", timeout=30.0):
    # ロックを取得してタスクを更新
    taskset = registry.get_taskset("chat-app")
    taskset.version += 1
    registry.task_store.save_taskset(taskset)
```

## アーキテクチャ

### コンポーネント構成

```
TaskRegistry (Main API)
    ├── TaskStore (Persistence)
    ├── EventStore (Audit Log)
    ├── LockManager (Concurrency Control)
    ├── KiroSyncManager (Kiro Integration)
    └── QueryEngine (Search/Filter)
```

### データモデル

#### Taskset
タスクセット全体を表すモデル

```python
@dataclass
class Taskset:
    spec_name: str              # Spec名
    version: int                # バージョン番号
    created_at: datetime        # 作成日時
    updated_at: datetime        # 更新日時
    tasks: List[Task]           # タスクのリスト
    metadata: Dict[str, Any]    # メタデータ
```

#### Task
個別タスクを表すモデル

```python
@dataclass
class Task:
    id: str                     # タスクID（例: "1.1", "2.3"）
    title: str                  # タイトル
    description: str            # 説明
    state: TaskState            # 状態（Ready/Running/Blocked/Done）
    dependencies: List[str]     # 依存タスクのID
    required_skill: Optional[str]  # 必要スキル
    priority: int               # 優先度
    is_optional: bool           # オプショナルフラグ
    
    # 実行時情報
    assigned_slot: Optional[str]      # 割り当てられたスロット
    reserved_branch: Optional[str]    # 予約されたブランチ
    runner_id: Optional[str]          # 実行中のRunner ID
    
    # 成果物
    artifacts: List[Artifact]   # 成果物のリスト
    
    # メタデータ
    metadata: Dict[str, Any]    # 追加のメタデータ
    created_at: datetime        # 作成日時
    updated_at: datetime        # 更新日時
```

#### TaskState
タスクの状態を表す列挙型

```python
class TaskState(Enum):
    READY = "ready"      # 実行可能
    RUNNING = "running"  # 実行中
    BLOCKED = "blocked"  # 依存タスク待ち
    DONE = "done"        # 完了
    FAILED = "failed"    # 失敗
```

#### TaskEvent
タスクイベントを表すモデル

```python
@dataclass
class TaskEvent:
    event_type: EventType       # イベントタイプ
    spec_name: str              # Spec名
    task_id: str                # タスクID
    timestamp: datetime         # タイムスタンプ
    details: Dict[str, Any]     # 詳細情報
```

#### Artifact
成果物の参照を表すモデル

```python
@dataclass
class Artifact:
    type: ArtifactType          # タイプ（diff/log/test）
    uri: str                    # URI
    size_bytes: Optional[int]   # サイズ（バイト）
    created_at: datetime        # 作成日時
    metadata: Dict[str, Any]    # メタデータ
```

### ファイル構造

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

## API リファレンス

### TaskRegistry

#### `__init__(registry_dir: Path)`
Task Registryを初期化します。

**Parameters:**
- `registry_dir`: レジストリデータの保存ディレクトリ

#### `create_taskset(spec_name: str, tasks: List[Task]) -> Taskset`
新しいタスクセットを作成します。

**Parameters:**
- `spec_name`: Spec名
- `tasks`: タスクのリスト

**Returns:**
- 作成されたTaskset

#### `get_taskset(spec_name: str) -> Taskset`
タスクセットを取得します。

**Parameters:**
- `spec_name`: Spec名

**Returns:**
- Taskset

**Raises:**
- `TasksetNotFoundError`: タスクセットが見つからない場合

#### `update_task_state(spec_name: str, task_id: str, new_state: TaskState, metadata: Optional[Dict] = None) -> None`
タスクの状態を更新します。

**Parameters:**
- `spec_name`: Spec名
- `task_id`: タスクID
- `new_state`: 新しい状態
- `metadata`: 追加のメタデータ（オプション）

**Raises:**
- `TaskNotFoundError`: タスクが見つからない場合
- `InvalidStateTransitionError`: 無効な状態遷移の場合

#### `get_ready_tasks(spec_name: str, required_skill: Optional[str] = None) -> List[Task]`
実行可能なタスクを取得します。

**Parameters:**
- `spec_name`: Spec名
- `required_skill`: 必要スキルでフィルタリング（オプション）

**Returns:**
- Ready状態のタスクのリスト

#### `add_artifact(spec_name: str, task_id: str, artifact_type: str, uri: str, metadata: Optional[Dict] = None) -> None`
成果物の参照を追加します。

**Parameters:**
- `spec_name`: Spec名
- `task_id`: タスクID
- `artifact_type`: 成果物のタイプ（"diff", "log", "test"）
- `uri`: 成果物のURI
- `metadata`: メタデータ（オプション）

#### `sync_with_kiro(spec_name: str, direction: str = "bidirectional") -> SyncResult`
Kiro tasks.mdと同期します。

**Parameters:**
- `spec_name`: Spec名
- `direction`: 同期方向（"from_kiro", "to_kiro", "bidirectional"）

**Returns:**
- SyncResult（同期結果）

### TaskStore

#### `save_taskset(taskset: Taskset) -> None`
タスクセットをJSONファイルに保存します。

#### `load_taskset(spec_name: str) -> Taskset`
タスクセットをJSONファイルから読み込みます。

#### `list_tasksets() -> List[str]`
すべてのタスクセット名を取得します。

#### `backup_taskset(spec_name: str, backup_dir: Path) -> Path`
タスクセットをバックアップします。

#### `restore_taskset(backup_path: Path) -> str`
バックアップから復元します。

### EventStore

#### `record_event(event: TaskEvent) -> None`
イベントを記録します。

#### `get_events_by_task(spec_name: str, task_id: str) -> List[TaskEvent]`
特定タスクのイベントを取得します。

#### `get_events_by_timerange(spec_name: str, start_time: datetime, end_time: datetime) -> List[TaskEvent]`
期間内のイベントを取得します。

#### `rotate_logs(max_size_mb: int = 100) -> None`
ログファイルをローテーションします。

### LockManager

#### `acquire_lock(spec_name: str, timeout: float = 30.0, retry_interval: float = 0.1) -> ContextManager`
ロックを取得します（コンテキストマネージャー）。

**Parameters:**
- `spec_name`: Spec名
- `timeout`: タイムアウト（秒）
- `retry_interval`: リトライ間隔（秒）

**Usage:**
```python
with lock_manager.acquire_lock("chat-app", timeout=30.0):
    # ロックを取得して処理
    pass
```

#### `is_locked(spec_name: str) -> bool`
ロック状態を確認します。

#### `force_unlock(spec_name: str) -> None`
強制的にロックを解除します（デッドロック対策）。

### KiroSyncManager

#### `sync_from_kiro(spec_name: str) -> SyncResult`
tasks.mdからTask Registryへ同期します。

#### `sync_to_kiro(spec_name: str) -> SyncResult`
Task Registryからtasks.mdへ同期します。

#### `parse_tasks_md(tasks_md_path: Path) -> List[TaskDefinition]`
tasks.mdを解析してタスク定義を抽出します。

#### `update_tasks_md(tasks_md_path: Path, task_states: Dict[str, TaskState]) -> None`
tasks.mdのチェックボックスを更新します。

### QueryEngine

#### `filter_by_state(spec_name: str, state: TaskState) -> List[Task]`
状態でフィルタリングします。

#### `filter_by_skill(spec_name: str, required_skill: str) -> List[Task]`
必要スキルでフィルタリングします。

#### `sort_by_priority(tasks: List[Task], descending: bool = True) -> List[Task]`
優先度でソートします。

#### `query(spec_name: str, filters: Dict[str, Any], sort_by: Optional[str] = None, limit: Optional[int] = None, offset: int = 0) -> List[Task]`
複合クエリを実行します。

## 設定

### RegistryConfig

```python
from necrocode.task_registry import RegistryConfig
from pathlib import Path

config = RegistryConfig(
    registry_dir=Path.home() / ".necrocode" / "registry",
    lock_timeout=30.0,
    lock_retry_interval=0.1,
    event_log_max_size_mb=100,
    backup_enabled=True,
    backup_interval_hours=24
)

registry = TaskRegistry(registry_dir=config.registry_dir)
```

## エラーハンドリング

### 例外階層

```python
TaskRegistryError              # ベース例外
├── TaskNotFoundError          # タスクが見つからない
├── TasksetNotFoundError       # タスクセットが見つからない
├── InvalidStateTransitionError # 無効な状態遷移
├── CircularDependencyError    # 循環依存
├── LockTimeoutError           # ロック取得タイムアウト
└── SyncError                  # Kiro同期エラー
```

### エラーハンドリングの例

```python
from necrocode.task_registry import (
    TaskRegistry,
    TaskNotFoundError,
    InvalidStateTransitionError,
    LockTimeoutError
)

registry = TaskRegistry()

try:
    registry.update_task_state("chat-app", "1.1", TaskState.DONE)
except TaskNotFoundError:
    print("Task not found")
except InvalidStateTransitionError as e:
    print(f"Invalid state transition: {e}")
except LockTimeoutError:
    print("Could not acquire lock")
```

## ベストプラクティス

### 1. ロックの使用

並行アクセスが予想される場合は、必ずロックを使用してください：

```python
with registry.lock_manager.acquire_lock("chat-app"):
    taskset = registry.get_taskset("chat-app")
    # タスクセットを更新
    registry.task_store.save_taskset(taskset)
```

### 2. イベントの記録

重要な操作の前後でイベントを記録してください：

```python
# タスク開始前
registry.event_store.record_event(TaskEvent(
    event_type=EventType.TASK_ASSIGNED,
    spec_name="chat-app",
    task_id="1.1",
    timestamp=datetime.now(),
    details={"runner_id": "runner-1"}
))

# タスク実行

# タスク完了後
registry.event_store.record_event(TaskEvent(
    event_type=EventType.TASK_COMPLETED,
    spec_name="chat-app",
    task_id="1.1",
    timestamp=datetime.now(),
    details={"duration_seconds": 120}
))
```

### 3. 依存関係の検証

タスクセット作成時に依存関係を検証してください：

```python
from necrocode.task_registry import validate_dependencies

tasks = [...]  # タスクのリスト
try:
    validate_dependencies(tasks)
except CircularDependencyError as e:
    print(f"Circular dependency detected: {e}")
```

### 4. 定期的なバックアップ

重要なタスクセットは定期的にバックアップしてください：

```python
backup_path = registry.task_store.backup_taskset(
    spec_name="chat-app",
    backup_dir=Path("./backups")
)
print(f"Backup created: {backup_path}")
```

## トラブルシューティング

### ロックが解放されない

デッドロックが発生した場合は、強制的にロックを解除できます：

```python
registry.lock_manager.force_unlock("chat-app")
```

### イベントログが大きくなりすぎる

ログローテーションを実行してください：

```python
registry.event_store.rotate_logs(max_size_mb=100)
```

### Kiro同期が失敗する

tasks.mdのフォーマットを確認してください。チェックボックスとタスク番号が正しい形式であることを確認してください：

```markdown
- [ ] 1.1 タスクタイトル
  - タスクの説明
  - _Requirements: 1.1, 2.3_
```

## パフォーマンス

### 推奨事項

- **大規模タスクセット**: 1000タスク以上の場合、クエリにインデックスを使用
- **イベントログ**: 定期的にローテーションして検索性能を維持
- **並行アクセス**: ロックのタイムアウトを適切に設定

### ベンチマーク

- タスクセット保存: ~10ms（100タスク）
- タスクセット読み込み: ~5ms（100タスク）
- イベント記録: ~1ms
- イベント検索: ~50ms（10,000イベント）

## 関連ドキュメント

- [Design Document](design.md) - アーキテクチャと設計の詳細
- [Requirements Document](requirements.md) - 要件定義
- [Tasks Document](tasks.md) - 実装タスクリスト
- [Graph Visualization](GRAPH_VISUALIZATION.md) - 依存関係グラフの可視化

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題が発生した場合は、GitHubのIssueを作成してください。

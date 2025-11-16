# Repo Pool Manager Design Document

## Overview

Repo Pool Managerは、ローカルマシン上に複数のリポジトリクローン（スロット）を管理し、Agent Runnerへの効率的な割当・返却・クリーンアップを提供します。ファイルベースのロック機構により並行アクセスを制御し、Git操作を抽象化することでAgent Runnerの実装を簡素化します。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Dispatcher ──────► Repo Pool Manager ◄────── Agent Runner │
│                           │                                 │
│                           │                                 │
│                           ▼                                 │
│                    File System                              │
│                  ~/.necrocode/workspaces/                   │
│                    ├── repo1/                               │
│                    │   ├── slot1/                           │
│                    │   ├── slot2/                           │
│                    │   └── slot3/                           │
│                    └── repo2/                               │
│                        ├── slot1/                           │
│                        └── slot2/                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Repo Pool Manager                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  PoolManager     │      │  SlotAllocator   │           │
│  │  (Main API)      │◄────►│  (Allocation)    │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  SlotStore       │      │  GitOperations   │           │
│  │  (Persistence)   │      │  (Git Commands)  │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  SlotCleaner     │      │  LockManager     │           │
│  │  (Cleanup)       │      │  (Concurrency)   │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. PoolManager (Main API)

プール管理の主要なインターフェースを提供します。

```python
class PoolManager:
    """Repo Pool Managerのメインクラス"""
    
    def __init__(self, config: PoolConfig):
        """
        Args:
            config: プール設定
        """
        self.config = config
        self.workspaces_dir = config.workspaces_dir
        self.slot_store = SlotStore(self.workspaces_dir)
        self.slot_allocator = SlotAllocator(self.slot_store)
        self.slot_cleaner = SlotCleaner()
        self.git_ops = GitOperations()
        self.lock_manager = LockManager(self.workspaces_dir / "locks")
    
    def create_pool(
        self,
        repo_name: str,
        repo_url: str,
        num_slots: int
    ) -> Pool:
        """新しいプールを作成"""
        pass
    
    def get_pool(self, repo_name: str) -> Pool:
        """プールを取得"""
        pass
    
    def list_pools(self) -> List[str]:
        """すべてのプール名を取得"""
        pass
    
    def allocate_slot(self, repo_name: str) -> Optional[Slot]:
        """利用可能なスロットを割り当て"""
        pass
    
    def release_slot(self, slot_id: str) -> None:
        """スロットを返却"""
        pass
    
    def get_slot_status(self, slot_id: str) -> SlotStatus:
        """スロットの状態を取得"""
        pass
    
    def get_pool_summary(self) -> Dict[str, PoolSummary]:
        """すべてのプールのサマリーを取得"""
        pass

### 2. SlotAllocator (Allocation Strategy)

スロットの割当戦略を実装します。

```python
class SlotAllocator:
    """スロット割当戦略"""
    
    def __init__(self, slot_store: SlotStore):
        self.slot_store = slot_store
        self.lru_cache: Dict[str, List[str]] = {}  # repo_name -> [slot_id]
    
    def find_available_slot(self, repo_name: str) -> Optional[Slot]:
        """利用可能なスロットを検索（LRU戦略）"""
        pass
    
    def mark_allocated(self, slot_id: str, metadata: Dict) -> None:
        """スロットをAllocated状態にマーク"""
        pass
    
    def mark_available(self, slot_id: str) -> None:
        """スロットをAvailable状態にマーク"""
        pass
    
    def update_lru_cache(self, repo_name: str, slot_id: str) -> None:
        """LRUキャッシュを更新"""
        pass
    
    def get_allocation_metrics(self, repo_name: str) -> AllocationMetrics:
        """割当メトリクスを取得"""
        pass

### 3. SlotStore (Persistence Layer)

スロットのメタデータと状態を永続化します。

```python
class SlotStore:
    """スロットの永続化"""
    
    def __init__(self, workspaces_dir: Path):
        self.workspaces_dir = workspaces_dir
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
    
    def save_pool(self, pool: Pool) -> None:
        """プール情報を保存"""
        # ファイルパス: {workspaces_dir}/{repo_name}/pool.json
        pass
    
    def load_pool(self, repo_name: str) -> Pool:
        """プール情報を読み込み"""
        pass
    
    def save_slot(self, slot: Slot) -> None:
        """スロット情報を保存"""
        # ファイルパス: {workspaces_dir}/{repo_name}/{slot_id}/slot.json
        pass
    
    def load_slot(self, slot_id: str) -> Slot:
        """スロット情報を読み込み"""
        pass
    
    def list_slots(self, repo_name: str) -> List[Slot]:
        """プール内のすべてのスロットを取得"""
        pass
    
    def delete_slot(self, slot_id: str) -> None:
        """スロットを削除"""
        pass

### 4. SlotCleaner (Cleanup Operations)

スロットのクリーンアップ処理を実行します。

```python
class SlotCleaner:
    """スロットのクリーンアップ"""
    
    def __init__(self):
        self.cleanup_log: List[CleanupRecord] = []
    
    def cleanup_before_allocation(self, slot: Slot) -> CleanupResult:
        """割当前のクリーンアップ"""
        # 1. git fetch --all
        # 2. git clean -fdx
        # 3. git reset --hard
        pass
    
    def cleanup_after_release(self, slot: Slot) -> CleanupResult:
        """返却後のクリーンアップ"""
        pass
    
    def warmup_slot(self, slot: Slot) -> None:
        """スロットの事前ウォームアップ"""
        pass
    
    def verify_slot_integrity(self, slot: Slot) -> bool:
        """スロットの整合性を検証"""
        pass
    
    def repair_slot(self, slot: Slot) -> RepairResult:
        """破損したスロットを修復"""
        pass
    
    def get_cleanup_log(self, slot_id: str) -> List[CleanupRecord]:
        """クリーンアップログを取得"""
        pass

### 5. GitOperations (Git Command Abstraction)

Git操作を抽象化します。

```python
class GitOperations:
    """Git操作の抽象化"""
    
    def clone_repo(self, repo_url: str, target_dir: Path) -> GitResult:
        """リポジトリをクローン"""
        pass
    
    def fetch_all(self, repo_dir: Path) -> GitResult:
        """すべてのリモートブランチをフェッチ"""
        pass
    
    def clean(self, repo_dir: Path, force: bool = True) -> GitResult:
        """未追跡ファイルを削除"""
        pass
    
    def reset_hard(self, repo_dir: Path, ref: str = "HEAD") -> GitResult:
        """ワーキングディレクトリをリセット"""
        pass
    
    def checkout(self, repo_dir: Path, branch: str) -> GitResult:
        """ブランチをチェックアウト"""
        pass
    
    def get_current_branch(self, repo_dir: Path) -> str:
        """現在のブランチ名を取得"""
        pass
    
    def get_current_commit(self, repo_dir: Path) -> str:
        """現在のコミットハッシュを取得"""
        pass
    
    def list_remote_branches(self, repo_dir: Path) -> List[str]:
        """リモートブランチの一覧を取得"""
        pass
    
    def is_clean_working_tree(self, repo_dir: Path) -> bool:
        """ワーキングツリーがクリーンか確認"""
        pass

### 6. LockManager (Concurrency Control)

スロットのロック機構を提供します。

```python
class LockManager:
    """スロットのロック管理"""
    
    def __init__(self, locks_dir: Path):
        self.locks_dir = locks_dir
        self.locks_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def acquire_slot_lock(
        self,
        slot_id: str,
        timeout: float = 30.0
    ) -> Generator[None, None, None]:
        """スロットロックを取得（コンテキストマネージャー）"""
        # ファイルパス: {locks_dir}/{slot_id}.lock
        pass
    
    def is_locked(self, slot_id: str) -> bool:
        """スロットがロックされているか確認"""
        pass
    
    def force_unlock(self, slot_id: str) -> None:
        """強制的にロックを解除"""
        pass
    
    def detect_stale_locks(self, max_age_hours: int = 24) -> List[str]:
        """古いロックを検出"""
        pass
    
    def cleanup_stale_locks(self, max_age_hours: int = 24) -> int:
        """古いロックを削除"""
        pass

## Data Models

### Pool

```python
@dataclass
class Pool:
    """リポジトリプール"""
    repo_name: str
    repo_url: str
    num_slots: int
    slots: List[Slot]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_available_slots(self) -> List[Slot]:
        """利用可能なスロットを取得"""
        pass
    
    def get_allocated_slots(self) -> List[Slot]:
        """割り当て済みスロットを取得"""
        pass
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        pass
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Pool":
        """辞書から復元"""
        pass

### Slot

```python
@dataclass
class Slot:
    """ワークスペーススロット"""
    slot_id: str  # 例: "workspace-chat-app-slot1"
    repo_name: str
    repo_url: str
    slot_path: Path
    state: SlotState
    
    # 使用統計
    allocation_count: int = 0
    total_usage_seconds: int = 0
    last_allocated_at: Optional[datetime] = None
    last_released_at: Optional[datetime] = None
    
    # Git情報
    current_branch: Optional[str] = None
    current_commit: Optional[str] = None
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def is_available(self) -> bool:
        """利用可能か確認"""
        return self.state == SlotState.AVAILABLE
    
    def mark_allocated(self, metadata: Optional[Dict] = None) -> None:
        """割り当て済みにマーク"""
        pass
    
    def mark_released(self) -> None:
        """返却済みにマーク"""
        pass

### SlotState

```python
class SlotState(Enum):
    """スロットの状態"""
    AVAILABLE = "available"  # 利用可能
    ALLOCATED = "allocated"  # 割り当て済み
    CLEANING = "cleaning"    # クリーンアップ中
    ERROR = "error"          # エラー状態

### SlotStatus

```python
@dataclass
class SlotStatus:
    """スロットの詳細状態"""
    slot_id: str
    state: SlotState
    is_locked: bool
    current_branch: Optional[str]
    current_commit: Optional[str]
    allocation_count: int
    last_allocated_at: Optional[datetime]
    disk_usage_mb: float

### PoolSummary

```python
@dataclass
class PoolSummary:
    """プールのサマリー"""
    repo_name: str
    total_slots: int
    available_slots: int
    allocated_slots: int
    cleaning_slots: int
    error_slots: int
    total_allocations: int
    average_allocation_time_seconds: float

### CleanupResult

```python
@dataclass
class CleanupResult:
    """クリーンアップ結果"""
    slot_id: str
    success: bool
    duration_seconds: float
    operations: List[str]  # ["fetch", "clean", "reset"]
    errors: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

### GitResult

```python
@dataclass
class GitResult:
    """Git操作の結果"""
    success: bool
    command: str
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float

### AllocationMetrics

```python
@dataclass
class AllocationMetrics:
    """割当メトリクス"""
    repo_name: str
    total_allocations: int
    average_allocation_time_seconds: float
    cache_hit_rate: float
    failed_allocations: int

## File Structure

```
~/.necrocode/workspaces/
├── chat-app/
│   ├── pool.json
│   ├── slot1/
│   │   ├── .git/
│   │   ├── slot.json
│   │   └── ... (リポジトリの内容)
│   ├── slot2/
│   │   ├── .git/
│   │   ├── slot.json
│   │   └── ...
│   └── slot3/
│       ├── .git/
│       ├── slot.json
│       └── ...
├── iot-dashboard/
│   ├── pool.json
│   ├── slot1/
│   └── slot2/
└── locks/
    ├── workspace-chat-app-slot1.lock
    └── workspace-iot-dashboard-slot1.lock
```

### pool.json Example

```json
{
  "repo_name": "chat-app",
  "repo_url": "https://github.com/user/chat-app.git",
  "num_slots": 3,
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T12:00:00Z",
  "metadata": {
    "default_branch": "main"
  }
}
```

### slot.json Example

```json
{
  "slot_id": "workspace-chat-app-slot1",
  "repo_name": "chat-app",
  "repo_url": "https://github.com/user/chat-app.git",
  "slot_path": "/Users/user/.necrocode/workspaces/chat-app/slot1",
  "state": "available",
  "allocation_count": 5,
  "total_usage_seconds": 3600,
  "last_allocated_at": "2025-11-15T11:00:00Z",
  "last_released_at": "2025-11-15T11:30:00Z",
  "current_branch": "main",
  "current_commit": "abc123def456",
  "metadata": {},
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T11:30:00Z"
}
```

## Configuration

### Pool Configuration File

```yaml
# ~/.necrocode/config/pools.yaml
pools:
  chat-app:
    repo_url: https://github.com/user/chat-app.git
    num_slots: 3
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
  
  iot-dashboard:
    repo_url: https://github.com/user/iot-dashboard.git
    num_slots: 2
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: true

defaults:
  num_slots: 2
  lock_timeout: 30.0
  cleanup_timeout: 60.0
  stale_lock_hours: 24
```

### PoolConfig Class

```python
@dataclass
class PoolConfig:
    """プール設定"""
    workspaces_dir: Path = Path.home() / ".necrocode" / "workspaces"
    config_file: Path = Path.home() / ".necrocode" / "config" / "pools.yaml"
    default_num_slots: int = 2
    lock_timeout: float = 30.0
    cleanup_timeout: float = 60.0
    stale_lock_hours: int = 24
    enable_metrics: bool = True
```

## Error Handling

### Exception Hierarchy

```python
class PoolManagerError(Exception):
    """Base exception for Pool Manager"""
    pass

class PoolNotFoundError(PoolManagerError):
    """Pool not found"""
    pass

class SlotNotFoundError(PoolManagerError):
    """Slot not found"""
    pass

class NoAvailableSlotError(PoolManagerError):
    """No available slot"""
    pass

class SlotAllocationError(PoolManagerError):
    """Slot allocation failed"""
    pass

class GitOperationError(PoolManagerError):
    """Git operation failed"""
    pass

class CleanupError(PoolManagerError):
    """Cleanup operation failed"""
    pass

class LockTimeoutError(PoolManagerError):
    """Lock acquisition timeout"""
    pass
```

### Error Handling Strategy

1. **Git操作失敗**: 3回リトライ後、GitOperationErrorを投げる
2. **スロット割当失敗**: 他のスロットを試行、すべて失敗でNoAvailableSlotError
3. **クリーンアップ失敗**: エラーログを記録し、スロットをERROR状態にマーク
4. **ロック取得失敗**: タイムアウト後、LockTimeoutErrorを投げる

## Testing Strategy

### Unit Tests

- `test_pool_manager.py`: PoolManagerの基本機能
- `test_slot_allocator.py`: SlotAllocatorの割当戦略
- `test_slot_store.py`: SlotStoreの永続化
- `test_slot_cleaner.py`: SlotCleanerのクリーンアップ
- `test_git_operations.py`: GitOperationsのGitコマンド
- `test_lock_manager.py`: LockManagerのロック機構

### Integration Tests

- `test_pool_lifecycle.py`: プール作成から削除までのライフサイクル
- `test_concurrent_allocation.py`: 複数プロセスからの同時割当
- `test_cleanup_integration.py`: 実際のGitリポジトリでのクリーンアップ

### Performance Tests

- `test_allocation_performance.py`: スロット割当の性能
- `test_cleanup_performance.py`: クリーンアップの性能
- `test_large_pool.py`: 大規模プール（100スロット）の管理

## Dependencies

```python
# requirements.txt
gitpython>=3.1.0
pyyaml>=6.0
filelock>=3.12.0
psutil>=5.9.0  # ディスク使用量の取得
```

## Future Enhancements

1. **リモートワークスペース**: SSH経由でリモートマシンのスロットを管理
2. **スロットプール**: 複数のリポジトリを1つのスロットで管理
3. **スナップショット機能**: スロットの状態をスナップショットとして保存
4. **自動スケーリング**: 需要に応じてスロット数を動的に調整
5. **Webhookサポート**: スロット割当/返却時の外部通知

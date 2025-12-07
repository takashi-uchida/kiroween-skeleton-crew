# Repo Pool Manager

**🚀 Git Worktreeで強化 - 10倍高速な割り当て、90%のディスク容量削減！**

Repo Pool Managerは、NecroCodeシステムにおいて並列エージェント実行のための複数のワークスペーススロットを管理するコンポーネントです。**git worktree**を使用して、効率的な割り当て、クリーンアップ、監視を提供します。

## 概要

Repo Pool Managerは、エージェントに割り当て可能な事前クローンされたgitリポジトリ（スロット）のプールを維持します。これにより、各タスクごとにリポジトリをクローンするオーバーヘッドが排除され、並列実行が可能になります。

## 主な機能

- **Git Worktreeベース**: 効率的な並列実行のためにgit worktreeを使用
- **10倍高速な割り当て**: 1秒未満でスロット作成（クローンの10-30秒と比較）
- **90%のディスク容量削減**: 全スロット間で.gitディレクトリを共有
- **プール管理**: リポジトリworktreeのプールを作成・管理
- **スロット割り当て**: 最適なパフォーマンスのためのLRUベース割り当て戦略
- **自動クリーンアップ**: 割り当て前後のGit操作（fetch、clean、reset）
- **並行制御**: ファイルベースのロックで二重割り当てを防止
- **ステータス監視**: スロット状態、使用統計、プールヘルスを追跡
- **動的スケーリング**: 実行時にスロットを追加・削除
- **100% API互換**: クローンベース実装のドロップイン置換

## アーキテクチャ

```
PoolManager (メインAPI)
    ├── SlotStore (永続化)
    ├── SlotAllocator (割り当て戦略)
    ├── SlotCleaner (クリーンアップ操作)
    ├── GitOperations (Gitコマンド)
    └── LockManager (並行制御)
```

## クイックスタート

```python
from necrocode.repo_pool import PoolManager, PoolConfig
from pathlib import Path

# PoolManagerを初期化
config = PoolConfig(
    workspaces_dir=Path.home() / ".necrocode" / "workspaces",
    lock_timeout=30.0,
)
manager = PoolManager(config)

# 3つのスロットを持つプールを作成
pool = manager.create_pool(
    repo_name="my-project",
    repo_url="https://github.com/user/my-project.git",
    num_slots=3
)

# スロットを割り当て
slot = manager.allocate_slot("my-project")
print(f"割り当て済み: {slot.slot_id}")
print(f"パス: {slot.slot_path}")

# スロットで作業を実行...
# (Git操作、テスト実行など)

# 完了したらスロットを解放
manager.release_slot(slot.slot_id)
```

## APIリファレンス

### PoolManager

プールとスロット管理のメインAPIクラスです。

#### プール管理

```python
# 新しいプールを作成
pool = manager.create_pool(
    repo_name="my-project",
    repo_url="https://github.com/user/my-project.git",
    num_slots=3
)

# 既存のプールを取得
pool = manager.get_pool("my-project")

# 全プールをリスト
pools = manager.list_pools()  # 戻り値: ["my-project", "other-project"]
```

#### スロット割り当て

```python
# スロットを割り当て（自動クリーンアップ付き）
slot = manager.allocate_slot("my-project", metadata={"task_id": "123"})

# スロットを解放（自動クリーンアップ付き）
manager.release_slot(slot.slot_id)

# クリーンアップなしで解放（高速だが安全性は低い）
manager.release_slot(slot.slot_id, cleanup=False)
```

#### ステータス監視

```python
# 詳細なスロットステータスを取得
status = manager.get_slot_status(slot.slot_id)
print(f"状態: {status.state.value}")
print(f"ロック中: {status.is_locked}")
print(f"割り当て回数: {status.allocation_count}")
print(f"ディスク使用量: {status.disk_usage_mb:.2f} MB")

# 全プールのサマリーを取得
summary = manager.get_pool_summary()
for repo_name, pool_summary in summary.items():
    print(f"プール: {repo_name}")
    print(f"  総スロット数: {pool_summary.total_slots}")
    print(f"  利用可能: {pool_summary.available_slots}")
    print(f"  割り当て済み: {pool_summary.allocated_slots}")
```

#### 動的スロット管理

```python
# 既存のプールに新しいスロットを追加
new_slot = manager.add_slot("my-project")

# スロットを削除（割り当て済みでないこと）
manager.remove_slot(slot.slot_id)

# 強制削除（割り当て済みでも削除）
manager.remove_slot(slot.slot_id, force=True)
```

## データモデル

### Slot

単一のワークスペーススロットを表します。

```python
@dataclass
class Slot:
    slot_id: str                    # "workspace-my-project-slot1"
    repo_name: str                  # "my-project"
    repo_url: str                   # リポジトリURL
    slot_path: Path                 # スロットディレクトリへのパス
    state: SlotState                # AVAILABLE, ALLOCATED, CLEANING, ERROR
    
    # 使用統計
    allocation_count: int
    total_usage_seconds: int
    last_allocated_at: Optional[datetime]
    last_released_at: Optional[datetime]
    
    # Git情報
    current_branch: Optional[str]
    current_commit: Optional[str]
```

### SlotState

スロット状態を表す列挙型：

- `AVAILABLE`: 割り当て可能
- `ALLOCATED`: 使用中
- `CLEANING`: クリーンアップ中
- `ERROR`: エラー状態、修復が必要

### Pool

リポジトリのスロットプールを表します。

```python
@dataclass
class Pool:
    repo_name: str
    repo_url: str
    num_slots: int
    slots: List[Slot]
    created_at: datetime
    updated_at: datetime
```

## ファイル構造

```
~/.necrocode/workspaces/
├── my-project/
│   ├── pool.json              # プールメタデータ
│   ├── slot1/
│   │   ├── .git/              # Gitリポジトリ
│   │   ├── slot.json          # スロットメタデータ
│   │   └── ...                # リポジトリファイル
│   ├── slot2/
│   └── slot3/
├── other-project/
│   ├── pool.json
│   ├── slot1/
│   └── slot2/
└── locks/
    ├── workspace-my-project-slot1.lock
    └── workspace-my-project-slot2.lock
```

## 設定

### 設定オブジェクト

```python
@dataclass
class PoolConfig:
    workspaces_dir: Path = Path.home() / ".necrocode" / "workspaces"
    config_file: Path = Path.home() / ".necrocode" / "config" / "pools.yaml"
    default_num_slots: int = 2
    lock_timeout: float = 30.0
    cleanup_timeout: float = 60.0
    stale_lock_hours: int = 24
    enable_metrics: bool = True
```

### YAML設定ファイル

Repo Pool Managerは、管理とデプロイを容易にするためにYAMLファイルからの設定読み込みをサポートしています。

#### 設定ファイル形式

`~/.necrocode/config/pools.yaml`に`pools.yaml`ファイルを作成します：

```yaml
# 全プールに適用されるデフォルト設定
defaults:
  num_slots: 2
  lock_timeout: 30.0
  cleanup_timeout: 60.0
  stale_lock_hours: 24
  enable_metrics: true

# プール定義
pools:
  my-project:
    repo_url: https://github.com/user/my-project.git
    num_slots: 3
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
  
  another-project:
    repo_url: https://github.com/user/another-project.git
    num_slots: 2
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: true
```

#### 設定の読み込み

```python
from necrocode.repo_pool import PoolManager, PoolConfig
from pathlib import Path

# デフォルトの場所から読み込み (~/.necrocode/config/pools.yaml)
config = PoolConfig.load_from_file()

# カスタムの場所から読み込み
config = PoolConfig.load_from_file(Path("custom/pools.yaml"))

# 設定を検証
config.validate()

# 読み込んだ設定でPoolManagerを作成
manager = PoolManager(config)
```

#### プールの自動初期化

設定で定義された全プールを自動的に作成：

```python
# PoolManagerを作成してプールを自動初期化
manager = PoolManager.from_config_file(auto_init_pools=True)

# または作成後に手動で初期化
manager = PoolManager(config)
created_pools = manager.initialize_pools_from_config()
```

#### 動的な設定リロード

再起動せずに実行時に設定をリロード：

```python
# ファイルから設定をリロード
manager.reload_config()

# カスタムファイルからリロード
manager.reload_config(Path("custom/pools.yaml"))
```

#### 設定ウォッチャー

設定変更を自動的に検出して適用：

```python
from necrocode.repo_pool.config import ConfigWatcher

# コールバック付きでウォッチャーを作成
def on_config_change(new_config):
    print(f"設定が更新されました: {len(new_config.pools)} プール")
    manager.reload_config()

watcher = ConfigWatcher(config, on_change=on_config_change)

# 定期的に変更をチェック
while True:
    watcher.check_and_reload()
    time.sleep(60)  # 1分ごとにチェック
```

#### 設定の保存

現在の設定をファイルに保存：

```python
# デフォルトの場所に保存
config.save_to_file()

# カスタムの場所に保存
config.save_to_file(Path("backup/pools.yaml"))
```

#### 設定の検証

設定システムは以下を検証します：
- 数値範囲（num_slots >= 1、タイムアウト > 0）
- 必須フィールド（repo_urlが存在すること）
- プール固有の設定

```python
from necrocode.repo_pool.config import ConfigValidationError

try:
    config.validate()
except ConfigValidationError as e:
    print(f"無効な設定: {e}")
```

## クリーンアップ操作

PoolManagerは自動的にクリーンアップ操作を実行します：

### 割り当て前
1. `git fetch --all` - リモート参照を更新
2. `git clean -fdx` - 追跡されていないファイルを削除
3. `git reset --hard` - 作業ディレクトリをリセット

### 解放後
割り当て前と同じ操作を実行し、次の使用のためにスロットをクリーンな状態にします。

## 並行制御

PoolManagerはファイルベースのロックを使用して、同じスロットへの並行アクセスを防止します：

```python
# ロックは自動的に取得/解放されます
with lock_manager.acquire_slot_lock(slot_id, timeout=30.0):
    # クリティカルセクション - スロットはロックされています
    allocate_slot()
```

### 古いロックの検出

```python
# 24時間以上古いロックを検出
stale_locks = lock_manager.detect_stale_locks(max_age_hours=24)

# 古いロックをクリーンアップ
cleaned = lock_manager.cleanup_stale_locks(max_age_hours=24)
```

## エラーハンドリングとリカバリー

### 例外処理

```python
from necrocode.repo_pool import (
    PoolNotFoundError,
    SlotNotFoundError,
    NoAvailableSlotError,
    SlotAllocationError,
    LockTimeoutError,
)

try:
    slot = manager.allocate_slot("my-project")
except PoolNotFoundError:
    print("プールが存在しません")
except NoAvailableSlotError:
    print("全てのスロットが現在割り当て済みです")
except LockTimeoutError:
    print("タイムアウト内にロックを取得できませんでした")
except SlotAllocationError as e:
    print(f"割り当てに失敗しました: {e}")
```

### 異常検出

様々なシステム異常を検出して処理：

```python
# 全ての異常を検出
anomalies = manager.detect_anomalies(max_allocation_hours=24)

# 特定の異常タイプをチェック
long_allocated = manager.detect_long_allocated_slots(max_allocation_hours=24)
corrupted = manager.detect_corrupted_slots()
orphaned_locks = manager.detect_orphaned_locks()
```

### 自動リカバリー

検出された問題から自動的にリカバリー：

```python
# 自動リカバリーを実行
results = manager.auto_recover(
    max_allocation_hours=24,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)

print(f"解放: {results['long_allocated_released']}")
print(f"リカバリー: {results['corrupted_recovered']}")
print(f"隔離: {results['corrupted_isolated']}")
print(f"ロッククリーンアップ: {results['orphaned_locks_cleaned']}")
```

### 手動リカバリー

個別のスロットをリカバリー：

```python
# 破損したスロットのリカバリーを試行
success = manager.recover_slot(slot_id, force=False)

# 問題のあるスロットを隔離
manager.isolate_slot(slot_id)
```

エラーハンドリングとリカバリーの詳細については、[ERROR_RECOVERY_GUIDE.md](ERROR_RECOVERY_GUIDE.md)を参照してください。

## パフォーマンス最適化

### LRUキャッシュ戦略

SlotAllocatorはLRU（Least Recently Used）キャッシュを使用して、最近使用されたスロットを優先します：

```python
# 割り当てメトリクスを取得
metrics = slot_allocator.get_allocation_metrics("my-project")
print(f"キャッシュヒット率: {metrics.cache_hit_rate:.2%}")
print(f"平均割り当て時間: {metrics.average_allocation_time_seconds:.2f}秒")
```

### スロットのウォームアップ

より高速な割り当てのためにスロットを事前ウォームアップ：

```python
# ウォームアップはgit fetchと整合性チェックを実行
result = slot_cleaner.warmup_slot(slot)
```

## NecroCodeとの統合

Repo Pool Managerは他のNecroCodeコンポーネントと統合されます：

- **Agent Runner**: タスク実行のためにスロットを要求
- **Dispatcher**: 複数のエージェント間でスロット割り当てを調整
- **Workspace Manager**: ワークスペース操作のベースとしてスロットを使用

## 使用例

完全な使用例については、`examples/pool_manager_example.py`を参照してください。

## 要件

- Python 3.11以上
- Git CLI
- filelockライブラリ

## 関連ドキュメント

- [エラーリカバリーガイド](ERROR_RECOVERY_GUIDE.md) - エラーハンドリングとリカバリーの包括的なガイド
- [設定ガイド](CONFIG_GUIDE.md) - 詳細な設定ドキュメント
- [設計ドキュメント](../../.kiro/specs/repo-pool-manager/design.md)
- [要件](../../.kiro/specs/repo-pool-manager/requirements.md)
- [タスクリスト](../../.kiro/specs/repo-pool-manager/tasks.md)
- [使用例](../../examples/) - エラーリカバリーを含む使用例

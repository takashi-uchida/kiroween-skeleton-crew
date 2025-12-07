# Repo Pool Manager設定ガイド

## クイックスタート

### 1. 設定ファイルの作成

`~/.necrocode/config/pools.yaml`を作成：

```yaml
defaults:
  num_slots: 2
  lock_timeout: 30.0
  cleanup_timeout: 60.0
  stale_lock_hours: 24

pools:
  my-project:
    repo_url: https://github.com/user/my-project.git
    num_slots: 3
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
```

### 2. PoolManagerの初期化

```python
from necrocode.repo_pool import PoolManager

# 設定を読み込んでプールを自動初期化
manager = PoolManager.from_config_file(auto_init_pools=True)
```

### 3. プールの使用

```python
# スロットを割り当て
slot = manager.allocate_slot("my-project")

# スロットを使用...

# 完了したら解放
manager.release_slot(slot.slot_id)
```

## 設定リファレンス

### Defaultsセクション

すべてのプールに適用されるグローバル設定：

```yaml
defaults:
  num_slots: 2              # プールごとのデフォルトスロット数
  lock_timeout: 30.0        # ロック取得タイムアウト（秒）
  cleanup_timeout: 60.0     # クリーンアップ操作タイムアウト（秒）
  stale_lock_hours: 24      # ロックが古いと見なされるまでの時間
  enable_metrics: true      # メトリクス収集を有効化
```

### Poolsセクション

個別のプール設定：

```yaml
pools:
  pool-name:
    repo_url: https://github.com/user/repo.git  # 必須
    num_slots: 3                                 # オプション（デフォルトを使用）
    cleanup_options:                             # オプション
      fetch_on_allocate: true                    # 割り当て前にフェッチ
      clean_on_release: true                     # 解放後にクリーン
      warmup_enabled: false                      # スロットのウォームアップを有効化
```

## 一般的なパターン

### 開発環境

```yaml
defaults:
  num_slots: 1
  lock_timeout: 10.0

pools:
  dev-project:
    repo_url: https://github.com/user/dev-project.git
    num_slots: 1
    cleanup_options:
      fetch_on_allocate: false  # 速度のためフェッチをスキップ
      clean_on_release: false
      warmup_enabled: false
```

### 本番環境

```yaml
defaults:
  num_slots: 5
  lock_timeout: 60.0
  cleanup_timeout: 120.0
  stale_lock_hours: 12

pools:
  prod-project:
    repo_url: https://github.com/user/prod-project.git
    num_slots: 10
    cleanup_options:
      fetch_on_allocate: true   # 常に最新をフェッチ
      clean_on_release: true    # 常にクリーン
      warmup_enabled: true      # スロットを事前ウォームアップ
```

### CI/CD環境

```yaml
defaults:
  num_slots: 3
  lock_timeout: 30.0
  stale_lock_hours: 1  # 積極的なクリーンアップ

pools:
  ci-project:
    repo_url: https://github.com/user/ci-project.git
    num_slots: 5
    cleanup_options:
      fetch_on_allocate: true
      clean_on_release: true
      warmup_enabled: false
```

## 動的設定

### 設定の再読み込み

```python
# ファイルから再読み込み
manager.reload_config()

# カスタムファイルから再読み込み
manager.reload_config(Path("custom/pools.yaml"))
```

### 変更の監視

```python
from necrocode.repo_pool.config import ConfigWatcher
import time

# ウォッチャーを作成
def on_change(new_config):
    print("設定が変更されました！")
    manager.reload_config()

watcher = ConfigWatcher(manager.config, on_change=on_change)

# 定期的にチェック
while True:
    watcher.check_and_reload()
    time.sleep(60)
```

### プログラムによる更新

```python
from necrocode.repo_pool.config import PoolDefinition, CleanupOptions

# 新しいプールを追加
pool_def = PoolDefinition(
    repo_name="new-project",
    repo_url="https://github.com/user/new-project.git",
    num_slots=3,
    cleanup_options=CleanupOptions(
        fetch_on_allocate=True,
        clean_on_release=True,
        warmup_enabled=False
    )
)
manager.config.add_pool_definition(pool_def)

# ファイルに保存
manager.config.save_to_file()

# 新しいプールを初期化
manager.initialize_pools_from_config()
```

## 検証

### 自動検証

設定は読み込み時に自動的に検証されます：

```python
from necrocode.repo_pool.config import ConfigValidationError

try:
    config = PoolConfig.load_from_file()
    config.validate()
except ConfigValidationError as e:
    print(f"無効な設定: {e}")
```

### 検証ルール

- `num_slots`は1以上である必要があります
- `lock_timeout`は0より大きい必要があります
- `cleanup_timeout`は0より大きい必要があります
- `stale_lock_hours`は0以上である必要があります
- 各プールには`repo_url`が必要です

## トラブルシューティング

### 設定が読み込まれない

```python
# ファイルが存在するか確認
config_file = Path.home() / ".necrocode" / "config" / "pools.yaml"
if not config_file.exists():
    print(f"設定ファイルが見つかりません: {config_file}")
```

### 無効なYAML構文

```python
try:
    config = PoolConfig.load_from_file()
except ConfigValidationError as e:
    print(f"YAML解析エラー: {e}")
```

### プールが初期化されない

```python
# プール定義を確認
pool_def = manager.config.get_pool_definition("my-project")
if pool_def is None:
    print("プールが設定で定義されていません")
else:
    print(f"プールURL: {pool_def.repo_url}")
    print(f"スロット数: {pool_def.num_slots}")
```

### 設定変更が適用されない

```python
# ファイルの変更時刻を確認
mtime = manager.config.get_file_mtime()
print(f"設定ファイルの最終更新: {mtime}")

# 強制再読み込み
manager.reload_config()
```

## ベストプラクティス

### 1. バージョン管理を使用

設定をバージョン管理に保存：

```bash
git add ~/.necrocode/config/pools.yaml
git commit -m "プール設定を更新"
```

### 2. 環境固有の設定

異なる環境に異なる設定を使用：

```python
import os

env = os.getenv("ENVIRONMENT", "development")
config_file = Path(f"config/pools.{env}.yaml")
manager = PoolManager.from_config_file(config_file)
```

### 3. デプロイ前の検証

```python
# デプロイ前に設定を検証
config = PoolConfig.load_from_file()
try:
    config.validate()
    print("✓ 設定は有効です")
except ConfigValidationError as e:
    print(f"✗ 設定エラー: {e}")
    exit(1)
```

### 4. 設定変更の監視

```python
# 設定変更をログに記録
def on_config_change(new_config):
    logger.info(f"設定が再読み込みされました: {len(new_config.pools)}個のプール")
    for repo_name in new_config.pools:
        logger.info(f"  - {repo_name}")
    manager.reload_config()

watcher = ConfigWatcher(manager.config, on_change=on_config_change)
```

### 5. 設定のバックアップ

```python
from datetime import datetime

# 変更前にバックアップ
backup_file = Path(f"config/pools.backup.{datetime.now().isoformat()}.yaml")
manager.config.save_to_file(backup_file)
```

## 使用例

`examples/config_management_example.py`で以下の完全な例を参照してください：
- 設定の読み込み
- 検証
- 動的再読み込み
- 設定ウォッチャー
- 設定の保存

## 関連ドキュメント

- [README.md](README.md) - メインドキュメント
- [設計ドキュメント](../../.kiro/specs/repo-pool-manager/design.md)
- [要件](../../.kiro/specs/repo-pool-manager/requirements.md)

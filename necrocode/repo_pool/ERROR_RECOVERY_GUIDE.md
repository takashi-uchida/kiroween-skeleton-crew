# エラーハンドリングとリカバリーガイド

このガイドでは、Repo Pool Managerのエラーハンドリングとリカバリー機能について説明します。

## 概要

Repo Pool Managerには、システムの健全性を維持し、問題がエージェント操作に影響を与えないようにするための包括的なエラー検出と自動リカバリー機能が含まれています。

## 異常検出

### 異常のタイプ

システムは3種類の異常を検出できます：

#### 1. 長時間割り当てられたスロット

異常に長い時間`ALLOCATED`状態にあるスロットは、以下を示す可能性があります：
- クラッシュしたエージェントプロセス
- 忘れられた割り当て
- デッドロックまたはハングしたプロセス

**検出方法:**
```python
long_allocated = manager.detect_long_allocated_slots(max_allocation_hours=24)
```

**デフォルトしきい値:** 24時間

#### 2. 破損したスロット

以下のような整合性の問題があるスロット：
- ディレクトリの欠落
- 破損したgitリポジトリ
- 無効なメタデータ
- 壊れた`.git`ディレクトリ

**検出方法:**
```python
corrupted = manager.detect_corrupted_slots()
```

**検証チェック:**
- スロットディレクトリが存在する
- `.git`ディレクトリが存在し有効である
- 現在のブランチとコミットを取得できる
- Gitリポジトリが破損していない

#### 3. 孤立したロック

以下のようなロックファイル：
- 既存のスロットに対応していない
- 古い（設定されたしきい値より古い）
- クラッシュしたプロセスによって残された

**検出方法:**
```python
orphaned = manager.detect_orphaned_locks()
```

**デフォルトしきい値:** 24時間（`stale_lock_hours`で設定可能）

### 包括的な異常検出

すべての検出方法を一度に実行：

```python
anomalies = manager.detect_anomalies(max_allocation_hours=24)

# 以下を含む辞書を返します:
# {
#     "long_allocated_slots": [Slot, ...],
#     "corrupted_slots": [Slot, ...],
#     "orphaned_locks": ["slot_id", ...]
# }
```

## 手動リカバリー

### 単一スロットのリカバリー

破損またはエラー状態のスロットをリカバリーしようとします：

```python
# 基本的なリカバリー
success = manager.recover_slot(slot_id, force=False)

# 強制リカバリー（修復が失敗しても利用可能としてマーク）
success = manager.recover_slot(slot_id, force=True)
```

**リカバリープロセス:**
1. スロットの整合性を検証
2. 破損している場合、修復を試みる：
   - `git fsck`を実行して破損をチェック
   - クリーンアップを試みて作業状態を復元
   - 修復が失敗した場合、リポジトリを削除して再クローン
3. スロット状態を`AVAILABLE`に更新

### 問題のあるスロットの隔離

スロットを`ERROR`としてマークして割り当てを防止：

```python
manager.isolate_slot(slot_id)
```

**効果:**
- スロット状態が`ERROR`に設定される
- 隔離タイムスタンプと理由がメタデータに追加される
- 手動でリカバリーされるまでスロットは割り当てられない
- 復元には手動介入が必要

**使用例:**
- 自動リカバリーできない永続的な破損
- 手動検査が必要なスロット
- 削除せずにプールから一時的に削除

## 自動リカバリー

### 基本的な自動リカバリー

デフォルト設定で自動リカバリーを実行：

```python
results = manager.auto_recover()
```

### 高度な自動リカバリー

リカバリー動作をカスタマイズ：

```python
results = manager.auto_recover(
    max_allocation_hours=24,           # 長時間割り当てのしきい値
    recover_corrupted=True,            # 破損したスロットのリカバリーを試みる
    cleanup_orphaned_locks=True,       # 孤立したロックファイルをクリーンアップ
    force_release_long_allocated=False # 長時間割り当てられたスロットを強制解放
)
```

**パラメータ:**

- `max_allocation_hours`（デフォルト: 24）
  - スロットが異常と見なされるまでの最大割り当て時間
  
- `recover_corrupted`（デフォルト: True）
  - 破損したスロットのリカバリーを試みるかどうか
  - リカバリーに失敗するとスロットが隔離される
  
- `cleanup_orphaned_locks`（デフォルト: True）
  - 孤立したロックファイルを削除するかどうか
  - 孤立したロックは検証されるため、有効にしても安全
  
- `force_release_long_allocated`（デフォルト: False）
  - 長時間割り当てられたスロットを強制解放するかどうか
  - **警告:** アクティブなエージェントプロセスを中断する可能性があります
  - 本番環境では注意して使用

**戻り値:**

```python
{
    "long_allocated_released": 2,      # 強制解放されたスロット数
    "corrupted_recovered": 1,          # 正常にリカバリーされたスロット数
    "corrupted_isolated": 1,           # 隔離されたスロット数（リカバリー失敗）
    "orphaned_locks_cleaned": 3,       # 削除された孤立したロック数
    "errors": ["error message", ...]   # 発生したエラーのリスト
}
```

## リカバリー戦略

### 戦略1: 保守的（本番環境推奨）

問題を検出するが、アクティブな割り当てを強制解放しない：

```python
results = manager.auto_recover(
    max_allocation_hours=48,           # より高いしきい値
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False # アクティブな作業を中断しない
)
```

**最適な用途:**
- 本番環境
- エージェントプロセスが正当に長時間実行される可能性がある場合
- 長時間割り当ての手動レビューが望ましい場合

### 戦略2: 積極的（開発環境推奨）

すべての異常を積極的にクリーンアップ：

```python
results = manager.auto_recover(
    max_allocation_hours=24,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=True  # 強制クリーンアップ
)
```

**最適な用途:**
- 開発環境
- システムクラッシュ後
- 正当な長時間実行プロセスが存在しないことがわかっている場合

### 戦略3: メンテナンスモード

破損とロックに焦点を当て、割り当てを無視：

```python
results = manager.auto_recover(
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)
```

**最適な用途:**
- 定期メンテナンス
- 実行中のエージェントに影響を与えずにインフラストラクチャの問題を修正したい場合

## スケジュールされたリカバリー

### Cronジョブの例

毎日午前2時に自動リカバリーを実行：

```bash
# /etc/cron.d/necrocode-recovery
0 2 * * * /usr/bin/python3 /path/to/recovery_script.py
```

**recovery_script.py:**
```python
#!/usr/bin/env python3
import logging
from pathlib import Path
from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/var/log/necrocode-recovery.log'
)

config = PoolConfig.load_from_file()
manager = PoolManager(config=config)

# 保守的なリカバリーを実行
results = manager.auto_recover(
    max_allocation_hours=48,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)

logging.info(f"リカバリー完了: {results}")
```

### 監視統合

監視システムとの統合：

```python
def health_check():
    """システムの健全性をチェックし、問題が見つかった場合はアラート"""
    manager = PoolManager.from_config_file()
    
    # 異常を検出
    anomalies = manager.detect_anomalies(max_allocation_hours=24)
    
    total_issues = (
        len(anomalies['long_allocated_slots']) +
        len(anomalies['corrupted_slots']) +
        len(anomalies['orphaned_locks'])
    )
    
    if total_issues > 0:
        # 監視システムにアラートを送信
        send_alert(f"Repo Pool Manager: {total_issues}件の問題を検出")
        
        # 自動リカバリーを試みる
        results = manager.auto_recover()
        
        # 結果を報告
        send_metric("recovery.slots_released", results['long_allocated_released'])
        send_metric("recovery.slots_recovered", results['corrupted_recovered'])
        send_metric("recovery.slots_isolated", results['corrupted_isolated'])
        send_metric("recovery.locks_cleaned", results['orphaned_locks_cleaned'])
    
    return total_issues == 0
```

## ベストプラクティス

### 1. 定期的な健全性チェック

定期的に異常検出を実行（例：毎時）：

```python
# アクションを取らずに問題をチェック
anomalies = manager.detect_anomalies()
if any(len(v) > 0 for v in anomalies.values()):
    logger.warning(f"異常を検出: {anomalies}")
```

### 2. 段階的なリカバリー

多数の問題がある場合は、段階的にリカバリー：

```python
# 第1パス: ロックをクリーンアップし、明らかな破損をリカバリー
results1 = manager.auto_recover(
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)

# 待機して検証
time.sleep(60)

# 第2パス: 必要に応じて残りの問題を処理
anomalies = manager.detect_anomalies()
if len(anomalies['long_allocated_slots']) > 0:
    # 手動レビューまたは強制解放
    pass
```

### 3. ロギングとアラート

常にリカバリーアクションをログに記録：

```python
import logging

logger = logging.getLogger(__name__)

results = manager.auto_recover()

logger.info(
    f"自動リカバリー完了: "
    f"解放={results['long_allocated_released']}, "
    f"リカバリー={results['corrupted_recovered']}, "
    f"隔離={results['corrupted_isolated']}, "
    f"ロッククリーンアップ={results['orphaned_locks_cleaned']}"
)

if results['errors']:
    logger.error(f"リカバリーエラー: {results['errors']}")
```

### 4. 隔離されたスロットの手動介入

隔離されたスロットには手動の注意が必要：

```python
# 隔離されたスロットを見つける
pool = manager.get_pool("my-repo")
isolated = [s for s in pool.slots if s.state == SlotState.ERROR]

for slot in isolated:
    logger.info(f"隔離されたスロット: {slot.slot_id}")
    logger.info(f"  隔離日時: {slot.metadata.get('isolated_at')}")
    logger.info(f"  理由: {slot.metadata.get('isolation_reason')}")
    
    # リカバリーを試みる
    success = manager.recover_slot(slot.slot_id, force=True)
    if success:
        logger.info(f"  ✓ 正常にリカバリー")
    else:
        logger.error(f"  ✗ リカバリー失敗 - 手動介入が必要")
```

## トラブルシューティング

### 問題: リカバリーが繰り返し失敗する

**症状:** 同じスロットが繰り返しリカバリーに失敗

**解決策:**
1. ディスク容量を確認: `df -h`
2. gitリポジトリの健全性を手動で確認:
   ```bash
   cd /path/to/slot
   git fsck --full
   ```
3. ファイルのパーミッションを確認
4. スロットを削除して再作成することを検討:
   ```python
   manager.remove_slot(slot_id, force=True)
   manager.add_slot(repo_name)
   ```

### 問題: 長時間割り当てられたスロットが多すぎる

**症状:** 多くのスロットが長時間割り当てられている

**考えられる原因:**
- エージェントプロセスが正当に長時間実行されている
- エージェントがスロットを解放せずにクラッシュしている
- しきい値が低すぎる

**解決策:**
1. しきい値を増やす: `max_allocation_hours=48`
2. クラッシュについてエージェントログを確認
3. エージェントハートビート監視を実装
4. エージェント実行にタイムアウトを追加

### 問題: 孤立したロックが持続する

**症状:** クリーンアップ後もロックが表示され続ける

**考えられる原因:**
- アクティブなプロセスがロックを作成している
- ファイルシステムの問題
- 適切なロックなしの同時アクセス

**解決策:**
1. 実行中のエージェントプロセスを確認
2. ロックディレクトリのパーミッションを確認
3. ファイルシステムエラーを確認
4. 適切なロック使用についてエージェントコードをレビュー

## APIリファレンス

### 検出メソッド

```python
# 長時間割り当てられたスロットを検出
long_allocated = manager.detect_long_allocated_slots(max_allocation_hours=24)

# 破損したスロットを検出
corrupted = manager.detect_corrupted_slots()

# 孤立したロックを検出
orphaned = manager.detect_orphaned_locks()

# すべての異常を検出
anomalies = manager.detect_anomalies(max_allocation_hours=24)
```

### リカバリーメソッド

```python
# 単一スロットをリカバリー
success = manager.recover_slot(slot_id, force=False)

# スロットを隔離
manager.isolate_slot(slot_id)

# 自動リカバリー
results = manager.auto_recover(
    max_allocation_hours=24,
    recover_corrupted=True,
    cleanup_orphaned_locks=True,
    force_release_long_allocated=False
)
```

### ロック管理

```python
# 古いロックを検出
stale = manager.lock_manager.detect_stale_locks(max_age_hours=24)

# 古いロックをクリーンアップ
count = manager.lock_manager.cleanup_stale_locks(max_age_hours=24)

# 強制アンロック
manager.lock_manager.force_unlock(slot_id)
```

## 要件マッピング

この実装は以下の要件を満たします：

- **要件 9.1**: Git操作のリトライメカニズム（3回リトライ）
- **要件 9.2**: スロットの修復と再初期化
- **要件 9.3**: 長時間割り当てられたスロットの検出
- **要件 9.4**: 孤立したロックの検出とクリーンアップ
- **要件 9.5**: 手動介入のためのスロット隔離

## 関連ドキュメント

- [README.md](README.md) - メインドキュメント
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - 設定ガイド
- [examples/error_recovery_example.py](../../examples/error_recovery_example.py) - 使用例

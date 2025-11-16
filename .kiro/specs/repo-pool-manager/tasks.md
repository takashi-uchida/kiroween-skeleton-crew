# Implementation Plan

- [ ] 1. プロジェクト構造とデータモデルの実装
  - necrocode/repo_pool/ディレクトリを作成
  - データモデル（Pool、Slot、SlotState、SlotStatus、PoolSummary）をmodels.pyに実装
  - 例外クラス（PoolManagerError、SlotNotFoundError等）をexceptions.pyに実装
  - 設定クラス（PoolConfig）をconfig.pyに実装
  - _Requirements: 1.1, 1.4_

- [ ] 2. GitOperationsの実装
  - [ ] 2.1 基本的なGit操作
    - GitOperationsクラスをgit_operations.pyに実装
    - clone_repo()メソッド: リポジトリをクローン
    - fetch_all()メソッド: すべてのリモートブランチをフェッチ
    - clean()メソッド: 未追跡ファイルを削除
    - reset_hard()メソッド: ワーキングディレクトリをリセット
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 2.2 ブランチ操作
    - checkout()メソッド: ブランチをチェックアウト
    - get_current_branch()メソッド: 現在のブランチ名を取得
    - get_current_commit()メソッド: 現在のコミットハッシュを取得
    - list_remote_branches()メソッド: リモートブランチの一覧を取得
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 2.3 エラーハンドリングとリトライ
    - Git操作のエラーハンドリング
    - 3回のリトライ機構
    - GitResultモデルの実装
    - _Requirements: 6.5, 9.1_

- [ ] 3. SlotStoreの実装
  - [ ] 3.1 プールの永続化
    - SlotStoreクラスをslot_store.pyに実装
    - save_pool()メソッド: プール情報をJSON形式で保存
    - load_pool()メソッド: プール情報を読み込み
    - _Requirements: 1.3_

  - [ ] 3.2 スロットの永続化
    - save_slot()メソッド: スロット情報をJSON形式で保存
    - load_slot()メソッド: スロット情報を読み込み
    - list_slots()メソッド: プール内のすべてのスロットを取得
    - _Requirements: 1.3, 1.5_

  - [ ] 3.3 スロットの削除
    - delete_slot()メソッド: スロットを削除
    - ディレクトリの完全削除
    - _Requirements: 7.5_

- [ ] 4. LockManagerの実装
  - [ ] 4.1 ファイルベースのロック機構
    - LockManagerクラスをlock_manager.pyに実装
    - acquire_slot_lock()コンテキストマネージャー: ロック取得と自動解放
    - filelockライブラリを使用した排他制御
    - _Requirements: 4.1_

  - [ ] 4.2 ロックの状態管理
    - is_locked()メソッド: ロック状態の確認
    - force_unlock()メソッド: 強制的なロック解除
    - _Requirements: 4.2, 4.5_

  - [ ] 4.3 古いロックの検出とクリーンアップ
    - detect_stale_locks()メソッド: 古いロックを検出
    - cleanup_stale_locks()メソッド: 古いロックを削除
    - _Requirements: 4.4, 9.4_

- [ ] 5. SlotCleanerの実装
  - [ ] 5.1 基本的なクリーンアップ機能
    - SlotCleanerクラスをslot_cleaner.pyに実装
    - cleanup_before_allocation()メソッド: 割当前のクリーンアップ
    - cleanup_after_release()メソッド: 返却後のクリーンアップ
    - CleanupResultモデルの実装
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 5.2 スロットの検証と修復
    - verify_slot_integrity()メソッド: スロットの整合性を検証
    - repair_slot()メソッド: 破損したスロットを修復
    - _Requirements: 9.2_

  - [ ] 5.3 ウォームアップとログ
    - warmup_slot()メソッド: スロットの事前ウォームアップ
    - get_cleanup_log()メソッド: クリーンアップログを取得
    - _Requirements: 3.5, 10.3_

- [ ] 6. SlotAllocatorの実装
  - [ ] 6.1 基本的な割当機能
    - SlotAllocatorクラスをslot_allocator.pyに実装
    - find_available_slot()メソッド: 利用可能なスロットを検索
    - mark_allocated()メソッド: スロットをAllocated状態にマーク
    - mark_available()メソッド: スロットをAvailable状態にマーク
    - _Requirements: 2.1, 2.2, 2.4_

  - [ ] 6.2 LRUキャッシュ戦略
    - update_lru_cache()メソッド: LRUキャッシュを更新
    - 最近使用されたスロットを優先的に割り当て
    - _Requirements: 10.2_

  - [ ] 6.3 割当メトリクス
    - get_allocation_metrics()メソッド: 割当メトリクスを取得
    - AllocationMetricsモデルの実装
    - _Requirements: 10.5_

- [ ] 7. PoolManagerメインクラスの実装
  - [ ] 7.1 初期化とコンポーネント統合
    - PoolManagerクラスをpool_manager.pyに実装
    - 各コンポーネント（SlotStore、SlotAllocator等）の初期化
    - ディレクトリ構造の自動作成
    - _Requirements: 1.1_

  - [ ] 7.2 プール管理API
    - create_pool()メソッド: 新しいプールを作成
    - get_pool()メソッド: プールを取得
    - list_pools()メソッド: すべてのプール名を取得
    - _Requirements: 1.1, 1.2, 1.5_

  - [ ] 7.3 スロット割当と返却API
    - allocate_slot()メソッド: 利用可能なスロットを割り当て
    - release_slot()メソッド: スロットを返却
    - スロット割当前後のクリーンアップ実行
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.4_

  - [ ] 7.4 スロット状態管理API
    - get_slot_status()メソッド: スロットの詳細状態を取得
    - get_pool_summary()メソッド: すべてのプールのサマリーを取得
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [ ] 7.5 スロットの動的追加と削除
    - add_slot()メソッド: 既存のプールに新しいスロットを追加
    - remove_slot()メソッド: 使用されていないスロットを削除
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 8. 設定管理の実装
  - [ ] 8.1 YAML設定ファイルのサポート
    - 設定ファイル（pools.yaml）の読み込み
    - 設定のバリデーション
    - デフォルト設定の提供
    - _Requirements: 8.1, 8.2, 8.4, 8.5_

  - [ ] 8.2 動的設定反映
    - 設定ファイルの変更検出
    - 動的なプール設定の反映
    - _Requirements: 8.3_

- [ ] 9. エラーハンドリングとリカバリの実装
  - [ ] 9.1 異常状態の検出
    - 長時間Allocated状態のスロットを検出
    - 破損したスロットを検出
    - 孤立したロックファイルを検出
    - _Requirements: 9.3, 9.4_

  - [ ] 9.2 自動リカバリ機能
    - スロットの再初期化
    - エラー状態のスロットの隔離
    - _Requirements: 9.2, 9.5_

- [ ] 10. パフォーマンス最適化の実装
  - [ ] 10.1 並列処理
    - git fetch --allの並列実行
    - 複数スロットの同時クリーンアップ
    - _Requirements: 10.1_

  - [ ] 10.2 バックグラウンドクリーンアップ
    - クリーンアップのバックグラウンド実行オプション
    - 非同期クリーンアップの実装
    - _Requirements: 10.4_

  - [ ] 10.3 メトリクス収集
    - スロット割当の平均時間を測定
    - メトリクスの記録と出力
    - _Requirements: 10.5_

- [ ] 11. ユニットテストの実装
  - [ ] 11.1 データモデルのテスト
    - test_models.py: Pool、Slot、SlotStatusのシリアライズ/デシリアライズ
    - _Requirements: 1.1_

  - [ ] 11.2 GitOperationsのテスト
    - test_git_operations.py: Git操作のテスト（モックを使用）
    - _Requirements: 3.1, 3.2, 3.3, 6.1, 6.2, 6.3, 6.4_

  - [ ] 11.3 SlotStoreのテスト
    - test_slot_store.py: 保存、読み込み、削除
    - _Requirements: 1.3, 1.5, 7.5_

  - [ ] 11.4 LockManagerのテスト
    - test_lock_manager.py: ロック取得、タイムアウト、古いロックの検出
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 11.5 SlotCleanerのテスト
    - test_slot_cleaner.py: クリーンアップ、検証、修復
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 9.2_

  - [ ] 11.6 SlotAllocatorのテスト
    - test_slot_allocator.py: 割当戦略、LRUキャッシュ、メトリクス
    - _Requirements: 2.1, 2.2, 2.4, 10.2, 10.5_

  - [ ] 11.7 PoolManagerのテスト
    - test_pool_manager.py: 全体的な統合テスト
    - _Requirements: すべて_

- [ ] 12. 統合テストの実装
  - [ ] 12.1 プールライフサイクルテスト
    - test_pool_lifecycle.py: プール作成から削除までのライフサイクル
    - _Requirements: 1.1, 1.2, 7.1, 7.2, 7.5_

  - [ ] 12.2 並行割当テスト
    - test_concurrent_allocation.py: 複数プロセスからの同時割当
    - _Requirements: 4.1, 4.2_

  - [ ] 12.3 実際のGitリポジトリでのテスト
    - test_cleanup_integration.py: 実際のGitリポジトリでのクリーンアップ
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 12.4 パフォーマンステスト
    - test_allocation_performance.py: スロット割当の性能
    - test_cleanup_performance.py: クリーンアップの性能
    - test_large_pool.py: 大規模プール（100スロット）の管理
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 13. ドキュメントとサンプルコード
  - [ ] 13.1 APIドキュメント
    - README.mdの作成: 使用方法、インストール手順
    - docstringの充実化
    - _Requirements: すべて_

  - [ ] 13.2 サンプルコード
    - examples/basic_pool_usage.py: 基本的な使用例
    - examples/concurrent_allocation.py: 並行割当の例
    - examples/custom_cleanup.py: カスタムクリーンアップの例
    - _Requirements: すべて_

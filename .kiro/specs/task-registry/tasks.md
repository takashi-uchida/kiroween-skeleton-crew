# Implementation Plan

- [x] 1. プロジェクト構造とデータモデルの実装
  - necrocode/task_registry/ディレクトリを作成
  - データモデル（Taskset、Task、TaskState、TaskEvent、Artifact）をmodels.pyに実装
  - 例外クラス（TaskRegistryError、TaskNotFoundError等）をexceptions.pyに実装
  - 設定クラス（RegistryConfig）をconfig.pyに実装
  - _Requirements: 1.1, 1.4_

- [x] 2. TaskStoreの実装
  - [x] 2.1 基本的な永続化機能
    - TaskStoreクラスをtask_store.pyに実装
    - save_taskset()メソッド: タスクセットをJSON形式で保存
    - load_taskset()メソッド: JSONファイルから読み込み
    - list_tasksets()メソッド: すべてのタスクセット名を取得
    - _Requirements: 1.1, 1.3_

  - [x] 2.2 バックアップとリストア機能
    - backup_taskset()メソッド: タスクセットをバックアップ
    - restore_taskset()メソッド: バックアップから復元
    - バックアップファイルの整合性検証機能
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 3. EventStoreの実装
  - [x] 3.1 イベントログ記録機能
    - EventStoreクラスをevent_store.pyに実装
    - record_event()メソッド: イベントをJSON Lines形式で記録
    - イベントタイプ（TaskCreated、TaskUpdated等）の処理
    - _Requirements: 4.1, 4.2_

  - [x] 3.2 イベント検索機能
    - get_events_by_task()メソッド: タスクIDでイベントを検索
    - get_events_by_timerange()メソッド: 期間でイベントを検索
    - _Requirements: 4.3, 4.4_

  - [x] 3.3 ログローテーション機能
    - rotate_logs()メソッド: ログファイルのローテーション
    - 最大サイズ制限の実装
    - _Requirements: 4.5_

- [x] 4. LockManagerの実装
  - [x] 4.1 ファイルベースのロック機構
    - LockManagerクラスをlock_manager.pyに実装
    - acquire_lock()コンテキストマネージャー: ロック取得と自動解放
    - filelockライブラリを使用した排他制御
    - _Requirements: 6.1_

  - [x] 4.2 ロックのタイムアウトとリトライ
    - タイムアウト設定の実装
    - リトライ機能の実装
    - is_locked()メソッド: ロック状態の確認
    - _Requirements: 6.3, 6.4_

  - [x] 4.3 デッドロック対策
    - force_unlock()メソッド: 強制的なロック解除
    - デッドロック検出機能
    - _Requirements: 6.5_

- [x] 5. KiroSyncManagerの実装
  - [x] 5.1 tasks.mdパーサー
    - KiroSyncManagerクラスをkiro_sync.pyに実装
    - parse_tasks_md()メソッド: tasks.mdを解析してタスク定義を抽出
    - チェックボックス状態（[ ]、[x]）の読み取り
    - タスク番号（1.1、1.2等）の抽出
    - オプショナルタスク（*マーク）の識別
    - _Requirements: 8.2, 8.4, 8.6_

  - [x] 5.2 依存関係の解析
    - extract_dependencies()メソッド: "_Requirements: X.Y_"から依存関係を抽出
    - 依存関係グラフの構築
    - 循環参照の検証
    - _Requirements: 3.1, 3.2, 8.5_

  - [x] 5.3 双方向同期機能
    - sync_from_kiro()メソッド: tasks.mdからTask Registryへ同期
    - sync_to_kiro()メソッド: Task Registryからtasks.mdへ同期
    - update_tasks_md()メソッド: チェックボックスの更新
    - 新規タスクの自動追加
    - _Requirements: 8.1, 8.3, 8.7_

- [x] 6. QueryEngineの実装
  - [x] 6.1 基本的なフィルタリング機能
    - QueryEngineクラスをquery_engine.pyに実装
    - filter_by_state()メソッド: 状態でフィルタリング
    - filter_by_skill()メソッド: 必要スキルでフィルタリング
    - _Requirements: 7.1, 7.2_

  - [x] 6.2 ソートとページネーション
    - sort_by_priority()メソッド: 優先度でソート
    - query()メソッド: 複合クエリとページネーション
    - _Requirements: 7.3, 7.4, 7.5_

- [x] 7. TaskRegistryメインクラスの実装
  - [x] 7.1 初期化とコンポーネント統合
    - TaskRegistryクラスをtask_registry.pyに実装
    - 各コンポーネント（TaskStore、EventStore等）の初期化
    - ディレクトリ構造の自動作成
    - _Requirements: 1.1_

  - [x] 7.2 タスクセット管理API
    - create_taskset()メソッド: 新しいタスクセットを作成
    - get_taskset()メソッド: タスクセットを取得
    - バージョン番号の自動インクリメント
    - _Requirements: 1.2, 1.5_

  - [x] 7.3 タスク状態管理API
    - update_task_state()メソッド: タスクの状態を更新
    - 状態遷移の妥当性検証
    - Running状態への遷移時にassigned_slot、reserved_branch、runner_idを記録
    - Done状態への遷移時に依存タスクのBlocked状態を解除
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [x] 7.4 実行可能タスクの取得
    - get_ready_tasks()メソッド: Ready状態のタスクを取得
    - required_skillによるフィルタリング
    - 依存関係を考慮した実行順序の計算
    - _Requirements: 2.3, 3.4_

  - [x] 7.5 成果物管理API
    - add_artifact()メソッド: 成果物の参照を追加
    - 成果物のタイプ（diff/log/test）とURIの記録
    - メタデータ（サイズ、作成日時）の保存
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [x] 7.6 Kiro同期API
    - sync_with_kiro()メソッド: tasks.mdとの同期を実行
    - 同期結果（SyncResult）の返却
    - _Requirements: 8.1, 8.3_

- [x] 8. 依存関係グラフの可視化
  - [x] 8.1 グラフ出力機能
    - 依存関係グラフをDOT形式で出力
    - Mermaid形式での出力もサポート
    - _Requirements: 3.5_

- [x] 9. ユニットテストの実装
  - [x] 9.1 データモデルのテスト
    - test_models.py: Taskset、Task、TaskEventのシリアライズ/デシリアライズ
    - _Requirements: 1.1_

  - [x] 9.2 TaskStoreのテスト
    - test_task_store.py: 保存、読み込み、バックアップ、リストア
    - _Requirements: 1.1, 1.3, 9.1, 9.2_

  - [x] 9.3 EventStoreのテスト
    - test_event_store.py: イベント記録、検索、ローテーション
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 9.4 LockManagerのテスト
    - test_lock_manager.py: ロック取得、タイムアウト、デッドロック検出
    - _Requirements: 6.1, 6.3, 6.4, 6.5_

  - [x] 9.5 KiroSyncManagerのテスト
    - test_kiro_sync.py: tasks.mdパース、依存関係抽出、双方向同期
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 9.6 QueryEngineのテスト
    - test_query_engine.py: フィルタリング、ソート、ページネーション
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 9.7 TaskRegistryのテスト
    - test_task_registry.py: 全体的な統合テスト
    - _Requirements: すべて_

- [x] 10. 統合テストの実装
  - [x] 10.1 並行アクセステスト
    - test_concurrent_access.py: 複数プロセスからの同時アクセス
    - 楽観的ロックの動作確認
    - _Requirements: 6.2_

  - [x] 10.2 Kiro同期統合テスト
    - test_kiro_sync_integration.py: 実際のtasks.mdファイルとの同期
    - _Requirements: 8.1, 8.3, 8.7_

  - [x] 10.3 パフォーマンステスト
    - test_large_taskset.py: 1000タスク以上の大規模タスクセット
    - test_event_log_performance.py: イベントログの書き込み性能
    - _Requirements: すべて_

- [x] 11. ドキュメントとサンプルコード
  - [x] 11.1 APIドキュメント
    - README.mdの作成: 使用方法、インストール手順
    - docstringの充実化
    - _Requirements: すべて_

  - [x] 11.2 サンプルコード
    - examples/basic_usage.py: 基本的な使用例
    - examples/kiro_sync_example.py: Kiro同期の例
    - examples/concurrent_usage.py: 並行アクセスの例
    - _Requirements: すべて_

# Implementation Plan

- [ ] 1. プロジェクト構造とデータモデルの実装
  - necrocode/dispatcher/ディレクトリを作成
  - データモデル（AgentPool、PoolType、Runner、RunnerState、RunnerInfo、SchedulingPolicy、PoolStatus）をmodels.pyに実装
  - 例外クラス（DispatcherError、TaskAssignmentError等）をexceptions.pyに実装
  - 設定クラス（DispatcherConfig）をconfig.pyに実装
  - _Requirements: 2.1, 2.2_

- [ ] 2. TaskMonitorの実装
  - [ ] 2.1 Task Registryクライアント
    - TaskMonitorクラスをtask_monitor.pyに実装
    - TaskRegistryClientクラス: Task Registryとの通信
    - _Requirements: 1.1_

  - [ ] 2.2 Readyタスクの取得
    - poll_ready_tasks()メソッド: Readyタスクを取得
    - ポーリング間隔の設定
    - _Requirements: 1.1, 1.2_

  - [ ] 2.3 タスクのフィルタリング
    - _filter_tasks()メソッド: 依存関係が解決されたタスクのみを返す
    - _Requirements: 1.4_

- [ ] 3. TaskQueueの実装
  - [ ] 3.1 優先度キュー
    - TaskQueueクラスをtask_queue.pyに実装
    - PriorityQueueを使用した実装
    - スレッドセーフな操作
    - _Requirements: 1.5_

  - [ ] 3.2 キュー操作
    - enqueue()メソッド: タスクをキューに追加
    - dequeue()メソッド: タスクをキューから取得
    - peek()メソッド: キューの先頭を確認
    - size()メソッド: キューのサイズを取得
    - clear()メソッド: キューをクリア
    - _Requirements: 1.3, 1.5_

- [ ] 4. Schedulerの実装
  - [ ] 4.1 スケジューリングポリシーの基本実装
    - Schedulerクラスをscheduler.pyに実装
    - schedule()メソッド: ポリシーに基づいてタスクを選択
    - _Requirements: 11.1, 11.5_

  - [ ] 4.2 FIFOスケジューリング
    - _schedule_fifo()メソッド: 先入先出スケジューリング
    - _Requirements: 11.1_

  - [ ] 4.3 優先度ベーススケジューリング
    - _schedule_priority()メソッド: 優先度ベーススケジューリング
    - _Requirements: 7.1, 7.2, 7.3, 11.2_

  - [ ] 4.4 スキルベーススケジューリング
    - _schedule_skill_based()メソッド: スキルベーススケジューリング
    - _Requirements: 3.1, 11.3_

  - [ ] 4.5 公平分配スケジューリング
    - _schedule_fair_share()メソッド: 公平分配スケジューリング
    - _Requirements: 11.4_

- [ ] 5. AgentPoolManagerの実装
  - [ ] 5.1 Agent Pool設定の読み込み
    - AgentPoolManagerクラスをagent_pool_manager.pyに実装
    - _load_pools()メソッド: YAML設定を読み込み
    - _Requirements: 2.1_

  - [ ] 5.2 スキルマッピング
    - get_pool_for_skill()メソッド: スキルに対応するプールを取得
    - スキルとプールのマッピング管理
    - _Requirements: 3.1, 3.2_

  - [ ] 5.3 負荷分散
    - _select_least_loaded_pool()メソッド: 最も空いているプールを選択
    - _Requirements: 3.3_

  - [ ] 5.4 並行実行制御
    - can_accept_task()メソッド: プールがタスクを受け入れ可能か確認
    - increment_running_count()メソッド: 実行中タスク数をインクリメント
    - decrement_running_count()メソッド: 実行中タスク数をデクリメント
    - _Requirements: 2.2, 2.3, 6.1, 6.2, 6.3_

  - [ ] 5.5 リソースクォータ管理
    - CPUクォータとメモリクォータの管理
    - リソース使用量の追跡
    - _Requirements: 2.4, 12.1, 12.2, 12.3, 12.4_

  - [ ] 5.6 プール状態管理
    - get_pool_status()メソッド: プールの状態を取得
    - プールの有効/無効の切り替え
    - _Requirements: 2.5_

- [ ] 6. RunnerLauncherの実装
  - [ ] 6.1 基本的な起動機能
    - RunnerLauncherクラスをrunner_launcher.pyに実装
    - launch()メソッド: Agent Runnerを起動
    - _generate_runner_id()メソッド: Runner IDを生成
    - _build_task_context()メソッド: タスクコンテキストを構築
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 6.2 Local Process Launcher
    - LocalProcessLauncherクラス: ローカルプロセスとして起動
    - サブプロセスの管理
    - _Requirements: 5.1_

  - [ ] 6.3 Docker Launcher
    - DockerLauncherクラス: Dockerコンテナとして起動
    - Dockerクライアントの使用
    - ワークスペースのマウント
    - 環境変数の注入
    - _Requirements: 5.1_

  - [ ] 6.4 Kubernetes Launcher
    - KubernetesLauncherクラス: Kubernetes Jobとして起動
    - Jobマニフェストの生成
    - Secretのマウント
    - _Requirements: 5.1_

  - [ ] 6.5 起動失敗のハンドリング
    - 起動失敗の検出
    - リトライまたはエラー報告
    - _Requirements: 5.5_

- [ ] 7. RunnerMonitorの実装
  - [ ] 7.1 Runner監視の基本機能
    - RunnerMonitorクラスをrunner_monitor.pyに実装
    - add_runner()メソッド: Runnerを監視対象に追加
    - remove_runner()メソッド: Runnerを監視対象から削除
    - _Requirements: 8.1_

  - [ ] 7.2 ハートビートチェック
    - update_heartbeat()メソッド: ハートビートを更新
    - check_heartbeats()メソッド: ハートビートをチェック
    - _Requirements: 8.1, 8.2_

  - [ ] 7.3 タイムアウト処理
    - _handle_timeout()メソッド: タイムアウトを処理
    - タスクの再割当
    - _Requirements: 8.3, 8.4_

  - [ ] 7.4 Runner状態の追跡
    - get_runner_status()メソッド: Runnerの状態を取得
    - _Requirements: 8.5_

- [ ] 8. MetricsCollectorの実装
  - [ ] 8.1 メトリクス収集
    - MetricsCollectorクラスをmetrics_collector.pyに実装
    - collect()メソッド: メトリクスを収集
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ] 8.2 メトリクスの記録
    - record_assignment()メソッド: タスク割当を記録
    - _Requirements: 14.5_

  - [ ] 8.3 Prometheus形式のエクスポート
    - export_prometheus()メソッド: Prometheus形式でエクスポート
    - _Requirements: 14.5_

  - [ ] 8.4 個別メトリクスの取得
    - _get_queue_size()メソッド: キューサイズを取得
    - _get_running_tasks_count()メソッド: 実行中タスク数を取得
    - _get_pool_utilization()メソッド: プール使用率を取得
    - _get_average_wait_time()メソッド: 平均待機時間を取得
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [ ] 9. DispatcherCoreメインクラスの実装
  - [ ] 9.1 初期化とコンポーネント統合
    - DispatcherCoreクラスをdispatcher_core.pyに実装
    - 各コンポーネント（TaskMonitor、TaskQueue等）の初期化
    - _Requirements: 1.1_

  - [ ] 9.2 メインループ
    - start()メソッド: Dispatcherを起動
    - _main_loop()メソッド: メインループ
    - Readyタスクの取得、キューへの追加、スケジューリング、割当
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [ ] 9.3 タスク割当
    - _assign_task()メソッド: タスクを割り当て
    - スロットの割当
    - Runnerの起動
    - Task Registryの更新
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4_

  - [ ] 9.4 スロット割当
    - _allocate_slot()メソッド: Repo Pool Managerからスロットを割り当て
    - スロット割当失敗時の処理
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 9.5 Task Registry更新
    - _update_task_registry()メソッド: Task Registryを更新
    - TaskAssignedイベントの記録
    - _Requirements: 4.4, 10.1, 10.2, 10.3, 10.4_

  - [ ] 9.6 グレースフルシャットダウン
    - stop()メソッド: Dispatcherを停止
    - _wait_for_runners()メソッド: 実行中のRunnerの完了を待機
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [ ] 10. タスク再試行の実装
  - [ ] 10.1 再試行カウンターの管理
    - タスクの再試行回数を追跡
    - _Requirements: 9.2_

  - [ ] 10.2 再試行ロジック
    - 失敗通知の受信
    - 再試行回数の確認
    - キューへの再追加またはFailed状態への遷移
    - _Requirements: 9.1, 9.3, 9.4_

  - [ ] 10.3 指数バックオフ
    - 再試行間隔の計算
    - _Requirements: 9.5_

- [ ] 11. デッドロック検出の実装
  - [ ] 11.1 依存関係グラフの分析
    - 依存関係グラフの構築
    - 循環依存の検出
    - _Requirements: 13.1, 13.2_

  - [ ] 11.2 デッドロック処理
    - デッドロック検出時の警告
    - 手動介入の要求
    - _Requirements: 13.3, 13.4, 13.5_

- [ ] 12. イベント記録の実装
  - [ ] 12.1 イベント送信
    - Task Registryへのイベント送信
    - イベントタイプ（TaskAssigned、RunnerStarted等）の処理
    - _Requirements: 10.1, 10.2_

  - [ ] 12.2 イベント詳細情報
    - Runner ID、スロットID、実行時間の記録
    - タイムスタンプの記録
    - _Requirements: 10.3, 10.4_

  - [ ] 12.3 イベント記録失敗の処理
    - ローカルログへのフォールバック
    - _Requirements: 10.5_

- [ ] 13. 並行実行制御の実装
  - [ ] 13.1 実行中タスク数の追跡
    - Agent Poolごとの実行中タスク数を追跡
    - グローバルな実行中タスク数を追跡
    - _Requirements: 6.1, 6.4_

  - [ ] 13.2 完了通知の処理
    - Agent Runnerからの完了通知を受信
    - 実行中タスク数をデクリメント
    - _Requirements: 6.3_

  - [ ] 13.3 並行実行メトリクス
    - 並行実行数のメトリクスを記録
    - _Requirements: 6.5_

- [ ] 14. 優先度管理の実装
  - [ ] 14.1 優先度の読み取り
    - タスクの優先度フィールドを読み取り
    - _Requirements: 7.1_

  - [ ] 14.2 優先度ベースのソート
    - 優先度の高いタスクを優先的に割り当て
    - 同じ優先度のタスクはFIFO順で処理
    - _Requirements: 7.2, 7.3_

  - [ ] 14.3 動的な優先度変更
    - 優先度の動的な変更をサポート
    - 優先度ベースのスケジューリングの無効化
    - _Requirements: 7.4, 7.5_

- [ ] 15. ユニットテストの実装
  - [ ] 15.1 データモデルのテスト
    - test_models.py: AgentPool、Runner、RunnerInfo等のシリアライズ/デシリアライズ
    - _Requirements: 2.1_

  - [ ] 15.2 TaskMonitorのテスト
    - test_task_monitor.py: ポーリング機能のテスト
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ] 15.3 TaskQueueのテスト
    - test_task_queue.py: 優先度キューのテスト
    - _Requirements: 1.3, 1.5_

  - [ ] 15.4 Schedulerのテスト
    - test_scheduler.py: スケジューリングポリシーのテスト
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ] 15.5 AgentPoolManagerのテスト
    - test_agent_pool_manager.py: プール管理のテスト
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3_

  - [ ] 15.6 RunnerLauncherのテスト
    - test_runner_launcher.py: Runner起動のテスト
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 15.7 RunnerMonitorのテスト
    - test_runner_monitor.py: Runner監視のテスト
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 15.8 MetricsCollectorのテスト
    - test_metrics_collector.py: メトリクス収集のテスト
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ] 15.9 DispatcherCoreのテスト
    - test_dispatcher_core.py: メインループのテスト
    - _Requirements: すべて_

- [ ] 16. 統合テストの実装
  - [ ] 16.1 実際のタスク割当テスト
    - test_dispatcher_integration.py: 実際のタスク割当の統合テスト
    - _Requirements: すべて_

  - [ ] 16.2 並行実行テスト
    - test_concurrent_dispatch.py: 並行実行の統合テスト
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ] 16.3 グレースフルシャットダウンテスト
    - test_graceful_shutdown.py: グレースフルシャットダウンのテスト
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [ ] 16.4 パフォーマンステスト
    - test_dispatcher_performance.py: スケジューリング性能の測定
    - test_high_load.py: 高負荷時の動作テスト
    - _Requirements: すべて_

- [ ] 17. ドキュメントとサンプルコード
  - [ ] 17.1 APIドキュメント
    - README.mdの作成: 使用方法、インストール手順
    - docstringの充実化
    - _Requirements: すべて_

  - [ ] 17.2 サンプルコード
    - examples/basic_dispatcher_usage.py: 基本的な使用例
    - examples/custom_scheduling_policy.py: カスタムスケジューリングポリシーの例
    - examples/multi_pool_setup.py: 複数Agent Poolの設定例
    - _Requirements: すべて_

  - [ ] 17.3 設定ファイルサンプル
    - config/dispatcher.yaml: Dispatcher設定のサンプル
    - config/agent-pools.yaml: Agent Pool設定のサンプル
    - _Requirements: 2.1, 11.5_

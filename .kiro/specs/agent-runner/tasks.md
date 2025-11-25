# Implementation Plan

- [x] 1. プロジェクト構造とデータモデルの実装
  - necrocode/agent_runner/ディレクトリを作成
  - データモデル（TaskContext、RunnerState、RunnerResult、ImplementationResult、TestResult、PushResult、Artifact）をmodels.pyに実装
  - 例外クラス（RunnerError、ImplementationError等）をexceptions.pyに実装
  - 設定クラス（RunnerConfig、RetryConfig）をconfig.pyに実装
  - _Requirements: 1.1, 1.3_

- [x] 2. WorkspaceManagerの実装
  - [x] 2.1 基本的なGit操作
    - WorkspaceManagerクラスをworkspace_manager.pyに実装
    - prepare_workspace()メソッド: checkout/fetch/rebase/branch作成
    - commit_changes()メソッド: 変更をコミット
    - get_diff()メソッド: 変更のdiffを取得
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [x] 2.2 プッシュとリトライ
    - push_branch()メソッド: ブランチをプッシュ（リトライ機能付き）
    - 指数バックオフによるリトライ
    - _Requirements: 5.4, 5.5, 8.2_

  - [x] 2.3 ロールバック機能
    - rollback()メソッド: 変更をロールバック
    - _Requirements: 8.1_

- [x] 3. TaskExecutorの実装
  - [x] 3.1 Kiro連携
    - TaskExecutorクラスをtask_executor.pyに実装
    - KiroClientクラス: Kiroとの通信
    - execute()メソッド: タスクを実装
    - _Requirements: 3.1, 3.2_

  - [x] 3.2 実装プロンプトの構築
    - _build_implementation_prompt()メソッド: タスクコンテキストからプロンプトを生成
    - 受入基準、依存情報を含める
    - _Requirements: 3.1_

  - [x] 3.3 実装の検証
    - _verify_implementation()メソッド: 実装結果を検証
    - エラーハンドリング
    - _Requirements: 3.3, 3.5_

- [x] 4. TestRunnerの実装
  - [x] 4.1 テスト実行機能
    - TestRunnerクラスをtest_runner.pyに実装
    - CommandExecutorクラス: コマンド実行の抽象化
    - run_tests()メソッド: テストを実行
    - _Requirements: 4.1_

  - [x] 4.2 テスト結果の記録
    - _run_single_test()メソッド: 単一のテストを実行
    - 標準出力/標準エラーの記録
    - TestResultモデルの生成
    - _Requirements: 4.2, 4.3_

  - [x] 4.3 デフォルトテストコマンド
    - _get_default_test_commands()メソッド: デフォルトのテストコマンドを取得
    - 言語/フレームワークごとのテストコマンド
    - _Requirements: 4.1, 4.5_

- [x] 5. ArtifactUploaderの実装
  - [x] 5.1 Artifact Storeクライアント
    - ArtifactUploaderクラスをartifact_uploader.pyに実装
    - ArtifactStoreClientクラス: Artifact Storeとの通信
    - _Requirements: 6.1_

  - [x] 5.2 成果物のアップロード
    - upload_artifacts()メソッド: すべての成果物をアップロード
    - _upload_diff()メソッド: diffをアップロード
    - _upload_log()メソッド: ログをアップロード
    - _upload_test_result()メソッド: テスト結果をアップロード
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.3 Task Registryへの記録
    - 成果物URIをTask Registryに記録
    - アップロード失敗時の警告処理
    - _Requirements: 6.4, 6.5_

- [x] 6. PlaybookEngineの実装
  - [x] 6.1 Playbookの読み込み
    - PlaybookEngineクラスをplaybook_engine.pyに実装
    - load_playbook()メソッド: YAML形式のPlaybookを読み込み
    - Playbookモデルの実装
    - _Requirements: 13.1_

  - [x] 6.2 Playbookの実行
    - execute_playbook()メソッド: Playbookを実行
    - _execute_step()メソッド: 個別ステップを実行
    - _Requirements: 13.2, 13.3_

  - [x] 6.3 条件分岐のサポート
    - _should_execute_step()メソッド: ステップの実行条件を評価
    - 条件式のパース
    - _Requirements: 13.4_

  - [x] 6.4 デフォルトPlaybook
    - デフォルトPlaybookの提供
    - カスタムPlaybookでの上書き
    - _Requirements: 13.5_

- [x] 7. RunnerOrchestratorメインクラスの実装
  - [x] 7.1 初期化とコンポーネント統合
    - RunnerOrchestratorクラスをrunner_orchestrator.pyに実装
    - 各コンポーネント（WorkspaceManager、TaskExecutor等）の初期化
    - Runner IDの生成
    - _Requirements: 1.1, 1.3_

  - [x] 7.2 タスクコンテキストの検証
    - _validate_task_context()メソッド: タスクコンテキストを検証
    - 必要な情報の確認
    - _Requirements: 1.2_

  - [x] 7.3 実行フローの制御
    - run()メソッド: タスク実行のメインフロー
    - _prepare_workspace()メソッド: ワークスペース準備
    - _execute_task()メソッド: タスク実装
    - _run_tests()メソッド: テスト実行
    - _commit_and_push()メソッド: コミット＆プッシュ
    - _upload_artifacts()メソッド: 成果物アップロード
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 6.1_

  - [x] 7.4 完了報告
    - _report_completion()メソッド: Task Registryに完了を報告
    - TaskCompletedイベントの記録
    - スロットの返却
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 7.5 エラーハンドリング
    - _handle_error()メソッド: エラーを処理
    - TaskFailedイベントの記録
    - エラーログの保存
    - _Requirements: 8.1, 8.3, 8.4, 8.5_

  - [x] 7.6 クリーンアップ
    - _cleanup()メソッド: リソースのクリーンアップ
    - 認証情報の削除
    - _Requirements: 10.3_

- [x] 8. 状態管理の実装
  - [x] 8.1 状態遷移
    - _transition_state()メソッド: 状態を遷移
    - 状態遷移の検証
    - _Requirements: 1.5_

  - [x] 8.2 状態の永続化
    - 状態をファイルに保存（オプション）
    - _Requirements: 1.5_

- [x] 9. セキュリティ機能の実装
  - [x] 9.1 認証情報の管理
    - 環境変数からGitトークンを取得
    - Secret Mountのサポート
    - _Requirements: 1.4, 10.1_

  - [x] 9.2 機密情報のマスキング
    - ログから機密情報を自動的にマスク
    - トークン、パスワードの検出
    - _Requirements: 10.5_

  - [x] 9.3 権限の制限
    - タスクスコープに限定された権限の使用
    - ワークスペースへのアクセス制限
    - _Requirements: 10.2, 10.4_

- [x] 10. タイムアウトとリソース制限の実装
  - [x] 10.1 タイムアウト機能
    - タスク実行の最大時間を設定
    - タイムアウト時の中断処理
    - _Requirements: 11.1, 11.2_

  - [x] 10.2 リソース監視
    - メモリ使用量の監視
    - CPU使用率の監視
    - psutilを使用したリソース測定
    - _Requirements: 11.3, 11.4, 11.5_

- [-] 11. ログとモニタリングの実装
  - [x] 11.1 構造化ログ
    - JSON形式のログ出力
    - ログレベルの設定
    - _Requirements: 12.1, 12.2, 12.4_

  - [x] 11.2 実行メトリクス
    - 実行時間、メモリ使用量、CPU使用率の記録
    - メトリクスの出力
    - _Requirements: 12.3_

  - [x] 11.3 ヘルスチェック
    - ヘルスチェックエンドポイントの実装（Kubernetes用）
    - _Requirements: 12.5_

- [x] 12. 実行環境の実装
  - [x] 12.1 Local Process Mode
    - LocalProcessRunnerクラスの実装
    - ローカルプロセスとしての実行
    - _Requirements: 9.2_

  - [x] 12.2 Docker Container Mode
    - DockerRunnerクラスの実装
    - Dockerコンテナとしての実行
    - ワークスペースのマウント
    - 環境変数の注入
    - _Requirements: 9.3_

  - [x] 12.3 Kubernetes Job Mode
    - KubernetesRunnerクラスの実装
    - Kubernetes Jobとしての実行
    - Jobマニフェストの生成
    - Secretのマウント
    - _Requirements: 9.4_

  - [x] 12.4 実行環境の抽象化
    - 共通インターフェースの定義
    - 実行環境固有の設定のサポート
    - _Requirements: 9.1, 9.5_

- [x] 13. 並列実行のサポート
  - [x] 13.1 ステートレス設計
    - 完全にステートレスな実装
    - 独立したワークスペースの使用
    - _Requirements: 14.1, 14.2_

  - [x] 13.2 リソース競合の検出
    - 並列実行時のリソース競合を検出
    - 適切な処理
    - _Requirements: 14.3_

  - [x] 13.3 並列実行メトリクス
    - 同時実行数、待機時間の記録
    - 最大並列実行数の設定
    - _Requirements: 14.4, 14.5_

- [x] 14. ユニットテストの実装
  - [x] 14.1 データモデルのテスト
    - test_models.py: TaskContext、RunnerResult等のシリアライズ/デシリアライズ
    - _Requirements: 1.1_

  - [x] 14.2 WorkspaceManagerのテスト
    - test_workspace_manager.py: Git操作のテスト（モックを使用）
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 5.4_

  - [x] 14.3 TaskExecutorのテスト
    - test_task_executor.py: 実装機能のテスト
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 14.4 TestRunnerのテスト
    - test_test_runner.py: テスト実行のテスト
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 14.5 ArtifactUploaderのテスト
    - test_artifact_uploader.py: アップロード機能のテスト
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 14.6 PlaybookEngineのテスト
    - test_playbook_engine.py: Playbook実行のテスト
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [x] 14.7 RunnerOrchestratorのテスト
    - test_runner_orchestrator.py: 実行フローのテスト
    - _Requirements: すべて_

- [x] 15. 統合テストの実装
  - [x] 15.1 実際のタスク実行テスト
    - test_runner_integration.py: 実際のタスク実行の統合テスト
    - _Requirements: すべて_

  - [x] 15.2 Docker実行テスト
    - test_docker_runner.py: Dockerコンテナでの実行テスト
    - _Requirements: 9.3_

  - [x] 15.3 Kubernetes実行テスト
    - test_kubernetes_runner.py: Kubernetes Jobでの実行テスト
    - _Requirements: 9.4_

  - [x] 15.4 パフォーマンステスト
    - test_runner_performance.py: 実行時間の測定
    - test_parallel_runners.py: 並列実行の性能テスト
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 16. ドキュメントとサンプルコード
  - [x] 16.1 APIドキュメント
    - README.mdの作成: 使用方法、インストール手順
    - docstringの充実化
    - _Requirements: すべて_

  - [x] 16.2 サンプルコード
    - examples/basic_runner_usage.py: 基本的な使用例
    - examples/custom_playbook.py: カスタムPlaybookの例
    - examples/docker_runner.py: Docker実行の例
    - examples/kubernetes_runner.py: Kubernetes実行の例
    - _Requirements: すべて_

  - [x] 16.3 Playbookサンプル
    - playbooks/backend-task.yaml: バックエンドタスク用Playbook
    - playbooks/frontend-task.yaml: フロントエンドタスク用Playbook
    - playbooks/test-task.yaml: テストタスク用Playbook
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

# Implementation Plan

- [x] 1. プロジェクト構造とデータモデルの更新
  - 新しいデータモデル（SlotAllocation、CodeChange、LLMResponse、LLMConfig）をmodels.pyに追加
  - ImplementationResultにllm_model、tokens_usedフィールドを追加
  - TaskContextにrelated_files、max_tokensフィールドを追加
  - 既存の例外クラスを確認・更新
  - _Requirements: 1.1, 1.3, 3.1, 16.1_

- [x] 3. WorkspaceManagerの実装（変更不要）
  - [x] 3.1 基本的なGit操作
    - WorkspaceManagerクラスをworkspace_manager.pyに実装
    - prepare_workspace()メソッド: checkout/fetch/rebase/branch作成
    - commit_changes()メソッド: 変更をコミット
    - get_diff()メソッド: 変更のdiffを取得
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 プッシュとリトライ
    - push_branch()メソッド: ブランチをプッシュ（リトライ機能付き）
    - 指数バックオフによるリトライ
    - _Requirements: 5.4, 5.5, 8.2_

  - [x] 3.3 ロールバック機能
    - rollback()メソッド: 変更をロールバック
    - _Requirements: 8.1_

- [x] 2. 外部サービスクライアントの実装
  - [x] 2.1 LLMClientの実装
    - LLMClientクラスをllm_client.pyに実装
    - generate_code()メソッド: OpenAI APIを使用してコード生成
    - レート制限エラーのハンドリングとリトライ
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

  - [x] 2.2 TaskRegistryClientの実装
    - TaskRegistryClientクラスをtask_registry_client.pyに実装
    - update_task_status()メソッド: タスク状態を更新
    - add_event()メソッド: イベントを記録
    - add_artifact()メソッド: 成果物を記録
    - _Requirements: 15.1, 15.4, 15.5, 15.6_

  - [x] 2.3 RepoPoolClientの実装
    - RepoPoolClientクラスをrepo_pool_client.pyに実装
    - allocate_slot()メソッド: スロットを割り当て
    - release_slot()メソッド: スロットを返却
    - _Requirements: 15.2, 15.4, 15.5, 15.6_

  - [x] 2.4 ArtifactStoreClientの実装
    - ArtifactStoreClientクラスをartifact_store_client.pyに実装
    - upload()メソッド: 成果物をアップロード
    - _Requirements: 15.3, 15.4, 15.5, 15.6_

- [x] 3. TaskExecutorの更新
  - [x] 3.1 LLM連携への変更
    - TaskExecutorをLLMClient使用に書き換え
    - A2AClient、KiroClient関連のコードを削除
    - execute()メソッド: LLMでコード生成
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 実装プロンプトの構築
    - _build_implementation_prompt()メソッド: タスクコンテキストからプロンプトを生成
    - 受入基準、依存情報、ワークスペース構造を含める
    - 関連ファイルの内容を含める
    - JSON形式のレスポンスを要求
    - _Requirements: 3.1, 3.4_

  - [x] 3.3 コード変更の適用
    - _apply_code_changes()メソッド: LLMが返したコード変更を適用
    - ファイルの作成/修正/削除をサポート
    - _Requirements: 3.3_

  - [x] 3.4 実装の検証
    - _verify_implementation()メソッド: 実装結果を検証
    - JSONパースエラーのハンドリング
    - _Requirements: 3.6, 3.7_

- [x] 4. TestRunnerの実装（変更不要）
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

- [x] 5. ArtifactUploaderの更新
  - [x] 5.1 ArtifactStoreClient統合
    - ArtifactUploaderをArtifactStoreClient使用に書き換え
    - コンストラクタでクライアントを受け取る
    - _Requirements: 6.1, 15.3_

  - [x] 5.2 成果物のアップロード
    - upload_artifacts()メソッド: すべての成果物をアップロード
    - _upload_diff()メソッド: diffをアップロード
    - _upload_log()メソッド: ログをアップロード
    - _upload_test_result()メソッド: テスト結果をアップロード
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.3 Task Registryへの記録
    - TaskRegistryClientを使用して成果物URIを記録
    - アップロード失敗時の警告処理
    - _Requirements: 6.4, 6.5, 15.1_

- [x] 6. PlaybookEngineの実装（変更不要）
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

- [x] 7. RunnerOrchestratorメインクラスの更新
  - [x] 7.1 初期化とコンポーネント統合の更新
    - A2A関連のコード（MessageBus、AgentRegistry、A2AClient）を削除
    - 外部サービスクライアント（TaskRegistryClient、RepoPoolClient、ArtifactStoreClient）を初期化
    - LLMConfigを追加
    - _Requirements: 1.1, 1.3, 15.1, 15.2, 15.3, 16.1_

  - [x] 7.2 タスクコンテキストの検証
    - _validate_task_context()メソッド: タスクコンテキストを検証
    - 必要な情報の確認
    - _Requirements: 1.2_

  - [x] 7.3 実行フローの制御の更新
    - run()メソッド: タスク実行のメインフロー
    - _prepare_workspace()メソッド: RepoPoolClientでスロット割り当て
    - _execute_task()メソッド: TaskExecutor（LLM使用）でタスク実装
    - _run_tests()メソッド: テスト実行
    - _commit_and_push()メソッド: コミット＆プッシュ
    - _upload_artifacts()メソッド: 成果物アップロード
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 6.1, 15.2_

  - [x] 7.4 完了報告の更新
    - _report_completion()メソッド: TaskRegistryClientで完了を報告
    - TaskCompletedイベントの記録
    - RepoPoolClientでスロットを返却
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 15.1, 15.2_

  - [x] 7.5 エラーハンドリングの更新
    - _handle_error()メソッド: エラーを処理
    - TaskRegistryClientでTaskFailedイベントを記録
    - エラーログの保存
    - 外部サービスエラーのハンドリング
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 15.5_

  - [x] 7.6 クリーンアップの更新
    - _cleanup()メソッド: リソースのクリーンアップ
    - 認証情報の削除
    - スロットの返却（エラー時も）
    - _Requirements: 10.3, 15.2_

- [x] 8. 状態管理の実装（変更不要）
  - [x] 8.1 状態遷移
    - _transition_state()メソッド: 状態を遷移
    - 状態遷移の検証
    - _Requirements: 1.5_

  - [x] 8.2 状態の永続化
    - 状態をファイルに保存（オプション）
    - _Requirements: 1.5_

- [x] 9. セキュリティ機能の更新
  - [x] 9.1 認証情報の管理の更新
    - 環境変数からGitトークンを取得
    - 環境変数からLLM APIキーを取得
    - Secret Mountのサポート
    - _Requirements: 1.4, 10.1, 16.1_

  - [x] 9.2 機密情報のマスキング（変更不要）
    - ログから機密情報を自動的にマスク
    - トークン、パスワード、APIキーの検出
    - _Requirements: 10.5_

  - [x] 9.3 権限の制限（変更不要）
    - タスクスコープに限定された権限の使用
    - ワークスペースへのアクセス制限
    - _Requirements: 10.2, 10.4_

- [x] 10. タイムアウトとリソース制限の更新
  - [x] 10.1 タイムアウト機能（変更不要）
    - タスク実行の最大時間を設定
    - タイムアウト時の中断処理
    - _Requirements: 11.1, 11.2_

  - [x] 10.2 リソース監視の更新
    - メモリ使用量の監視
    - CPU使用率の監視
    - LLM呼び出し時間の監視
    - 外部サービス呼び出し時間の監視
    - _Requirements: 11.3, 11.4, 11.5, 16.3_

- [x] 11. ログとモニタリングの更新
  - [x] 11.1 構造化ログの更新
    - LLMリクエスト/レスポンスのログ追加
    - 外部サービス呼び出しのログ追加
    - トークン使用量のログ追加
    - _Requirements: 12.1, 12.2, 12.4, 3.4, 16.4_

  - [x] 11.2 実行メトリクスの更新
    - LLM呼び出し時間の記録
    - 外部サービス呼び出し時間の記録
    - トークン使用量の記録
    - _Requirements: 12.3, 16.4_

  - [x] 11.3 ヘルスチェックの更新
    - 外部サービスの接続チェック
    - LLMサービスの接続チェック
    - _Requirements: 12.5, 15.5, 16.6_

- [x] 12. 実行環境の実装（変更不要）
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

- [x] 13. 並列実行のサポート（変更不要）
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

- [x] 14. ユニットテストの更新
  - [x] 14.1 データモデルのテスト更新
    - test_models.py: 新しいモデル（SlotAllocation、CodeChange、LLMResponse、LLMConfig）のテスト
    - ImplementationResultの新フィールドのテスト
    - _Requirements: 1.1, 16.1_

  - [x] 14.2 外部サービスクライアントのテスト
    - test_llm_client.py: LLMClientのテスト（モックを使用）
    - test_task_registry_client.py: TaskRegistryClientのテスト
    - test_repo_pool_client.py: RepoPoolClientのテスト
    - test_artifact_store_client.py: ArtifactStoreClientのテスト
    - _Requirements: 15.1, 15.2, 15.3, 16.1_

  - [x] 14.3 TaskExecutorのテスト更新
    - test_task_executor.py: LLM連携のテスト（モックを使用）
    - プロンプト構築のテスト
    - コード変更適用のテスト
    - JSONパースエラーのテスト
    - _Requirements: 3.1, 3.2, 3.3, 3.7_

  - [x] 14.4 ArtifactUploaderのテスト更新
    - test_artifact_uploader.py: ArtifactStoreClient統合のテスト
    - TaskRegistryClient統合のテスト
    - _Requirements: 6.1, 6.2, 6.3, 15.1, 15.3_

  - [x] 14.5 RunnerOrchestratorのテスト更新
    - test_runner_orchestrator.py: 外部サービス統合のテスト
    - スロット割り当て・返却のテスト
    - エラーハンドリングのテスト
    - _Requirements: すべて_

- [x] 15. 統合テストの更新
  - [x] 15.1 外部サービス統合テスト
    - test_external_services_integration.py: 実際の外部サービスとの統合テスト
    - Task Registry、Repo Pool Manager、Artifact Storeとの連携テスト
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [x] 15.2 LLM統合テスト
    - test_llm_integration.py: 実際のLLMサービスとの統合テスト
    - レート制限エラーのテスト
    - タイムアウトのテスト
    - _Requirements: 16.1, 16.2, 16.3, 16.5, 16.6_

  - [x] 15.3 エンドツーエンドテスト
    - test_runner_e2e.py: タスク受信から完了までのエンドツーエンドテスト
    - 障害シナリオのテスト（ネットワークエラー、サービス利用不可）
    - _Requirements: すべて_

  - [x] 15.4 パフォーマンステスト更新
    - test_runner_performance.py: 実行時間の測定（LLM呼び出しを含む）
    - test_parallel_runners.py: 並列実行の性能テスト
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 16. ドキュメントとサンプルコードの更新
  - [x] 16.1 APIドキュメントの更新
    - README.mdの更新: 新しいアーキテクチャの説明
    - 外部サービス統合の説明
    - LLM設定の説明
    - 設定ファイル例の追加
    - _Requirements: すべて_

  - [x] 16.2 サンプルコードの更新
    - examples/basic_runner_usage.py: 基本的な使用例（外部サービス統合を含む）
    - examples/llm_integration.py: LLM統合の例
    - examples/external_services.py: 外部サービス統合の例
    - examples/custom_playbook.py: カスタムPlaybookの例
    - _Requirements: すべて_

  - [x] 16.3 設定ファイルサンプル
    - config/config.yaml: 設定ファイルのサンプル
    - config/config.docker.yaml: Docker用設定
    - config/config.k8s.yaml: Kubernetes用設定
    - _Requirements: 15.6, 16.1, 16.2_

  - [x] 16.4 マイグレーションガイド
    - MIGRATION.md: 旧アーキテクチャからの移行ガイド
    - A2A関連コードの削除方法
    - 新しいクライアントの使用方法
    - _Requirements: すべて_

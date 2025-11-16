# Implementation Plan

- [ ] 1. プロジェクト構造とデータモデルの実装
  - necrocode/review_pr_service/ディレクトリを作成
  - データモデル（PullRequest、PRState、CIStatus）をmodels.pyに実装
  - 例外クラス（PRServiceError、AuthenticationError等）をexceptions.pyに実装
  - 設定クラス（PRServiceConfig）をconfig.pyに実装
  - _Requirements: 1.1, 3.5_

- [ ] 2. GitHostClientの実装
  - [ ] 2.1 抽象インターフェース
    - GitHostClient抽象クラスをgit_host_client.pyに実装
    - create_pull_request()、get_ci_status()、add_comment()、add_labels()、assign_reviewers()メソッドを定義
    - _Requirements: 3.1_

  - [ ] 2.2 GitHubClient
    - GitHubClientクラスの実装
    - PyGithubを使用したGitHub API操作
    - _Requirements: 1.4, 3.2_

  - [ ] 2.3 GitLabClient
    - GitLabClientクラスの実装
    - python-gitlabを使用したGitLab API操作
    - _Requirements: 3.3_

  - [ ] 2.4 BitbucketClient
    - BitbucketClientクラスの実装
    - atlassian-python-apiを使用したBitbucket API操作
    - _Requirements: 3.4_

- [ ] 3. PRTemplateEngineの実装
  - [ ] 3.1 テンプレートの読み込み
    - PRTemplateEngineクラスをpr_template_engine.pyに実装
    - Jinja2を使用したテンプレートエンジン
    - _load_template()メソッド: Markdownテンプレートを読み込み
    - _Requirements: 2.1_

  - [ ] 3.2 PR説明文の生成
    - generate()メソッド: PR説明文を生成
    - タスクID、タイトル、説明、受入基準を含める
    - _Requirements: 2.2_

  - [ ] 3.3 テスト結果のフォーマット
    - _format_test_results()メソッド: テスト結果のサマリーを生成
    - _Requirements: 2.3_

  - [ ] 3.4 成果物リンクのフォーマット
    - _format_artifact_links()メソッド: 成果物へのリンクを生成
    - _Requirements: 2.4_

  - [ ] 3.5 カスタムテンプレート
    - カスタムテンプレートのサポート
    - _Requirements: 2.5_

- [ ] 4. PRServiceメインクラスの実装
  - [ ] 4.1 初期化とコンポーネント統合
    - PRServiceクラスをpr_service.pyに実装
    - 各コンポーネント（GitHostClient、PRTemplateEngine等）の初期化
    - _Requirements: 1.1_

  - [ ] 4.2 PR作成機能
    - create_pr()メソッド: PRを作成
    - 成果物のダウンロード
    - PR説明文の生成
    - GitホストAPIを使用したPR作成
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 4.3 Task Registryへの記録
    - _record_pr_created()メソッド: PRのURLをTask Registryに記録
    - _Requirements: 1.5_

  - [ ] 4.4 PR説明文の更新
    - update_pr_description()メソッド: PR説明文を更新
    - 実行ログ、テスト結果、実行時間を追加
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 5. ラベル管理の実装
  - [ ] 5.1 ラベルの自動付与
    - _apply_labels()メソッド: タスクのタイプと優先度に基づいてラベルを付ける
    - _Requirements: 7.1, 7.2_

  - [ ] 5.2 CI状態に基づくラベル更新
    - CI状態に基づいてラベルを更新
    - _Requirements: 7.3_

  - [ ] 5.3 カスタムラベルルール
    - カスタムラベルルールのサポート
    - ラベルの自動付与を無効化
    - _Requirements: 7.4, 7.5_

- [ ] 6. レビュアー割当の実装
  - [ ] 6.1 レビュアーの自動割当
    - _assign_reviewers()メソッド: レビュアーを割り当て
    - タスクのタイプに基づく割当
    - _Requirements: 8.1_

  - [ ] 6.2 CODEOWNERSサポート
    - CODEOWNERSファイルの解析
    - _Requirements: 8.2_

  - [ ] 6.3 ラウンドロビン方式
    - ラウンドロビン方式でレビュアーを割り当て
    - _Requirements: 8.3_

  - [ ] 6.4 負荷分散
    - レビュアーの負荷を考慮した割当
    - レビュアーの自動割当を無効化
    - _Requirements: 8.4, 8.5_

- [ ] 7. CIStatusMonitorの実装
  - [ ] 7.1 CI状態の取得
    - CIStatusMonitorクラスをci_status_monitor.pyに実装
    - monitor_ci_status()メソッド: CI状態を取得
    - _Requirements: 4.1_

  - [ ] 7.2 CI状態の記録
    - CI状態をTask Registryに記録
    - _Requirements: 4.2_

  - [ ] 7.3 CI状態のポーリング
    - CI状態の変化を定期的にポーリング
    - _Requirements: 4.3_

  - [ ] 7.4 CI失敗時の処理
    - CI失敗時にTaskFailedイベントを記録
    - _Requirements: 4.4_

  - [ ] 7.5 CI成功時の処理
    - CI成功時にTaskCompletedイベントを記録
    - _Requirements: 4.5_

- [ ] 8. PRイベント処理の実装
  - [ ] 8.1 PRマージイベントの検出
    - handle_pr_merged()メソッド: PRマージイベントを処理
    - _Requirements: 5.1_

  - [ ] 8.2 PRMergedイベントの記録
    - Task RegistryにPRMergedイベントを記録
    - _Requirements: 5.2_

  - [ ] 8.3 ブランチの削除
    - マージ後にブランチを削除するオプション
    - _Requirements: 5.3_

  - [ ] 8.4 スロットの返却
    - Repo Pool Managerにスロットを返却
    - _Requirements: 5.4_

  - [ ] 8.5 依存タスクの解除
    - 依存タスクのBlocked状態を解除
    - _Requirements: 5.5_

- [ ] 9. レビューコメントの実装
  - [ ] 9.1 自動コメント投稿
    - テスト失敗時にPRにコメントを投稿
    - _Requirements: 6.1_

  - [ ] 9.2 コメント内容
    - テスト失敗の詳細を含める
    - エラーログへのリンクを含める
    - _Requirements: 6.2, 6.3_

  - [ ] 9.3 コメントテンプレート
    - コメントテンプレートのカスタマイズ
    - 自動コメントを無効化
    - _Requirements: 6.4, 6.5_

- [ ] 10. マージ戦略の実装
  - [ ] 10.1 マージ戦略の設定
    - マージ戦略（merge/squash/rebase）の設定
    - _Requirements: 9.1_

  - [ ] 10.2 自動マージ
    - CI成功後の自動マージ
    - _Requirements: 9.2_

  - [ ] 10.3 レビュー承認数の設定
    - 必要なレビュー承認数の設定
    - _Requirements: 9.3_

  - [ ] 10.4 コンフリクト検出
    - マージ前のコンフリクト検出
    - _Requirements: 9.4, 13.1_

  - [ ] 10.5 マージ失敗の処理
    - マージ失敗時のエラー記録
    - _Requirements: 9.5_

- [ ] 11. WebhookHandlerの実装
  - [ ] 11.1 Webhookエンドポイント
    - WebhookHandlerクラスをwebhook_handler.pyに実装
    - HTTPサーバーとしてWebhookエンドポイントを提供
    - _Requirements: 11.1_

  - [ ] 11.2 Webhook署名の検証
    - Webhookの署名を検証
    - _Requirements: 11.2_

  - [ ] 11.3 PRマージイベントの受信
    - PRマージイベントをWebhookから受信
    - _Requirements: 11.3_

  - [ ] 11.4 CI状態変更イベントの受信
    - CI状態変更イベントをWebhookから受信
    - _Requirements: 11.4_

  - [ ] 11.5 非同期処理
    - Webhookイベントを非同期で処理
    - _Requirements: 11.5_

- [ ] 12. ドラフト機能の実装
  - [ ] 12.1 ドラフトPRの作成
    - PRをドラフト状態で作成するオプション
    - _Requirements: 12.1_

  - [ ] 12.2 ドラフトの解除
    - テスト成功後にドラフトを解除
    - _Requirements: 12.2_

  - [ ] 12.3 ドラフトPRの処理
    - ドラフトPRにはレビュアーを割り当てない
    - ドラフトPRには特別なラベルを付ける
    - _Requirements: 12.3, 12.4_

  - [ ] 12.4 ドラフト機能の無効化
    - ドラフト機能を無効化
    - _Requirements: 12.5_

- [ ] 13. コンフリクト検出の実装
  - [ ] 13.1 コンフリクト検出
    - PR作成時にコンフリクトを検出
    - _Requirements: 13.1_

  - [ ] 13.2 コンフリクト通知
    - コンフリクト検出時にPRにコメントを投稿
    - コンフリクトの詳細を記録
    - _Requirements: 13.2, 13.3_

  - [ ] 13.3 コンフリクト再チェック
    - コンフリクト解決後に再チェック
    - 定期的なコンフリクト検出
    - _Requirements: 13.4, 13.5_

- [ ] 14. メトリクス収集の実装
  - [ ] 14.1 PRメトリクスの記録
    - PR作成からマージまでの時間を記録
    - レビューコメント数を記録
    - CI実行時間を記録
    - マージ率を記録
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ] 14.2 Prometheus形式のエクスポート
    - メトリクスをPrometheus形式で出力
    - _Requirements: 14.5_

- [ ] 15. エラーハンドリングとリトライの実装
  - [ ] 15.1 レート制限の処理
    - GitホストAPIのレート制限を検出
    - 待機処理
    - _Requirements: 15.1_

  - [ ] 15.2 ネットワークエラーのリトライ
    - ネットワークエラーを検出
    - 3回までのリトライ
    - 指数バックオフ
    - _Requirements: 15.2, 15.4_

  - [ ] 15.3 認証エラーの処理
    - 認証エラーを検出
    - AuthenticationErrorを投げ
    - _Requirements: 15.3_

  - [ ] 15.4 エラーログ
    - すべてのエラーをログに記録
    - _Requirements: 15.5_

- [ ] 16. ユニットテストの実装
  - [ ] 16.1 データモデルのテスト
    - test_models.py: PullRequest、PRState、CIStatusのシリアライズ/デシリアライズ
    - _Requirements: 1.1_

  - [ ] 16.2 GitHostClientのテスト
    - test_git_host_client.py: 各クライアントのテスト（モックを使用）
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 16.3 PRTemplateEngineのテスト
    - test_pr_template_engine.py: テンプレート生成のテスト
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 16.4 PRServiceのテスト
    - test_pr_service.py: メイン機能のテスト
    - _Requirements: すべて_

  - [ ] 16.5 CIStatusMonitorのテスト
    - test_ci_status_monitor.py: CI監視のテスト
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 16.6 WebhookHandlerのテスト
    - test_webhook_handler.py: Webhook処理のテスト
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 17. 統合テストの実装
  - [ ] 17.1 実際のGitホストAPIでのテスト
    - test_pr_service_integration.py: 実際のGitホストAPIでの統合テスト
    - _Requirements: すべて_

  - [ ] 17.2 Webhook受信テスト
    - test_webhook_integration.py: Webhook受信の統合テスト
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 18. ドキュメントとサンプルコード
  - [ ] 18.1 APIドキュメント
    - README.mdの作成: 使用方法、インストール手順
    - docstringの充実化
    - _Requirements: すべて_

  - [ ] 18.2 サンプルコード
    - examples/basic_pr_service_usage.py: 基本的な使用例
    - examples/github_setup.py: GitHub設定の例
    - examples/webhook_setup.py: Webhook設定の例
    - _Requirements: すべて_

  - [ ] 18.3 テンプレートサンプル
    - templates/pr-template.md: PRテンプレートのサンプル
    - templates/comment-template.md: コメントテンプレートのサンプル
    - _Requirements: 2.1, 2.5, 6.4_

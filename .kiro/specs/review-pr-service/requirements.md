# Requirements Document

## Introduction

Review & PR Serviceは、NecroCodeシステムにおいてAgent Runnerの成果物をもとにPull Requestを自動作成し、テンプレート生成、CI状態の連携、PRイベントのTask Registryへの反映を行うコンポーネントです。GitHub、GitLab、Bitbucketなど複数のGitホストをサポートします。

## Glossary

- **Review & PR Service**: PR自動作成とCI連携を行うコンポーネント
- **Pull Request (PR)**: コードレビューとマージのためのGitホストの機能
- **PR Template**: PRの説明文を自動生成するテンプレート
- **Git Host**: GitHub、GitLab、Bitbucketなどのホスティングサービス
- **CI Status**: 継続的インテグレーションの実行状態
- **PR Event**: PRの作成、更新、マージなどのイベント
- **Review Comment**: PRに対するレビューコメント

## Requirements

### Requirement 1: PRの自動作成

**User Story:** Agent Runnerとして、タスク完了後に自動的にPRを作成したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL Agent Runnerからの完了通知を受け取る
2. THE Review & PR Service SHALL Artifact Storeから成果物（diff、ログ、テスト結果）をダウンロードする
3. THE Review & PR Service SHALL PRテンプレートに基づいて説明文を生成する
4. THE Review & PR Service SHALL GitホストAPIを使用してPRを作成する
5. THE Review & PR Service SHALL 作成したPRのURLをTask Registryに記録する

### Requirement 2: PRテンプレートの生成

**User Story:** システム管理者として、PRの説明文を自動生成するテンプレートを定義したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PRテンプレートをMarkdown形式で定義可能にする
2. THE Review & PR Service SHALL テンプレートにタスクID、タイトル、説明、受入基準を含める
3. THE Review & PR Service SHALL テンプレートにテスト結果のサマリーを含める
4. THE Review & PR Service SHALL テンプレートに成果物へのリンクを含める
5. THE Review & PR Service SHALL カスタムテンプレートをサポートする

### Requirement 3: Gitホストの抽象化

**User Story:** システム管理者として、GitHub、GitLab、Bitbucketなど複数のGitホストをサポートしたい

#### Acceptance Criteria

1. THE Review & PR Service SHALL GitホストAPIの共通インターフェースを定義する
2. THE Review & PR Service SHALL GitHub APIをサポートする
3. THE Review & PR Service SHALL GitLab APIをサポートする
4. THE Review & PR Service SHALL Bitbucket APIをサポートする
5. THE Review & PR Service SHALL 設定ファイルでGitホストを選択可能にする

### Requirement 4: CI状態の連携

**User Story:** システム監視者として、PRのCI実行状態をTask Registryに反映したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PRのCI状態をGitホストから取得する
2. THE Review & PR Service SHALL CI状態（pending/success/failure）をTask Registryに記録する
3. THE Review & PR Service SHALL CI状態の変化を定期的にポーリングする
4. THE Review & PR Service SHALL CI失敗時にTask RegistryにTaskFailedイベントを記録する
5. THE Review & PR Service SHALL CI成功時にTask RegistryにTaskCompletedイベントを記録する

### Requirement 5: PRイベントの処理

**User Story:** システム管理者として、PRのマージやクローズなどのイベントを処理したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PRマージイベントを検出する
2. WHEN PRがマージされる時、THE Review & PR Service SHALL Task RegistryにPRMergedイベントを記録する
3. THE Review & PR Service SHALL マージ後にブランチを削除するオプションを提供する
4. THE Review & PR Service SHALL マージ後にRepo Pool Managerにスロットを返却する
5. THE Review & PR Service SHALL 依存タスクのBlocked状態を解除する

### Requirement 6: レビューコメントの自動投稿

**User Story:** システム管理者として、テスト失敗時に自動的にレビューコメントを投稿したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL テスト失敗時にPRにコメントを投稿する
2. THE Review & PR Service SHALL コメントにテスト失敗の詳細を含める
3. THE Review & PR Service SHALL コメントにエラーログへのリンクを含める
4. THE Review & PR Service SHALL コメントテンプレートをカスタマイズ可能にする
5. THE Review & PR Service SHALL 自動コメントを無効化可能にする

### Requirement 7: PRラベルの管理

**User Story:** システム管理者として、PRに自動的にラベルを付けて分類したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL タスクのタイプ（backend/frontend/database等）に基づいてラベルを付ける
2. THE Review & PR Service SHALL タスクの優先度に基づいてラベルを付ける
3. THE Review & PR Service SHALL CI状態に基づいてラベルを更新する
4. THE Review & PR Service SHALL カスタムラベルルールをサポートする
5. THE Review & PR Service SHALL ラベルの自動付与を無効化可能にする

### Requirement 8: レビュアーの自動割当

**User Story:** システム管理者として、PRに自動的にレビュアーを割り当てたい

#### Acceptance Criteria

1. THE Review & PR Service SHALL タスクのタイプに基づいてレビュアーを割り当てる
2. THE Review & PR Service SHALL CODEOWNERSファイルをサポートする
3. THE Review & PR Service SHALL ラウンドロビン方式でレビュアーを割り当てる
4. THE Review & PR Service SHALL レビュアーの負荷を考慮して割り当てる
5. THE Review & PR Service SHALL レビュアーの自動割当を無効化可能にする

### Requirement 9: PRのマージ戦略

**User Story:** システム管理者として、PRのマージ戦略を設定したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL マージ戦略（merge/squash/rebase）を設定可能にする
2. THE Review & PR Service SHALL CI成功後の自動マージをサポートする
3. THE Review & PR Service SHALL 必要なレビュー承認数を設定可能にする
4. THE Review & PR Service SHALL マージ前のコンフリクト検出を行う
5. THE Review & PR Service SHALL マージ失敗時にエラーを記録する

### Requirement 10: PRの説明文の更新

**User Story:** Agent Runnerとして、タスク実行中にPRの説明文を更新したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PRの説明文を更新するメソッドを提供する
2. THE Review & PR Service SHALL 実行ログへのリンクを追加する
3. THE Review & PR Service SHALL テスト結果のサマリーを更新する
4. THE Review & PR Service SHALL 実行時間を記録する
5. THE Review & PR Service SHALL 更新履歴を保持する

### Requirement 11: Webhookのサポート

**User Story:** システム管理者として、GitホストからのWebhookを受信してイベントを処理したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL WebhookエンドポイントをHTTPサーバーとして提供する
2. THE Review & PR Service SHALL Webhookの署名を検証する
3. THE Review & PR Service SHALL PRマージイベントをWebhookから受信する
4. THE Review & PR Service SHALL CI状態変更イベントをWebhookから受信する
5. THE Review & PR Service SHALL Webhookイベントを非同期で処理する

### Requirement 12: PRのドラフト機能

**User Story:** Agent Runnerとして、実装中のPRをドラフトとして作成したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PRをドラフト状態で作成するオプションを提供する
2. THE Review & PR Service SHALL テスト成功後にドラフトを解除する
3. THE Review & PR Service SHALL ドラフトPRにはレビュアーを割り当てない
4. THE Review & PR Service SHALL ドラフトPRには特別なラベルを付ける
5. THE Review & PR Service SHALL ドラフト機能を無効化可能にする

### Requirement 13: PRのコンフリクト検出

**User Story:** システム管理者として、PRのコンフリクトを早期に検出したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PR作成時にコンフリクトを検出する
2. THE Review & PR Service SHALL コンフリクト検出時にPRにコメントを投稿する
3. THE Review & PR Service SHALL コンフリクトの詳細を記録する
4. THE Review & PR Service SHALL コンフリクト解決後に再チェックする
5. THE Review & PR Service SHALL コンフリクト検出を定期的に実行する

### Requirement 14: PRのメトリクス収集

**User Story:** システム監視者として、PRのメトリクスを収集し、分析したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL PR作成からマージまでの時間を記録する
2. THE Review & PR Service SHALL レビューコメント数を記録する
3. THE Review & PR Service SHALL CI実行時間を記録する
4. THE Review & PR Service SHALL マージ率（マージされたPRの割合）を記録する
5. THE Review & PR Service SHALL メトリクスをPrometheus形式で出力する

### Requirement 15: エラーハンドリングとリトライ

**User Story:** Agent Runnerとして、一時的なエラーを自動的にリトライし、永続的なエラーは適切に報告したい

#### Acceptance Criteria

1. THE Review & PR Service SHALL GitホストAPIのレート制限を検出し、待機する
2. THE Review & PR Service SHALL ネットワークエラーを検出し、3回までリトライする
3. THE Review & PR Service SHALL 認証エラーを検出し、AuthenticationErrorを投げる
4. THE Review & PR Service SHALL リトライ間隔を指数バックオフで増加させる
5. THE Review & PR Service SHALL すべてのエラーをログに記録する

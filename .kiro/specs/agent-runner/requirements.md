# Requirements Document

## Introduction

Agent Runnerは、NecroCodeシステムにおいてタスクを実行するワーカーコンポーネントです。コンテナベースで起動し、Repo Pool Managerから割り当てられたワークスペースをマウントして、fetch→rebase→branch→実装→テスト→pushの一連の処理を自動実行します。完全にステートレスな設計により、水平スケールが可能です。

## Glossary

- **Agent Runner**: タスクを実行するワーカーコンポーネント
- **Runner Instance**: Agent Runnerの1つの実行インスタンス
- **Task Context**: タスク実行に必要な情報（タスクID、説明、受入基準など）
- **Execution Environment**: Runnerが実行される環境（local-process/docker/k8s）
- **Playbook**: タスク実行の手順を定義したスクリプト
- **Artifact**: タスク実行の成果物（diff、ログ、テスト結果）
- **Runner State**: Runnerの現在の状態（Idle/Running/Completed/Failed）

## Requirements

### Requirement 1: タスクの受信と初期化

**User Story:** Dispatcherとして、Agent Runnerにタスクを割り当て、実行を開始させたい

#### Acceptance Criteria

1. THE Agent Runner SHALL タスクコンテキスト（タスクID、説明、受入基準、依存情報）を受信する
2. THE Agent Runner SHALL 受信したタスクコンテキストを検証し、必要な情報が揃っていることを確認する
3. THE Agent Runner SHALL 一意のRunner IDを生成し、Task Registryに登録する
4. THE Agent Runner SHALL 環境変数またはSecret Mountから認証情報（Gitトークン、APIキー）を取得する
5. THE Agent Runner SHALL 初期化完了後、Running状態に遷移する

### Requirement 2: ワークスペースの準備

**User Story:** Agent Runnerとして、Repo Pool Managerから割り当てられたワークスペースを準備したい

#### Acceptance Criteria

1. THE Agent Runner SHALL Repo Pool Managerから割り当てられたスロットパスをマウントする
2. THE Agent Runner SHALL git checkout mainを実行してメインブランチに切り替える
3. THE Agent Runner SHALL git fetch originを実行して最新の変更を取得する
4. THE Agent Runner SHALL git rebase origin/mainを実行してローカルブランチを最新化する
5. THE Agent Runner SHALL 新しいブランチ（feature/task-{spec}-{task-id}）を作成してチェックアウトする

### Requirement 3: タスクの実装

**User Story:** Agent Runnerとして、タスクコンテキストに基づいてコードを実装したい

#### Acceptance Criteria

1. THE Agent Runner SHALL タスクの説明と受入基準をKiroに渡して実装を依頼する
2. THE Agent Runner SHALL Kiroが生成したコードをワークスペースに適用する
3. THE Agent Runner SHALL 実装中のログを記録する
4. THE Agent Runner SHALL 実装が完了したら、変更内容をdiff形式で保存する
5. THE Agent Runner SHALL 実装エラーが発生した場合、エラー情報を記録してFailed状態に遷移する

### Requirement 4: テストの実行

**User Story:** Agent Runnerとして、実装したコードのテストを自動実行したい

#### Acceptance Criteria

1. THE Agent Runner SHALL タスクコンテキストに定義されたテストコマンドを実行する
2. THE Agent Runner SHALL テストの標準出力と標準エラーを記録する
3. THE Agent Runner SHALL テスト結果（成功/失敗、実行時間）を構造化データとして保存する
4. WHEN テストが失敗する時、THE Agent Runner SHALL エラー情報を記録してFailed状態に遷移する
5. THE Agent Runner SHALL テストが成功した場合のみ、次のステップに進む

### Requirement 5: 変更のコミットとプッシュ

**User Story:** Agent Runnerとして、実装した変更をGitリポジトリにコミットしてプッシュしたい

#### Acceptance Criteria

1. THE Agent Runner SHALL git add .を実行してすべての変更をステージングする
2. THE Agent Runner SHALL コミットメッセージを生成する（例: "feat(task-{id}): {title}"）
3. THE Agent Runner SHALL git commitを実行して変更をコミットする
4. THE Agent Runner SHALL git push origin {branch}を実行してリモートにプッシュする
5. THE Agent Runner SHALL プッシュが失敗した場合、リトライを実行し、失敗した場合はエラーを記録する

### Requirement 6: 成果物のアップロード

**User Story:** Agent Runnerとして、タスク実行の成果物をArtifact Storeにアップロードしたい

#### Acceptance Criteria

1. THE Agent Runner SHALL 実装のdiffファイルをArtifact Storeにアップロードする
2. THE Agent Runner SHALL 実行ログファイルをArtifact Storeにアップロードする
3. THE Agent Runner SHALL テスト結果ファイルをArtifact Storeにアップロードする
4. THE Agent Runner SHALL 各成果物のURIをTask Registryに記録する
5. THE Agent Runner SHALL アップロードが失敗した場合、警告を記録するが実行は継続する

### Requirement 7: タスクの完了報告

**User Story:** Agent Runnerとして、タスク実行の結果をTask RegistryとDispatcherに報告したい

#### Acceptance Criteria

1. THE Agent Runner SHALL タスクの状態をTask Registryに更新する（Done/Failed）
2. THE Agent Runner SHALL 実行時間、成果物URI、エラー情報を含む実行サマリーを生成する
3. THE Agent Runner SHALL TaskCompletedまたはTaskFailedイベントをTask Registryに記録する
4. THE Agent Runner SHALL Repo Pool Managerにスロットを返却する
5. THE Agent Runner SHALL Completed状態に遷移し、終了する

### Requirement 8: エラーハンドリングとリトライ

**User Story:** Agent Runnerとして、一時的なエラーを自動的にリトライし、永続的なエラーは適切に報告したい

#### Acceptance Criteria

1. THE Agent Runner SHALL Git操作の失敗を検出し、3回までリトライする
2. THE Agent Runner SHALL ネットワークエラーを検出し、指数バックオフでリトライする
3. THE Agent Runner SHALL リトライ回数の上限に達した場合、Failed状態に遷移する
4. THE Agent Runner SHALL すべてのエラーをログに記録し、Artifact Storeにアップロードする
5. THE Agent Runner SHALL クリティカルエラー（認証失敗、スロット割当失敗）は即座に失敗とする

### Requirement 9: 実行環境の抽象化

**User Story:** システム管理者として、Agent Runnerを複数の実行環境（local-process/docker/k8s）で動作させたい

#### Acceptance Criteria

1. THE Agent Runner SHALL 実行環境に依存しない共通のインターフェースを提供する
2. THE Agent Runner SHALL local-processモードでの実行をサポートする
3. THE Agent Runner SHALL dockerコンテナとしての実行をサポートする
4. THE Agent Runner SHALL Kubernetes Jobとしての実行をサポートする
5. THE Agent Runner SHALL 実行環境固有の設定（リソース制限、環境変数）を受け入れる

### Requirement 10: セキュリティと権限管理

**User Story:** セキュリティ管理者として、Agent Runnerが最小限の権限で動作し、機密情報を適切に扱うようにしたい

#### Acceptance Criteria

1. THE Agent Runner SHALL Gitトークンを環境変数またはSecret Mountから取得し、ログに出力しない
2. THE Agent Runner SHALL タスクスコープに限定された権限（PR作成、ブランチpush）のみを使用する
3. THE Agent Runner SHALL 実行終了時にすべての認証情報をメモリから削除する
4. THE Agent Runner SHALL ワークスペースへのアクセスを読み書き専用に制限する
5. THE Agent Runner SHALL 実行ログから機密情報（トークン、パスワード）を自動的にマスクする

### Requirement 11: タイムアウトとリソース制限

**User Story:** システム管理者として、Agent Runnerの実行時間とリソース使用量を制限したい

#### Acceptance Criteria

1. THE Agent Runner SHALL タスク実行の最大時間（デフォルト: 30分）を設定可能にする
2. WHEN タイムアウトに達する時、THE Agent Runner SHALL 実行を中断し、Failed状態に遷移する
3. THE Agent Runner SHALL メモリ使用量の上限を設定可能にする
4. THE Agent Runner SHALL CPU使用率の上限を設定可能にする
5. THE Agent Runner SHALL リソース制限に達した場合、警告を記録する

### Requirement 12: ログとモニタリング

**User Story:** システム監視者として、Agent Runnerの実行状況をリアルタイムで監視したい

#### Acceptance Criteria

1. THE Agent Runner SHALL 実行の各ステップ（初期化、実装、テスト、プッシュ）の開始と終了をログに記録する
2. THE Agent Runner SHALL 構造化ログ（JSON形式）を出力する
3. THE Agent Runner SHALL 実行メトリクス（実行時間、メモリ使用量、CPU使用率）を記録する
4. THE Agent Runner SHALL ログレベル（DEBUG/INFO/WARNING/ERROR）を設定可能にする
5. THE Agent Runner SHALL ヘルスチェックエンドポイントを提供する（Kubernetes用）

### Requirement 13: Playbookのサポート

**User Story:** システム管理者として、タスクタイプごとに異なる実行手順を定義したい

#### Acceptance Criteria

1. THE Agent Runner SHALL Playbookファイル（YAML形式）を読み込む
2. THE Agent Runner SHALL Playbookに定義されたステップを順次実行する
3. THE Agent Runner SHALL Playbookのステップごとにカスタムコマンドを実行可能にする
4. THE Agent Runner SHALL Playbookの条件分岐（if/else）をサポートする
5. THE Agent Runner SHALL デフォルトPlaybookを提供し、カスタムPlaybookで上書き可能にする

### Requirement 14: 並列実行のサポート

**User Story:** Dispatcherとして、複数のAgent Runnerを並列実行し、タスクを高速に処理したい

#### Acceptance Criteria

1. THE Agent Runner SHALL 完全にステートレスな設計により、複数インスタンスの並列実行をサポートする
2. THE Agent Runner SHALL 他のRunnerインスタンスと競合しないように、独立したワークスペースを使用する
3. THE Agent Runner SHALL 並列実行時のリソース競合を検出し、適切に処理する
4. THE Agent Runner SHALL 並列実行のメトリクス（同時実行数、待機時間）を記録する
5. THE Agent Runner SHALL 最大並列実行数を設定可能にする

# Requirements Document

## Introduction

Artifact Storeは、NecroCodeシステムにおいてAgent Runnerが生成した成果物（diff、ログ、テスト結果）を保管するストレージコンポーネントです。ファイルシステムベースの実装を基本とし、将来的にはS3やGCSなどのクラウドストレージもサポートします。成果物のメタデータ管理、検索、クリーンアップ機能を提供します。

## Glossary

- **Artifact Store**: 成果物を保管するストレージコンポーネント
- **Artifact**: タスク実行の成果物（diff、ログ、テスト結果）
- **Artifact Type**: 成果物のタイプ（diff/log/test）
- **Storage Backend**: ストレージの実装（filesystem/s3/gcs）
- **Artifact URI**: 成果物の一意な識別子（例: file://~/.necrocode/artifacts/chat-app/1.1/diff.txt）
- **Retention Policy**: 成果物の保持期間ポリシー
- **Artifact Metadata**: 成果物のメタデータ（サイズ、作成日時、タスクID等）

## Requirements

### Requirement 1: 成果物のアップロード

**User Story:** Agent Runnerとして、タスク実行の成果物をArtifact Storeにアップロードしたい

#### Acceptance Criteria

1. THE Artifact Store SHALL diff、ログ、テスト結果の3種類の成果物をサポートする
2. THE Artifact Store SHALL 成果物をタスクIDとタイプに基づいて整理して保存する
3. THE Artifact Store SHALL アップロード時に成果物のメタデータ（サイズ、作成日時、MIME type）を記録する
4. THE Artifact Store SHALL アップロード完了後、成果物のURIを返す
5. THE Artifact Store SHALL 同じタスクIDとタイプの成果物が既に存在する場合、上書きする

### Requirement 2: 成果物のダウンロード

**User Story:** Review & PR Serviceとして、成果物をダウンロードしてPR作成に使用したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 成果物のURIを指定してダウンロードするメソッドを提供する
2. THE Artifact Store SHALL 成果物が存在しない場合、ArtifactNotFoundErrorを投げる
3. THE Artifact Store SHALL ダウンロード時に成果物の内容をバイト列またはストリームで返す
4. THE Artifact Store SHALL 大きな成果物（>10MB）のストリーミングダウンロードをサポートする
5. THE Artifact Store SHALL ダウンロード失敗時にリトライを実行する

### Requirement 3: 成果物のメタデータ管理

**User Story:** システム管理者として、成果物のメタデータを検索し、管理したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 成果物のメタデータをJSON形式で保存する
2. THE Artifact Store SHALL メタデータにタスクID、Spec名、タイプ、サイズ、作成日時、MIME typeを含める
3. THE Artifact Store SHALL 成果物のURIからメタデータを取得するメソッドを提供する
4. THE Artifact Store SHALL タスクIDに関連するすべての成果物のメタデータを取得するメソッドを提供する
5. THE Artifact Store SHALL Spec名に関連するすべての成果物のメタデータを取得するメソッドを提供する

### Requirement 4: 成果物の検索

**User Story:** システム監査者として、特定の条件に合致する成果物を検索したい

#### Acceptance Criteria

1. THE Artifact Store SHALL タスクIDで成果物を検索するメソッドを提供する
2. THE Artifact Store SHALL Spec名で成果物を検索するメソッドを提供する
3. THE Artifact Store SHALL 成果物のタイプで成果物を検索するメソッドを提供する
4. THE Artifact Store SHALL 作成日時の範囲で成果物を検索するメソッドを提供する
5. THE Artifact Store SHALL 複数の条件を組み合わせた検索をサポートする

### Requirement 5: 成果物の削除

**User Story:** システム管理者として、不要な成果物を削除してストレージを節約したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 成果物のURIを指定して削除するメソッドを提供する
2. THE Artifact Store SHALL タスクIDに関連するすべての成果物を削除するメソッドを提供する
3. THE Artifact Store SHALL Spec名に関連するすべての成果物を削除するメソッドを提供する
4. THE Artifact Store SHALL 削除時にメタデータも同時に削除する
5. THE Artifact Store SHALL 削除された成果物の数を返す

### Requirement 6: 保持期間ポリシー

**User Story:** システム管理者として、成果物の保持期間を設定し、古い成果物を自動的に削除したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 成果物の保持期間をタイプごとに設定可能にする
2. THE Artifact Store SHALL デフォルトの保持期間（diff: 30日、log: 7日、test: 14日）を提供する
3. THE Artifact Store SHALL 保持期間を過ぎた成果物を検出するメソッドを提供する
4. THE Artifact Store SHALL 保持期間を過ぎた成果物を自動的に削除するクリーンアップ機能を提供する
5. THE Artifact Store SHALL クリーンアップの実行ログを記録する

### Requirement 7: ストレージバックエンドの抽象化

**User Story:** システム管理者として、ファイルシステム、S3、GCSなど複数のストレージバックエンドをサポートしたい

#### Acceptance Criteria

1. THE Artifact Store SHALL ストレージバックエンドの共通インターフェースを定義する
2. THE Artifact Store SHALL ファイルシステムベースのストレージバックエンドを実装する
3. THE Artifact Store SHALL S3互換のストレージバックエンドを実装する
4. THE Artifact Store SHALL GCS互換のストレージバックエンドを実装する
5. THE Artifact Store SHALL 設定ファイルでストレージバックエンドを選択可能にする

### Requirement 8: 成果物の圧縮

**User Story:** システム管理者として、ストレージ容量を節約するために成果物を圧縮したい

#### Acceptance Criteria

1. THE Artifact Store SHALL アップロード時に成果物を自動的に圧縮するオプションを提供する
2. THE Artifact Store SHALL gzip圧縮をサポートする
3. THE Artifact Store SHALL ダウンロード時に自動的に解凍する
4. THE Artifact Store SHALL 圧縮前後のサイズをメタデータに記録する
5. THE Artifact Store SHALL 圧縮を無効化可能にする

### Requirement 9: 成果物の整合性検証

**User Story:** システム管理者として、成果物の整合性を検証し、破損を検出したい

#### Acceptance Criteria

1. THE Artifact Store SHALL アップロード時に成果物のチェックサム（SHA256）を計算する
2. THE Artifact Store SHALL チェックサムをメタデータに保存する
3. THE Artifact Store SHALL ダウンロード時にチェックサムを検証するオプションを提供する
4. WHEN チェックサムが一致しない時、THE Artifact Store SHALL IntegrityErrorを投げる
5. THE Artifact Store SHALL すべての成果物の整合性を検証するメソッドを提供する

### Requirement 10: ストレージ使用量の監視

**User Story:** システム管理者として、ストレージの使用量を監視し、容量不足を検出したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 現在のストレージ使用量を取得するメソッドを提供する
2. THE Artifact Store SHALL Spec名ごとのストレージ使用量を取得するメソッドを提供する
3. THE Artifact Store SHALL 成果物のタイプごとのストレージ使用量を取得するメソッドを提供する
4. THE Artifact Store SHALL ストレージ使用量の上限を設定可能にする
5. WHEN ストレージ使用量が上限に達する時、THE Artifact Store SHALL 警告を記録する

### Requirement 11: 並行アクセスの制御

**User Story:** 複数のAgent Runnerが同時にアップロードする環境で、データの整合性を保ちたい

#### Acceptance Criteria

1. THE Artifact Store SHALL 同じ成果物への同時書き込みを検出する
2. THE Artifact Store SHALL ファイルベースのロック機構を使用して同時書き込みを防止する
3. THE Artifact Store SHALL ロック取得のタイムアウトを設定可能にする
4. THE Artifact Store SHALL ロック取得失敗時にリトライを実行する
5. THE Artifact Store SHALL 読み取り操作はロックなしで実行可能にする

### Requirement 12: 成果物のバージョニング

**User Story:** システム管理者として、同じタスクの成果物の複数バージョンを保持したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 成果物のバージョニングを有効化するオプションを提供する
2. WHEN バージョニングが有効な時、THE Artifact Store SHALL 上書きではなく新しいバージョンとして保存する
3. THE Artifact Store SHALL 成果物の全バージョンを取得するメソッドを提供する
4. THE Artifact Store SHALL 特定のバージョンを指定してダウンロードするメソッドを提供する
5. THE Artifact Store SHALL 古いバージョンを削除するメソッドを提供する

### Requirement 13: 成果物のタグ付け

**User Story:** システム管理者として、成果物にタグを付けて分類したい

#### Acceptance Criteria

1. THE Artifact Store SHALL 成果物にカスタムタグを付けるメソッドを提供する
2. THE Artifact Store SHALL タグをメタデータに保存する
3. THE Artifact Store SHALL タグで成果物を検索するメソッドを提供する
4. THE Artifact Store SHALL 成果物のタグを更新するメソッドを提供する
5. THE Artifact Store SHALL 成果物のタグを削除するメソッドを提供する

### Requirement 14: 成果物のエクスポート

**User Story:** システム管理者として、成果物をまとめてエクスポートしたい

#### Acceptance Criteria

1. THE Artifact Store SHALL Spec名に関連するすべての成果物をZIPファイルにエクスポートするメソッドを提供する
2. THE Artifact Store SHALL タスクIDに関連するすべての成果物をZIPファイルにエクスポートするメソッドを提供する
3. THE Artifact Store SHALL エクスポート時にメタデータも含める
4. THE Artifact Store SHALL エクスポートの進捗を報告する
5. THE Artifact Store SHALL エクスポートしたZIPファイルのパスを返す

### Requirement 15: エラーハンドリングとリトライ

**User Story:** Agent Runnerとして、一時的なエラーを自動的にリトライし、永続的なエラーは適切に報告したい

#### Acceptance Criteria

1. THE Artifact Store SHALL ネットワークエラーを検出し、3回までリトライする
2. THE Artifact Store SHALL ストレージ容量不足エラーを検出し、StorageFullErrorを投げる
3. THE Artifact Store SHALL 権限エラーを検出し、PermissionErrorを投げる
4. THE Artifact Store SHALL リトライ間隔を指数バックオフで増加させる
5. THE Artifact Store SHALL すべてのエラーをログに記録する

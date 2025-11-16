# Requirements Document

## Introduction

Task Registryは、NecroCodeシステムにおけるタスクの状態管理、バージョン管理、イベント履歴を一元管理する永続ストレージコンポーネントです。複数のタスクセットを管理し、各タスクの状態遷移（Ready/Running/Blocked/Done）を追跡し、失敗時の再実行や監査を容易にします。

## Glossary

- **Task Registry**: タスクセットのバージョン管理、状態管理、イベント履歴を保持する永続ストアコンポーネント
- **Taskset**: 1つのSpecから生成されたタスクの集合
- **Task**: 実装可能な最小単位の作業項目
- **Task State**: タスクの現在の状態（Ready/Running/Blocked/Done）
- **Event**: タスクの状態変化やシステムイベントの記録
- **Artifact**: タスク実行の成果物（diff、ログ、テスト結果など）
- **Slot**: Repo Pool Managerが管理するワークスペースの割当単位
- **Runner**: タスクを実行するエージェントワーカー

## Requirements

### Requirement 1: タスクセットの永続化

**User Story:** システム管理者として、タスクセットをJSON形式で永続化し、システム再起動後も状態を復元できるようにしたい

#### Acceptance Criteria

1. WHEN タスクセットが作成される時、THE Task Registry SHALL タスクセットをJSON形式でファイルシステムに保存する
2. THE Task Registry SHALL タスクセットのバージョン番号を管理し、更新のたびにインクリメントする
3. WHEN システムが再起動される時、THE Task Registry SHALL 保存されたタスクセットを読み込み、状態を復元する
4. THE Task Registry SHALL 各タスクに一意のIDを割り当て、重複を防止する
5. THE Task Registry SHALL タスクセットのメタデータ（作成日時、最終更新日時、Spec名）を保存する

### Requirement 2: タスク状態管理

**User Story:** Dispatcherとして、タスクの状態を更新し、実行可能なタスクを取得できるようにしたい

#### Acceptance Criteria

1. THE Task Registry SHALL タスクの状態をReady、Running、Blocked、Doneの4つの状態で管理する
2. WHEN タスクの状態が更新される時、THE Task Registry SHALL 状態遷移の妥当性を検証する
3. THE Task Registry SHALL Ready状態のタスクのリストを取得するメソッドを提供する
4. WHEN タスクがRunning状態に遷移する時、THE Task Registry SHALL assigned_slot、reserved_branch、runner_idを記録する
5. WHEN タスクがDone状態に遷移する時、THE Task Registry SHALL 依存する他のタスクのBlocked状態を解除する

### Requirement 3: 依存関係の管理

**User Story:** Task Plannerとして、タスク間の依存関係を定義し、実行順序を制御したい

#### Acceptance Criteria

1. THE Task Registry SHALL 各タスクの依存タスクIDのリストを保存する
2. THE Task Registry SHALL タスクの依存関係が循環参照していないことを検証する
3. WHEN 依存タスクがすべてDone状態になる時、THE Task Registry SHALL 依存先タスクの状態をBlockedからReadyに更新する
4. THE Task Registry SHALL 依存関係を考慮したタスクの実行順序を計算するメソッドを提供する
5. THE Task Registry SHALL 依存関係グラフを可視化可能な形式で出力する

### Requirement 4: イベント履歴の記録

**User Story:** システム監査者として、すべてのタスクイベントを時系列で記録し、障害調査に活用したい

#### Acceptance Criteria

1. THE Task Registry SHALL TaskCreated、TaskUpdated、TaskReady、TaskAssigned、TaskCompleted、TaskFailedのイベントを記録する
2. WHEN イベントが発生する時、THE Task Registry SHALL イベントタイプ、タスクID、タイムスタンプ、詳細情報をJSON Lines形式で保存する
3. THE Task Registry SHALL 特定のタスクIDに関連するすべてのイベントを取得するメソッドを提供する
4. THE Task Registry SHALL 特定の期間内のイベントを取得するメソッドを提供する
5. THE Task Registry SHALL イベントログファイルのローテーション機能を提供する

### Requirement 5: 成果物の参照管理

**User Story:** Agent Runnerとして、タスク実行の成果物（diff、ログ、テスト結果）への参照を保存したい

#### Acceptance Criteria

1. THE Task Registry SHALL 各タスクに関連する成果物のURIリストを保存する
2. WHEN 成果物が追加される時、THE Task Registry SHALL 成果物のタイプ（diff/log/test）とURIを記録する
3. THE Task Registry SHALL タスクIDから成果物のURIリストを取得するメソッドを提供する
4. THE Task Registry SHALL 成果物の存在確認を行わず、URIの記録のみを行う
5. THE Task Registry SHALL 成果物のメタデータ（サイズ、作成日時）を保存する

### Requirement 6: 並行アクセスの制御

**User Story:** 複数のDispatcherとRunnerが同時にアクセスする環境で、データの整合性を保ちたい

#### Acceptance Criteria

1. THE Task Registry SHALL ファイルベースのロック機構を使用して、同時書き込みを防止する
2. WHEN タスク状態の更新が競合する時、THE Task Registry SHALL 楽観的ロックを使用してエラーを返す
3. THE Task Registry SHALL ロック取得のタイムアウトを設定可能にする
4. THE Task Registry SHALL ロック取得失敗時にリトライ機能を提供する
5. THE Task Registry SHALL デッドロックを検出し、自動的に解除する

### Requirement 7: クエリとフィルタリング

**User Story:** Dispatcherとして、特定の条件に合致するタスクを効率的に検索したい

#### Acceptance Criteria

1. THE Task Registry SHALL タスクの状態でフィルタリングするメソッドを提供する
2. THE Task Registry SHALL required_skillでフィルタリングするメソッドを提供する
3. THE Task Registry SHALL 優先度でソートされたタスクリストを取得するメソッドを提供する
4. THE Task Registry SHALL 複数の条件を組み合わせたクエリをサポートする
5. THE Task Registry SHALL クエリ結果をページネーション可能にする

### Requirement 8: Kiro Specとの同期

**User Story:** Task Plannerとして、Kiroの.kiro/specs/{spec-name}/tasks.mdと Task Registryを双方向で同期させたい

#### Acceptance Criteria

1. WHEN Kiroのtasks.mdファイルが更新される時、THE Task Registry SHALL 変更を検出し、タスクセットを更新する
2. THE Task Registry SHALL tasks.mdのチェックボックス状態（[ ]、[x]）をタスクの状態（Ready/Done）にマッピングする
3. WHEN Task Registryのタスク状態が更新される時、THE Task Registry SHALL 対応するtasks.mdのチェックボックスを更新する
4. THE Task Registry SHALL tasks.mdのタスク番号（1.1、1.2など）とTask Registry内部のタスクIDを関連付ける
5. THE Task Registry SHALL tasks.mdの依存関係情報（Requirements: X.Y）を解析し、依存関係グラフを構築する
6. THE Task Registry SHALL tasks.mdのオプショナルタスク（*マーク）を識別し、メタデータに記録する
7. WHEN tasks.mdに新しいタスクが追加される時、THE Task Registry SHALL 自動的に新しいタスクエントリを作成する

### Requirement 9: バックアップとリストア

**User Story:** システム管理者として、Task Registryのデータをバックアップし、障害時に復元したい

#### Acceptance Criteria

1. THE Task Registry SHALL タスクセットとイベントログを含む完全なバックアップを作成するメソッドを提供する
2. THE Task Registry SHALL バックアップファイルから状態を復元するメソッドを提供する
3. THE Task Registry SHALL バックアップファイルの整合性を検証する
4. THE Task Registry SHALL 増分バックアップをサポートする
5. THE Task Registry SHALL バックアップの自動スケジューリング機能を提供する

# Requirements Document

## Introduction

Repo Pool Managerは、NecroCodeシステムにおいて複数のワークスペーススロットを管理し、Agent Runnerへの割当・返却・クリーンアップを行うコンポーネントです。ローカルマシン上に複数のリポジトリクローンを保持し、排他制御により同一スロットの二重利用を防止します。

## Glossary

- **Repo Pool Manager**: ワークスペーススロットの管理、割当、クリーンアップを行うコンポーネント
- **Slot**: 1つのリポジトリクローンを含むワークスペースの割当単位
- **Pool**: 特定のリポジトリに対する複数のスロットの集合
- **Slot Lock**: スロットの排他制御用ロックファイル
- **Workspace**: Agent Runnerが作業を行うGitリポジトリのクローン
- **Slot State**: スロットの現在の状態（Available/Allocated/Cleaning）

## Requirements

### Requirement 1: スロットの初期化と管理

**User Story:** システム管理者として、リポジトリごとに複数のスロットを初期化し、管理できるようにしたい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL リポジトリURLとスロット数を指定してプールを作成する
2. WHEN プールが作成される時、THE Repo Pool Manager SHALL 各スロットのディレクトリを作成し、リポジトリをクローンする
3. THE Repo Pool Manager SHALL スロットのメタデータ（リポジトリURL、作成日時、最終使用日時）を保存する
4. THE Repo Pool Manager SHALL スロットに一意の識別子（例: workspace-{repo}-slot1）を割り当てる
5. THE Repo Pool Manager SHALL プール内のすべてのスロット情報を取得するメソッドを提供する

### Requirement 2: スロットの割当と返却

**User Story:** Dispatcherとして、利用可能なスロットを取得し、使用後に返却できるようにしたい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL 利用可能なスロットを取得するメソッドを提供する
2. WHEN スロットが割り当てられる時、THE Repo Pool Manager SHALL スロットをAllocated状態にし、ロックファイルを作成する
3. THE Repo Pool Manager SHALL 割り当てたスロットのパスとメタデータを返却する
4. WHEN スロットが返却される時、THE Repo Pool Manager SHALL ロックファイルを削除し、スロットをAvailable状態にする
5. THE Repo Pool Manager SHALL スロットの割当履歴を記録する

### Requirement 3: スロットのクリーンアップ

**User Story:** Agent Runnerとして、スロット使用前後に自動的にクリーンアップが実行されるようにしたい

#### Acceptance Criteria

1. WHEN スロットが割り当てられる時、THE Repo Pool Manager SHALL git fetch --allを実行して最新の状態に更新する
2. THE Repo Pool Manager SHALL git clean -fdxを実行して未追跡ファイルを削除する
3. THE Repo Pool Manager SHALL git reset --hardを実行してワーキングディレクトリをリセットする
4. WHEN スロットが返却される時、THE Repo Pool Manager SHALL 同様のクリーンアップを実行する
5. THE Repo Pool Manager SHALL クリーンアップの実行ログを記録する

### Requirement 4: 排他制御とロック機構

**User Story:** 複数のDispatcherが同時にスロットを要求する環境で、同一スロットの二重割当を防止したい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL ファイルベースのロック（slot.lock）を使用してスロットの排他制御を行う
2. WHEN スロットが既に割り当てられている時、THE Repo Pool Manager SHALL 他のスロットを探すか、利用可能なスロットがない場合はNoneを返す
3. THE Repo Pool Manager SHALL ロック取得のタイムアウトを設定可能にする
4. THE Repo Pool Manager SHALL デッドロックを検出し、古いロックを自動的に解除する
5. THE Repo Pool Manager SHALL ロックの状態を確認するメソッドを提供する

### Requirement 5: スロットの状態管理

**User Story:** システム監視者として、各スロットの状態を確認し、問題のあるスロットを特定したい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL スロットの状態をAvailable、Allocated、Cleaningの3つの状態で管理する
2. THE Repo Pool Manager SHALL 各スロットの現在の状態を取得するメソッドを提供する
3. THE Repo Pool Manager SHALL スロットの使用統計（割当回数、総使用時間）を記録する
4. THE Repo Pool Manager SHALL 特定のリポジトリの利用可能なスロット数を取得するメソッドを提供する
5. THE Repo Pool Manager SHALL すべてのプールの状態をサマリー形式で出力する

### Requirement 6: Gitリポジトリの操作

**User Story:** Agent Runnerとして、スロット内のGitリポジトリを安全に操作できるようにしたい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL スロット内でgit checkoutを実行してブランチを切り替えるメソッドを提供する
2. THE Repo Pool Manager SHALL 現在のブランチ名を取得するメソッドを提供する
3. THE Repo Pool Manager SHALL 最新のコミットハッシュを取得するメソッドを提供する
4. THE Repo Pool Manager SHALL リモートブランチの一覧を取得するメソッドを提供する
5. THE Repo Pool Manager SHALL Git操作のエラーを適切に処理し、エラーメッセージを返す

### Requirement 7: スロットの動的追加と削除

**User Story:** システム管理者として、実行時にスロットを追加または削除できるようにしたい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL 既存のプールに新しいスロットを追加するメソッドを提供する
2. WHEN 新しいスロットが追加される時、THE Repo Pool Manager SHALL リポジトリをクローンし、初期化する
3. THE Repo Pool Manager SHALL 使用されていないスロットを削除するメソッドを提供する
4. WHEN スロットが削除される時、THE Repo Pool Manager SHALL スロットがAllocated状態でないことを確認する
5. THE Repo Pool Manager SHALL 削除されたスロットのディレクトリを完全に削除する

### Requirement 8: プールの設定管理

**User Story:** システム管理者として、プールの設定をファイルで管理し、起動時に自動的にロードしたい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL プール設定をYAML形式で保存する
2. THE Repo Pool Manager SHALL 起動時に設定ファイルから複数のプールを自動的に初期化する
3. THE Repo Pool Manager SHALL プール設定の変更を検出し、動的に反映する
4. THE Repo Pool Manager SHALL 設定ファイルのバリデーションを行い、不正な設定を拒否する
5. THE Repo Pool Manager SHALL デフォルト設定（スロット数、クリーンアップオプション）を提供する

### Requirement 9: エラーハンドリングとリカバリ

**User Story:** システム管理者として、スロットの異常状態を検出し、自動的に復旧できるようにしたい

#### Acceptance Criteria

1. WHEN Gitクローンが失敗する時、THE Repo Pool Manager SHALL リトライを実行し、失敗した場合はエラーを記録する
2. THE Repo Pool Manager SHALL 破損したスロットを検出し、再初期化するメソッドを提供する
3. THE Repo Pool Manager SHALL 長時間Allocated状態のスロットを検出し、警告を発する
4. THE Repo Pool Manager SHALL 孤立したロックファイルを検出し、自動的に削除する
5. THE Repo Pool Manager SHALL エラー発生時にスロットを隔離し、手動介入を要求する

### Requirement 10: パフォーマンスと最適化

**User Story:** システム管理者として、スロットの割当とクリーンアップを高速に実行したい

#### Acceptance Criteria

1. THE Repo Pool Manager SHALL git fetch --allを並列実行してクリーンアップ時間を短縮する
2. THE Repo Pool Manager SHALL 最近使用されたスロットを優先的に割り当てる（LRUキャッシュ戦略）
3. THE Repo Pool Manager SHALL スロットの事前ウォームアップ機能を提供する
4. THE Repo Pool Manager SHALL クリーンアップをバックグラウンドで実行するオプションを提供する
5. THE Repo Pool Manager SHALL スロット割当の平均時間を測定し、メトリクスとして記録する

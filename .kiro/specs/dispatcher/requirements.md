# Requirements Document

## Introduction

Dispatcherは、NecroCodeシステムにおいてタスクのスケジューリングとAgent Runnerへの割当を行うコンポーネントです。Task RegistryからReadyタスクを監視し、必要スキルと利用可能なAgent Poolに基づいて実行予約を行い、Repo Pool Managerからスロットを確保してAgent Runnerに情報を渡します。

## Glossary

- **Dispatcher**: タスクスケジューリングとAgent Runnerへの割当を行うコンポーネント
- **Agent Pool**: Agent Runnerのプール定義（local-process/docker/k8s等）
- **Task Queue**: 実行待ちタスクのキュー
- **Scheduling Policy**: タスクの実行順序を決定するポリシー（FIFO/Priority/Skill-based）
- **Concurrency Limit**: Agent Poolごとの最大同時実行数
- **Task Assignment**: タスクをAgent Runnerに割り当てる処理
- **Heartbeat**: Agent Runnerの生存確認

## Requirements

### Requirement 1: タスクの監視と取得

**User Story:** Dispatcherとして、Task RegistryからReadyタスクを定期的に監視し、実行可能なタスクを取得したい

#### Acceptance Criteria

1. THE Dispatcher SHALL Task Registryを定期的にポーリングし、Ready状態のタスクを取得する
2. THE Dispatcher SHALL ポーリング間隔を設定可能にする（デフォルト: 5秒）
3. THE Dispatcher SHALL 取得したタスクを優先度順にソートする
4. THE Dispatcher SHALL 依存関係が解決されたタスクのみを取得する
5. THE Dispatcher SHALL 取得したタスクをTask Queueに追加する

### Requirement 2: Agent Poolの管理

**User Story:** システム管理者として、複数のAgent Pool（local-process/docker/k8s）を定義し、管理したい

#### Acceptance Criteria

1. THE Dispatcher SHALL Agent Pool設定をYAML形式で読み込む
2. THE Dispatcher SHALL 各Agent Poolの最大同時実行数を管理する
3. THE Dispatcher SHALL 各Agent Poolの現在の実行中タスク数を追跡する
4. THE Dispatcher SHALL Agent Poolごとのリソースクォータ（CPU、メモリ）を管理する
5. THE Dispatcher SHALL Agent Poolの有効/無効を動的に切り替える

### Requirement 3: スキルベースのルーティング

**User Story:** Dispatcherとして、タスクの必要スキルに基づいて適切なAgent Poolを選択したい

#### Acceptance Criteria

1. THE Dispatcher SHALL タスクのrequired_skillフィールドを読み取る
2. THE Dispatcher SHALL スキルとAgent Poolのマッピング設定を管理する
3. THE Dispatcher SHALL 複数のAgent Poolが対応可能な場合、負荷分散を行う
4. THE Dispatcher SHALL 対応可能なAgent Poolがない場合、警告を記録する
5. THE Dispatcher SHALL デフォルトAgent Poolを設定可能にする

### Requirement 4: スロットの割当

**User Story:** Dispatcherとして、Repo Pool Managerから利用可能なスロットを取得し、タスクに割り当てたい

#### Acceptance Criteria

1. THE Dispatcher SHALL Repo Pool Managerにスロット割当を要求する
2. WHEN スロットが利用可能な時、THE Dispatcher SHALL スロット情報（slot_id、slot_path）を取得する
3. WHEN スロットが利用不可能な時、THE Dispatcher SHALL タスクをキューに戻し、後で再試行する
4. THE Dispatcher SHALL 割り当てたスロット情報をTask Registryに記録する
5. THE Dispatcher SHALL スロット割当の失敗をログに記録する

### Requirement 5: Agent Runnerの起動

**User Story:** Dispatcherとして、選択したAgent PoolでAgent Runnerを起動し、タスクを実行させたい

#### Acceptance Criteria

1. THE Dispatcher SHALL Agent Poolの種類（local-process/docker/k8s）に応じてAgent Runnerを起動する
2. THE Dispatcher SHALL タスクコンテキストとスロット情報をAgent Runnerに渡す
3. THE Dispatcher SHALL Agent RunnerにRunner IDを割り当てる
4. THE Dispatcher SHALL 起動したAgent Runnerの情報をTask Registryに記録する
5. THE Dispatcher SHALL Agent Runnerの起動失敗を検出し、リトライまたはエラー報告を行う

### Requirement 6: 並行実行の制御

**User Story:** Dispatcherとして、Agent Poolごとの最大同時実行数を超えないように制御したい

#### Acceptance Criteria

1. THE Dispatcher SHALL 各Agent Poolの現在の実行中タスク数を追跡する
2. WHEN Agent Poolの最大同時実行数に達している時、THE Dispatcher SHALL 新しいタスクの割当を待機する
3. THE Dispatcher SHALL Agent Runnerの完了通知を受け取り、実行中タスク数をデクリメントする
4. THE Dispatcher SHALL グローバルな最大同時実行数も設定可能にする
5. THE Dispatcher SHALL 並行実行数のメトリクスを記録する

### Requirement 7: タスクの優先度管理

**User Story:** Dispatcherとして、タスクの優先度に基づいて実行順序を制御したい

#### Acceptance Criteria

1. THE Dispatcher SHALL タスクの優先度フィールドを読み取る
2. THE Dispatcher SHALL 優先度の高いタスクを優先的に割り当てる
3. THE Dispatcher SHALL 同じ優先度のタスクはFIFO順で処理する
4. THE Dispatcher SHALL 優先度の動的な変更をサポートする
5. THE Dispatcher SHALL 優先度ベースのスケジューリングを無効化可能にする

### Requirement 8: Agent Runnerの監視

**User Story:** Dispatcherとして、実行中のAgent Runnerを監視し、異常を検出したい

#### Acceptance Criteria

1. THE Dispatcher SHALL Agent Runnerからのハートビートを定期的に受信する
2. WHEN ハートビートが一定時間途絶える時、THE Dispatcher SHALL Agent Runnerを異常と判定する
3. THE Dispatcher SHALL 異常なAgent Runnerのタスクを再割当する
4. THE Dispatcher SHALL Agent Runnerの実行時間を監視し、タイムアウトを検出する
5. THE Dispatcher SHALL Agent Runnerの状態（Running/Completed/Failed）を追跡する

### Requirement 9: タスクの再試行

**User Story:** Dispatcherとして、失敗したタスクを自動的に再試行したい

#### Acceptance Criteria

1. THE Dispatcher SHALL タスクの失敗通知を受け取る
2. THE Dispatcher SHALL タスクの再試行回数を追跡する
3. WHEN 再試行回数が上限未満の時、THE Dispatcher SHALL タスクをキューに戻す
4. WHEN 再試行回数が上限に達する時、THE Dispatcher SHALL タスクをFailed状態にする
5. THE Dispatcher SHALL 再試行間隔を指数バックオフで増加させる

### Requirement 10: イベントの記録

**User Story:** システム監査者として、Dispatcherのすべての操作をイベントとして記録したい

#### Acceptance Criteria

1. THE Dispatcher SHALL TaskAssigned、RunnerStarted、RunnerCompleted、RunnerFailedのイベントを記録する
2. THE Dispatcher SHALL イベントをTask Registryに送信する
3. THE Dispatcher SHALL イベントに詳細情報（Runner ID、スロットID、実行時間）を含める
4. THE Dispatcher SHALL イベントのタイムスタンプを記録する
5. THE Dispatcher SHALL イベント記録の失敗を検出し、ローカルログに記録する

### Requirement 11: スケジューリングポリシー

**User Story:** システム管理者として、タスクのスケジューリングポリシーを選択したい

#### Acceptance Criteria

1. THE Dispatcher SHALL FIFO（先入先出）ポリシーをサポートする
2. THE Dispatcher SHALL Priority（優先度ベース）ポリシーをサポートする
3. THE Dispatcher SHALL Skill-based（スキルベース）ポリシーをサポートする
4. THE Dispatcher SHALL Fair-share（公平分配）ポリシーをサポートする
5. THE Dispatcher SHALL スケジューリングポリシーを設定ファイルで指定可能にする

### Requirement 12: リソースクォータの管理

**User Story:** システム管理者として、Agent Poolごとのリソース使用量を制限したい

#### Acceptance Criteria

1. THE Dispatcher SHALL Agent PoolごとのCPUクォータを設定可能にする
2. THE Dispatcher SHALL Agent Poolごとのメモリクォータを設定可能にする
3. WHEN リソースクォータに達する時、THE Dispatcher SHALL 新しいタスクの割当を待機する
4. THE Dispatcher SHALL 現在のリソース使用量を追跡する
5. THE Dispatcher SHALL リソースクォータ超過の警告を記録する

### Requirement 13: デッドロックの検出と解決

**User Story:** Dispatcherとして、タスクの依存関係によるデッドロックを検出し、解決したい

#### Acceptance Criteria

1. THE Dispatcher SHALL タスクの依存関係グラフを分析する
2. THE Dispatcher SHALL 循環依存を検出する
3. WHEN デッドロックが検出される時、THE Dispatcher SHALL 警告を記録する
4. THE Dispatcher SHALL デッドロック解決のための手動介入を要求する
5. THE Dispatcher SHALL デッドロック検出を定期的に実行する

### Requirement 14: メトリクスとモニタリング

**User Story:** システム監視者として、Dispatcherの動作状況をメトリクスで監視したい

#### Acceptance Criteria

1. THE Dispatcher SHALL キュー内のタスク数を記録する
2. THE Dispatcher SHALL 実行中のタスク数を記録する
3. THE Dispatcher SHALL タスクの平均待機時間を記録する
4. THE Dispatcher SHALL Agent Poolごとの使用率を記録する
5. THE Dispatcher SHALL メトリクスをPrometheus形式で出力する

### Requirement 15: グレースフルシャットダウン

**User Story:** システム管理者として、Dispatcherを安全にシャットダウンしたい

#### Acceptance Criteria

1. WHEN シャットダウンシグナルを受信する時、THE Dispatcher SHALL 新しいタスクの受付を停止する
2. THE Dispatcher SHALL 実行中のAgent Runnerの完了を待機する
3. THE Dispatcher SHALL 待機タイムアウト（デフォルト: 5分）を設定可能にする
4. WHEN タイムアウトに達する時、THE Dispatcher SHALL 実行中のタスクを中断する
5. THE Dispatcher SHALL シャットダウン時の状態をTask Registryに記録する

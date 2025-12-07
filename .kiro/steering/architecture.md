# NecroCode アーキテクチャ

## クイックリファレンス
- **目的**: NecroCodeの構成とシステム内のデータフローを説明
- **対象読者**: アーキテクト、シニアエンジニア、フレームワークを拡張するスピリット
- **次に読むべき文書**: プロダクト概要 → `overview.md`、実装ガイド → `development.md`

## システムコンテキスト
NecroCodeはジョブ記述を取り込み、`.kiro/specs/`内の仕様に分解し、協働するスピリットを通じてそれらの仕様を実行します。オーケストレーションスタックは以下に分割されています：
- `framework/orchestrator/` (Necromancer、イシュールーティング、ワークロード監視)
- `framework/workspace_manager/` (ワークスペースライフサイクル + Git自動化)
- `necrocode/task_registry/` (ステートフルなタスク/イベント永続化)
- `framework/agents/` + `strandsagents/` (LLMバックエンドの実行ヘルパー)
- オプションサービス (Artifact Store、Repo Pool Manager、Dispatcher、Review PR Service) は`.kiro/specs/*`で定義

## 技術スタック
| 関心事 | 実装 |
| --- | --- |
| 言語 / ランタイム | Python 3.11+、`dataclasses`、`typing`、`asyncio`対応コンポーネント |
| データ & 永続化 | レジストリ/イベントログ用のJSONファイル (`necrocode/task_registry`)、ファイルベースのロック |
| バージョン管理 | `framework/workspace_manager/git_operations.py`経由のネイティブgit CLI、PR用のGitHub |
| AI / LLM | `strandsagents.llm.OpenAIChatClient`経由のOpenAI GPT-5 Codex |
| メッセージング | メッセージバスユーティリティを通じて交換されるスピリットプロトコルペイロード (dispatcherスペックで計画中) |

## アーキテクチャパターン
- **マルチスピリットオーケストレーション**: Necromancerが役割ごとに複数のインスタンスを召喚し、負荷を分散 (`.kiro/specs/necrocode-agent-orchestration`参照)
- **ワークスペース分離**: 全ての仕様は`WorkspaceManager`によって追跡される専用のクローンワークスペース内で実行
- **イベントソーシング**: タスク/イベントストアがクエリエンジンに供給される不変ログを追加 (`necrocode/task_registry/event_store.py`)
- **プラガブルサービス**: Artifact Store、Repo Pool Manager、Agent Runner、Review PR Serviceは、スピリットプロトコル + タスクレジストリ経由で統合されるスタンドアロンサービス

## スピリットプロトコル仕様
- **コミット形式**: `spirit(<scope>): <spell description> [Task <spec-task-id>]`。例：`spirit(frontend): craft login form [Task 2.1]`
- **ブランチ命名**: `feature/task-{spec-id}-{task-number}-{slug}` または複数インスタンスが同時動作する場合は`{role}/spirit-{instance}/{feature}`。スラグは`framework/workspace_manager/branch_strategy.py`でサニタイズされます
- **メッセージエンベロープ**:
  ```json
  {
    "type": "issue_assignment",
    "agent_instance": "frontend_spirit_2",
    "issue_id": "login-ui",
    "payload": {
      "task": "2.1",
      "dependencies": ["1.1"],
      "context": "requirements + design extracts"
    }
  }
  ```
- **メタデータ**: 各メッセージまたはコミットは`spec_id`、`task_id`、`agent_instance`、およびオプションで`issue_id`を参照し、タスクレジストリ内でのトレーサビリティを可能にします

## コアコンポーネント
### Necromancer (`framework/orchestrator/necromancer.py`)
ジョブ記述を解析し、スピリットチームを編成し、スプリント実行を調整します。IssueRouter、WorkspaceManager、TaskRegistryと協働してタスクの流れを維持します。

### Issue Router (`framework/orchestrator/issue_router.py`)
キーワードルールとワークロード認識を使用して、バックログアイテムを最適なスピリットタイプ/インスタンスにルーティングします。バイリンガルキーワード辞書と最小負荷スケジューリングをサポートします。

### Workspace Manager (`framework/workspace_manager/*.py`)
ワークスペースライフサイクルを所有：リポジトリのクローン、ブランチ/コミットの生成、変更のプッシュ、ワークスペース状態の永続化 (`state_tracker.py`)。`branch_strategy.py`経由でスピリットプロトコル命名を強制します。

### Repo Pool Manager (`.kiro/specs/repo-pool-manager`のスペック)
エージェント用にウォームなgitワークスペースのプールを維持するサービス。スロット割り当て、スロットクリーニング、LRU割り当て、古いロックのクリーンアップを処理します。

### Agent Runner (`.kiro/specs/agent-runner`)
ワークスペース操作、TestRunner、ArtifactUploader、PlaybookEngineを調整して個別の仕様タスクを実行します。RunnerOrchestratorはタスクレジストリ + Artifact Storeと統合されます。

### Artifact Store (`.kiro/specs/artifact-store`)
スピリットによって生成された差分、ログ、テスト出力、バイナリアーティファクトを永続化します。Review PR Serviceおよび下流ツール用の取得APIを提供します。

### Task Registry (`necrocode/task_registry/*`)
仕様、タスク、タスク状態、イベント、アーティファクトの信頼できる情報源。コンポーネントには`task_store.py`、`event_store.py`、`lock_manager.py`、およびクエリ/グラフ可視化ヘルパーが含まれます。

### Dispatcher & Review PR Service
Dispatcherはスキル/可用性に基づいて準備完了タスクをランナーに割り当てます。Review PR Serviceはコミット/アーティファクトを消費し、レビューヒューリスティックを実行し、結果をレジストリに報告します。

## データモデル
- **Taskset / Task / TaskEvent** – `necrocode/task_registry/models.py`で定義、仕様メタデータ、依存関係グラフ、ライフサイクルイベントをキャプチャ
- **Artifact** – `type`、`uri`、サイズ、タイムスタンプと共にタスクと並行して保存 (`task_registry/task_registry.py::add_artifact`)
- **WorkspaceInfo** – ワークスペースパス、リポジトリURL、ブランチ、ステータスフラグと共に`framework/workspace_manager/state_tracker.py`経由で永続化
- **AgentInstance & Issue** – `.kiro/specs/necrocode-agent-orchestration`実装で定義、ルーティングメタデータ（役割、ワークロード、割り当てられたブランチ）を保持
- **Slot / Pool / AllocationMetrics** – Repo Pool Manager用の計画されたデータモデル、スロットが状態とヘルス情報と共に永続化されることを保証

## 品質属性
- **パフォーマンス**: ワークスペース作成はgit clone/pullが支配的、状態とレジストリ操作はO(1)のファイル書き込み、イシュールーティングはエージェントインスタンスに対してO(n)
- **セキュリティ**: シークレットは環境から取得（例：`OPENAI_API_KEY`）、ログにシークレットは永続化されない。ワークスペース分離により相互汚染を回避。アーティファクトURIはアクセス制御付きのストレージバックエンドを参照
- **スケーラビリティ**: 複数のエージェントインスタンス + Repo Pool Managerスロット経由の水平スケール。タスクレジストリはファイルロックを通じて並行更新を処理。Dispatcher/Agent Runnerスペックはステートレスワーカーを記述
- **可観測性**: ルーティング/ランナー決定用の構造化ログ、`event_store.py`のイベントログ、将来のPrometheusレポート用にagent-runnerスペックで概説されたメトリクスフック

## 相互参照
- 用語 + プロダクト概要: `overview.md`
- ディレクトリレイアウト、コーディング標準、ワークフロー: `development.md`
- サービスレベル要件: `.kiro/specs/*/requirements.md`

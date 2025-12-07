# NecroCode 開発ガイド

## クイックリファレンス
- **目的**: NecroCodeの構築、拡張、運用方法を説明
- **対象読者**: タスクを実装するスピリットとフレームワークを保守する人間
- **関連ドキュメント**: プロダクト概要 → `overview.md`、システム設計 → `architecture.md`

## ディレクトリレイアウト
```
.
├── .kiro/
│   ├── specs/                # フレームワーク仕様 + タスク計画
│   └── steering/             # 概要、アーキテクチャ、このガイド
├── framework/
│   ├── agents/               # スピリット抽象化とヘルパー
│   ├── communication/        # スピリットプロトコル + バスユーティリティ
│   ├── orchestrator/         # Necromancer、イシュールーティング、ワークロードモニター
│   └── workspace_manager/    # Git + ワークスペースライフサイクル
├── necrocode/task_registry/  # タスク/イベント/アーティファクト永続化
├── strandsagents/            # LLMランナー (StrandsAgent、SpecTaskRunner)
├── examples/                 # 使用例デモとノートブック
├── tests/                    # Pytestスイート
└── demo_* / scripts/         # シナリオウォークスルー
```

### `.kiro/`
- `steering/`は正規のステアリングドキュメントをホスト、履歴入力は`.bak`バックアップとして保存
- `specs/`は全てのサブシステム（agent runner、repo pool、dispatcherなど）の要件/設計/タスクを含む。仕様は`necrocode/task_registry/kiro_sync.py`を通じてタスクレジストリと同期

### `framework/`
- `agents/`: 高レベルのスピリットロジック（タスクプランナー、チームビルダー）
- `communication/`: スピリットプロトコルのシリアライゼーションとバスヘルパー（将来のdispatcherフック）
- `orchestrator/`: Necromancer調整 (`necromancer.py`)、イシュールーティング、ワークロード監視、チーム構成
- `workspace_manager/`: `BranchStrategy`、`GitOperations`、`Workspace`、`WorkspaceManager`、`.gitignore`マネージャー、`StateTracker`

### `necrocode/task_registry/`
`TaskRegistry`、永続化ストア、ロック、クエリ/グラフエンジン、kiro-syncユーティリティを実装。全てのデータは簡単に検査できるようJSONまたはJSONL形式。

### `strandsagents/`
オーケストレーションフローと今後のTaskExecutionOrchestrator機能で使用される`StrandsAgent`、`SpecTaskRunner`、OpenAIクライアントラッパーを含む。

### `examples/` & `demos/`
`examples/basic_usage.py`、`demo_multi_agent.py`、`demo_task_registry_graph.py`などの自己完結型スクリプトが標準フローを示します。これらを生きたランブックとして扱ってください。

## モジュール構成とインポート
- 常に絶対インポートを優先（例：`from framework.workspace_manager.workspace import Workspace`）
- ドメインデータクラスはモジュールの隣に配置（`WorkspaceInfo`は`workspace_manager/models.py`、`Taskset`は`task_registry/models.py`）
- Orchestratorモジュールは薄く保つ：Gitやレジストリロジックを直接埋め込むのではなく、専用ヘルパーを呼び出す

## 命名規則
- **ブランチ**: `feature/task-{spec-id}-{task-number}-{slug}`は`BranchStrategy.generate_branch_name`経由で生成。マルチインスタンススピリットは`{role}/spirit-{instance}/{slug}`を使用可能
- **コミット**: `spirit(scope): <spell description> [Task X.Y]`は`Workspace.commit_task`経由
- **仕様/タスク**: 10進数番号付け（1、1.1、1.1.1）と要件IDに一致する`_Requirements:`パンくずリスト
- **コード**: モジュール/フォルダはsnake_case、クラスはPascalCase、関数はsnake_case、定数はUPPER_SNAKE_CASE、各`__all__`でエクスポートを定義

## スピリットワークフロー
1. **召喚** – `framework/orchestrator/team_builder.py`が役割リクエストを読み取り、スピリットをインスタンス化（役割ごとに複数インスタンスの可能性）し、メッセージバスに登録
2. **計画** – Architect/ScrumMasterスピリットが`.kiro/specs/*/tasks.md`を解析、`necrocode/task_registry/kiro_sync.py`が依存関係グラフと共にタスクレジストリにミラーリング
3. **実行** – Agent Runner（スペック）または他のスピリットが`WorkspaceManager`からワークスペースを要求し、コード変更を適用し、ブランチ/コミットのスピリットプロトコル形式に従う
4. **報告** – イベントが`event_store.py`に流れ込み、アーティファクトは`TaskRegistry.add_artifact`経由で添付。Dispatcher/Review PR Serviceスペックが結果が人間に返される方法を記述
5. **完了** – 依存タスクが自動的にブロック解除（`TaskRegistry.update_task_state`）、ワークスペースは`WorkspaceManager.cleanup_workspace`でクリーンアップ、Repo Poolスロットがプールに返却

## コンテキスト構築とプロンプティング
- `SpecTaskRunner` (`strandsagents/spec_runner.py`)がタスクを解析し、`StrandsTask`を生成
- `StrandsAgent.run_task`を呼び出す際、オプションの`context`辞書に要件/設計スニペットを供給。プロンプトには既に識別子、説明、チェックリストが含まれています
- デフォルトのLLMモデルは`gpt-5-codex`。実験時はランナー、エージェント、または`OPENAI_MODEL`環境変数で上書き可能

## 並列実行と負荷分散
- マルチインスタンスルーティングは`.kiro/specs/necrocode-agent-orchestration`に従って実装：IssueRouterがバイリンガルキーワードルールをチェックし、各スピリットに`get_workload()`を問い合わせて最も負荷の少ないインスタンスを選択
- Workspace Managerは`lock_manager.py`のファイルロックにより並行性安全。共有可変状態を避けるため、タスクごとに別々の`Workspace`オブジェクトを開く
- Repo Pool Manager（スペック）は事前ウォームアップされたgitスロットを提供。Dispatcher背後の複数ランナーで実行できるよう、新しいコードはステートレスに保つ

## エラーハンドリングと監視
- Git操作は説明的な例外を発生。バブルアップ前にタスクコンテキストを追加するため、タスク実行全体をtry/exceptでラップ
- `strandsagents/llm.OpenAIChatClient`は`OPENAI_API_KEY`を検証し、TaskExecutionOrchestratorが実装される際（スペックタスク17-19）にリトライ/バックオフロジックでラップすべき
- タスクID、ワークスペースパス、エージェントインスタンスを含む構造化ログを出力（`demo_logging_monitoring.py`参照）。agent-runnerスペックで計画されたメトリクスフックは実行時間、リトライ、アーティファクト数をキャプチャすべき

## テスト戦略
- ユニットテストは`tests/`に配置（例：`tests/test_task_registry.py`、`tests/test_lock_manager.py`、`tests/test_ai_components.py`）。ファイルシステム作業にはpytestフィクスチャ/一時ディレクトリを使用
- リポジトリルートの統合テスト（`test_graph_visualization.py`、`test_logging_monitoring.py`など）は複数モジュールが正しく協働することを保証
- 新しいサービスを追加する際は、ターゲットフィクスチャ（モックgitリポジトリ、スタブLLMクライアント）を作成し、パターンが再利用可能になった場合は`tests/README.md`に文書化

## 拡張ポイント
- **TaskExecutionOrchestrator** (`framework/task_executor/`スペック)はStrandsAgent出力、ファイル書き込み、コミット、プッシュを調整
- **Dispatcher**はタスクレジストリから準備完了タスクを取得し、Agent Runnerインスタンスに渡す
- **Artifact Store**はReview PR Serviceと下流分析用にログ/差分/バイナリを永続化
- **Review PR Service**は差分レビューを自動化し、結果をタスクレジストリイベントに返す

## ベストプラクティス
- `examples/`配下のファイルは決して変更しない。ゴールデンデモとして扱う
- 全てのブランチ/コミットに`WorkspaceManager`を使用。手動gitコマンドはスピリットプロトコル規約をバイパス可能
- Markdownスペックとkiro-syncの整合性を保つため、ワークスペースアクションと並行してタスクレジストリ状態を常に更新
- 古いロックを避けるため、失敗時でも一時ワークスペース/スロットをクリーンアップ

## 相互参照
- 高レベルの価値提案とワークフロー: `overview.md`
- コンポーネントの責任とスピリットプロトコル: `architecture.md`
- 詳細要件: `.kiro/specs/<service>/requirements.md`

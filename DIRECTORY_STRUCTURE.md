# NecroCode ディレクトリ構成

## プロジェクト構造

```
kiroween-skeleton-crew/
├── necrocode/                    # コアフレームワーク
│   ├── cli.py                   # CLIインターフェース
│   ├── worktree_manager.py      # Git Worktree管理
│   ├── parallel_orchestrator.py # 並列実行調整
│   ├── task_context.py          # タスクコンテキスト生成
│   ├── kiro_invoker.py          # Kiro実行
│   ├── task_registry/           # タスク管理
│   ├── repo_pool/               # リポジトリプール
│   ├── review_pr_service/       # PR管理
│   ├── dispatcher/              # タスクディスパッチャー
│   ├── agent_runner/            # エージェント実行
│   ├── artifact_store/          # アーティファクト保存
│   └── orchestration/           # オーケストレーション
│
├── framework/                    # 既存フレームワーク（保持）
│   ├── workspace_manager/       # ワークスペース管理
│   └── task_executor/           # タスク実行
│
├── examples/                     # 実行例
│   ├── parallel_execution_demo.py        # メインデモ
│   ├── worktree_pool_example.py         # Worktreeプール例
│   ├── parallel_agents_worktree.py      # 並列エージェント例
│   └── real_world_parallel_scenario.py  # 実用例
│
├── tests/                        # テスト
│   ├── test_worktree_manager.py         # Worktree管理テスト
│   ├── test_integration.py              # 統合テスト
│   ├── test_worktree_pool_manager.py    # プールマネージャーテスト
│   └── test_e2e_integration.py          # E2Eテスト
│
├── config/                       # 設定ファイル
│   ├── config.yaml              # 基本設定
│   ├── config.docker.yaml       # Docker設定
│   └── config.k8s.yaml          # Kubernetes設定
│
├── .kiro/                        # Kiro設定
│   ├── steering/                # アーキテクチャドキュメント
│   │   ├── kiro-native-architecture.md
│   │   ├── architecture.md
│   │   └── overview.md
│   ├── tasks/                   # タスク定義
│   │   ├── demo-chat-app/
│   │   ├── sample-project/
│   │   └── directory-cleanup/
│   ├── specs/                   # 機能仕様
│   └── hooks/                   # Kiro Hooks
│
├── templates/                    # テンプレート
│   ├── pr-template.md
│   └── comment-template.md
│
├── strandsagents/               # LLM統合
│   ├── agent.py
│   ├── llm.py
│   └── spec_runner.py
│
├── worktrees/                   # 実行時Worktree（自動生成）
│   ├── task-1/
│   ├── task-2/
│   └── ...
│
├── README.md                    # メインドキュメント
├── QUICKSTART.md               # クイックスタート
├── IMPLEMENTATION_SUMMARY.md   # 実装サマリー
└── DIRECTORY_STRUCTURE.md      # このファイル
```

## ディレクトリの役割

### コアコンポーネント (`necrocode/`)

Kiroネイティブ並列実行フレームワークのコア実装。

- **cli.py**: コマンドラインインターフェース
- **worktree_manager.py**: Git Worktreeの作成・削除・管理
- **parallel_orchestrator.py**: 依存関係解決と並列実行調整
- **task_context.py**: Kiro用のタスクコンテキスト生成
- **kiro_invoker.py**: Kiroの実行（auto/manual/apiモード）

### サブモジュール

- **task_registry/**: タスクの状態管理と永続化
- **repo_pool/**: Git Worktreeベースのリポジトリプール
- **review_pr_service/**: GitHub PR管理とレビュー
- **dispatcher/**: タスクのディスパッチと優先度管理
- **agent_runner/**: エージェント実行環境
- **artifact_store/**: ビルド成果物の保存
- **orchestration/**: サービス間のオーケストレーション

### 既存フレームワーク (`framework/`)

新アーキテクチャと共存する既存コンポーネント。

- **workspace_manager/**: ワークスペースの管理
- **task_executor/**: タスク実行ロジック

### 実行例 (`examples/`)

新アーキテクチャの使用例。

- **parallel_execution_demo.py**: 5タスクのチャットアプリデモ
- **worktree_pool_example.py**: Worktreeプールの使用例
- **parallel_agents_worktree.py**: 並列エージェントの例
- **real_world_parallel_scenario.py**: 実用的なシナリオ

### テスト (`tests/`)

新アーキテクチャのテストスイート。

- **test_worktree_manager.py**: Worktree管理のユニットテスト
- **test_integration.py**: 統合テスト
- **test_worktree_pool_manager.py**: プールマネージャーテスト
- **test_e2e_integration.py**: エンドツーエンドテスト

### 設定 (`config/`)

環境別の設定ファイル。

- **config.yaml**: 基本設定
- **config.docker.yaml**: Docker環境用
- **config.k8s.yaml**: Kubernetes環境用

### Kiro設定 (`.kiro/`)

Kiro関連の設定とドキュメント。

- **steering/**: アーキテクチャドキュメント
- **tasks/**: プロジェクトごとのタスク定義
- **specs/**: 機能仕様
- **hooks/**: Kiro Hooks

### 実行時ディレクトリ (`worktrees/`)

並列実行時に自動生成されるGit Worktree。各タスクが独立した環境で実行される。

## 使用方法

### 基本的なワークフロー

```bash
# 1. サンプルプロジェクトを作成
python3 examples/parallel_execution_demo.py

# 2. タスク一覧を確認
python3 -m necrocode.cli list-tasks demo-chat-app

# 3. 並列実行
python3 -m necrocode.cli execute demo-chat-app --workers 3 --mode manual

# 4. クリーンアップ
python3 -m necrocode.cli cleanup
```

### カスタムタスクの作成

1. `.kiro/tasks/{project-name}/tasks.json`を作成
2. タスク定義を記述
3. `necrocode.cli execute`で実行

詳細は[QUICKSTART.md](QUICKSTART.md)を参照してください。

## 削除されたディレクトリ

以下のディレクトリは旧アーキテクチャのため削除されました：

- ❌ `framework/agents/` - スピリットベースのエージェント
- ❌ `framework/communication/` - スピリット間通信
- ❌ `framework/orchestrator/` - 旧オーケストレーター
- ❌ `scripts/` - 古いドキュメント生成スクリプト
- ❌ `examples/workspace1, workspace2/` - 古いワークスペース例
- ❌ `examples/output/` - 古い出力ファイル

## 関連ドキュメント

- [README.md](README.md) - プロジェクト概要
- [QUICKSTART.md](QUICKSTART.md) - クイックスタート
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 実装詳細
- [.kiro/steering/kiro-native-architecture.md](.kiro/steering/kiro-native-architecture.md) - アーキテクチャ詳細

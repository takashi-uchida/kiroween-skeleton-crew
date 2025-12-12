# NecroCode: Kiroネイティブ並列実行フレームワーク

NecroCodeは、Git Worktreeを活用して複数のKiroインスタンスを並列実行し、ソフトウェア開発タスクを自動化するフレームワークです。

## コアコンセプト

**Kiroがエージェントです。** 複数のKiroインスタンスをGit Worktreeで物理的に分離して並列実行します。

```
1つのリポジトリ
  ↓
複数のworktree（独立したディレクトリ）
  ↓
各worktreeで独立したKiroインスタンスが並列実行
  ↓
タスクレジストリで調整・同期
```

## 主要機能

### 🔄 Git Worktreeベースの並列実行
- 各タスクが独立したworktreeで実行
- ファイルシステムレベルで競合なし
- 効率的なディスク使用（.gitディレクトリは共有）

### 📋 タスク管理
- 依存関係を自動解決
- 並列実行可能なタスクを自動検出
- タスクレジストリで進捗管理

### 🤖 Kiro統合
- 各worktreeでKiroを実行
- タスクコンテキストを自動生成
- コミット・PR作成を自動化

## クイックスタート

### インストール

```bash
cd kiroween-skeleton-crew
pip install -e .
```

### 基本的な使い方

```bash
# 1. タスクを計画
python -m necrocode.cli plan "認証機能付きチャットアプリを作成" --project chat-app

# 2. 並列実行（3つのKiroインスタンス）
python -m necrocode.cli execute chat-app --workers 3

# 3. 状況確認
python -m necrocode.cli status --project chat-app

# 4. クリーンアップ
python -m necrocode.cli cleanup
```

### 実際の使用例

```bash
# Webアプリケーションの作成
python -m necrocode.cli plan "React + FastAPI でTodoアプリを作成。認証、CRUD、リアルタイム更新機能を含む" --project todo-app

# APIサービスの作成  
python -m necrocode.cli plan "GraphQL APIサーバーを作成。ユーザー管理、投稿機能、検索機能を含む" --project graphql-api

# モバイルアプリのバックエンド
python -m necrocode.cli plan "Flutter用のバックエンドAPI。プッシュ通知、画像アップロード、チャット機能" --project mobile-backend
```

## プロジェクト構造

```
kiroween-skeleton-crew/
├── necrocode/                     # コアモジュール
│   ├── cli.py                    # CLIインターフェース
│   ├── parallel_orchestrator.py  # 並列実行調整
│   ├── worktree_manager.py       # Git Worktree管理
│   ├── task_planner.py           # タスク計画
│   ├── task_context.py           # タスクコンテキスト生成
│   ├── kiro_invoker.py           # Kiro呼び出し
│   ├── task_registry/            # タスクレジストリ
│   └── repo_pool/                # リポジトリプール
├── scripts/                       # 開発・検証スクリプト
│   ├── necrocode_cli.py          # CLIラッパー
│   └── verification/             # 検証スクリプト
├── tests/                         # テストファイル
├── examples/                      # 使用例
├── templates/                     # PRテンプレート
├── docs/archive/                  # 過去のドキュメント
└── .kiro/                        # Kiro設定・タスク定義
    ├── steering/                 # アーキテクチャドキュメント
    ├── tasks/                    # タスク定義
    └── registry/                 # タスクレジストリ
```

## アーキテクチャ

### ディレクトリ構造

```
project/
├── .git/                          # 共有Gitリポジトリ
├── necrocode/                     # オーケストレーター
│   ├── worktree_manager.py       # Worktree管理
│   ├── parallel_orchestrator.py  # 並列実行調整
│   ├── task_context.py           # タスクコンテキスト生成
│   └── cli.py                    # CLIインターフェース
├── .kiro/
│   ├── tasks/                    # タスク定義
│   │   └── {project}/
│   │       └── tasks.json
│   └── registry/                 # タスクレジストリ
└── worktrees/                    # 実行時worktree
    ├── task-1/                   # Task 1専用
    ├── task-2/                   # Task 2専用
    └── task-3/                   # Task 3専用
```

### コンポーネント

1. **Worktree Manager**: Git worktreeの作成・削除・管理
2. **Parallel Orchestrator**: 依存関係解決と並列実行調整
3. **Task Context Generator**: Kiro用のタスクコンテキスト生成
4. **Task Registry**: タスク状態の永続化と同期

## タスク定義形式

```json
{
  "project": "chat-app",
  "tasks": [
    {
      "id": "1",
      "title": "データベーススキーマ設定",
      "description": "ユーザーとメッセージのモデルを作成",
      "dependencies": [],
      "type": "backend",
      "files_to_create": ["models/user.py", "models/message.py"],
      "acceptance_criteria": [
        "Userモデルに必要なフィールドがある",
        "Messageモデルに必要なフィールドがある"
      ]
    }
  ]
}
```

## 実行モード

### 並列実行（デフォルト）
```bash
python -m necrocode.cli execute chat-app --workers 3
```

### 順次実行
```bash
python -m necrocode.cli execute chat-app --workers 1
```

## Git Worktreeの利点

1. **物理的分離**: 各worktreeは独立したディレクトリ
2. **Git統合**: worktreeはGitネイティブ機能
3. **並列安全**: ファイルシステムレベルで競合なし
4. **効率的**: .gitディレクトリは共有
5. **クリーンアップ簡単**: `git worktree remove`で完全削除

## ドキュメント

- [アーキテクチャ詳細](.kiro/steering/kiro-native-architecture.md)
- [開発ガイド](.kiro/steering/development.md)
- [タスクレジストリ](necrocode/task_registry/README.md)

## ライセンス

MIT License

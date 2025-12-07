# NecroCode: Kiroネイティブ + Git Worktree アーキテクチャ

## コアコンセプト

**Kiroがエージェントです。** 複数のKiroインスタンスをGit Worktreeで並列実行します。

### 基本原理

```
1つのGitリポジトリ
  ↓
複数のworktree（物理的に独立したディレクトリ）
  ↓
各worktreeで独立したKiroインスタンスが並列実行
  ↓
タスクレジストリで調整・同期
```

## アーキテクチャ図

```
project/
├── .git/                          # 共有Gitリポジトリ
├── main/                          # メインworktree
│   ├── necrocode/                 # オーケストレーター
│   ├── .kiro/
│   │   ├── tasks/
│   │   │   └── chat-app/
│   │   │       └── tasks.json     # タスク定義
│   │   └── registry/              # 共有タスクレジストリ
│   │       ├── tasks.jsonl
│   │       └── events.jsonl
│   └── ...
│
├── worktrees/                     # Worktreeディレクトリ
│   ├── task-1/                    # Task 1専用worktree
│   │   ├── .kiro/
│   │   │   └── current-task.md   # Task 1コンテキスト
│   │   └── [ブランチ: feature/task-1-auth]
│   │
│   ├── task-2/                    # Task 2専用worktree
│   │   └── [ブランチ: feature/task-2-websocket]
│   │
│   └── task-3/                    # Task 3専用worktree
│       └── [ブランチ: feature/task-3-login-ui]
```

## 主要コンポーネント

### 1. Worktree Manager
Git worktreeの作成・削除・管理を担当

### 2. Parallel Orchestrator
依存関係を解決し、並列タスク実行を調整

### 3. Task Context Generator
Kiro用のタスクコンテキストファイルを生成

### 4. Kiro Invoker
各worktree内でKiroを実行

### 5. Task Planner
ジョブ記述を構造化されたタスクに変換

## ワークフロー

```
1. ユーザー: "チャットアプリを作成"
   ↓
2. Task Planner: タスクに分解 → tasks.json
   ↓
3. Parallel Orchestrator: 依存関係を解決
   ↓
4. 各タスク（並列実行）:
   a. Worktreeを作成
   b. タスクコンテキストを書き込み
   c. Kiroを呼び出し
   d. 変更をコミット
   e. ブランチをプッシュ
   f. PRを作成
   g. Worktreeをクリーンアップ
   ↓
5. 全タスク完了
```

## Git Worktreeの利点

1. **物理的分離**: 各worktreeは独立したディレクトリ
2. **Git統合**: worktreeはGitネイティブ機能
3. **並列安全**: ファイルシステムレベルで競合なし
4. **効率的**: .gitディレクトリは共有、ディスク使用量最小
5. **クリーンアップ簡単**: `git worktree remove`で完全削除

## 実行モード

### モード1: 並列実行（デフォルト）
```bash
necrocode execute chat-app --workers 3
```

### モード2: 順次実行
```bash
necrocode execute chat-app --workers 1
```

### モード3: 手動実行
```bash
necrocode plan "チャットアプリ"
necrocode next
# ユーザーがKiroで実装
necrocode complete
```

## タスク定義形式

```json
{
  "project": "chat-app",
  "tasks": [
    {
      "id": "1",
      "title": "データベーススキーマ設定",
      "description": "MongoDBでUserとMessageモデルを作成",
      "dependencies": [],
      "type": "backend",
      "files_to_create": ["models/User.js", "models/Message.js"],
      "acceptance_criteria": [
        "Userモデルにemail, password, usernameフィールドがある",
        "Messageモデルにsender, content, timestampがある"
      ]
    }
  ]
}
```

## 技術スタック

- **言語**: Python 3.11+
- **Git**: ネイティブgit CLI（worktree機能）
- **並列処理**: ProcessPoolExecutor
- **永続化**: JSON/JSONL（タスクレジストリ）
- **Kiro統合**: CLI/API経由

## 旧アーキテクチャとの違い

| 項目 | 旧（スピリットベース） | 新（Kiroネイティブ） |
|------|----------------------|---------------------|
| エージェント | 抽象的なスピリット | 実際のKiroインスタンス |
| 並列実行 | シミュレート | Git Worktreeで真の並列 |
| 通信 | スピリットプロトコル | タスクレジストリ経由 |
| 分離 | 論理的 | 物理的（ファイルシステム） |
| 複雑度 | 高い | シンプル |

## 次のステップ

1. Worktree Managerの実装
2. Parallel Orchestratorの実装
3. Task Context Generatorの実装
4. Kiro Invokerの実装
5. CLIインターフェースの実装

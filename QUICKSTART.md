# NecroCode クイックスタート

## インストール

```bash
cd kiroween-skeleton-crew
pip install -e .
```

## 基本的な使い方

### 1. サンプルプロジェクトを作成

```bash
python examples/parallel_execution_demo.py
```

これにより、5つのタスクを持つチャットアプリプロジェクトが作成されます。

### 2. タスク一覧を確認

```bash
python -m necrocode.cli list-tasks demo-chat-app
```

出力例:
```
プロジェクト: demo-chat-app
タスク数: 5

Task 1: プロジェクト構造作成
  タイプ: setup
  説明: 基本的なディレクトリとファイルを作成

Task 2: データモデル実装 (依存: 1)
  タイプ: backend
  説明: UserとMessageのデータモデルを作成
...
```

### 3. タスクを実行

#### 手動モード（推奨）

```bash
python -m necrocode.cli execute demo-chat-app --workers 3 --mode manual
```

各タスクで以下が実行されます:
1. 専用worktreeが作成される
2. タスクコンテキストが生成される
3. ユーザーに実装を促すメッセージが表示される
4. ユーザーがKiroで実装
5. 変更が自動的にコミットされる

#### 自動モード（実験的）

```bash
python -m necrocode.cli execute demo-chat-app --workers 3 --mode auto
```

Kiro CLIが自動的に呼び出されます。

### 4. 実行状況を確認

```bash
# Worktreeの状態を確認
git worktree list

# 作成されたブランチを確認
git branch
```

### 5. クリーンアップ

```bash
python -m necrocode.cli cleanup
```

## 実行フロー

```
1. タスク定義を読み込み
   ↓
2. 依存関係を解決
   ↓
3. 実行可能なタスクを並列実行
   ├─ Task 1 (worktree: worktrees/task-1)
   ├─ Task 2 (worktree: worktrees/task-2)
   └─ Task 3 (worktree: worktrees/task-3)
   ↓
4. 各タスクで:
   - Worktreeを作成
   - タスクコンテキストを生成
   - Kiroを実行
   - 変更をコミット
   ↓
5. 依存タスクが完了したら次のタスクを実行
   ↓
6. 全タスク完了
```

## ディレクトリ構造

実行中:
```
project/
├── .git/                    # 共有リポジトリ
├── .kiro/
│   └── tasks/
│       └── demo-chat-app/
│           └── tasks.json   # タスク定義
└── worktrees/               # 実行時に作成
    ├── task-1/              # Task 1専用
    │   ├── .kiro/
    │   │   └── current-task.md
    │   └── [実装ファイル]
    ├── task-2/              # Task 2専用
    └── task-3/              # Task 3専用
```

## カスタムタスクの作成

### タスク定義ファイル

`.kiro/tasks/{project-name}/tasks.json`:

```json
{
  "project": "my-project",
  "tasks": [
    {
      "id": "1",
      "title": "タスクのタイトル",
      "description": "詳細な説明",
      "dependencies": [],
      "type": "backend",
      "files_to_create": ["file1.py", "file2.py"],
      "acceptance_criteria": [
        "基準1",
        "基準2"
      ]
    }
  ]
}
```

### 実行

```bash
python -m necrocode.cli execute my-project --workers 2 --mode manual
```

## トラブルシューティング

### Worktreeが残っている

```bash
# 全てクリーンアップ
python -m necrocode.cli cleanup --force

# または手動で
git worktree remove worktrees/task-1 --force
```

### ブランチが残っている

```bash
# ローカルブランチを削除
git branch -D feature/task-1-*
```

### タスクが見つからない

```bash
# タスク定義ファイルを確認
ls -la .kiro/tasks/*/tasks.json
```

## 次のステップ

- [アーキテクチャ詳細](.kiro/steering/kiro-native-architecture.md)
- [開発ガイド](.kiro/steering/development.md)
- [タスクレジストリ](necrocode/task_registry/README.md)

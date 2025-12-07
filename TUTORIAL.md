# NecroCode チュートリアル

## はじめに

このチュートリアルでは、NecroCodeを使って実際のプロジェクトを並列実行する方法を学びます。

## 前提条件

- Python 3.9以上
- Git
- GitHub アカウント（オプション）

## インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/takashi-uchida/kiroween-skeleton-crew.git
cd kiroween-skeleton-crew
```

### 2. インストール

```bash
pip install -e .
```

### 3. 動作確認

```bash
necrocode --help
```

出力:
```
Usage: necrocode [OPTIONS] COMMAND [ARGS]...

  NecroCode - Kiro並列実行オーケストレーター

Commands:
  cleanup     全てのworktreeをクリーンアップ
  execute     タスクを並列実行
  list-tasks  プロジェクトのタスク一覧を表示
  plan        ジョブ記述からタスクを計画
  status      実行状況を表示
```

## チュートリアル 1: シンプルなTODOアプリ

### ステップ 1: プロジェクトを計画

```bash
necrocode plan "シンプルなTODOアプリを作成" --project todo-app --no-llm
```

出力:
```
✓ 1個のタスクを作成しました
  保存先: .kiro/tasks/todo-app/tasks.json
```

### ステップ 2: タスクを確認

```bash
necrocode list-tasks todo-app
```

出力:
```
プロジェクト: todo-app
タスク数: 1

Task 1: プロジェクト初期化
  タイプ: setup
  説明: 基本的なプロジェクト構造を作成
```

### ステップ 3: タスクを実行（手動モード）

```bash
necrocode execute todo-app --workers 1 --mode manual
```

実行中:
```
プロジェクト 'todo-app' を実行中...
並列ワーカー数: 1
Kiroモード: manual

[Task 1] Worktreeを作成中...
[Task 1] タスクコンテキストを生成中...
[Task 1] Kiroを実行中...

============================================================
Task 1: プロジェクト初期化
============================================================

Worktree: worktrees/task-1
Context: worktrees/task-1/.kiro/current-task.md

次のコマンドを実行してください:
  cd worktrees/task-1
  kiro-cli chat

実装が完了したら、このスクリプトを続行してください。

Enterキーを押して続行...
```

### ステップ 4: Kiroで実装

別のターミナルで:
```bash
cd worktrees/task-1
kiro-cli chat
```

Kiroに指示:
```
.kiro/current-task.mdのタスクを実装してください
```

### ステップ 5: 完了を確認

元のターミナルでEnterキーを押す

### ステップ 6: クリーンアップ

```bash
necrocode cleanup
```

## チュートリアル 2: チャットアプリ（複数タスク）

### ステップ 1: サンプルプロジェクトを作成

```bash
python3 examples/parallel_execution_demo.py
```

出力:
```
✓ サンプルプロジェクト 'demo-chat-app' を作成しました
  タスク数: 5
```

### ステップ 2: タスク一覧を確認

```bash
necrocode list-tasks demo-chat-app
```

出力:
```
プロジェクト: demo-chat-app
説明: シンプルなチャットアプリケーション
タスク数: 5

Task 1: プロジェクト構造作成
  タイプ: setup
  説明: 基本的なディレクトリとファイルを作成

Task 2: データモデル実装 (依存: 1)
  タイプ: backend
  説明: UserとMessageのデータモデルを作成

Task 3: 認証API実装 (依存: 2)
  タイプ: backend
  説明: ユーザー登録とログイン機能を実装

Task 4: メッセージAPI実装 (依存: 2)
  タイプ: backend
  説明: メッセージの送受信機能を実装

Task 5: フロントエンド実装 (依存: 3, 4)
  タイプ: frontend
  説明: チャットUIを作成
```

### ステップ 3: 依存関係を理解

```
Task 1 (setup)
  ↓
Task 2 (backend)
  ↓
Task 3 (backend) ← 並列実行可能 → Task 4 (backend)
  ↓
Task 5 (frontend)
```

### ステップ 4: 並列実行

```bash
necrocode execute demo-chat-app --workers 3 --mode manual
```

実行フロー:
1. Task 1が実行される
2. Task 1完了後、Task 2が実行される
3. Task 2完了後、Task 3とTask 4が並列実行される
4. Task 3とTask 4完了後、Task 5が実行される

### ステップ 5: 進捗を確認

実行中に表示される進捗:
```
==================================================
進捗: ████████░░░░░░░░░░░░ 40% (2/5)
完了: 2 | 失敗: 0 | 実行中: 2
経過時間: 15.3秒

実行中:
  ⚙ Task 3: 認証API実装
  ⚙ Task 4: メッセージAPI実装
==================================================
```

## チュートリアル 3: カスタムタスクの作成

### ステップ 1: タスク定義ファイルを作成

```bash
mkdir -p .kiro/tasks/my-project
```

`my-project/tasks.json`:
```json
{
  "project": "my-project",
  "description": "カスタムプロジェクト",
  "tasks": [
    {
      "id": "1",
      "title": "環境設定",
      "description": "開発環境をセットアップ",
      "dependencies": [],
      "type": "setup",
      "files_to_create": [
        "requirements.txt",
        ".env.example"
      ],
      "acceptance_criteria": [
        "requirements.txtに必要なパッケージがリストされている",
        ".env.exampleに環境変数の例がある"
      ]
    },
    {
      "id": "2",
      "title": "データベース設計",
      "description": "データベーススキーマを作成",
      "dependencies": ["1"],
      "type": "backend",
      "files_to_create": [
        "models/user.py",
        "migrations/001_initial.sql"
      ],
      "acceptance_criteria": [
        "Userモデルが定義されている",
        "マイグレーションファイルが作成されている"
      ]
    }
  ]
}
```

### ステップ 2: 実行

```bash
necrocode execute my-project --workers 2 --mode manual
```

## よくある使い方

### プロジェクト一覧を確認

```bash
necrocode status
```

### 特定プロジェクトの詳細

```bash
necrocode status --project demo-chat-app
```

### 進捗表示なしで実行

```bash
necrocode execute my-project --no-progress
```

### ワーカー数を調整

```bash
# 順次実行
necrocode execute my-project --workers 1

# 高並列度
necrocode execute my-project --workers 5
```

## トラブルシューティング

### Worktreeが残っている

```bash
necrocode cleanup --force
```

### タスクが見つからない

```bash
# タスク定義ファイルを確認
ls -la .kiro/tasks/*/tasks.json
```

### Kiroが見つからない

```bash
# Kiroがインストールされているか確認
which kiro-cli

# インストール
# （Kiroのインストール手順に従う）
```

## 次のステップ

- [QUICKSTART.md](QUICKSTART.md) - より詳細なクイックスタート
- [CLI_IMPROVEMENTS.md](CLI_IMPROVEMENTS.md) - 今後の機能追加
- [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) - プロジェクト構造

## まとめ

このチュートリアルで学んだこと:

1. ✅ NecroCodeのインストール
2. ✅ タスクの計画と確認
3. ✅ 手動モードでの実行
4. ✅ 並列実行の理解
5. ✅ カスタムタスクの作成

NecroCodeを使って、効率的な並列開発を始めましょう！🚀

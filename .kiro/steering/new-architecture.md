# NecroCode v2: Kiroネイティブアーキテクチャ

## コアインサイト
**Kiroがエージェントそのものです。** 複数のエージェントをシミュレートする必要はありません - 異なるブランチで動作するKiroインスタンスをオーケストレートする必要があります。

## アーキテクチャ概要

```
ユーザー入力: "チャットアプリを作成"
     ↓
[Task Planner] - タスクに分解
     ↓
[Task Queue] - メタデータ付きでタスクを保存
     ↓
[Kiro Orchestrator] - タスクを順次実行
     ↓
各タスク（依存関係順）：
  1. 新しいブランチをチェックアウト
  2. タスクコンテキストを.kiro/current-task.mdに書き込み
  3. Kiro Hookをトリガー（または手動実行）
  4. Kiroがソリューションを実装
  5. 変更をコミット
  6. PRを作成
  7. 次のタスクに移動
```

**注意**: 現在のKiroアーキテクチャでは並列実行は実現不可能です。
タスクは依存関係を尊重して順次実行されます。

## 主要コンポーネント

### 1. Task Planner (Python)
**目的**: ジョブ記述を構造化されたタスクに変換

```python
class TaskPlanner:
    def plan(self, job_description: str) -> List[Task]:
        """
        Kiroを使用してジョブ記述を分析し、タスク分解を作成
        以下を含む構造化されたタスクリストを返す：
        - task_id
        - title
        - description
        - dependencies
        - estimated_complexity
        - required_skills (frontend/backend/db/etc)
        """
```

**出力形式** (`.kiro/tasks/{project}/tasks.json`):
```json
{
  "project": "chat-app",
  "tasks": [
    {
      "id": "1",
      "title": "Setup database schema",
      "description": "Create User and Message models with MongoDB",
      "dependencies": [],
      "type": "backend",
      "files_to_create": ["models/User.js", "models/Message.js"],
      "acceptance_criteria": [
        "User model has email, password, username fields",
        "Message model has sender, content, timestamp"
      ]
    },
    {
      "id": "2",
      "title": "Implement JWT authentication",
      "description": "Add login/register endpoints with JWT",
      "dependencies": ["1"],
      "type": "backend",
      "files_to_create": ["routes/auth.js", "middleware/auth.js"]
    }
  ]
}
```

### 2. Kiro Orchestrator (Python)
**目的**: 並列Kiroセッションを管理

```python
class KiroOrchestrator:
    def execute_tasks(self, project: str):
        """
        1. .kiro/tasks/{project}/tasks.jsonからタスクを読み込み
        2. 依存関係を解決（トポロジカルソート）
        3. 各準備完了タスクに対して：
           - ブランチを作成: feature/task-{id}-{slug}
           - タスクコンテキストを.kiro/current-task.mdに書き込み
           - CLI/API経由でKiroを呼び出し
           - 完了を監視
           - GitHub API経由でPRを作成
        """
```

### 3. Task Context File
**目的**: タスクに必要な全てのコンテキストをKiroに提供

**場所**: `.kiro/current-task.md` (一時的、セッションごと)

```markdown
# Task: Implement JWT Authentication

## Task ID
2

## Description
Add login and register endpoints with JWT token generation and validation.

## Dependencies Completed
- Task 1: Database schema (User model exists)

## Files to Create/Modify
- `routes/auth.js` - Login/register endpoints
- `middleware/auth.js` - JWT validation middleware
- `tests/auth.test.js` - Unit tests

## Acceptance Criteria
- [ ] POST /api/auth/register creates new user
- [ ] POST /api/auth/login returns JWT token
- [ ] Middleware validates JWT on protected routes
- [ ] Passwords are hashed with bcrypt
- [ ] Tests cover happy path and error cases

## Technical Context
- Stack: Node.js + Express + MongoDB
- JWT library: jsonwebtoken
- Password hashing: bcrypt
- Existing code: models/User.js (from Task 1)

## Related Files
#[[file:models/User.js]]
#[[file:package.json]]
```

### 4. Kiro Hook: タスク自動実行
**目的**: タスクコンテキストが書き込まれた時にKiroをトリガー

**場所**: `.kiro/hooks/on_task_ready.py`

```python
# トリガー: .kiro/current-task.mdが作成/更新された時
# アクション: タスク実装を実行

def on_task_ready(context):
    task_file = Path(".kiro/current-task.md")
    if task_file.exists():
        # Kiroがタスクコンテキストを読み取る
        # ソリューションを実装
        # "feat(task-{id}): {title}"形式でコミット
        # タスクを完了としてマーク
        pass
```

### 5. GitHub統合
**目的**: PRを自動作成

```python
class GitHubIntegration:
    def create_pr(self, branch: str, task: Task):
        """
        以下を含むPRを作成：
        - タイトル: "Task {id}: {title}"
        - 本文: タスク説明 + 受け入れ基準
        - ラベル: task.type (backend/frontend/etc)
        - レビュアー: (オプション)
        """
```

## ワークフロー例

### ステップ1: ユーザー入力
```bash
python necrocode.py "認証機能付きのリアルタイムチャットアプリを作成"
```

### ステップ2: タスク計画
```
[Task Planner] 要件を分析中...
8個のタスクを作成：
  1. データベーススキーマ (backend)
  2. JWT認証 (backend)
  3. WebSocketサーバー (backend)
  4. ログインUI (frontend)
  5. チャットインターフェース (frontend)
  6. メッセージ永続化 (backend)
  7. ユーザープレゼンス (backend)
  8. 統合テスト (qa)
```

### ステップ3: 順次実行
```
[Orchestrator] タスク実行を開始...

タスク1:
  ✓ ブランチ作成: feature/task-1-database-schema
  ✓ タスクコンテキストを.kiro/current-task.mdに書き込み
  ✓ Kiro Hookトリガー（または手動: "Kiro、現在のタスクを実装して"）
  ✓ ファイル作成: models/User.js, models/Message.js
  ✓ コミット: feat(task-1): setup database schema
  ✓ PR作成: #101
  ✓ mainにマージ

タスク2（タスク1に依存）:
  ✓ ブランチ作成: feature/task-2-jwt-auth
  ✓ タスクコンテキスト書き込み（タスク1の結果を含む）
  ✓ Kiroが実装...
  ✓ コミット: feat(task-2): implement JWT authentication
  ✓ PR作成: #102
  ...
```

## 旧アーキテクチャとの主な違い

### 旧（スピリットベース）
- ❌ 実際の機能にマッピングされない抽象的な「スピリット」
- ❌ 複雑なスピリット間通信
- ❌ シミュレートされた並列処理
- ❌ 明確な実行モデルがない

### 新（Kiroネイティブ）
- ✅ Kiroがエージェント（シミュレートではなく実在）
- ✅ 依存関係を持つシンプルなタスクキュー
- ✅ 順次実行（単一Kiroインスタンスに現実的）
- ✅ 明確な実行：1タスク = 1ブランチ = 1 PR
- ✅ Kiroの実際の強み（コード生成、ファイル操作）を活用
- ✅ Hooksで半自動化、または完全手動が可能

## 実装優先順位

1. **Task Planner** - ジョブ記述をtasks.jsonに変換
2. **Task Context Generator** - .kiro/current-task.mdを作成
3. **Manual Execution** - ユーザーがタスクコンテキストでKiroを実行
4. **Git Automation** - ブランチとコミットを自動作成
5. **GitHub Integration** - PRを自動作成
6. **Orchestrator** - Hooksを使用した順次タスク実行

## 実行モード

### モード1: 完全手動
```bash
python necrocode.py plan "チャットアプリを作成"  # tasks.jsonを作成
python necrocode.py next                         # current-task.mdを書き込み
# ユーザー: "Kiro、現在のタスクを実装して"
python necrocode.py complete                     # コミット & PRを作成
python necrocode.py next                         # 次のタスク
```

### モード2: 半自動（Hooks）
```bash
python necrocode.py plan "チャットアプリを作成"
python necrocode.py start                        # オーケストレーターを起動
# オーケストレーターがタスクコンテキストを書き込み
# Kiro Hookが自動的にトリガー
# ユーザーがレビューして承認
# 次のタスクに移動
```

### モード3: バッチモード（将来）
```bash
python necrocode.py batch "チャットアプリを作成"
# 夜間に全タスクを実行
# 複数のPRを作成
# 朝にユーザーがレビュー
```

## 参考資料

### Claude Agent Skills
- 構造化されたタスク定義を使用
- 明確な受け入れ基準
- ファイルレベルのコンテキスト

### cc-sddパターン
- 仕様駆動開発
- 依存関係を持つタスク分解
- 自動化された実行

### 活用すべきKiro機能
- タスク定義用のSpecs
- 自動化用のHooks
- ファイルコンテキスト（#[[file:...]]）
- Git操作
- 診断ツール

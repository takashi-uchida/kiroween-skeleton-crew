# NecroCode 実行手順（簡易版）

## 🚀 クイックスタート（5分）

### 1. 環境変数設定
```bash
export GITHUB_TOKEN="ghp_your_token_here"
export OPENAI_API_KEY="sk-your_key_here"
```

### 2. セットアップ
```bash
python necrocode_cli.py setup
```

### 3. ジョブ投稿
```bash
python necrocode_cli.py submit \
  --project my-api \
  --repo https://github.com/your-org/my-api.git \
  "Create a REST API with authentication"
```

### 4. サービス起動
```bash
python necrocode_cli.py start --detached
```

### 5. 監視
```bash
# ステータス確認
python necrocode_cli.py status

# ログ確認
python necrocode_cli.py logs --follow

# ジョブ確認
python necrocode_cli.py job status <job-id>
```

---

## 📋 詳細な実行手順

### ステップ1: 環境準備

```bash
# リポジトリに移動
cd /path/to/necrocode

# 依存パッケージ確認
pip list | grep -E "(dataclasses|typing|pathlib)"

# CLIを実行可能にする
chmod +x necrocode_cli.py
```

### ステップ2: 初期設定

```bash
# サービス設定を初期化
python necrocode_cli.py setup

# 作成された設定を確認
ls -la .necrocode/
cat .necrocode/dispatcher.json
```

**期待される出力:**
```
🎃 Setting up NecroCode services...
✅ All services configured successfully!

Configuration files created in: .necrocode
```

### ステップ3: 環境変数設定

```bash
# GitHub トークン（必須）
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# OpenAI APIキー（LLM使用時に必須）
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 確認
echo $GITHUB_TOKEN
echo $OPENAI_API_KEY
```

### ステップ4: ジョブ投稿

```bash
# 基本的な投稿
python necrocode_cli.py submit \
  --project task-manager \
  --repo https://github.com/myorg/task-manager.git \
  "Create a task management API with user authentication"

# ファイルから投稿
python necrocode_cli.py submit \
  --project blog-system \
  --repo https://github.com/myorg/blog.git \
  --file job_description.txt
```

**期待される出力:**
```
📝 Submitting job: Create a task management API...
✅ Job submitted: job-abc123def456

Track progress: necrocode job status job-abc123def456
```

### ステップ5: ジョブステータス確認

```bash
# ジョブIDを変数に保存
JOB_ID="job-abc123def456"

# ステータス確認
python necrocode_cli.py job status $JOB_ID
```

**期待される出力:**
```
============================================================
Job Status: job-abc123def456
============================================================

Project: task-manager
Status: running
Created: 2025-11-28T10:30:45

Tasks: 0/3
  ⏳ 1: Project setup and structure
  ⏳ 2: Core implementation
  ⏳ 3: Testing and documentation

============================================================
```

### ステップ6: サービス起動

#### オプションA: フォアグラウンド（開発時）
```bash
python necrocode_cli.py start
# Ctrl+C で停止
```

#### オプションB: バックグラウンド（本番時）
```bash
python necrocode_cli.py start --detached
```

**期待される出力:**
```
🚀 Starting NecroCode services...
✅ Services started in background

Check status: necrocode status
View logs: necrocode logs
```

### ステップ7: サービス監視

```bash
# サービスステータス
python necrocode_cli.py status

# 全ログ表示
python necrocode_cli.py logs

# 特定サービスのログ
python necrocode_cli.py logs --service dispatcher

# リアルタイムログ
python necrocode_cli.py logs --follow
```

### ステップ8: ジョブ進捗確認

```bash
# 定期的にステータス確認（5秒ごと）
watch -n 5 "python necrocode_cli.py job status $JOB_ID"

# または手動で確認
python necrocode_cli.py job status $JOB_ID
```

**実行中の出力例:**
```
Tasks: 1/3
  ✅ 1: Project setup and structure
  🔄 2: Core implementation
  ⏳ 3: Testing and documentation

Pull Requests: 1
  #42: Task 1: Project setup and structure (open)
```

### ステップ9: PR確認とマージ

```bash
# GitHubでPRを確認
open https://github.com/myorg/task-manager/pulls

# または gh CLI を使用
gh pr list
gh pr view 42
gh pr merge 42
```

### ステップ10: サービス停止

```bash
# グレースフルシャットダウン
python necrocode_cli.py stop

# タイムアウト指定
python necrocode_cli.py stop --timeout 60
```

**期待される出力:**
```
🛑 Stopping NecroCode services...
✅ Services stopped
```

---

## 🧪 テスト実行

### エンドツーエンドテスト

```bash
# 基本テスト
PYTHONPATH=. python3 tests/test_e2e_integration.py

# Pytestで実行
PYTHONPATH=. python3 -m pytest tests/test_e2e_integration.py -v

# 詳細ログ付き
PYTHONPATH=. python3 -m pytest tests/test_e2e_integration.py -v -s
```

### 個別コンポーネントテスト

```bash
# Task Registry
PYTHONPATH=. python3 -m pytest tests/test_task_registry.py

# Dispatcher
PYTHONPATH=. python3 -m pytest tests/test_dispatcher_core.py

# Agent Runner
PYTHONPATH=. python3 -m pytest tests/test_agent_runner_models.py
```

---

## 📊 実行例（完全なワークフロー）

```bash
# 1. セットアップ
$ python necrocode_cli.py setup
🎃 Setting up NecroCode services...
✅ All services configured successfully!

# 2. 環境変数
$ export GITHUB_TOKEN="ghp_..."
$ export OPENAI_API_KEY="sk-..."

# 3. ジョブ投稿
$ python necrocode_cli.py submit \
  --project user-api \
  --repo https://github.com/me/user-api.git \
  "Create REST API with JWT auth"
📝 Submitting job...
✅ Job submitted: job-7f8e9d0c1b2a

# 4. サービス起動
$ python necrocode_cli.py start --detached
🚀 Starting NecroCode services...
✅ Services started in background

# 5. ステータス確認（30秒後）
$ python necrocode_cli.py status
🟢 DISPATCHER - Running (PID: 12345)
🟢 REVIEW_PR_SERVICE - Running (PID: 12346)

# 6. ジョブ確認（5分後）
$ python necrocode_cli.py job status job-7f8e9d0c1b2a
Tasks: 1/3
  ✅ 1: Project setup
  🔄 2: Core implementation
  ⏳ 3: Testing

Pull Requests: 1
  #42: Task 1 (open)

# 7. 完了確認（30分後）
$ python necrocode_cli.py job status job-7f8e9d0c1b2a
Status: completed
Tasks: 3/3
Pull Requests: 3 (all merged)

# 8. 停止
$ python necrocode_cli.py stop
🛑 Stopping services...
✅ Services stopped
```

---

## ⚠️ トラブルシューティング

### エラー: "Address already in use"
```bash
# ポート確認
lsof -i :8000
# プロセス停止
kill -9 <PID>
```

### エラー: "GITHUB_TOKEN not set"
```bash
# 環境変数確認
echo $GITHUB_TOKEN
# 設定
export GITHUB_TOKEN="your_token"
```

### エラー: "Docker image not found"
```bash
# ローカルプロセスに切り替え
vim .necrocode/dispatcher.json
# "type": "docker" → "type": "local_process"
```

### ジョブが実行されない
```bash
# Dispatcherログ確認
python necrocode_cli.py logs --service dispatcher
# Task Registry確認
ls -la .necrocode/data/task_registry/
```

---

## 📚 関連ドキュメント

- **詳細ガイド**: [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)
- **クイックスタート**: [QUICKSTART.md](QUICKSTART.md)
- **統合完了**: [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md)
- **テストログ**: [TEST_EXECUTION_LOG.md](TEST_EXECUTION_LOG.md)

---

## ✅ チェックリスト

実行前に以下を確認してください：

- [ ] Python 3.11以上がインストールされている
- [ ] 依存パッケージがインストールされている
- [ ] GITHUB_TOKEN が設定されている
- [ ] OPENAI_API_KEY が設定されている（LLM使用時）
- [ ] リポジトリへのアクセス権限がある
- [ ] Docker がインストールされている（Docker使用時）

---

## 🎯 次のステップ

1. ✅ 基本的な実行を試す
2. ✅ 小規模プロジェクトでテスト
3. ✅ 設定をカスタマイズ
4. ✅ 本番環境にデプロイ

**Happy Coding with NecroCode! 🎃**

# NecroCode 実行ガイド

## 目次
1. [環境準備](#環境準備)
2. [初回セットアップ](#初回セットアップ)
3. [基本的な使い方](#基本的な使い方)
4. [実行ログ例](#実行ログ例)
5. [トラブルシューティング](#トラブルシューティング)

## 環境準備

### 必要な環境
- Python 3.11以上
- Git
- Docker（オプション、コンテナ実行時）
- GitHub/GitLabアカウントとAPIトークン

### 依存パッケージのインストール

```bash
# リポジトリのクローン
git clone https://github.com/your-org/necrocode.git
cd necrocode

# 依存パッケージのインストール
pip install -r requirements.txt

# CLIを実行可能にする
chmod +x necrocode_cli.py
```

### 環境変数の設定

```bash
# GitHub APIトークン（必須）
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# OpenAI APIキー（LLM使用時に必須）
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# GitLab使用時（オプション）
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
```

## 初回セットアップ

### ステップ1: サービス設定の初期化

```bash
python necrocode_cli.py setup
```


**実行ログ例:**

```
🎃 Setting up NecroCode services...
✅ All services configured successfully!

Configuration files created in: .necrocode

Next steps:
  1. Review and customize config files
  2. Run: necrocode start
```

**作成されるファイル:**
```
.necrocode/
├── task_registry.json      # Task Registry設定
├── repo_pool.json          # Repo Pool Manager設定
├── dispatcher.json         # Dispatcher設定
├── artifact_store.json     # Artifact Store設定
└── review_pr_service.json  # Review PR Service設定
```

### ステップ2: 設定ファイルの確認と調整

```bash
# Dispatcher設定を確認
cat .necrocode/dispatcher.json
```

**デフォルト設定例:**
```json
{
  "poll_interval": 5,
  "scheduling_policy": "priority",
  "max_global_concurrency": 10,
  "heartbeat_timeout": 60,
  "retry_max_attempts": 3,
  "task_registry_dir": ".necrocode/data/task_registry",
  "agent_pools": [
    {
      "name": "local",
      "type": "local_process",
      "max_concurrency": 2,
      "enabled": true
    },
    {
      "name": "docker",
      "type": "docker",
      "max_concurrency": 5,
      "cpu_quota": 4,
      "memory_quota": 8192,
      "enabled": true,
      "config": {
        "image": "necrocode/runner:latest"
      }
    }
  ]
}
```

## 基本的な使い方

### 1. ジョブの投稿

```bash
python necrocode_cli.py submit \
  --project task-manager-api \
  --repo https://github.com/your-org/task-manager-api.git \
  "Create a REST API for task management with user authentication, CRUD operations, and SQLite database"
```

**実行ログ例:**
```
📝 Submitting job: Create a REST API for task management...
✅ Job submitted: job-a1b2c3d4e5f6

Track progress: necrocode job status job-a1b2c3d4e5f6
```

### 2. ジョブステータスの確認

```bash
python necrocode_cli.py job status job-a1b2c3d4e5f6
```

**実行ログ例:**
```
============================================================
Job Status: job-a1b2c3d4e5f6
============================================================

Project: task-manager-api
Status: running
Created: 2025-11-28T10:30:45

Tasks: 1/3
  ✅ 1: Project setup and structure
  🔄 2: Core implementation
  ⏳ 3: Testing and documentation

============================================================
```

### 3. サービスの起動

#### フォアグラウンドで起動（開発時）

```bash
python necrocode_cli.py start
```

**実行ログ例:**
```
🚀 Starting NecroCode services...

⏸️  Press Ctrl+C to stop services...
```

#### バックグラウンドで起動（本番時）

```bash
python necrocode_cli.py start --detached
```

**実行ログ例:**
```
🚀 Starting NecroCode services...
✅ Services started in background

Check status: necrocode status
View logs: necrocode logs
```

### 4. サービスステータスの確認

```bash
python necrocode_cli.py status
```

**実行ログ例:**
```
============================================================
NecroCode Services Status
============================================================

🟢 TASK_REGISTRY
   Status: Running
   PID: 12345

🟢 DISPATCHER
   Status: Running
   PID: 12346
   Port: 8000

🟢 REVIEW_PR_SERVICE
   Status: Running
   PID: 12347
   Port: 8080

🔴 REPO_POOL
   Status: Stopped

🔴 ARTIFACT_STORE
   Status: Stopped

============================================================
```

### 5. ログの確認

#### 全サービスのログを表示

```bash
python necrocode_cli.py logs
```

#### 特定サービスのログを表示

```bash
python necrocode_cli.py logs --service dispatcher
```

#### ログをリアルタイムで追跡

```bash
python necrocode_cli.py logs --follow
```

**実行ログ例:**
```
============================================================
DISPATCHER LOGS
============================================================
2025-11-28 10:35:12 - INFO - Starting Dispatcher...
2025-11-28 10:35:13 - INFO - Loaded 2 agent pools
2025-11-28 10:35:13 - INFO - Main dispatch loop started
2025-11-28 10:35:18 - INFO - Enqueued task 1 (priority=10)
2025-11-28 10:35:18 - INFO - Allocated slot test-slot-1 for task 1
2025-11-28 10:35:19 - INFO - Launched runner runner-abc123 for task 1
2025-11-28 10:35:19 - INFO - Successfully assigned task 1 to runner runner-abc123
```

### 6. ジョブ一覧の確認

```bash
python necrocode_cli.py job list
```

**実行ログ例:**
```
============================================================
Submitted Jobs
============================================================

✅ job-a1b2c3d4e5f6
   Project: task-manager-api
   Status: completed
   Created: 2025-11-28T10:30:45
   Tasks: 3/3

🔄 job-f6e5d4c3b2a1
   Project: chat-app
   Status: running
   Created: 2025-11-28T11:15:22
   Tasks: 2/5

⏳ job-123456789abc
   Project: blog-system
   Status: pending
   Created: 2025-11-28T11:45:10
   Tasks: 0/8

============================================================
```

### 7. サービスの停止

```bash
python necrocode_cli.py stop
```

**実行ログ例:**
```
🛑 Stopping NecroCode services...
✅ Services stopped
```

## 実行ログ例

### 完全なワークフロー実行例

```bash
# 1. セットアップ
$ python necrocode_cli.py setup
```

```
🎃 Setting up NecroCode services...
✅ All services configured successfully!

Configuration files created in: .necrocode

Next steps:
  1. Review and customize config files
  2. Run: necrocode start
```

```bash
# 2. 環境変数設定
$ export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$ export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

```bash
# 3. ジョブ投稿
$ python necrocode_cli.py submit \
  --project user-api \
  --repo https://github.com/myorg/user-api.git \
  "Create a REST API with user authentication (JWT), CRUD operations for users, and PostgreSQL database"
```

```
📝 Submitting job: Create a REST API with user authentication...
✅ Job submitted: job-7f8e9d0c1b2a

Track progress: necrocode job status job-7f8e9d0c1b2a
```

```bash
# 4. ジョブステータス確認
$ python necrocode_cli.py job status job-7f8e9d0c1b2a
```

```
============================================================
Job Status: job-7f8e9d0c1b2a
============================================================

Project: user-api
Status: running
Created: 2025-11-28T14:22:15

Tasks: 0/3
  ⏳ 1: Project setup and structure
  ⏳ 2: Core implementation
  ⏳ 3: Testing and documentation

============================================================
```

```bash
# 5. サービス起動（バックグラウンド）
$ python necrocode_cli.py start --detached
```

```
🚀 Starting NecroCode services...
Starting dispatcher...
Dispatcher started (PID: 45678)
Starting review_pr_service...
Review PR Service started (PID: 45679)
✅ Services started in background

Check status: necrocode status
View logs: necrocode logs
```

```bash
# 6. ステータス確認（30秒後）
$ python necrocode_cli.py status
```

```
============================================================
NecroCode Services Status
============================================================

🟢 TASK_REGISTRY
   Status: Running

🟢 DISPATCHER
   Status: Running
   PID: 45678

🟢 REVIEW_PR_SERVICE
   Status: Running
   PID: 45679
   Port: 8080

============================================================
```

```bash
# 7. ログ確認
$ python necrocode_cli.py logs --service dispatcher --lines 20
```

```
2025-11-28 14:23:01 - INFO - Starting Dispatcher...
2025-11-28 14:23:01 - INFO - Initializing Dispatcher components...
2025-11-28 14:23:01 - INFO - Initialized Task Registry Client
2025-11-28 14:23:01 - INFO - DispatcherCore initialized successfully
2025-11-28 14:23:01 - INFO - Starting Dispatcher...
2025-11-28 14:23:01 - INFO - Dispatcher started successfully
2025-11-28 14:23:01 - INFO - Main dispatch loop started
2025-11-28 14:23:06 - INFO - Polling for ready tasks...
2025-11-28 14:23:06 - INFO - Found 1 ready task(s)
2025-11-28 14:23:06 - INFO - Enqueued task 1 (priority=10)
2025-11-28 14:23:06 - INFO - Scheduling tasks...
2025-11-28 14:23:06 - INFO - Assigning task 1 to pool local
2025-11-28 14:23:06 - INFO - Allocating slot for task 1 from repo 'user-api'
2025-11-28 14:23:07 - INFO - Allocated slot user-api-slot-1 for task 1
2025-11-28 14:23:07 - INFO - Launching local process runner runner-abc123 for task 1
2025-11-28 14:23:07 - INFO - Local runner runner-abc123 started with PID 45680
2025-11-28 14:23:07 - INFO - Updated Task Registry: task 1 -> RUNNING
2025-11-28 14:23:07 - INFO - Successfully assigned task 1 to runner runner-abc123
```

```bash
# 8. ジョブステータス再確認（5分後）
$ python necrocode_cli.py job status job-7f8e9d0c1b2a
```

```
============================================================
Job Status: job-7f8e9d0c1b2a
============================================================

Project: user-api
Status: running
Created: 2025-11-28T14:22:15

Tasks: 1/3
  ✅ 1: Project setup and structure
  🔄 2: Core implementation
  ⏳ 3: Testing and documentation

Pull Requests: 1
  #42: Task 1: Project setup and structure (open)

============================================================
```

```bash
# 9. 完了後のステータス（30分後）
$ python necrocode_cli.py job status job-7f8e9d0c1b2a
```

```
============================================================
Job Status: job-7f8e9d0c1b2a
============================================================

Project: user-api
Status: completed
Created: 2025-11-28T14:22:15

Tasks: 3/3
  ✅ 1: Project setup and structure
  ✅ 2: Core implementation
  ✅ 3: Testing and documentation

Pull Requests: 3
  #42: Task 1: Project setup and structure (merged)
  #43: Task 2: Core implementation (merged)
  #44: Task 3: Testing and documentation (open)

============================================================
```

```bash
# 10. サービス停止
$ python necrocode_cli.py stop
```

```
🛑 Stopping NecroCode services...
Stopping dispatcher...
Sent SIGTERM to dispatcher (PID: 45678)
dispatcher stopped
Stopping review_pr_service...
Sent SIGTERM to review_pr_service (PID: 45679)
review_pr_service stopped
✅ Services stopped
```

## エンドツーエンドテストの実行

### テスト実行

```bash
PYTHONPATH=. python3 tests/test_e2e_integration.py
```

**実行ログ例:**
```
test_service_manager_setup (__main__.TestE2EIntegration)
Test ServiceManager setup. ... ok
test_job_submission (__main__.TestE2EIntegration)
Test job submission workflow. ... ok
test_task_registry_integration (__main__.TestE2EIntegration)
Test Task Registry integration. ... ok
test_dispatcher_integration (__main__.TestE2EIntegration)
Test Dispatcher integration with mocked runner. ... ok
test_complete_workflow_mocked (__main__.TestE2EIntegration)
Test complete workflow with mocked components. ... 
============================================================
Testing Complete Workflow (Mocked)
============================================================

1. Setting up services...
   ✅ Services configured

2. Submitting job...
   ✅ Job submitted: job-eb4d481a5921

3. Verifying Task Registry...
   ✅ Spec created: user-api-job-eb4d
   ✅ Tasks: 3
      - Task 1: Project setup and structure (ready)
      - Task 2: Core implementation (blocked)
      - Task 3: Testing and documentation (blocked)

4. Simulating task execution...
   🔄 Task 1: RUNNING
   ✅ Task 1: DONE
   🔄 Task 2: RUNNING
   ✅ Task 2: DONE
   🔄 Task 3: RUNNING
   ✅ Task 3: DONE

5. Verifying completion...
   Job status: completed
   Tasks completed: 3/3

============================================================
✅ Complete workflow test passed!
============================================================
ok

----------------------------------------------------------------------
Ran 5 tests in 3.039s

OK
```

### Pytestでの実行

```bash
PYTHONPATH=. python3 -m pytest tests/test_e2e_integration.py -v
```

**実行ログ例:**
```
========================= test session starts ==========================
platform darwin -- Python 3.9.6, pytest-7.4.3
collected 5 items

tests/test_e2e_integration.py::TestE2EIntegration::test_service_manager_setup PASSED [ 20%]
tests/test_e2e_integration.py::TestE2EIntegration::test_job_submission PASSED [ 40%]
tests/test_e2e_integration.py::TestE2EIntegration::test_task_registry_integration PASSED [ 60%]
tests/test_e2e_integration.py::TestE2EIntegration::test_dispatcher_integration PASSED [ 80%]
tests/test_e2e_integration.py::TestE2EIntegration::test_complete_workflow_mocked PASSED [100%]

========================== 5 passed in 3.11s ===========================
```

## トラブルシューティング

### 問題1: サービスが起動しない

**症状:**
```
Failed to start dispatcher: [Errno 48] Address already in use
```

**解決方法:**
```bash
# ポートを使用しているプロセスを確認
lsof -i :8000

# プロセスを停止
kill -9 <PID>

# または設定ファイルでポートを変更
vim .necrocode/dispatcher.json
```

### 問題2: ジョブが実行されない

**症状:**
ジョブステータスが`pending`のまま変わらない

**確認手順:**
```bash
# 1. Dispatcherが起動しているか確認
python necrocode_cli.py status

# 2. Dispatcherログを確認
python necrocode_cli.py logs --service dispatcher

# 3. Task Registryにタスクが登録されているか確認
ls -la .necrocode/data/task_registry/
```

### 問題3: 環境変数が設定されていない

**症状:**
```
ERROR: GITHUB_TOKEN not set
```

**解決方法:**
```bash
# 環境変数を設定
export GITHUB_TOKEN="your_token_here"

# 永続化する場合
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

### 問題4: Dockerイメージが見つからない

**症状:**
```
ERROR: Docker image necrocode/runner:latest not found
```

**解決方法:**
```bash
# イメージをビルド
cd docker
docker build -t necrocode/runner:latest .

# または設定でローカルプロセスを使用
vim .necrocode/dispatcher.json
# "type": "docker" を "type": "local_process" に変更
```

## 高度な使い方

### カスタム設定でのサービス起動

```bash
# カスタム設定ディレクトリを指定
python necrocode_cli.py --config-dir /path/to/config start
```

### 特定のサービスのみ起動

```bash
# Dispatcherのみ起動
python necrocode_cli.py start --services dispatcher

# 複数サービスを指定
python necrocode_cli.py start --services dispatcher,review_pr_service
```

### ログレベルの変更

```bash
# Dispatcherを直接起動（デバッグモード）
python -m necrocode.dispatcher.main \
  --config .necrocode/dispatcher.json \
  --log-level DEBUG
```

## まとめ

NecroCodeの基本的な実行フローは以下の通りです：

1. **セットアップ**: `necrocode_cli.py setup`
2. **環境変数設定**: `export GITHUB_TOKEN=...`
3. **ジョブ投稿**: `necrocode_cli.py submit`
4. **サービス起動**: `necrocode_cli.py start --detached`
5. **監視**: `necrocode_cli.py status` / `logs`
6. **PR確認**: GitHubでPRをレビュー
7. **停止**: `necrocode_cli.py stop`

詳細は[QUICKSTART.md](QUICKSTART.md)と[INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md)を参照してください。

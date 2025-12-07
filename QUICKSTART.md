# NecroCode クイックスタートガイド

5分でNecroCodeを始めましょう。

## 前提条件

- Python 3.11+
- Git
- Docker（オプション、コンテナ化されたランナー用）
- APIトークン付きのGitHub/GitLabアカウント

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-org/necrocode.git
cd necrocode

# 依存関係をインストール
pip install -r requirements.txt

# CLIを実行可能にする
chmod +x necrocode_cli.py
```

## クイックスタート

### 1. サービスのセットアップ

デフォルト設定でNecroCodeサービスを初期化：

```bash
python necrocode_cli.py setup
```

これにより`.necrocode/`に設定ファイルが作成されます：
- `task_registry.json` - タスク永続化
- `repo_pool.json` - リポジトリワークスペース管理
- `dispatcher.json` - タスクスケジューリング
- `artifact_store.json` - ビルドアーティファクト
- `review_pr_service.json` - PR自動化

### 2. 認証情報の設定

必要な環境変数を設定：

```bash
# GitHubトークン（PR作成に必要）
export GITHUB_TOKEN="your_github_token"

# LLM APIキー（タスク実装に必要）
export OPENAI_API_KEY="your_openai_api_key"

# オプション：GitLabトークン
export GITLAB_TOKEN="your_gitlab_token"
```

### 3. ジョブの投稿

自然言語でジョブ記述を投稿：

```bash
python necrocode_cli.py submit \
  --project my-api \
  --repo https://github.com/your-org/my-api.git \
  "ユーザー認証とCRUD操作を持つREST APIを作成"
```

これにより：
- ジョブ記述を解析
- タスク分解を生成
- タスクレジストリにタスクを作成
- 追跡用のジョブIDを返却

### 4. サービスの起動

全てのNecroCodeサービスを起動：

```bash
# フォアグラウンドで起動（Ctrl+Cで停止）
python necrocode_cli.py start

# またはバックグラウンドで起動
python necrocode_cli.py start --detached
```

サービスは以下を実行：
- タスクレジストリで準備完了タスクを監視
- ワークスペーススロットを割り当て
- Agent Runnerを起動（Dockerコンテナまたはローカルプロセス）
- LLMでタスクを実行
- PRを自動作成

### 5. 進捗の監視

ジョブステータスを確認：

```bash
python necrocode_cli.py job status <job-id>
```

サービスログを表示：

```bash
# 全サービス
python necrocode_cli.py logs

# 特定のサービス
python necrocode_cli.py logs --service dispatcher

# ログをフォロー
python necrocode_cli.py logs --follow
```

サービスヘルスを確認：

```bash
python necrocode_cli.py status
```

### 6. プルリクエストのレビュー

タスクが完了すると、GitHub/GitLabに自動的にPRが作成されます。

PRをレビューしてマージ：
1. GitHubのリポジトリに移動
2. 自動化されたPRをレビュー
3. 承認されたPRをマージ

## Example Workflow

```bash
# 1. Setup
python necrocode_cli.py setup

# 2. Configure credentials
export GITHUB_TOKEN="ghp_..."
export OPENAI_API_KEY="sk-..."

# 3. Submit job
JOB_ID=$(python necrocode_cli.py submit \
  --project chat-app \
  --repo https://github.com/me/chat-app.git \
  "Create a real-time chat application with WebSocket support" | grep "Job submitted" | awk '{print $3}')

# 4. Start services
python necrocode_cli.py start --detached

# 5. Monitor
watch -n 5 "python necrocode_cli.py job status $JOB_ID"

# 6. Stop when done
python necrocode_cli.py stop
```

## Configuration

### Dispatcher Configuration

Edit `.necrocode/dispatcher.json`:

```json
{
  "poll_interval": 5,
  "scheduling_policy": "priority",
  "max_global_concurrency": 10,
  "agent_pools": [
    {
      "name": "docker",
      "type": "docker",
      "max_concurrency": 5,
      "cpu_quota": 4,
      "memory_quota": 8192,
      "config": {
        "image": "necrocode/runner:latest"
      }
    }
  ]
}
```

### Skill Mapping

Map task types to agent pools:

```json
{
  "skill_mapping": {
    "backend": ["docker"],
    "frontend": ["docker"],
    "database": ["docker"],
    "qa": ["local"],
    "default": ["local"]
  }
}
```

## Docker Runner Setup

Build the runner image:

```bash
cd docker
docker build -t necrocode/runner:latest .
```

Or use pre-built image:

```bash
docker pull necrocode/runner:latest
```

## Kubernetes Setup

For production deployments:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Configure dispatcher for Kubernetes
# Edit .necrocode/dispatcher.json:
{
  "agent_pools": [
    {
      "name": "k8s",
      "type": "kubernetes",
      "max_concurrency": 20,
      "config": {
        "namespace": "necrocode-agents",
        "image": "necrocode/runner:latest"
      }
    }
  ]
}
```

## Troubleshooting

### Services won't start

Check logs:
```bash
python necrocode_cli.py logs
```

Verify configuration:
```bash
ls -la .necrocode/
cat .necrocode/dispatcher.json
```

### Tasks not executing

1. Check Dispatcher is running:
   ```bash
   python necrocode_cli.py status
   ```

2. Verify Task Registry has tasks:
   ```bash
   ls -la .necrocode/data/task_registry/
   ```

3. Check agent pool configuration:
   ```bash
   cat .necrocode/dispatcher.json | jq '.agent_pools'
   ```

### PRs not created

1. Verify GitHub token:
   ```bash
   echo $GITHUB_TOKEN
   ```

2. Check Review PR Service logs:
   ```bash
   python necrocode_cli.py logs --service review_pr_service
   ```

3. Verify webhook configuration (if using webhooks)

## Advanced Usage

### Custom Task Breakdown

Provide custom task breakdown instead of LLM generation:

```python
from necrocode.orchestration.job_submitter import JobSubmitter
from necrocode.task_registry.models import Task, TaskState

submitter = JobSubmitter()

# Create custom tasks
tasks = [
    Task(
        id="1",
        title="Setup database schema",
        description="Create User and Post models",
        state=TaskState.PENDING,
        dependencies=[],
        required_skill="database"
    ),
    Task(
        id="2",
        title="Implement API endpoints",
        description="Create REST endpoints for CRUD operations",
        state=TaskState.PENDING,
        dependencies=["1"],
        required_skill="backend"
    )
]

# Submit with custom tasks
job_id = submitter.submit_job_with_tasks(
    project_name="my-api",
    tasks=tasks,
    repo_url="https://github.com/me/my-api.git"
)
```

### Parallel Execution

Configure parallel execution limits:

```json
{
  "max_global_concurrency": 20,
  "agent_pools": [
    {
      "name": "docker-pool-1",
      "max_concurrency": 10
    },
    {
      "name": "docker-pool-2",
      "max_concurrency": 10
    }
  ]
}
```

### Custom Playbooks

Define custom execution playbooks:

```yaml
# .necrocode/playbooks/backend-api.yaml
name: Backend API Implementation
steps:
  - name: Setup
    commands:
      - npm install
  - name: Implement
    llm_prompt: "Implement the API endpoint as described"
  - name: Test
    commands:
      - npm test
  - name: Lint
    commands:
      - npm run lint
```

## Next Steps

- Read [Architecture Guide](architecture.md) for system design
- See [Development Guide](development.md) for contributing
- Check [Examples](examples/) for more use cases
- Join our [Discord](https://discord.gg/necrocode) for support

## Support

- Documentation: https://necrocode.dev/docs
- Issues: https://github.com/your-org/necrocode/issues
- Discord: https://discord.gg/necrocode
- Email: support@necrocode.dev

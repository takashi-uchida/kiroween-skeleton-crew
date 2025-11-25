# Agent Runner Migration Guide

このガイドは、旧アーキテクチャ（A2A通信ベース）から新アーキテクチャ（外部サービス統合 + LLM）への移行方法を説明します。

## 目次

1. [アーキテクチャの変更点](#アーキテクチャの変更点)
2. [削除されたコンポーネント](#削除されたコンポーネント)
3. [新しいコンポーネント](#新しいコンポーネント)
4. [移行手順](#移行手順)
5. [コード変更例](#コード変更例)
6. [トラブルシューティング](#トラブルシューティング)

## アーキテクチャの変更点

### 旧アーキテクチャ

```
┌──────────────┐
│  Dispatcher  │ ──A2A──► ┌──────────────┐
└──────────────┘          │ Agent Runner │
                          └──────────────┘
┌──────────────┐                 │
│ Message Bus  │ ◄──A2A──────────┤
└──────────────┘                 │
                                 │
┌──────────────┐                 │
│ A2A Client   │ ◄──A2A──────────┤
└──────────────┘                 │
                                 │
┌──────────────┐                 │
│ Kiro Client  │ ◄──────────────┘
└──────────────┘
```

**特徴:**
- A2A（Agent-to-Agent）通信プロトコル
- MessageBusを介したエージェント間通信
- KiroClientを使用したコード生成

### 新アーキテクチャ

```
┌──────────────┐
│  Dispatcher  │ ──HTTP/gRPC──► ┌──────────────┐
└──────────────┘                │ Agent Runner │
                                └──────────────┘
┌──────────────┐                       │
│Task Registry │ ◄──REST API───────────┤
└──────────────┘                       │
                                       │
┌──────────────┐                       │
│ Repo Pool    │ ◄──REST API───────────┤
│ Manager      │                       │
└──────────────┘                       │
                                       │
┌──────────────┐                       │
│ Artifact     │ ◄──REST API───────────┤
│ Store        │                       │
└──────────────┘                       │
                                       │
┌──────────────┐                       │
│ LLM Service  │ ◄──OpenAI API─────────┘
│ (OpenAI)     │
└──────────────┘
```

**特徴:**
- REST API ベースの外部サービス統合
- LLMサービス（OpenAI等）を直接使用
- ステートレスな設計で水平スケール可能

## 削除されたコンポーネント

以下のコンポーネントは新アーキテクチャでは使用されません：

### 1. A2A関連

- `MessageBus` - エージェント間通信バス
- `AgentRegistry` - エージェント登録管理
- `A2AClient` - A2A通信クライアント
- `A2AProtocol` - A2A通信プロトコル

### 2. Kiro関連

- `KiroClient` - Kiroとの通信クライアント
- `KiroAgent` - Kiroエージェント抽象化

これらのコンポーネントは、外部サービスクライアント（TaskRegistryClient、RepoPoolClient、ArtifactStoreClient）とLLMClient に置き換えられました。

## 新しいコンポーネント

### 1. 外部サービスクライアント

#### TaskRegistryClient

タスク状態管理とイベント記録を担当します。

```python
from necrocode.agent_runner import TaskRegistryClient

client = TaskRegistryClient(base_url="http://localhost:8001")

# タスク状態を更新
client.update_task_status(task_id="1.1", status="in_progress")

# イベントを記録
client.add_event(task_id="1.1", event_type="implementation_started", data={})

# 成果物を記録
client.add_artifact(task_id="1.1", artifact_type="diff", uri="s3://...", size_bytes=1024)
```

#### RepoPoolClient

ワークスペース（スロット）の割り当て・返却を担当します。

```python
from necrocode.agent_runner import RepoPoolClient

client = RepoPoolClient(base_url="http://localhost:8002")

# スロットを割り当て
allocation = client.allocate_slot(
    repo_url="https://github.com/user/repo.git",
    required_by="runner-1"
)

# スロットを使用
# ...

# スロットを返却
client.release_slot(allocation.slot_id)
```

#### ArtifactStoreClient

成果物（diff、ログ、テスト結果）の保存を担当します。

```python
from necrocode.agent_runner import ArtifactStoreClient

client = ArtifactStoreClient(base_url="http://localhost:8003")

# 成果物をアップロード
uri = client.upload(
    artifact_type="diff",
    content=b"diff content",
    metadata={"task_id": "1.1"}
)
```

### 2. LLMClient

LLMサービス（OpenAI等）を使用してコードを生成します。

```python
from necrocode.agent_runner import LLMClient, LLMConfig

config = LLMConfig(
    api_key="your-api-key",
    model="gpt-4",
    timeout_seconds=120
)

client = LLMClient(config)

# コードを生成
response = client.generate_code(
    prompt="Create a User model",
    workspace_path=Path("/workspace"),
    max_tokens=4000
)

# 生成されたコード変更を取得
for change in response.code_changes:
    print(f"{change.operation}: {change.file_path}")
```

## 移行手順

### ステップ 1: 依存関係の更新

```bash
# 新しい依存関係をインストール
pip install openai requests

# 不要になった依存関係を削除（オプション）
# pip uninstall a2a-protocol kiro-client
```

### ステップ 2: 設定ファイルの更新

旧設定ファイル（`config.old.yaml`）:

```yaml
execution_mode: local-process
message_bus_url: http://localhost:5000
kiro_url: http://localhost:6000
```

新設定ファイル（`config.yaml`）:

```yaml
execution_mode: local-process

# 外部サービスのURL
task_registry_url: http://localhost:8001
repo_pool_url: http://localhost:8002
artifact_store_url: http://localhost:8003

# LLM設定
llm:
  model: gpt-4
  timeout_seconds: 120
```

### ステップ 3: 環境変数の更新

旧環境変数:

```bash
export MESSAGE_BUS_URL=http://localhost:5000
export KIRO_URL=http://localhost:6000
export GIT_TOKEN=your-token
```

新環境変数:

```bash
export TASK_REGISTRY_URL=http://localhost:8001
export REPO_POOL_URL=http://localhost:8002
export ARTIFACT_STORE_URL=http://localhost:8003
export OPENAI_API_KEY=your-api-key
export GIT_TOKEN=your-token
```

### ステップ 4: コードの更新

詳細は次のセクション「コード変更例」を参照してください。

### ステップ 5: 外部サービスの起動

新アーキテクチャでは、以下の外部サービスが必要です：

```bash
# Task Registry
docker run -p 8001:8001 necrocode/task-registry

# Repo Pool Manager
docker run -p 8002:8002 necrocode/repo-pool

# Artifact Store
docker run -p 8003:8003 necrocode/artifact-store
```

または、docker-compose を使用:

```bash
docker-compose up -d
```

### ステップ 6: 動作確認

```bash
# サンプルコードを実行して動作確認
python examples/basic_runner_usage.py
```

## コード変更例

### 例1: RunnerOrchestratorの初期化

#### 旧コード

```python
from necrocode.agent_runner import RunnerOrchestrator, RunnerConfig

config = RunnerConfig(
    execution_mode="local-process",
    message_bus_url="http://localhost:5000",
    kiro_url="http://localhost:6000"
)

orchestrator = RunnerOrchestrator(config)
```

#### 新コード

```python
from necrocode.agent_runner import RunnerOrchestrator, RunnerConfig, LLMConfig

# LLM設定を作成
llm_config = LLMConfig(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4",
    timeout_seconds=120
)

# Runner設定を作成
config = RunnerConfig(
    execution_mode="local-process",
    task_registry_url="http://localhost:8001",
    repo_pool_url="http://localhost:8002",
    artifact_store_url="http://localhost:8003",
    llm_config=llm_config
)

orchestrator = RunnerOrchestrator(config)
```

### 例2: タスク実行

#### 旧コード

```python
# A2AClientを使用してタスクを受信
task = a2a_client.receive_task()

# KiroClientを使用してコードを生成
code = kiro_client.generate_code(task.description)

# MessageBusを使用して結果を送信
message_bus.send_result(task.id, code)
```

#### 新コード

```python
# TaskContextを作成
task_context = TaskContext(
    task_id="1.1",
    spec_name="chat-app",
    title="データベーススキーマの実装",
    description="UserとMessageモデルを作成",
    acceptance_criteria=[...],
    dependencies=[],
    required_skill="backend",
    slot_path=Path("/workspace"),
    slot_id="slot-1",
    branch_name="feature/task-1.1-database-schema"
)

# Runnerを実行（内部でLLMClient、外部サービスクライアントを使用）
result = orchestrator.run(task_context)

# 結果は自動的にTask Registryに記録される
```

### 例3: 成果物のアップロード

#### 旧コード

```python
# ローカルファイルシステムに保存
with open("/tmp/artifacts/diff.patch", "w") as f:
    f.write(diff_content)

# MessageBusで通知
message_bus.notify_artifact_created(task_id, "/tmp/artifacts/diff.patch")
```

#### 新コード

```python
# ArtifactStoreClientを使用（RunnerOrchestrator内部で自動的に実行）
# 手動でアップロードする場合:
from necrocode.agent_runner import ArtifactStoreClient

client = ArtifactStoreClient(base_url="http://localhost:8003")
uri = client.upload(
    artifact_type="diff",
    content=diff_content.encode(),
    metadata={"task_id": "1.1"}
)

# Task Registryに記録
task_registry_client.add_artifact(
    task_id="1.1",
    artifact_type="diff",
    uri=uri,
    size_bytes=len(diff_content)
)
```

## トラブルシューティング

### 問題1: 外部サービスに接続できない

**症状:**
```
ConnectionError: Failed to connect to http://localhost:8001
```

**解決方法:**

1. 外部サービスが起動しているか確認:
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   ```

2. 設定ファイルのURLが正しいか確認:
   ```yaml
   task_registry_url: http://localhost:8001  # ポート番号を確認
   ```

3. Dockerネットワークを使用している場合、サービス名を使用:
   ```yaml
   task_registry_url: http://task-registry:8001
   ```

### 問題2: LLM APIキーが無効

**症状:**
```
AuthenticationError: Invalid API key
```

**解決方法:**

1. 環境変数が設定されているか確認:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. APIキーが有効か確認:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. 設定ファイルで正しい環境変数名を指定:
   ```yaml
   llm_api_key_env_var: OPENAI_API_KEY
   ```

### 問題3: スロット割り当てに失敗

**症状:**
```
SlotAllocationError: No available slots
```

**解決方法:**

1. Repo Pool Managerの状態を確認:
   ```bash
   curl http://localhost:8002/pools/status
   ```

2. スロットを手動で解放:
   ```bash
   curl -X POST http://localhost:8002/slots/{slot_id}/release
   ```

3. プールサイズを増やす（Repo Pool Managerの設定）:
   ```yaml
   pool_size: 10  # デフォルト: 5
   ```

### 問題4: タスク状態が更新されない

**症状:**
タスクが完了してもTask Registryに反映されない

**解決方法:**

1. Task Registryのログを確認:
   ```bash
   docker logs task-registry
   ```

2. TaskRegistryClientの接続を確認:
   ```python
   client = TaskRegistryClient(base_url="http://localhost:8001")
   # テスト
   client.update_task_status("test", "in_progress")
   ```

3. ネットワークエラーのリトライ設定を確認:
   ```yaml
   network_retry_count: 3
   ```

## 参考資料

- [Agent Runner README](necrocode/agent_runner/README.md)
- [Requirements](.kiro/specs/agent-runner/requirements.md)
- [Design](.kiro/specs/agent-runner/design.md)
- [Sample Code](examples/)

## サポート

移行に関する質問や問題がある場合は、以下のリソースを参照してください：

- GitHub Issues: https://github.com/necrocode/agent-runner/issues
- Documentation: https://docs.necrocode.dev
- Community Forum: https://forum.necrocode.dev

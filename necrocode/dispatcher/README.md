# Dispatcher

Dispatcherは、NecroCodeシステムにおいてタスクのスケジューリングとAgent Runnerへの割当を行うコンポーネントです。Task RegistryからReadyタスクを監視し、必要スキルと利用可能なAgent Poolに基づいて実行予約を行い、Repo Pool Managerからスロットを確保してAgent Runnerに情報を渡します。

## 目次

- [概要](#概要)
- [インストール](#インストール)
- [クイックスタート](#クイックスタート)
- [アーキテクチャ](#アーキテクチャ)
- [コンポーネント](#コンポーネント)
- [設定](#設定)
- [使用例](#使用例)
- [API リファレンス](#apiリファレンス)
- [トラブルシューティング](#トラブルシューティング)

## 概要

Dispatcherは以下の機能を提供します：

- **タスク監視**: Task RegistryからReadyタスクを定期的にポーリング
- **スケジューリング**: 複数のポリシー（FIFO、優先度、スキルベース、公平分配）をサポート
- **Agent Pool管理**: local-process、Docker、Kubernetesの複数プールを管理
- **並行実行制御**: プールごとの最大同時実行数を制御
- **Runner監視**: Agent Runnerのハートビートとタイムアウトを監視
- **再試行管理**: 失敗したタスクの自動再試行（指数バックオフ）
- **デッドロック検出**: タスク依存関係の循環を検出
- **メトリクス収集**: Prometheus形式でメトリクスをエクスポート

## インストール

### 前提条件

- Python 3.11以上
- Task Registry（necrocode/task_registry）
- Repo Pool Manager（necrocode/repo_pool）

### 依存関係のインストール

```bash
pip install pyyaml>=6.0
pip install docker>=6.1.0  # Dockerプールを使用する場合
pip install kubernetes>=27.2.0  # Kubernetesプールを使用する場合
pip install prometheus-client>=0.17.0  # メトリクスエクスポート用
```

## クイックスタート

### 基本的な使用例

```python
from necrocode.dispatcher import DispatcherCore, DispatcherConfig
from necrocode.dispatcher.models import SchedulingPolicy

# 設定を作成
config = DispatcherConfig(
    poll_interval=5,
    scheduling_policy=SchedulingPolicy.PRIORITY,
    max_global_concurrency=10
)

# Dispatcherを起動
dispatcher = DispatcherCore(config)
dispatcher.start()

# グレースフルシャットダウン
dispatcher.stop(timeout=300)
```

### 設定ファイルを使用

```python
from necrocode.dispatcher import DispatcherCore
from necrocode.dispatcher.config import load_config

# YAMLファイルから設定を読み込み
config = load_config("config/dispatcher.yaml")

# Dispatcherを起動
dispatcher = DispatcherCore(config)
dispatcher.start()
```

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                       Dispatcher                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  DispatcherCore  │      │  TaskMonitor     │           │
│  │  (Main Loop)     │◄────►│  (Polling)       │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  TaskQueue       │      │  Scheduler       │           │
│  │  (Priority Queue)│      │  (Policy)        │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  AgentPoolManager│      │  RunnerLauncher  │           │
│  │  (Pool Mgmt)     │      │  (Launch)        │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  RunnerMonitor   │      │  MetricsCollector│           │
│  │  (Heartbeat)     │      │  (Metrics)       │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## コンポーネント

### DispatcherCore

メインコントローラー。すべてのコンポーネントを統合し、メインループを実行します。

### TaskMonitor

Task RegistryからReadyタスクを定期的にポーリングし、依存関係が解決されたタスクを取得します。

### TaskQueue

優先度付きキュー。タスクを優先度順に管理し、スレッドセーフな操作を提供します。

### Scheduler

スケジューリングポリシーに基づいてタスクを選択します：
- **FIFO**: 先入先出
- **Priority**: 優先度ベース
- **Skill-based**: スキルベース
- **Fair-share**: 公平分配

### AgentPoolManager

Agent Poolの管理と選択を行います。スキルマッピング、負荷分散、リソースクォータ管理を提供します。

### RunnerLauncher

Agent Runnerを起動します。local-process、Docker、Kubernetesの3つのランチャーをサポートします。

### RunnerMonitor

Agent Runnerの監視とハートビートチェックを行います。タイムアウトを検出し、タスクを再割当します。

### MetricsCollector

メトリクスを収集し、Prometheus形式でエクスポートします。

### RetryManager

失敗したタスクの再試行を管理します。指数バックオフをサポートします。

### DeadlockDetector

タスク依存関係の循環を検出し、デッドロックを警告します。

### EventRecorder

Task Registryへのイベント送信を管理します。

## 設定

### 設定ファイル形式

```yaml
# config/dispatcher.yaml
dispatcher:
  poll_interval: 5  # 秒
  scheduling_policy: priority  # fifo, priority, skill-based, fair-share
  max_global_concurrency: 10
  heartbeat_timeout: 60  # 秒
  retry_max_attempts: 3
  retry_backoff_base: 2.0
  graceful_shutdown_timeout: 300  # 秒

agent_pools:
  local:
    type: local-process
    max_concurrency: 2
    enabled: true
  
  docker:
    type: docker
    max_concurrency: 4
    cpu_quota: 4
    memory_quota: 8192  # MB
    enabled: true
    config:
      image: necrocode/runner:latest
      mount_repo_pool: true
  
  k8s:
    type: kubernetes
    max_concurrency: 10
    cpu_quota: 10
    memory_quota: 20480  # MB
    enabled: true
    config:
      namespace: necrocode-agents
      job_template: manifests/runner-job.yaml

skill_mapping:
  backend: [docker, k8s]
  frontend: [docker, k8s]
  database: [docker]
  devops: [k8s]
  default: [local]
```

### プログラムによる設定

```python
from necrocode.dispatcher import DispatcherConfig
from necrocode.dispatcher.models import AgentPool, PoolType, SchedulingPolicy

config = DispatcherConfig(
    poll_interval=5,
    scheduling_policy=SchedulingPolicy.PRIORITY,
    max_global_concurrency=10,
    heartbeat_timeout=60,
    retry_max_attempts=3,
    retry_backoff_base=2.0
)

# Agent Poolを追加
local_pool = AgentPool(
    name="local",
    type=PoolType.LOCAL_PROCESS,
    max_concurrency=2,
    enabled=True
)
config.agent_pools.append(local_pool)

# スキルマッピングを設定
config.skill_mapping = {
    "backend": ["docker", "k8s"],
    "frontend": ["docker", "k8s"],
    "default": ["local"]
}
```

## 使用例

詳細な使用例は`examples/`ディレクトリを参照してください：

- `basic_dispatcher_usage.py`: 基本的な使用例
- `custom_scheduling_policy.py`: カスタムスケジューリングポリシー
- `multi_pool_setup.py`: 複数Agent Poolの設定
- `dispatcher_core_example.py`: DispatcherCoreの詳細な使用例
- `agent_pool_manager_example.py`: AgentPoolManagerの使用例
- `runner_launcher_example.py`: RunnerLauncherの使用例
- `runner_monitor_example.py`: RunnerMonitorの使用例
- `metrics_collector_example.py`: MetricsCollectorの使用例
- `retry_manager_example.py`: RetryManagerの使用例
- `deadlock_detector_example.py`: DeadlockDetectorの使用例
- `event_recorder_example.py`: EventRecorderの使用例
- `priority_management_example.py`: 優先度管理の使用例
- `concurrency_control_example.py`: 並行実行制御の使用例

## API リファレンス

### DispatcherCore

```python
class DispatcherCore:
    """Dispatcherのメインコントローラー"""
    
    def __init__(self, config: DispatcherConfig):
        """
        Args:
            config: Dispatcher設定
        """
    
    def start(self) -> None:
        """Dispatcherを起動"""
    
    def stop(self, timeout: int = 300) -> None:
        """
        Dispatcherを停止（グレースフルシャットダウン）
        
        Args:
            timeout: シャットダウンタイムアウト（秒）
        """
    
    def get_status(self) -> Dict[str, Any]:
        """
        Dispatcherの状態を取得
        
        Returns:
            状態情報の辞書
        """
```

### TaskMonitor

```python
class TaskMonitor:
    """Task Registryの監視"""
    
    def __init__(self, config: DispatcherConfig):
        """
        Args:
            config: Dispatcher設定
        """
    
    def poll_ready_tasks(self) -> List[Task]:
        """
        Readyタスクを取得
        
        Returns:
            Readyタスクのリスト
        """
```

### TaskQueue

```python
class TaskQueue:
    """タスクキュー"""
    
    def enqueue(self, task: Task) -> None:
        """
        タスクをキューに追加
        
        Args:
            task: 追加するタスク
        """
    
    def dequeue(self) -> Optional[Task]:
        """
        タスクをキューから取得
        
        Returns:
            タスク、またはキューが空の場合はNone
        """
    
    def peek(self) -> Optional[Task]:
        """
        キューの先頭を確認（取得しない）
        
        Returns:
            タスク、またはキューが空の場合はNone
        """
    
    def size(self) -> int:
        """
        キューのサイズを取得
        
        Returns:
            キュー内のタスク数
        """
    
    def clear(self) -> None:
        """キューをクリア"""
```

### Scheduler

```python
class Scheduler:
    """スケジューラー"""
    
    def __init__(self, policy: SchedulingPolicy):
        """
        Args:
            policy: スケジューリングポリシー
        """
    
    def schedule(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """
        タスクをスケジューリング
        
        Args:
            task_queue: タスクキュー
            agent_pool_manager: Agent Pool Manager
        
        Returns:
            (タスク, Agent Pool)のタプルのリスト
        """
```

### AgentPoolManager

```python
class AgentPoolManager:
    """Agent Poolの管理"""
    
    def __init__(self, config: DispatcherConfig):
        """
        Args:
            config: Dispatcher設定
        """
    
    def get_pool_for_skill(self, skill: str) -> Optional[AgentPool]:
        """
        スキルに対応するAgent Poolを取得
        
        Args:
            skill: スキル名
        
        Returns:
            Agent Pool、または見つからない場合はNone
        """
    
    def can_accept_task(self, pool: AgentPool) -> bool:
        """
        プールがタスクを受け入れ可能か確認
        
        Args:
            pool: Agent Pool
        
        Returns:
            受け入れ可能な場合はTrue
        """
    
    def get_pool_status(self, pool_name: str) -> PoolStatus:
        """
        プールの状態を取得
        
        Args:
            pool_name: プール名
        
        Returns:
            プールの状態
        """
```

### RunnerLauncher

```python
class RunnerLauncher:
    """Agent Runnerの起動"""
    
    def launch(
        self,
        task: Task,
        slot: Slot,
        pool: AgentPool
    ) -> Runner:
        """
        Agent Runnerを起動
        
        Args:
            task: タスク
            slot: Repo Poolスロット
            pool: Agent Pool
        
        Returns:
            起動したRunner情報
        
        Raises:
            RunnerLaunchError: 起動に失敗した場合
        """
```

### RunnerMonitor

```python
class RunnerMonitor:
    """Agent Runnerの監視"""
    
    def add_runner(self, runner: Runner) -> None:
        """
        Runnerを監視対象に追加
        
        Args:
            runner: Runner情報
        """
    
    def update_heartbeat(self, runner_id: str) -> None:
        """
        ハートビートを更新
        
        Args:
            runner_id: Runner ID
        """
    
    def check_heartbeats(self) -> None:
        """ハートビートをチェック"""
    
    def remove_runner(self, runner_id: str) -> None:
        """
        Runnerを監視対象から削除
        
        Args:
            runner_id: Runner ID
        """
    
    def get_runner_status(self, runner_id: str) -> Optional[RunnerInfo]:
        """
        Runnerの状態を取得
        
        Args:
            runner_id: Runner ID
        
        Returns:
            Runner情報、または見つからない場合はNone
        """
```

### MetricsCollector

```python
class MetricsCollector:
    """メトリクスの収集"""
    
    def collect(self) -> None:
        """メトリクスを収集"""
    
    def record_assignment(self, task: Task, pool: AgentPool) -> None:
        """
        タスク割当を記録
        
        Args:
            task: タスク
            pool: Agent Pool
        """
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        メトリクスを取得
        
        Returns:
            メトリクスの辞書
        """
    
    def export_prometheus(self) -> str:
        """
        Prometheus形式でエクスポート
        
        Returns:
            Prometheus形式のメトリクス文字列
        """
```

## トラブルシューティング

### タスクが割り当てられない

**症状**: Readyタスクがあるのに、Agent Runnerに割り当てられない

**原因と対処**:
1. Agent Poolの最大同時実行数に達している
   - `get_pool_status()`でプールの状態を確認
   - `max_concurrency`を増やす
2. スキルマッピングが正しくない
   - タスクの`required_skill`とプール設定を確認
3. Repo Poolのスロットが不足している
   - Repo Pool Managerのログを確認

### Runner起動に失敗する

**症状**: `RunnerLaunchError`が発生する

**原因と対処**:
1. Dockerデーモンが起動していない（Dockerプールの場合）
   - `docker ps`で確認
2. Kubernetesクラスタに接続できない（K8sプールの場合）
   - `kubectl cluster-info`で確認
3. 環境変数が設定されていない
   - `DOCKER_HOST`、`KUBECONFIG`などを確認

### ハートビートタイムアウトが頻発する

**症状**: Runnerが正常に動作しているのにタイムアウトする

**原因と対処**:
1. `heartbeat_timeout`が短すぎる
   - 設定を60秒以上に増やす
2. ネットワーク遅延が大きい
   - タイムアウト値を調整
3. Runnerの負荷が高い
   - プールの`max_concurrency`を減らす

### デッドロックが検出される

**症状**: `DeadlockDetectedError`が発生する

**原因と対処**:
1. タスクの依存関係に循環がある
   - Task Registryのタスク定義を確認
   - 依存関係グラフを可視化（`graph_visualizer.py`）
2. 手動でタスクの依存関係を修正
   - Task Registryで依存関係を更新

### メトリクスが収集されない

**症状**: `export_prometheus()`が空の文字列を返す

**原因と対処**:
1. `prometheus-client`がインストールされていない
   - `pip install prometheus-client`
2. `collect()`が呼ばれていない
   - メインループで定期的に呼び出されているか確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題が発生した場合は、GitHubのIssueを作成してください。

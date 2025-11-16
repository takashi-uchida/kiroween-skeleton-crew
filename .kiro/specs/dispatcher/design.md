# Dispatcher Design Document

## Overview

Dispatcherは、Task RegistryからReadyタスクを監視し、スキルベースのルーティングとリソース管理に基づいてAgent Runnerに割り当てるスケジューリングコンポーネントです。複数のAgent Pool（local-process/docker/k8s）を管理し、並行実行制御、優先度管理、デッドロック検出を行います。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     NecroCode System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task Registry ──────► Dispatcher ◄────── Agent Pool       │
│                           │                                 │
│                           ▼                                 │
│                    Repo Pool Manager                        │
│                           │                                 │
│                           ▼                                 │
│                    Agent Runner (×N)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

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

## Components and Interfaces

### 1. DispatcherCore (Main Loop)

Dispatcherのメインループを制御します。

```python
class DispatcherCore:
    """Dispatcherのメインコントローラー"""
    
    def __init__(self, config: DispatcherConfig):
        """
        Args:
            config: Dispatcher設定
        """
        self.config = config
        self.running = False
        self.task_monitor = TaskMonitor(config)
        self.task_queue = TaskQueue()
        self.scheduler = Scheduler(config.scheduling_policy)
        self.agent_pool_manager = AgentPoolManager(config)
        self.runner_launcher = RunnerLauncher()
        self.runner_monitor = RunnerMonitor()
        self.metrics_collector = MetricsCollector()
    
    def start(self) -> None:
        """Dispatcherを起動"""
        self.running = True
        self._main_loop()
    
    def stop(self, timeout: int = 300) -> None:
        """Dispatcherを停止（グレースフルシャットダウン）"""
        self.running = False
        self._wait_for_runners(timeout)
    
    def _main_loop(self) -> None:
        """メインループ"""
        while self.running:
            try:
                # 1. Readyタスクを取得
                ready_tasks = self.task_monitor.poll_ready_tasks()
                
                # 2. タスクをキューに追加
                for task in ready_tasks:
                    self.task_queue.enqueue(task)
                
                # 3. スケジューリング
                scheduled_tasks = self.scheduler.schedule(
                    self.task_queue,
                    self.agent_pool_manager
                )
                
                # 4. タスクを割り当て
                for task, pool in scheduled_tasks:
                    self._assign_task(task, pool)
                
                # 5. Runnerを監視
                self.runner_monitor.check_heartbeats()
                
                # 6. メトリクスを収集
                self.metrics_collector.collect()
                
                # 7. 待機
                time.sleep(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
    
    def _assign_task(self, task: Task, pool: AgentPool) -> None:
        """タスクを割り当て"""
        try:
            # 1. スロットを割り当て
            slot = self._allocate_slot(task)
            if not slot:
                self.task_queue.enqueue(task)  # キューに戻す
                return
            
            # 2. Runnerを起動
            runner = self.runner_launcher.launch(task, slot, pool)
            
            # 3. Task Registryを更新
            self._update_task_registry(task, runner, slot)
            
            # 4. Runnerを監視対象に追加
            self.runner_monitor.add_runner(runner)
            
            # 5. メトリクスを更新
            self.metrics_collector.record_assignment(task, pool)
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.id}: {e}")
            self.task_queue.enqueue(task)  # キューに戻す
    
    def _allocate_slot(self, task: Task) -> Optional[Slot]:
        """スロットを割り当て"""
        pass
    
    def _update_task_registry(self, task: Task, runner: Runner, slot: Slot) -> None:
        """Task Registryを更新"""
        pass
    
    def _wait_for_runners(self, timeout: int) -> None:
        """実行中のRunnerの完了を待機"""
        pass

### 2. TaskMonitor (Task Polling)

Task RegistryからReadyタスクを定期的に取得します。

```python
class TaskMonitor:
    """Task Registryの監視"""
    
    def __init__(self, config: DispatcherConfig):
        self.config = config
        self.task_registry_client = TaskRegistryClient()
    
    def poll_ready_tasks(self) -> List[Task]:
        """Readyタスクを取得"""
        try:
            tasks = self.task_registry_client.get_ready_tasks()
            return self._filter_tasks(tasks)
        except Exception as e:
            logger.error(f"Failed to poll tasks: {e}")
            return []
    
    def _filter_tasks(self, tasks: List[Task]) -> List[Task]:
        """タスクをフィルタリング"""
        # 依存関係が解決されたタスクのみを返す
        pass

### 3. TaskQueue (Priority Queue)

タスクを優先度順に管理します。

```python
class TaskQueue:
    """タスクキュー"""
    
    def __init__(self):
        self.queue: PriorityQueue = PriorityQueue()
        self.lock = threading.Lock()
    
    def enqueue(self, task: Task) -> None:
        """タスクをキューに追加"""
        with self.lock:
            priority = -task.priority  # 高い優先度が先
            self.queue.put((priority, task.created_at, task))
    
    def dequeue(self) -> Optional[Task]:
        """タスクをキューから取得"""
        with self.lock:
            if self.queue.empty():
                return None
            _, _, task = self.queue.get()
            return task
    
    def peek(self) -> Optional[Task]:
        """キューの先頭を確認（取得しない）"""
        pass
    
    def size(self) -> int:
        """キューのサイズを取得"""
        return self.queue.qsize()
    
    def clear(self) -> None:
        """キューをクリア"""
        with self.lock:
            self.queue = PriorityQueue()

### 4. Scheduler (Scheduling Policy)

スケジューリングポリシーに基づいてタスクを選択します。

```python
class Scheduler:
    """スケジューラー"""
    
    def __init__(self, policy: SchedulingPolicy):
        self.policy = policy
    
    def schedule(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """タスクをスケジューリング"""
        if self.policy == SchedulingPolicy.FIFO:
            return self._schedule_fifo(task_queue, agent_pool_manager)
        elif self.policy == SchedulingPolicy.PRIORITY:
            return self._schedule_priority(task_queue, agent_pool_manager)
        elif self.policy == SchedulingPolicy.SKILL_BASED:
            return self._schedule_skill_based(task_queue, agent_pool_manager)
        elif self.policy == SchedulingPolicy.FAIR_SHARE:
            return self._schedule_fair_share(task_queue, agent_pool_manager)
        else:
            raise ValueError(f"Unknown scheduling policy: {self.policy}")
    
    def _schedule_fifo(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """FIFO（先入先出）スケジューリング"""
        pass
    
    def _schedule_priority(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """優先度ベーススケジューリング"""
        pass
    
    def _schedule_skill_based(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """スキルベーススケジューリング"""
        pass
    
    def _schedule_fair_share(
        self,
        task_queue: TaskQueue,
        agent_pool_manager: AgentPoolManager
    ) -> List[Tuple[Task, AgentPool]]:
        """公平分配スケジューリング"""
        pass

### 5. AgentPoolManager (Pool Management)

Agent Poolの管理と選択を行います。

```python
class AgentPoolManager:
    """Agent Poolの管理"""
    
    def __init__(self, config: DispatcherConfig):
        self.config = config
        self.pools: Dict[str, AgentPool] = {}
        self.skill_mapping: Dict[str, List[str]] = {}  # skill -> [pool_name]
        self._load_pools()
    
    def _load_pools(self) -> None:
        """Agent Pool設定を読み込み"""
        pass
    
    def get_pool_for_skill(self, skill: str) -> Optional[AgentPool]:
        """スキルに対応するAgent Poolを取得"""
        pool_names = self.skill_mapping.get(skill, [])
        if not pool_names:
            return self.get_default_pool()
        
        # 負荷分散: 最も空いているプールを選択
        return self._select_least_loaded_pool(pool_names)
    
    def get_default_pool(self) -> Optional[AgentPool]:
        """デフォルトAgent Poolを取得"""
        pass
    
    def _select_least_loaded_pool(self, pool_names: List[str]) -> Optional[AgentPool]:
        """最も空いているプールを選択"""
        pass
    
    def can_accept_task(self, pool: AgentPool) -> bool:
        """プールがタスクを受け入れ可能か確認"""
        # 最大同時実行数とリソースクォータをチェック
        pass
    
    def increment_running_count(self, pool: AgentPool) -> None:
        """実行中タスク数をインクリメント"""
        pass
    
    def decrement_running_count(self, pool: AgentPool) -> None:
        """実行中タスク数をデクリメント"""
        pass
    
    def get_pool_status(self, pool_name: str) -> PoolStatus:
        """プールの状態を取得"""
        pass

### 6. RunnerLauncher (Runner Launch)

Agent Runnerを起動します。

```python
class RunnerLauncher:
    """Agent Runnerの起動"""
    
    def __init__(self):
        self.local_launcher = LocalProcessLauncher()
        self.docker_launcher = DockerLauncher()
        self.k8s_launcher = KubernetesLauncher()
    
    def launch(
        self,
        task: Task,
        slot: Slot,
        pool: AgentPool
    ) -> Runner:
        """Agent Runnerを起動"""
        runner_id = self._generate_runner_id()
        task_context = self._build_task_context(task, slot)
        
        if pool.type == PoolType.LOCAL_PROCESS:
            return self.local_launcher.launch(runner_id, task_context, pool)
        elif pool.type == PoolType.DOCKER:
            return self.docker_launcher.launch(runner_id, task_context, pool)
        elif pool.type == PoolType.KUBERNETES:
            return self.k8s_launcher.launch(runner_id, task_context, pool)
        else:
            raise ValueError(f"Unknown pool type: {pool.type}")
    
    def _generate_runner_id(self) -> str:
        """Runner IDを生成"""
        pass
    
    def _build_task_context(self, task: Task, slot: Slot) -> TaskContext:
        """タスクコンテキストを構築"""
        pass

class LocalProcessLauncher:
    """ローカルプロセスとして起動"""
    
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """ローカルプロセスを起動"""
        pass

class DockerLauncher:
    """Dockerコンテナとして起動"""
    
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """Dockerコンテナを起動"""
        pass

class KubernetesLauncher:
    """Kubernetes Jobとして起動"""
    
    def launch(
        self,
        runner_id: str,
        task_context: TaskContext,
        pool: AgentPool
    ) -> Runner:
        """Kubernetes Jobを起動"""
        pass

### 7. RunnerMonitor (Runner Monitoring)

Agent Runnerの監視とハートビートチェックを行います。

```python
class RunnerMonitor:
    """Agent Runnerの監視"""
    
    def __init__(self):
        self.runners: Dict[str, RunnerInfo] = {}
        self.heartbeat_timeout = 60  # 秒
    
    def add_runner(self, runner: Runner) -> None:
        """Runnerを監視対象に追加"""
        self.runners[runner.runner_id] = RunnerInfo(
            runner=runner,
            last_heartbeat=datetime.now(),
            state=RunnerState.RUNNING
        )
    
    def update_heartbeat(self, runner_id: str) -> None:
        """ハートビートを更新"""
        if runner_id in self.runners:
            self.runners[runner_id].last_heartbeat = datetime.now()
    
    def check_heartbeats(self) -> None:
        """ハートビートをチェック"""
        now = datetime.now()
        for runner_id, info in list(self.runners.items()):
            elapsed = (now - info.last_heartbeat).total_seconds()
            if elapsed > self.heartbeat_timeout:
                self._handle_timeout(runner_id, info)
    
    def _handle_timeout(self, runner_id: str, info: RunnerInfo) -> None:
        """タイムアウトを処理"""
        logger.warning(f"Runner {runner_id} timeout detected")
        # タスクを再割当
        pass
    
    def remove_runner(self, runner_id: str) -> None:
        """Runnerを監視対象から削除"""
        if runner_id in self.runners:
            del self.runners[runner_id]
    
    def get_runner_status(self, runner_id: str) -> Optional[RunnerInfo]:
        """Runnerの状態を取得"""
        return self.runners.get(runner_id)

### 8. MetricsCollector (Metrics Collection)

メトリクスを収集します。

```python
class MetricsCollector:
    """メトリクスの収集"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
    
    def collect(self) -> None:
        """メトリクスを収集"""
        self.metrics = {
            "queue_size": self._get_queue_size(),
            "running_tasks": self._get_running_tasks_count(),
            "pool_utilization": self._get_pool_utilization(),
            "average_wait_time": self._get_average_wait_time(),
            "timestamp": datetime.now().isoformat()
        }
    
    def record_assignment(self, task: Task, pool: AgentPool) -> None:
        """タスク割当を記録"""
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクスを取得"""
        return self.metrics
    
    def export_prometheus(self) -> str:
        """Prometheus形式でエクスポート"""
        pass
    
    def _get_queue_size(self) -> int:
        """キューサイズを取得"""
        pass
    
    def _get_running_tasks_count(self) -> int:
        """実行中タスク数を取得"""
        pass
    
    def _get_pool_utilization(self) -> Dict[str, float]:
        """プール使用率を取得"""
        pass
    
    def _get_average_wait_time(self) -> float:
        """平均待機時間を取得"""
        pass

## Data Models

### AgentPool

```python
@dataclass
class AgentPool:
    """Agent Pool定義"""
    name: str
    type: PoolType
    max_concurrency: int
    current_running: int = 0
    
    # リソースクォータ
    cpu_quota: Optional[int] = None  # CPU cores
    memory_quota: Optional[int] = None  # MB
    
    # 設定
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    def can_accept_task(self) -> bool:
        """タスクを受け入れ可能か"""
        return self.enabled and self.current_running < self.max_concurrency

class PoolType(Enum):
    """プールタイプ"""
    LOCAL_PROCESS = "local-process"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"

### Runner

```python
@dataclass
class Runner:
    """Agent Runner情報"""
    runner_id: str
    task_id: str
    pool_name: str
    slot_id: str
    state: RunnerState
    started_at: datetime
    pid: Optional[int] = None  # ローカルプロセスの場合
    container_id: Optional[str] = None  # Dockerの場合
    job_name: Optional[str] = None  # Kubernetesの場合

class RunnerState(Enum):
    """Runner状態"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

### RunnerInfo

```python
@dataclass
class RunnerInfo:
    """Runner監視情報"""
    runner: Runner
    last_heartbeat: datetime
    state: RunnerState

### SchedulingPolicy

```python
class SchedulingPolicy(Enum):
    """スケジューリングポリシー"""
    FIFO = "fifo"
    PRIORITY = "priority"
    SKILL_BASED = "skill-based"
    FAIR_SHARE = "fair-share"

### PoolStatus

```python
@dataclass
class PoolStatus:
    """プール状態"""
    pool_name: str
    type: PoolType
    enabled: bool
    max_concurrency: int
    current_running: int
    utilization: float  # 0.0 - 1.0
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None

## Configuration

### Dispatcher Configuration File

```yaml
# ~/.necrocode/config/dispatcher.yaml
dispatcher:
  poll_interval: 5  # 秒
  scheduling_policy: priority
  max_global_concurrency: 10
  heartbeat_timeout: 60  # 秒
  retry_max_attempts: 3
  retry_backoff_base: 2.0

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

### DispatcherConfig Class

```python
@dataclass
class DispatcherConfig:
    """Dispatcher設定"""
    poll_interval: int = 5
    scheduling_policy: SchedulingPolicy = SchedulingPolicy.PRIORITY
    max_global_concurrency: int = 10
    heartbeat_timeout: int = 60
    retry_max_attempts: int = 3
    retry_backoff_base: float = 2.0
    graceful_shutdown_timeout: int = 300
    
    # Agent Pool設定
    agent_pools: List[AgentPool] = field(default_factory=list)
    skill_mapping: Dict[str, List[str]] = field(default_factory=dict)

## Error Handling

### Exception Hierarchy

```python
class DispatcherError(Exception):
    """Base exception for Dispatcher"""
    pass

class TaskAssignmentError(DispatcherError):
    """Task assignment failed"""
    pass

class SlotAllocationError(DispatcherError):
    """Slot allocation failed"""
    pass

class RunnerLaunchError(DispatcherError):
    """Runner launch failed"""
    pass

class PoolNotFoundError(DispatcherError):
    """Agent pool not found"""
    pass

class DeadlockDetectedError(DispatcherError):
    """Deadlock detected"""
    pass
```

## Testing Strategy

### Unit Tests

- `test_dispatcher_core.py`: DispatcherCoreのメインループ
- `test_task_monitor.py`: TaskMonitorのポーリング
- `test_task_queue.py`: TaskQueueの優先度管理
- `test_scheduler.py`: Schedulerのスケジューリングポリシー
- `test_agent_pool_manager.py`: AgentPoolManagerのプール管理
- `test_runner_launcher.py`: RunnerLauncherの起動機能
- `test_runner_monitor.py`: RunnerMonitorの監視機能
- `test_metrics_collector.py`: MetricsCollectorのメトリクス収集

### Integration Tests

- `test_dispatcher_integration.py`: 実際のタスク割当の統合テスト
- `test_concurrent_dispatch.py`: 並行実行の統合テスト
- `test_graceful_shutdown.py`: グレースフルシャットダウンのテスト

### Performance Tests

- `test_dispatcher_performance.py`: スケジューリング性能の測定
- `test_high_load.py`: 高負荷時の動作テスト

## Dependencies

```python
# requirements.txt
pyyaml>=6.0
docker>=6.1.0
kubernetes>=27.2.0
prometheus-client>=0.17.0  # Prometheusメトリクス
```

## Future Enhancements

1. **動的スケーリング**: 負荷に応じてAgent Poolを自動スケール
2. **予測スケジューリング**: 機械学習によるタスク実行時間の予測
3. **コスト最適化**: クラウドリソースのコスト最適化
4. **マルチリージョン**: 複数リージョンのAgent Poolをサポート
5. **WebUI**: Dispatcherの状態を可視化するWebダッシュボード

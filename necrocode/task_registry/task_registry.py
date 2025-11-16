"""
TaskRegistry - Main API for task management

Provides the primary interface for managing tasksets, task states, events, and synchronization.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import (
    Task,
    TaskState,
    Taskset,
    TaskEvent,
    EventType,
    Artifact,
    ArtifactType,
)
from .config import RegistryConfig
from .task_store import TaskStore
from .event_store import EventStore
from .lock_manager import LockManager
from .kiro_sync import KiroSyncManager, TaskDefinition, SyncResult
from .query_engine import QueryEngine
from .graph_visualizer import GraphVisualizer
from .exceptions import (
    TaskRegistryError,
    TaskNotFoundError,
    TasksetNotFoundError,
    InvalidStateTransitionError,
)


class TaskRegistry:
    """
    TaskRegistry - タスクの状態管理、バージョン管理、イベント履歴を一元管理
    
    Main API for managing tasksets, task states, artifacts, and synchronization with Kiro.
    """
    
    def __init__(self, registry_dir: Optional[Path] = None, config: Optional[RegistryConfig] = None):
        """
        Initialize TaskRegistry
        
        Args:
            registry_dir: レジストリデータの保存ディレクトリ（Noneの場合はconfigから取得）
            config: レジストリ設定（Noneの場合はデフォルト設定を使用）
        """
        # 設定の初期化
        if config is None:
            if registry_dir is not None:
                config = RegistryConfig(registry_dir=Path(registry_dir))
            else:
                config = RegistryConfig()
        elif registry_dir is not None:
            # registry_dirが指定されている場合は優先
            config.registry_dir = Path(registry_dir)
        
        self.config = config
        self.registry_dir = config.registry_dir
        
        # ディレクトリ構造の自動作成
        self.config.ensure_directories()
        
        # コンポーネントの初期化
        self.task_store = TaskStore(config.tasksets_dir)
        self.event_store = EventStore(config.events_dir)
        self.lock_manager = LockManager(config.locks_dir)
        self.kiro_sync = KiroSyncManager(self)
        self.query_engine = QueryEngine(self.task_store)
        self.graph_visualizer = GraphVisualizer()
    
    def create_taskset(
        self,
        spec_name: str,
        tasks: List[TaskDefinition],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Taskset:
        """
        新しいタスクセットを作成
        
        Args:
            spec_name: Spec名
            tasks: タスク定義のリスト
            metadata: タスクセットのメタデータ
            
        Returns:
            作成されたTaskset
            
        Raises:
            TaskRegistryError: タスクセットの作成に失敗した場合
        """
        with self.lock_manager.acquire_lock(
            spec_name,
            timeout=self.config.lock_timeout,
            retry_interval=self.config.lock_retry_interval
        ):
            # 既存のタスクセットがある場合はバージョンをインクリメント
            version = 1
            if self.task_store.taskset_exists(spec_name):
                existing = self.task_store.load_taskset(spec_name)
                version = existing.version + 1
            
            # TaskDefinitionからTaskオブジェクトを作成
            task_objects = []
            for task_def in tasks:
                # 初期状態を決定（依存関係がある場合はBLOCKED、ない場合はREADY）
                initial_state = TaskState.BLOCKED if task_def.dependencies else TaskState.READY
                if task_def.is_completed:
                    initial_state = TaskState.DONE
                
                task = Task(
                    id=task_def.id,
                    title=task_def.title,
                    description=task_def.description,
                    state=initial_state,
                    dependencies=task_def.dependencies,
                    is_optional=task_def.is_optional,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                task_objects.append(task)
            
            # タスクセットを作成
            now = datetime.now()
            taskset = Taskset(
                spec_name=spec_name,
                version=version,
                created_at=now,
                updated_at=now,
                tasks=task_objects,
                metadata=metadata or {}
            )
            
            # 保存
            self.task_store.save_taskset(taskset)
            
            # イベントを記録
            for task in task_objects:
                event = TaskEvent(
                    event_type=EventType.TASK_CREATED,
                    spec_name=spec_name,
                    task_id=task.id,
                    timestamp=now,
                    details={"title": task.title, "state": task.state.value}
                )
                self.event_store.record_event(event)
            
            return taskset
    
    def get_taskset(self, spec_name: str) -> Taskset:
        """
        タスクセットを取得
        
        Args:
            spec_name: Spec名
            
        Returns:
            Taskset
            
        Raises:
            TasksetNotFoundError: タスクセットが存在しない場合
        """
        return self.task_store.load_taskset(spec_name)
    
    def update_task_state(
        self,
        spec_name: str,
        task_id: str,
        new_state: TaskState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        タスクの状態を更新
        
        Args:
            spec_name: Spec名
            task_id: タスクID
            new_state: 新しい状態
            metadata: 状態遷移に関するメタデータ（assigned_slot, reserved_branch, runner_id等）
            
        Raises:
            TaskNotFoundError: タスクが存在しない場合
            InvalidStateTransitionError: 無効な状態遷移の場合
        """
        with self.lock_manager.acquire_lock(
            spec_name,
            timeout=self.config.lock_timeout,
            retry_interval=self.config.lock_retry_interval
        ):
            # タスクセットを取得
            taskset = self.task_store.load_taskset(spec_name)
            
            # タスクを検索
            task = None
            for t in taskset.tasks:
                if t.id == task_id:
                    task = t
                    break
            
            if task is None:
                raise TaskNotFoundError(task_id, spec_name)
            
            # 状態遷移の妥当性を検証
            old_state = task.state
            self._validate_state_transition(task, new_state)
            
            # 状態を更新
            task.state = new_state
            task.updated_at = datetime.now()
            
            # Running状態への遷移時にメタデータを記録
            if new_state == TaskState.RUNNING and metadata:
                if "assigned_slot" in metadata:
                    task.assigned_slot = metadata["assigned_slot"]
                if "reserved_branch" in metadata:
                    task.reserved_branch = metadata["reserved_branch"]
                if "runner_id" in metadata:
                    task.runner_id = metadata["runner_id"]
            
            # Done状態への遷移時に依存タスクのBlocked状態を解除
            if new_state == TaskState.DONE:
                self._unblock_dependent_tasks(taskset, task_id)
            
            # バージョンをインクリメント
            taskset.version += 1
            taskset.updated_at = datetime.now()
            
            # タスクセットを保存
            self.task_store.save_taskset(taskset)
            
            # イベントを記録
            event_type = self._get_event_type_for_state(new_state)
            event = TaskEvent(
                event_type=event_type,
                spec_name=spec_name,
                task_id=task_id,
                timestamp=datetime.now(),
                details={
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                    **(metadata or {})
                }
            )
            self.event_store.record_event(event)
    
    def _validate_state_transition(self, task: Task, new_state: TaskState) -> None:
        """
        状態遷移の妥当性を検証
        
        Args:
            task: タスク
            new_state: 新しい状態
            
        Raises:
            InvalidStateTransitionError: 無効な状態遷移の場合
        """
        old_state = task.state
        
        # 同じ状態への遷移は許可
        if old_state == new_state:
            return
        
        # 有効な状態遷移のルール
        valid_transitions = {
            TaskState.READY: {TaskState.RUNNING, TaskState.BLOCKED, TaskState.DONE},  # DONEへの直接遷移を許可
            TaskState.RUNNING: {TaskState.DONE, TaskState.FAILED, TaskState.READY},
            TaskState.BLOCKED: {TaskState.READY, TaskState.RUNNING},  # RUNNINGへの直接遷移を許可
            TaskState.DONE: {TaskState.READY},  # 再実行のため
            TaskState.FAILED: {TaskState.READY, TaskState.RUNNING},  # リトライのため
        }
        
        if new_state not in valid_transitions.get(old_state, set()):
            raise InvalidStateTransitionError(
                task.id,
                old_state.value,
                new_state.value
            )
    
    def _unblock_dependent_tasks(self, taskset: Taskset, completed_task_id: str) -> None:
        """
        完了したタスクに依存するタスクのBlocked状態を解除
        
        Args:
            taskset: タスクセット
            completed_task_id: 完了したタスクのID
        """
        for task in taskset.tasks:
            if task.state == TaskState.BLOCKED and completed_task_id in task.dependencies:
                # すべての依存タスクが完了しているか確認
                all_deps_done = True
                for dep_id in task.dependencies:
                    dep_task = None
                    for t in taskset.tasks:
                        if t.id == dep_id:
                            dep_task = t
                            break
                    
                    if dep_task is None or dep_task.state != TaskState.DONE:
                        all_deps_done = False
                        break
                
                # すべての依存タスクが完了していればREADYに遷移
                if all_deps_done:
                    task.state = TaskState.READY
                    task.updated_at = datetime.now()
    
    def _get_event_type_for_state(self, state: TaskState) -> EventType:
        """
        状態に対応するイベントタイプを取得
        
        Args:
            state: タスクの状態
            
        Returns:
            EventType
        """
        state_to_event = {
            TaskState.READY: EventType.TASK_READY,
            TaskState.RUNNING: EventType.TASK_ASSIGNED,
            TaskState.DONE: EventType.TASK_COMPLETED,
            TaskState.FAILED: EventType.TASK_FAILED,
        }
        return state_to_event.get(state, EventType.TASK_UPDATED)
    
    def get_ready_tasks(
        self,
        spec_name: str,
        required_skill: Optional[str] = None
    ) -> List[Task]:
        """
        実行可能なタスクを取得
        
        Args:
            spec_name: Spec名
            required_skill: 必要スキルでフィルタリング（Noneの場合はすべて）
            
        Returns:
            Ready状態のタスクのリスト
        """
        # QueryEngineを使用してReady状態のタスクを取得
        ready_tasks = self.query_engine.filter_by_state(spec_name, TaskState.READY)
        
        # required_skillでフィルタリング
        if required_skill is not None:
            ready_tasks = [
                task for task in ready_tasks
                if task.required_skill == required_skill
            ]
        
        # 依存関係を考慮した実行順序でソート
        # 依存関係が少ないタスクを優先
        ready_tasks = sorted(ready_tasks, key=lambda t: len(t.dependencies))
        
        return ready_tasks
    
    def add_artifact(
        self,
        spec_name: str,
        task_id: str,
        artifact_type: ArtifactType,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        成果物の参照を追加
        
        Args:
            spec_name: Spec名
            task_id: タスクID
            artifact_type: 成果物のタイプ
            uri: 成果物のURI
            metadata: 成果物のメタデータ（サイズ、作成日時等）
            
        Raises:
            TaskNotFoundError: タスクが存在しない場合
        """
        with self.lock_manager.acquire_lock(
            spec_name,
            timeout=self.config.lock_timeout,
            retry_interval=self.config.lock_retry_interval
        ):
            # タスクセットを取得
            taskset = self.task_store.load_taskset(spec_name)
            
            # タスクを検索
            task = None
            for t in taskset.tasks:
                if t.id == task_id:
                    task = t
                    break
            
            if task is None:
                raise TaskNotFoundError(task_id, spec_name)
            
            # 成果物を作成
            artifact = Artifact(
                type=artifact_type,
                uri=uri,
                size_bytes=metadata.get("size_bytes") if metadata else None,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            # タスクに成果物を追加
            task.artifacts.append(artifact)
            task.updated_at = datetime.now()
            
            # バージョンをインクリメント
            taskset.version += 1
            taskset.updated_at = datetime.now()
            
            # タスクセットを保存
            self.task_store.save_taskset(taskset)
            
            # イベントを記録
            event = TaskEvent(
                event_type=EventType.TASK_UPDATED,
                spec_name=spec_name,
                task_id=task_id,
                timestamp=datetime.now(),
                details={
                    "action": "artifact_added",
                    "artifact_type": artifact_type.value,
                    "uri": uri
                }
            )
            self.event_store.record_event(event)
    
    def sync_with_kiro(self, spec_name: str, tasks_md_path: Optional[Path] = None) -> SyncResult:
        """
        Kiro tasks.mdと同期
        
        Args:
            spec_name: Spec名
            tasks_md_path: tasks.mdファイルのパス（Noneの場合は自動検出）
            
        Returns:
            同期結果
        """
        # tasks_md_pathが指定されていない場合は自動検出
        if tasks_md_path is None:
            # デフォルトのKiro specパスを試す
            tasks_md_path = Path(f".kiro/specs/{spec_name}/tasks.md")
            
            if not tasks_md_path.exists():
                # カレントディレクトリからの相対パスも試す
                alt_path = Path.cwd() / ".kiro" / "specs" / spec_name / "tasks.md"
                if alt_path.exists():
                    tasks_md_path = alt_path
        
        # tasks.mdから同期
        return self.kiro_sync.sync_from_kiro(spec_name, tasks_md_path)
    
    def export_dependency_graph_dot(self, spec_name: str) -> str:
        """
        依存関係グラフをDOT形式で出力
        
        Args:
            spec_name: Spec名
            
        Returns:
            DOT形式の文字列
            
        Raises:
            TasksetNotFoundError: タスクセットが存在しない場合
        """
        taskset = self.get_taskset(spec_name)
        return self.graph_visualizer.generate_dot(taskset)
    
    def export_dependency_graph_mermaid(self, spec_name: str) -> str:
        """
        依存関係グラフをMermaid形式で出力
        
        Args:
            spec_name: Spec名
            
        Returns:
            Mermaid形式の文字列
            
        Raises:
            TasksetNotFoundError: タスクセットが存在しない場合
        """
        taskset = self.get_taskset(spec_name)
        return self.graph_visualizer.generate_mermaid(taskset)
    
    def get_execution_order(self, spec_name: str) -> List[List[str]]:
        """
        依存関係を考慮した実行順序を取得
        
        Args:
            spec_name: Spec名
            
        Returns:
            実行順序のリスト（各要素は並列実行可能なタスクIDのリスト）
            
        Raises:
            TasksetNotFoundError: タスクセットが存在しない場合
        """
        taskset = self.get_taskset(spec_name)
        return self.graph_visualizer.get_execution_order(taskset)

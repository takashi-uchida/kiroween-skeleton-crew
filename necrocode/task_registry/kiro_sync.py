"""
KiroSyncManager - Synchronization with Kiro tasks.md files

Handles bidirectional sync between Task Registry and Kiro's .kiro/specs/{spec-name}/tasks.md
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from .models import Task, TaskState, Taskset
from .exceptions import SyncError, CircularDependencyError


@dataclass
class TaskDefinition:
    """tasks.mdから抽出されたタスク定義"""
    id: str
    title: str
    description: str
    is_optional: bool
    is_completed: bool
    dependencies: List[str]
    parent_id: Optional[str] = None
    line_number: int = 0

    _ALIASES = {
        "completed": "is_completed",
        "optional": "is_optional",
        "parent": "parent_id",
        "line": "line_number",
    }

    def __getitem__(self, key: str):
        """dict互換アクセスを許可"""
        attr = self._ALIASES.get(key, key)
        return getattr(self, attr)


@dataclass
class SyncResult:
    """同期結果"""
    success: bool
    tasks_added: List[str]
    tasks_updated: List[str]
    tasks_removed: List[str]
    errors: List[str]
    
    def __str__(self) -> str:
        """文字列表現"""
        lines = [
            f"Sync {'succeeded' if self.success else 'failed'}",
            f"  Added: {len(self.tasks_added)}",
            f"  Updated: {len(self.tasks_updated)}",
            f"  Removed: {len(self.tasks_removed)}",
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for error in self.errors:
                lines.append(f"    - {error}")
        return "\n".join(lines)


class KiroSyncManager:
    """Kiro tasks.mdとの同期管理"""
    
    # 正規表現パターン
    TASK_PATTERN = re.compile(
        r'^(\s*)- \[([ x\-])\](\*)?\s+(\d+(?:\.\d+)*)\.?\s+(.+)$',
        re.MULTILINE
    )
    REQUIREMENTS_PATTERN = re.compile(
        r'_Requirements?:\s*([\d\.,\s]+)_',
        re.IGNORECASE
    )
    
    def __init__(self, registry):
        """
        Initialize KiroSyncManager
        
        Args:
            registry: TaskRegistry instance
        """
        self.registry = registry
    
    def parse_tasks_md(self, tasks_md_path: Path) -> List[TaskDefinition]:
        """
        tasks.mdを解析してタスク定義を抽出
        
        Args:
            tasks_md_path: tasks.mdファイルのパス
            
        Returns:
            抽出されたタスク定義のリスト
            
        Raises:
            SyncError: ファイルの読み込みまたは解析に失敗した場合
        """
        if not tasks_md_path.exists():
            raise SyncError(f"tasks.md not found: {tasks_md_path}")
        
        try:
            with open(tasks_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise SyncError(f"Failed to read tasks.md: {e}") from e
        
        return self._parse_content(content)
    
    def _parse_content(self, content: str) -> List[TaskDefinition]:
        """
        tasks.mdの内容を解析
        
        Args:
            content: tasks.mdの内容
            
        Returns:
            タスク定義のリスト
        """
        tasks = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = self.TASK_PATTERN.match(line)
            
            if not match:
                i += 1
                continue
            
            indent, checkbox, optional_mark, task_id, title = match.groups()
            
            # インデントレベルを計算（スペース2つまたはタブ1つで1レベル）
            indent_level = len(indent.replace('\t', '  ')) // 2
            
            # チェックボックスの状態
            is_completed = checkbox.lower() == 'x'
            
            # オプショナルマーク
            is_optional = optional_mark == '*'
            
            # 親タスクの判定
            parent_id = None
            if indent_level > 0:
                # サブタスクの場合、親タスクを探す
                parent_id = self._find_parent_task(tasks, task_id, indent_level)
            
            # タスクの説明と依存関係を抽出
            description_lines = []
            dependencies = []
            
            # 次の行から説明を収集
            j = i + 1
            while j < len(lines):
                desc_line = lines[j]
                
                # 次のタスクに到達したら終了
                if self.TASK_PATTERN.match(desc_line):
                    break
                
                # 空行はスキップ
                stripped = desc_line.strip()
                if not stripped:
                    j += 1
                    continue
                
                # 説明の箇条書き（インデントされた行）
                if stripped.startswith('-') and not stripped.startswith('- ['):
                    description_lines.append(stripped[1:].strip())
                    
                    # 依存関係を抽出
                    req_match = self.REQUIREMENTS_PATTERN.search(stripped)
                    if req_match:
                        dependencies = self._parse_dependencies(req_match.group(1))
                
                j += 1
            
            description = '\n'.join(description_lines) if description_lines else title
            
            task_def = TaskDefinition(
                id=task_id,
                title=title.strip(),
                description=description,
                is_optional=is_optional,
                is_completed=is_completed,
                dependencies=dependencies,
                parent_id=parent_id,
                line_number=i + 1
            )
            
            tasks.append(task_def)
            i += 1
        
        return tasks
    
    def _find_parent_task(
        self,
        tasks: List[TaskDefinition],
        task_id: str,
        indent_level: int
    ) -> Optional[str]:
        """
        サブタスクの親タスクを見つける
        
        Args:
            tasks: これまでに解析されたタスクのリスト
            task_id: 現在のタスクID（例: "1.2"）
            indent_level: インデントレベル
            
        Returns:
            親タスクのID、見つからない場合はNone
        """
        # タスクIDから親を推測（例: "1.2" -> "1"）
        parts = task_id.split('.')
        if len(parts) > 1:
            parent_id = '.'.join(parts[:-1])
            # 親タスクが存在するか確認
            for task in reversed(tasks):
                if task.id == parent_id:
                    return parent_id
        
        return None
    
    def _parse_dependencies(self, deps_str: str) -> List[str]:
        """
        依存関係文字列を解析
        
        Args:
            deps_str: "1.1, 2.3, 3.4" のような文字列
            
        Returns:
            依存タスクIDのリスト
        """
        dependencies = []
        for dep in deps_str.split(','):
            dep = dep.strip()
            if dep:
                dependencies.append(dep)
        return dependencies
    
    def extract_dependencies(self, task_text: str) -> List[str]:
        """
        タスクテキストから依存関係を抽出
        
        Args:
            task_text: タスクの説明テキスト
            
        Returns:
            依存タスクIDのリスト
        """
        match = self.REQUIREMENTS_PATTERN.search(task_text)
        if match:
            return self._parse_dependencies(match.group(1))
        return []
    
    def build_dependency_graph(
        self,
        tasks: List[TaskDefinition]
    ) -> Dict[str, List[str]]:
        """
        依存関係グラフを構築
        
        Args:
            tasks: タスク定義のリスト
            
        Returns:
            タスクIDをキー、依存タスクIDのリストを値とする辞書
        """
        graph = {}
        for task in tasks:
            graph[task.id] = task.dependencies.copy()
        return graph
    
    def verify_no_circular_dependencies(
        self,
        tasks: List[TaskDefinition]
    ) -> None:
        """
        循環参照がないことを検証
        
        Args:
            tasks: タスク定義のリスト
            
        Raises:
            CircularDependencyError: 循環参照が検出された場合
        """
        graph = self.build_dependency_graph(tasks)
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str, path: List[str]) -> Optional[List[str]]:
            """DFSで循環を検出"""
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)
            
            for dep in graph.get(task_id, []):
                if dep not in visited:
                    cycle = has_cycle(dep, path.copy())
                    if cycle:
                        return cycle
                elif dep in rec_stack:
                    # 循環を検出
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
            
            rec_stack.remove(task_id)
            return None
        
        for task_id in graph:
            if task_id not in visited:
                cycle = has_cycle(task_id, [])
                if cycle:
                    cycle_str = ' -> '.join(cycle)
                    raise CircularDependencyError(
                        f"Circular dependency detected: {cycle_str}"
                    )
    
    def sync_from_kiro(self, spec_name: str, tasks_md_path: Path) -> SyncResult:
        """
        tasks.mdからTask Registryへ同期
        
        Args:
            spec_name: Spec名
            tasks_md_path: tasks.mdファイルのパス
            
        Returns:
            同期結果
        """
        result = SyncResult(
            success=False,
            tasks_added=[],
            tasks_updated=[],
            tasks_removed=[],
            errors=[]
        )
        
        try:
            # tasks.mdを解析
            task_defs = self.parse_tasks_md(tasks_md_path)
            
            # 循環参照をチェック
            self.verify_no_circular_dependencies(task_defs)
            
            # 既存のタスクセットを取得（存在しない場合は新規作成）
            try:
                taskset = self.registry.task_store.load_taskset(spec_name)
                existing_task_ids = {task.id for task in taskset.tasks}
            except Exception:
                # 新規タスクセット
                taskset = Taskset(
                    spec_name=spec_name,
                    version=1,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tasks=[],
                    metadata={"kiro_spec_path": str(tasks_md_path)}
                )
                existing_task_ids = set()
            
            # 新しいタスクリスト
            new_tasks = []
            new_task_ids = set()
            
            for task_def in task_defs:
                new_task_ids.add(task_def.id)
                
                # 既存タスクを探す
                existing_task = None
                for task in taskset.tasks:
                    if task.id == task_def.id:
                        existing_task = task
                        break
                
                if existing_task:
                    # 既存タスクを更新
                    updated = False
                    
                    # タイトルの更新
                    if existing_task.title != task_def.title:
                        existing_task.title = task_def.title
                        updated = True
                    
                    # 説明の更新
                    if existing_task.description != task_def.description:
                        existing_task.description = task_def.description
                        updated = True
                    
                    # 状態の更新（チェックボックスから）
                    new_state = TaskState.DONE if task_def.is_completed else TaskState.READY
                    if existing_task.state != new_state:
                        existing_task.state = new_state
                        updated = True
                    
                    # オプショナルフラグの更新
                    if existing_task.is_optional != task_def.is_optional:
                        existing_task.is_optional = task_def.is_optional
                        updated = True
                    
                    # 依存関係の更新
                    if set(existing_task.dependencies) != set(task_def.dependencies):
                        existing_task.dependencies = task_def.dependencies
                        updated = True
                    
                    if updated:
                        existing_task.updated_at = datetime.now()
                        result.tasks_updated.append(task_def.id)
                    
                    new_tasks.append(existing_task)
                else:
                    # 新規タスクを作成
                    new_task = Task(
                        id=task_def.id,
                        title=task_def.title,
                        description=task_def.description,
                        state=TaskState.DONE if task_def.is_completed else TaskState.READY,
                        dependencies=task_def.dependencies,
                        is_optional=task_def.is_optional,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    new_tasks.append(new_task)
                    result.tasks_added.append(task_def.id)
            
            # 削除されたタスクを検出
            removed_ids = existing_task_ids - new_task_ids
            result.tasks_removed.extend(removed_ids)
            
            # タスクセットを更新
            taskset.tasks = new_tasks
            taskset.version += 1
            taskset.updated_at = datetime.now()
            
            # 保存
            self.registry.task_store.save_taskset(taskset)
            
            result.success = True
            
        except CircularDependencyError as e:
            result.errors.append(str(e))
        except SyncError as e:
            result.errors.append(str(e))
        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")
        
        return result
    
    def sync_to_kiro(self, spec_name: str, tasks_md_path: Path) -> SyncResult:
        """
        Task Registryからtasks.mdへ同期
        
        Args:
            spec_name: Spec名
            tasks_md_path: tasks.mdファイルのパス
            
        Returns:
            同期結果
        """
        result = SyncResult(
            success=False,
            tasks_added=[],
            tasks_updated=[],
            tasks_removed=[],
            errors=[]
        )
        
        try:
            # タスクセットを取得
            taskset = self.registry.task_store.load_taskset(spec_name)
            
            # タスクの状態マップを作成
            task_states = {task.id: task.state for task in taskset.tasks}
            
            # tasks.mdを更新
            updated_count = self.update_tasks_md(tasks_md_path, task_states)
            
            if updated_count > 0:
                result.tasks_updated = [
                    task_id for task_id, state in task_states.items()
                    if state == TaskState.DONE
                ]
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Failed to sync to Kiro: {e}")
        
        return result
    
    def update_tasks_md(
        self,
        tasks_md_path: Path,
        task_states: Dict[str, TaskState]
    ) -> int:
        """
        tasks.mdのチェックボックスを更新
        
        Args:
            tasks_md_path: tasks.mdファイルのパス
            task_states: タスクIDと状態のマップ
            
        Returns:
            更新されたタスクの数
            
        Raises:
            SyncError: ファイルの読み書きに失敗した場合
        """
        if not tasks_md_path.exists():
            raise SyncError(f"tasks.md not found: {tasks_md_path}")
        
        try:
            with open(tasks_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise SyncError(f"Failed to read tasks.md: {e}") from e
        
        updated_count = 0
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            match = self.TASK_PATTERN.match(line)
            if match:
                indent, checkbox, optional_mark, task_id, title = match.groups()
                
                # 状態を取得
                if task_id in task_states:
                    state = task_states[task_id]
                    
                    # チェックボックスを更新
                    if state == TaskState.DONE and checkbox != 'x':
                        new_checkbox = 'x'
                        updated_count += 1
                    elif state == TaskState.RUNNING and checkbox != '-':
                        new_checkbox = '-'
                        updated_count += 1
                    elif state in (TaskState.READY, TaskState.BLOCKED) and checkbox != ' ':
                        new_checkbox = ' '
                        updated_count += 1
                    else:
                        new_checkbox = checkbox
                    
                    # 行を再構築
                    optional_str = '*' if optional_mark else ''
                    new_line = f"{indent}- [{new_checkbox}]{optional_str} {task_id}. {title}"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # ファイルに書き戻す
        if updated_count > 0:
            try:
                new_content = '\n'.join(new_lines)
                with open(tasks_md_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                raise SyncError(f"Failed to write tasks.md: {e}") from e
        
        return updated_count

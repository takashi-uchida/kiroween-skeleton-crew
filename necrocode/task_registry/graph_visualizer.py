"""
Graph Visualizer - Dependency graph visualization

Provides functionality to visualize task dependency graphs in DOT and Mermaid formats.
"""

from typing import List, Set
from .models import Task, Taskset, TaskState


class GraphVisualizer:
    """
    依存関係グラフの可視化
    
    Generates dependency graphs in DOT and Mermaid formats for visualization.
    """
    
    def __init__(self):
        """Initialize GraphVisualizer"""
        pass
    
    def generate_dot(self, taskset: Taskset) -> str:
        """
        依存関係グラフをDOT形式で出力
        
        Args:
            taskset: タスクセット
            
        Returns:
            DOT形式の文字列
        """
        lines = []
        lines.append("digraph TaskDependencies {")
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")
        
        # ノードの定義
        for task in taskset.tasks:
            # 状態に応じた色を設定
            color = self._get_node_color_dot(task.state)
            style = "filled,rounded"
            
            # オプショナルタスクは点線で表示
            if task.is_optional:
                style = "dashed,rounded"
            
            # ラベルを作成
            label = self._escape_dot_label(f"{task.id}: {task.title}")
            
            lines.append(
                f'    "{task.id}" [label="{label}", '
                f'fillcolor="{color}", style="{style}"];'
            )
        
        lines.append("")
        
        # エッジの定義（依存関係）
        for task in taskset.tasks:
            for dep_id in task.dependencies:
                lines.append(f'    "{dep_id}" -> "{task.id}";')
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def generate_mermaid(self, taskset: Taskset) -> str:
        """
        依存関係グラフをMermaid形式で出力
        
        Args:
            taskset: タスクセット
            
        Returns:
            Mermaid形式の文字列
        """
        lines = []
        lines.append("graph TD")
        
        # ノードの定義
        for task in taskset.tasks:
            # ノードIDをサニタイズ（Mermaidでは特殊文字を避ける）
            node_id = self._sanitize_mermaid_id(task.id)
            
            # ラベルを作成
            label = f"{task.id}: {task.title}"
            
            # 状態に応じたスタイルクラスを設定
            style_class = self._get_node_class_mermaid(task.state)
            
            # オプショナルタスクの場合は括弧を変更
            if task.is_optional:
                lines.append(f'    {node_id}["{label}"]')
                lines.append(f'    class {node_id} optional')
            else:
                lines.append(f'    {node_id}["{label}"]')
                lines.append(f'    class {node_id} {style_class}')
        
        lines.append("")
        
        # エッジの定義（依存関係）
        for task in taskset.tasks:
            node_id = self._sanitize_mermaid_id(task.id)
            for dep_id in task.dependencies:
                dep_node_id = self._sanitize_mermaid_id(dep_id)
                lines.append(f'    {dep_node_id} --> {node_id}')
        
        lines.append("")
        
        # スタイルクラスの定義
        lines.append("    classDef ready fill:#90EE90,stroke:#333,stroke-width:2px")
        lines.append("    classDef running fill:#FFD700,stroke:#333,stroke-width:2px")
        lines.append("    classDef blocked fill:#D3D3D3,stroke:#333,stroke-width:2px")
        lines.append("    classDef done fill:#87CEEB,stroke:#333,stroke-width:2px")
        lines.append("    classDef failed fill:#FF6B6B,stroke:#333,stroke-width:2px")
        lines.append("    classDef optional fill:#FFF,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5")
        
        return "\n".join(lines)
    
    def _get_node_color_dot(self, state: TaskState) -> str:
        """
        タスクの状態に応じたDOT形式の色を取得
        
        Args:
            state: タスクの状態
            
        Returns:
            色の名前または16進数カラーコード
        """
        color_map = {
            TaskState.READY: "lightgreen",
            TaskState.RUNNING: "gold",
            TaskState.BLOCKED: "lightgray",
            TaskState.DONE: "lightblue",
            TaskState.FAILED: "lightcoral",
        }
        return color_map.get(state, "white")
    
    def _get_node_class_mermaid(self, state: TaskState) -> str:
        """
        タスクの状態に応じたMermaid形式のクラス名を取得
        
        Args:
            state: タスクの状態
            
        Returns:
            クラス名
        """
        class_map = {
            TaskState.READY: "ready",
            TaskState.RUNNING: "running",
            TaskState.BLOCKED: "blocked",
            TaskState.DONE: "done",
            TaskState.FAILED: "failed",
        }
        return class_map.get(state, "ready")
    
    def _escape_dot_label(self, label: str) -> str:
        """
        DOT形式のラベルをエスケープ
        
        Args:
            label: ラベル文字列
            
        Returns:
            エスケープされたラベル
        """
        # ダブルクォートとバックスラッシュをエスケープ
        label = label.replace("\\", "\\\\")
        label = label.replace('"', '\\"')
        return label
    
    def _sanitize_mermaid_id(self, task_id: str) -> str:
        """
        MermaidのノードIDをサニタイズ
        
        Args:
            task_id: タスクID
            
        Returns:
            サニタイズされたID
        """
        # ドットやその他の特殊文字をアンダースコアに置換
        sanitized = task_id.replace(".", "_")
        sanitized = sanitized.replace("-", "_")
        return f"task_{sanitized}"
    
    def get_execution_order(self, taskset: Taskset) -> List[List[str]]:
        """
        依存関係を考慮した実行順序を計算（トポロジカルソート）
        
        Args:
            taskset: タスクセット
            
        Returns:
            実行順序のリスト（各要素は並列実行可能なタスクIDのリスト）
        """
        # タスクIDからTaskオブジェクトへのマップを作成
        task_map = {task.id: task for task in taskset.tasks}
        
        # 各タスクの入次数を計算
        in_degree = {task.id: len(task.dependencies) for task in taskset.tasks}
        
        # 実行順序を格納するリスト
        execution_order = []
        
        # 処理済みタスクのセット
        processed: Set[str] = set()
        
        while len(processed) < len(taskset.tasks):
            # 入次数が0のタスク（依存関係が解決されたタスク）を取得
            ready_tasks = [
                task_id for task_id, degree in in_degree.items()
                if degree == 0 and task_id not in processed
            ]
            
            if not ready_tasks:
                # 循環依存がある場合
                remaining = [tid for tid in task_map.keys() if tid not in processed]
                if remaining:
                    # 残りのタスクを強制的に追加（循環依存を示す）
                    execution_order.append(remaining)
                    processed.update(remaining)
                break
            
            # 現在のレベルのタスクを追加
            execution_order.append(ready_tasks)
            processed.update(ready_tasks)
            
            # 処理したタスクに依存するタスクの入次数を減らす
            for task_id in ready_tasks:
                for task in taskset.tasks:
                    if task_id in task.dependencies:
                        in_degree[task.id] -= 1
        
        return execution_order

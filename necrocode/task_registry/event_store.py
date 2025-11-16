"""
EventStore implementation for Task Registry
Handles event logging, searching, and log rotation
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json
import os
import shutil

from .models import TaskEvent, EventType
from .exceptions import TaskRegistryError


class EventStore:
    """イベント履歴の記録"""
    
    def __init__(self, events_dir: Path):
        """
        Initialize EventStore
        
        Args:
            events_dir: イベントログの保存ディレクトリ
        """
        self.events_dir = Path(events_dir)
        self.events_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_event_file_path(self, spec_name: str) -> Path:
        """
        Get the event log file path for a spec
        
        Args:
            spec_name: Spec名
            
        Returns:
            イベントログファイルのパス
        """
        spec_dir = self.events_dir / spec_name
        spec_dir.mkdir(parents=True, exist_ok=True)
        return spec_dir / "events.jsonl"
    
    def record_event(self, event: TaskEvent) -> None:
        """
        イベントを記録
        
        Args:
            event: 記録するイベント
            
        Raises:
            TaskRegistryError: イベント記録に失敗した場合
        """
        try:
            event_file = self._get_event_file_path(event.spec_name)
            
            # JSON Lines形式で追記
            with open(event_file, 'a', encoding='utf-8') as f:
                f.write(event.to_jsonl() + '\n')
                
        except Exception as e:
            raise TaskRegistryError(
                f"Failed to record event for spec '{event.spec_name}': {e}"
            ) from e
    
    def get_events_by_task(
        self, 
        spec_name: str, 
        task_id: str
    ) -> List[TaskEvent]:
        """
        特定タスクのイベントを取得
        
        Args:
            spec_name: Spec名
            task_id: タスクID
            
        Returns:
            タスクに関連するイベントのリスト
        """
        event_file = self._get_event_file_path(spec_name)
        
        if not event_file.exists():
            return []
        
        events = []
        try:
            with open(event_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = TaskEvent.from_jsonl(line)
                        if event.task_id == task_id:
                            events.append(event)
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        # 破損したログ行をスキップ
                        continue
                        
        except Exception as e:
            raise TaskRegistryError(
                f"Failed to read events for spec '{spec_name}': {e}"
            ) from e
        
        return events
    
    def get_events_by_timerange(
        self,
        spec_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[TaskEvent]:
        """
        期間内のイベントを取得
        
        Args:
            spec_name: Spec名
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            期間内のイベントのリスト
        """
        event_file = self._get_event_file_path(spec_name)
        
        if not event_file.exists():
            return []
        
        events = []
        try:
            with open(event_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = TaskEvent.from_jsonl(line)
                        if start_time <= event.timestamp <= end_time:
                            events.append(event)
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        # 破損したログ行をスキップ
                        continue
                        
        except Exception as e:
            raise TaskRegistryError(
                f"Failed to read events for spec '{spec_name}': {e}"
            ) from e
        
        return events
    
    def rotate_logs(self, max_size_mb: int = 100) -> None:
        """
        ログファイルをローテーション
        
        Args:
            max_size_mb: 最大ファイルサイズ（MB）
            
        Raises:
            TaskRegistryError: ローテーションに失敗した場合
        """
        max_size_bytes = max_size_mb * 1024 * 1024
        
        try:
            # すべてのspecディレクトリを走査
            for spec_dir in self.events_dir.iterdir():
                if not spec_dir.is_dir():
                    continue
                
                event_file = spec_dir / "events.jsonl"
                if not event_file.exists():
                    continue
                
                # ファイルサイズをチェック
                file_size = event_file.stat().st_size
                if file_size < max_size_bytes:
                    continue
                
                # ローテーション番号を決定
                rotation_num = 1
                while True:
                    rotated_file = spec_dir / f"events.jsonl.{rotation_num}"
                    if not rotated_file.exists():
                        break
                    rotation_num += 1
                
                # ファイルをローテーション
                shutil.move(str(event_file), str(rotated_file))
                
                # 新しい空のログファイルを作成
                event_file.touch()
                
        except Exception as e:
            raise TaskRegistryError(
                f"Failed to rotate logs: {e}"
            ) from e
    
    def get_all_events(self, spec_name: str) -> List[TaskEvent]:
        """
        特定specのすべてのイベントを取得
        
        Args:
            spec_name: Spec名
            
        Returns:
            すべてのイベントのリスト
        """
        event_file = self._get_event_file_path(spec_name)
        
        if not event_file.exists():
            return []
        
        events = []
        try:
            with open(event_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = TaskEvent.from_jsonl(line)
                        events.append(event)
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        # 破損したログ行をスキップ
                        continue
                        
        except Exception as e:
            raise TaskRegistryError(
                f"Failed to read events for spec '{spec_name}': {e}"
            ) from e
        
        return events
    
    def clear_events(self, spec_name: str) -> None:
        """
        特定specのイベントログをクリア（テスト用）
        
        Args:
            spec_name: Spec名
        """
        event_file = self._get_event_file_path(spec_name)
        if event_file.exists():
            event_file.unlink()

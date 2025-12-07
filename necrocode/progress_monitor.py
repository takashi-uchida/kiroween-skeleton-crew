"""リアルタイム進捗表示"""
from typing import Dict, List
from datetime import datetime


class ProgressMonitor:
    """タスク実行の進捗を表示"""
    
    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed = 0
        self.failed = 0
        self.running = set()
        self.start_time = datetime.now()
        self.task_times = {}
    
    def start_task(self, task_id: str, title: str):
        """タスク開始"""
        self.running.add(task_id)
        self.task_times[task_id] = {"start": datetime.now(), "title": title}
        self._display()
    
    def complete_task(self, task_id: str, success: bool = True):
        """タスク完了"""
        if task_id in self.running:
            self.running.remove(task_id)
        
        if task_id in self.task_times:
            self.task_times[task_id]["end"] = datetime.now()
            duration = (self.task_times[task_id]["end"] - self.task_times[task_id]["start"]).total_seconds()
            self.task_times[task_id]["duration"] = duration
        
        if success:
            self.completed += 1
        else:
            self.failed += 1
        
        self._display()
    
    def _display(self):
        """進捗を表示"""
        progress = (self.completed + self.failed) / self.total_tasks * 100
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{'='*50}")
        print(f"進捗: {bar} {progress:.0f}% ({self.completed + self.failed}/{self.total_tasks})")
        print(f"完了: {self.completed} | 失敗: {self.failed} | 実行中: {len(self.running)}")
        print(f"経過時間: {elapsed:.1f}秒")
        
        if self.running:
            print(f"\n実行中:")
            for task_id in self.running:
                if task_id in self.task_times:
                    title = self.task_times[task_id]["title"]
                    print(f"  ⚙ Task {task_id}: {title}")
        
        print(f"{'='*50}\n")
    
    def summary(self):
        """最終サマリーを表示"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{'='*50}")
        print(f"実行完了")
        print(f"{'='*50}")
        print(f"総タスク数: {self.total_tasks}")
        print(f"成功: {self.completed}")
        print(f"失敗: {self.failed}")
        print(f"総実行時間: {total_time:.1f}秒")
        
        if self.task_times:
            print(f"\nタスク別実行時間:")
            for task_id, info in self.task_times.items():
                if "duration" in info:
                    print(f"  Task {task_id}: {info['duration']:.1f}秒 - {info['title']}")
        
        print(f"{'='*50}\n")

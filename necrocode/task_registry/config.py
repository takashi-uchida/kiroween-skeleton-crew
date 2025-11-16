"""
Configuration for Task Registry
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegistryConfig:
    """Task Registry設定"""
    registry_dir: Path = Path.home() / ".necrocode" / "registry"
    lock_timeout: float = 30.0
    lock_retry_interval: float = 0.01
    event_log_max_size_mb: int = 100
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    
    def __post_init__(self):
        """設定の検証と初期化"""
        # Pathオブジェクトに変換
        if isinstance(self.registry_dir, str):
            self.registry_dir = Path(self.registry_dir)
        
        # 値の検証
        if self.lock_timeout <= 0:
            raise ValueError("lock_timeout must be positive")
        
        if self.lock_retry_interval <= 0:
            raise ValueError("lock_retry_interval must be positive")
        
        if self.event_log_max_size_mb <= 0:
            raise ValueError("event_log_max_size_mb must be positive")
        
        if self.backup_interval_hours <= 0:
            raise ValueError("backup_interval_hours must be positive")
    
    @property
    def tasksets_dir(self) -> Path:
        """タスクセット保存ディレクトリ"""
        return self.registry_dir / "tasksets"
    
    @property
    def events_dir(self) -> Path:
        """イベントログ保存ディレクトリ"""
        return self.registry_dir / "events"
    
    @property
    def locks_dir(self) -> Path:
        """ロックファイル保存ディレクトリ"""
        return self.registry_dir / "locks"
    
    @property
    def backups_dir(self) -> Path:
        """バックアップ保存ディレクトリ"""
        return self.registry_dir / "backups"
    
    def ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.tasksets_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        if self.backup_enabled:
            self.backups_dir.mkdir(parents=True, exist_ok=True)

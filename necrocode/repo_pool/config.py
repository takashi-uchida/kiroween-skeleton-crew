"""Configuration for Repo Pool Manager."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import yaml
import os
from datetime import datetime

from .exceptions import PoolManagerError


class ConfigValidationError(PoolManagerError):
    """Configuration validation error."""
    pass


@dataclass
class CleanupOptions:
    """Cleanup options for a pool."""
    fetch_on_allocate: bool = True
    clean_on_release: bool = True
    warmup_enabled: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CleanupOptions":
        """Create from dictionary."""
        return cls(
            fetch_on_allocate=data.get("fetch_on_allocate", True),
            clean_on_release=data.get("clean_on_release", True),
            warmup_enabled=data.get("warmup_enabled", False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fetch_on_allocate": self.fetch_on_allocate,
            "clean_on_release": self.clean_on_release,
            "warmup_enabled": self.warmup_enabled
        }


@dataclass
class PoolDefinition:
    """Pool definition from configuration."""
    repo_name: str
    repo_url: str
    num_slots: int = 2
    cleanup_options: CleanupOptions = field(default_factory=CleanupOptions)
    
    @classmethod
    def from_dict(cls, repo_name: str, data: Dict[str, Any]) -> "PoolDefinition":
        """Create from dictionary."""
        cleanup_data = data.get("cleanup_options", {})
        cleanup_options = CleanupOptions.from_dict(cleanup_data)
        
        return cls(
            repo_name=repo_name,
            repo_url=data["repo_url"],
            num_slots=data.get("num_slots", 2),
            cleanup_options=cleanup_options
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repo_url": self.repo_url,
            "num_slots": self.num_slots,
            "cleanup_options": self.cleanup_options.to_dict()
        }


@dataclass
class PoolConfig:
    """Pool configuration."""
    workspaces_dir: Path = Path.home() / ".necrocode" / "workspaces"
    config_file: Path = Path.home() / ".necrocode" / "config" / "pools.yaml"
    default_num_slots: int = 2
    lock_timeout: float = 30.0
    cleanup_timeout: float = 60.0
    stale_lock_hours: int = 24
    enable_metrics: bool = True
    
    # Pool definitions loaded from YAML
    pools: Dict[str, PoolDefinition] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure paths are Path objects."""
        if not isinstance(self.workspaces_dir, Path):
            self.workspaces_dir = Path(self.workspaces_dir)
        if not isinstance(self.config_file, Path):
            self.config_file = Path(self.config_file)
    
    @classmethod
    def load_from_file(cls, config_file: Optional[Path] = None) -> "PoolConfig":
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to configuration file (optional)
            
        Returns:
            PoolConfig instance with loaded settings
            
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        if config_file is None:
            config_file = Path.home() / ".necrocode" / "config" / "pools.yaml"
        
        config = cls(config_file=config_file)
        
        # If config file doesn't exist, return default config
        if not config_file.exists():
            return config
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return config
            
            # Load defaults section
            defaults = data.get("defaults", {})
            if defaults:
                config._apply_defaults(defaults)
            
            # Load pools section
            pools_data = data.get("pools", {})
            if pools_data:
                config._load_pools(pools_data)
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Failed to load configuration: {e}")
    
    def _apply_defaults(self, defaults: Dict[str, Any]) -> None:
        """Apply default settings from configuration."""
        if "num_slots" in defaults:
            self.default_num_slots = int(defaults["num_slots"])
        if "lock_timeout" in defaults:
            self.lock_timeout = float(defaults["lock_timeout"])
        if "cleanup_timeout" in defaults:
            self.cleanup_timeout = float(defaults["cleanup_timeout"])
        if "stale_lock_hours" in defaults:
            self.stale_lock_hours = int(defaults["stale_lock_hours"])
        if "enable_metrics" in defaults:
            self.enable_metrics = bool(defaults["enable_metrics"])
    
    def _load_pools(self, pools_data: Dict[str, Any]) -> None:
        """
        Load pool definitions from configuration.
        
        Args:
            pools_data: Dictionary of pool configurations
            
        Raises:
            ConfigValidationError: If pool configuration is invalid
        """
        for repo_name, pool_data in pools_data.items():
            try:
                # Validate required fields
                if not isinstance(pool_data, dict):
                    raise ConfigValidationError(
                        f"Pool '{repo_name}' configuration must be a dictionary"
                    )
                
                if "repo_url" not in pool_data:
                    raise ConfigValidationError(
                        f"Pool '{repo_name}' missing required field 'repo_url'"
                    )
                
                # Apply default num_slots if not specified
                if "num_slots" not in pool_data:
                    pool_data["num_slots"] = self.default_num_slots
                
                # Create pool definition
                pool_def = PoolDefinition.from_dict(repo_name, pool_data)
                self.pools[repo_name] = pool_def
                
            except Exception as e:
                raise ConfigValidationError(
                    f"Failed to load pool '{repo_name}': {e}"
                )
    
    def validate(self) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Validate numeric ranges
        if self.default_num_slots < 1:
            raise ConfigValidationError("default_num_slots must be at least 1")
        
        if self.lock_timeout <= 0:
            raise ConfigValidationError("lock_timeout must be positive")
        
        if self.cleanup_timeout <= 0:
            raise ConfigValidationError("cleanup_timeout must be positive")
        
        if self.stale_lock_hours < 0:
            raise ConfigValidationError("stale_lock_hours must be non-negative")
        
        # Validate pool definitions
        for repo_name, pool_def in self.pools.items():
            if pool_def.num_slots < 1:
                raise ConfigValidationError(
                    f"Pool '{repo_name}' num_slots must be at least 1"
                )
            
            if not pool_def.repo_url:
                raise ConfigValidationError(
                    f"Pool '{repo_name}' repo_url cannot be empty"
                )
    
    def save_to_file(self, config_file: Optional[Path] = None) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        if config_file is None:
            config_file = self.config_file
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build configuration dictionary
        config_data = {
            "defaults": {
                "num_slots": self.default_num_slots,
                "lock_timeout": self.lock_timeout,
                "cleanup_timeout": self.cleanup_timeout,
                "stale_lock_hours": self.stale_lock_hours,
                "enable_metrics": self.enable_metrics
            },
            "pools": {
                repo_name: pool_def.to_dict()
                for repo_name, pool_def in self.pools.items()
            }
        }
        
        # Write to file
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    
    def get_pool_definition(self, repo_name: str) -> Optional[PoolDefinition]:
        """
        Get pool definition by name.
        
        Args:
            repo_name: Repository name
            
        Returns:
            PoolDefinition if found, None otherwise
        """
        return self.pools.get(repo_name)
    
    def add_pool_definition(self, pool_def: PoolDefinition) -> None:
        """
        Add or update pool definition.
        
        Args:
            pool_def: Pool definition to add
        """
        self.pools[pool_def.repo_name] = pool_def
    
    def remove_pool_definition(self, repo_name: str) -> bool:
        """
        Remove pool definition.
        
        Args:
            repo_name: Repository name
            
        Returns:
            True if removed, False if not found
        """
        if repo_name in self.pools:
            del self.pools[repo_name]
            return True
        return False
    
    def get_file_mtime(self) -> Optional[float]:
        """
        Get modification time of configuration file.
        
        Returns:
            Modification timestamp or None if file doesn't exist
        """
        if self.config_file.exists():
            return os.path.getmtime(self.config_file)
        return None
    
    def has_changed(self, last_mtime: Optional[float]) -> bool:
        """
        Check if configuration file has changed since last check.
        
        Args:
            last_mtime: Last known modification time
            
        Returns:
            True if file has changed or was created
        """
        current_mtime = self.get_file_mtime()
        
        # File was created
        if last_mtime is None and current_mtime is not None:
            return True
        
        # File was deleted
        if last_mtime is not None and current_mtime is None:
            return False
        
        # File was modified
        if last_mtime is not None and current_mtime is not None:
            return current_mtime > last_mtime
        
        return False
    
    def reload(self) -> "PoolConfig":
        """
        Reload configuration from file.
        
        Returns:
            New PoolConfig instance with reloaded settings
            
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        return PoolConfig.load_from_file(self.config_file)


class ConfigWatcher:
    """
    Watches configuration file for changes and triggers reload.
    """
    
    def __init__(self, config: PoolConfig, on_change: Optional[Callable[[PoolConfig], None]] = None):
        """
        Initialize configuration watcher.
        
        Args:
            config: Initial configuration
            on_change: Callback function called when configuration changes
        """
        self.config = config
        self.on_change = on_change
        self.last_mtime = config.get_file_mtime()
    
    def check_and_reload(self) -> Optional[PoolConfig]:
        """
        Check if configuration has changed and reload if necessary.
        
        Returns:
            New PoolConfig if changed, None otherwise
            
        Raises:
            ConfigValidationError: If new configuration is invalid
        """
        if self.config.has_changed(self.last_mtime):
            try:
                # Reload configuration
                new_config = self.config.reload()
                new_config.validate()
                
                # Update tracking
                self.config = new_config
                self.last_mtime = new_config.get_file_mtime()
                
                # Trigger callback
                if self.on_change:
                    self.on_change(new_config)
                
                return new_config
                
            except Exception as e:
                # Log error but don't crash - keep using old config
                raise ConfigValidationError(f"Failed to reload configuration: {e}")
        
        return None
    
    def get_current_config(self) -> PoolConfig:
        """
        Get current configuration.
        
        Returns:
            Current PoolConfig instance
        """
        return self.config

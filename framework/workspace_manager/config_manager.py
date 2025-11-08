"""Configuration management for workspace system.

This module provides configuration loading, validation, and default
configuration generation for the workspace management system.
"""

import json
from pathlib import Path
from typing import Optional

from .models import WorkspaceConfig


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages workspace configuration loading and validation."""
    
    DEFAULT_CONFIG_PATH = Path(".kiro/workspace-config.json")
    
    @staticmethod
    def get_default_config() -> WorkspaceConfig:
        """Get default workspace configuration.
        
        Returns:
            WorkspaceConfig with default values
        """
        return WorkspaceConfig(
            base_path=Path("."),
            state_file=Path(".kiro/workspace-state.json"),
            gitignore_path=Path(".gitignore"),
            auto_push=True,
            auto_pr=False,
        )
    
    @staticmethod
    def validate_config(config: WorkspaceConfig) -> None:
        """Validate workspace configuration.
        
        Args:
            config: WorkspaceConfig to validate
            
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Validate base_path
        if not isinstance(config.base_path, Path):
            raise ConfigValidationError(
                f"base_path must be a Path object, got {type(config.base_path)}"
            )
        
        # Validate state_file
        if not isinstance(config.state_file, Path):
            raise ConfigValidationError(
                f"state_file must be a Path object, got {type(config.state_file)}"
            )
        
        # Validate gitignore_path
        if not isinstance(config.gitignore_path, Path):
            raise ConfigValidationError(
                f"gitignore_path must be a Path object, got {type(config.gitignore_path)}"
            )
        
        # Validate boolean flags
        if not isinstance(config.auto_push, bool):
            raise ConfigValidationError(
                f"auto_push must be a boolean, got {type(config.auto_push)}"
            )
        
        if not isinstance(config.auto_pr, bool):
            raise ConfigValidationError(
                f"auto_pr must be a boolean, got {type(config.auto_pr)}"
            )
        
        # Validate that state_file parent directory can be created
        state_parent = config.state_file.parent
        if not state_parent.exists():
            try:
                state_parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigValidationError(
                    f"Cannot create state file directory {state_parent}: {str(e)}"
                ) from e
    
    @staticmethod
    def create_default_config_file(
        config_path: Optional[Path] = None
    ) -> Path:
        """Create default configuration file.
        
        Args:
            config_path: Path where to create config file.
                        Defaults to .kiro/workspace-config.json
        
        Returns:
            Path to the created configuration file
            
        Raises:
            IOError: If file creation fails
        """
        if config_path is None:
            config_path = ConfigManager.DEFAULT_CONFIG_PATH
        
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get default config and convert to dict
        default_config = ConfigManager.get_default_config()
        config_dict = default_config.to_dict()
        
        # Write to file with pretty formatting
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return config_path

    
    @staticmethod
    def load_config(config_path: Optional[Path] = None) -> WorkspaceConfig:
        """Load workspace configuration from file with fallback to defaults.
        
        Attempts to load configuration from the specified path. If the file
        doesn't exist or is invalid, falls back to default configuration.
        
        Args:
            config_path: Path to configuration file.
                        Defaults to .kiro/workspace-config.json
        
        Returns:
            WorkspaceConfig instance loaded from file or defaults
            
        Example:
            >>> config = ConfigManager.load_config()
            >>> print(config.base_path)
            .
            
            >>> config = ConfigManager.load_config(Path("custom-config.json"))
            >>> print(config.auto_push)
            True
        """
        if config_path is None:
            config_path = ConfigManager.DEFAULT_CONFIG_PATH
        
        # If config file doesn't exist, return defaults
        if not config_path.exists():
            return ConfigManager.get_default_config()
        
        # Try to load from file
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            
            # Create config from dict
            config = WorkspaceConfig.from_dict(config_dict)
            
            # Validate the loaded config
            ConfigManager.validate_config(config)
            
            return config
            
        except json.JSONDecodeError as e:
            # Invalid JSON, fall back to defaults
            print(
                f"Warning: Invalid JSON in config file {config_path}: {str(e)}. "
                f"Using default configuration."
            )
            return ConfigManager.get_default_config()
            
        except (KeyError, ValueError, ConfigValidationError) as e:
            # Invalid config structure, fall back to defaults
            print(
                f"Warning: Invalid configuration in {config_path}: {str(e)}. "
                f"Using default configuration."
            )
            return ConfigManager.get_default_config()
        
        except Exception as e:
            # Unexpected error, fall back to defaults
            print(
                f"Warning: Error loading config from {config_path}: {str(e)}. "
                f"Using default configuration."
            )
            return ConfigManager.get_default_config()
    
    @staticmethod
    def save_config(
        config: WorkspaceConfig,
        config_path: Optional[Path] = None
    ) -> None:
        """Save workspace configuration to file.
        
        Args:
            config: WorkspaceConfig to save
            config_path: Path where to save config file.
                        Defaults to .kiro/workspace-config.json
        
        Raises:
            ConfigValidationError: If configuration is invalid
            IOError: If file write fails
        """
        if config_path is None:
            config_path = ConfigManager.DEFAULT_CONFIG_PATH
        
        # Validate before saving
        ConfigManager.validate_config(config)
        
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        config_dict = config.to_dict()
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)

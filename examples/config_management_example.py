"""
Example: Configuration Management

This example demonstrates:
1. Loading configuration from YAML file
2. Validating configuration
3. Auto-initializing pools from configuration
4. Dynamic configuration reload
5. Configuration watcher for automatic updates
"""

import logging
import time
from pathlib import Path
from necrocode.repo_pool.config import PoolConfig, ConfigWatcher, ConfigValidationError
from necrocode.repo_pool.pool_manager import PoolManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_load_config():
    """Example 1: Load configuration from YAML file"""
    print("\n" + "="*60)
    print("Example 1: Load Configuration from YAML")
    print("="*60)
    
    config_file = Path("examples/pools_example.yaml")
    
    try:
        # Load configuration
        config = PoolConfig.load_from_file(config_file)
        
        print(f"\nLoaded configuration from: {config_file}")
        print(f"Default num_slots: {config.default_num_slots}")
        print(f"Lock timeout: {config.lock_timeout}s")
        print(f"Cleanup timeout: {config.cleanup_timeout}s")
        print(f"Stale lock hours: {config.stale_lock_hours}")
        
        print(f"\nConfigured pools: {len(config.pools)}")
        for repo_name, pool_def in config.pools.items():
            print(f"  - {repo_name}:")
            print(f"      URL: {pool_def.repo_url}")
            print(f"      Slots: {pool_def.num_slots}")
            print(f"      Fetch on allocate: {pool_def.cleanup_options.fetch_on_allocate}")
            print(f"      Clean on release: {pool_def.cleanup_options.clean_on_release}")
            print(f"      Warmup enabled: {pool_def.cleanup_options.warmup_enabled}")
        
        # Validate configuration
        config.validate()
        print("\n✓ Configuration is valid")
        
    except ConfigValidationError as e:
        print(f"\n✗ Configuration validation failed: {e}")
    except Exception as e:
        print(f"\n✗ Failed to load configuration: {e}")


def example_2_create_manager_from_config():
    """Example 2: Create PoolManager from configuration file"""
    print("\n" + "="*60)
    print("Example 2: Create PoolManager from Configuration")
    print("="*60)
    
    config_file = Path("examples/pools_example.yaml")
    
    try:
        # Create PoolManager from config file (without auto-init)
        manager = PoolManager.from_config_file(config_file, auto_init_pools=False)
        
        print(f"\n✓ PoolManager created from configuration")
        print(f"Workspaces directory: {manager.workspaces_dir}")
        print(f"Configured pools: {len(manager.config.pools)}")
        
        # Note: We don't actually initialize pools in this example
        # to avoid cloning real repositories
        print("\nNote: Pools not initialized to avoid cloning repositories")
        print("In production, set auto_init_pools=True to initialize automatically")
        
    except Exception as e:
        print(f"\n✗ Failed to create PoolManager: {e}")


def example_3_save_config():
    """Example 3: Save configuration to file"""
    print("\n" + "="*60)
    print("Example 3: Save Configuration to File")
    print("="*60)
    
    # Create a new configuration
    config = PoolConfig()
    config.default_num_slots = 3
    config.lock_timeout = 45.0
    
    # Add pool definitions
    from necrocode.repo_pool.config import PoolDefinition, CleanupOptions
    
    pool_def = PoolDefinition(
        repo_name="test-repo",
        repo_url="https://github.com/user/test-repo.git",
        num_slots=4,
        cleanup_options=CleanupOptions(
            fetch_on_allocate=True,
            clean_on_release=False,
            warmup_enabled=True
        )
    )
    config.add_pool_definition(pool_def)
    
    # Save to file
    output_file = Path("examples/generated_config.yaml")
    config.save_to_file(output_file)
    
    print(f"\n✓ Configuration saved to: {output_file}")
    print("\nGenerated configuration:")
    with open(output_file, 'r') as f:
        print(f.read())


def example_4_config_watcher():
    """Example 4: Watch configuration for changes"""
    print("\n" + "="*60)
    print("Example 4: Configuration Watcher")
    print("="*60)
    
    config_file = Path("examples/pools_example.yaml")
    
    try:
        # Load initial configuration
        config = PoolConfig.load_from_file(config_file)
        
        # Define callback for configuration changes
        def on_config_change(new_config: PoolConfig):
            print(f"\n🔄 Configuration changed!")
            print(f"   New default_num_slots: {new_config.default_num_slots}")
            print(f"   Number of pools: {len(new_config.pools)}")
        
        # Create watcher
        watcher = ConfigWatcher(config, on_change=on_config_change)
        
        print(f"\n✓ Watching configuration file: {config_file}")
        print("   (In production, call watcher.check_and_reload() periodically)")
        
        # Simulate checking for changes
        print("\nChecking for changes...")
        result = watcher.check_and_reload()
        if result:
            print("Configuration was reloaded")
        else:
            print("No changes detected")
        
    except Exception as e:
        print(f"\n✗ Failed to setup watcher: {e}")


def example_5_validation():
    """Example 5: Configuration validation"""
    print("\n" + "="*60)
    print("Example 5: Configuration Validation")
    print("="*60)
    
    # Test valid configuration
    print("\nTest 1: Valid configuration")
    config = PoolConfig()
    config.default_num_slots = 2
    config.lock_timeout = 30.0
    try:
        config.validate()
        print("✓ Configuration is valid")
    except ConfigValidationError as e:
        print(f"✗ Validation failed: {e}")
    
    # Test invalid configuration - negative num_slots
    print("\nTest 2: Invalid num_slots (0)")
    config = PoolConfig()
    config.default_num_slots = 0
    try:
        config.validate()
        print("✓ Configuration is valid")
    except ConfigValidationError as e:
        print(f"✓ Validation correctly failed: {e}")
    
    # Test invalid configuration - negative timeout
    print("\nTest 3: Invalid lock_timeout (-5)")
    config = PoolConfig()
    config.lock_timeout = -5.0
    try:
        config.validate()
        print("✓ Configuration is valid")
    except ConfigValidationError as e:
        print(f"✓ Validation correctly failed: {e}")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("Configuration Management Examples")
    print("="*60)
    
    example_1_load_config()
    example_2_create_manager_from_config()
    example_3_save_config()
    example_4_config_watcher()
    example_5_validation()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)


if __name__ == "__main__":
    main()

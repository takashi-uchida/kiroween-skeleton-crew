"""
Example demonstrating PlaybookEngine usage.

This example shows how to:
1. Load a Playbook from a YAML file
2. Use the default Playbook
3. Execute a Playbook with context
4. Handle conditional steps
"""

import tempfile
from pathlib import Path

from necrocode.agent_runner import PlaybookEngine


def example_load_playbook():
    """Example: Load a Playbook from YAML file."""
    print("=== Example: Load Playbook ===\n")
    
    # Create a temporary Playbook file
    playbook_yaml = """
name: Backend Task Playbook
steps:
  - name: Install dependencies
    command: npm install
    timeout_seconds: 300
    retry_count: 2
  
  - name: Run linter
    command: npm run lint
    condition: lint_enabled == true
    fail_fast: false
  
  - name: Run unit tests
    command: npm test
    timeout_seconds: 600
    fail_fast: true
  
  - name: Build project
    command: npm run build
    timeout_seconds: 300
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(playbook_yaml)
        playbook_path = Path(f.name)
    
    try:
        # Load Playbook
        engine = PlaybookEngine()
        playbook = engine.load_playbook(playbook_path)
        
        print(f"Loaded Playbook: {playbook.name}")
        print(f"Number of steps: {len(playbook.steps)}")
        print("\nSteps:")
        for i, step in enumerate(playbook.steps, 1):
            print(f"  {i}. {step.name}")
            print(f"     Command: {step.command}")
            if step.condition:
                print(f"     Condition: {step.condition}")
            print(f"     Timeout: {step.timeout_seconds}s")
            print(f"     Retry: {step.retry_count}")
            print()
    
    finally:
        # Clean up
        playbook_path.unlink()


def example_default_playbook():
    """Example: Use default Playbook."""
    print("\n=== Example: Default Playbook ===\n")
    
    engine = PlaybookEngine()
    playbook = engine.get_default_playbook()
    
    print(f"Default Playbook: {playbook.name}")
    print(f"Number of steps: {len(playbook.steps)}")
    print("\nSteps:")
    for i, step in enumerate(playbook.steps, 1):
        print(f"  {i}. {step.name}")
        if step.condition:
            print(f"     Condition: {step.condition}")
        print()


def example_execute_playbook():
    """Example: Execute a Playbook."""
    print("\n=== Example: Execute Playbook ===\n")
    
    # Create a simple Playbook
    playbook_yaml = """
name: Simple Test Playbook
steps:
  - name: Echo message
    command: echo "Hello from Playbook"
    timeout_seconds: 10
  
  - name: List files
    command: ls -la
    timeout_seconds: 10
  
  - name: Conditional step
    command: echo "This step is skipped"
    condition: skip_this == true
  
  - name: Print working directory
    command: pwd
    timeout_seconds: 10
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(playbook_yaml)
        playbook_path = Path(f.name)
    
    try:
        # Load and execute Playbook
        engine = PlaybookEngine()
        playbook = engine.load_playbook(playbook_path)
        
        # Execution context
        context = {
            "skip_this": False,  # Condition will be false
            "test_enabled": True,
        }
        
        # Execute in current directory
        cwd = Path.cwd()
        
        print(f"Executing Playbook: {playbook.name}")
        print(f"Working directory: {cwd}")
        print(f"Context: {context}\n")
        
        result = engine.execute_playbook(playbook, context, cwd)
        
        print(f"\nPlaybook execution completed: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Total duration: {result.total_duration_seconds:.2f}s")
        print(f"\nStep results:")
        
        for step_result in result.step_results:
            status = "SKIPPED" if step_result.skipped else ("PASS" if step_result.success else "FAIL")
            print(f"  [{status}] {step_result.step_name}")
            if not step_result.skipped:
                print(f"         Duration: {step_result.duration_seconds:.2f}s")
                if step_result.stdout:
                    print(f"         Output: {step_result.stdout.strip()[:100]}")
    
    finally:
        # Clean up
        playbook_path.unlink()


def example_conditional_execution():
    """Example: Conditional step execution."""
    print("\n=== Example: Conditional Execution ===\n")
    
    playbook_yaml = """
name: Conditional Playbook
steps:
  - name: Always runs
    command: echo "This always runs"
  
  - name: Runs when enabled
    command: echo "Feature is enabled"
    condition: feature_enabled == true
  
  - name: Runs when disabled
    command: echo "Feature is disabled"
    condition: feature_enabled == false
  
  - name: Numeric comparison
    command: echo "Count is high"
    condition: count > 5
  
  - name: String comparison
    command: echo "Environment is production"
    condition: env == "production"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(playbook_yaml)
        playbook_path = Path(f.name)
    
    try:
        engine = PlaybookEngine()
        playbook = engine.load_playbook(playbook_path)
        
        # Test with different contexts
        contexts = [
            {
                "feature_enabled": True,
                "count": 10,
                "env": "production"
            },
            {
                "feature_enabled": False,
                "count": 3,
                "env": "development"
            }
        ]
        
        for i, context in enumerate(contexts, 1):
            print(f"\nTest {i} - Context: {context}")
            result = engine.execute_playbook(playbook, context, Path.cwd())
            
            print(f"Steps executed:")
            for step_result in result.step_results:
                if not step_result.skipped:
                    print(f"  ✓ {step_result.step_name}")
                else:
                    print(f"  ⊘ {step_result.step_name} (skipped)")
    
    finally:
        playbook_path.unlink()


def example_load_or_default():
    """Example: Load Playbook with fallback to default."""
    print("\n=== Example: Load or Default ===\n")
    
    engine = PlaybookEngine()
    
    # Try to load non-existent file (will use default)
    print("Attempting to load non-existent Playbook...")
    playbook = engine.load_playbook_or_default(Path("/nonexistent/playbook.yaml"))
    print(f"Result: {playbook.name}")
    print(f"Source: {playbook.metadata.get('source')}\n")
    
    # Load without path (will use default)
    print("Loading without path...")
    playbook = engine.load_playbook_or_default(None)
    print(f"Result: {playbook.name}")
    print(f"Source: {playbook.metadata.get('source')}")


if __name__ == "__main__":
    example_load_playbook()
    example_default_playbook()
    example_execute_playbook()
    example_conditional_execution()
    example_load_or_default()
    
    print("\n=== All examples completed ===")

"""
Test script for graph visualization functionality
"""

from pathlib import Path
import tempfile
import shutil
from necrocode.task_registry import TaskRegistry, TaskDefinition


def test_graph_visualization():
    """Test DOT and Mermaid graph generation"""
    
    # Create temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize TaskRegistry
        registry = TaskRegistry(registry_dir=temp_dir)
        
        # Create sample tasks with dependencies
        tasks = [
            TaskDefinition(
                id="1.1",
                title="Setup database schema",
                description="Create User and Message models",
                dependencies=[],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="1.2",
                title="Implement JWT authentication",
                description="Add login/register endpoints",
                dependencies=["1.1"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="2.1",
                title="Create login UI",
                description="Build login form component",
                dependencies=["1.2"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="2.2",
                title="Create chat interface",
                description="Build chat room component",
                dependencies=["1.1"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="3.1",
                title="Write unit tests",
                description="Test authentication flow",
                dependencies=["1.2", "2.1"],
                is_optional=True,
                is_completed=False
            ),
        ]
        
        # Create taskset
        spec_name = "test-chat-app"
        taskset = registry.create_taskset(spec_name, tasks)
        
        print(f"Created taskset '{spec_name}' with {len(taskset.tasks)} tasks\n")
        
        # Generate DOT format
        print("=" * 60)
        print("DOT Format:")
        print("=" * 60)
        dot_output = registry.export_dependency_graph_dot(spec_name)
        print(dot_output)
        print()
        
        # Generate Mermaid format
        print("=" * 60)
        print("Mermaid Format:")
        print("=" * 60)
        mermaid_output = registry.export_dependency_graph_mermaid(spec_name)
        print(mermaid_output)
        print()
        
        # Get execution order
        print("=" * 60)
        print("Execution Order (Topological Sort):")
        print("=" * 60)
        execution_order = registry.get_execution_order(spec_name)
        for level, task_ids in enumerate(execution_order, 1):
            print(f"Level {level}: {', '.join(task_ids)}")
        print()
        
        # Save outputs to files
        output_dir = Path("graph_outputs")
        output_dir.mkdir(exist_ok=True)
        
        dot_file = output_dir / f"{spec_name}.dot"
        with open(dot_file, "w") as f:
            f.write(dot_output)
        print(f"✓ DOT output saved to: {dot_file}")
        
        mermaid_file = output_dir / f"{spec_name}.mmd"
        with open(mermaid_file, "w") as f:
            f.write(mermaid_output)
        print(f"✓ Mermaid output saved to: {mermaid_file}")
        
        print("\nTest completed successfully!")
        print(f"\nTo visualize the DOT graph, you can use:")
        print(f"  dot -Tpng {dot_file} -o {spec_name}.png")
        print(f"\nTo visualize the Mermaid graph, paste the content into:")
        print(f"  https://mermaid.live/")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_graph_visualization()

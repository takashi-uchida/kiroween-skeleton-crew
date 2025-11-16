"""
Example: Task Registry Graph Visualization

This example demonstrates how to use the graph visualization features
of the Task Registry to visualize task dependencies.
"""

from pathlib import Path
import tempfile
import shutil
from necrocode.task_registry import TaskRegistry, TaskDefinition


def main():
    """Main example function"""
    
    # Create temporary directory for the example
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize TaskRegistry
        print("Initializing Task Registry...")
        registry = TaskRegistry(registry_dir=temp_dir)
        
        # Define sample tasks with dependencies
        print("\nCreating sample taskset...")
        tasks = [
            TaskDefinition(
                id="1.1",
                title="Setup project structure",
                description="Create directory structure and configuration files",
                dependencies=[],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="1.2",
                title="Setup database",
                description="Configure database connection and create schema",
                dependencies=["1.1"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="2.1",
                title="Implement user authentication",
                description="Create login and registration endpoints",
                dependencies=["1.2"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="2.2",
                title="Implement user profile",
                description="Create user profile management endpoints",
                dependencies=["1.2"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="3.1",
                title="Create frontend components",
                description="Build React components for user interface",
                dependencies=["2.1", "2.2"],
                is_optional=False,
                is_completed=False
            ),
            TaskDefinition(
                id="4.1",
                title="Write unit tests",
                description="Create comprehensive unit tests",
                dependencies=["2.1", "2.2"],
                is_optional=True,  # Optional task
                is_completed=False
            ),
        ]
        
        # Create taskset
        spec_name = "example-project"
        taskset = registry.create_taskset(spec_name, tasks)
        print(f"✓ Created taskset '{spec_name}' with {len(taskset.tasks)} tasks")
        
        # Export to DOT format
        print("\n" + "=" * 60)
        print("DOT Format (Graphviz):")
        print("=" * 60)
        dot_output = registry.export_dependency_graph_dot(spec_name)
        print(dot_output)
        
        # Export to Mermaid format
        print("\n" + "=" * 60)
        print("Mermaid Format:")
        print("=" * 60)
        mermaid_output = registry.export_dependency_graph_mermaid(spec_name)
        print(mermaid_output)
        
        # Get execution order
        print("\n" + "=" * 60)
        print("Execution Order (Topological Sort):")
        print("=" * 60)
        execution_order = registry.get_execution_order(spec_name)
        
        for level, task_ids in enumerate(execution_order, 1):
            print(f"\nLevel {level} (can run in parallel):")
            for task_id in task_ids:
                task = next((t for t in taskset.tasks if t.id == task_id), None)
                if task:
                    optional = " [OPTIONAL]" if task.is_optional else ""
                    print(f"  - {task_id}: {task.title}{optional}")
        
        # Save outputs
        output_dir = Path("examples/output")
        output_dir.mkdir(exist_ok=True)
        
        dot_file = output_dir / f"{spec_name}.dot"
        with open(dot_file, "w") as f:
            f.write(dot_output)
        
        mermaid_file = output_dir / f"{spec_name}.mmd"
        with open(mermaid_file, "w") as f:
            f.write(mermaid_output)
        
        print("\n" + "=" * 60)
        print("Files Saved:")
        print("=" * 60)
        print(f"✓ DOT format: {dot_file}")
        print(f"✓ Mermaid format: {mermaid_file}")
        
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("\n1. Visualize DOT graph:")
        print(f"   dot -Tpng {dot_file} -o {spec_name}.png")
        
        print("\n2. Visualize Mermaid graph:")
        print("   - Open https://mermaid.live/")
        print(f"   - Paste content from {mermaid_file}")
        
        print("\n3. Use in documentation:")
        print("   - Include Mermaid diagram in Markdown files")
        print("   - Embed PNG images in documentation")
        
        print("\n✓ Example completed successfully!")
        
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()

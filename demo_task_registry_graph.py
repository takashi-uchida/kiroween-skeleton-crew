"""
Demo: Visualize task-registry dependency graph

This script demonstrates the graph visualization functionality by creating
a taskset from the actual task-registry spec and generating DOT and Mermaid graphs.
"""

from pathlib import Path
import tempfile
import shutil
from necrocode.task_registry import TaskRegistry


def demo_task_registry_graph():
    """Demonstrate graph visualization with task-registry spec"""
    
    # Create temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize TaskRegistry
        registry = TaskRegistry(registry_dir=temp_dir)
        
        # Sync from the actual task-registry tasks.md
        spec_name = "task-registry"
        tasks_md_path = Path(".kiro/specs/task-registry/tasks.md")
        
        if not tasks_md_path.exists():
            print(f"Error: {tasks_md_path} not found")
            return
        
        print(f"Syncing from {tasks_md_path}...")
        sync_result = registry.sync_with_kiro(spec_name, tasks_md_path)
        
        print(f"✓ Sync completed")
        print(f"  - Added: {len(sync_result.tasks_added)}")
        print(f"  - Updated: {len(sync_result.tasks_updated)}")
        print(f"  - Removed: {len(sync_result.tasks_removed)}")
        if sync_result.errors:
            print(f"  - Errors: {len(sync_result.errors)}")
        print()
        
        # Get the taskset
        taskset = registry.get_taskset(spec_name)
        print(f"Taskset '{spec_name}' has {len(taskset.tasks)} tasks\n")
        
        # Generate DOT format
        print("=" * 60)
        print("Generating DOT format...")
        print("=" * 60)
        dot_output = registry.export_dependency_graph_dot(spec_name)
        
        # Generate Mermaid format
        print("Generating Mermaid format...")
        mermaid_output = registry.export_dependency_graph_mermaid(spec_name)
        
        # Get execution order
        print("Calculating execution order...")
        execution_order = registry.get_execution_order(spec_name)
        
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
        
        # Save execution order
        order_file = output_dir / f"{spec_name}_execution_order.txt"
        with open(order_file, "w") as f:
            f.write(f"Execution Order for {spec_name}\n")
            f.write("=" * 60 + "\n\n")
            for level, task_ids in enumerate(execution_order, 1):
                f.write(f"Level {level} (can run in parallel):\n")
                for task_id in task_ids:
                    # Find task details
                    task = next((t for t in taskset.tasks if t.id == task_id), None)
                    if task:
                        f.write(f"  - {task_id}: {task.title}\n")
                f.write("\n")
        print(f"✓ Execution order saved to: {order_file}")
        
        print("\n" + "=" * 60)
        print("Execution Order Summary:")
        print("=" * 60)
        for level, task_ids in enumerate(execution_order, 1):
            print(f"Level {level}: {len(task_ids)} task(s) - {', '.join(task_ids)}")
        
        print("\n" + "=" * 60)
        print("Visualization Instructions:")
        print("=" * 60)
        print(f"\n1. DOT Graph (Graphviz):")
        print(f"   Install Graphviz: brew install graphviz")
        print(f"   Generate PNG: dot -Tpng {dot_file} -o {spec_name}.png")
        print(f"   Generate SVG: dot -Tsvg {dot_file} -o {spec_name}.svg")
        
        print(f"\n2. Mermaid Graph (Online):")
        print(f"   Open: https://mermaid.live/")
        print(f"   Paste content from: {mermaid_file}")
        
        print(f"\n3. Mermaid Graph (CLI):")
        print(f"   Install: npm install -g @mermaid-js/mermaid-cli")
        print(f"   Generate PNG: mmdc -i {mermaid_file} -o {spec_name}.png")
        
        print("\n✓ Demo completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    demo_task_registry_graph()

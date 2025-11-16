"""
Task Context Generator - Creates context files for Kiro to execute tasks
"""
from pathlib import Path
from typing import List
from .task_planner import Task


class TaskContextGenerator:
    """Generates .kiro/current-task.md for Kiro to execute"""
    
    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.kiro_dir = workspace_root / ".kiro"
    
    def generate_context(self, task: Task, completed_tasks: List[Task]) -> str:
        """Generate markdown context for a task"""
        
        # Find dependencies that are completed
        completed_deps = [
            t for t in completed_tasks 
            if t.id in task.dependencies
        ]
        
        context = f"""# Task: {task.title}

## Task ID
{task.id}

## Type
{task.type}

## Description
{task.description}

## Dependencies Completed
"""
        
        if completed_deps:
            for dep in completed_deps:
                context += f"- Task {dep.id}: {dep.title}\n"
        else:
            context += "- None (this task has no dependencies)\n"
        
        context += f"""
## Files to Create/Modify
"""
        for file in task.files_to_create:
            context += f"- `{file}`\n"
        
        context += f"""
## Acceptance Criteria
"""
        for i, criteria in enumerate(task.acceptance_criteria, 1):
            context += f"{i}. {criteria}\n"
        
        context += f"""
## Technical Context
"""
        for key, value in task.technical_context.items():
            context += f"- **{key}**: {value}\n"
        
        context += """
## Instructions for Kiro

Please implement this task following these steps:

1. Review the acceptance criteria carefully
2. Create/modify the specified files
3. Ensure code follows best practices
4. Add appropriate error handling
5. Include inline comments for complex logic
6. Commit changes with format: `feat(task-{task.id}): {task.title}`

## Related Files

Review these files for context:
"""
        
        # Add file references for dependencies
        for dep in completed_deps:
            for file in dep.files_to_create:
                if Path(self.workspace_root / file).exists():
                    context += f"#[[file:{file}]]\n"
        
        return context
    
    def write_context(self, task: Task, completed_tasks: List[Task] = None):
        """Write task context to .kiro/current-task.md"""
        if completed_tasks is None:
            completed_tasks = []
        
        context = self.generate_context(task, completed_tasks)
        
        context_file = self.kiro_dir / "current-task.md"
        with open(context_file, 'w') as f:
            f.write(context)
        
        print(f"✓ Task context written to {context_file}")
        return context_file
    
    def clear_context(self):
        """Remove current task context"""
        context_file = self.kiro_dir / "current-task.md"
        if context_file.exists():
            context_file.unlink()
            print(f"✓ Cleared task context")

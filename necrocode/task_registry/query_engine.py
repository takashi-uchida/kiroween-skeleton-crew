"""
QueryEngine - Search and filter functionality for tasks

Provides methods to query, filter, and sort tasks from tasksets.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from .models import Task, TaskState, Taskset
from .task_store import TaskStore
from .exceptions import TasksetNotFoundError


class QueryEngine:
    """QueryEngine provides search and filtering capabilities for tasks"""
    
    def __init__(self, task_store: TaskStore):
        """
        Initialize QueryEngine
        
        Args:
            task_store: TaskStore instance for loading tasksets
        """
        self.task_store = task_store
    
    def filter_by_state(
        self,
        spec_name: str,
        state: TaskState
    ) -> List[Task]:
        """
        Filter tasks by state
        
        Args:
            spec_name: Name of the spec/taskset
            state: TaskState to filter by
            
        Returns:
            List of tasks matching the state
            
        Example:
            ready_tasks = engine.filter_by_state("chat-app", TaskState.READY)
        """
        try:
            taskset = self.task_store.load_taskset(spec_name)
        except TasksetNotFoundError:
            return []
        return [task for task in taskset.tasks if task.state == state]
    
    def filter_by_skill(
        self,
        spec_name: str,
        required_skill: str
    ) -> List[Task]:
        """
        Filter tasks by required skill
        
        Args:
            spec_name: Name of the spec/taskset
            required_skill: Skill to filter by (e.g., "backend", "frontend")
            
        Returns:
            List of tasks requiring the specified skill
            
        Example:
            backend_tasks = engine.filter_by_skill("chat-app", "backend")
        """
        try:
            taskset = self.task_store.load_taskset(spec_name)
        except TasksetNotFoundError:
            return []
        return [
            task for task in taskset.tasks
            if task.required_skill == required_skill
        ]
    
    def sort_by_priority(
        self,
        tasks: List[Task],
        descending: bool = True
    ) -> List[Task]:
        """
        Sort tasks by priority
        
        Args:
            tasks: List of tasks to sort
            descending: If True, sort highest priority first (default: True)
            
        Returns:
            Sorted list of tasks
            
        Example:
            sorted_tasks = engine.sort_by_priority(tasks, descending=True)
        """
        return sorted(tasks, key=lambda t: t.priority, reverse=descending)
    
    def query(
        self,
        spec_name: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """
        Execute a complex query with multiple filters, sorting, and pagination
        
        Args:
            spec_name: Name of the spec/taskset
            filters: Dictionary of filter criteria:
                - state: TaskState or str
                - required_skill: str
                - is_optional: bool
                - has_dependencies: bool (True if task has dependencies)
                - runner_id: str
                - assigned_slot: str
            sort_by: Field to sort by ("priority", "created_at", "updated_at", "id")
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            
        Returns:
            List of tasks matching the query
            
        Example:
            # Get first 10 ready backend tasks, sorted by priority
            tasks = engine.query(
                "chat-app",
                filters={"state": "ready", "required_skill": "backend"},
                sort_by="priority",
                limit=10,
                offset=0
            )
        """
        # Load taskset
        try:
            taskset = self.task_store.load_taskset(spec_name)
        except TasksetNotFoundError:
            return []
        results = taskset.tasks.copy()
        
        # Apply filters
        if filters:
            results = self._apply_filters(results, filters)
        
        # Apply sorting
        if sort_by:
            results = self._apply_sorting(results, sort_by)
        
        # Apply pagination
        if offset > 0:
            results = results[offset:]
        
        if limit is not None:
            results = results[:limit]
        
        return results
    
    def _apply_filters(self, tasks: List[Task], filters: Dict[str, Any]) -> List[Task]:
        """
        Apply filter criteria to a list of tasks
        
        Args:
            tasks: List of tasks to filter
            filters: Dictionary of filter criteria
            
        Returns:
            Filtered list of tasks
        """
        results = tasks
        
        # Filter by state
        if "state" in filters:
            state_filter = filters["state"]
            if isinstance(state_filter, str):
                state_filter = TaskState(state_filter)
            results = [t for t in results if t.state == state_filter]
        
        # Filter by required_skill
        if "required_skill" in filters:
            skill = filters["required_skill"]
            results = [t for t in results if t.required_skill == skill]
        
        # Filter by is_optional
        if "is_optional" in filters:
            is_optional = filters["is_optional"]
            results = [t for t in results if t.is_optional == is_optional]
        
        # Filter by has_dependencies
        if "has_dependencies" in filters:
            has_deps = filters["has_dependencies"]
            if has_deps:
                results = [t for t in results if len(t.dependencies) > 0]
            else:
                results = [t for t in results if len(t.dependencies) == 0]
        
        # Filter by runner_id
        if "runner_id" in filters:
            runner_id = filters["runner_id"]
            results = [t for t in results if t.runner_id == runner_id]
        
        # Filter by assigned_slot
        if "assigned_slot" in filters:
            slot = filters["assigned_slot"]
            results = [t for t in results if t.assigned_slot == slot]
        
        return results
    
    def _apply_sorting(self, tasks: List[Task], sort_by: str) -> List[Task]:
        """
        Apply sorting to a list of tasks
        
        Args:
            tasks: List of tasks to sort
            sort_by: Field name to sort by
            
        Returns:
            Sorted list of tasks
        """
        if sort_by == "priority":
            return sorted(tasks, key=lambda t: t.priority, reverse=True)
        elif sort_by == "created_at":
            return sorted(tasks, key=lambda t: t.created_at)
        elif sort_by == "updated_at":
            return sorted(tasks, key=lambda t: t.updated_at)
        elif sort_by == "id":
            return sorted(tasks, key=lambda t: t.id)
        else:
            # Unknown sort field, return as-is
            return tasks

"""
Deadlock detection for task dependencies.

Analyzes task dependency graphs to detect circular dependencies and deadlocks.
"""

import logging
from typing import Dict, List, Set, Optional
from datetime import datetime

from necrocode.task_registry.models import Task, TaskState
from necrocode.dispatcher.exceptions import DeadlockDetectedError

logger = logging.getLogger(__name__)


class DeadlockDetector:
    """
    Detects deadlocks in task dependency graphs.
    
    Analyzes task dependencies to identify circular dependencies that could
    cause deadlocks in task execution.
    """
    
    def __init__(self):
        """Initialize the deadlock detector."""
        self.last_check: Optional[datetime] = None
        self.detected_cycles: List[List[str]] = []
    
    def detect_deadlock(self, tasks: List[Task]) -> List[List[str]]:
        """
        Detect circular dependencies in task list.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            List of cycles, where each cycle is a list of task IDs
            
        Raises:
            DeadlockDetectedError: If a deadlock is detected
        """
        self.last_check = datetime.now()
        self.detected_cycles = []
        
        # Build dependency graph
        graph = self._build_dependency_graph(tasks)
        
        # Detect cycles using DFS
        cycles = self._detect_cycles(graph)
        
        if cycles:
            self.detected_cycles = cycles
            logger.warning(f"Detected {len(cycles)} circular dependencies")
            for i, cycle in enumerate(cycles, 1):
                logger.warning(f"Cycle {i}: {' -> '.join(cycle)} -> {cycle[0]}")
        
        return cycles
    
    def _build_dependency_graph(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Build a dependency graph from tasks.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Dictionary mapping task ID to list of dependency task IDs
        """
        graph: Dict[str, List[str]] = {}
        
        for task in tasks:
            # Only consider tasks that are not completed or failed
            if task.state not in [TaskState.DONE, TaskState.FAILED]:
                graph[task.id] = task.dependencies.copy()
        
        return graph
    
    def _detect_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        Detect cycles in a directed graph using DFS.
        
        Args:
            graph: Dependency graph (task_id -> [dependency_ids])
            
        Returns:
            List of cycles found
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(node: str) -> bool:
            """
            Depth-first search to detect cycles.
            
            Args:
                node: Current node (task ID)
                
            Returns:
                True if a cycle is detected
            """
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # Visit all dependencies
            for dependency in graph.get(node, []):
                if dependency not in visited:
                    if dfs(dependency):
                        return True
                elif dependency in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(dependency)
                    cycle = path[cycle_start:] + [dependency]
                    cycles.append(cycle)
                    logger.debug(f"Cycle detected: {' -> '.join(cycle)}")
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        # Check all nodes
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def check_for_deadlock(
        self,
        tasks: List[Task],
        raise_on_deadlock: bool = False
    ) -> bool:
        """
        Check if there is a deadlock in the task dependencies.
        
        Args:
            tasks: List of tasks to check
            raise_on_deadlock: If True, raise exception on deadlock detection
            
        Returns:
            True if deadlock detected, False otherwise
            
        Raises:
            DeadlockDetectedError: If deadlock detected and raise_on_deadlock is True
        """
        cycles = self.detect_deadlock(tasks)
        
        if cycles and raise_on_deadlock:
            cycle_descriptions = []
            for cycle in cycles:
                cycle_str = " -> ".join(cycle) + f" -> {cycle[0]}"
                cycle_descriptions.append(cycle_str)
            
            error_msg = (
                f"Deadlock detected: {len(cycles)} circular "
                f"{'dependency' if len(cycles) == 1 else 'dependencies'} found.\n"
                + "\n".join(f"  - {desc}" for desc in cycle_descriptions)
            )
            raise DeadlockDetectedError(error_msg)
        
        return len(cycles) > 0
    
    def get_blocked_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Get tasks that are blocked by circular dependencies.
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of tasks involved in circular dependencies
        """
        cycles = self.detect_deadlock(tasks)
        
        if not cycles:
            return []
        
        # Collect all task IDs involved in cycles
        blocked_task_ids: Set[str] = set()
        for cycle in cycles:
            blocked_task_ids.update(cycle)
        
        # Return tasks that are in the blocked set
        return [task for task in tasks if task.id in blocked_task_ids]
    
    def suggest_resolution(self, cycles: List[List[str]]) -> List[str]:
        """
        Suggest resolutions for detected cycles.
        
        Args:
            cycles: List of detected cycles
            
        Returns:
            List of suggested resolution actions
        """
        suggestions = []
        
        for i, cycle in enumerate(cycles, 1):
            suggestions.append(
                f"Cycle {i}: Remove dependency from {cycle[-1]} to {cycle[0]}"
            )
        
        return suggestions
    
    def get_last_check_time(self) -> Optional[datetime]:
        """
        Get the timestamp of the last deadlock check.
        
        Returns:
            Datetime of last check, or None if never checked
        """
        return self.last_check
    
    def get_detected_cycles(self) -> List[List[str]]:
        """
        Get the cycles detected in the last check.
        
        Returns:
            List of cycles from last check
        """
        return self.detected_cycles.copy()

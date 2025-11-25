"""
TaskMonitor - Monitors Task Registry for ready tasks

Polls the Task Registry periodically to retrieve tasks in Ready state
and filters them based on dependency resolution.
"""

import logging
from typing import List, Optional, Set
from pathlib import Path

from necrocode.task_registry import TaskRegistry
from necrocode.task_registry.models import Task, TaskState
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.exceptions import DispatcherError


logger = logging.getLogger(__name__)


class TaskRegistryClient:
    """
    Client for communicating with Task Registry
    
    Provides a simplified interface for the Dispatcher to interact
    with the Task Registry.
    """
    
    def __init__(self, registry_dir: Optional[Path] = None):
        """
        Initialize Task Registry client
        
        Args:
            registry_dir: Path to Task Registry data directory
        """
        self.registry = TaskRegistry(registry_dir=registry_dir)
        logger.info(f"TaskRegistryClient initialized with registry_dir: {registry_dir}")
    
    def get_ready_tasks(self, spec_name: Optional[str] = None) -> List[Task]:
        """
        Get all ready tasks from Task Registry
        
        Args:
            spec_name: Optional spec name to filter tasks. If None, gets tasks from all specs.
            
        Returns:
            List of tasks in Ready state
            
        Raises:
            DispatcherError: If failed to retrieve tasks
        """
        try:
            if spec_name:
                # Get ready tasks for specific spec
                tasks = self.registry.get_ready_tasks(spec_name)
                logger.debug(f"Retrieved {len(tasks)} ready tasks for spec '{spec_name}'")
                return tasks
            else:
                # Get ready tasks from all specs
                all_tasks = []
                tasksets = self.registry.task_store.list_tasksets()
                
                for spec in tasksets:
                    spec_tasks = self.registry.get_ready_tasks(spec)
                    all_tasks.extend(spec_tasks)
                
                logger.debug(f"Retrieved {len(all_tasks)} ready tasks from all specs")
                return all_tasks
                
        except Exception as e:
            logger.error(f"Failed to retrieve ready tasks: {e}")
            raise DispatcherError(f"Failed to retrieve ready tasks: {e}") from e
    
    def get_task(self, spec_name: str, task_id: str) -> Optional[Task]:
        """
        Get a specific task by ID
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            
        Returns:
            Task if found, None otherwise
        """
        try:
            taskset = self.registry.task_store.load_taskset(spec_name)
            if taskset:
                # tasks is a list, so we need to search for the task
                for task in taskset.tasks:
                    if task.id == task_id:
                        return task
            return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id} from spec {spec_name}: {e}")
            return None
    
    def get_task_dependencies(self, spec_name: str, task_id: str) -> List[str]:
        """
        Get dependencies for a specific task
        
        Args:
            spec_name: Spec name
            task_id: Task ID
            
        Returns:
            List of dependency task IDs
        """
        task = self.get_task(spec_name, task_id)
        if task:
            return task.dependencies
        return []


class TaskMonitor:
    """
    Monitors Task Registry for ready tasks
    
    Polls the Task Registry at configured intervals and filters tasks
    based on dependency resolution.
    """
    
    def __init__(self, config: DispatcherConfig):
        """
        Initialize TaskMonitor
        
        Args:
            config: Dispatcher configuration
        """
        self.config = config
        self.task_registry_client = TaskRegistryClient(
            registry_dir=config.task_registry_dir
        )
        logger.info("TaskMonitor initialized")
    
    def poll_ready_tasks(self, spec_name: Optional[str] = None) -> List[Task]:
        """
        Poll Task Registry for ready tasks
        
        Retrieves tasks in Ready state and filters them to ensure
        all dependencies are resolved.
        
        Args:
            spec_name: Optional spec name to filter tasks
            
        Returns:
            List of ready tasks with resolved dependencies
        """
        try:
            # Get ready tasks from Task Registry
            ready_tasks = self.task_registry_client.get_ready_tasks(spec_name)
            
            if not ready_tasks:
                logger.debug("No ready tasks found")
                return []
            
            # Filter tasks to ensure dependencies are resolved
            filtered_tasks = self._filter_tasks(ready_tasks)
            
            logger.info(f"Polled {len(ready_tasks)} ready tasks, "
                       f"{len(filtered_tasks)} have resolved dependencies")
            
            return filtered_tasks
            
        except Exception as e:
            logger.error(f"Error polling ready tasks: {e}")
            return []
    
    def _filter_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Filter tasks to return only those with resolved dependencies
        
        A task's dependencies are considered resolved if all dependent tasks
        are in DONE state. This method verifies this condition by checking
        the actual state of dependency tasks in the Task Registry.
        
        Args:
            tasks: List of tasks to filter
            
        Returns:
            List of tasks with all dependencies resolved
        """
        filtered_tasks = []
        
        for task in tasks:
            if self._are_dependencies_resolved(task):
                filtered_tasks.append(task)
            else:
                logger.debug(f"Task {task.id} has unresolved dependencies: {task.dependencies}")
        
        return filtered_tasks
    
    def _are_dependencies_resolved(self, task: Task) -> bool:
        """
        Check if all dependencies for a task are resolved
        
        Args:
            task: Task to check
            
        Returns:
            True if all dependencies are in DONE state, False otherwise
        """
        # If no dependencies, task is ready
        if not task.dependencies:
            return True
        
        # Extract spec_name from task metadata or use a default approach
        # Tasks should have metadata indicating their spec
        spec_name = task.metadata.get("spec_name")
        if not spec_name:
            # If spec_name is not in metadata, we need to find it
            # This is a fallback - ideally spec_name should be in task metadata
            logger.warning(f"Task {task.id} missing spec_name in metadata")
            return True  # Assume dependencies are resolved if we can't verify
        
        # Check each dependency
        for dep_id in task.dependencies:
            dep_task = self.task_registry_client.get_task(spec_name, dep_id)
            
            if dep_task is None:
                logger.warning(f"Dependency task {dep_id} not found for task {task.id}")
                return False
            
            if dep_task.state != TaskState.DONE:
                logger.debug(f"Dependency {dep_id} is in state {dep_task.state.value}, "
                           f"not DONE")
                return False
        
        # All dependencies are in DONE state
        return True

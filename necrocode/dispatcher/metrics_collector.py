"""
Metrics Collector for the Dispatcher component.

Collects and exports metrics about task queue, running tasks, pool utilization,
and task assignment performance.
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from necrocode.task_registry.models import Task
from necrocode.dispatcher.models import AgentPool


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Metrics Collector for Dispatcher.
    
    Collects and exports metrics including:
    - Queue size
    - Running tasks count
    - Pool utilization
    - Average wait time
    - Task assignment history
    
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._lock = threading.Lock()
        self.metrics: Dict[str, Any] = {}
        
        # Task assignment tracking
        self._assignment_history: List[Dict[str, Any]] = []
        self._task_wait_times: Dict[str, float] = {}  # task_id -> wait_time_seconds
        
        # References to components (set externally)
        self._task_queue = None
        self._agent_pool_manager = None
        self._runner_monitor = None
        self._dispatcher_core = None  # For global concurrency metrics
        
        logger.info("MetricsCollector initialized")
    
    def set_task_queue(self, task_queue) -> None:
        """
        Set reference to TaskQueue for metrics collection.
        
        Args:
            task_queue: TaskQueue instance
        """
        self._task_queue = task_queue
    
    def set_agent_pool_manager(self, agent_pool_manager) -> None:
        """
        Set reference to AgentPoolManager for metrics collection.
        
        Args:
            agent_pool_manager: AgentPoolManager instance
        """
        self._agent_pool_manager = agent_pool_manager
    
    def set_runner_monitor(self, runner_monitor) -> None:
        """
        Set reference to RunnerMonitor for metrics collection.
        
        Args:
            runner_monitor: RunnerMonitor instance
        """
        self._runner_monitor = runner_monitor
    
    def set_dispatcher_core(self, dispatcher_core) -> None:
        """
        Set reference to DispatcherCore for global concurrency metrics.
        
        Args:
            dispatcher_core: DispatcherCore instance
        """
        self._dispatcher_core = dispatcher_core
    
    def collect(self) -> None:
        """
        Collect current metrics snapshot.
        
        Gathers metrics from all components and updates the metrics dictionary.
        
        Requirements: 14.1, 14.2, 14.3, 14.4, 6.5
        """
        with self._lock:
            self.metrics = {
                "queue_size": self._get_queue_size(),
                "running_tasks": self._get_running_tasks_count(),
                "global_running_count": self._get_global_running_count(),
                "max_global_concurrency": self._get_max_global_concurrency(),
                "global_utilization": self._get_global_utilization(),
                "pool_utilization": self._get_pool_utilization(),
                "pool_running_counts": self._get_pool_running_counts(),
                "average_wait_time": self._get_average_wait_time(),
                "timestamp": datetime.now().isoformat(),
                "total_assignments": len(self._assignment_history),
            }
            
            logger.debug(f"Collected metrics: {self.metrics}")
    
    def record_assignment(self, task: Task, pool: AgentPool) -> None:
        """
        Record a task assignment event.
        
        Tracks when a task is assigned to a pool, including wait time calculation.
        
        Args:
            task: Task that was assigned
            pool: AgentPool the task was assigned to
            
        Requirements: 14.5
        """
        with self._lock:
            now = datetime.now()
            
            # Calculate wait time (time from task creation to assignment)
            wait_time = (now - task.created_at).total_seconds()
            self._task_wait_times[task.id] = wait_time
            
            # Record assignment
            assignment_record = {
                "task_id": task.id,
                "pool_name": pool.name,
                "pool_type": pool.type.value,
                "priority": task.priority,
                "wait_time_seconds": wait_time,
                "assigned_at": now.isoformat(),
            }
            
            self._assignment_history.append(assignment_record)
            
            logger.info(
                f"Recorded assignment: task={task.id}, pool={pool.name}, "
                f"wait_time={wait_time:.2f}s"
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get the current metrics snapshot.
        
        Returns:
            Dictionary containing all collected metrics
        """
        with self._lock:
            return self.metrics.copy()
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        Returns:
            Metrics formatted for Prometheus scraping
            
        Requirements: 14.5, 6.5
        """
        with self._lock:
            lines = []
            
            # Queue size
            lines.append("# HELP dispatcher_queue_size Number of tasks in queue")
            lines.append("# TYPE dispatcher_queue_size gauge")
            lines.append(f"dispatcher_queue_size {self.metrics.get('queue_size', 0)}")
            
            # Running tasks (per-pool total)
            lines.append("# HELP dispatcher_running_tasks Number of currently running tasks (per-pool total)")
            lines.append("# TYPE dispatcher_running_tasks gauge")
            lines.append(f"dispatcher_running_tasks {self.metrics.get('running_tasks', 0)}")
            
            # Global running count
            lines.append("# HELP dispatcher_global_running_count Global running task count")
            lines.append("# TYPE dispatcher_global_running_count gauge")
            lines.append(f"dispatcher_global_running_count {self.metrics.get('global_running_count', 0)}")
            
            # Max global concurrency
            lines.append("# HELP dispatcher_max_global_concurrency Maximum global concurrency limit")
            lines.append("# TYPE dispatcher_max_global_concurrency gauge")
            lines.append(f"dispatcher_max_global_concurrency {self.metrics.get('max_global_concurrency', 0)}")
            
            # Global utilization
            lines.append("# HELP dispatcher_global_utilization Global concurrency utilization ratio (0.0-1.0)")
            lines.append("# TYPE dispatcher_global_utilization gauge")
            lines.append(f"dispatcher_global_utilization {self.metrics.get('global_utilization', 0.0)}")
            
            # Average wait time
            lines.append("# HELP dispatcher_average_wait_time_seconds Average task wait time in seconds")
            lines.append("# TYPE dispatcher_average_wait_time_seconds gauge")
            lines.append(f"dispatcher_average_wait_time_seconds {self.metrics.get('average_wait_time', 0.0)}")
            
            # Total assignments
            lines.append("# HELP dispatcher_total_assignments Total number of task assignments")
            lines.append("# TYPE dispatcher_total_assignments counter")
            lines.append(f"dispatcher_total_assignments {self.metrics.get('total_assignments', 0)}")
            
            # Pool utilization (per pool)
            pool_utilization = self.metrics.get('pool_utilization', {})
            if pool_utilization:
                lines.append("# HELP dispatcher_pool_utilization Pool utilization ratio (0.0-1.0)")
                lines.append("# TYPE dispatcher_pool_utilization gauge")
                for pool_name, utilization in pool_utilization.items():
                    lines.append(f'dispatcher_pool_utilization{{pool="{pool_name}"}} {utilization}')
            
            # Pool running counts (per pool)
            pool_running_counts = self.metrics.get('pool_running_counts', {})
            if pool_running_counts:
                lines.append("# HELP dispatcher_pool_running_count Running task count per pool")
                lines.append("# TYPE dispatcher_pool_running_count gauge")
                for pool_name, count in pool_running_counts.items():
                    lines.append(f'dispatcher_pool_running_count{{pool="{pool_name}"}} {count}')
            
            return "\n".join(lines) + "\n"
    
    def _get_queue_size(self) -> int:
        """
        Get the current queue size.
        
        Returns:
            Number of tasks in the queue
            
        Requirements: 14.1
        """
        if self._task_queue is None:
            logger.warning("TaskQueue not set, returning 0 for queue size")
            return 0
        
        return self._task_queue.size()
    
    def _get_running_tasks_count(self) -> int:
        """
        Get the number of currently running tasks.
        
        Returns:
            Number of running tasks across all pools
            
        Requirements: 14.2
        """
        if self._agent_pool_manager is None:
            logger.warning("AgentPoolManager not set, returning 0 for running tasks")
            return 0
        
        total_running = 0
        for pool in self._agent_pool_manager.pools.values():
            total_running += pool.current_running
        
        return total_running
    
    def _get_pool_utilization(self) -> Dict[str, float]:
        """
        Get utilization for all pools.
        
        Returns:
            Dictionary mapping pool name to utilization ratio (0.0-1.0)
            
        Requirements: 14.3
        """
        if self._agent_pool_manager is None:
            logger.warning("AgentPoolManager not set, returning empty pool utilization")
            return {}
        
        utilization = {}
        for pool_name, pool in self._agent_pool_manager.pools.items():
            if pool.max_concurrency > 0:
                utilization[pool_name] = pool.current_running / pool.max_concurrency
            else:
                utilization[pool_name] = 0.0
        
        return utilization
    
    def _get_average_wait_time(self) -> float:
        """
        Get the average wait time for tasks.
        
        Calculates the average time between task creation and assignment
        across all recorded assignments.
        
        Returns:
            Average wait time in seconds
            
        Requirements: 14.4
        """
        if not self._task_wait_times:
            return 0.0
        
        total_wait_time = sum(self._task_wait_times.values())
        return total_wait_time / len(self._task_wait_times)
    
    def _get_global_running_count(self) -> int:
        """
        Get the global running task count.
        
        Returns:
            Number of tasks running across all pools
            
        Requirements: 6.5
        """
        if self._dispatcher_core is None:
            logger.warning("DispatcherCore not set, returning 0 for global running count")
            return 0
        
        return self._dispatcher_core.get_global_running_count()
    
    def _get_max_global_concurrency(self) -> int:
        """
        Get the maximum global concurrency limit.
        
        Returns:
            Maximum number of tasks that can run concurrently
            
        Requirements: 6.5
        """
        if self._dispatcher_core is None:
            logger.warning("DispatcherCore not set, returning 0 for max global concurrency")
            return 0
        
        return self._dispatcher_core.config.max_global_concurrency
    
    def _get_global_utilization(self) -> float:
        """
        Get the global concurrency utilization ratio.
        
        Returns:
            Utilization ratio (0.0-1.0)
            
        Requirements: 6.5
        """
        max_concurrency = self._get_max_global_concurrency()
        if max_concurrency == 0:
            return 0.0
        
        running_count = self._get_global_running_count()
        return running_count / max_concurrency
    
    def _get_pool_running_counts(self) -> Dict[str, int]:
        """
        Get running task counts for all pools.
        
        Returns:
            Dictionary mapping pool name to running task count
            
        Requirements: 6.5
        """
        if self._agent_pool_manager is None:
            logger.warning("AgentPoolManager not set, returning empty pool running counts")
            return {}
        
        counts = {}
        for pool_name, pool in self._agent_pool_manager.pools.items():
            counts[pool_name] = pool.current_running
        
        return counts
    
    def get_assignment_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get task assignment history.
        
        Args:
            limit: Maximum number of recent assignments to return (None for all)
            
        Returns:
            List of assignment records
        """
        with self._lock:
            if limit is None:
                return self._assignment_history.copy()
            else:
                return self._assignment_history[-limit:]
    
    def get_pool_assignment_counts(self) -> Dict[str, int]:
        """
        Get assignment counts per pool.
        
        Returns:
            Dictionary mapping pool name to number of assignments
        """
        with self._lock:
            counts: Dict[str, int] = defaultdict(int)
            for record in self._assignment_history:
                counts[record["pool_name"]] += 1
            return dict(counts)
    
    def get_priority_distribution(self) -> Dict[int, int]:
        """
        Get distribution of task priorities in assignment history.
        
        Returns:
            Dictionary mapping priority level to count
        """
        with self._lock:
            distribution: Dict[int, int] = defaultdict(int)
            for record in self._assignment_history:
                distribution[record["priority"]] += 1
            return dict(distribution)
    
    def reset_metrics(self) -> None:
        """
        Reset all collected metrics and history.
        
        Useful for testing or periodic cleanup.
        """
        with self._lock:
            self.metrics = {}
            self._assignment_history = []
            self._task_wait_times = {}
            logger.info("Metrics reset")

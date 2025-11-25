"""
Dispatcher module for NecroCode.

The Dispatcher is responsible for scheduling and assigning tasks from the Task Registry
to Agent Runners based on skills, resource availability, and scheduling policies.
"""

from necrocode.dispatcher.models import (
    AgentPool,
    PoolType,
    Runner,
    RunnerState,
    RunnerInfo,
    SchedulingPolicy,
    PoolStatus,
)
from necrocode.dispatcher.exceptions import (
    DispatcherError,
    TaskAssignmentError,
    SlotAllocationError,
    RunnerLaunchError,
    PoolNotFoundError,
    DeadlockDetectedError,
)
from necrocode.dispatcher.config import DispatcherConfig
from necrocode.dispatcher.task_monitor import TaskMonitor, TaskRegistryClient
from necrocode.dispatcher.task_queue import TaskQueue
from necrocode.dispatcher.scheduler import Scheduler
from necrocode.dispatcher.agent_pool_manager import AgentPoolManager
from necrocode.dispatcher.runner_launcher import (
    RunnerLauncher,
    TaskContext,
    LocalProcessLauncher,
    DockerLauncher,
    KubernetesLauncher,
)
from necrocode.dispatcher.runner_monitor import RunnerMonitor
from necrocode.dispatcher.metrics_collector import MetricsCollector
from necrocode.dispatcher.retry_manager import RetryManager
from necrocode.dispatcher.deadlock_detector import DeadlockDetector
from necrocode.dispatcher.event_recorder import EventRecorder
from necrocode.dispatcher.dispatcher_core import DispatcherCore

__all__ = [
    "AgentPool",
    "PoolType",
    "Runner",
    "RunnerState",
    "RunnerInfo",
    "SchedulingPolicy",
    "PoolStatus",
    "DispatcherError",
    "TaskAssignmentError",
    "SlotAllocationError",
    "RunnerLaunchError",
    "PoolNotFoundError",
    "DeadlockDetectedError",
    "DispatcherConfig",
    "TaskMonitor",
    "TaskRegistryClient",
    "TaskQueue",
    "Scheduler",
    "AgentPoolManager",
    "RunnerLauncher",
    "TaskContext",
    "LocalProcessLauncher",
    "DockerLauncher",
    "KubernetesLauncher",
    "RunnerMonitor",
    "MetricsCollector",
    "RetryManager",
    "DeadlockDetector",
    "EventRecorder",
    "DispatcherCore",
]

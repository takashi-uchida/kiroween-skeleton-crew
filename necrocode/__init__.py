"""
NecroCode v2 - Kiro-Native Task Orchestration
"""
from .task_planner import Task, TaskPlanner
from .task_context import TaskContextGenerator
from .orchestrator import KiroOrchestrator

__version__ = "2.0.0"
__all__ = ["Task", "TaskPlanner", "TaskContextGenerator", "KiroOrchestrator"]

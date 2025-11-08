"""Spirit Protocol primitives."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# Spirit Protocol Message Types
class MessageType:
    """Enumeration of all supported Spirit Protocol message types."""
    
    # Core workflow messages
    SUMMONING = "summoning"  # Necromancer → Spirit (initialization)
    TASK_ASSIGNMENT = "task_assignment"  # Scrum Master → Dev Spirit
    TASK_COMPLETED = "task_completed"  # Dev Spirit → Scrum Master
    
    # Coordination messages
    API_READY = "api_ready"  # Backend → Frontend
    SCHEMA_READY = "schema_ready"  # Database → Backend
    TEST_FAILURE = "test_failure"  # QA → Scrum Master
    CONFLICT_RESOLUTION = "conflict_resolution"  # Scrum Master → Any Spirit
    DEPLOYMENT_READY = "deployment_ready"  # DevOps → Necromancer
    
    # NEW: Issue routing and load balancing messages
    ISSUE_ASSIGNMENT = "issue_assignment"  # IssueRouter → Agent
    WORKLOAD_QUERY = "workload_query"  # IssueRouter/Scrum Master → Agent
    AGENT_STATUS = "agent_status"  # Agent → IssueRouter/Scrum Master


@dataclass
class AgentMessage:
    """
    Core message structure for Spirit Protocol communication.
    
    Enhanced to support issue tracking and agent instance identification.
    """
    sender: str
    receiver: str
    workspace: str
    message_type: str
    payload: Dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # NEW: Optional fields for enhanced routing and tracking
    issue_id: Optional[str] = None  # Related issue ID for tracking
    agent_instance: Optional[str] = None  # Specific agent instance identifier


@dataclass
class Issue:
    """Represents a work item that can be assigned to agents."""
    id: str
    title: str
    description: str
    labels: List[str] = field(default_factory=list)
    priority: str = "medium"  # "high", "medium", "low"
    assigned_to: str = ""  # Agent identifier like "frontend_spirit_1"
    status: str = "open"  # "open", "assigned", "in_progress", "completed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentInstance:
    """Represents a specific instance of an agent with workload tracking."""
    identifier: str  # "frontend_spirit_1"
    role: str  # "frontend"
    instance_number: int  # 1
    skills: List[str] = field(default_factory=list)
    workspace: str = "workspace1"
    current_tasks: List[str] = field(default_factory=list)  # ["TASK-001", "TASK-005"]
    completed_tasks: List[str] = field(default_factory=list)  # ["TASK-002", "TASK-003"]
    active_branches: List[str] = field(default_factory=list)  # ["frontend/issue-42-login-ui"]
    status: str = "idle"  # "idle", "busy", "blocked"


@dataclass
class Task:
    """Represents a specific task assigned to an agent instance."""
    id: str  # "TASK-001"
    agent: str  # "database" (agent type)
    agent_instance: str  # "database_spirit_1" (specific instance)
    task: str  # "Create User schema"
    issue_id: str = ""  # Related issue ID
    status: str = "assigned"  # "assigned", "in_progress", "completed"
    blocking: List[str] = field(default_factory=list)  # ["backend", "frontend"]
    branch_name: str = ""  # Git branch for this task


# Message Payload Specifications
# ==============================
# 
# ISSUE_ASSIGNMENT:
#   payload: {
#       "issue": Issue,  # The issue being assigned
#       "reason": str,   # Why this agent was selected (e.g., "keyword match: ui, component")
#       "priority": str  # "high", "medium", "low"
#   }
#   issue_id: str  # Issue ID for tracking
#   agent_instance: str  # Target agent instance identifier
#
# WORKLOAD_QUERY:
#   payload: {
#       "query_type": str,  # "current_load", "availability", "capacity"
#       "requester": str    # Who is asking (for response routing)
#   }
#   Response expected via AGENT_STATUS message
#
# AGENT_STATUS:
#   payload: {
#       "status": str,  # "idle", "busy", "blocked"
#       "current_tasks": List[str],  # Active task IDs
#       "completed_tasks": List[str],  # Completed task IDs
#       "workload": int,  # Number of active tasks
#       "capacity": int,  # Maximum concurrent tasks (default: 3)
#       "active_branches": List[str]  # Current Git branches
#   }
#   agent_instance: str  # Reporting agent instance identifier

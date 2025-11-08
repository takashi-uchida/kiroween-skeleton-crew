"""Spirit Protocol primitives."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    workspace: str
    message_type: str
    payload: Dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
